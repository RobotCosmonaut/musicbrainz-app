#
#   Orchestr8r – A Prototype Music Recommendation System using Microservices 
#   
#   Recommendation Service: Provides music recommendations with artist diversity based on user queries and profiles.
#
#   This script was created in Microsoft VSCode and Claude.ai was referenced/utilized in the script development
#

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import UserProfile
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn
import logging
import requests
import time
import json
import os
from typing import List, Dict, Set, Optional
from collections import defaultdict
import random
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/musicbrainz")
    return create_engine(DATABASE_URL)

app = FastAPI(title="Diverse Recommendation Service", version="2.5.0")

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

class ProfileData(BaseModel):
    """
    Model for user profile data received in JSON request body.
    
    When the gateway sends:
    {
        "favorite_genres": ["rock", "jazz"],
        "favorite_artists": ["id1", "id2"]
    }
    
    FastAPI automatically converts it into a ProfileData object.
    """
    favorite_genres: List[str] = []
    favorite_artists: List[str] = []

class DiverseMusicBrainzClient:
    def __init__(self):
        self.base_url = "https://musicbrainz.org/ws/2"
        self.headers = {'User-Agent': 'MusicBrainzApp/1.0'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_recordings_diverse(self, query: str, limit: int = 20) -> List[Dict]:
        try:
            logger.info(f"Diverse MusicBrainz search: {query}")
            url = f"{self.base_url}/recording"
            params = {
                'query': query,
                'fmt': 'json',
                'limit': min(limit, 25)  # Get more to ensure diversity
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            recordings = data.get('recordings', [])
            logger.info(f"Found {len(recordings)} recordings for diversity filtering")
            
            return recordings
            
        except Exception as e:
            logger.error(f"Diverse MusicBrainz search failed: {e}")
            return []

# Initialize client
mb_client = DiverseMusicBrainzClient()

# Enhanced genre mapping with MORE diverse artists
DIVERSE_GENRE_QUERIES = {
    'rock': [
        'the beatles', 'queen', 'led zeppelin', 'pink floyd', 'the rolling stones',
        'nirvana', 'radiohead', 'foo fighters', 'red hot chili peppers', 'pearl jam'
    ],
    'jazz': [
        'miles davis', 'john coltrane', 'bill evans', 'charlie parker', 'herbie hancock',
        'duke ellington', 'ella fitzgerald', 'louis armstrong', 'diana krall', 'keith jarrett'
    ],
    'hip-hop': [
        'eminem', 'jay-z', 'nas', 'kendrick lamar', 'j. cole', 'drake', 'kanye west',
        'tupac', 'biggie', 'ice cube', 'outkast', 'wu-tang clan'
    ],
    'pop': [
        'taylor swift', 'ed sheeran', 'bruno mars', 'adele', 'billie eilish',
        'ariana grande', 'justin bieber', 'the weeknd', 'dua lipa', 'harry styles'
    ],
    'electronic': [
        'daft punk', 'calvin harris', 'deadmau5', 'avicii', 'skrillex',
        'tiësto', 'david guetta', 'diplo', 'flume', 'odesza'
    ],
    'country': [
        'johnny cash', 'dolly parton', 'garth brooks', 'carrie underwood',
        'keith urban', 'blake shelton', 'willie nelson', 'kacey musgraves'
    ],
    'reggae': [
        'bob marley', 'jimmy cliff', 'peter tosh', 'burning spear',
        'ziggy marley', 'toots and the maytals'
    ],
    'blues': [
        'bb king', 'muddy waters', 'eric clapton', 'stevie ray vaughan',
        'john lee hooker', 'buddy guy', 'robert johnson'
    ],
    'r&b': [
        'beyoncé', 'john legend', 'alicia keys', 'usher', 'mary j. blige',
        'stevie wonder', 'aretha franklin', 'the weeknd'
    ],
    'metal': [
        'metallica', 'black sabbath', 'iron maiden', 'judas priest',
        'megadeth', 'tool', 'system of a down', 'pantera'
    ]
}

def detect_genre_enhanced(query: str) -> Optional[str]:
    """Enhanced genre detection with more keywords"""
    query_lower = query.lower()
    
    # Enhanced keyword matching with more variations
    if any(word in query_lower for word in ['rap', 'hip-hop', 'hip hop', 'hiphop', 'old school', 'trap', 'boom bap']):
        return 'hip-hop'
    elif any(word in query_lower for word in ['rock', 'alternative', 'indie', 'grunge', 'punk']):
        return 'rock'
    elif any(word in query_lower for word in ['jazz', 'swing', 'bebop', 'smooth jazz', 'fusion']):
        return 'jazz'
    elif any(word in query_lower for word in ['pop', 'mainstream', 'chart', 'dance pop']):
        return 'pop'
    elif any(word in query_lower for word in ['electronic', 'edm', 'techno', 'house', 'ambient', 'dance']):
        return 'electronic'
    elif any(word in query_lower for word in ['country', 'folk', 'bluegrass', 'americana']):
        return 'country'
    elif any(word in query_lower for word in ['reggae', 'ska', 'dub']):
        return 'reggae'
    elif any(word in query_lower for word in ['blues', 'delta blues', 'chicago blues']):
        return 'blues'
    elif any(word in query_lower for word in ['r&b', 'soul', 'funk', 'rhythm and blues']):
        return 'r&b'
    elif any(word in query_lower for word in ['metal', 'heavy metal', 'death metal', 'thrash']):
        return 'metal'
    
    return None

def ensure_artist_diversity(recommendations: List[Dict], max_per_artist: int = 1) -> List[Dict]:
    """Ensure no artist appears more than max_per_artist times"""
    artist_counts = defaultdict(int)
    diverse_recommendations = []
    
    # Sort by score first to prioritize best matches
    sorted_recs = sorted(recommendations, key=lambda x: x['score'], reverse=True)
    
    for rec in sorted_recs:
        artist_name = rec['artist_name'].lower()
        
        if artist_counts[artist_name] < max_per_artist:
            diverse_recommendations.append(rec)
            artist_counts[artist_name] += 1
    
    logger.info(f"Diversity filter: {len(recommendations)} → {len(diverse_recommendations)} (max {max_per_artist} per artist)")
    return diverse_recommendations

def get_diverse_recommendations(query: str, limit: int = 10) -> Dict:
    """Get diverse recommendations with artist variety"""
    try:
        start_time = time.time()
        logger.info(f"Diverse recommendations for: '{query}'")
        
        recommendations = []
        detected_genre = detect_genre_enhanced(query)
        
        # Strategy 1: Multi-artist genre search for diversity
        if detected_genre and detected_genre in DIVERSE_GENRE_QUERIES:
            logger.info(f"Genre detected for diversity: {detected_genre}")
            
            # Get artists for this genre and shuffle for variety
            genre_artists = DIVERSE_GENRE_QUERIES[detected_genre].copy()
            random.shuffle(genre_artists)  # Randomize to get different artists each time
            
            # Search multiple artists but limit tracks per artist
            for artist in genre_artists[:6]:  # Use more artists but fewer tracks each
                if time.time() - start_time > 8:  # Timeout protection
                    logger.warning("Genre search timeout")
                    break
                    
                try:
                    artist_recordings = mb_client.search_recordings_diverse(f'artist:"{artist}"', limit=3)
                    
                    # Only take 1-2 tracks per artist for diversity
                    for recording in artist_recordings[:2]:
                        artist_info = recording.get('artist-credit', [{}])[0].get('artist', {})
                        recommendations.append({
                            'track_id': recording['id'],
                            'track_title': recording['title'],
                            'artist_id': artist_info.get('id', ''),
                            'artist_name': artist_info.get('name', 'Unknown'),
                            'score': 85,
                            'recommendation_type': f'diverse_genre_{detected_genre}',
                            'search_method': 'diverse_genre_artist'
                        })
                        
                        if len(recommendations) >= limit * 2:  # Get extra for diversity filtering
                            break
                    
                    if len(recommendations) >= limit * 2:
                        break
                        
                except Exception as e:
                    logger.warning(f"Artist search failed for {artist}: {e}")
                    continue
        
        # Strategy 2: Tag-based diverse search
        if detected_genre and len(recommendations) < limit * 1.5:
            try:
                # Search by genre tag to get different artists
                tag_recordings = mb_client.search_recordings_diverse(f'tag:{detected_genre}', limit=15)
                
                for recording in tag_recordings:
                    artist_info = recording.get('artist-credit', [{}])[0].get('artist', {})
                    recommendations.append({
                        'track_id': recording['id'],
                        'track_title': recording['title'],
                        'artist_id': artist_info.get('id', ''),
                        'artist_name': artist_info.get('name', 'Unknown'),
                        'score': 75,
                        'recommendation_type': f'diverse_tag_{detected_genre}',
                        'search_method': 'diverse_tag_search'
                    })
                    
            except Exception as e:
                logger.warning(f"Tag search failed: {e}")
        
        # Strategy 3: Fallback direct search with diversity
        if len(recommendations) < limit:
            try:
                direct_recordings = mb_client.search_recordings_diverse(query, limit=10)
                for recording in direct_recordings:
                    artist_info = recording.get('artist-credit', [{}])[0].get('artist', {})
                    recommendations.append({
                        'track_id': recording['id'],
                        'track_title': recording['title'],
                        'artist_id': artist_info.get('id', ''),
                        'artist_name': artist_info.get('name', 'Unknown'),
                        'score': 60,
                        'recommendation_type': 'diverse_fallback',
                        'search_method': 'diverse_direct'
                    })
            except Exception as e:
                logger.warning(f"Fallback search failed: {e}")
        
        # Apply diversity filtering - max 1 track per artist
        diverse_recs = ensure_artist_diversity(recommendations, max_per_artist=1)
        
        # If we still don't have enough, allow 2 tracks per artist
        if len(diverse_recs) < limit and len(recommendations) > len(diverse_recs):
            logger.info("Expanding to 2 tracks per artist for sufficient results")
            diverse_recs = ensure_artist_diversity(recommendations, max_per_artist=2)
        
        # Remove any remaining duplicates by track ID
        seen_tracks = set()
        unique_recs = []
        for rec in diverse_recs:
            if rec['track_id'] not in seen_tracks:
                seen_tracks.add(rec['track_id'])
                unique_recs.append(rec)
        
        # Sort by score and limit results
        unique_recs.sort(key=lambda x: x['score'], reverse=True)
        final_recs = unique_recs[:limit]
        
        elapsed_time = time.time() - start_time
        
        # Count unique artists in final results
        unique_artists = len({rec['artist_name'] for rec in final_recs})
        
        logger.info(f"Diverse recommendations: {len(final_recs)} tracks from {unique_artists} different artists in {elapsed_time:.2f}s")
        
        return {
            'recommendations': final_recs,
            'query_analyzed': {
                'detected_genre': detected_genre,
                'unique_artists': unique_artists,
                'total_tracks': len(final_recs),
                'diversity_ratio': f"{unique_artists}/{len(final_recs)}",
                'processing_time': f"{elapsed_time:.2f}s",
                'strategy_used': 'diverse_multi_artist'
            },
            'algorithm_version': '2.5.0_diverse'
        }
        
    except Exception as e:
        logger.error(f"Diverse recommendations error: {e}")
        return {
            'recommendations': [],
            'query_analyzed': {'error': str(e)},
            'algorithm_version': '2.5.0_diverse'
        }

@app.get("/health")
def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "diverse-recommendation-service",
        "version": "2.5.0",
        "features": ["artist_diversity", "genre_detection", "multi_strategy_search"]
    }

@app.get("/recommendations/query")
def get_query_recommendations(query: str, limit: int = 10, username: str = None):
    """Diverse recommendation endpoint"""
    try:
        logger.info(f"Diverse query request: '{query}', limit={limit}")
        
        if not query or len(query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        
        if limit < 1 or limit > 20:  # Allow more results for diversity
            limit = 10
        
        result = get_diverse_recommendations(query.strip(), limit)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diverse endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/recommendations/profile/{username}")
def get_profile_recommendations(
    username: str, 
    limit: int = 10,
    db: Session = Depends(get_db)  # ✓ Reuses connection pool
):
    """Generate recommendations based on user's profile preferences"""
    try:
        logger.info(f"Getting profile recommendations for {username}")
        
        # Use injected session (faster in production!)
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        
        if not profile:
            logger.warning(f"No profile found for user: {username}")
            return {
                "recommendations": [],
                "message": "Profile not found. Please create a profile first."
            }
        
        # Parse favorite genres (stored as JSON string)
        favorite_genres = json.loads(profile.favorite_genres) if profile.favorite_genres else []
        favorite_artists = json.loads(profile.favorite_artists) if profile.favorite_artists else []
        
        if not favorite_genres and not favorite_artists:
            logger.warning(f"Empty profile for user: {username}")
            return {
                "recommendations": [],
                "message": "Please add favorite genres or artists to your profile."
            }
        
        # Generate recommendations based on favorite genres
        all_recommendations = []
        
        # Strategy 1: Use favorite genres
        if favorite_genres:
            logger.info(f"Generating recommendations for genres: {favorite_genres}")
            
            # Take the first 2-3 genres to avoid overwhelming the API
            for genre in favorite_genres[:3]:
                genre_recs = get_diverse_recommendations(genre, limit=limit // len(favorite_genres[:3]) + 2)
                all_recommendations.extend(genre_recs.get('recommendations', []))
        
        # Strategy 2: Use favorite artists (if you want to implement this)
        # This would require querying MusicBrainz for songs by those artists
        
        # Remove duplicates and sort by score
        seen_tracks = set()
        unique_recommendations = []
        
        for rec in all_recommendations:
            if rec['track_id'] not in seen_tracks:
                seen_tracks.add(rec['track_id'])
                # Mark as profile-based recommendation
                rec['recommendation_type'] = 'profile_based'
                unique_recommendations.append(rec)
        
        # Sort by score and limit results
        unique_recommendations.sort(key=lambda x: x['score'], reverse=True)
        final_recommendations = unique_recommendations[:limit]
        
        logger.info(f"Generated {len(final_recommendations)} profile-based recommendations for {username}")
        
        return {
            "recommendations": final_recommendations,
            "profile_analysis": {
                "favorite_genres": favorite_genres,
                "genres_used": favorite_genres[:3],
                "total_matches": len(all_recommendations),
                "unique_results": len(final_recommendations)
            }
        }
        
    except Exception as e:
        logger.error(f"Profile recommendations error for {username}: {e}")
        return {
            "recommendations": [],
            "error": str(e),
            "message": "Error generating profile recommendations"
        }

@app.get("/recommendations/similar/{artist_name}")
def get_similar_recommendations(artist_name: str, limit: int = 10):
    """Diverse similar artist recommendations"""
    try:
        # For similar artists, we want diversity across different artists
        result = get_diverse_recommendations(artist_name, limit)
        return {"recommendations": result['recommendations']}
    except Exception as e:
        logger.error(f"Diverse similar error: {e}")
        return {"recommendations": []}

# Profile endpoints
@app.post("/users/{username}/profile")
def create_profile(
    username: str,                      # <- From URL path: /users/{username}/profile
    profile_data: ProfileData,          # <- From JSON body (Pydantic auto-parses)
    db: Session = Depends(get_db)       # <- Database session (dependency injection)
):
    """
    Create or update user profile.
    
    Request example:
        POST /users/john/profile
        Body: {"favorite_genres": ["rock"], "favorite_artists": ["id1"]}
    
    Flow:
        1. FastAPI extracts 'john' from URL -> username
        2. FastAPI parses JSON body -> profile_data (ProfileData object)
        3. FastAPI provides database session -> db
        4. We extract and save the data
    """
    try:
        # Step 1: Extract data from Pydantic model
        favorite_genres = profile_data.favorite_genres    # This is a list
        favorite_artists = profile_data.favorite_artists  # This is a list
        
        logger.info(f"Received profile data for {username}: genres={favorite_genres}, artists={favorite_artists}")
        
        # Step 2: Check if profile already exists in database
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        
        if profile:
            # UPDATE existing profile
            profile.favorite_genres = json.dumps(favorite_genres)    # Convert list to JSON string
            profile.favorite_artists = json.dumps(favorite_artists)  # Convert list to JSON string
            logger.info(f"Updated existing profile for {username}")
        else:
            # CREATE new profile
            profile = UserProfile(
                username=username,
                favorite_genres=json.dumps(favorite_genres),    # Convert list to JSON string
                favorite_artists=json.dumps(favorite_artists)   # Convert list to JSON string
            )
            db.add(profile)
            logger.info(f"Created new profile for {username}")
        
        # Step 3: Save to database
        db.commit()
        db.refresh(profile)
        
        # Step 4: Return success response
        return {
            "message": f"Profile saved for {username}",
            "username": username,
            "favorite_genres": favorite_genres,      # Return as list
            "favorite_artists": favorite_artists     # Return as list
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving profile for {username}: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving profile: {str(e)}")


@app.get("/users/{username}/profile") 
def get_profile(
    username: str,                      # <- From URL path
    db: Session = Depends(get_db)       # <- Database session
):
    """
    Get user profile.
    
    Request example:
        GET /users/john/profile
    
    Returns the user's saved favorite genres and artists.
    """
    try:
        # Step 1: Query database for profile
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        
        # Step 2: If no profile found, return empty
        if not profile:
            logger.info(f"No profile found for {username}, returning empty")
            return {
                "username": username,
                "favorite_genres": [],
                "favorite_artists": []
            }
        
        # Step 3: Parse JSON strings back to lists
        # (Database stores as JSON strings, we need to convert back to lists)
        favorite_genres = json.loads(profile.favorite_genres) if profile.favorite_genres else []
        favorite_artists = json.loads(profile.favorite_artists) if profile.favorite_artists else []
        
        logger.info(f"Retrieved profile for {username}: {len(favorite_genres)} genres, {len(favorite_artists)} artists")
        
        # Step 4: Return profile data
        return {
            "username": username,
            "favorite_genres": favorite_genres,
            "favorite_artists": favorite_artists,
            "created_at": str(profile.created_at),
            "updated_at": str(profile.updated_at)
        }
        
    except Exception as e:
        logger.error(f"Error getting profile for {username}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting profile: {str(e)}")


@app.post("/users/{username}/listening-history")
def add_history(
    username: str, 
    track_id: str, 
    artist_id: str, 
    interaction_type: str = "played", 
    db: Session = Depends(get_db)
):
    """Add listening history entry - FIXED VERSION with better error handling"""
    try:
        # Import here to avoid circular imports
        from shared.models import ListeningHistory
        from datetime import datetime
        
        logger.info(f"Adding {interaction_type} history for user {username}: track={track_id}, artist={artist_id}")
        
        # Step 1: Get or create user profile
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        
        if not profile:
            logger.info(f"Profile not found for {username}, creating new profile")
            profile = UserProfile(
                username=username,
                favorite_genres=json.dumps([]),
                favorite_artists=json.dumps([])
            )
            db.add(profile)
            db.flush()  # Flush to get the ID without committing
            logger.info(f"Created profile with id={profile.id}")
        else:
            logger.info(f"Found existing profile with id={profile.id}")
        
        # Step 2: Create listening history entry
        history_entry = ListeningHistory(
            user_id=profile.id,
            track_id=track_id,
            artist_id=artist_id,
            interaction_type=interaction_type,
            played_at=datetime.now(timezone.utc)
        )
        
        db.add(history_entry)
        
        # Step 3: Commit everything
        db.commit()
        
        logger.info(f"Successfully added {interaction_type} history for {username}")
        
        # Step 4: Verify it was saved
        verify_count = db.query(ListeningHistory).filter(
            ListeningHistory.user_id == profile.id,
            ListeningHistory.track_id == track_id,
            ListeningHistory.interaction_type == interaction_type
        ).count()
        
        logger.info(f"Verification: Found {verify_count} matching history entries")
        
        return {
            "message": "History added successfully",
            "username": username,
            "user_id": profile.id,
            "track_id": track_id,
            "artist_id": artist_id,
            "interaction_type": interaction_type,
            "verification_count": verify_count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"ERROR adding history for {username}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error adding history: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)