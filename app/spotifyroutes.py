from flask import Blueprint, request, redirect, url_for, session, flash, render_template, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import spotify, db
from app.spotify_utils import get_client_credentials_token, get_user_top_songs_artists, spotify_search_tracks, get_user_recently_played_songs
import requests
import logging
from .models import Song, Stream
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

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

@spotifyroutes.route('/spotify/search')
def spotify_search():
    query = request.args.get('q')
    logging.debug(f"Search query received: {query}")  # Log the incoming query
    if query:
        try:
            results = spotify_search_tracks(query)
            logging.debug(f"Spotify search results: {results}")  # Log the results from Spotify
            return jsonify(results)
        except Exception as e:
            logging.error(f"Failed to search Spotify: {e}")
            return jsonify({'error': 'Failed to fetch data from Spotify'}), 500
    return jsonify({'tracks': {'items': []}})

def spotify_search_tracks(query):
    import requests
    access_token = get_client_credentials_token()  # Correct the variable name here
    url = "https://api.spotify.com/v1/search"
    headers = {
        "Authorization": f"Bearer {access_token}"  # Use f-string to correctly include the token
    }
    params = {
        "q": query,
        "type": "track",
        "limit": 10
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


@spotifyroutes.route('/recently-played')
@login_required
def recently_played():
    recently_played = get_user_recently_played_songs(current_user)
    print("Recently Played:", recently_played)  # Log fetched data
    items = recently_played['items']

    for item in items:
        track = item['track']
        album = track['album']
        artist = track['album']['artists'][0]
        new_song = Song(uri=track['uri'], name=track['name'], album=album['name'], artist=artist['name'])
        new_stream = Stream(time=item['played_at'], user_id=current_user.id)

        try:
            db.session.add(new_song)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            print("Song already exists:", track['uri'])  # Log duplicate entry

        existing_song = Song.query.filter_by(uri=track['uri']).first()
        if existing_song:
            new_stream.song_id = existing_song.id

            try:
                db.session.add(new_stream)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                print("Failed to add stream for:", track['uri'])  # Log failed stream addition

    return 'Data processed'

       
            

   

@spotifyroutes.route('/user-streams')
@login_required
def user_streams():
    # Define the maximum number of results to return
    limit_results = 5

    # Subquery for song frequency
    subquery = db.session.query(
        Stream.song_id,
        func.count(Stream.song_id).label('frequency')
    ).filter(
        Stream.user_id == current_user.id
    ).group_by(
        Stream.song_id
    ).subquery()

    # Main query for songs
    query_result = db.session.query(
        Song,
        subquery.c.frequency
    ).join(
        subquery, Song.id == subquery.c.song_id
    ).order_by(
        subquery.c.frequency.desc()
    ).limit(limit_results).all()

    songs = [{"id": song.id, "title": song.name, "frequency": frequency or 0} for song, frequency in query_result]

    # Query for artist frequency
    artist_freq = db.session.query(
        Song.artist,
        func.count(Stream.song_id).label('total_streams')
    ).join(
        Stream,
        Song.id == Stream.song_id
    ).filter(
        Stream.user_id == current_user.id
    ).group_by(
        Song.artist
    ).order_by(
        func.count(Stream.song_id).desc()
    ).limit(limit_results).all()

    artists = [{"artist": artist, "total_streams": total_streams} for artist, total_streams in artist_freq]

    return jsonify({"songs": songs, "artists": artists})

        
