"""Controller for search API requests."""

import pytz
from http import HTTPStatus
from collections import defaultdict
from typing import Tuple, Dict, Any, Optional, List, Union

import dateutil.parser
from mypy_extensions import TypedDict
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest, NotFound

from arxiv import taxonomy
import logging


from search import consts
from search.services import index
from search.controllers.util import paginate
from search.domain import (
    Query,
    APIQuery,
    FieldedSearchList,
    FieldedSearchTerm,
    DateRange,
    Classification,
    DocumentSet,
    ClassicAPIQuery,
)


logger = logging.getLogger(__name__)


SearchResponseData = TypedDict(
    "SearchResponseData",
    {"results": DocumentSet, "query": Union[Query, ClassicAPIQuery]},
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
    parsed_operators = (
        None  # Default in the event that there is not a Classic query.
    )
    try:
        parsed_operators, parsed_terms = _parse_search_query(
            params.get("query", "")
        )
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

    primary = params.get("primary_classification")
    if primary:
        primary_classification = _get_classification(
            primary, "primary_classification", query_terms
        )
        q.primary_classification = primary_classification

    secondaries = params.getlist("secondary_classification")
    if secondaries:
        q.secondary_classification = [
            _get_classification(sec, "secondary_classification", query_terms)
            for sec in secondaries
        ]

    include_fields = _get_include_fields(params, query_terms)
    if include_fields:
        q.include_fields += include_fields

    q = paginate(q, params)  # type: ignore
    document_set = index.SearchSession.search(  # type: ignore
        q, highlight=False
    )
    document_set["metadata"]["query"] = query_terms
    logger.debug(
        "Got document set with %i results", len(document_set["results"])
    )
    return {"results": document_set, "query": q}, HTTPStatus.OK, {}


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
        document = index.SearchSession.current_session().get_document(
            paper_id
        )  # type: ignore
    except index.DocumentNotFound as ex:
        logger.error("Document not found")
        raise NotFound("No such document") from ex
    return {"results": document}, HTTPStatus.OK, {}


def _get_include_fields(params: MultiDict, query_terms: List) -> List[str]:
    include_fields: List[str] = params.getlist("include")

    if include_fields:
        for field in include_fields:
            # hack to exclude submitter field from results
            if field == 'submitter':
                include_fields.remove('submitter')
            else:
                query_terms.append({"parameter": "include", "value": field})
        return include_fields
    return []


def _get_fielded_terms(
    params: MultiDict,
    query_terms: List,
    operators: Optional[Dict[str, Any]] = None,
) -> Optional[FieldedSearchList]:
    if operators is None:
        operators = defaultdict(lambda: "AND")
    terms = FieldedSearchList()
    for field, _ in Query.SUPPORTED_FIELDS:
        values = params.getlist(field)
        for value in values:
            query_terms.append({"parameter": field, "value": value})
            terms.append(
                FieldedSearchTerm(  # type: ignore
                    operator=operators[field], field=field, term=value
                )
            )
    if not terms:
        return None
    return terms


def _get_date_params(
    params: MultiDict, query_terms: List
) -> Optional[DateRange]:
    date_params = {}
    for field in ["start_date", "end_date"]:
        value = params.getlist(field)
        if not value:
            continue
        try:
            dt = dateutil.parser.parse(value[0])
            if not dt.tzinfo:
                dt = pytz.utc.localize(dt)
            dt = dt.replace(tzinfo=consts.EASTERN)
        except ValueError:
            raise BadRequest(f"Invalid datetime in {field}")
        date_params[field] = dt
        query_terms.append({"parameter": field, "value": dt})
    if "date_type" in params:
        date_params["date_type"] = params.get("date_type")  # type: ignore
        query_terms.append(
            {"parameter": "date_type", "value": date_params["date_type"]}
        )
    if date_params:
        return DateRange(**date_params)  # type: ignore
    return None


def _to_classification(value: str) -> Tuple[Classification, ...]:
    clsns = []
    if value in taxonomy.definitions.GROUPS:
        klass = taxonomy.Group
        field = "group"
    elif value in taxonomy.definitions.ARCHIVES:
        klass = taxonomy.Archive
        field = "archive"
    elif value in taxonomy.definitions.CATEGORIES:
        klass = taxonomy.Category
        field = "category"
    else:
        raise ValueError("not a valid classification")
    cast_value = klass(value)
    clsns.append(Classification(**{field: {"id": value}}))  # type: ignore
    if cast_value.unalias() != cast_value:
        clsns.append(
            Classification(  # type: ignore # noqa: E501 # fmt: off
                **{field: {"id": cast_value.unalias()}}
            )
        )
    if (
        cast_value.canonical != cast_value
        and cast_value.canonical != cast_value.unalias()
    ):
        clsns.append(
            Classification(  # type: ignore # noqa: E501 # fmt: off
                **{field: {"id": cast_value.canonical}}
            )
        )
    return tuple(clsns)


def _get_classification(
    value: str, field: str, query_terms: List
) -> Tuple[Classification, ...]:
    try:
        clsns = _to_classification(value)
    except ValueError:
        raise BadRequest(f"Not a valid classification term: {field}={value}")
    query_terms.append({"parameter": field, "value": value})
    return clsns


SEARCH_QUERY_FIELDS = {
    "ti": "title",
    "au": "author",
    "abs": "abstract",
    "co": "comments",
    "jr": "journal_ref",
    "cat": "primary_classification",
    "rn": "report_number",
    "id": "paper_id",
    "all": "all",
}


def _parse_search_query(query: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Parses a query into tuple of operators and parameters."""
    new_query_params = {}
    new_query_operators: Dict[str, str] = defaultdict(lambda: "AND")
    terms = query.split()

    expect_new = True  # expect_new handles quotation state.
    next_operator = "AND"  # next_operator handles the operator state.

    for term in terms:
        if expect_new and term in ["AND", "OR", "ANDNOT", "NOT"]:
            if term == "ANDNOT":
                term = "NOT"  # Translate to NG representation.
            next_operator = term
        elif expect_new:
            field, term = term.split(":")

            # Quotation handling.
            if term.startswith('"') and not term.endswith('"'):
                expect_new = False
            term = term.replace('"', "")

            new_query_params[SEARCH_QUERY_FIELDS[field]] = term
            new_query_operators[SEARCH_QUERY_FIELDS[field]] = next_operator
        else:
            # If the term ends in a quote, we close the term and look for the
            # next one.
            if term.endswith('"'):
                expect_new = True
                term = term.replace('"', "")

            new_query_params[SEARCH_QUERY_FIELDS[field]] += " " + term

    return new_query_operators, new_query_params
