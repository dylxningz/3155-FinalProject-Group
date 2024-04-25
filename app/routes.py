from flask import render_template, redirect, url_for, session, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_required, login_user, logout_user
from app import app, db, spotify, get_client_credentials_token
from app.models import User, Post, Comment  
from app.forms import SignupForm, LoginForm, PostForm 
import requests
from sqlalchemy import desc


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



def refresh_spotify_token(user_id):
    user = User.query.get(user_id)
    if user.spotify_refresh_token:
        # Use Spotify's OAuth token refresh endpoint
        token_info = spotify.refresh_token(user.spotify_refresh_token)
        user.spotify_access_token = token_info['access_token']
        db.session.commit()
        return token_info['access_token']
    return None


# fetches top artists and songs (5 of each) for a user At least I think its 5 of each, might be more :shrug:
# separated from the dashboard route to make it easier to reuse in other routes
def get_user_top_songs_artists(user):
    user_top_songs = []
    user_top_artists = []

    if user.spotify_access_token:
        headers = {'Authorization': f'Bearer {user.spotify_access_token}'}

        # Fetch top tracks
        tracks_response = requests.get('https://api.spotify.com/v1/me/top/tracks?limit=5', headers=headers)
        if tracks_response.ok:
            tracks_data = tracks_response.json()
            user_top_songs = [
                {
                    'name': track['name'],
                    'artists': [{'name': artist['name'], 'id': artist['id']} for artist in track['artists']],
                    'cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'rank': idx + 1
                }
                for idx, track in enumerate(tracks_data['items'])
            ]

        # Fetch top artists
        artists_response = requests.get('https://api.spotify.com/v1/me/top/artists?limit=5', headers=headers)
        if artists_response.ok:
            artists_data = artists_response.json()
            user_top_artists = [
                {
                    'name': artist['name'],
                    'id': artist['id'],
                    'cover': artist['images'][0]['url'] if artist['images'] else None,
                    'genre': ', '.join(artist['genres'][:2]),  # Optionally show up to 2 genres
                    'rank': idx + 1
                }
                for idx, artist in enumerate(artists_data['items'])
            ]
    return user_top_songs, user_top_artists


def get_spotify_profile_picture(user):
    headers = {
        'Authorization': f'Bearer {user.spotify_access_token}'
    }
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
    return None # Default profile picture if not found (replace None with suitable image later)

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
        user = User.query.filter((User.username == form.username_or_email.data) | (User.email == form.username_or_email.data)).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)  
            flash('Login successful.', 'success')
            next_page = request.args.get('next')  
            return redirect(next_page or url_for('dashboard'))  
        else:
            flash('Login Unsuccessful. Please check username/email and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    top_songs, top_artists = get_user_top_songs_artists(current_user)

    return render_template(
        'dashboard.html',
        username=current_user.username,
        top_songs=top_songs,
        top_artists=top_artists)

@app.get('/habits')
@login_required
def habits():
    return render_template('habits.html')



#SPOTIFY ROUTES
# Spotify login route authentication required
@app.route('/login/spotify')

def login_spotify():
    redirect_uri = url_for('authorize_spotify', _external=True)
    return spotify.authorize_redirect(redirect_uri)

# Spotify callback route
@app.route('/authorize/spotify')
def authorize_spotify():
    try:
        # Exchange the code for an access token
        token = spotify.authorize_access_token()
        
        # Save the access token in the session for immediate use
        session['access_token'] = token['access_token']
        
        # Get the user's Spotify profile information to obtain their Spotify ID
        resp = requests.get('https://api.spotify.com/v1/me', headers={'Authorization': f'Bearer {token["access_token"]}'})
        if resp.ok:
            profile = resp.json()
            spotify_id = profile['id']

            # Update the current user's profile with Spotify details
            current_user.spotify_id = spotify_id
            current_user.spotify_access_token = token['access_token']
            if 'refresh_token' in token:
                current_user.spotify_refresh_token = token['refresh_token']
            db.session.commit()

            flash('Spotify account linked successfully!', 'success')
        else:
            flash('Failed to fetch Spotify profile information.', 'error')
    except Exception as e:
        flash(f'Failed to link Spotify account: {str(e)}', 'error')
    # Redirect to the next URL or default to the dashboard
    next_url = session.pop('next_url', None)
    return redirect(next_url if next_url else url_for('dashboard'))


@app.get('/terms')
def terms():
    return render_template('terms.html')

#####COMMUNITY PAGE#####
@app.get('/community')
def community_get():
    search_query = request.args.get('search', '')
    if search_query:
        # Using ILIKE for case-insensitive search, assuming you are using PostgreSQL
        posts = Post.query.filter(
            (Post.title.ilike(f'%{search_query}%')) | 
            (Post.content.ilike(f'%{search_query}%')) | 
            (Post.author.has(User.username.ilike(f'%{search_query}%')))
        ).order_by(Post.date_posted.desc()).all()
    else:
        # Fetch all posts and order them by descending date_posted if no search query is provided
        posts = db.session.query(Post).order_by(Post.date_posted.desc()).all()

    return render_template('community.html', posts=posts)
@app.post('/community')
def community_post():
    title = request.form['title']
    content = request.form['content']
    author = current_user.id  # current_user should have the id directly accessible

    # Create and save a new post using the correct model name 'Post'
    post = Post(title=title, content=content, author_id=author)
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('community_get'))


#####POST PAGE######
@app.get('/community/<post_id>')
def view_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    comments = Comment.query.filter_by(post_id=post_id).order_by(desc(Comment.date_posted)).all()
    return render_template('post.html', post=post, comments=comments, user=current_user)


@app.post('/community/<post_id>')
def post_comment(post_id):
    content = request.form['comment']
    author_id = current_user.id
    comment = Comment(content=content,post_id=post_id,author_id=author_id)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('view_post', post_id=post_id))


@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        return render_template('create_post.html', form=form)


@app.route('/profile')
@login_required
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


@app.route('/users/<username>')
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
                'cover': current_song_data['album']['images'][0]['url'] if current_song_data['album'][
                    'images'] else None,
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