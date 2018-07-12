"""Provides form rendering and validation for the advanced search feature."""

import calendar
import re
from datetime import date, datetime
from typing import Callable, Optional, List, Any

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList, \
    RadioField

from wtforms.fields import HiddenField
from wtforms import widgets

from arxiv import taxonomy

from search.controllers.util import doesNotStartWithWildcard, stripWhiteSpace


class MultiFormatDateField(DateField):
    """Extends :class:`.DateField` to support multiple date formats."""

    def __init__(self, label: Optional[str] = None,
                 validators: Optional[List[Callable]] = None,
                 formats: List[str] = ['%Y-%m-%d %H:%M:%S'],
                 default_upper_bound: bool = False,
                 **kwargs: Any) -> None:
        """Override to change ``format: str`` to ``formats: List[str]``."""
        super(DateField, self).__init__(label, validators, **kwargs)
        self.formats = formats
        self.default_upper_bound = default_upper_bound

    def _value(self) -> str:
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            return self.data and self.data.strftime(self.formats[0]) or ''

    def process_formdata(self, valuelist: List[str]) -> None:
        """Try date formats until one sticks, or raise ValueError."""
        if valuelist:
            date_str = ' '.join(valuelist)
            self.data: Optional[date]
            for fmt in self.formats:
                try:
                    adj_date = datetime.strptime(date_str, fmt).date()
                    if self.default_upper_bound:
                        if not re.search(r'%[Bbm]', fmt):
                            # when month does not appear in matching format
                            adj_date = adj_date.replace(month=12, day=31)
                        elif not re.search('%d', fmt):
                            # when day does not appear in matching format
                            last_day = calendar.monthrange(adj_date.year,
                                                           adj_date.month)[1]
                            adj_date = adj_date.replace(day=last_day)
                    self.data = adj_date
                    return
                except ValueError:
                    continue
            self.data = None
            raise ValueError(self.gettext('Not a valid date value'))


class FieldForm(Form):
    """Subform for query parts on specific fields."""

    # pylint: disable=too-few-public-methods

    term = StringField("Search term...", filters=[stripWhiteSpace],
                       validators=[doesNotStartWithWildcard])
    operator = SelectField("Operator", choices=[
        ('AND', 'AND'), ('OR', 'OR'), ('NOT', 'NOT')
    ], default='AND')
    field = SelectField("Field", choices=[
        ('title', 'Title'),
        ('author', 'Author(s)'),
        ('abstract', 'Abstract'),
        ('comments', 'Comments'),
        ('journal_ref', 'Journal reference'),
        ('acm_class', 'ACM classification'),
        ('msc_class', 'MSC classification'),
        ('report_num', 'Report number'),
        ('paper_id', 'arXiv identifier'),
        ('doi', 'DOI'),
        ('orcid', 'ORCID'),
        ('author_id', 'arXiv author ID'),
        ('all', 'All fields')
    ])


class ClassificationForm(Form):
    """Subform for selecting a classification to (disjunctively) filter by."""

    # pylint: disable=too-few-public-methods

    # Map arXiv archives to fields on this form. Ideally we would autogenerate
    # form fields based on the arXiv taxonomy, but this can't easily happen
    # until we replace the classic-style advanced interface with faceted
    # search.
    ARCHIVES = [
        ('cs', 'computer_science'),
        ('econ', 'economics'),
        ('eess', 'eess'),
        ('math', 'mathematics'),
        ('physics', 'physics'),
        ('q-bio', 'q_biology'),
        ('q-fin', 'q_finance'),
        ('stat', 'statistics')
    ]
    PHYSICS_ARCHIVES = [('all', 'all')] + \
        [(archive, archive) for archive, description
         in taxonomy.ARCHIVES_ACTIVE.items()
         if description['in_group'] == 'grp_physics']

    computer_science = BooleanField('Computer Science (cs)')
    economics = BooleanField('Economics (econ)')
    eess = BooleanField('Electrical Engineering and Systems Science (eess)')
    mathematics = BooleanField('Mathematics (math)')
    physics = BooleanField('Physics')
    physics_archives = SelectField(choices=PHYSICS_ARCHIVES, default='all')
    q_biology = BooleanField('Quantitative Biology (q-bio)')
    q_finance = BooleanField('Quantitative Finance (q-fin)')
    statistics = BooleanField('Statistics (stat)')


def yearInBounds(form: Form, field: DateField) -> None:
    """May not be prior to 1991, or later than the current year."""
    if field.data is None:
        return None

    start_of_time = date(year=1991, month=1, day=1)
    if field.data < start_of_time or field.data > date.today():
        raise ValidationError('Not a valid publication year')


class DateForm(Form):
    """Subform with options for limiting results by publication date."""

    filter_by = RadioField(
        'Filter by', choices=[
            ('all_dates', 'All dates'),
            ('past_12', 'Past 12 months'),
            ('specific_year', 'Specific year'),
            ('date_range', 'Date range')
        ],
        default='all_dates'
    )

    year = DateField(
        'Year',
        format='%Y',
        validators=[validators.Optional(), yearInBounds]
    )
    from_date = MultiFormatDateField(
        'From',
        validators=[validators.Optional(), yearInBounds],
        formats=['%Y-%m-%d', '%Y-%m', '%Y']

    )
    to_date = MultiFormatDateField(
        'to',
        validators=[validators.Optional(), yearInBounds],
        formats=['%Y-%m-%d', '%Y-%m', '%Y'],
        default_upper_bound=True
    )

    def validate_filter_by(self, field: RadioField) -> None:
        """Ensure that related fields are filled."""
        if field.data == 'specific_year' and not self.data.get('year'):
            raise ValidationError('Please select a year')
        elif field.data == 'date_range':
            if not self.data.get('from_date') and not self.data.get('to_date'):
                raise ValidationError('Must select start and/or end date(s)')
            if self.data.get('from_date') and self.data.get('to_date'):
                if self.data.get('from_date') >= self.data.get('to_date'):
                    raise ValidationError(
                        'End date must be later than start date'
                    )


class AdvancedSearchForm(Form):
    """Replacement for the 'classic' advanced search interface."""

    # pylint: disable=too-few-public-methods

    advanced = HiddenField('Advanced', default=1)
    """Used to indicate whether the form should be shown."""

    terms = FieldList(FormField(FieldForm), min_entries=1)
    classification = FormField(ClassificationForm)
    date = FormField(DateForm)
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
    include_older_versions = BooleanField('Include older versions of papers')
