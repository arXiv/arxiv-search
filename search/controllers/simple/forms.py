"""Provides form rendering and validation for the simple search feature."""

from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList, \
    widgets, RadioField
from wtforms.fields import HiddenField

from search.controllers.util import does_not_start_with_wildcard, \
                                    has_balanced_quotes, strip_white_space
from ...domain import Query


class SimpleSearchForm(Form):
    """Provides a simple field-query search form."""

    searchtype = SelectField("Field", choices=Query.SUPPORTED_FIELDS)
    query = StringField('Search or Article ID',
                        filters=[strip_white_space],
                        validators=[does_not_start_with_wildcard,
                                    has_balanced_quotes])
    size = SelectField('results per page', default=50, choices=[
        ('25', '25'),
        ('50', '50'),
        ('100', '100'),
        ('200', '200')
    ])
    order = SelectField('Sort results by', choices=[
        ('-announced_date_first', 'Announcement date (newest first)'),
        ('announced_date_first', 'Announcement date (oldest first)'),
        ('-submitted_date', 'Submission date (newest first)'),
        ('submitted_date', 'Submission date (oldest first)'),
        ('', 'Relevance')
    ], validators=[validators.Optional()], default='-announced_date_first')

    HIDE_ABSTRACTS = 'hide'
    SHOW_ABSTRACTS = 'show'

    abstracts = RadioField('Abstracts', choices=[
        (SHOW_ABSTRACTS, 'Show abstracts'),
        (HIDE_ABSTRACTS, 'Hide abstracts')
    ], default=SHOW_ABSTRACTS)

    def validate_query(form: Form, field: StringField) -> None:
        """Validate the length of the querystring, if searchtype is set."""
        if form.searchtype.data is None or form.searchtype.data == 'None':
            return
        if not form.query.data or len(form.query.data) < 1:
            raise validators.ValidationError(
                'Field must be at least 1 character long.'
            )
