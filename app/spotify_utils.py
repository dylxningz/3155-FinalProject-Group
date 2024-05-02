from datetime import datetime, timedelta
import pytz
from app.models import User,Song,Stream
import requests
from db_secrets import CLIENT_ID, CLIENT_SECRET
from app import db
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

def is_token_expired(user):
    utc = pytz.UTC
    current_time = datetime.now(pytz.utc)
    if user.token_expiry:
        if user.token_expiry.tzinfo is None or user.token_expiry.tzinfo.utcoffset(user.token_expiry) is None:
            user.token_expiry = utc.localize(user.token_expiry)
        return current_time >= user.token_expiry - timedelta(minutes=5)
    return True

def refresh_spotify_token(user_id):
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")
    if user.spotify_refresh_token:
        refresh_url = 'https://accounts.spotify.com/api/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': user.spotify_refresh_token,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        response = requests.post(refresh_url, headers=headers, data=data)
        if response.status_code == 200:
            token_info = response.json()
            user.spotify_access_token = token_info['access_token']
            if 'expires_in' in token_info:
                user.token_expiry = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
            db.session.commit()

            # Fetch and save recently played songs immediately after refreshing token
            update_recently_played_songs(user)

            return token_info['access_token']
        else:
            raise Exception("Failed to refresh token")
    return None

def update_recently_played_songs(user):
    recently_played = get_user_recently_played_songs(user)
    if recently_played and 'items' in recently_played:
        for item in recently_played['items']:
            track = item['track']
            album = track['album']
            artist = track['album']['artists'][0]
            # Extract track ID from URI for potential use
            uri_parts = track['uri'].split(':')
            track_id = uri_parts[2] if len(uri_parts) > 2 else None

            new_song = Song(uri=track['uri'], name=track['name'], album=album['name'], artist=artist['name'])
            new_stream = Stream(time=item['played_at'], user_id=user.id)

            # Avoid duplication of song records
            existing_song = Song.query.filter_by(uri=track['uri']).first()
            if not existing_song:
                db.session.add(new_song)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()

            # Attach song_id to new_stream
            existing_song = existing_song or Song.query.filter_by(uri=track['uri']).first()
            new_stream.song_id = existing_song.id
            db.session.add(new_stream)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

            

def get_spotify_access_token(user):
    if is_token_expired(user):
        return refresh_spotify_token(user.id)
    return user.spotify_access_token

def get_user_top_songs_artists(user):
    if is_token_expired(user):
        new_token = refresh_spotify_token(user.id)
        if not new_token:
            # Handle the case where the token refresh fails
            return None, None

    headers = {'Authorization': f'Bearer {user.spotify_access_token}'}
    tracks_response = requests.get('https://api.spotify.com/v1/me/top/tracks?limit=5', headers=headers)
    user_top_songs = []
    user_top_artists = []
    if tracks_response.ok:
        tracks_data = tracks_response.json()
        user_top_songs = [{
            'name': track['name'],
            'artists': [{'name': artist['name'], 'id': artist['id']} for artist in track['artists']],
            'cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'rank': idx + 1
        } for idx, track in enumerate(tracks_data['items'])]

    artists_response = requests.get('https://api.spotify.com/v1/me/top/artists?limit=5', headers=headers)
    if artists_response.ok:
        artists_data = artists_response.json()
        user_top_artists = [{
            'name': artist['name'],
            'id': artist['id'],
            'cover': artist['images'][0]['url'] if artist['images'] else None,
            'genre': ', '.join(artist['genres'][:2]),  # Optionally show up to 2 genres
            'rank': idx + 1
        } for idx, artist in enumerate(artists_data['items'])]

    return user_top_songs, user_top_artists

def get_spotify_profile_picture(user):
    headers = {'Authorization': f'Bearer {user.spotify_access_token}'}
    response = requests.get('https://api.spotify.com/v1/me', headers=headers)
    if response.status_code == 200:
        profile_data = response.json()
        if 'images' in profile_data and len(profile_data['images']) > 0:
            profile_picture_url = profile_data['images'][0]['url']
            for image in profile_data['images']:
                if image['width'] > 200 and image['height'] > 200:
                    profile_picture_url = image['url']
                    break
            return profile_picture_url
    return None

def get_client_credentials_token():
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    token_url = 'https://accounts.spotify.com/api/token'
    response = requests.post(token_url, auth=(client_id, client_secret), data={'grant_type': 'client_credentials'})
    if response.status_code == 200:
        token_info = response.json()
        return token_info['access_token']
    else:
        raise Exception("Failed to obtain token")
    
def spotify_search_tracks(query, access_token):
    """
    Search for tracks on Spotify using a given query.
    
    Args:
        query (str): The search term.
        access_token (str): Spotify API access token.
    
    Returns:
        dict: JSON response containing search results.
    """
    url = "https://api.spotify.com/v1/search"
    headers = {
        "Authorization": f"Bearer {access_token}"
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
        return {"tracks": {"items": []}}
    

def get_song_details(song_id):
    access_token = get_client_credentials_token()
    url = f"https://api.spotify.com/v1/tracks/{song_id}"
    headers = { "Authorization": f"Bearer {access_token}" }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return {
            'name': data['name'],
            'artists': [{'name': artist['name'], 'id': artist['id']} for artist in data['artists']],
            'album_cover': data['album']['images'][0]['url']
        }
    else:
        response.raise_for_status()

def get_user_recently_played_songs(user):
    if not user.spotify_access_token:
        return None  # or handle appropriately if no token is available

    headers = {'Authorization': f'Bearer {user.spotify_access_token}'}
    response = requests.get('https://api.spotify.com/v1/me/player/recently-played?limit=30', headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        # Log the error status and message
        print(f"Failed to fetch recently played songs: Status {response.status_code}, Message: {response.text}")
        return None
