"""Translate classic API `Phrase` objects to Elasticsearch DSL."""

from typing import Dict, Callable

from elasticsearch_dsl import Q, Search

from search.domain import (
    ClassicAPIQuery,
    Phrase,
    Term,
    SortOrder,
    Field,
    Operator,
)
from search.services.index.prepare import (
    SEARCH_FIELDS,
    query_any_subject_exact_raw,
)


def classic_search(search: Search, query: ClassicAPIQuery) -> Search:
    """
    Prepare a :class:`.Search` from a :class:`.ClassicAPIQuery`.

    Parameters
    ----------
    search : :class:`.Search`
        An Elasticsearch search in preparation.
    query : :class:`.ClassicAPIQuery`
        An query originating from the Classic API.

    Returns
    -------
    :class:`.Search`
        The passed ES search object, updated with specific query parameters
        that implement the advanced query.

    """
    # Initialize query.
    if query.phrase:
        dsl_query = _phrase_to_query(query.phrase)
    else:
        dsl_query = Q()

    # Filter id_list if necessary.
    if query.id_list:
        # Separate versioned and unversioned papers.
        paper_ids = [id for id in query.id_list if "v" not in id]
        paper_ids_vs = [id for id in query.id_list if "v" in id]

        # Filter by most recent unversioned paper or any versioned paper.
        id_query = (
            Q("terms", paper_id=paper_ids) & Q("term", is_current=True)
        ) | Q("terms", paper_id_v=paper_ids_vs)

        search = search.filter(id_query).sort(
            f"-{query.sort_by}"
            if query.sort_order == SortOrder.descending
            else f"{query.sort_by}"
        )
    else:
        # If no id_list, only display current results.
        search = search.filter("term", is_current=True)

    return search.query(dsl_query)


def _phrase_to_query(phrase: Phrase) -> Q:
    """Parses a Phrase of a Classic API request into an ES Q object."""
    # mypy doesn't yet handle recursive type annotations, so ignored types
    # base case - simple term query automatically handled by delegation.
    if isinstance(phrase[0], Field) and len(phrase) == 2:
        return _term_to_query(phrase)  # type: ignore

    # Parse Phrase object an build Q.
    q = Q()
    current_operator: Operator = Operator.AND

    for token in phrase:
        if isinstance(token, Operator):
            current_operator = token
        elif isinstance(token, tuple):
            phrase_q: Q = Q()
            if isinstance(token[0], Operator) or len(token) == 3:
                phrase_q = _phrase_to_query(token)  # type: ignore
            elif len(token) == 2:
                phrase_q = _term_to_query(token)  # type: ignore
            else:
                raise ValueError(f"invalid phrase component: {token}")

            if current_operator is Operator.AND:
                q &= phrase_q
            elif current_operator is Operator.OR:
                q |= phrase_q
            elif current_operator is Operator.ANDNOT:
                q &= ~phrase_q  # pylint: disable=invalid-unary-operand-type

    return q


def _term_to_query(term: Term) -> Q:
    """
    Parses a fielded term using transfromations from the current API.

    See Also
    --------
    :module:`.api`

    """
    field, val = term

    FIELD_TERM_MAPPING: Dict[Field, Callable[[str], Q]] = {
        Field.Author: SEARCH_FIELDS["author"],
        Field.Comment: SEARCH_FIELDS["comments"],
        Field.Identifier: SEARCH_FIELDS["paper_id"],
        Field.JournalReference: SEARCH_FIELDS["journal_ref"],
        Field.ReportNumber: SEARCH_FIELDS["report_num"],
        # Expects to match on primary or secondary category.
        Field.SubjectCategory: query_any_subject_exact_raw,
        Field.Title: SEARCH_FIELDS["title"],
        Field.All: SEARCH_FIELDS["all"],
    }

    return FIELD_TERM_MAPPING[field](val)
