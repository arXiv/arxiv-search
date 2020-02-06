"""Represents fielded search terms, with multiple operators."""

from typing import Optional
from dataclasses import dataclass, field

from search.domain.base import DateRange, Query, ClassificationList


@dataclass
class FieldedSearchTerm:
    """Represents a fielded search term."""

    operator: str
    field: str
    term: str

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return f"{self.operator} {self.field}={self.term}"


class FieldedSearchList(list):
    """Represents a list of fielded search terms."""

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return "; ".join([str(item) for item in self])


@dataclass
class AdvancedQuery(Query):
    """
    Represents an advanced query.

    An advanced query contains fielded search terms and boolean operators.
    """

    SUPPORTED_FIELDS = [
        ("title", "Title"),
        ("author", "Author(s)"),
        ("abstract", "Abstract"),
        ("comments", "Comments"),
        ("journal_ref", "Journal reference"),
        ("acm_class", "ACM classification"),
        ("msc_class", "MSC classification"),
        ("report_num", "Report number"),
        ("paper_id", "arXiv identifier"),
        ("cross_list_category", "Cross-list category"),
        ("doi", "DOI"),
        ("orcid", "ORCID"),
        ("author_id", "arXiv author ID"),
        ("all", "All fields"),
    ]

    date_range: Optional[DateRange] = None

    classification: ClassificationList = field(
        default_factory=ClassificationList
    )
    """Classification(s) by which to limit results."""

    include_cross_list: bool = field(default=True)
    """If True, secondaries are considered when limiting by classification."""

    terms: FieldedSearchList = field(default_factory=FieldedSearchList)
