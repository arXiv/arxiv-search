"""wtforms representations for a simple search."""

from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList

from wtforms.fields import HiddenField
from wtforms import widgets

from search.controllers.util import doesNotStartWithWildcard


class SimpleSearchForm(Form):
    """Provides a simple field-query search form."""

    searchtype = SelectField("Field", choices=[
        ('all', 'All fields'),
        ('title', 'Title'),
        ('author', 'Author(s)'),
        ('abstract', 'Abstract')
    ])
    query = StringField('Search or Article ID',
                        validators=[doesNotStartWithWildcard])
    size = SelectField('results per page', default=25, choices=[
        ('25', '25'),
        ('50', '50'),
        ('100', '100')
    ])
    order = SelectField('Sort results by', choices=[
        ('', 'Relevance'),
        ('submitted_date', 'Submission date (ascending)'),
        ('-submitted_date', 'Submission date (descending)'),
    ], validators=[validators.Optional()])

    def validate_query(form: Form, field: StringField) -> None:
        """Validate the length of the querystring, if searchtype is set."""
        if form.searchtype.data is None or form.searchtype.data == 'None':
            return
        if not form.query.data or len(form.query.data) < 1:
            raise validators.ValidationError(
                'Field must be at least 1 character long.'
            )
