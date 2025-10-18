#
#   Orchestr8r – A Prototype Music Recommendation System using Microservices 
#   
#   Album Service: Manages album data, including searching for albums, retrieving album details, and storing album information along with associated tracks.
#
#   This script was created in Microsoft VSCode and Claude.ai was referenced/utilized in the script development
#

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import Album, Artist, Track
from services.musicbrainz_service import MusicBrainzService
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Album Service", version="1.0.0")
musicbrainz = MusicBrainzService()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "album-service"}

@app.get("/albums/search")
def search_albums(artist_name: str = "", album_title: str = "", limit: int = 25, db: Session = Depends(get_db)):
    """Search albums from MusicBrainz and save with tracks"""
    releases = musicbrainz.search_releases(artist_name, album_title, limit)
    
    saved_albums = []
    for release in releases:
        try:
            # Check if album already exists
            existing_album = db.query(Album).filter(Album.id == release['id']).first()
            
            if not existing_album:
                # Get or create artist
                artist_credit = release.get('artist-credit', [{}])[0].get('artist', {})
                artist_id = artist_credit.get('id')
                
                if artist_id:
                    artist = db.query(Artist).filter(Artist.id == artist_id).first()
                    if not artist:
                        artist = Artist(
                            id=artist_id,
                            name=artist_credit.get('name', ''),
                            sort_name=artist_credit.get('sort-name', '')
                        )
                        db.add(artist)
                    
                    # Save album
                    album = Album(
                        id=release['id'],
                        title=release['title'],
                        artist_id=artist_id,
                        release_date=release.get('date', ''),
                        status=release.get('status', ''),
                        country=release.get('country', '')
                    )
                    db.add(album)
                    db.commit()
                    
                    # Now fetch and save tracks for this album
                    logger.info(f"Fetching tracks for album: {release['title']}")
                    release_details = musicbrainz.get_release(release['id'], "recordings")
                    
                    if release_details and 'media' in release_details:
                        track_count = 0
                        for medium in release_details['media']:
                            for track_data in medium.get('tracks', []):
                                recording = track_data.get('recording', {})
                                track_id = recording.get('id')
                                
                                if track_id:
                                    # Check if track already exists
                                    existing_track = db.query(Track).filter(Track.id == track_id).first()
                                    if not existing_track:
                                        track = Track(
                                            id=track_id,
                                            title=recording.get('title', 'Unknown'),
                                            album_id=release['id'],
                                            track_number=track_data.get('position', 0),
                                            length=recording.get('length', 0)
                                        )
                                        db.add(track)
                                        track_count += 1
                        
                        if track_count > 0:
                            db.commit()
                            logger.info(f"Saved {track_count} tracks for album {release['title']}")
            
            saved_albums.append(release)
            
        except Exception as e:
            logger.error(f"Error processing album {release.get('title', 'Unknown')}: {e}")
            db.rollback()
            continue
    
    return {"albums": saved_albums}

@app.get("/albums/{album_id}")
def get_album(album_id: str, db: Session = Depends(get_db)):
    """Get album details with tracks"""
    album = db.query(Album).filter(Album.id == album_id).first()
    
    if not album:
        # Fetch from MusicBrainz
        logger.info(f"Album {album_id} not in database, fetching from MusicBrainz...")
        release_data = musicbrainz.get_release(album_id, "recordings+artist-credits")
        
        if not release_data:
            raise HTTPException(status_code=404, detail="Album not found")
        
        try:
            # Get or create artist
            artist_credit = release_data.get('artist-credit', [{}])[0].get('artist', {})
            artist_id = artist_credit.get('id')
            
            if not artist_id:
                raise HTTPException(status_code=400, detail="No artist information available")
            
            artist = db.query(Artist).filter(Artist.id == artist_id).first()
            if not artist:
                artist = Artist(
                    id=artist_id,
                    name=artist_credit.get('name', ''),
                    sort_name=artist_credit.get('sort-name', '')
                )
                db.add(artist)
            
            # Save album
            album = Album(
                id=release_data['id'],
                title=release_data['title'],
                artist_id=artist_id,
                release_date=release_data.get('date', ''),
                status=release_data.get('status', ''),
                country=release_data.get('country', '')
            )
            db.add(album)
            db.commit()
            
            # Save tracks
            if 'media' in release_data:
                track_count = 0
                for medium in release_data['media']:
                    for track_data in medium.get('tracks', []):
                        recording = track_data.get('recording', {})
                        track_id = recording.get('id')
                        
                        if track_id:
                            existing_track = db.query(Track).filter(Track.id == track_id).first()
                            if not existing_track:
                                track = Track(
                                    id=track_id,
                                    title=recording.get('title', 'Unknown'),
                                    album_id=release_data['id'],
                                    track_number=track_data.get('position', 0),
                                    length=recording.get('length', 0)
                                )
                                db.add(track)
                                track_count += 1
                
                if track_count > 0:
                    db.commit()
                    logger.info(f"Saved {track_count} tracks for album {release_data['title']}")
        
        except Exception as e:
            logger.error(f"Error saving album and tracks: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error processing album: {str(e)}")
    
    # Get tracks from database
    tracks = db.query(Track).filter(Track.album_id == album_id).order_by(Track.track_number).all()
    
    return {
        "id": album.id,
        "title": album.title,
        "artist_id": album.artist_id,
        "release_date": album.release_date,
        "status": album.status,
        "country": album.country,
        "track_count": len(tracks),
        "tracks": [
            {
                "id": t.id,
                "title": t.title,
                "track_number": t.track_number,
                "length": t.length
            } for t in tracks
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)