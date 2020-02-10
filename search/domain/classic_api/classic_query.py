"""Classic API Query object."""

from typing import Optional, List
from dataclasses import dataclass, field

from search.domain.documents import DocumentSet
from search.domain.base import SortBy, SortOrder, Query, Phrase
from search.domain.classic_api.query_parser import parse_classic_query


@dataclass
class ClassicAPIQuery(Query):
    """Query supported by the classic arXiv API."""

    SortBy = SortBy
    SortOrder = SortOrder

    search_query: Optional[str] = field(default=None)
    phrase: Optional[Phrase] = field(default=None)
    id_list: Optional[List[str]] = field(default=None)
    size: int = field(default=10)
    sort_by: SortBy = field(default=SortBy.relevance)
    sort_order: SortOrder = field(default=SortOrder.descending)

    def __post_init__(self) -> None:
        """Ensure that either a phrase or id_list is set."""
        if self.search_query is not None:
            self.phrase = parse_classic_query(self.search_query)

        if self.phrase is None and self.id_list is None:
            raise ValueError(
                "ClassicAPIQuery requires either a phrase, id_list, or both"
            )

    def to_query_string(self) -> str:
        """Returns a string representation of the API query."""
        return (
            f"search_query={self.search_query or ''}&"
            f"id_list={','.join(self.id_list) if self.id_list else ''}&"
            f"start={self.page_start}&"
            f"max_results={self.size}"
        )


@dataclass
class ClassicSearchResponseData:
    results: DocumentSet = None
    query: ClassicAPIQuery = None
