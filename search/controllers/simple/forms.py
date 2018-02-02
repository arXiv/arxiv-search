from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList

from wtforms.fields import HiddenField
from wtforms import widgets


class SimpleSearchForm(Form):
    searchtype = SelectField("Field", choices=[
        ('all', 'All fields'),
        ('title', 'Title'),
        ('author', 'Author(s)'),
        ('abstract', 'Abstract')
    ])
    query = StringField('Search or Article ID',
                        validators=[validators.Length(min=1)])
    results_per_page = SelectField('results per page', default=25, choices=[
        ('25', '25'),
        ('50', '50'),
        ('100', '100')
    ])
