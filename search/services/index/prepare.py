"""
Functions for preparing a :class:`.Search` (prior to execution).

The primary public object is ``SEARCH_FIELDS``, which maps :class:`.Query`
fields to query-building functions in the module.

See :func:`._query_all_fields` for information on how results are scored.
"""

from typing import Any, List, Tuple, Callable, Dict
from functools import reduce, wraps
from operator import ior, iand
import re
from string import punctuation

from elasticsearch_dsl import Search, Q, SF

from arxiv.base import logging

from search.domain import SimpleQuery, Query, AdvancedQuery, Classification
from .util import strip_tex, Q_, is_tex_query, is_literal_query, escape, \
    wildcardEscape, remove_single_characters, has_wildcard, match_date_partial
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
             allow_leading_wildcard=False, query=escape(term))


def _query_abstract(term: str, default_operator: str = 'AND') -> Q:
    fields = ["abstract.english"]
    if is_literal_query(term):
        fields += ["abstract"]
    return Q("query_string", fields=fields, default_operator=default_operator,
             allow_leading_wildcard=False, query=escape(term))


def _query_comments(term: str, default_operator: str = 'AND') -> Q:
    return Q("query_string", fields=["comments"],
             default_operator=default_operator,
             allow_leading_wildcard=False, query=escape(term))


def _tex_query(field: str, term: str, operator: str = 'and') -> Q:
    return Q("match",
             **{f'{field}.tex': {'query': term, 'operator': operator}})


def _query_journal_ref(term: str, boost: int = 1, operator: str = 'and') -> Q:
    return Q("query_string", fields=["journal_ref"], default_operator=operator,
             allow_leading_wildcard=False, query=escape(term))


def _query_report_num(term: str, boost: int = 1, operator: str = 'and') -> Q:
    return Q("query_string", fields=["report_num"], default_operator=operator,
             allow_leading_wildcard=False, query=escape(term))


def _query_acm_class(term: str, operator: str = 'and') -> Q:
    if has_wildcard(term):
        return Q("wildcard", acm_class=term)
    return Q("match", acm_class={"query": term, "operator": operator})


def _query_msc_class(term: str, operator: str = 'and') -> Q:
    if has_wildcard(term):
        return Q("wildcard", msc_class=term)
    return Q("match", msc_class={"query": term, "operator": operator})


def _query_doi(term: str, operator: str = 'and') -> Q:
    value, wildcard = wildcardEscape(term)
    if wildcard:
        return Q('wildcard', doi={'value': term.lower()})
    return Q('match', doi={'query': term, 'operator': operator})


def _query_primary(term: str, operator: str = 'and') -> Q:
    # In the 'or' case, we're basically just looking for hit highlighting
    # after a match on the combined field. Since primary classification fields
    # are keyword fields, they won't match the same way as the combined field
    # (text). So we have to be a bit fuzzy here to get the highlight.
    # TODO: in a future version, we should consider changes to the mappings
    # to make this more straightforward.
    if operator == 'or':
        return reduce(ior, [(
            Q("match", **{"primary_classification__category__id": {"query": part, "operator": operator}})
            | Q("wildcard", **{"primary_classification.category.name": f"*{part}*"})
            | Q("match", **{"primary_classification__archive__id": {"query": part, "operator": operator}})
            | Q("wildcard", **{"primary_classification.archive.name": f"*{part}*"})
        ) for part in term.split()])
    return (
        Q("match", **{"primary_classification__category__id": {"query": term, "operator": operator}})
        | Q("match", **{"primary_classification__category__name": {"query": term, "operator": operator}})
        | Q("match", **{"primary_classification__archive__id": {"query": term, "operator": operator}})
        | Q("match", **{"primary_classification__archive__name": {"query": term, "operator": operator}})
    )


