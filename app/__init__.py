from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
import requests
from flask_login import LoginManager
from db_secrets import DB_URI, CLIENT_ID, CLIENT_SECRET

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecret'
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'  
login_manager.login_message_category = 'info'

oauth = OAuth(app)
spotify = oauth.register(
    name="spotify",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
    api_base_url='https://api.spotify.com/v1/',
    client_kwargs={'scope': 'user-read-email user-read-private user-top-read'}
)

@login_manager.user_loader
def load_user(user_id):
    from app.models import User 
    return User.query.get(int(user_id))


from app.auth import auth as auth_blueprint
from app.community import community as community_blueprint
from app.errors import errors as errors_blueprint
from app.profile import profile as profile_blueprint
from app.spotifyroutes import spotifyroutes as spotifyroutes_blueprint
from app.main import main as main_blueprint
app.register_blueprint(main_blueprint)


# Register Blueprints
app.register_blueprint(auth_blueprint)
app.register_blueprint(community_blueprint)
app.register_blueprint(errors_blueprint)
app.register_blueprint(profile_blueprint)
app.register_blueprint(spotifyroutes_blueprint)