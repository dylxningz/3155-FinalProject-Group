from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
import requests
from flask_login import LoginManager
from db_secrets import DB_URI, CLIENT_ID, CLIENT_SECRET


import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecret'
app.config['SQLALCHEMY_DATABASE_URI'] =(DB_URI)
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Specify the login route
login_manager.login_message_category = 'info'




from app.models import User  # Import your User model
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


oauth = OAuth(app)

# used when we need to pull data from specific user on spotify// requires their consent and authentication

spotify = oauth.register(
    name="spotify",
    client_id=(CLIENT_ID),
    client_secret=(CLIENT_SECRET),
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
    api_base_url='https://api.spotify.com/v1/',
    client_kwargs={'scope': 'user-read-email user-read-private user-top-read'},
)
# Used when we need to pull public data from spotify not pertaining to a specific user

#client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
#sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_client_credentials_token():
    client_id=(CLIENT_ID)
    client_secret=(CLIENT_SECRET)
    token_url = 'https://accounts.spotify.com/api/token'

    response = requests.post(token_url, auth=(client_id, client_secret), data={'grant_type': 'client_credentials'})

    if response.status_code == 200:
        token_info = response.json()
        return token_info['access_token']
    else:
        raise Exception("Failed to obtain token")
        
from app import routes, models #leave at bottom of init file
