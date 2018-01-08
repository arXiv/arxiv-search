"""Core data structures internal to the search service."""

import json
from typing import Optional, Type, Any
import jsonschema


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


class Query(SchemaBase):
    """Represents a search query originating from the UI or API."""

    __schema__ = 'schema/Query.json'


class Document(SchemaBase):
    """A single search document, representing an arXiv paper."""

    __schema__ = 'schema/Document.json'


class DocumentSet(SchemaBase):
    """A set of search results retrieved from the search index."""

    __schema__ = 'schema/DocumentSet.json'
