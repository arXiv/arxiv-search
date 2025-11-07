"""Classic API Query object."""

__all__ = ["ClassicAPIQuery", "ClassicSearchResponseData", "adapt_query"]

from search.domain.classic_api.classic_query import (
    ClassicAPIQuery,
    ClassicSearchResponseData,
)
from search.domain.classic_api.classic_search_query import (
    adapt_query,
)
