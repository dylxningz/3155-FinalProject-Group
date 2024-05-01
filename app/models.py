from app import db
from flask_login import UserMixin
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    spotify_id = db.Column(db.String(120), unique=True, nullable=True)
    spotify_access_token = db.Column(db.String(255), nullable=True)
    spotify_refresh_token = db.Column(db.String(255), nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    posts = db.relationship('Post', backref='author', lazy=True)
    streams = db.relationship('Stream', backref='streamer', lazy=True)
    comments = db.relationship('Comment', backref='commenter', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'
    

class Song(db.Model):
    __tablename__ = 'song'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    uri = db.Column(db.String(), nullable=False, unique=True)
    name = db.Column(db.String(), nullable=False)
    album = db.Column(db.String(),  nullable=False)
    artist = db.Column(db.String(), nullable=False)

    song_streams = db.relationship('Stream', backref='song-stream', lazy=True)

    def __repr__(self):
        return '<Song %r>' % self.name  
     

class Stream(db.Model):
    __tablename__ = 'stream'
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
    time = db.Column(db.DateTime, nullable=False, unique=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, primary_key=True)

    def __repr__(self):
        return '<Stream %r>' % self.id


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_song_id = db.Column(db.String(), nullable=True) 
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    __tablename__ = "comment"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

