"""Base domain classes for search service."""

from enum import Enum
from datetime import datetime
from typing import Any, Optional, List, Dict, Union, Tuple
from dataclasses import dataclass, field, asdict as _asdict

from mypy_extensions import TypedDict

from search import consts


# FIXME: Return type.
def asdict(obj: Any) -> Dict[Any, Any]:
    """Coerce a dataclass object to a dict."""
    return {key: value for key, value in _asdict(obj).items()}


@dataclass
class DocMeta:
    """Metadata for an arXiv paper, retrieved from the core repository."""

    paper_id: str = field(default_factory=str)
    abstract: str = field(default_factory=str)
    abstract_utf8: str = field(default_factory=str)
    authors_parsed: List[Dict] = field(default_factory=list)
    authors_utf8: str = field(default_factory=str)
    author_owners: List[Dict] = field(default_factory=list)
    authors: str = field(default_factory=str)
    submitted_date: str = field(default_factory=str)
    submitted_date_all: List[str] = field(default_factory=list)
    modified_date: str = field(default_factory=str)
    updated_date: str = field(default_factory=str)
    announced_date_first: str = field(default_factory=str)
    is_current: bool = field(default=True)
    is_withdrawn: bool = field(default=False)
    license: Dict[str, str] = field(default_factory=dict)
    primary_classification: Dict[str, str] = field(default_factory=dict)
    secondary_classification: List[Dict[str, str]] = field(
        default_factory=list
    )
    title: str = field(default_factory=str)
    title_utf8: str = field(default_factory=str)
    source: Dict[str, Any] = field(default_factory=dict)
    version: int = field(default=1)
    submitter: Dict[str, str] = field(default_factory=dict)
    report_num: str = field(default_factory=str)
    proxy: bool = field(default=False)
    msc_class: str = field(default_factory=str)
    acm_class: str = field(default_factory=str)
    metadata_id: int = field(default=-1)
    document_id: int = field(default=-1)
    journal_ref: str = field(default_factory=str)
    journal_ref_utf8: str = field(default_factory=str)
    doi: str = field(default_factory=str)
    comments: str = field(default_factory=str)
    comments_utf8: str = field(default_factory=str)
    abs_categories: str = field(default_factory=str)
    formats: List[str] = field(default_factory=list)
    latest_version: int = field(default=1)
    latest: str = field(default_factory=str)

@dataclass
class Fulltext:
    """Fulltext content for an arXiv paper, including extraction metadata.

    **This is currently not in use. Currently arxiv-search does not
    index the full text of articles.**
    """

    content: str
    version: str
    created: datetime


@dataclass
class DateRange:
    """Represents an open or closed date range, for use in :class:`.Query`."""

    start_date: datetime = datetime(1990, 1, 1, tzinfo=consts.EASTERN)
    """The day/time on which the range begins."""

    end_date: datetime = datetime.now(tz=consts.EASTERN)
    """The day/time at (just before) which the range ends."""

    SUBMITTED_ORIGINAL = "submitted_date_first"
    SUBMITTED_CURRENT = "submitted_date"
    ANNOUNCED = "announced_date_first"
    date_type: str = field(default=SUBMITTED_CURRENT)
    """The date associated with the paper that should be queried."""

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        _str = ""
        if self.start_date:
            start_date = self.start_date.strftime("%Y-%m-%d")
            _str += f"from {start_date} "
        if self.end_date:
            end_date = self.end_date.strftime("%Y-%m-%d")
            _str += f"to {end_date}"
        return _str


# These have been refactored as TypedDicts for performance reasons. See
# DECISIONS.md (2019-04-22) for details.
class ClassificationPart(TypedDict):
    """Represents a node (group, archive, category) in a classification."""

    id: str
    name: str


class Classification(TypedDict):
    """Classification assigned to an e-print."""

    group: Optional[ClassificationPart]
    archive: Optional[ClassificationPart]
    category: Optional[ClassificationPart]


class ClassificationList(list):
    """Represents a list of arXiv classifications."""

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return ", ".join([str(item) for item in self])


class Operator(str, Enum):
    """Supported boolean operators."""

    AND = "AND"
    OR = "OR"
    ANDNOT = "ANDNOT"

    @classmethod
    def is_valid_value(cls, value: str) -> bool:
        """
        Determine whether or not ``value`` is a valid value of a member.

        Parameters
        ----------
        value : str

        Returns
        -------
        bool

        """
        try:
            cls(value)
        except ValueError:
            return False
        return True


class Field(str, Enum):
    """Supported fields in the classic API."""

    Title = "ti"
    Author = "au"
    Abstract = "abs"
    Comment = "co"
    JournalReference = "jr"
    SubjectCategory = "cat"
    ReportNumber = "rn"
    Identifier = "id"
    All = "all"


