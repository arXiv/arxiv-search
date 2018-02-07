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
                        validators=[validators.Length(min=1),
                                    doesNotStartWithWildcard])
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
