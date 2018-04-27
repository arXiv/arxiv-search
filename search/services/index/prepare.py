"""Functions for preparing a :class:`.Search` (prior to execution)."""

from typing import Any, List, Tuple
from functools import reduce, wraps
from operator import ior
import re
from string import punctuation

from elasticsearch_dsl import Search, Q, SF
from elasticsearch_dsl.query import Range, Match, Bool

from arxiv.base import logging

from search.domain import SimpleQuery, Query, AdvancedQuery, Classification
from .util import strip_tex, Q_, HIGHLIGHT_TAG_OPEN, HIGHLIGHT_TAG_CLOSE, \
    is_tex_query, is_literal_query, escape, wildcardEscape, \
    remove_single_characters
from .authors import author_query, author_id_query, orcid_query

logger = logging.getLogger(__name__)


ALL_SEARCH_FIELDS = ['author', 'title', 'abstract', 'comments', 'journal_ref',
                     'acm_class', 'msc_class', 'report_num', 'paper_id', 'doi',
                     'orcid', 'author_id']

TEX_FIELDS = ['title', 'abstract', 'comments']


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


def _classification(field: str, classification: Classification) -> Match:
    """Get a query part for a :class:`.Classification`."""
    query = Q()
    if classification.group:
        field_name = '%s__group__id' % field
        query &= Q('match', **{field_name: classification.group})
    if classification.archive:
        field_name = '%s__archive__id' % field
        query &= Q('match', **{field_name: classification.archive})
    if classification.category:
        field_name = '%s__category__id' % field
        query &= Q('match', **{field_name: classification.category})
    return query


def _classifications(q: AdvancedQuery) -> Match:
    """Get a query part for classifications on an :class:`.AdvancedQuery`."""
    if not q.primary_classification:
        return Q()
    query = _classification('primary_classification',
                            q.primary_classification[0])
    if len(q.primary_classification) > 1:
        for classification in q.primary_classification[1:]:
            query |= _classification('primary_classification', classification)
    return query


def _date_range(q: AdvancedQuery) -> Range:
    """Generate a query part for a date range."""
    if not q.date_range:
        return Q()
    params = {}
    if q.date_range.start_date:
        params["gte"] = q.date_range.start_date.strftime('%Y-%m-%dT%H:%M:%S%z')
    if q.date_range.end_date:
        params["lt"] = q.date_range.end_date.strftime('%Y-%m-%dT%H:%M:%S%z')
    return Q('range', submitted_date=params)


def _query_title(term: str, default_operator: str = 'AND') -> Q:
    if is_tex_query(term):
        return Q("match", **{f'title.tex': {'query': term}})
    fields = ['title.english']
    if is_literal_query(term):
        fields += ['title']
    return Q("query_string", fields=fields, default_operator=default_operator,
             analyze_wildcard=True, allow_leading_wildcard=False,
             auto_generate_phrase_queries=True, query=escape(term))


def _query_abstract(term: str, default_operator: str = 'AND') -> Q:
    fields = ['abstract.english']
    if is_literal_query(term):
        fields += ['abstract']
    return Q("query_string", fields=fields, default_operator=default_operator,
             analyze_wildcard=True, allow_leading_wildcard=False,
             auto_generate_phrase_queries=True, query=escape(term))


def _query_comments(term: str, default_operator: str = 'AND') -> Q:
    return Q("query_string", fields=['comments'],
             default_operator=default_operator, analyze_wildcard=True,
             allow_leading_wildcard=False, auto_generate_phrase_queries=True,
             query=escape(term))


def _tex_query(field: str, term: str, boost: int = 2) -> Q:
    return Q("match", **{f'{field}.tex': {'query': term, 'boost': boost}})


def _query_journal_ref(term: str, boost: int = 1) -> Q:
    return Q_('match_phrase', 'journal_ref', escape(term))


