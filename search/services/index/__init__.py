"""
Provides integration with an ElasticSearch cluster.

The primary entrypoint to this module is :func:`.search`, which handles
:class:`search.domain.Query` instances passed by controllers, and returns a
:class:`.DocumentSet` containing search results. :func:`.get_document` is
available for future use, e.g. as part of a search API.

In addition, :func:`.add_document` and :func:`.bulk_add_documents` are provided
for indexing (e.g. by the
:mod:`search.agent.consumer.MetadataRecordProcessor`).

:class:`.SearchSession` encapsulates configuration parameters and a connection
to the Elasticsearch cluster for thread-safety. The functions mentioned above
load the appropriate instance of :class:`.SearchSession` depending on the
context of the request.
"""

import re
import json
import urllib3
from math import floor
from datetime import datetime
from typing import Any, Optional, Tuple, Union, List
from functools import wraps
from elasticsearch import Elasticsearch, ElasticsearchException, \
                          SerializationError, TransportError, helpers
from elasticsearch.connection import Urllib3HttpConnection
from elasticsearch.helpers import BulkIndexError

from elasticsearch_dsl import Search, Q, SF
from elasticsearch_dsl.query import Range, Match, Bool
from elasticsearch_dsl.response import Response

from search.context import get_application_config, get_application_global
from search import logging
from search.domain import Document, DocumentSet, Query, DateRange, \
    Classification, AdvancedQuery, SimpleQuery, asdict

from .exceptions import QueryError, IndexConnectionError, DocumentNotFound, \
    IndexingError, OutsideAllowedRange, MappingError
from .util import Q_, wildcardEscape
from .authors import construct_author_query, construct_author_id_query


logger = logging.getLogger(__name__)

# TODO: make this configurable.
MAX_RESULTS = 10_000
"""This is the maximum result offset for pagination."""


