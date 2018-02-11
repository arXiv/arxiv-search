"""wtforms representations for an author."""

from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList

from wtforms.fields import HiddenField
from wtforms import widgets

from search.controllers.util import doesNotStartWithWildcard


class AuthorForm(Form):
    # pylint: disable=missing-docstring,too-few-public-methods
    forename = StringField("Forename", validators=[validators.Length(min=1),
                                                   validators.Optional(),
                                                   doesNotStartWithWildcard])
    surname = StringField("Surname", validators=[validators.Length(min=1),
                                                 doesNotStartWithWildcard])


class AuthorSearchForm(Form):
    # pylint: disable=missing-docstring,too-few-public-methods
    authors = FieldList(FormField(AuthorForm), min_entries=1)
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
