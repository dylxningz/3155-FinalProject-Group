from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, ValidationError
import psycopg
from db_secrets import DB_PASS
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
        with psycopg.connect(
                conninfo=f'postgresql://postgres:{DB_PASS}@localhost:5432/sympthonysonaruserdb',
        ) as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM user WHERE username IS NOT NULL OR email IS NOT NULL"
            values = (field.data, field.data)
            cursor.execute(query, values)

            result = cursor.fetchone()

            if result is not None:
                raise ValidationError('Username or Email already exists')