class SearchSession(object):
    """Encapsulates session with Elasticsearch host."""

    # TODO: we need to take on security considerations here. Presumably we will
    # use SSL. Presumably we will use HTTP Auth, or something else.

    def __init__(self, host: str, index: str, port: int=9200,
                 scheme: str='http', user: Optional[str]=None,
                 password: Optional[str]=None, mapping: Optional[str]=None,
                 verify: bool=True, **extra: Any) -> None:
        """
        Initialize the connection to Elasticsearch.

        Parameters
        ----------
        host : str
        index : str
        port : int
            Default: 9200
        scheme: str
            Default: 'http'
        user: str
            Default: None
        password: str
            Default: None

        Raises
        ------
        IndexConnectionError
            Problem communicating with Elasticsearch host.


        """
        self.index = index
        self.mapping = mapping
        use_ssl = True if scheme == 'https' else False
        http_auth = '%s:%s' % (user, password) if user else None

        logger.debug(
            f'init ES session for index "{index}" at {scheme}://{host}:{port}'
            f' with verify={verify} and ssl={use_ssl}'
        )

        try:
            self.es = Elasticsearch([{'host': host, 'port': port,
                                      'use_ssl': use_ssl,
                                      'http_auth': http_auth,
                                      'verify_certs': verify}],
                                    connection_class=Urllib3HttpConnection,
                                    **extra)
        except ElasticsearchException as e:
            logger.error('ElasticsearchException: %s', e)
            raise IndexConnectionError(
                'Could not initialize ES session: %s' % e
            ) from e

    # TODO: Verify type of `SearchSession._get_operator(obj)`
    @staticmethod
    def _get_operator(obj: Any) -> str:
        if type(obj) is tuple:
            return SearchSession._get_operator(obj[0])
        return obj.operator     # type: ignore

    @staticmethod
    def _group_terms(query: AdvancedQuery) -> tuple:
        """Group fielded search terms into a set of nested tuples."""
        terms = query.terms[:]
        for operator in ['NOT', 'AND', 'OR']:
            i = 0
            while i < len(terms) - 1:
                if SearchSession._get_operator(terms[i+1]) == operator:
                    terms[i] = (terms[i], operator, terms[i+1])
                    terms.pop(i+1)
                    i -= 1
                i += 1
        assert len(terms) == 1
        return terms[0]     # type: ignore

    @staticmethod
    def _field_term_to_q(field: str, term: str) -> Q:
        # These terms have fields for both TeX and English normalization.
        term = term.lower()
        if field in ['title', 'abstract']:
            return (
                Q("simple_query_string", fields=[
                    field,
                    f'{field}__tex',
                    f'{field}__english',
                    f'{field}_utf8',
                    f'{field}_utf8__tex',
                    f'{field}_utf8__english',
                  ], query=term)
            )
        # These terms have no additional fields.
        elif field in ['comments']:
            return Q("simple_query_string", fields=[field], query=term)
        # These terms require a match_phrase search.
        elif field in ['journal_ref', 'report_num']:
            return Q_('match_phrase', field, term)
        # These terms require a simple match.
        elif field in ['acm_class', 'msc_class', 'doi']:
            return Q_('match', field, term)
        # Search both with and without version.
        elif field == 'paper_id':
            return (
                Q_('match', 'paper_id', term)
                | Q_('match', 'paper_id_v', term)
            )
        elif field in ['orcid', 'author_id']:
            return construct_author_id_query(field, term)
        elif field == 'author':
            return construct_author_query(term)
        return Q_("match", field, term)

    @staticmethod
    def _grouped_terms_to_q(term_pair: tuple) -> Q:
        """Generate a :class:`.Q` from grouped terms."""
        term_a_raw, operator, term_b_raw = term_pair

        if type(term_a_raw) is tuple:
            term_a = SearchSession._grouped_terms_to_q(term_a_raw)
        else:
            term_a = SearchSession._field_term_to_q(term_a_raw.field,
                                                    term_a_raw.term)

        if type(term_b_raw) is tuple:
            term_b = SearchSession._grouped_terms_to_q(term_b_raw)
        else:
            term_b = SearchSession._field_term_to_q(term_b_raw.field,
                                                    term_b_raw.term)

        if operator == 'OR':
            return term_a | term_b
        elif operator == 'AND':
            return term_a & term_b
        elif operator == 'NOT':
            return term_a & ~term_b
        else:
            # TODO: Confirm proper exception.
            raise TypeError("Invalid operator for terms")

    @staticmethod
    def _daterange_to_q(query: AdvancedQuery) -> Range:
        if not query.date_range:
            return Q()
        params = {}
        if query.date_range.start_date:
            params["gte"] = query.date_range.start_date \
                .strftime('%Y-%m-%dT%H:%M:%S%z')
        if query.date_range.end_date:
            params["lt"] = query.date_range.end_date\
                .strftime('%Y-%m-%dT%H:%M:%S%z')
        return Q('range', submitted_date=params)

    @classmethod
    def _fielded_terms_to_q(cls, query: AdvancedQuery) -> Match:
        if len(query.terms) == 1:
            term = query.terms[0]
            return SearchSession._field_term_to_q(term.field, term.term)
            # return Q("match", **{query.terms[0].field: query.terms[0].term})
        elif len(query.terms) > 1:
            terms = cls._group_terms(query)
            return cls._grouped_terms_to_q(terms)
        return Q('match_all')

    @staticmethod
    def _classification_to_q(field: str, classification: Classification) \
            -> Match:
        q = Q()
        if classification.group:
            field_name = '%s__group__id' % field
            q &= Q('match', **{field_name: classification.group})
        if classification.archive:
            field_name = '%s__archive__id' % field
            q &= Q('match', **{field_name: classification.archive})
        if classification.category:
            field_name = '%s__category__id' % field
            q &= Q('match', **{field_name: classification.category})
        return q    # Q('nested', path=field, query=q)

    @classmethod
    def _classifications_to_q(cls, query: AdvancedQuery) -> Match:
        if not query.primary_classification:
            return Q()
        q = cls._classification_to_q('primary_classification',
                                     query.primary_classification[0])
        if len(query.primary_classification) > 1:
            for classification in query.primary_classification[1:]:
                q |= cls._classification_to_q('primary_classification',
                                              classification)
        return q

    @classmethod
    def _get_sort_parameters(cls, query: Query) -> list:
        if not query.order:
            return ['_score', '_doc']
        else:
            return [query.order, '_score', '_doc']

    def _apply_sort(self, query: Query, current_search: Search) -> Search:
        sort_params = self._get_sort_parameters(query)
        if sort_params is not None:
            current_search = current_search.sort(*sort_params)
        return current_search

    def _base_search(self) -> Search:
        return Search(using=self.es, index=self.index)

    def _prepare(self, query: AdvancedQuery) -> Search:
        """Generate an ES :class:`.Search` from a :class:`.AdvancedQuery`."""
        current_search = self._base_search()
        q = (
            self._fielded_terms_to_q(query)
            & self._daterange_to_q(query)
            & self._classifications_to_q(query)
        )
        if query.order is None or query.order == 'relevance':
            # Boost the current version heavily when sorting by relevance.
            logger.debug('apply filter functions')
            q = Q('function_score', query=q, boost=5, boost_mode="multiply",
                  score_mode="max",
                  functions=[
                    SF({'weight': 5, 'filter': Q('term', is_current=True)})
                  ])
        current_search = self._apply_sort(query, current_search)
        current_search = current_search.query(q)

        return current_search

    def _prepare_simple(self, query: SimpleQuery) -> Search:
        """Generate an ES :class:`.Search` from a :class:`.SimpleQuery`."""
        current_search = self._base_search().filter("term", is_current=True)
        if query.field == 'all':
            q = (
                self._field_term_to_q('author', query.value)
                | self._field_term_to_q('title', query.value)
                | self._field_term_to_q('abstract', query.value)
                | self._field_term_to_q('comments', query.value)
                | self._field_term_to_q('journal_ref', query.value)
                | self._field_term_to_q('acm_class', query.value)
                | self._field_term_to_q('msc_class', query.value)
                | self._field_term_to_q('report_num', query.value)
                | self._field_term_to_q('paper_id', query.value)
                | self._field_term_to_q('doi', query.value)
                | self._field_term_to_q('orcid', query.value)
                | self._field_term_to_q('author_id', query.value)
            )
        else:
            q = self._field_term_to_q(query.field, query.value)
        current_search = current_search.query(q)
        current_search = self._apply_sort(query, current_search)
        return current_search

    # def _author_query_part(self, author, field: str) -> Search:
    #     _q = None
    #     if author.surname:
    #         _q = Q_('match', f'{field}__last_name__folded', author.surname)
    #         if author.forename:    # Try as both forename and initials.
    #             _q_forename = Q_('match', f'{field}__first_name__folded',
    #                              author.forename)
    #             initials = author.forename.replace('.', ' ').split()
    #             if initials:
    #                 _q_init = Q()
    #                 for i in initials:
    #                     _q_init &= Q_('match', f'{field}__initials__folded', i)
    #                 _q &= (_q_forename | _q_init)
    #             else:
    #                 _q &= _q_forename
    #     if author.surname and author.fullname:
    #         _q |= Q_('match', f'{field}__full_name', author.fullname)
    #     elif author.fullname:
    #         _q = Q_('match', f'{field}__full_name', author.fullname)
    #     return _q

    def cluster_available(self) -> bool:
        """
        Determine whether or not the ES cluster is available.

        Returns
        -------
        bool
        """
        try:
            self.es.cluster.health(wait_for_status='yellow', request_timeout=1)
            return True
        except urllib3.exceptions.HTTPError as e:
            logger.debug('Health check failed: %s', str(e))
            return False
        except Exception as e:
            logger.debug('Health check failed: %s', str(e))
            return False

    def create_index(self) -> None:
        """
        Create the search index.

        Parameters
        ----------
        mappings : dict
            See
            elastic.co/guide/en/elasticsearch/reference/current/mapping.html

        """
        logger.debug('create ES index "%s"', self.index)
        if not self.mapping or type(self.mapping) is not str:
            raise IndexingError('Mapping not set')
        try:
            with open(self.mapping) as f:
                mappings = json.load(f)
            self.es.indices.create(self.index, mappings)
        except TransportError as e:
            if e.error == 'resource_already_exists_exception':
                logger.debug('Index already exists; move along')
                return
            elif e.error == 'mapper_parsing_exception':
                logger.error('Invalid document mapping; create index failed')
                logger.debug(str(e.info))
                raise MappingError('Invalid mapping: %s' % str(e.info)) from e
            logger.error('Problem communicating with ES: %s' % e.error)
            raise IndexConnectionError(
                'Problem communicating with ES: %s' % e.error
            ) from e

    def add_document(self, document: Document) -> None:
        """
        Add a document to the search index.

        Uses ``paper_id_v`` as the primary identifier for the document. If the
        document is already indexed, will quietly overwrite.

        Parameters
        ----------
        document : :class:`.Document`
            Must be a valid search document, per ``schema/Document.json``.

        Raises
        ------
        :class:`.IndexConnectionError`
            Problem communicating with Elasticsearch host.
        :class:`.QueryError`
            Problem serializing ``document`` for indexing.

        """
        if not self.es.indices.exists(index=self.index):
            self.create_index()
        try:
            ident = document.id if document.id else document.paper_id
            logger.debug(f'{ident}: index document')
            self.es.index(index=self.index, doc_type='document',
                          id=ident, body=document)
        except SerializationError as e:
            logger.error("SerializationError: %s", e)
            raise IndexingError('Problem serializing document: %s' % e) from e
        except TransportError as e:
            if e.error == 'index_not_found_exception':
                self.create_index()
            logger.error("TransportError: %s", e)
            raise IndexConnectionError(
                'Problem communicating with ES: %s' % e
            ) from e

    def bulk_add_documents(self, documents: List[Document],
                           docs_per_chunk: int = 500) -> None:
        """
        Add documents to the search index using the bulk API.

        Parameters
        ----------
        document : :class:`.Document`
            Must be a valid search document, per ``schema/Document.json``.
        docs_per_chunk: int
            Number of documents to send to ES in a single chunk
        Raises
        ------
        IndexConnectionError
            Problem communicating with Elasticsearch host.
        BulkIndexingError
            Problem serializing ``document`` for indexing.

        """
        if not self.es.indices.exists(index=self.index):
            logger.debug('index does not exist')
            self.create_index()
            logger.debug('created index')

        try:
            actions = ({
                '_index': self.index,
                '_type': 'document',
                '_id': document.id if document.id else document.paper_id,
                '_source': asdict(document)
            } for document in documents)

            helpers.bulk(client=self.es, actions=actions,
                         chunk_size=docs_per_chunk)
            logger.debug('added %i documents to index', len(documents))

        except SerializationError as e:
            logger.error("SerializationError: %s", e)
            raise IndexingError(
                'Problem serializing documents: %s' % e) from e
        except BulkIndexError as e:
            logger.error("BulkIndexError: %s", e)
            raise IndexingError('Problem with bulk indexing: %s' % e) from e
        except TransportError as e:
            logger.error("TransportError: %s", e)
            if e.error == 'index_not_found_exception':
                self.create_index()
            raise IndexConnectionError(
                'Problem communicating with ES: %s' % e
            ) from e

    def get_document(self, document_id: int) -> Document:
        """
        Retrieve a document from the index by ID.

        Uses ``metadata_id`` as the primary identifier for the document.

        Parameters
        ----------
        doument_id : int
            Value of ``metadata_id`` in the original document.

        Returns
        -------
        :class:`.Document`

        Raises
        ------
        IndexConnectionError
            Problem communicating with the search index.
        QueryError
            Invalid query parameters.

        """
        try:
            record = self.es.get(index=self.index, doc_type='document',
                                 id=document_id)
        except SerializationError as e:
            logger.error("SerializationError: %s", e)
            raise QueryError('Problem serializing document: %s' % e) from e
        except TransportError as e:
            logger.error("TransportError: %s", e)
            if e.error == 'index_not_found_exception':
                self.create_index()
            raise IndexConnectionError(
                'Problem communicating with ES: %s' % e
            ) from e
        if not record:
            logger.error("No such document: %s", document_id)
            raise DocumentNotFound('No such document')
        return Document(**record['_source'])    # type: ignore
        # See https://github.com/python/mypy/issues/3937

    def search(self, query: Query) -> DocumentSet:
        """
        Perform a search.

        Parameters
        ----------
        query : :class:`.Query`

        Returns
        -------
        :class:`.DocumentSet`

        Raises
        ------
        IndexConnectionError
            Problem communicating with the search index.
        QueryError
            Invalid query parameters.

        """
        logger.debug('got current_search request %s', str(query))
        if isinstance(query, AdvancedQuery):
            current_search = self._prepare(query)
        elif isinstance(query, SimpleQuery):
            current_search = self._prepare_simple(query)
        logger.debug(str(current_search.to_dict()))

        current_search = self._highlight(current_search)

        try:
            results = current_search[query.page_start:query.page_end].execute()
        except TransportError as e:
            logger.error("TransportError: %s", e)
            if e.error == 'index_not_found_exception':
                self.create_index()
            if e.error == 'parsing_exception':
                raise QueryError(e.info) from e
            raise IndexConnectionError(
                'Problem communicating with ES: %s' % e
            ) from e

        N_pages_raw = results['hits']['total']/query.page_size
        N_pages = int(floor(N_pages_raw)) + \
            int(N_pages_raw % query.page_size > 0)
        logger.debug('got %i results', results['hits']['total'])

        max_pages = int(MAX_RESULTS/query.page_size)
        if query.page > max_pages:
            _message = f'Requested page {query.page}, but max is {max_pages}'
            logger.error(_message)
            raise OutsideAllowedRange(_message)

        return DocumentSet(**{  # type: ignore
            'metadata': {
                'start': query.page_start,
                'end': min(query.page_start + query.page_size,
                           results['hits']['total']),
                'total': results['hits']['total'],
                'current_page': query.page,
                'total_pages': N_pages,
                'page_size': query.page_size,
                'max_pages': max_pages
            },
            'results': [self._to_document(raw) for raw in results]
        })
        # See https://github.com/python/mypy/issues/3937

    def _highlight(self, search: Search) -> Search:
        """Apply hit highlighting to the search, before execution."""
        # TODO: consider a .highlight class?
        search = search.highlight_options(
            pre_tags=['<span class="has-text-success has-text-weight-bold">'],
            post_tags=['</span>']
        )
        search = search.highlight('title*', type='plain')

        search = search.highlight('comments')
        # type=plain ensures that the field isn't truncated at a dot.
        search = search.highlight('journal_ref', type='plain')
        search = search.highlight('doi', type='plain')
        search = search.highlight('report_num', type='plain')
        search = search.highlight('abstract', type='plain', fragment_size=75)
        return search

    def _to_document(self, raw: Response) -> Document:
        """Transform an ES search result back into a :class:`.Document`."""
        # typing: ignore
        result = {}
        for key in Document.fields():
            if not hasattr(raw, key):
                continue
            value = getattr(raw, key)
            if key in ['submitted_date', 'submitted_date_first',
                       'submitted_date_latest']:
                try:
                    value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')
                except (ValueError, TypeError):
                    logger.warning(
                        f'Could not parse {key}: {value} as datetime'
                    )
                    pass

            # # Even though DOI is a string field, some users have crammed more
            # # than one DOI in. Since we're not
            # if key in ['doi']:
            #     value = value.split()
            result[key] = value
        result['score'] = raw.meta.score


        # Add highlighting to the result.
        if hasattr(raw.meta, 'highlight'):
            result['highlight'] = {}
            for field in dir(raw.meta.highlight):
                value = getattr(raw.meta.highlight, field)
                if field == 'abstract':
                    value = (
                        '&hellip;' + ('&hellip;'.join(value[:2])) + '&hellip;'
                    )
                else:
                    value = ' '.join(value)
                result['highlight'][field] = value

        return Document(**result)   # type: ignore
        # See https://github.com/python/mypy/issues/3937


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('ELASTICSEARCH_HOST', 'localhost')
    config.setdefault('ELASTICSEARCH_PORT', '9200')
    config.setdefault('ELASTICSEARCH_INDEX', 'arxiv')
    config.setdefault('ELASTICSEARCH_USER', None)
    config.setdefault('ELASTICSEARCH_PASSWORD', None)
    config.setdefault('ELASTICSEARCH_MAPPING', 'mappings/DocumentMapping.json')
    config.setdefault('ELASTICSEARCH_VERIFY', 'true')


