"""Controller helpers."""

import re
from typing import Tuple

from wtforms import Form, StringField, validators

from search.domain import Query

CLASSIC_AUTHOR = r'([A-Za-z]+)_([a-zA-Z])(?=$|\s)'
OLD_ID_NUMBER = \
   r'(910[7-9]|911[0-2]|9[2-9](0[1-9]|1[0-2])|0[0-6](0[1-9]|1[0-2])|070[1-3])'\
   r'(00[1-9]|0[1-9][0-9]|[1-9][0-9][0-9])'
"""
The number part of the old arXiv identifier looks like YYMMNNN.

The old arXiv identifier scheme was used between 1991-07 and 2007-03
(inclusive).
"""


def does_not_start_with_wildcard(form: Form, field: StringField) -> None:
    """Check that ``value`` does not start with a wildcard character."""
    if not field.data:
        return
    if field.data.startswith('?') or field.data.startswith('*'):
        raise validators.ValidationError('Search cannot start with a wildcard')


def strip_white_space(value: str) -> str:
    """Strip whitespace from form input."""
    if not value:
        return value
    return value.strip()


def paginate(query: Query, data: dict) -> Query:
    """
    Update pagination parameters on a :class:`.Query` from request parameters.

    Parameters
    ----------
    query : :class:`.Query`
    data : dict

    Returns
    -------
    :class:`.Query`

    """
    query.page_start = int(data.get('start', 0))
    query.page_size = int(data.get('size', 50))
    return query


def catch_underscore_syntax(term: str) -> Tuple[str, bool]:
    """Rewrite author name strings in `surname_f` format to use commas."""
    match = re.search(CLASSIC_AUTHOR, term)
    if not match:
        return term, False
    return re.sub(CLASSIC_AUTHOR, r'\g<1>, \g<2>;', term).rstrip(';'), True


def is_old_papernum(term: str) -> bool:
    """Check whether term matches 7-digit pattern for old arXiv ID numbers."""
    if term and re.search(OLD_ID_NUMBER, term):
        return True
    return False
