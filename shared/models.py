from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Artist(Base):
    __tablename__ = 'artists'
    
    id = Column(String, primary_key=True)  # MusicBrainz ID
    name = Column(String(255), nullable=False)
    sort_name = Column(String(255))
    type = Column(String(50))
    country = Column(String(10))
    begin_date = Column(String(20))
    end_date = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    albums = relationship("Album", back_populates="artist")

class Album(Base):
    __tablename__ = 'albums'
    
    id = Column(String, primary_key=True)  # MusicBrainz ID
    title = Column(String(255), nullable=False)
    artist_id = Column(String, ForeignKey('artists.id'))
    release_date = Column(String(20))
    status = Column(String(50))
    country = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    artist = relationship("Artist", back_populates="albums")
    tracks = relationship("Track", back_populates="album")

class Track(Base):
    __tablename__ = 'tracks'
    
    id = Column(String, primary_key=True)  # MusicBrainz ID
    title = Column(String(255), nullable=False)
    album_id = Column(String, ForeignKey('albums.id'))
    track_number = Column(Integer)
    length = Column(Integer)  # in milliseconds
    created_at = Column(DateTime, default=datetime.utcnow)
    
    album = relationship("Album", back_populates="tracks")

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    favorite_genres = Column(Text)  # JSON string of genres
    favorite_artists = Column(Text)  # JSON string of artist IDs
    listening_history = Column(Text)  # JSON string of track/artist interactions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user_profiles.id'))
    track_id = Column(String)  # MusicBrainz recording ID
    artist_id = Column(String)  # MusicBrainz artist ID
    track_title = Column(String(255))
    artist_name = Column(String(255))
    score = Column(Integer)  # Recommendation score 1-100
    recommendation_type = Column(String(50))  # 'profile', 'query', 'similar'
    created_at = Column(DateTime, default=datetime.utcnow)

class ListeningHistory(Base):
    __tablename__ = 'listening_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user_profiles.id'))
    track_id = Column(String)
    artist_id = Column(String)
    played_at = Column(DateTime, default=datetime.utcnow)
    interaction_type = Column(String(20))  # 'played', 'liked', 'saved', 'skipped'
