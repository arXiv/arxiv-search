"""
Functions for preparing a :class:`.Search` (prior to execution).

The primary public object is ``SEARCH_FIELDS``, which maps :class:`.Query`
fields to query-building functions in the module.

See :func:`._query_all_fields` for information on how results are scored.
"""

from typing import Any, List, Tuple, Callable, Dict, Optional
from functools import reduce, wraps
from operator import ior, iand
import re
from datetime import datetime
from string import punctuation

from elasticsearch_dsl import Search, Q, SF

from arxiv.base import logging

from search.domain import SimpleQuery, Query, AdvancedQuery, Classification, \
    ClassificationList
from .util import strip_tex, Q_, is_tex_query, is_literal_query, escape, \
    wildcard_escape, remove_single_characters, has_wildcard, is_old_papernum, \
    parse_date, parse_date_partial

from .highlighting import HIGHLIGHT_TAG_OPEN, HIGHLIGHT_TAG_CLOSE
from .authors import author_query, author_id_query, orcid_query

logger = logging.getLogger(__name__)

START_YEAR = 1991
END_YEAR = datetime.now().year


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
             allow_leading_wildcard=False, query=escape(term),
             _name="abstract")


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
    value, wildcard = wildcard_escape(term)
    if wildcard:
        return Q('wildcard', doi={'value': term.lower()})
    return Q('match', doi={'query': term, 'operator': operator})


def _query_announcement_date(term: str) -> Optional[Q]:
    """
    Query against the original announcement date.

    If ``term`` looks like a year, will use a range search for all months in
    that year. If it looks like a year-month combo, will match.
    """
    year_match = re.match(r'^([0-9]{4})$', term)    # Looks like a year.
    if year_match and END_YEAR >= int(year_match.group(1)) >= START_YEAR:
        _range = {'gte': f'{term}-01', 'lte': f'{term}-12'}
        return Q('range', announced_date_first=_range)

    month_match = re.match(r'^([0-9]{4})-([0-9]{2})$', term)    # yyyy-MM.
    if month_match and END_YEAR >= int(month_match.group(1)) >= START_YEAR:
        return Q('match', announced_date_first=term)
    return None


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


def _query_secondary(term: str, operator: str = 'and') -> Q:
    if operator == 'or':
        q = reduce(ior, [(
            Q("match", **{"secondary_classification__category__id": {"query": part, "operator": operator}})
            | Q("wildcard", **{"secondary_classification.category.name": f"*{part}*"})
            | Q("match", **{"secondary_classification__archive__id": {"query": part, "operator": operator}})
            | Q("wildcard", **{"secondary_classification.archive.name": f"*{part}*"})
        ) for part in term.split()])
    else:
        q = (
            Q("match", **{"secondary_classification__category__id": {"query": term, "operator": operator}})
            | Q("match", **{"secondary_classification__category__name": {"query": term, "operator": operator}})
            | Q("match", **{"secondary_classification__archive__id": {"query": term, "operator": operator}})
            | Q("match", **{"secondary_classification__archive__name": {"query": term, "operator": operator}})
        )
    return Q("nested", path="secondary_classification", query=q)


def _query_paper_id(term: str, operator: str = 'and') -> Q:
    operator = operator.lower()
    logger.debug(f'query paper ID with: {term}')
    q = (Q_('match', 'paper_id', escape(term), operator=operator)
         | Q_('match', 'paper_id_v', escape(term), operator=operator))
    if is_old_papernum(term):
        q |= Q('wildcard', paper_id=f'*/{term}')
    return q


def _license_query(term: str, operator: str = 'and') -> Q:
    """Search by license, using its URI (exact)."""
    return Q('term', **{'license__uri': term})


