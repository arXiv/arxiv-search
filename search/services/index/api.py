"""Supports the advanced search feature."""

from operator import ior
from functools import reduce
from typing import Any, Tuple

from elasticsearch_dsl import Search, Q, SF
from elasticsearch_dsl.query import Range, Match

from search.domain import APIQuery
from search.services.index.util import sort
from search.services.index.prepare import (
    SEARCH_FIELDS,
    query_primary_exact,
    query_secondary_exact,
)


def api_search(search: Search, query: APIQuery) -> Search:
    """
    Prepare a :class:`.Search` from a :class:`.APIQuery`.

    Parameters
    ----------
    search : :class:`.Search`
        An Elasticsearch search in preparation.
    query : :class:`.APIQuery`
        An query originating from the API.

    Returns
    -------
    :class:`.Search`
        The passed ES search object, updated with specific query parameters
        that implement the advanced query.

    """

    _q_clsn = Q()
    if query.primary_classification:
        _q_clsn &= reduce(
            ior, map(query_primary_exact, list(query.primary_classification))
        )
    if query.secondary_classification:
        for classification in query.secondary_classification:
            _q_clsn &= reduce(
                ior, map(query_secondary_exact, list(classification))
            )
    q = _fielded_terms_to_q(query) & _date_range(query) & _q_clsn
    if query.order is None or query.order == "relevance":
        # Boost the current version heavily when sorting by relevance.
        q = Q(
            "function_score",
            query=q,
            boost=5,
            boost_mode="multiply",
            score_mode="max",
            functions=[
                SF({"weight": 5, "filter": Q("term", is_current=True)})
            ],
        )
    search = sort(query, search)
    search = search.query(q)
    return search


def _date_range(q: APIQuery) -> Range:
    """Generate a query part for a date range."""
    if not q.date_range:
        return Q()
    params = {}
    if q.date_range.date_type == q.date_range.ANNOUNCED:
        fmt = "%Y-%m"
    else:
        fmt = "%Y-%m-%dT%H:%M:%S%z"
    if q.date_range.start_date:
        params["gte"] = q.date_range.start_date.strftime(fmt)
    if q.date_range.end_date:
        params["lt"] = q.date_range.end_date.strftime(fmt)
    return Q("range", **{q.date_range.date_type: params})


def _grouped_terms_to_q(term_pair: Tuple[Any, Any, Any]) -> Q:
    """Generate a :class:`.Q` from grouped terms."""
    term_a_raw, operator, term_b_raw = term_pair

    if type(term_a_raw) is tuple:
        term_a = _grouped_terms_to_q(term_a_raw)
    else:
        term_a = SEARCH_FIELDS[term_a_raw.field](term_a_raw.term)

    if type(term_b_raw) is tuple:
        term_b = _grouped_terms_to_q(term_b_raw)
    else:
        term_b = SEARCH_FIELDS[term_b_raw.field](term_b_raw.term)

    if operator == "OR":
        return term_a | term_b
    elif operator == "AND":
        return term_a & term_b
    elif operator == "NOT":
        return term_a & ~term_b
    else:
        # TODO: Confirm proper exception.
        raise TypeError("Invalid operator for terms")


def _get_operator(obj: Any) -> str:
    if type(obj) is tuple:
        return _get_operator(obj[0])
    return obj.operator  # type: ignore


# FIXME: Return type.
def _group_terms(query: APIQuery) -> Tuple[Any, ...]:
    """Group fielded search terms into a set of nested tuples."""
    terms = query.terms[:]
    for operator in ["NOT", "AND", "OR"]:
        i = 0
        while i < len(terms) - 1:
            if _get_operator(terms[i + 1]) == operator:
                terms[i] = (terms[i], operator, terms[i + 1])
                terms.pop(i + 1)
                i -= 1
            i += 1
    assert len(terms) == 1
    return terms[0]  # type: ignore


def _fielded_terms_to_q(query: APIQuery) -> Match:
    if len(query.terms) == 1:
        return SEARCH_FIELDS[query.terms[0].field](query.terms[0].term)
    elif len(query.terms) > 1:
        return _grouped_terms_to_q(_group_terms(query))  # type:ignore
    return Q("match_all")
