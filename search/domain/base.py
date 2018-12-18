"""Base domain classes for search service."""

from typing import Any, Optional, List, Dict
from datetime import datetime, date
from operator import attrgetter
from pytz import timezone
import re

from arxiv import taxonomy

from dataclasses import dataclass, field
from dataclasses import asdict as _asdict

EASTERN = timezone('US/Eastern')


def asdict(obj: Any) -> dict:
    """Coerce a dataclass object to a dict."""
    return {key: value for key, value in _asdict(obj).items()}


@dataclass
class Person:
    """Represents an author, owner, or other person in metadata."""

    full_name: str
    last_name: str = field(default_factory=str)
    first_name: str = field(default_factory=str)
    suffix: str = field(default_factory=str)

    affiliation: List[str] = field(default_factory=list)
    """Institutional affiliations."""

    orcid: Optional[str] = field(default=None)
    """ORCID identifier."""

    author_id: Optional[str] = field(default=None)
    """Legacy arXiv author identifier."""

    @classmethod
    def fields(cls) -> List[str]:
        """Get the names of fields on this class."""
        return cls.__dataclass_fields__.keys()  # type: ignore


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
    secondary_classification: List[Dict[str, str]] = \
        field(default_factory=list)
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
    """Fulltext content for an arXiv paper, including extraction metadata."""

    content: str
    version: str
    created: datetime


@dataclass
class DateRange:
    """Represents an open or closed date range, for use in :class:`.Query`."""

    start_date: datetime = datetime(1990, 1, 1, tzinfo=EASTERN)
    """The day/time on which the range begins."""

    end_date: datetime = datetime.now(tz=EASTERN)
    """The day/time at (just before) which the range ends."""

    SUBMITTED_ORIGINAL = 'submitted_date_first'
    SUBMITTED_CURRENT = 'submitted_date'
    ANNOUNCED = 'announced_date_first'
    date_type: str = field(default=SUBMITTED_CURRENT)
    """The date associated with the paper that should be queried."""

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        _str = ''
        if self.start_date:
            start_date = self.start_date.strftime('%Y-%m-%d')
            _str += f'from {start_date} '
        if self.end_date:
            end_date = self.end_date.strftime('%Y-%m-%d')
            _str += f'to {end_date}'
        return _str


@dataclass
class Classification:
    """Represents an arXiv classification for a paper."""

    group: Optional[dict] = None
    archive: Optional[dict] = None
    category: Optional[dict] = None

    @property
    def group_display(self) -> str:
        if "name" in self.group:
            return self.group["name"]
        return taxonomy.get_group_display(self.group["id"])

    @property
    def archive_display(self) -> str:
        if "name" in self.archive:
            return self.archive["name"]
        return taxonomy.get_archive_display(self.archive["id"])

    @property
    def category_display(self) -> str:
        if "name" in self.category:
            return self.category["name"]
        return taxonomy.get_category_display(self.category["id"])

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        s = ""
        if self.group:
            s += self.group_display
        if self.archive:
            if s:
                s += " :: "
            s += self.archive_display
        if self.category:
            if s:
                s += " :: "
            s += self.category_display
        return s


class ClassificationList(list):
    """Represents a list of arXiv classifications."""

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return ', '.join([str(item) for item in self])


@dataclass
class Query:
    """Represents a search query originating from the UI or API."""

    MAXIMUM_size = 500
    """The maximum number of records that can be retrieved."""

    SUPPORTED_FIELDS = [
        ('all', 'All fields'),
        ('title', 'Title'),
        ('author', 'Author(s)'),
        ('abstract', 'Abstract'),
        ('comments', 'Comments'),
        ('journal_ref', 'Journal reference'),
        ('acm_class', 'ACM classification'),
        ('msc_class', 'MSC classification'),
        ('report_num', 'Report number'),
        ('paper_id', 'arXiv identifier'),
        ('doi', 'DOI'),
        ('orcid', 'ORCID'),
        ('license', 'License (URI)'),
        ('author_id', 'arXiv author ID'),
        ('help', 'Help pages'),
        ('full_text', 'Full text')
    ]

    order: Optional[str] = field(default=None)
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
        return 1 + int(round(self.page_start/self.size))

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return '; '.join([
            '%s: %s' % (attr, attrgetter(attr)(self))
            for attr in type(self).__dataclass_fields__.keys()   # type: ignore
            if attrgetter(attr)(self)
        ])  # pylint: disable=E1101


@dataclass
class SimpleQuery(Query):
    """Represents a simple search query."""

    search_field: str = field(default_factory=str)
    value: str = field(default_factory=str)
    primary_classification: ClassificationList = field(
        default_factory=ClassificationList
    )


@dataclass(init=True)
class Document:
    """A search document, representing an arXiv paper."""

    submitted_date: Optional[datetime] = None
    announced_date_first: Optional[date] = None
    submitted_date_first: Optional[datetime] = None
    submitted_date_latest: Optional[datetime] = None
    submitted_date_all: List[str] = field(default_factory=list)
    id: str = field(default_factory=str)
    abstract: str = field(default_factory=str)
    abstract_tex: str = field(default_factory=str)
    authors: List[Person] = field(default_factory=list)
    authors_freeform: str = field(default_factory=str)
    owners: List[Person] = field(default_factory=list)
    modified_date: str = field(default_factory=str)
    updated_date: str = field(default_factory=str)
    is_current: bool = True
    is_withdrawn: bool = False
    license: Dict[str, str] = field(default_factory=dict)
    paper_id: str = field(default_factory=str)
    paper_id_v: str = field(default_factory=str)
    title: str = field(default_factory=str)
    title_tex: str = field(default_factory=str)
    source: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    latest: str = field(default_factory=str)
    latest_version: int = 0
    submitter: Optional[Person] = field(default=None)
    report_num: str = field(default_factory=str)
    proxy: bool = False
    msc_class: List[str] = field(default_factory=list)
    acm_class: List[str] = field(default_factory=list)
    metadata_id: int = -1
    journal_ref: str = field(default_factory=str)
    doi: str = field(default_factory=str)
    comments: str = field(default_factory=str)
    abs_categories: str = field(default_factory=str)
    formats: List[str] = field(default_factory=list)
    primary_classification: Classification = field(
        default_factory=Classification
    )
    secondary_classification: ClassificationList = field(
        default_factory=ClassificationList
    )

    score: float = 1.0

    highlight: dict = field(default_factory=dict)
    """Contains highlighted versions of field values."""

    preview: dict = field(default_factory=dict)
    """Contains truncations of field values for preview/snippet display."""

    match: dict = field(default_factory=dict)
    """Contains fields that matched but lack highlighting."""

    truncated: dict = field(default_factory=dict)
    """Contains fields for which the preview is truncated."""

    def __post_init__(self) -> None:
        """Set latest_version, if not already set."""
        if not self.latest_version and self.latest:
            m = re.match(r'^(.+?)(?:v(?P<version>[\d]+))?$', self.latest)
            if m and m.group('version'):
                self.latest_version = int(m.group('version'))
            else:
                self.latest_version = 1

    @classmethod
    def fields(cls) -> List[str]:
        """Get the names of fields on this class."""
        return cls.__dataclass_fields__.keys()  # type: ignore


@dataclass
class DocumentSet:
    """A set of search results retrieved from the search index."""

    metadata: Dict[str, Any]
    results: List[Document]
    # __schema__ = 'schema/DocumentSet.json'
