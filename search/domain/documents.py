"""Data structs for search documents."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from mypy_extensions import TypedDict


class Person(TypedDict):
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


class Document(TypedDict):
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
    primary_classification: Dict[str, str]
    secondary_classification: List[Dict[str, str]]

    score: float

    highlight: dict
    """Contains highlighted versions of field values."""

    preview: dict
    """Contains truncations of field values for preview/snippet display."""

    match: dict
    """Contains fields that matched but lack highlighting."""

    truncated: dict
    """Contains fields for which the preview is truncated."""


class DocumentSet(TypedDict):
    """A set of search results retrieved from the search index."""

    metadata: Dict[str, Any]
    results: List[Document]
