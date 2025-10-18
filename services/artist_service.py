#
#   Orchestr8r – A Prototype Music Recommendation System using Microservices 
#   
#   Artist Service: Manages artist data, including searching for artists, retrieving artist details, and storing artist information.
#
#   This script was created in Microsoft VSCode and Claude.ai was referenced/utilized in the script development
#

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from shared.database import get_db  # Remove create_tables import
from shared.models import Artist, Album
from services.musicbrainz_service import MusicBrainzService
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Artist Service", version="1.0.0")
musicbrainz = MusicBrainzService()

# Remove this line - tables will be created by init service
# create_tables()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "artist-service"}

@app.get("/artists/search")
def search_artists(query: str, limit: int = 25, db: Session = Depends(get_db)):
    """Search artists from MusicBrainz and optionally save to DB"""
    try:
        artists_data = musicbrainz.search_artists(query, limit)
        
        saved_artists = []
        for artist_data in artists_data:
            # Check if artist already exists
            existing_artist = db.query(Artist).filter(Artist.id == artist_data['id']).first()
            
            if not existing_artist:
                # Save new artist
                artist = Artist(
                    id=artist_data['id'],
                    name=artist_data['name'],
                    sort_name=artist_data.get('sort-name', ''),
                    type=artist_data.get('type', ''),
                    country=artist_data.get('country', ''),
                    begin_date=artist_data.get('life-span', {}).get('begin', ''),
                    end_date=artist_data.get('life-span', {}).get('end', '')
                )
                db.add(artist)
                db.commit()
                saved_artists.append(artist_data)
            else:
                saved_artists.append(artist_data)
        
        return {"artists": saved_artists}
    except Exception as e:
        logger.error(f"Error in search_artists: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/artists/{artist_id}")
def get_artist(artist_id: str, db: Session = Depends(get_db)):
    """Get artist from local DB or fetch from MusicBrainz"""
    try:
        # Try local DB first
        artist = db.query(Artist).filter(Artist.id == artist_id).first()
        
        if not artist:
            # Fetch from MusicBrainz
            artist_data = musicbrainz.get_artist(artist_id)
            if not artist_data:
                raise HTTPException(status_code=404, detail="Artist not found")
            
            # Save to DB
            artist = Artist(
                id=artist_data['id'],
                name=artist_data['name'],
                sort_name=artist_data.get('sort-name', ''),
                type=artist_data.get('type', ''),
                country=artist_data.get('country', ''),
                begin_date=artist_data.get('life-span', {}).get('begin', ''),
                end_date=artist_data.get('life-span', {}).get('end', '')
            )
            db.add(artist)
            db.commit()
        
        return {
            "id": artist.id,
            "name": artist.name,
            "sort_name": artist.sort_name,
            "type": artist.type,
            "country": artist.country,
            "begin_date": artist.begin_date,
            "end_date": artist.end_date
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_artist: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/artists")
def list_artists(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List artists from local database"""
    try:
        # Order by created_at DESC to get most recent first
        artists = db.query(Artist).order_by(Artist.created_at.desc()).offset(skip).limit(limit).all()
        return {"artists": [{"id": a.id, "name": a.name, "country": a.country, "created_at": str(a.created_at)} for a in artists]}
    except Exception as e:
        logger.error(f"Error in list_artists: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
