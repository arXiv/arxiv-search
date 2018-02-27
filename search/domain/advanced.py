"""Represents fielded search terms, with multiple operators."""

from .base import Property, DateRange, Query, ClassificationList


class FieldedSearchTerm(dict):
    """Represents a fielded search term."""

    operator = Property('operator', str)
    field = Property('field', str)
    term = Property('term', str)

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return f'{self.operator} {self.field}={self.term}'


class FieldedSearchList(list):
    """Represents a list of fielded search terms."""

    def __str__(self) -> str:
        """Build a string representation, for use in rendering."""
        return '; '.join([str(item) for item in self])


class AdvancedQuery(Query):
    """
    Represents an advanced query.

    An advanced query contains fielded search terms and boolean operators.
    """

    date_range = Property('date_range', DateRange)
    primary_classification = Property('primary_classification',
                                      ClassificationList)
    terms = Property('terms', FieldedSearchList, FieldedSearchList())
