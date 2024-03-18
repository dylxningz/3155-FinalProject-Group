from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, ValidationError
import re  # Regular expression module for email validation


class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username_or_email = StringField('Username or Email', validators=[DataRequired(), Length(min=4, max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Login')

    def validate_username_or_email(form, field):
        # This method should ideally be used to perform custom validation.
        # However, for the purpose of distinguishing between a username and email,
        # this logic may be better suited directly in the view function,
        # as validation here would prevent form submission if the field doesn't match an email pattern,
        # which isn't the intended behavior if usernames are allowed.
        pass
