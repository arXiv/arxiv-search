"""Data structs for search documents."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any

from dataclasses import dataclass, field
from mypy_extensions import TypedDict

from search.utils import utc_now
from search.domain.base import Classification, ClassificationList


# The class keyword ``total=False`` allows instances that do not contain all of
# the typed keys. See https://github.com/python/mypy/issues/2632 for
# background.


@dataclass
class Error:
    """Represents an error that happened in the system."""

    id: str
    error: str
    link: str
    author: str = "arXiv api core"
    created: datetime = field(default_factory=utc_now)


class Person(TypedDict, total=False):
    """Represents an author, owner, or other person in metadata."""

    full_name: str
    last_name: str
    first_name: str
    suffix: str

    affiliation: List[str]
    """Institutional affiliations."""

    orcid: Optional[str]
    """ORCID identifier."""

    author_id: Optional[str]
    """Legacy arXiv author identifier."""


class Document(TypedDict, total=False):
    """A search document, representing an arXiv paper."""

    submitted_date: datetime
    announced_date_first: date
    submitted_date_first: datetime
    submitted_date_latest: datetime
    submitted_date_all: List[str]
    id: str
    abstract: str
    abstract_tex: str
    authors: List[Person]
    authors_freeform: str
    owners: List[Person]
    modified_date: str
    updated_date: str
    is_current: bool
    is_withdrawn: bool
    license: Dict[str, str]
    paper_id: str
    paper_id_v: str
    title: str
    title_tex: str
    source: Dict[str, Any]
    version: int
    latest: str
    latest_version: int
    submitter: Optional[Person]
    report_num: str
    proxy: bool
    msc_class: List[str]
    acm_class: List[str]
    metadata_id: int
    journal_ref: str
    doi: str
    comments: str
    abs_categories: str
    formats: List[str]
    primary_classification: Classification
    secondary_classification: ClassificationList

    score: float

    # FIXME: Type.
    highlight: Dict[Any, Any]
    """Contains highlighted versions of field values."""

    # FIXME: Type.
    preview: Dict[Any, Any]
    """Contains truncations of field values for preview/snippet display."""

    # FIXME: Type.
    match: Dict[Any, Any]
    """Contains fields that matched but lack highlighting."""

    # FIXME: Type.
    truncated: Dict[Any, Any]
    """Contains fields for which the preview is truncated."""

    fulltext: Optional[str]

    # fulltext_vector: Optional[??]


class DocumentSetMetadata(TypedDict, total=False):
    """Metadata for search results."""

    current_page: int
    end: int
    max_pages: int
    size: int
    start: int
    total_results: int
    total_pages: int
    query: List[Dict[str, Any]]


class DocumentSet(TypedDict):
    """A set of search results retrieved from the search index."""

    metadata: DocumentSetMetadata
    results: List[Document]


def document_set_from_documents(documents: List[Document]) -> DocumentSet:
    """Generate a DocumentSet with only a list of Documents.

    Generates the metadata automatically, which is an advantage over calling
    DocumentSet(results=documents, metadata=dict()).
    """
    return DocumentSet(
        results=documents, metadata=metadata_from_documents(documents)
    )


def metadata_from_documents(documents: List[Document]) -> DocumentSetMetadata:
    """Generate DocumentSet metadata from a list of documents."""
    metadata: DocumentSetMetadata = {}
    metadata["size"] = len(documents)
    metadata["end"] = len(documents)
    metadata["total_results"] = len(documents)
    metadata["start"] = 0
    metadata["max_pages"] = 1
    metadata["current_page"] = 1
    metadata["total_pages"] = 1

    return metadata
