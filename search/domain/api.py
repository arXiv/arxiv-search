"""API-specific domain classes."""

from enum import Enum
from typing import NamedTuple, Optional, Tuple, Union

from .base import DateRange, Query, ClassificationList, Classification, List
from .advanced import FieldedSearchList, FieldedSearchTerm

from dataclasses import dataclass, field


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
    All = 'alll'


Term = Tuple[Field, str]     # The 1th position is the value of the field.
"""

Examples
--------

.. code-block:: python

   term: Term = ('ti': 'dark matter')

"""
Expression = Union[Term, Tuple[Operator, Term]]
"""A query term (field, value pair) with support for unary operators."""

Triple = Tuple[Union[Expression, 'Phrase'],
               Operator,
               Union[Expression, 'Phrase']]

Phrase = Union[Expression, Triple, List[Expression]]
"""

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
class ClassicAPIQuery:
    """Query supported by the classic arXiv API."""

    phrase: Phrase
    order: Optional[str] = field(default=None)
    size: int = field(default=50)
    page_start: int = field(default=0)


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
