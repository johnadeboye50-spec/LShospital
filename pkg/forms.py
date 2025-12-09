from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, PasswordField, SubmitField,FileField,TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length,Optional,NumberRange

from flask_wtf.file import FileAllowed


class ProfileForm(FlaskForm):
    user_fullname = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=150)])
    user_bio = TextAreaField('Bio',validators=[DataRequired()])
    user_avatar = FileField('Image', validators=[Optional(), FileAllowed(['jpg','jpeg','png'], 'Image Only')])
    submit = SubmitField('Register')


class RegistrationForm(FlaskForm):
    first_name = StringField( validators=[DataRequired(), Length(min=3, max=100)])
    last_name = StringField( validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password',validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')

class CompleteProfileForm(FlaskForm):
    phone = StringField('Phone Number', validators=[DataRequired(message="Phone number is required."), Length(min=10, max=15)])
    address = TextAreaField('Address', validators=[DataRequired(message="Address is required."), Length(min=10, max=200)])
    gender = SelectField('Gender', choices=[("male", "Male"), ("female", "Female")],validators=[DataRequired(message="Please select a gender.")])
    dob = DateField("Date of Birth",format='%Y-%m-%d',validators=[DataRequired(message="Date of birth is required.")])
    submit = SubmitField('Save & Continue')

class LoginForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class PatientSettingsForm(FlaskForm):
    fname = StringField("First Name", validators=[DataRequired()])
    lname = StringField("Last Name", validators=[DataRequired()])
    phone = StringField("Phone Number", validators=[DataRequired()])
    address = TextAreaField("Address", validators=[DataRequired()])
    bio = TextAreaField("Bio")
    picture = FileField("Profile Picture")
    submit = SubmitField("Save Changes")

class DoctorForm(FlaskForm):
    firstname = StringField("First Name",validators=[DataRequired(), Length(min=2, max=100)])
    lastname = StringField("Last Name",validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email",validators=[DataRequired(), Email()])
    phone = IntegerField("Phone Number",validators=[DataRequired(), NumberRange(min=10000000, max=99999999999999999999)])
    specialization = SelectField("Specialization",validators=[DataRequired()],choices=[])
    license_no = StringField("Medical License Number",validators=[DataRequired(), Length(min=4, max=50)])
    experience = IntegerField("Years of Experience",validators=[DataRequired(), NumberRange(min=0, max=60)])
    bio = TextAreaField("Short Bio",validators=[Length(max=500)])
    doctor_gender = SelectField("Gender", choices=[("male", "Male"), ("female", "Female")], validators=[DataRequired()])
    profile_pic = FileField("Profile Photo",validators=[FileAllowed(["jpg", "png", "jpeg"], "Images only!")])
    password = PasswordField("Password",validators=[DataRequired(), Length(min=6, max=255)])
    confirm_password = PasswordField("Confirm Password",validators=[DataRequired(),EqualTo("password", message="Passwords must match.")])
    submit = SubmitField("Create Account")

class DoctorLoginForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class DoctorSettingsForm(FlaskForm):
    fname = StringField("First Name", validators=[DataRequired()])
    lname = StringField("Last Name", validators=[DataRequired()])
    phone = StringField("Phone Number", validators=[DataRequired()])
    address = TextAreaField("Address", validators=[DataRequired()])
    department = SelectField("Department", choices=[], validators=[DataRequired()])
    bio = TextAreaField("Bio")
    picture = FileField("Profile Picture")
    submit = SubmitField("Save Changes")

class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class DepartmentForm(FlaskForm):
    department_name = StringField('Department Name', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Save Department')

class SpecialtyForm(FlaskForm):
    specialty_name = StringField('Specialty Name', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Save Specialty')

class AdminPasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Change Password')