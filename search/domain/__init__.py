"""
Domain classes for search service.

The domain provides a description of the main data objects used in module APIs.
Specifically, the :mod:`search.controllers`, :mod:`search.services`, and
:mod:`search.process` modules should use the domain as their primary
"language". This is intended to make static checking easier and enhance overall
intelligibility of the codebase.
"""

__all__ = [
    # base
    "DocMeta",
    "Fulltext",
    "DateRange",
    "Classification",
    "ClassificationList",
    "Operator",
    "Field",
    "Term",
    "Phrase",
    "SortBy",
    "SortOrder",
    "Query",
    "SimpleQuery",
    # advanced
    "FieldedSearchTerm",
    "FieldedSearchList",
    "AdvancedQuery",
    # api
    "APIQuery",
    # classic api
    "ClassicAPIQuery",
    "ClassicSearchResponseData",
    # documenhts
    "Error",
    "Document",
    "DocumentSet",
    "document_set_from_documents",
]

# pylint: disable=wildcard-import
from search.domain.base import (
    DocMeta,
    Fulltext,
    DateRange,
    Classification,
    ClassificationList,
    Operator,
    Field,
    Term,
    Phrase,
    SortBy,
    SortOrder,
    Query,
    SimpleQuery,
)
from search.domain.advanced import (
    FieldedSearchTerm,
    FieldedSearchList,
    AdvancedQuery,
)
from search.domain.api import APIQuery
from search.domain.classic_api import (
    ClassicAPIQuery,
    ClassicSearchResponseData,
)
from search.domain.documents import (
    Error,
    Document,
    DocumentSet,
    document_set_from_documents,
)
