"""Provides form rendering and validation for the simple search feature."""

from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList, \
    widgets
from wtforms.fields import HiddenField

from search.controllers.util import doesNotStartWithWildcard, stripWhiteSpace


class SimpleSearchForm(Form):
    """Provides a simple field-query search form."""

    searchtype = SelectField("Field", choices=[
        ('all', 'All fields'),
        ('title', 'Title'),
        ('author', 'Author(s)'),
        ('abstract', 'Abstract'),
        ('comments', 'Comments'),
        ('journal_ref', 'Journal ref'),
        ('acm_class', 'ACM classification'),
        ('msc_class', 'MSC classification'),
        ('report_num', 'Report number'),
        ('paper_id', 'Identifier'),
        ('doi', 'DOI'),
        ('orcid', 'ORCID'),
        ('author_id', 'Author ID')
    ])
    query = StringField('Search or Article ID',
                        filters=[stripWhiteSpace],
                        validators=[doesNotStartWithWildcard])
    size = SelectField('results per page', default=50, choices=[
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
    ], validators=[validators.Optional()])

    def validate_query(form: Form, field: StringField) -> None:
        """Validate the length of the querystring, if searchtype is set."""
        if form.searchtype.data is None or form.searchtype.data == 'None':
            return
        if not form.query.data or len(form.query.data) < 1:
            raise validators.ValidationError(
                'Field must be at least 1 character long.'
            )
