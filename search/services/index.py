"""Integration with search index."""

import json
import re
from math import floor
from typing import Tuple
from functools import wraps
from elasticsearch import Elasticsearch, ElasticsearchException, \
                          SerializationError, TransportError
from elasticsearch.connection import Urllib3HttpConnection

from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.query import Range, Match, Bool

from search.context import get_application_config, get_application_global
from search import logging
from search.domain import Document, DocumentSet, Query, DateRange, \
    Classification, AdvancedQuery, SimpleQuery, AuthorQuery

logger = logging.getLogger(__name__)


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
    parts = [part.replace('*', '\*').replace('?', '\?')
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
    def __init__(self, host: str, index: str, scheme: str, port: int=9200,
                 **extra) -> None:
        """
        Initialize the connection to Elasticsearch.

        Parameters
        ----------
        host : str
        index : str
        scheme: str
        port : int
            Default: 9200

        Raises
        ------
        IndexConnectionError
            Problem communicating with Elasticsearch host.
        """
        logger.debug('init ES session for index "%s" at %s:%s',
                     index, host, port)
        self.index = index
        try:
            self.es = Elasticsearch([{'host': host, 'port': port,
                                      'scheme': scheme}],
                                    connection_class=Urllib3HttpConnection,
                                    **extra)
        except ElasticsearchException as e:
            raise IndexConnectionError(
                'Could not initialize ES session: %s' % e
            ) from e

    @staticmethod
    def _get_operator(obj):
        if type(obj) is tuple:
            return SearchSession._get_operator(obj[0])
        return obj.operator

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
        return terms[0]

    @staticmethod
    def _field_term_to_q(term) -> Q:
        if term.field in ['title', 'abstract']:
            return (
                _Q("match", f'{term.field}__tex', term.term)
                | _Q("match", f'{term.field}__english', term.term)
            )
        elif term.field == 'author':
            return Q('nested', path='authors', query=(
                _Q('match', 'authors__first_name__folded', term.term) |
                _Q('match', 'authors__last_name__folded', term.term)
            ))
        return _Q("match", term.field, term.term)

    @staticmethod
    def _grouped_terms_to_q(term_pair: tuple) -> Bool:
        """Generate a :class:`.Q` from grouped terms."""
        term_a, operator, term_b = term_pair
        if type(term_a) is tuple:
            term_a = SearchSession._grouped_terms_to_q(term_a)
        else:
            term_a = SearchSession._field_term_to_q(term_a)
        if type(term_b) is tuple:
            term_b = SearchSession._grouped_terms_to_q(term_b)
        else:
            term_b = SearchSession._field_term_to_q(term_b)
        if operator == 'OR':
            return term_a | term_b
        elif operator == 'AND':
            return term_a & term_b
        elif operator == 'NOT':
            return term_a & ~term_b

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
            return SearchSession._field_term_to_q(query.terms[0])
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
        return Q('nested', path=field, query=q)

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
            return
        return [query.order]

    def _apply_sort(self, query: Query, search: Search) -> Search:
        sort_params = self._get_sort_parameters(query)
        if sort_params is not None:
            search = search.sort(*sort_params)
        return search

    def _prepare(self, query: AdvancedQuery) -> Search:
        """Generate an ES :class:`.Search` from a :class:`.AdvancedQuery`."""
        search = Search(using=self.es, index=self.index)
        search = search.query(
            self._fielded_terms_to_q(query)
            & self._daterange_to_q(query)
            & self._classifications_to_q(query)
        )
        search = self._apply_sort(query, search)
        return search

    def _prepare_simple(self, query: SimpleQuery) -> Search:
        """Generate an ES :class:`.Search` from a :class:`.SimpleQuery`."""
        search = Search(using=self.es, index=self.index)
        if query.field == 'all':
            search = search.query(
                Q('nested', path='authors', query=(
                    _Q('match', 'authors__first_name__folded', query.value)
                    |
                    _Q('match', 'authors__last_name__folded', query.value)
                ))
                |
                _Q('match', 'title__english', query.value)
                |
                _Q('match', 'title__tex', query.value)
                |
                _Q('match', 'abstract__english', query.value)
                |
                _Q('match', 'abstract__tex', query.value)
            )
        elif query.field == 'author':
            search = search.query(
                Q('nested', path='authors', query=(
                    _Q('match', 'authors__first_name__folded', query.value)
                    |
                    _Q('match', 'authors__last_name__folded', query.value)
                ))
            )
        else:
            search = search.query(
                _Q('match', f'{query.field}__english', query.value)
                |
                _Q('match', f'{query.field}__tex', query.value)
            )
        search = self._apply_sort(query, search)
        return search

    def _prepare_author(self, query: AuthorQuery) -> Search:
        search = Search(using=self.es, index=self.index)
        q = Q()
        for au in query.authors:
            _q = _Q('match', 'authors__last_name__folded', au.surname)

            if au.forename:    # Try as both forename and initials.
                _q_init = Q()
                for i in au.forename.replace('.', ' ').split():
                    _q_init &= _Q('match', 'authors__initials__folded', i)
                _q &= (
                    _Q('match', 'authors__first_name__folded', au.forename)
                    |
                    _q_init
                )

            q &= Q('nested', path='authors', query=_q)
        search = self._apply_sort(query, search)
        return search.query(q)

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
        self.es.indices.create(self.index, mappings, ignore=400)

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
            raise IndexingError('Problem serializing document: %s' % e) from e
        except TransportError as e:
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
            raise QueryError('Problem serializing document: %s' % e) from e
        except TransportError as e:
            raise IndexConnectionError(
                'Problem communicating with ES: %s' % e
            ) from e
        if not record:
            raise DocumentNotFound('No such document')
        return Document(record['_source'])

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
        logger.debug('got search request %s', str(query))
        if isinstance(query, AdvancedQuery):
            search = self._prepare(query)
        elif isinstance(query, SimpleQuery):
            search = self._prepare_simple(query)
        elif isinstance(query, AuthorQuery):
            search = self._prepare_author(query)
        logger.debug(str(search.to_dict()))

        try:
            results = search[query.page_start:query.page_end].execute()
        except TransportError as e:
            if e.error == 'parsing_exception':
                raise QueryError(e.info) from e
            raise IndexConnectionError(
                'Problem communicating with ES: %s' % e
            ) from e

        N_pages_raw = results['hits']['total']/query.page_size
        N_pages = int(floor(N_pages_raw)) + \
            int(N_pages_raw % query.page_size > 0)
        logger.debug('got %i results', results['hits']['total'])
        return DocumentSet({
            'metadata': {
                'start': query.page_start,
                'total': results['hits']['total'],
                'current_page': query.page,
                'total_pages': N_pages,
                'page_size': query.page_size
            },
            'results': list(map(self._transform, results))
        })

    def _transform(self, raw: dict) -> Document:
        """Transform an ES search result back into a :class:`.Document`."""
        result = {}
        for key in dir(raw):
            result[key] = getattr(raw, key)
        # result = raw['_source']
        result['score'] = raw.meta.score
        return Document(result)


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('ELASTICSEARCH_HOST', 'localhost')
    config.setdefault('ELASTICSEARCH_PORT', '9200')
    config.setdefault('ELASTICSEARCH_INDEX', 'arxiv')
    config.setdefault('ELASTICSEARCH_USER', 'elastic')
    config.setdefault('ELASTICSEARCH_PASSWORD', 'changeme')


def get_session(app: object = None) -> SearchSession:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('ELASTICSEARCH_HOST', 'localhost')
    port = config.get('ELASTICSEARCH_PORT', '9200')
    scheme = config.get('ELASTICSEARCH_SCHEME', 'http')
    index = config.get('ELASTICSEARCH_INDEX', 'arxiv')
    user = config.get('ELASTICSEARCH_USER', 'elastic')
    password = config.get('ELASTICSEARCH_PASSWORD', 'changeme')
    return SearchSession(host, index, port,
                         http_auth='%s:%s' % (user, password))


def current_session():
    """Get/create :class:`.SearchSession` for this context."""
    g = get_application_global()
    if not g:
        return get_session()
    if 'search' not in g:
        g.search = get_session()
    return g.search


@wraps(SearchSession.search)
def search(query: Query) -> DocumentSet:
    return current_session().search(query)


@wraps(SearchSession.add_document)
def add_document(document: Document) -> None:
    return current_session().add_document(document)


@wraps(SearchSession.get_document)
def get_document(document_id: int) -> Document:
    return current_session().get_document(document_id)


def ok() -> bool:
    """Health check."""
    try:
        current_session()
    except Exception as e:    # TODO: be more specific.
        return False
    return True
