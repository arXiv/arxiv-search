"""Functions for preparing a :class:`.Search` (prior to execution)."""

from typing import Any
from functools import reduce, wraps
from operator import ior
import re

from elasticsearch_dsl import Search, Q, SF
from elasticsearch_dsl.query import Range, Match, Bool

from search.domain import SimpleQuery, Query, AdvancedQuery, Classification
from .util import strip_tex, Q_, HIGHLIGHT_TAG_OPEN, HIGHLIGHT_TAG_CLOSE, \
    is_tex_query
from .authors import construct_author_query, construct_author_id_query


ALL_SEARCH_FIELDS = ['author', 'title', 'abstract', 'comments', 'journal_ref',
                     'acm_class', 'msc_class', 'report_num', 'paper_id', 'doi',
                     'orcid', 'author_id']
TEX_FIELDS = ['title', 'abstract', 'comments']

SPECIAL_CHARACTERS = ['+', '-', '=', '&&', '||', '>', '<', '!', '(', ')', '{',
                      '}', '[', ']', '^', '~', ':', '\\', '/']


def _escape(term: str) -> str:
    """Escape special characters."""
    escaped = []
    for i, char in enumerate(term):
        if char in SPECIAL_CHARACTERS:
            escaped.append("\\")
        escaped.append(char)
    return "".join(escaped)


def _get_sort_parameters(query: Query) -> list:
    if not query.order:
        return ['_score', '-announced_date_first', '_doc']
    direction = '-' if query.order.startswith('-') else ''
    return [query.order, f'{direction}paper_id_v']


def _apply_sort(query: Query, search: Search) -> Search:
    sort_params = _get_sort_parameters(query)
    if sort_params is not None:
        search = search.sort(*sort_params)
    return search


def _classification_to_q(field: str, classification: Classification) -> Match:
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


def _classifications_to_q(query: AdvancedQuery) -> Match:
    if not query.primary_classification:
        return Q()
    q = _classification_to_q('primary_classification',
                             query.primary_classification[0])
    if len(query.primary_classification) > 1:
        for classification in query.primary_classification[1:]:
            q |= _classification_to_q('primary_classification', classification)
    return q


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


def _field_term_to_q(field: str, term: str) -> Q:
    """Generate a query fragment for a query on a specific field."""
    # Searching with TeXisms in non-TeX-tokenized fields leads to
    # spurious results and challenges with highlighting.
    term_sans_tex = _escape(strip_tex(term).lower())
    # These terms have fields for both TeX and English normalization.
    if field in ['title', 'abstract']:
        # Boost the TeX field, since these will be exact matches, and we
        # prefer them to partial matches within TeXisms.
        if is_tex_query(term):
            return Q("match", **{f'{field}.tex': {'query': term, 'boost': 2}})
        q = (
            Q("query_string", fields=[
                field,
                f'{field}_utf8',
                f'{field}__english',
                f'{field}_utf8__english'
              ],
              default_operator='AND',
              analyze_wildcard=True,
              allow_leading_wildcard=False,
              query=term_sans_tex)
        )
        return q

    # These terms have no additional fields.
    elif field in ['comments']:
        return Q("simple_query_string", fields=[field],
                 query=term_sans_tex)
    # These terms require a match_phrase search.
    elif field in ['journal_ref', 'report_num']:
        return Q_('match_phrase', field, term_sans_tex)
    # These terms require a simple match.
    elif field in ['acm_class', 'msc_class', 'doi']:
        return Q_('match', field, term)
    # Search both with and without version.
    elif field == 'paper_id':
        return (
            Q_('match', 'paper_id', term_sans_tex)
            | Q_('match', 'paper_id_v', term_sans_tex)
        )
    elif field in ['orcid', 'author_id']:
        return construct_author_id_query(field, term)
    elif field == 'author':
        return construct_author_query(term_sans_tex)
    return Q_("match", field, term)


