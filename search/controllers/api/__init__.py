"""Controller for search API requests."""

from collections import defaultdict
from datetime import date, datetime
import re

from typing import Tuple, Dict, Any, Optional, List, Union
from mypy_extensions import TypedDict

from dateutil.relativedelta import relativedelta
import dateutil.parser
import pytz
from pytz import timezone
from werkzeug.datastructures import MultiDict, ImmutableMultiDict
from werkzeug.exceptions import InternalServerError, BadRequest, NotFound
from flask import url_for

from arxiv import status, taxonomy
from arxiv.base import logging

from search.services import index, fulltext, metadata
from search.controllers.util import paginate
from ...domain import Query, APIQuery, FieldedSearchList, FieldedSearchTerm, \
    DateRange, ClassificationList, Classification, asdict, DocumentSet, \
    Document, ClassicAPIQuery
from ...domain.api import Phrase, Term, Operator, Field
from .classic_parser import parse_classic_query

logger = logging.getLogger(__name__)
EASTERN = timezone('US/Eastern')

SearchResponseData = TypedDict(
    'SearchResponseData', 
    {'results': DocumentSet, 'query': Union[Query, ClassicAPIQuery]}
)


def search(params: MultiDict) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Handle a search request from the API.

    Parameters
    ----------
    params : :class:`MultiDict`
        GET query parameters from the request.

    Returns
    -------
    dict
        Response data (to serialize).
    int
        HTTP status code.
    dict
        Extra headers for the response.
    """
    q = APIQuery()

    # Parse NG queries utilizing the Classic API syntax.
    # This implementation parses the `query` parameter as if it were
    # using the Classic endpoint's `search_query` parameter. It is meant
    # as a migration pathway so that the URL and query structure aren't
    # both changed at the same time by end users.
    # TODO: Implement the NG API using the Classic API domain.
    parsed_operators = None  # Default in the event that there is not a Classic query.
    try:
        parsed_operators, parsed_terms = _parse_search_query(params.get('query', ''))
        params = params.copy()
        for field, term in parsed_terms.items():
            params.add(field, term)
    except ValueError:
        raise BadRequest(f"Improper syntax in query: {params.get('query')}")

    # process fielded terms, using the operators above
    query_terms: List[Dict[str, Any]] = []
    terms = _get_fielded_terms(params, query_terms, parsed_operators)

    if terms is not None:
        q.terms = terms
    date_range = _get_date_params(params, query_terms)
    if date_range is not None:
        q.date_range = date_range

    primary = params.get('primary_classification')
    if primary:
        primary_classification = _get_classification(primary,
                                                     'primary_classification',
                                                     query_terms)
        q.primary_classification = primary_classification

    secondaries = params.getlist('secondary_classification')
    if secondaries:
        q.secondary_classification = [
            _get_classification(sec, 'secondary_classification', query_terms)
            for sec in secondaries
        ]

    include_fields = _get_include_fields(params, query_terms)
    if include_fields:
        q.include_fields += include_fields

    q = paginate(q, params)     # type: ignore
    document_set = index.SearchSession.search(q, highlight=False)  # type: ignore
    document_set['metadata']['query'] = query_terms
    logger.debug('Got document set with %i results',
                 len(document_set['results']))
    return {'results': document_set, 'query': q}, status.HTTP_200_OK, {}


def classic_query(params: MultiDict) \
        -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Handle a search request from the Clasic API.

    First, the method maps old request parameters to new parameters:
    - search_query -> query
    - start -> start
    - max_results -> size

    Then the request is passed to :method:`search()` and returned.

    If ``id_list`` is specified in the parameters and ``search_query`` is
    NOT specified, then each request is passed to :method:`paper()` and
    results are aggregated.

    If ``id_list`` is specified AND ``search_query`` is also specified,
    then the results from :method:`search()` are filtered by ``id_list``.

    Parameters
    ----------
    params : :class:`MultiDict`
        GET query parameters from the request.

    Returns
    -------
    dict
        Response data (to serialize).
    int
        HTTP status code.
    dict
        Extra headers for the response.

    Raises
    ------
    :class:`BadRequest`
        Raised when the search_query and id_list are not specified.
    """
    params = params.copy()
    raw_query = params.get('search_query')

    # parse id_list
    id_list = params.get('id_list', '')
    if id_list:
        id_list = id_list.split(',')
    else:
        id_list = []

    # error if neither search_query nor id_list are specified.
    if not id_list and not raw_query:
        raise BadRequest("Either a search_query or id_list must be specified"
                         " for the classic API.")


    if raw_query:
        # migrate search_query -> query variable
        phrase = parse_classic_query(raw_query)
        # TODO: add support for order, size, page_start
        query = ClassicAPIQuery(phrase=phrase)

        # pass to search indexer, which will handle parsing
        document_set: DocumentSet = index.SearchSession.search(query)
        data: SearchResponseData = {'results': document_set, 'query': query}
        logger.debug('Got document set with %i results',
                     len(document_set['results']))

        if id_list: # and raw_query
            results = [paper for paper in document_set.results
                       if paper.paper_id in id_list or paper.paper_id_v in id_list]


            # TODO: Aggregate search metadata for response data
            data = {
                'results' : DocumentSet(results=results, metadata=dict()),
                'query' : query
            }

    elif id_list: # and not raw_query
        # Process only id_lists.
        # Note lack of error handling to implicitly propogate any errors.
        # Classic API also errors if even one ID is malformed.
        papers = [paper(paper_id) for paper_id in id_list]

        papers, _, _ = zip(*papers) # type: ignore
        results: List[Document] = [paper['results'] for paper in papers] # type: ignore
        # TODO: Aggregate search metadata in result set
        data = {
            'results' : DocumentSet(results=results, metadata=dict()),
            'query' : APIQuery() # TODO: Generate API query based on paper_ids
        }

    return data, status.HTTP_200_OK, {}



