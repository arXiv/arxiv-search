"""wtforms representations for an advanced search."""

from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError, FieldList

from wtforms.fields import HiddenField
from wtforms import widgets

from search.controllers.util import doesNotStartWithWildcard


class FieldForm(Form):
    """Subform for query parts on specific fields."""

    # pylint: disable=too-few-public-methods

    term = StringField("Search term...", validators=[doesNotStartWithWildcard])
    operator = SelectField("Operator", choices=[
        ('AND', 'AND'), ('OR', 'OR'), ('NOT', 'NOT')
    ], default='AND')
    field = SelectField("Field", choices=[
        ('title', 'Title'),
        ('author', 'Author(s)'),
        ('abstract', 'Abstract')
    ])


class ClassificationForm(Form):
    """Subform for selecting a classification to (disjunctively) filter by."""

    # pylint: disable=too-few-public-methods

    computer_science = BooleanField('Computer science (cs)')
    economics = BooleanField('Economics (econ)')
    eess = BooleanField('Electrical Engineering and Systems Science (eess)')
    mathematics = BooleanField('Mathematics (math)')
    physics = BooleanField('Physics')
    physics_archives = SelectField(choices=[
        ('all', 'all'), ('astro-ph', 'astro-ph'), ('cond-mat', 'cond-mat'),
        ('gr-qc', 'gr-qc'), ('hep-ex', 'hep-ex'), ('hep-lat', 'hep-lat'),
        ('hep-ph', 'hep-ph'), ('hep-th', 'hep-th'), ('math-ph', 'math-ph'),
        ('nlin', 'nlin'), ('nucl-ex', 'nucl-ex'), ('nucl-th', 'nucl-th'),
        ('physics', 'physics'), ('quant-ph', 'quant-ph')
    ], default='all')
    q_biology = BooleanField('Quantitative Biology (q-bio)')
    q_finance = BooleanField('Quantitative Finance (q-fin)')
    statistics = BooleanField('Statistics (stat)')


class DateForm(Form):
    """Subform with options for limiting results by publication date."""

    all_dates = BooleanField('All dates')
    past_12 = BooleanField('Past 12 months')

    specific_year = BooleanField('Specific year')
    year = DateField('Year', format='%Y', validators=[validators.Optional()])

    date_range = BooleanField('Date range')
    from_date = DateField('From', validators=[validators.Optional()])
    to_date = DateField('to', validators=[validators.Optional()])

    def validate_all_dates(self, field) -> None:
        """Only one option may be selected."""
        selected = int(field.data)
        for fname in ['past_12', 'specific_year', 'date_range']:
            selected += int(self.data.get(fname))
        if selected > 1:
            raise ValidationError('Only one date filter may be selected')

    def validate_specific_year(self, field) -> None:
        """If ``specific_year`` is selected, ``year`` must be set."""
        if field.data and not self.data.get('year'):
            raise ValidationError('Please select a year')

    def validate_date_range(self, field) -> None:
        """The field(s) ``from_date`` and/or ``to_date`` must be set."""
        if not field.data:
            return None

        if not self.data.get('from_date') and not self.data.get('to_date'):
            raise ValidationError('Must select start and/or end date(s)')
        if self.data.get('from_date') and self.data.get('to_date'):
            if self.data.get('from_date') >= self.data.get('to_date'):
                raise ValidationError('End date must be later than start date')

    def validate_year(self, field) -> None:
        """May not be prior to 1991, or later than the current year."""
        if field.data is None:
            return None

        start_of_time = date(year=1991, month=1, day=1)
        if field.data < start_of_time or field.data > date.today():
            raise ValidationError('Not a valid publication year')


class AdvancedSearchForm(Form):
    """Replacement for the 'classic' advanced search interface."""

    # pylint: disable=too-few-public-methods

    advanced = HiddenField('Advanced', default=1)
    """Used to indicate whether the form should be shown."""

    terms = FieldList(FormField(FieldForm), min_entries=1)
    classification = FormField(ClassificationForm)
    date = FormField(DateForm)
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
