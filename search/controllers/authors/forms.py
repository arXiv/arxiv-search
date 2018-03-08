"""wtforms representations for an author."""

from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList

from wtforms.fields import HiddenField
from wtforms import widgets

from search.controllers.util import doesNotStartWithWildcard, stripWhiteSpace


def validate_fullname(form: Form, field: StringField) -> None:
    """Either fullname or surname must be set."""
    if not (form.data['surname'] or form.data['fullname']):
        raise ValidationError('Enter a value for either surname or fullname')


class AuthorForm(Form):
    """wtforms.Form representing an author."""

    # pylint: disable=missing-docstring,too-few-public-methods

    forename = StringField("Forename",
                           validators=[
                                validators.Length(min=1),
                                validators.Optional(strip_whitespace=True),
                                doesNotStartWithWildcard
                           ],
                           filters=[stripWhiteSpace])
    surname = StringField("Surname", filters=[stripWhiteSpace],
                          validators=[doesNotStartWithWildcard])
    fullname = StringField("Full name", filters=[stripWhiteSpace],
                           validators=[validate_fullname,
                                       doesNotStartWithWildcard])


class AuthorSearchForm(Form):
    """wtforms.Form representing an author search."""

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
