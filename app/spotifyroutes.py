from flask import Blueprint, request, redirect, url_for, session, flash, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import spotify, db
from app.spotify_utils import get_client_credentials_token, get_user_top_songs_artists
import requests

spotifyroutes = Blueprint('spotifyroutes', __name__)

@spotifyroutes.route('/login/spotify')
def login_spotify():
    redirect_uri = url_for('spotifyroutes.authorize_spotify', _external=True)
    return spotify.authorize_redirect(redirect_uri)

@spotifyroutes.route('/authorize/spotify')
def authorize_spotify():
    try:
        token = spotify.authorize_access_token()
        if not token:
            raise Exception("No token retrieved from Spotify")
        current_user.spotify_access_token = token['access_token']
        current_user.spotify_refresh_token = token.get('refresh_token', current_user.spotify_refresh_token)
        current_user.token_expiry = datetime.now() + timedelta(seconds=token['expires_in'])
        profile_response = requests.get('https://api.spotify.com/v1/me', headers={'Authorization': f'Bearer {token["access_token"]}'})
        if profile_response.ok:
            profile = profile_response.json()
            current_user.spotify_id = profile['id']
            db.session.commit()
            flash('Spotify account linked successfully!', 'success')
        else:
            db.session.rollback()
            flash('Failed to fetch Spotify profile information.', 'error')
    except Exception as e:
        flash(f'Failed to link Spotify account: {str(e)}', 'error')
    next_url = session.pop('next_url', url_for('profile.dashboard'))
    return redirect(next_url)

@spotifyroutes.route('/artist/<artist_id>')
def artist_page(artist_id):
    try:
        access_token = get_client_credentials_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        artist_response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=headers)
        top_tracks_response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US', headers=headers)
        albums_response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}/albums?market=US&limit=5', headers=headers)
        if artist_response.status_code == 200 and top_tracks_response.status_code == 200 and albums_response.status_code == 200:
            artist_info = artist_response.json()
            top_tracks = top_tracks_response.json()['tracks'][:5]  # Limit to top 5 tracks
            albums = albums_response.json()['items']
            return render_template('spotify/artist.html', artist=artist_info, top_tracks=top_tracks, albums=albums)
        else:
            flash('Failed to fetch artist information, top tracks, or albums from Spotify.', 'error')
            return redirect(url_for('spotifyroutes.index'))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('spotifyroutes.index'))

@spotifyroutes.route('/top-songs')
@login_required
def top_songs():
    try:
        access_token = get_client_credentials_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get('https://api.spotify.com/v1/playlists/37i9dQZEVXbLRQDuF5jeBp/tracks', headers=headers)
        if response.status_code == 200:
            top_songs = response.json()['items'][:50]  # Limit to top 50 songs
            user_top_songs, user_top_artists = get_user_top_songs_artists(current_user)
            return render_template('spotify/top_songs.html', top_songs=top_songs, user_top_songs=user_top_songs, user_top_artists=user_top_artists)
        else:
            flash('Failed to fetch top songs from Spotify.', 'error')
            return redirect(url_for('spotifyroutes.index'))
    except Exception as e:
        flash(str(e), 'error')