@dataclass
class Term:
    """Class representing a Field and search term.

    Examples
    --------
    .. code-block:: python

       term = Term(Field.Title, 'dark matter')

    """

    field: Field
    value: str = ""

    @property
    def is_empty(self) -> bool:
        """Return whether term is empty."""
        return self.value.strip() == ""


# mypy doesn't yet support recursive type definitions. These ignores suppress
# the cyclic definition error, and forward-references to ``Phrase`` are
# are replaced with ``Any``.
Phrase = Union[  # type: ignore
    Term,  # type: ignore
    Tuple[Operator, "Phrase"],  # type: ignore
    Tuple[Operator, "Phrase", "Phrase"],  # type: ignore
]
"""
Recursive representation of a search query.

Examples
--------

.. code-block:: python

   # Simple query without grouping/nesting.
   phrase: Phrase = Term(Field.Author, 'copernicus')

   # Simple query with a unary operator without grouping/nesting.
   phrase: Phrase = (Operator.ANDNOT, Term(Field.Author, 'copernicus'))

   # Simple conjunct query.
   phrase: Phrase = (
       Operator.AND,
       Term(Field.Author, "del_maestro"),
       Term(Field.Title, "checkerboard")
    )

   # Disjunct query with an unary not.
   phrase = (
       Operator.OR,
       Term(Field.Author, "del_maestro"),
       (
           Operator.ANDNOT,
           Term(Field.Title, "checkerboard")
        )
    )

   # Conjunct query with nested disjunct query.
   phrase = (
       Operator.ANDNOT,
       Term(Field.Author, "del_maestro"),
       (
           Operator.OR,
           Term(Field.Title, "checkerboard"),
           Term(Field.Title, "Pyrochlore")
        )
    )
"""


class SortDirection(str, Enum):
    """Provides function to convert sort direction string to ES DSL."""

    ascending = "ascending"
    descending = "descending"

    def to_es(self) -> Dict[str, str]:
        """Convert to ElasticSearch DSL."""
        return {"order": "asc" if self == SortDirection.ascending else "desc"}


class SortBy(str, Enum):
    """Provides function to convert sort-by string to ES DSL."""

    relevance = "relevance"
    last_updated_date = "lastUpdatedDate"
    submitted_date = "submittedDate"

    def to_es(self) -> str:
        """Convert to ElasticSearch DSL."""
        return {
            SortBy.relevance: "_score",
            SortBy.last_updated_date: "updated_date",
            SortBy.submitted_date: "submitted_date",
        }[self]


@dataclass
class SortOrder:
    """Provides function to convert sort order to ES DSL."""

    by: Optional[SortBy] = None
    direction: SortDirection = SortDirection.descending

    def to_es(self) -> List[Dict[str, Dict[str, str]]]:
        """Convert to ElasticSearch DSL."""
        if self.by is None:
            return consts.DEFAULT_SORT_ORDER
        else:
            return [{self.by.to_es(): self.direction.to_es()}]


@dataclass
class Query:
    """Represents a search query originating from the UI or API."""

    MAXIMUM_size = 2000
    """The maximum number of records that can be retrieved."""

    SUPPORTED_FIELDS = [
        ("all", "All fields"),
        ("title", "Title"),
        ("author", "Author(s)"),
        ("abstract", "Abstract"),
        ("comments", "Comments"),
        ("journal_ref", "Journal reference"),
        ("acm_class", "ACM classification"),
        ("msc_class", "MSC classification"),
        ("report_num", "Report number"),
        ("paper_id", "arXiv identifier"),
        ("doi", "DOI"),
        ("orcid", "ORCID"),
        ("license", "License (URI)"),
        ("author_id", "arXiv author ID"),
        ("help", "Help pages"),
        ("full_text", "Full text"),
    ]

    order: Union[SortOrder, Optional[str]] = field(default=None)
    size: int = field(default=50)
    page_start: int = field(default=0)
    include_older_versions: bool = field(default=False)
    hide_abstracts: bool = field(default=False)

    @property
    def page_end(self) -> int:
        """Get the index/offset of the end of the page."""
        return self.page_start + self.size

    @property
    def page(self) -> int:
        """Get the approximate page number."""
        return 1 + int(round(self.page_start / self.size))


@dataclass
class SimpleQuery(Query):
    """Represents a simple search query."""

    search_field: str = field(default_factory=str)
    value: str = field(default_factory=str)

    classification: ClassificationList = field(
        default_factory=ClassificationList
    )
    """Classification(s) by which to limit results."""

    include_cross_list: bool = field(default=True)
    """If True, secondaries are considered when limiting by classification."""
