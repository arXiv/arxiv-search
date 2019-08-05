"""API-specific domain classes."""
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple, Optional, Tuple, Union

from .base import DateRange, Query, ClassificationList, Classification, List
from .advanced import FieldedSearchList, FieldedSearchTerm


class Operator(Enum):
    """Supported boolean operators."""

    AND = 'AND'
    OR = 'OR'
    ANDNOT = 'ANDNOT'


class Field(Enum):
    """Supported fields in the classic API."""

    Title = 'ti'
    Author = 'au'
    Abstract = 'abs'
    Comment = 'co'
    JournalReference = 'jr'
    SubjectCategory = 'cat'
    ReportNumber = 'rn'
    Identifier = 'id'
    All = 'all'


Term = Tuple[Field, str]
"""
Tuple representing a Field and search term.

Examples
--------

.. code-block:: python

   term: Term = (Field.Title : 'dark matter')

"""

# mypy doesn't yet support recursive type definitions, so we suppress analysis
Phrase = Union[Term, Tuple[Operator, 'Phrase'], Tuple['Phrase']]  #type: ignore
"""
Recursive representation of a search query.

Examples
--------

.. code-block:: python

   # Simple query without grouping/nesting.
   phrase: Phrase = ('au', 'copernicus')

   # Simple query with a unary operator without grouping/nesting.
   phrase: Phrase = ('ANDNOT', ('au', 'copernicus'))

   # Simple conjunct query.
   phrase: Phrase = (('au', 'del_maestro'), 'AND', ('ti', 'checkerboard'))

   # Disjunct query with an unary not.
   phrase = (('au', 'del_maestro'), 'OR', ('ANDNOT', ('ti', 'checkerboard')))

   # Conjunct query with nested disjunct query.
   phrase = (('au', 'del_maestro'), 'ANDNOT',
             (('ti', 'checkerboard'), 'OR', ('ti', 'Pyrochlore')))


"""


@dataclass
class ClassicAPIQuery(Query):
    """Query supported by the classic arXiv API."""

    phrase: Optional[Phrase] = field(default=None)
    id_list: Optional[List[str]] = field(default=None)

    def __post_init__(self) -> None:
        """Ensure that either a phrase or id_list is set."""
        if self.phrase is None and self.id_list is None:
            raise ValueError("ClassicAPIQuery requires either a phrase, id_list, or both")


def get_default_extra_fields() -> List[str]:
    """These are the default extra fields."""
    return ['title']


def get_required_fields() -> List[str]:
    """These fields should always be included."""
    return ['paper_id', 'paper_id_v', 'version', 'href', 'canonical']


@dataclass
class APIQuery(Query):
    """
    Represents an API query.

    Similar to an advanced query.
    """

    date_range: Optional[DateRange] = None
    primary_classification: Tuple[Classification, ...] = \
        field(default_factory=tuple)
    """Limit results to a specific primary classification."""
    secondary_classification: List[Tuple[Classification, ...]] = field(
        default_factory=list
    )
    """Limit results by cross-list classification."""
    terms: FieldedSearchList = field(default_factory=FieldedSearchList)
    include_fields: List[str] = field(default_factory=get_default_extra_fields)

    def __post_init__(self) -> None:
        """Be sure that the required fields are prepended to include_fields."""
        self.include_fields = list(
            set(get_required_fields() + self.include_fields)
        )
