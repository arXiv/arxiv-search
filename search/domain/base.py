"""Core data structures internal to the search service."""

import json
from typing import Optional, Type, Any
from datetime import date, datetime
import jsonschema


class Property(object):
    """Describes a named, typed property on a data structure."""

    def __init__(self, name: str, klass: Optional[Type] = None,
                 default: Any = None) -> None:
        """Set the name, type, and default value for the property."""
        self._name = name
        self.klass = klass
        self.default = default

    def __get__(self, instance: Any, owner: Optional[Type] = None) -> Any:
        """
        Retrieve the value of property from the data instance.
        Parameters
        ----------
        instance : object
            The data structure instance on which the property is set.
        owner : type
            The class/type of ``instance``.
        Returns
        -------
        object
            If the data structure is instantiated, returns the value of this
            property. Otherwise returns this :class:`.Property` instance.
        """
        if instance:
            if self._name not in instance.keys():
                instance[self._name] = self.default
            return instance[self._name]
        return self.default

    def __set__(self, instance: Any, value: Any) -> None:
        """
        Set the value of the property on the data instance.
        Parameters
        ----------
        instance : object
            The data structure instance on which the property is set.
        value : object
            The value to which the property should be set.
        Raises
        ------
        TypeError
            Raised when ``value`` is not an instance of the specified type
            for the property.
        """
        if self.klass is not None and not isinstance(value, self.klass):
            raise TypeError('Must be an %s' % self.klass.__name__)
        instance[self._name] = value


class SchemaBase(dict):
    """Base for domain classes with schema validation."""

    __schema__ = None

    @property
    def valid(self):
        """Indicate whether the domain object is valid, per its __schema__."""
        if self.__schema__ is None:    # No schema to validate against.
            return
        try:
            with open(self.__schema__) as f:
                schema = json.load(f)
        except IOError as e:
            raise RuntimeError('Could not load %s' % self.__schema__) from e

        try:
            jsonschema.validate(self, schema)
        except jsonschema.ValidationError as e:
            return False
        return True

    def json(self):
        """Return the string representation of the instance in JSON."""
        return json.dumps(self, default=lambda o: o.__dict__)

    def __str__(self):
        """Build a string representation, for use in rendering."""
        return '; '.join(['%s: %s' % (k, str(v))
                          for k, v in self.items() if v])


class DocMeta(SchemaBase):
    """Metadata for an arXiv paper, retrieved from the core repository."""


class Fulltext(SchemaBase):
    """Fulltext content for an arXiv paper, including extraction metadata."""


class DateRange(dict):
    """Represents an open or closed date range."""

    start_date = Property('start_date', datetime)
    """The day/time on which the range begins."""

    end_date = Property('end_date', datetime)
    """The day/time at (just before) which the range ends."""

    # on_version = Property('field', str)
    # """The date field on which to filter

    def __str__(self):
        """Build a string representation, for use in rendering."""
        _str = ''
        if self.start_date:
            start_date = self.start_date.strftime('%Y-%m-%d')
            _str += f'from {start_date} '
        if self.end_date:
            end_date = self.end_date.strftime('%Y-%m-%d')
            _str += f'to {end_date}'
        return _str


class Classification(dict):
    group = Property('group', str)
    archive = Property('archive', str)
    category = Property('category', str)

    def __str__(self):
        """Build a string representation, for use in rendering."""
        rep = f'{self.group}'
        if self.archive:
            rep += f':{self.archive}'
            if self.category:
                rep += f':{self.category}'
        return rep


class ClassificationList(list):
    def __str__(self):
        """Build a string representation, for use in rendering."""
        return ', '.join([str(item) for item in self])


class Query(SchemaBase):
    """Represents a search query originating from the UI or API."""

    raw_query = Property('raw_query', str)
    order = Property('order', str)
    page_size = Property('page_size', int)
    page_start = Property('page_start', int, 0)

    @property
    def page_end(self):
        """Get the index/offset of the end of the page."""
        return self.page_start + self.page_size

    @property
    def page(self):
        """Get the approximate page number."""
        return 1 + int(round(self.page_start/self.page_size))


class SimpleQuery(Query):
    """A query on a single field with a single value."""
    field = Property('field', str)
    value = Property('value', str)


class Document(SchemaBase):
    """A single search document, representing an arXiv paper."""

    __schema__ = 'schema/Document.json'


class DocumentSet(SchemaBase):
    """A set of search results retrieved from the search index."""

    __schema__ = 'schema/DocumentSet.json'
