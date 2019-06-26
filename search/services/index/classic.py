
"""
Module for translating classic API `Phrase` objects to the
Elasticsearch DSL and retrieving results.
"""

from elasticsearch_dsl import Q, Search
from elasticsearch_dsl.query import QueryString

from ...domain import ClassicAPIQuery, Phrase, Term, Expression, Field, Operator

def classic_search(search: Search, query: ClassicAPIQuery) -> Search:
    """
    Performs a classic API search query.
    """
    dsl_query = _query_to_dsl(query.phrase)

    return search.query(dsl_query) 


def _query_to_dsl(phrase: Phrase) -> Q:
    """
    Parses a ClassicAPIQuery into the Elasticsearch DSL.
    """
    query_string = _phrase_to_query_string(phrase)
    return Q(QueryString(query=query_string))


def _phrase_to_query_string(phrase: Phrase) -> str:
    """
    Parses a ClassicAPIQuery into a query string using the 
    `syntax of the Elasticsearch DSL`_

    _syntax of the Elasticsearch DSL: https://www.elastic.co/guide/en/elasticsearch/reference/6.3/query-dsl-query-string-query.html
    """

    qs_parts = []

    if isinstance(phrase[0], Field) and len(phrase) == 2:
        return _term_to_query_string(phrase)

    for token in phrase:
        if isinstance(token, Operator):
            qs_parts.append(_operator_to_query_string(token))
        elif isinstance(token, tuple):
            if isinstance(token[0], Operator) or len(token) == 3:
                qs_parts.append('('+_phrase_to_query_string(token)+')')
            elif len(token) == 2:
                qs_parts.append(_term_to_query_string(token))
            else:
                raise ValueError(f"invalid phrase component: {token}")

    return ' '.join(qs_parts)

def _operator_to_query_string(op: Operator) -> str:
    OPERATOR_DSL_MAPPING = {
        Operator.AND : 'AND',
        Operator.OR : 'OR',
        Operator.ANDNOT : 'NOT'
    }

    return OPERATOR_DSL_MAPPING[op]

def _term_to_query_string(term: Term) -> str:
    """
    Parses a term into a query
    """
    field, val = term

    FIELD_DSL_MAPPING = {
        Field.Author : 'authors',
        Field.Comment : 'comments',
        Field.Identifier : 'paper_id', # TODO: edge case of versioned data
        Field.JournalReference : 'journal_ref',
        Field.ReportNumber : 'report_num',
        Field.SubjectCategory : 'abs_categories', # TODO: unsure of where classifications are unified
        Field.Title : 'title'
    }

    return f'{FIELD_DSL_MAPPING[field]}:{val}'




