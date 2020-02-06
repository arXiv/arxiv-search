"""Supports the advanced search feature."""

from typing import Any, Union

from functools import reduce, wraps
from operator import ior, iand

from elasticsearch_dsl import Search, Q, SF
from elasticsearch_dsl.query import Range, Match, Bool

from search.domain import AdvancedQuery, Classification

from .prepare import SEARCH_FIELDS, limit_by_classification
from .util import sort


def advanced_search(search: Search, query: AdvancedQuery) -> Search:
    """
    Prepare a :class:`.Search` from a :class:`.AdvancedQuery`.

    Parameters
    ----------
    search : :class:`.Search`
        An Elasticsearch search in preparation.
    query : :class:`.AdvancedQuery`
        A query originating from the advanced search UI.

    Returns
    -------
    :class:`.Search`
        The passed ES search object, updated with specific query parameters
        that implement the advanced query.

    """
    # Classification and date are treated as filters; this foreshadows the
    # behavior of faceted search.
    if not query.include_older_versions:
        search = search.filter("term", is_current=True)
    _q_clsn = limit_by_classification(query.classification)
    if query.include_cross_list:
        _q_clsn |= limit_by_classification(
            query.classification, "secondary_classification"
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


def _date_range(q: AdvancedQuery) -> Range:
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


def _grouped_terms_to_q(term_pair: tuple) -> Q:
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


def _group_terms(query: AdvancedQuery) -> tuple:
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


def _fielded_terms_to_q(query: AdvancedQuery) -> Match:
    if len(query.terms) == 1:
        return SEARCH_FIELDS[query.terms[0].field](query.terms[0].term)
    elif len(query.terms) > 1:
        return _grouped_terms_to_q(_group_terms(query))
    return Q("match_all")
