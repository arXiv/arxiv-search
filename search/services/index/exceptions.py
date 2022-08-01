"""Exceptions raised by the search index service."""

__all__ = (
    "MappingError",
    "IndexConnectionError",
    "IndexingError",
    "QueryError",
    "DocumentNotFound",
    "OutsideAllowedRange",
)


class MappingError(ValueError):
    """There was a problem with the search document mapping."""


class IndexConnectionError(IOError):
    """There was a problem connecting to the search index."""


class IndexingError(IOError):
    """There was a problem adding a document to the index."""


class QueryError(ValueError):
    """
    Elasticsearch could not handle the query.

    This is likely due either to a programming error that resulted in a bad
    index, or to a malformed query.
    """


class DocumentNotFound(RuntimeError):
    """Could not find a requested document in the search index."""


class OutsideAllowedRange(RuntimeError):
    """A page outside of the allowed range has been requested."""
