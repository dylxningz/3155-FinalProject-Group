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

    def __repr__(self):
        return f'<User {self.username}>'

class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return '<Genre %r>' % self.name

class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return '<Artist %r>' % self.name

class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    release_date = db.Column(db.Date, nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=False)
    artist = db.relationship('Artist', backref=db.backref('albums', lazy=True))

    def __repr__(self):
        return '<Album %r>' % self.title

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    album_id = db.Column(db.Integer, db.ForeignKey('album.id'), nullable=False)
    album = db.relationship('Album', backref=db.backref('songs', lazy=True))
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), nullable=True)
    genre = db.relationship('Genre', backref=db.backref('songs', lazy=True))
    duration = db.Column(db.Integer, nullable=False)  # Duration in seconds

    def __repr__(self):
        return '<Song %r>' % self.title



class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
