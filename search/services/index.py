"""Integration with search index."""

import re
import json
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
    Classification, AdvancedQuery, SimpleQuery, AuthorQuery, Author

logger = logging.getLogger(__name__)

MAX_RESULTS = 10_000


class MappingError(ValueError):
    """There was a problem with the search document mapping."""


class IndexConnectionError(IOError):
    """There was a problem connecting to the search index."""


class IndexingError(IOError):
    """There was a problem adding a document to the index."""


class QueryError(ValueError):
    """
    Elasticsearch could not handle the query.

    This is likely due either to a programming error that resulted in a bad
    index, or to a mal-formed query.
    """


class DocumentNotFound(RuntimeError):
    """Could not find a requested document in the search index."""


class OutsideAllowedRange(RuntimeError):
    """A page outside of the allowed range has been requested."""


# We'll compile this ahead of time, since it gets called quite a lot.
STRING_LITERAL = re.compile(r"(['\"][^'\"]*['\"])")


def _wildcardEscape(querystring: str) -> Tuple[str, bool]:
    """
    Detect wildcard characters, and escape any that occur within a literal.

    Parameters
    ----------
    querystring : str

    Returns
    -------
    str
        Query string with wildcard characters enclosed in literals escaped.
    bool
        If a non-literal wildcard character is present, returns True.

    """
    # This should get caught by the controller (form validation), but just
    # in case we should check for it here.
    if querystring.startswith('?') or querystring.startswith('*'):
        raise QueryError('Query cannot start with a wildcard')

    # Escape wildcard characters within string literals.
    # re.sub() can't handle the complexity, sadly...
    parts = re.split(STRING_LITERAL, querystring)
    parts = [part.replace('*', r'\*').replace('?', r'\?')
             if part.startswith('"') or part.startswith("'") else part
             for part in parts]
    querystring = "".join(parts)

    # Only unescaped wildcard characters should remain.
    wildcard = re.search(r'(?<!\\)([\*\?])', querystring) is not None
    return querystring, wildcard


def _Q(qtype: str, field: str, value: str) -> Q:
    """Construct a :class:`.Q`, but handle wildcards first."""
    value, wildcard = _wildcardEscape(value)
    if wildcard:
        return Q('wildcard', **{field: value})
    return Q(qtype, **{field: value})


