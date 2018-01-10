"""Core data structures internal to the search service."""

import json
from typing import Optional, Type, Any
from datetime import date
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


class DocMeta(SchemaBase):
    """Metadata for an arXiv paper, retrieved from the core repository."""


class Fulltext(SchemaBase):
    """Fulltext content for an arXiv paper, including extraction metadata."""


class DateRange(dict):
    """Represents an open or closed date range."""

    start_date = Property('start_date', date)
    """The day on which the range begins."""

    end_date = Property('end_date', date)
    """The day at (just before) which the range ends."""


class FieldedSearchTerm(dict):
    """Represents a fielded search term."""

    operator = Property('operator', str)
    field = Property('field', str)
    term = Property('term', str)


class Query(SchemaBase):
    """Represents a search query originating from the UI or API."""

    raw_query = Property('raw_query', str)
    date_range = Property('date_range', DateRange)
    subjects = Property('subjects', list)
    terms = Property('terms', list, [])
    order = Property('order', str)


class Document(SchemaBase):
    """A single search document, representing an arXiv paper."""

    __schema__ = 'schema/Document.json'


class DocumentSet(SchemaBase):
    """A set of search results retrieved from the search index."""

    __schema__ = 'schema/DocumentSet.json'
