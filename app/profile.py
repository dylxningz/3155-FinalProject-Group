from flask import Blueprint, render_template
from app.models import User, Post , Song, Stream, PostLike
from app.spotify_utils import get_user_top_songs_artists, get_spotify_profile_picture
import requests
from flask import flash, redirect, url_for
from flask_login import current_user, login_required
from app.spotify_utils import get_spotify_access_token, get_user_recently_played_songs
from app import db
from sqlalchemy import func, distinct

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
    user_posts = Post.query.filter_by(author_id=current_user.id).order_by(Post.date_posted.desc()).all()
    liked_posts = Post.query.join(PostLike, (PostLike.post_id == Post.id)).filter(PostLike.user_id == current_user.id).all()
    recently_played_data = get_user_recently_played_songs(current_user)

    recently_played_songs = []
    if recently_played_data and 'items' in recently_played_data:
        for item in recently_played_data['items'][:5]:  # Limit to the last 5 songs
            track = item['track']
            track_id = track['uri'].split(':')[2]  # Extract the Spotify track ID from the URI
            song = {
                'id': track_id,  # Include the Spotify track ID
                'name': track['name'],
                'artist': ', '.join(artist['name'] for artist in track['artists']),
                'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'played_at': item['played_at']
            }
            recently_played_songs.append(song)

    return render_template('dashboard.html', username=current_user.username, top_songs=top_songs, top_artists=top_artists,
                           user_posts=user_posts, liked_posts=liked_posts, recently_played_songs=recently_played_songs)


@profile.route('/habits')
@login_required
def habits():
    top_songs = get_top_songs(current_user.id)
    top_artists = get_top_artists(current_user.id)
    
    return render_template('habits.html', top_songs=top_songs, top_artists=top_artists)

def get_top_songs(user_id):
    """Retrieve the top 5 songs based on the number of times they have been played by the user."""
    query = db.session.query(
        Song.name,
        Song.uri,
        func.count(Stream.time).label('plays')
    ).join(Stream, Stream.song_id == Song.id
    ).filter(Stream.user_id == user_id
    ).group_by(Song.id
    ).order_by(func.count(Stream.time).desc()
    ).limit(5).all()

    return [{'name': name, 'uri': uri, 'plays': plays, 'rank': idx + 1}
            for idx, (name, uri, plays) in enumerate(query)]

def get_top_artists(user_id):
    """Retrieve the top 5 artists based on the number of different songs played by the user."""
    query = db.session.query(
        Song.artist,
        func.count(distinct(Song.id)).label('song_count')
    ).join(Stream, Stream.song_id == Song.id
    ).filter(Stream.user_id == user_id
    ).group_by(Song.artist
    ).order_by(func.count(distinct(Song.id)).desc()
    ).limit(5).all()



    return [{'artist': artist, 'song_count': song_count}
            for artist, song_count in query]


@profile.route('/settings')
@login_required
def settings():
    return render_template('settings.html')