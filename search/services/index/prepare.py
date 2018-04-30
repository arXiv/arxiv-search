"""
Functions for preparing a :class:`.Search` (prior to execution).

The primary public object is ``SEARCH_FIELDS``, which maps :class:`.Query`
fields to query-building functions in the module.
"""

from typing import Any, List, Tuple, Callable, Dict
from functools import reduce, wraps
from operator import ior
import re
from string import punctuation

from elasticsearch_dsl import Search, Q, SF

from arxiv.base import logging

from search.domain import SimpleQuery, Query, AdvancedQuery, Classification
from .util import strip_tex, Q_, is_tex_query, is_literal_query, escape, \
    wildcardEscape, remove_single_characters
from .highlighting import HIGHLIGHT_TAG_OPEN, HIGHLIGHT_TAG_CLOSE
from .authors import author_query, author_id_query, orcid_query

logger = logging.getLogger(__name__)


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
    scores = [SF({'weight': i + 1, 'filter': q})
              for i, q in enumerate(queries[::-1])]
    return Q('function_score', query=query, score_mode="sum", functions=scores,
             boost_mode='multiply')


SEARCH_FIELDS: Dict[str, Callable[[str], Q]] = dict([
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
