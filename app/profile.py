from flask import Blueprint, render_template
from app.models import User, Post , Song, Stream, PostLike
from app.spotify_utils import get_user_top_songs_artists, get_spotify_profile_picture
import requests
from app.models import User, Post
from app.spotify_utils import get_user_top_songs_artists, get_spotify_profile_picture, get_current_track_info
from flask import flash, redirect, url_for
from flask_login import current_user, login_required
from app.spotify_utils import get_spotify_access_token, get_user_recently_played_songs
from app import db
from sqlalchemy import func, distinct
from flask import request
import re

profile = Blueprint('profile', __name__)

@profile.route('/users/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user_top_songs, user_top_artists = get_user_top_songs_artists(user)
        profile_picture = get_spotify_profile_picture(user)
        recent_posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).limit(3).all()

        return render_template(
            'user_profile.html',
            user=user,
            username=username,
            top_songs=user_top_songs,
            top_artists=user_top_artists,
            profile_picture=profile_picture,
            recent_posts=recent_posts
        )
    else:
        flash('User not found.', 'error')
        return redirect(url_for('profile.dashboard'))
    
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


@profile.route('/search', methods=['GET'])
def search():
    search_query = request.args.get('search_query')
    if search_query:
        matching_user = User.query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%')) |
            (User.spotify_id.ilike(f'%{search_query}%'))
        ).first()

        if matching_user:
            return redirect(url_for('profile.user_profile', username=matching_user.username))

    flash('User not found.', 'error')
    return redirect(url_for('profile.user_profile', username='current_user.username'))

@profile.route('/users/', methods=['GET'])
def users_search():
    request_path = request.path
    match = re.match(r"/users/\?search_query=(\w+)", request_path)
    if match:
        search_query = match.group(1)
        return redirect(url_for('profile.user_profile', username=search_query))

    flash('Invalid search query.', 'error')
    return redirect(url_for('profile.user_profile', username='current_user.username'))

@profile.route('/update_about_me', methods=['POST'])
@login_required
def update_about_me():
    about_me = request.form.get('about_me')
    current_user.about_me = about_me
    db.session.commit()
    flash('About Me updated successfully.', 'success')
    return redirect(url_for('profile.settings'))
