from datetime import date

from wtforms import Form, BooleanField, StringField, SelectField, validators, \
    FormField, SelectMultipleField, DateField, ValidationError

from wtforms.fields import HiddenField

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
    economics = BooleanField('Economics (econ)')
    mathematics = BooleanField('Mathematics (math)')
    physics = BooleanField('Physics')
    physics_archives = SelectMultipleField(choices=[
        ('all', 'all'),
        # 'astro-ph', 'cond-mat', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph',
        # 'hep-th', 'math-ph', 'nlin', 'nucl-ex', 'nucl-th', 'physics',
        # 'quant-ph'
    ])


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
    # subjects = FormField(SubjectForm)
    date = FormField(DateForm)
    results_per_page = SelectField('results per page', choices=[
        ('25', '25'),
        ('50', '50'),
        ('100', '100')
    ])