def _grouped_terms_to_q(term_pair: tuple) -> Q:
    """Generate a :class:`.Q` from grouped terms."""
    term_a_raw, operator, term_b_raw = term_pair

    if type(term_a_raw) is tuple:
        term_a = _grouped_terms_to_q(term_a_raw)
    else:
        if term_a_raw.field == 'all':
            q_ar = [_field_term_to_q(field, term_a_raw.term)
                    for field in ALL_SEARCH_FIELDS]
            term_a = reduce(ior, q_ar)
        else:
            term_a = _field_term_to_q(term_a_raw.field, term_a_raw.term)

    if type(term_b_raw) is tuple:
        term_b = _grouped_terms_to_q(term_b_raw)
    else:
        if term_b_raw.field == 'all':
            q_ar = [_field_term_to_q(field, term_b_raw.term)
                    for field in ALL_SEARCH_FIELDS]
            term_b = reduce(ior, q_ar)
        else:
            term_b = _field_term_to_q(term_b_raw.field, term_b_raw.term)

    if operator == 'OR':
        return term_a | term_b
    elif operator == 'AND':
        return term_a & term_b
    elif operator == 'NOT':
        return term_a & ~term_b
    else:
        # TODO: Confirm proper exception.
        raise TypeError("Invalid operator for terms")


def _get_operator(obj: Any) -> str:
    if type(obj) is tuple:
        return _get_operator(obj[0])
    return obj.operator     # type: ignore


def _group_terms(query: AdvancedQuery) -> tuple:
    """Group fielded search terms into a set of nested tuples."""
    terms = query.terms[:]
    for operator in ['NOT', 'AND', 'OR']:
        i = 0
        while i < len(terms) - 1:
            if _get_operator(terms[i+1]) == operator:
                terms[i] = (terms[i], operator, terms[i+1])
                terms.pop(i+1)
                i -= 1
            i += 1
    assert len(terms) == 1
    return terms[0]     # type: ignore


def _fielded_terms_to_q(query: AdvancedQuery) -> Match:
    if len(query.terms) == 1:
        term = query.terms[0]

        if term.field == 'all':
            q_ar = [_field_term_to_q(field, term.term)
                    for field in ALL_SEARCH_FIELDS]
            q = reduce(ior, q_ar)
        else:
            q = _field_term_to_q(term.field, term.term)

        return q
    elif len(query.terms) > 1:
        return _grouped_terms_to_q(_group_terms(query))
    return Q('match_all')


def simple(search: Search, query: SimpleQuery) -> Search:
    """Prepare a :class:`.Search` from a :class:`.SimpleQuery`."""
    search = search.filter("term", is_current=True)
    if query.search_field == 'all':
        use = TEX_FIELDS if is_tex_query(query.value) else ALL_SEARCH_FIELDS
        q_ar = [_field_term_to_q(field, query.value)
                for field in use]
        q = reduce(ior, q_ar)
    else:
        q = _field_term_to_q(query.search_field, query.value)
    search = search.query(q)
    search = _apply_sort(query, search)
    return search


def advanced(search: Search, query: AdvancedQuery) -> Search:
    """Prepare a :class:`.Search` from a :class:`.AdvancedQuery`."""
    # Classification and date are treated as filters; this foreshadows the
    # behavior of faceted search.
    if not query.include_older_versions:
        search = search.filter("term", is_current=True)
    q = (
        _fielded_terms_to_q(query)
        & _daterange_to_q(query)
        & _classifications_to_q(query)
    )
    if query.order is None or query.order == 'relevance':
        # Boost the current version heavily when sorting by relevance.
        q = Q('function_score', query=q, boost=5, boost_mode="multiply",
              score_mode="max",
              functions=[
                SF({'weight': 5, 'filter': Q('term', is_current=True)})
              ])
    search = _apply_sort(query, search)
    search = search.query(q)
    return search


def highlight(search: Search) -> Search:
    """Apply hit highlighting to the search, before execution."""
    # Highlight class .search-hit defined in search.sass
    search = search.highlight_options(
        pre_tags=[HIGHLIGHT_TAG_OPEN],
        post_tags=[HIGHLIGHT_TAG_CLOSE]
    )
    search = search.highlight('title', type='plain', number_of_fragments=0)
    search = search.highlight('title.tex', type='plain', number_of_fragments=0)
    search = search.highlight('title_utf8', type='plain',
                              number_of_fragments=0)

    search = search.highlight('comments', number_of_fragments=0)
    # Highlight any field the name of which begins with "author".
    search = search.highlight('author*')
    search = search.highlight('journal_ref', type='plain')
    search = search.highlight('acm_class', number_of_fragments=0)
    search = search.highlight('msc_class', number_of_fragments=0)
    search = search.highlight('doi', type='plain')
    search = search.highlight('report_num', type='plain')

    # Setting number_of_fragments to 0 tells ES to highlight the entire
    # abstract.
    search = search.highlight('abstract', type='plain', number_of_fragments=0)
    search = search.highlight('abstract.tex', type='plain',
                              number_of_fragments=0)
    return search