def _query_combined(term: str) -> Q:
    # Only wildcards in literals should be escaped.
    wildcard_escaped, has_wildcard = wildcard_escape(term)
    query_term = (wildcard_escaped if has_wildcard else escape(term)).lower()

    # All terms must match in the combined field.
    return Q("query_string", fields=['combined'], default_operator='AND',
             allow_leading_wildcard=False, query=query_term)


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

    match_all_fields = _query_combined(term)

    # We include matches of any term in any field, so that we can highlight
    # and score appropriately.
    queries = [
        _query_paper_id(term, operator='or'),
        author_query(term, operator='or'),
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
        _query_primary(term, operator='or'),
        _query_secondary(term, operator='or')
    ]

    # If the whole query matches on a specific field, we should consider that
    # responsive even if the query on the combined field does not respond.
    match_individual_field = reduce(ior, [
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
    ])


    # It is possible that the query includes a date-related term, which we
    # interpret as an announcement date of v1 of the paper. We currently
    # support both "standard" `yyyy` or `yyyy-MM`` formats as well as a
    # legacy format ``yyMM``.
    #
    # The general strategy here is to first attempt to match a date fragment
    # using one the formats above, and split the query so that we can handle
    # the date fragment and the remainder of the query separately. If we find
    # something that looks like a date fragment, we perform the all-fields
    # search on the remainder and use the fragment to build queries against the
    # announcement-date of the original paper version.
    date_fragment: Optional[str] = None
    remainder: Optional[str] = None
    try:
        date_fragment, remainder = parse_date(term)
    except ValueError:
        pass

    if date_fragment:
        logger.debug('date: %s; remainder: %s', date_fragment, remainder)
        match_date: Optional[Q] = None
        match_date_partial: Optional[Q] = None
        match_date_announced: Optional[Q] = None
        match_dates: List[Q] = []
        logger.debug('date_fragment: %s', date_fragment)

        # Try to query using legacy yyMM date partial format.
        date_partial = parse_date_partial(date_fragment)
        logger.debug('date_partial: %s', date_partial)
        if date_partial is not None:
            match_date_partial = Q("term", announced_date_first=date_partial)
            match_dates.append(match_date_partial)

        # Also try using yyyy-MM and yyyy formats.
        match_date_announced = _query_announcement_date(date_fragment)
        if match_date_announced:
            match_dates.append(match_date_announced)

        # Build the composite announcement date query here, using the
        # sub-queries based on "standard" and legay date formats.
        if match_dates:
            # The only way to know in the end whether the query matched on
            # the announcement date is to wrap this in a top-level query and
            # give it a ``_name``. This causes the ``_name`` to show up
            # in the ``.meta.matched_queries`` property on the search result.
            match_date = Q("bool", should=match_dates, minimum_should_match=1,
                           _name="announced_date_first")
            logger.debug('match date: %s', match_date)
            queries.insert(0, match_date)

        # Now join the announcement date query with the all-fields queries.
        if match_date is not None:
            if remainder:
                match_remainder = _query_combined(remainder)
                match_all_fields |= (match_remainder & match_date)

                match_individual_sans_date = reduce(ior, [
                    _query_paper_id(remainder, operator='AND'),
                    author_query(remainder, operator='AND'),
                    _query_title(remainder, default_operator='and'),
                    _query_abstract(remainder, default_operator='and'),
                    _query_comments(remainder, default_operator='and'),
                    orcid_query(remainder, operator='and'),
                    author_id_query(remainder, operator='and'),
                    _query_doi(remainder, operator='and'),
                    _query_journal_ref(remainder, operator='and'),
                    _query_report_num(remainder, operator='and'),
                    _query_acm_class(remainder, operator='and'),
                    _query_msc_class(remainder, operator='and'),
                    _query_primary(remainder, operator='and')
                ])
                match_individual_field = Q('bool', should=[
                        match_individual_field,
                        match_individual_sans_date & match_date
                    ], minimum_should_match=1)
            else:
                match_all_fields = Q('bool',
                                     should=[match_all_fields, match_date],
                                     minimum_should_match=1)

    query = (match_all_fields | match_individual_field)
    query &= Q("bool", should=queries)  # Partial matches across fields.
    scores = [SF({'weight': i + 1, 'filter': q})
              for i, q in enumerate(queries[::-1])]
    return Q('function_score', query=query, score_mode="sum", functions=scores,
             boost_mode='multiply')


def limit_by_classification(classifications: ClassificationList) -> Q:
    """Generate a :class:`Q` to limit a query by by classification."""
    def _to_q(classification: Classification) -> Q:
        _qs = []
        if classification.group:
            _qs.append(
                Q("match", **{
                    "primary_classification__group__id": {
                        "query": classification.group
                    }
                })
            )
        if classification.archive:
            _qs.append(
                Q("match", **{
                    "primary_classification__archive__id": {
                        "query": classification.archive
                    }
                })
            )
        if classification.category:
            _qs.append(
                Q("match", **{
                    "primary_classification__category__id": {
                        "query": classification.category
                    }
                })
            )
        return reduce(iand, _qs)

    return reduce(ior, [_to_q(clsn) for clsn in classifications])


SEARCH_FIELDS: Dict[str, Callable[[str], Q]] = dict([
    ('author', author_query),
    ('title', _query_title),
    ('abstract', _query_abstract),
    ('comments', _query_comments),
    ('journal_ref', _query_journal_ref),
    ('report_num', _query_report_num),
    ('acm_class', _query_acm_class),
    ('msc_class', _query_msc_class),
    ('cross_list_category', _query_secondary),
    ('doi', _query_doi),
    ('paper_id', _query_paper_id),
    ('orcid', orcid_query),
    ('author_id', author_id_query),
    ('license', _license_query),
    ('all', _query_all_fields)
])
