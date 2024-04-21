from app import db
from flask_login import UserMixin
from datetime import datetime, timezone

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    spotify_id = db.Column(db.String(120), unique=True, nullable=True)
    spotify_access_token = db.Column(db.String(255), nullable=True)
    spotify_refresh_token = db.Column(db.String(255), nullable=True)

    posts = db.relationship('Post', backref='author', lazy=True)
    streams = db.relationship('Stream', backref='streamer', lazy=True)
    comments = db.relationship('Comment', backref='commenter', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Song(db.Model):
    __tablename__ = 'song'
    id = db.Column(db.Integer, primary_key=True)
    spotify_song_id = db.Column(db.String(22), nullable=False)
    num_streams = db.Column(db.Integer, nullable=False)
    # Assuming songs are related to streams
    streams = db.relationship('Stream', backref='song', lazy=True)

    def __repr__(self):
        return '<Song %r>' % self.spotify_song_id

class Stream(db.Model):
    __tablename__ = 'stream'
    id = db.Column(db.Integer, db.ForeignKey('song.id'), primary_key=True)
    spotify_song_id = db.Column(db.String(22))
    time = db.Column(db.Float, nullable=False, unique=True)
    user = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return '<Stream %r>' % self.id

class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    # Reintegrating Album as the relationship makes sense for an Artist
    albums = db.relationship('Album', backref='artist', lazy=True)

    def __repr__(self):
        return '<Artist %r>' % self.name

class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    release_date = db.Column(db.Date, nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=False)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

