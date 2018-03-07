"""Controller helpers."""

from wtforms import Form, StringField, validators


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
