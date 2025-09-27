from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from shared.database import get_db, create_tables
from shared.models import Album, Artist, Track
from services.musicbrainz_service import MusicBrainzService
import uvicorn

app = FastAPI(title="Album Service", version="1.0.0")
musicbrainz = MusicBrainzService()

create_tables()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "album-service"}

@app.get("/albums/search")
def search_albums(artist_name: str = "", album_title: str = "", limit: int = 25, db: Session = Depends(get_db)):
    """Search albums from MusicBrainz"""
    releases = musicbrainz.search_releases(artist_name, album_title, limit)
    
    saved_albums = []
    for release in releases:
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
        
        saved_albums.append(release)
    
    return {"albums": saved_albums}

@app.get("/albums/{album_id}")
def get_album(album_id: str, db: Session = Depends(get_db)):
    """Get album details with tracks"""
    album = db.query(Album).filter(Album.id == album_id).first()
    
    if not album:
        # Fetch from MusicBrainz
        release_data = musicbrainz.get_release(album_id, "recordings+artist-credits")
        if not release_data:
            raise HTTPException(status_code=404, detail="Album not found")
        
        # Save album and tracks logic here...
        # (Implementation similar to search_albums)
    
    # Get tracks
    tracks = db.query(Track).filter(Track.album_id == album_id).all()
    
    return {
        "id": album.id,
        "title": album.title,
        "artist_id": album.artist_id,
        "release_date": album.release_date,
        "tracks": [{"id": t.id, "title": t.title, "track_number": t.track_number} for t in tracks]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
