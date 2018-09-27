"""API-specific domain classes."""

from .base import DateRange, Query, ClassificationList, List
from .advanced import FieldedSearchList, FieldedSearchTerm

from dataclasses import dataclass, field
from typing import NamedTuple, Optional


def get_default_extra_fields() -> List[str]:
    return ['title']


def get_required_fields() -> List[str]:
    return ['paper_id', 'paper_id_v', 'version']


@dataclass
class APIQuery(Query):
    """
    Represents an API query.

    Similar to an advanced query.
    """
    date_range: Optional[DateRange] = None
    primary_classification: ClassificationList = field(
        default_factory=ClassificationList
    )
    terms: FieldedSearchList = field(default_factory=FieldedSearchList)

    include_fields: List[str] = field(default_factory=get_default_extra_fields)

    def __post_init__(self) -> None:
        self.include_fields = list(
            set(get_required_fields() + self.include_fields)
        )
        print(self.include_fields)
