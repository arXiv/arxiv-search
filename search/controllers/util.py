"""Controller helpers."""

import re
from typing import Tuple

from wtforms import Form, StringField, validators

from search.domain import Query

CLASSIC_AUTHOR = r"([A-Za-z]+)_([a-zA-Z])(?=$|\s)"

# TODO: these should all be snake-case, or all camel-case, but not both.


def doesNotStartWithWildcard(form: Form, field: StringField) -> None:
    """Check that ``value`` does not start with a wildcard character."""
    if not field.data:
        return
    if field.data.startswith('?') or field.data.startswith('*'):
        raise validators.ValidationError('Search cannot start with a wildcard')


def stripWhiteSpace(value: str) -> str:
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
    return re.sub(CLASSIC_AUTHOR, "\g<1>, \g<2>;", term).rstrip(';'), True