# TODO: consider making this private.
def get_session(app: object = None) -> SearchSession:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('ELASTICSEARCH_HOST', 'localhost')
    port = config.get('ELASTICSEARCH_PORT', '9200')
    scheme = config.get('ELASTICSEARCH_SCHEME', 'http')
    index = config.get('ELASTICSEARCH_INDEX', 'arxiv')
    verify = config.get('ELASTICSEARCH_VERIFY', 'true') == 'true'
    user = config.get('ELASTICSEARCH_USER', None)
    password = config.get('ELASTICSEARCH_PASSWORD', None)
    mapping = config.get('ELASTICSEARCH_MAPPING',
                         'mappings/DocumentMapping.json')
    return SearchSession(host, index, port, scheme, user, password, mapping,
                         verify=verify)


# TODO: consider making this private.
def current_session() -> SearchSession:
    """Get/create :class:`.SearchSession` for this context."""
    g = get_application_global()
    if not g:
        return get_session()
    if 'search' not in g:
        g.search = get_session()    # type: ignore
    return g.search     # type: ignore


@wraps(SearchSession.search)
def search(query: Query) -> DocumentSet:
    """Retrieve search results."""
    return current_session().search(query)


@wraps(SearchSession.add_document)
def add_document(document: Document) -> None:
    """Add Document."""
    return current_session().add_document(document)


@wraps(SearchSession.bulk_add_documents)
def bulk_add_documents(documents: List[Document]) -> None:
    """Add Documents."""
    return current_session().bulk_add_documents(documents)


@wraps(SearchSession.get_document)
def get_document(document_id: int) -> Document:
    """Retrieve arxiv document by id."""
    return current_session().get_document(document_id)


@wraps(SearchSession.cluster_available)
def cluster_available() -> bool:
    """Check whether the cluster is available."""
    return current_session().cluster_available()


@wraps(SearchSession.create_index)
def create_index() -> None:
    """Create the search index."""
    current_session().create_index()


def ok() -> bool:
    """Health check."""
    try:
        current_session()
    except Exception:    # TODO: be more specific.
        return False
    return True
