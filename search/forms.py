from wtforms import Form, BooleanField, StringField, SelectField, validators, FormField

# Special characters?

#wtforms.fields.FieldList(
#fields.BooleanField(
#wtforms.fields.DateField(
#wtforms.fields.FormField(form_class, default field arguments, separator='-')

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
    phyics = BooleanField('Physics')

class AdvancedSearchForm(Form):
    text_terms = FormField(FieldForm)
    subjects = FormField(SubjectForm)
    

    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email Address', [validators.Length(min=6, max=35)])
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', [validators.DataRequired()])
