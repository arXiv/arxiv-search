"""Query builder for classic API."""
from typing import Dict, Callable

from elasticsearch_dsl import Q

from search.domain import Phrase, Term, Field, Operator
from search.services.index.prepare import (
    SEARCH_FIELDS,
    query_any_subject_exact_raw,
)

FIELD_TERM_MAPPING: Dict[Field, Callable[[str], Q]] = {
    Field.Abstract: SEARCH_FIELDS["abstract"],
    Field.Author: SEARCH_FIELDS["author"],
    Field.Comment: SEARCH_FIELDS["comments"],
    Field.Identifier: SEARCH_FIELDS["paper_id"],
    Field.JournalReference: SEARCH_FIELDS["journal_ref"],
    Field.ReportNumber: SEARCH_FIELDS["report_num"],
    # Expects to match on primary or secondary category.
    Field.SubjectCategory: query_any_subject_exact_raw,
    Field.SubmittedDate : SEARCH_FIELDS["submittedDate"],
    Field.Title: SEARCH_FIELDS["title"],
    Field.All: SEARCH_FIELDS["all"],
}


def term_to_query(term: Term) -> Q:
    """
    Parses a fielded term using transfromations from the current API.

    See Also
    --------
    :module:`.api`
    """

    return Q() if term.is_empty else FIELD_TERM_MAPPING[term.field](term.value)


def query_builder(phrase: Phrase) -> Q:
    """Parses a Phrase of a Classic API request into an ES Q object."""
    if isinstance(phrase, Term):
        return term_to_query(phrase)
    elif len(phrase) == 2:
        # This is unary ANDNOT which is just NOT
        return ~term_to_query(phrase[1])
    elif len(phrase) == 3:
        binary_op, exp1, exp2 = phrase[:3]  # type:ignore
        q1 = query_builder(exp1)
        q2 = query_builder(exp2)
        if binary_op is Operator.AND:
            return q1 & q2
        elif binary_op is Operator.OR:
            return q1 | q2
        elif binary_op is Operator.ANDNOT:
            return q1 & (~q2)
    else:
        # Error?
        return Q()
