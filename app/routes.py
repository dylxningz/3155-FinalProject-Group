from flask import render_template, redirect, url_for, session
from app import app, db
from app.models import User
from app.forms import SignupForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask import render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash
from app import app, db
from app.models import User
from app.forms import SignupForm
from dotenv import load_dotenv
import os 
from authlib.integrations.flask_client import OAuth

load_dotenv()
oauth = OAuth(app)

spotify = oauth.register(
    name="spotify",
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
    api_base_url='https://api.spotify.com/v1/',
    client_kwargs={'scope': 'user-read-email user-read-private'},
)











#HOMEPAGE ROUTE
@app.route('/')
def index():
    return render_template('index.html')


#ERROR ROUTES
@app.errorhandler(404)
def page_not_found(error):
    error_status = 404
    error_message = "Page not found"
    return render_template('error.html', error_status=error_status, error_message=error_message), 404

@app.errorhandler(500)
def internal_server_error(error):
    error_status = 500
    error_message = "Internal server error"
    return render_template('error.html', error_status=error_status, error_message=error_message), 500

@app.errorhandler(403)
def forbidden(error):
    error_status = 403
    error_message = "Forbidden"
    return render_template('error.html', error_status=error_status, error_message=error_message), 403


#ACOUNT ROUTES

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Attempt to fetch the user by username first
        user = User.query.filter((User.username == form.username_or_email.data) | (User.email == form.username_or_email.data)).first()
        if user and check_password_hash(user.password, form.password.data):
            session['username'] = user.username
            # Redirect to the dashboard after successful login
            return redirect(url_for('dashboard'))
        else:
            # Flash a message if login was unsuccessful
            flash('Login Unsuccessful. Please check username/email and password', 'danger')
    # Render the login template with the form
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))
  
@app.route('/login/spotify')
def login_spotify():
    redirect_uri = url_for('authorize_spotify', _external=True)
    return spotify.authorize_redirect(redirect_uri)

# Spotify callback route
@app.route('/authorize/spotify')
def authorize_spotify():
    token = spotify.authorize_access_token()
    resp = spotify.get('me', token=token)
    user_info = resp.json()
    # Just a test to see whether we can connect or not so only printing user info
    print(user_info)
    
    return redirect(url_for('dashboard'))

@app.route('/community')
def community():
    return render_template('community.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')
