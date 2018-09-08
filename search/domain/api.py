"""API-specific domain classes."""

from .base import DateRange, Query, ClassificationList
from .advanced import FieldedSearchList, FieldedSearchTerm

from dataclasses import dataclass, field
from typing import NamedTuple, Optional


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
