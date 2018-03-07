"""Represents fielded search terms, with multiple operators."""

from .base import DateRange, Query, ClassificationList

from dataclasses import dataclass, field
from typing import NamedTuple

class FieldedSearchTerm(NamedTuple):
    """Represents a fielded search term."""

    operator: str
    field: str
    term: str

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return f'{self.operator} {self.field}={self.term}'


class FieldedSearchList(list):
    """Represents a list of fielded search terms."""

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return '; '.join([str(item) for item in self])

@dataclass
class AdvancedQuery(Query):
    """
    Represents an advanced query.

    An advanced query contains fielded search terms and boolean operators.
    """

    date_range: DateRange
    primary_classification: ClassificationList
    terms: FieldedSearchList = field(default_factory=FieldedSearchList)
