from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList

from wtforms.fields import HiddenField
from wtforms import widgets


class SimpleSearchForm(Form):
    field = SelectField("Field", choices=[
        ('title', 'Title'),
        ('author', 'Author(s)'),
        ('abstract', 'Abstract')
    ])
    value = StringField('Search or Article ID')