def paper(paper_id: str) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Handle a request for paper metadata from the API.

    Parameters
    ----------
    paper_id : str
        arXiv paper ID for the requested paper.

    Returns
    -------
    dict
        Response data (to serialize).
    int
        HTTP status code.
    dict
        Extra headers for the response.

    Raises
    ------
    :class:`NotFound`
        Raised when there is no document with the provided paper ID.

    """
    try:
        document = index.SearchSession.get_document(paper_id)    # type: ignore
    except index.DocumentNotFound as e:
        logger.error('Document not found')
        raise NotFound('No such document') from e
    return {'results': document}, status.HTTP_200_OK, {}


def _get_include_fields(params: MultiDict, query_terms: List) -> List[str]:
    include_fields: List[str] = params.getlist('include')
    if include_fields:
        for field in include_fields:
            query_terms.append({'parameter': 'include', 'value': field})
        return include_fields
    return []


def _get_fielded_terms(params: MultiDict, query_terms: List,
                       operators: Optional[Dict[str, Any]] = None) -> Optional[FieldedSearchList]:
    if operators is None:
        operators = defaultdict(default_factory=lambda: "AND")
    terms = FieldedSearchList()
    for field, _ in Query.SUPPORTED_FIELDS:
        values = params.getlist(field)
        for value in values:
            query_terms.append({'parameter': field, 'value': value})
            terms.append(FieldedSearchTerm(     # type: ignore
                operator=operators[field],
                field=field,
                term=value
            ))
    if not terms:
        return None
    return terms


def _get_date_params(params: MultiDict, query_terms: List) \
        -> Optional[DateRange]:
    date_params = {}
    for field in ['start_date', 'end_date']:
        value = params.getlist(field)
        if not value:
            continue
        try:
            dt = dateutil.parser.parse(value[0])
            if not dt.tzinfo:
                dt = pytz.utc.localize(dt)
            dt = dt.replace(tzinfo=EASTERN)
        except ValueError:
            raise BadRequest(f'Invalid datetime in {field}')
        date_params[field] = dt
        query_terms.append({'parameter': field, 'value': dt})
    if 'date_type' in params:
        date_params['date_type'] = params.get('date_type')   # type: ignore
        query_terms.append({'parameter': 'date_type',
                            'value': date_params['date_type']})
    if date_params:
        return DateRange(**date_params)  # type: ignore
    return None


def _to_classification(value: str) \
        -> Tuple[Classification, ...]:
    clsns = []
    if value in taxonomy.definitions.GROUPS:
        klass = taxonomy.Group
        field = 'group'
    elif value in taxonomy.definitions.ARCHIVES:
        klass = taxonomy.Archive
        field = 'archive'
    elif value in taxonomy.definitions.CATEGORIES:
        klass = taxonomy.Category
        field = 'category'
    else:
        raise ValueError('not a valid classification')
    cast_value = klass(value)
    clsns.append(Classification(**{field: {'id': value}}))   # type: ignore
    if cast_value.unalias() != cast_value:
        clsns.append(Classification(**{field: {'id': cast_value.unalias()}}))   # type: ignore
    if cast_value.canonical != cast_value \
            and cast_value.canonical != cast_value.unalias():
        clsns.append(Classification(**{field: {'id': cast_value.canonical}}))   # type: ignore
    return tuple(clsns)


def _get_classification(value: str, field: str, query_terms: List) \
        -> Tuple[Classification, ...]:
    try:
        clsns = _to_classification(value)
    except ValueError:
        raise BadRequest(f'Not a valid classification term: {field}={value}')
    query_terms.append({'parameter': field, 'value': value})
    return clsns

SEARCH_QUERY_FIELDS = {
    'ti' : 'title',
    'au' : 'author',
    'abs' : 'abstract',
    'co' : 'comments',
    'jr' : 'journal_ref',
    'cat' : 'primary_classification',
    'rn' : 'report_number',
    'id' : 'paper_id',
    'all' : 'all'
}


def _parse_search_query(query: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Parses a query into tuple of operators and parameters."""
    new_query_params = {}
    new_query_operators: Dict[str, str] = defaultdict(default_factory=lambda: "AND")
    terms = query.split()

    expect_new = True
    """expect_new handles quotation state."""
    next_operator = "AND"
    """new_bool handles the operator state """

    for term in terms:
        if expect_new and term in ["AND", "OR", "ANDNOT", "NOT"]:
            if term == "ANDNOT":
                term = "NOT" # translate to new representation
            next_operator = term
        elif expect_new:
            field, term = term.split(':')

            # quotation handling
            if term.startswith('"') and not term.endswith('"'):
                expect_new = False
            term = term.replace('"', '')

            new_query_params[SEARCH_QUERY_FIELDS[field]] = term
            new_query_operators[SEARCH_QUERY_FIELDS[field]] = next_operator
        else:
            # quotation handling, expecting more terms
            if term.endswith('"'):
                expect_new = True
                term = term.replace('"', '')

            new_query_params[SEARCH_QUERY_FIELDS[field]] += " " + term


    return new_query_operators, new_query_params


def _get_search_query(params: MultiDict, query_terms: List,
                      operators: Dict[str, Any]) -> Optional[FieldedSearchList]:
    terms = FieldedSearchList()
    for field, _ in Query.SUPPORTED_FIELDS:
        values = params.getlist(field)
        for value in values:
            query_terms.append({'parameter': field, 'value': value})
            terms.append(FieldedSearchTerm(     # type: ignore
                operator=operators[field],
                field=field,
                term=value
            ))

    if not terms:
        return None
    return terms
