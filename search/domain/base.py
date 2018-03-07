"""Core data structures internal to the search service."""

from typing import Any, Iterable, NamedTuple, Optional, Type
from datetime import date, datetime
import json
from operator import attrgetter

import jsonschema

from dataclasses import dataclass, fields

@dataclass(init=False)
class SchemaBase:
    """Base for domain classes with standardized JSON and str representations."""

    def json(self) -> str:
        """Return the string representation of the instance in JSON."""
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return '; '.join(['%s: %s' % (attr, attrgetter(attr)(self))
                          for attr in fields(self) if attrgetter(attr)(self)]) # pylint: disable=E1101

@dataclass
class DocMeta(SchemaBase):
    """Metadata for an arXiv paper, retrieved from the core repository."""

@dataclass
class Fulltext(SchemaBase):
    """Fulltext content for an arXiv paper, including extraction metadata."""

class DateRange(NamedTuple):
    """Represents an open or closed date range."""

    start_date: datetime
    """The day/time on which the range begins."""

    end_date: datetime
    """The day/time at (just before) which the range ends."""

    # on_version = Property('field', str)
    # """The date field on which to filter

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


class Classification(NamedTuple):
    """Represents an arxiv classification."""

    group: str
    archive: str
    category: str

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        rep = f'{self.group}'
        if self.archive:
            rep += f':{self.archive}'
            if self.category:
                rep += f':{self.category}'
        return rep


class ClassificationList(list):
    """Represents a list of arxiv classifications."""

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return ', '.join([str(item) for item in self])

@dataclass
class Query(SchemaBase):
    """Represents a search query originating from the UI or API."""

    raw_query: str
    order: str
    page_size: int
    page_start: int

    @property
    def page_end(self) -> int:
        """Get the index/offset of the end of the page."""
        return self.page_start + self.page_size

    @property
    def page(self) -> int:
        """Get the approximate page number."""
        return 1 + int(round(self.page_start/self.page_size))

@dataclass
class SimpleQuery(Query):
    """A query on a single field with a single value."""

    field: str
    value: str

@dataclass
class Document(SchemaBase):
    """A single search document, representing an arXiv paper."""

    # __schema__ = 'schema/Document.json'

@dataclass
class DocumentSet(SchemaBase):
    """A set of search results retrieved from the search index."""

    # __schema__ = 'schema/DocumentSet.json'
