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
import requests

load_dotenv()
oauth = OAuth(app)

#used when we need to pull data from specific user on spotify// requires their consent and authentication

spotify = oauth.register(
    name="spotify",
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
    api_base_url='https://api.spotify.com/v1/',
    client_kwargs={'scope': 'user-read-email user-read-private'},
)
#Used when we need to pull public data from spotify not pertaning to a specific user

def get_client_credentials_token():
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    token_url = 'https://accounts.spotify.com/api/token'
    
    response = requests.post(token_url, auth=(client_id, client_secret), data={'grant_type': 'client_credentials'})
    
    if response.status_code == 200:
        token_info = response.json()
        return token_info['access_token']
    else:
        raise Exception("Failed to obtain token")


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
  

# Spotify login route authentication required
@app.route('/login/spotify')
def login_spotify():
    redirect_uri = url_for('authorize_spotify', _external=True)
    return spotify.authorize_redirect(redirect_uri)

# Spotify callback route
@app.route('/authorize/spotify')
def authorize_spotify():
    try:
        token = spotify.authorize_access_token()
        session['access_token'] = token['access_token']

    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('index'))
    #used to make sure user is redirected to correct page and not automatically dashboard after each request
    next_url = session.pop('next_url', None)
    return redirect(next_url if next_url else url_for('dashboard'))

@app.route('/community')
def community():
    return render_template('community.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')


# Spotify routes client credentials flow (no user authentication required)
#should pull data from spotify and people not needing to link spotify account to view

@app.route('/artist/<artist_id>')
def artist_page(artist_id):
    try:
        access_token = get_client_credentials_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        # Artist information
        artist_response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=headers)

        # Artist's top tracks
        top_tracks_response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US', headers=headers)

        # Artist's albums
        albums_response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}/albums?market=US&limit=5', headers=headers)

        if artist_response.status_code == 200 and top_tracks_response.status_code == 200 and albums_response.status_code == 200:
            artist_info = artist_response.json()
            top_tracks = top_tracks_response.json()['tracks'][:5]  # Limit to top 5 tracks
            albums = albums_response.json()['items']
            return render_template('spotify/artist.html', artist=artist_info, top_tracks=top_tracks, albums=albums)
        else:
            flash('Failed to fetch artist information, top tracks, or albums from Spotify.', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('index'))
    

@app.route('/top-songs')
def top_songs():
    try:
        access_token = get_client_credentials_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Retrieve top 50 songs in the US
        response = requests.get('https://api.spotify.com/v1/playlists/37i9dQZEVXbLRQDuF5jeBp/tracks', headers=headers)
        
        if response.status_code == 200:
            top_songs = response.json()['items'][:50]  # Limit to top 50 songs
            return render_template('spotify/top_songs.html', top_songs=top_songs)
        else:
            flash('Failed to fetch top songs from Spotify.', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('index'))