def _query_report_num(term: str, boost: int = 1) -> Q:
    return Q_('match_phrase', 'report_num', escape(term))


def _query_acm_class(term: str) -> Q:
    return Q_('match', 'acm_class', escape(term).upper())


def _query_msc_class(term: str) -> Q:
    return Q_('match', 'msc_class', escape(term))


def _query_doi(term: str) -> Q:
    return Q_('match', 'doi', term)


def _query_paper_id(term: str) -> Q:
    return (Q_('match', 'paper_id', escape(term))
            | Q_('match', 'paper_id_v', escape(term)))


def _literal_chunks(term: str) -> List[Tuple[str, bool]]:
    out = []
    current = ''
    i = 0
    while i < len(term):
        quoted = re.search(r'^"[^"]+"', term[i:])
        if quoted:
            out.append((current, False))
            current = ''
            out.append((quoted.group(0), True))
            i += quoted.end()
        else:
            current += term[i]
            i += 1
    if current:
        out.append((current, False))
    return out


def _query_all_fields(term: str) -> Q:
    """Construct a query against all fields."""
    # We only perform TeX queries on title and abstract.
    if is_tex_query(term):
        return _tex_query('title', term) | _tex_query('abstract', term)

    # Only wildcards in literals should be escaped.
    wildcard_escaped, has_wildcard = wildcardEscape(term)
    query_term = wildcard_escaped if has_wildcard else escape(term)

    # All terms must match in the combined field.
    match_all_fields = Q("query_string", fields=['combined'],
                         default_operator='AND', analyze_wildcard=True,
                         allow_leading_wildcard=False,
                         auto_generate_phrase_queries=True,
                         query=remove_single_characters(query_term.lower()))

    # In addition, all terms must each match in at least one field.
    # TODO: continue implementing disjunct case, so that partials match on
    # individual fields (e.g. ORCID, ACM class, etc).
    queries = [
        author_query(term, operator='OR'),
        _query_title(term, default_operator='or'),
        _query_abstract(term, default_operator='or'),
        _query_comments(term, default_operator='or'),
        orcid_query(term),
        author_id_query(term),
        _query_doi(term),
        _query_journal_ref(term),
        _query_report_num(term),
        _query_acm_class(term),
        _query_msc_class(term),
    ]
    query = match_all_fields & Q("bool", should=queries)
    scores = [SF({'weight': i + 1, 'filter': q}) for i, q in enumerate(queries[::-1])]
    return Q('function_score', query=query, score_mode="sum", functions=scores, boost_mode='multiply')


SEARCH_FIELDS = dict([
    ('author', author_query),
    ('title', _query_title),
    ('abstract', _query_abstract),
    ('comments', _query_comments),
    ('journal_ref', _query_journal_ref),
    ('report_num', _query_report_num),
    ('acm_class', _query_acm_class),
    ('msc_class', _query_msc_class),
    ('doi', _query_doi),
    ('paper_id', _query_paper_id),
    ('orcid', orcid_query),
    ('author_id', author_id_query),
    ('all', _query_all_fields)
])


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
        return SEARCH_FIELDS[term.field](term.term)
    elif len(query.terms) > 1:
        return _grouped_terms_to_q(_group_terms(query))
    return Q('match_all')


def simple(search: Search, query: SimpleQuery) -> Search:
    """Prepare a :class:`.Search` from a :class:`.SimpleQuery`."""
    search = search.filter("term", is_current=True)
    q = SEARCH_FIELDS[query.search_field](query.value)
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
        & _date_range(query)
        & _classifications(query)
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
    # search = search.highlight('title', type='plain', number_of_fragments=0)
    search = search.highlight('title.english', type='plain', number_of_fragments=0)
    search = search.highlight('title.tex', type='plain', number_of_fragments=0)
    # search = search.highlight('title', type='plain',
    #                           number_of_fragments=0)

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
    search = search.highlight('abstract.english', type='plain',
                               number_of_fragments=0)
    return search
