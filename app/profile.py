from flask import Blueprint, render_template
from app.models import User
from app.spotify_utils import get_user_top_songs_artists, get_spotify_profile_picture
import requests
from flask import flash, redirect, url_for
from flask_login import current_user, login_required
from app.spotify_utils import get_spotify_access_token
from app import db

profile = Blueprint('profile', __name__)

@profile.route('/users/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first()
    user_top_songs, user_top_artists = get_user_top_songs_artists(user)
    profile_picture = get_spotify_profile_picture(user)
    spotify_info = None
    if user and user.spotify_access_token:
        headers = {'Authorization': f'Bearer {user.spotify_access_token}'}
        response = requests.get('https://api.spotify.com/v1/me/player/currently-playing', headers=headers)
        current_song_data = response.json().get('item')
        if current_song_data:
            current_song = {
                'name': current_song_data['name'],
                'artist': current_song_data['artists'][0]['name'],
                'cover': current_song_data['album']['images'][0]['url'] if current_song_data['album']['images'] else None,
                'timestamp': current_song_data['timestamp'],
                'end_time': current_song_data['end_time']
            }
            spotify_info = {
                'is_currently_listening': True,
                'current_song': current_song
            }
        else:
            spotify_info = {
                'is_currently_listening': False
            }
    if user:
        return render_template(
            'user_profile.html',
            user=user,
            username=username,
            top_songs=user_top_songs,
            top_artists=user_top_artists,
            profile_picture=profile_picture,
            spotify_info=spotify_info)
    else:
        flash('User not found.', 'error')
        return redirect(url_for('index'))
    
@profile.route('/dashboard')
@login_required
def dashboard():
    access_token = get_spotify_access_token(current_user)
    top_songs, top_artists = get_user_top_songs_artists(current_user)
    return render_template('dashboard.html', username=current_user.username, top_songs=top_songs, top_artists=top_artists)

@profile.route('/habits')
@login_required
def habits():
    return render_template('habits.html')

@profile.route('/settings')
@login_required
def settings():
    return render_template('settings.html')