class SearchSession(object):
    """Encapsulates session with Elasticsearch host."""

    # TODO: we need to take on security considerations here. Presumably we will
    # use SSL. Presumably we will use HTTP Auth, or something else.

    def __init__(self, host: str, index: str, port: int=9200,
                 scheme: str='http', user: Optional[str]=None,
                 password: Optional[str]=None, mapping: Optional[str]=None,
                 **extra) -> None:
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
        logger.debug('init ES session for index "%s" at %s:%s',
                     index, host, port)
        self.index = index
        self.mapping = mapping
        use_ssl = True if scheme == 'https' else False
        http_auth = '%s:%s' % (user, password) if user else None
        try:
            self.es = Elasticsearch([{'host': host, 'port': port,
                                      'scheme': scheme, 'use_ssl': use_ssl,
                                      'http_auth': http_auth}],
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
    def _group_terms(query: Query) -> tuple:
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
        if field in ['title', 'abstract']:
            return (
                Q("simple_query_string", fields=[
                    field,
                    f'{field}__tex',
                    f'{field}__english'
                  ], query=term)
            )
        # These terms have no additional fields.
        elif field in ['comments']:
            return Q("simple_query_string", fields=[field], query=term)
        # These terms require a match_phrase search.
        elif field in ['journal_ref', 'report_num']:
            return _Q('match_phrase', field, term)
        # These terms require a simple match.
        elif field in ['acm_class', 'msc_class', 'doi']:
            return _Q('match', field, term)
        # Search both with and without version.
        elif field == 'paper_id':
            return (
                _Q('match', 'paper_id', term)
                | _Q('match', 'paper_id_v', term)
            )
        elif field in ['orcid', 'author_id']:
            return (
                Q("nested", path="authors",
                  query=_Q('match', f'authors__{field}', term))
                | Q("nested", path="owners",
                    query=_Q('match', f'owners__{field}', term))
                | _Q('match', f'submitter__{field}', term)
            )

        elif field == 'author':
            return (
                Q('nested', path='authors', query=(
                    _Q('match', 'authors__first_name__folded', term)
                    | _Q('match', 'authors__last_name__folded', term)
                    | _Q('match', 'authors__full_name__folded', term)
                ))
                | Q('nested', path='owners', query=(
                    _Q('match', 'owners__first_name__folded', term)
                    | _Q('match', 'owners__last_name__folded', term)
                    | _Q('match', 'owners__full_name__folded', term)
                ))
                | (
                    _Q('match', 'submitter__name', term)
                    & Q('match', **{'submitter__is_author': True})
                )
            )
        return _Q("match", field, term)

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
    def _daterange_to_q(query: Query) -> Range:
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
    def _fielded_terms_to_q(cls, query: Query) -> Match:
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
    def _classifications_to_q(cls, query: Query) -> Match:
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
        if query.order is None:
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

    def _author_query_part(self, author: Author, field: str) -> Search:
        _q = None
        if author.surname:
            _q = _Q('match', f'{field}__last_name__folded', author.surname)
            if author.forename:    # Try as both forename and initials.
                _q_init = Q()
                for i in author.forename.replace('.', ' ').split():
                    _q_init &= _Q('match', f'{field}__initials__folded', i)
                _q &= (
                    _Q('match', f'{field}__first_name__folded',
                       author.forename)
                    | _q_init
                )
        if author.surname and author.fullname:
            _q |= _Q('match', f'{field}__full_name', author.fullname)
        elif author.fullname:
            _q = _Q('match', f'{field}__full_name', author.fullname)
        return _q

    def _prepare_author(self, query: AuthorQuery) -> Search:
        current_search = self._base_search().filter("term", is_current=True)
        q = Q()
        for au in query.authors:
            # We should be checking this in the controller (e.g. form data
            # validation), but just in case...
            if not (au.surname or au.fullname):
                raise ValueError('Surname or fullname must be set')

            # We may get a higher-quality hit from owners.
            # TODO: consider weighting owner-hits more highly?
            q &= (
                Q('nested', path='authors',
                  query=self._author_query_part(au, 'authors'))
                | Q('nested', path='owners',
                    query=self._author_query_part(au, 'owners'))
                | (_Q('match', 'submitter__name',
                      f'{au.forename} {au.surname} {au.fullname}')
                   & Q('match', **{'submitter__is_author': True}))
            )
        current_search = current_search.query(q)
        current_search = self._apply_sort(query, current_search)
        return current_search

    def _try_create_index(self):
        try:
            logger.error('Index not found; attempting to create')
            with open(self.mapping) as f:
                mapping = json.load(f)
            self.create_index(mapping)
        except Exception as e:
            raise IndexConnectionError(
                'Could not create index: %s' % e
            ) from e

    def create_index(self, mappings: dict) -> None:
        """
        Create the search index.

        Parameters
        ----------
        mappings : dict
            See
            elastic.co/guide/en/elasticsearch/reference/current/mapping.html

        """
        logger.debug('create ES index "%s"', self.index)
        try:
            self.es.indices.create(self.index, mappings)
        except TransportError as e:
            if e.error == 'resource_already_exists_exception':
                logger.debug('Index already exists; move along')
            elif e.error == 'mapper_parsing_exception':
                logger.error('Invalid document mapping; create index failed')
                logger.debug(str(e.info))
                raise MappingError('Invalid mapping: %s' % str(e.info)) from e
            else:
                raise RuntimeError('Unhandled exception: %s' % str(e)) from e

    def add_document(self, document: Document) -> None:
        """
        Add a document to the search index.

        Uses ``paper_id_v`` as the primary identifier for the document. If the
        document is already indexed, will quietly overwrite.

        Paramters
        ---------
        document : :class:`.Document`
            Must be a valid search document, per ``schema/Document.json``.

        Raises
        ------
        IndexConnectionError
            Problem communicating with Elasticsearch host.
        QueryError
            Problem serializing ``document`` for indexing.

        """
        try:
            ident = document.get('id', document['paper_id'])
            self.es.index(index=self.index, doc_type='document',
                          id=ident, body=document)
        except SerializationError as e:
            logger.error("SerializationError: %s", e)
            raise IndexingError('Problem serializing document: %s' % e) from e
        except TransportError as e:
            if e.error == 'index_not_found_exception':
                self._try_create_index()
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
        try:
            actions = ({
                '_index': self.index,
                '_type': 'document',
                '_id': document.get('id', document['paper_id']),
                '_source': document
            } for document in documents)

            helpers.bulk(client=self.es, actions=actions,
                         chunk_size=docs_per_chunk)

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
                self._try_create_index()
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
                self._try_create_index()
            raise IndexConnectionError(
                'Problem communicating with ES: %s' % e
            ) from e
        if not record:
            logger.error("No such document: %s", document_id)
            raise DocumentNotFound('No such document')
        return Document(**record['_source'])

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
        elif isinstance(query, AuthorQuery):
            current_search = self._prepare_author(query)
        logger.debug(str(current_search.to_dict()))

        try:
            results = current_search[query.page_start:query.page_end].execute()
        except TransportError as e:
            logger.error("TransportError: %s", e)
            if e.error == 'index_not_found_exception':
                self._try_create_index()
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

        return DocumentSet(**{
            'metadata': {
                'start': query.page_start,
                'total': results['hits']['total'],
                'current_page': query.page,
                'total_pages': N_pages,
                'page_size': query.page_size,
                'max_pages': max_pages
            },
            'results': [self._transform(raw) for raw in results]
        })

    def _transform(self, raw: Response) -> Document:
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
            result[key] = value
        result['score'] = raw.meta.score

        return Document(**result)


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('ELASTICSEARCH_HOST', 'localhost')
    config.setdefault('ELASTICSEARCH_PORT', '9200')
    config.setdefault('ELASTICSEARCH_INDEX', 'arxiv')
    config.setdefault('ELASTICSEARCH_USER', 'elastic')
    config.setdefault('ELASTICSEARCH_PASSWORD', 'changeme')
    config.setdefault('ELASTICSEARCH_MAPPING', 'mappings/DocumentMapping.json')


def get_session(app: object = None) -> SearchSession:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('ELASTICSEARCH_HOST', 'localhost')
    port = config.get('ELASTICSEARCH_PORT', '9200')
    scheme = config.get('ELASTICSEARCH_SCHEME', 'http')
    index = config.get('ELASTICSEARCH_INDEX', 'arxiv')
    user = config.get('ELASTICSEARCH_USER', 'elastic')
    password = config.get('ELASTICSEARCH_PASSWORD', 'changeme')
    mapping = config.get('ELASTICSEARCH_MAPPING',
                         'mappings/DocumentMapping.json')
    return SearchSession(host, index, port, scheme, user, password, mapping)


def current_session() -> SearchSession:
    """Get/create :class:`.SearchSession` for this context."""
    g = get_application_global()
    if not g:
        return get_session()
    if 'search' not in g:
        g.search = get_session()    #type: ignore
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


def ok() -> bool:
    """Health check."""
    try:
        current_session()
    except Exception:    # TODO: be more specific.
        return False
    return True