def _query_paper_id(term: str, operator: str = 'and') -> Q:
    operator = operator.lower()
    logger.debug(f'query paper ID with: {term}')
    try:
        date_partial, rmd = match_date_partial(term)
        logger.debug(f'found date partial: {date_partial}')
    except ValueError:
        date_partial = None
        rmd = None
    logger.debug(f'partial: {date_partial}; rem: {rmd}; op: {operator}')

    if date_partial:
        q = Q("term", announced_date_first=date_partial)
        if operator == 'or' and rmd:
            q |= (Q_('match', 'paper_id', escape(rmd), operator=operator)
                  | Q_('match', 'paper_id_v', escape(rmd), operator=operator))
        elif operator == 'and' and rmd:
            q &= (Q_('match', 'paper_id', escape(rmd), operator=operator)
                  | Q_('match', 'paper_id_v', escape(rmd), operator=operator))
    else:
        q = (Q_('match', 'paper_id', escape(term), operator=operator)
             | Q_('match', 'paper_id_v', escape(term), operator=operator))
    return q


def _query_all_fields(term: str) -> Q:
    """
    Construct a query against all fields.

    The heart of the query is a `query_string` search against a "combined"
    field, which contains tokens from all of the searchable metadata fields on
    each paper. All tokens in the query must match in that combined field.

    The reason that we do it this way, instead of combining queries across
    multiple fields, is that:

    - To query in a term-centric way across fields (e.g. the `cross_fields`
      query type for `query_string` or `multi_match` searches), all of those
      fields must have the same analyzer. It's a drag to constrain analyzer
      choice on individual fields, so this way we can do what we want with
      individual fields but also support a consistent all-fields search that
      behaves the way that users expect.
    - Performing a disjunct search across all fields can't guarantee that all
      terms match (if we use the disjunct operator within each field), and
      can't handle queries that span fieds (if we use the conjunect operator
      within each field).

    In addition to the combined query, we also perform dijunct queries across
    individual fields to generate field-specific hits, and to provide control
    over scoring.

    Weights are applied using :class:`.SF` (score functions). In the current
    implementation, fields are given monotonically decreasing weights in the
    order applied below. More complex score functions may be introduced, and
    that should happen here.

    Parameters
    ----------
    term : str
        A query string.

    Returns
    -------
    :class:`.Q`
        A search-ready query part, including score functions.

    """
    # We only perform TeX queries on title and abstract.
    if is_tex_query(term):
        return _tex_query('title', term) | _tex_query('abstract', term)

    # Only wildcards in literals should be escaped.
    wildcard_escaped, has_wildcard = wildcardEscape(term)
    query_term = wildcard_escaped if has_wildcard else escape(term)

    # All terms must match in the combined field.
    _query = query_term.lower()
    match_all_fields = Q("query_string", fields=['combined'],
                         default_operator='AND',
                         allow_leading_wildcard=False,
                         query=escape(_query))

    # We include matches of any term in any field, so that we can highlight
    # and score appropriately.
    queries = [
        _query_paper_id(term, operator='or'),
        author_query(term, operator='OR'),
        _query_title(term, default_operator='or'),
        _query_abstract(term, default_operator='or'),
        _query_comments(term, default_operator='or'),
        orcid_query(term, operator='or'),
        author_id_query(term, operator='or'),
        _query_doi(term, operator='or'),
        _query_journal_ref(term, operator='or'),
        _query_report_num(term, operator='or'),
        _query_acm_class(term, operator='or'),
        _query_msc_class(term, operator='or'),
        _query_primary(term, operator='or')
    ]
    conj_queries = [
        _query_paper_id(term, operator='AND'),
        author_query(term, operator='AND'),
        _query_title(term, default_operator='and'),
        _query_abstract(term, default_operator='and'),
        _query_comments(term, default_operator='and'),
        orcid_query(term, operator='and'),
        author_id_query(term, operator='and'),
        _query_doi(term, operator='and'),
        _query_journal_ref(term, operator='and'),
        _query_report_num(term, operator='and'),
        _query_acm_class(term, operator='and'),
        _query_msc_class(term, operator='and'),
        _query_primary(term, operator='and')
    ]
    query = (match_all_fields)# | reduce(ior, conj_queries))
    query &= Q("bool", should=queries)  # Partial matches across fields.
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
