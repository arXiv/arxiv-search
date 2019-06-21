
"""
Module for translating classic API `Phrase` objects to the
Elasticsearch DSL and retrieving results.
"""

from ...domain import ClassicAPIQuery

from elasticsearch_dsl import Q, Search

def classic_search(search: Search, query: ClassicAPIQuery) -> Search:
    pass

def _query_to_dsl(query: ClassicAPIQuery) -> Q:
    """
    Parses a ClassicAPIQuery into the Elasticsearch DSL.
    """

    phrase = query.phrase