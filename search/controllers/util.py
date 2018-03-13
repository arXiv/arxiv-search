"""Controller helpers."""

from wtforms import Form, StringField, validators
from search.domain import Query


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
    query.page_size = int(data.get('size', 25))
    return query
