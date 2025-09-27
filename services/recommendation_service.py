from fastapi import FastAPI, HTTPException
import uvicorn
import logging
import requests
import time
from typing import List, Dict, Set
from collections import defaultdict
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Diverse Recommendation Service", version="2.5.0")

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

def detect_genre_enhanced(query: str) -> str:
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
        unique_artists = len(set(rec['artist_name'] for rec in final_recs))
        
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
def get_profile_recommendations(username: str, limit: int = 10):
    """Diverse profile recommendations"""
    return {"recommendations": [], "message": "Use genre-based search for diverse results"}

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
def create_profile(username: str):
    return {"message": f"Profile created for {username}"}

@app.get("/users/{username}/profile") 
def get_profile(username: str):
    return {"username": username, "favorite_genres": [], "favorite_artists": []}

@app.post("/users/{username}/listening-history")
def add_history(username: str, track_id: str, artist_id: str, interaction_type: str = "played"):
    return {"message": "History added"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)