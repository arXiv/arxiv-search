from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError

from wtforms.fields import HiddenField
from wtforms import widgets

# Special characters?


class FieldForm(Form):
    term = StringField("Search term...", [validators.Length(min=2)])
    operator = SelectField("Operator", choices=[
        ('AND', 'AND'), ('OR', 'OR'), ('NOT', 'NOT')
    ])
    field = SelectField("Field", choices=[
        ('title', 'Title'),
        ('author', 'Author(s)'),
        ('abstract', 'Abstract')
    ])


class SubjectForm(Form):
    all_subjects = BooleanField('All subjects')
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
    ])
    q_biology = BooleanField('Quantitative Biology (q-bio)')
    q_finance = BooleanField('Quantitative Finance (q-fin)')
    statistics = BooleanField('Statistics (stat)')


class DateForm(Form):
    all_dates = BooleanField('All dates')
    past_12 = BooleanField('Past 12 months')

    specific_year = BooleanField('Specific year')
    year = DateField('Year', format='%Y')

    date_range = BooleanField('Date range')

    from_date = DateField('From')
    to_date = DateField('to')

    def validate_year(form, field):
        if field.data is None:
            return
        start_of_time = date(year=1991, month=1, day=1)
        today = date.now().year
        if field.data < start_of_time or field.data > today:
            raise ValidationError('Not a valid publication year')



class AdvancedSearchForm(Form):
    advanced = HiddenField('true')
    # text_terms = FormField(FieldForm)
    subjects = FormField(SubjectForm)
    date = FormField(DateForm)
    results_per_page = SelectField('results per page', choices=[
        ('25', '25'),
        ('50', '50'),
        ('100', '100')
    ])
