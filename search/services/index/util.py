"""Helpers for building ES queries."""

import re
from typing import Any, Optional, Tuple, Union, List
from elasticsearch_dsl import Search, Q, SF

from .exceptions import QueryError

# We'll compile this ahead of time, since it gets called quite a lot.
STRING_LITERAL = re.compile(r"(['\"][^'\"]*['\"])")
"""Pattern for string literals (quoted) in search queries."""


def wildcardEscape(querystring: str) -> Tuple[str, bool]:
    """
    Detect wildcard characters, and escape any that occur within a literal.

    Parameters
    ----------
    querystring : str

    Returns
    -------
    str
        Query string with wildcard characters enclosed in literals escaped.
    bool
        If a non-literal wildcard character is present, returns True.

    """
    # This should get caught by the controller (form validation), but just
    # in case we should check for it here.
    if querystring.startswith('?') or querystring.startswith('*'):
        raise QueryError('Query cannot start with a wildcard')

    # Escape wildcard characters within string literals.
    # re.sub() can't handle the complexity, sadly...
    parts = re.split(STRING_LITERAL, querystring)
    parts = [part.replace('*', r'\*').replace('?', r'\?')
             if part.startswith('"') or part.startswith("'") else part
             for part in parts]
    querystring = "".join(parts)

    # Only unescaped wildcard characters should remain.
    wildcard = re.search(r'(?<!\\)([\*\?])', querystring) is not None
    return querystring, wildcard


def is_literal_query(term: str) -> bool:
    """Determine whether the term is intended to be treated as a literal."""
    return re.match('"[^"]+"', term) is not None


def Q_(qtype: str, field: str, value: str) -> Q:
    """Construct a :class:`.Q`, but handle wildcards first."""
    value, wildcard = wildcardEscape(value)
    if wildcard:
        return Q('wildcard', **{field: value})
    return Q(qtype, **{field: value})
