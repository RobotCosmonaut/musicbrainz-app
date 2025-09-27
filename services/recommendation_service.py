from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from shared.database import get_db, create_tables_safe
from shared.models import UserProfile, Recommendation, ListeningHistory, Artist
from services.musicbrainz_service import MusicBrainzService
from typing import List, Dict, Optional
import json
import random
import uvicorn
from collections import Counter, defaultdict
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enhanced Recommendation Service", version="2.0.0")
musicbrainz = MusicBrainzService()

class EnhancedRecommendationEngine:
    def __init__(self, musicbrainz_service: MusicBrainzService):
        self.musicbrainz = musicbrainz_service
        
        # Genre keywords for better matching
        self.genre_keywords = {
            'rock': ['rock', 'alternative', 'indie', 'grunge', 'punk', 'metal', 'hard rock', 'classic rock'],
            'pop': ['pop', 'dance', 'electropop', 'synth-pop', 'bubblegum', 'mainstream'],
            'jazz': ['jazz', 'swing', 'bebop', 'smooth jazz', 'fusion', 'bossa nova'],
            'classical': ['classical', 'orchestra', 'symphony', 'concerto', 'opera', 'chamber'],
            'electronic': ['electronic', 'edm', 'techno', 'house', 'ambient', 'synthesizer', 'electro'],
            'hip-hop': ['hip-hop', 'rap', 'trap', 'gangsta', 'conscious', 'old school', 'boom bap'],
            'country': ['country', 'bluegrass', 'folk', 'americana', 'western', 'honky-tonk'],
            'blues': ['blues', 'rhythm and blues', 'delta blues', 'chicago blues', 'electric blues'],
            'reggae': ['reggae', 'ska', 'dub', 'dancehall', 'roots reggae'],
            'r&b': ['r&b', 'soul', 'funk', 'motown', 'neo-soul', 'contemporary r&b']
        }
        
        # Mood/style keywords
        self.mood_keywords = {
            'upbeat': ['upbeat', 'energetic', 'fast', 'dance', 'party', 'happy', 'lively'],
            'relaxing': ['relaxing', 'calm', 'chill', 'peaceful', 'ambient', 'slow', 'mellow'],
            'emotional': ['emotional', 'sad', 'melancholy', 'heartbreak', 'ballad', 'deep'],
            'aggressive': ['aggressive', 'hard', 'heavy', 'intense', 'angry', 'powerful'],
            'romantic': ['romantic', 'love', 'sweet', 'tender', 'intimate', 'soft']
        }
    
    def extract_search_intent(self, query: str) -> Dict[str, any]:
        """Extract genre, mood, and other attributes from search query"""
        query_lower = query.lower()
        intent = {
            'genres': [],
            'moods': [],
            'artists': [],
            'keywords': query_lower.split(),
            'original_query': query
        }
        
        # Extract genres
        for genre, keywords in self.genre_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                intent['genres'].append(genre)
        
        # Extract moods
        for mood, keywords in self.mood_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                intent['moods'].append(mood)
        
        # Extract potential artist names (simple heuristic)
        words = query_lower.split()
        potential_artists = []
        for i, word in enumerate(words):
            if word in ['by', 'from', 'artist', 'band']:
                if i + 1 < len(words):
                    potential_artists.extend(words[i+1:])
                    break
        intent['artists'] = potential_artists
        
        return intent
    
    def calculate_relevance_score(self, recording: Dict, search_intent: Dict, user_profile: Optional[UserProfile] = None) -> int:
        """Calculate comprehensive relevance score for a recording"""
        score = 0
        max_score = 100
        
        # Get recording details
        title = recording.get('title', '').lower()
        artist_info = recording.get('artist-credit', [{}])[0].get('artist', {})
        artist_name = artist_info.get('name', '').lower()
        tags = recording.get('tags', [])
        tag_names = [tag.get('name', '').lower() for tag in tags]
        
        # 1. Title relevance (reduced weight from 50% to 25%)
        title_score = 0
        query_words = search_intent['keywords']
        for word in query_words:
            if word in title:
                title_score += 15 if word == title else 10
        score += min(title_score, 25)
        
        # 2. Artist relevance (increased weight to 30%)
        artist_score = 0
        for word in query_words:
            if word in artist_name:
                artist_score += 20 if len(word) > 3 else 10
        
        # Check against potential artist names from query
        for potential_artist in search_intent['artists']:
            if potential_artist in artist_name:
                artist_score += 25
        
        score += min(artist_score, 30)
        
        # 3. Genre relevance (25%)
        genre_score = 0
        detected_genres = search_intent['genres']
        
        for genre in detected_genres:
            # Check tags for genre matches
            for tag in tag_names:
                if any(keyword in tag for keyword in self.genre_keywords.get(genre, [])):
                    genre_score += 20
                    break
            
            # Check if genre keywords appear in title or artist
            genre_keywords = self.genre_keywords.get(genre, [])
            if any(keyword in title or keyword in artist_name for keyword in genre_keywords):
                genre_score += 15
        
        score += min(genre_score, 25)
        
        # 4. Mood/style relevance (10%)
        mood_score = 0
        for mood in search_intent['moods']:
            mood_keywords = self.mood_keywords.get(mood, [])
            if any(keyword in title or keyword in artist_name for keyword in mood_keywords):
                mood_score += 8
            
            # Check tags for mood indicators
            for tag in tag_names:
                if any(keyword in tag for keyword in mood_keywords):
                    mood_score += 5
                    break
        
        score += min(mood_score, 10)
        
        # 5. User profile bonus (10%)
        profile_score = 0
        if user_profile:
            try:
                favorite_genres = json.loads(user_profile.favorite_genres or '[]')
                favorite_artists = json.loads(user_profile.favorite_artists or '[]')
                
                # Bonus for matching user's favorite genres
                for fav_genre in favorite_genres:
                    if fav_genre in detected_genres:
                        profile_score += 5
                
                # Bonus for matching user's favorite artists
                artist_id = artist_info.get('id', '')
                if artist_id in favorite_artists:
                    profile_score += 15
                
            except (json.JSONDecodeError, AttributeError):
                pass
        
        score += min(profile_score, 10)
        
        # Apply penalties for poor matches
        if not any([title_score > 0, artist_score > 0, genre_score > 0]):
            score = max(score - 20, 0)
        
        return min(int(score), max_score)
    
    def get_profile_recommendations(self, user_profile: UserProfile, db: Session, limit: int = 10) -> List[Dict]:
        """Generate recommendations based on user profile"""
        recommendations = []
        
        try:
            # Parse user preferences
            favorite_artists = json.loads(user_profile.favorite_artists or '[]')
            favorite_genres = json.loads(user_profile.favorite_genres or '[]')
            
            # Get tracks from favorite artists (higher weight)
            for artist_id in favorite_artists[:3]:
                try:
                    recordings = self.musicbrainz.get_artist_recordings(artist_id, limit=20)
                    for recording in recordings[:5]:
                        artist_name = recording.get('artist-credit', [{}])[0].get('artist', {}).get('name', 'Unknown')
                        recommendations.append({
                            'track_id': recording['id'],
                            'track_title': recording['title'],
                            'artist_id': artist_id,
                            'artist_name': artist_name,
                            'score': 95,  # High score for favorite artists
                            'recommendation_type': 'profile_favorite_artist'
                        })
                except Exception as e:
                    logger.warning(f"Error getting recordings for artist {artist_id}: {e}")
            
            # Search for genre-based recommendations
            for genre in favorite_genres[:3]:
                try:
                    # Use multiple search strategies for better genre coverage
                    search_queries = [
                        f'tag:{genre}',
                        f'{genre}',
                        f'genre:{genre}'
                    ]
                    
                    for search_query in search_queries:
                        genre_recordings = self.musicbrainz.search_recordings(query=search_query, limit=10)
                        for recording in genre_recordings[:2]:
                            artist_name = recording.get('artist-credit', [{}])[0].get('artist', {}).get('name', 'Unknown')
                            artist_id = recording.get('artist-credit', [{}])[0].get('artist', {}).get('id', '')
                            
                            # Calculate score based on genre match quality
                            search_intent = self.extract_search_intent(genre)
                            score = self.calculate_relevance_score(recording, search_intent, user_profile)
                            score = max(score, 70)  # Minimum score for profile-based recommendations
                            
                            recommendations.append({
                                'track_id': recording['id'],
                                'track_title': recording['title'],
                                'artist_id': artist_id,
                                'artist_name': artist_name,
                                'score': score,
                                'recommendation_type': 'profile_genre'
                            })
                        
                        if len(recommendations) >= limit * 2:  # Get more than needed for filtering
                            break
                    
                except Exception as e:
                    logger.warning(f"Error getting genre recommendations for {genre}: {e}")
            
        except Exception as e:
            logger.error(f"Error in profile recommendations: {e}")
        
        # Remove duplicates and sort by score
        seen_tracks = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec['track_id'] not in seen_tracks:
                seen_tracks.add(rec['track_id'])
                unique_recommendations.append(rec)
        
        return sorted(unique_recommendations, key=lambda x: x['score'], reverse=True)[:limit]
    
    def get_query_recommendations(self, query: str, limit: int = 10, user_profile: Optional[UserProfile] = None) -> List[Dict]:
        """Enhanced query-based recommendations with better scoring"""
        recommendations = []
        
        try:
            # Extract search intent
            search_intent = self.extract_search_intent(query)
            logger.info(f"Search intent: {search_intent}")
            
            # Multiple search strategies for comprehensive results
            search_strategies = [
                # Direct query search
                {'query': query, 'weight': 1.0},
                # Genre-focused searches
                *[{'query': f'tag:{genre}', 'weight': 0.9} for genre in search_intent['genres']],
                # Artist-focused searches
                *[{'query': f'artist:"{artist}"', 'weight': 0.8} for artist in search_intent['artists']],
                # Mood-based searches
                *[{'query': f'{mood}', 'weight': 0.7} for mood in search_intent['moods']]
            ]
            
            # Remove duplicates while preserving order
            seen_queries = set()
            unique_strategies = []
            for strategy in search_strategies:
                if strategy['query'] not in seen_queries:
                    seen_queries.add(strategy['query'])
                    unique_strategies.append(strategy)
            
            # Execute searches
            for strategy in unique_strategies[:5]:  # Limit to top 5 strategies
                try:
                    recordings = self.musicbrainz.search_recordings(
                        query=strategy['query'], 
                        limit=min(limit * 2, 25)
                    )
                    
                    for recording in recordings:
                        artist_name = recording.get('artist-credit', [{}])[0].get('artist', {}).get('name', 'Unknown')
                        artist_id = recording.get('artist-credit', [{}])[0].get('artist', {}).get('id', '')
                        
                        # Calculate comprehensive relevance score
                        base_score = self.calculate_relevance_score(recording, search_intent, user_profile)
                        final_score = int(base_score * strategy['weight'])
                        
                        recommendations.append({
                            'track_id': recording['id'],
                            'track_title': recording['title'],
                            'artist_id': artist_id,
                            'artist_name': artist_name,
                            'score': final_score,
                            'recommendation_type': 'enhanced_query_based',
                            'search_strategy': strategy['query']
                        })
                
                except Exception as e:
                    logger.warning(f"Search strategy failed for '{strategy['query']}': {e}")
        
        except Exception as e:
            logger.error(f"Error in query recommendations: {e}")
        
        # Remove duplicates, prioritizing higher scores
        track_scores = {}
        for rec in recommendations:
            track_id = rec['track_id']
            if track_id not in track_scores or rec['score'] > track_scores[track_id]['score']:
                track_scores[track_id] = rec
        
        # Sort by score and return top results
        final_recommendations = list(track_scores.values())
        final_recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return final_recommendations[:limit]
    
    def get_similar_artist_recommendations(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """Enhanced similar artist recommendations"""
        recommendations = []
        
        try:
            # Search for the main artist first
            main_artists = self.musicbrainz.search_artists(artist_name, limit=5)
            
            if not main_artists:
                return recommendations
            
            # Get the primary artist
            primary_artist = main_artists[0]
            
            # Search for similar artists using multiple strategies
            search_strategies = [
                artist_name,  # Direct name match
                f'{artist_name} similar',  # Similar artists
                f'{artist_name} style',   # Similar style
            ]
            
            # Also search by potential genre if we can infer it
            primary_artist_id = primary_artist.get('id')
            if primary_artist_id:
                try:
                    # Get some tracks from the primary artist to understand their style
                    sample_tracks = self.musicbrainz.get_artist_recordings(primary_artist_id, limit=5)
                    
                    # Extract genres from sample tracks
                    inferred_genres = set()
                    for track in sample_tracks:
                        tags = track.get('tags', [])
                        for tag in tags:
                            tag_name = tag.get('name', '').lower()
                            for genre, keywords in self.genre_keywords.items():
                                if any(keyword in tag_name for keyword in keywords):
                                    inferred_genres.add(genre)
                    
                    # Add genre-based searches
                    for genre in list(inferred_genres)[:2]:  # Max 2 genres
                        search_strategies.append(f'tag:{genre}')
                
                except Exception as e:
                    logger.warning(f"Could not infer genres for artist {artist_name}: {e}")
            
            # Execute artist searches
            similar_artists = []
            for strategy in search_strategies:
                try:
                    artists = self.musicbrainz.search_artists(strategy, limit=5)
                    similar_artists.extend(artists)
                except Exception as e:
                    logger.warning(f"Artist search failed for '{strategy}': {e}")
            
            # Remove duplicates and the original artist
            seen_artist_ids = {primary_artist.get('id')}
            unique_artists = []
            for artist in similar_artists:
                if artist.get('id') not in seen_artist_ids:
                    seen_artist_ids.add(artist.get('id'))
                    unique_artists.append(artist)
            
            # Get recordings from similar artists
            for artist in unique_artists[:5]:  # Limit to 5 similar artists
                try:
                    recordings = self.musicbrainz.get_artist_recordings(artist['id'], limit=4)
                    
                    # Calculate similarity score based on various factors
                    base_similarity = 60
                    
                    # Bonus for name similarity
                    if artist_name.lower() in artist['name'].lower() or artist['name'].lower() in artist_name.lower():
                        base_similarity += 15
                    
                    # Bonus for same country
                    if (primary_artist.get('country') and artist.get('country') and 
                        primary_artist['country'] == artist['country']):
                        base_similarity += 10
                    
                    # Bonus for same time period
                    primary_begin = primary_artist.get('life-span', {}).get('begin', '')
                    artist_begin = artist.get('life-span', {}).get('begin', '')
                    if primary_begin and artist_begin:
                        try:
                            primary_year = int(primary_begin[:4])
                            artist_year = int(artist_begin[:4])
                            if abs(primary_year - artist_year) <= 10:
                                base_similarity += 10
                        except (ValueError, TypeError):
                            pass
                    
                    for recording in recordings:
                        recommendations.append({
                            'track_id': recording['id'],
                            'track_title': recording['title'],
                            'artist_id': artist['id'],
                            'artist_name': artist['name'],
                            'score': min(base_similarity, 85),
                            'recommendation_type': 'enhanced_similar_artist'
                        })
                
                except Exception as e:
                    logger.warning(f"Error getting recordings for similar artist {artist.get('name', 'Unknown')}: {e}")
        
        except Exception as e:
            logger.error(f"Error in similar artist recommendations: {e}")
        
        # Sort by score and limit results
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]

# Initialize the enhanced engine
recommendation_engine = EnhancedRecommendationEngine(musicbrainz)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "enhanced-recommendation-service", "version": "2.0.0"}

@app.post("/users/{username}/profile")
def create_or_update_profile(
    username: str, 
    favorite_genres: List[str] = [], 
    favorite_artists: List[str] = [],
    db: Session = Depends(get_db)
):
    """Create or update user profile"""
    try:
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        
        if profile:
            profile.favorite_genres = json.dumps(favorite_genres)
            profile.favorite_artists = json.dumps(favorite_artists)
            profile.updated_at = datetime.utcnow()
        else:
            profile = UserProfile(
                username=username,
                favorite_genres=json.dumps(favorite_genres),
                favorite_artists=json.dumps(favorite_artists)
            )
            db.add(profile)
        
        db.commit()
        return {"message": f"Profile {'updated' if profile else 'created'} for {username}"}
    except Exception as e:
        logger.error(f"Error updating profile for {username}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/users/{username}/profile")
def get_user_profile(username: str, db: Session = Depends(get_db)):
    """Get user profile"""
    try:
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return {
            "username": profile.username,
            "favorite_genres": json.loads(profile.favorite_genres or '[]'),
            "favorite_artists": json.loads(profile.favorite_artists or '[]'),
            "created_at": profile.created_at,
            "updated_at": profile.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile for {username}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/recommendations/profile/{username}")
def get_profile_recommendations(username: str, limit: int = 10, db: Session = Depends(get_db)):
    """Get recommendations based on user profile"""
    try:
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        recommendations = recommendation_engine.get_profile_recommendations(profile, db, limit)
        
        # Save recommendations to database
        for rec in recommendations:
            try:
                db_rec = Recommendation(
                    user_id=profile.id,
                    track_id=rec['track_id'],
                    artist_id=rec['artist_id'],
                    track_title=rec['track_title'],
                    artist_name=rec['artist_name'],
                    score=rec['score'],
                    recommendation_type=rec['recommendation_type']
                )
                db.add(db_rec)
            except Exception as e:
                logger.warning(f"Could not save recommendation to DB: {e}")
        
        try:
            db.commit()
        except Exception as e:
            logger.warning(f"Could not commit recommendations to DB: {e}")
            db.rollback()
        
        return {"recommendations": recommendations}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile recommendations for {username}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/recommendations/query")
def get_query_recommendations(query: str, limit: int = 10, username: str = None, db: Session = Depends(get_db)):
    """Enhanced query-based recommendations"""
    try:
        user_profile = None
        if username and username != "guest":
            user_profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        
        recommendations = recommendation_engine.get_query_recommendations(query, limit, user_profile)
        
        logger.info(f"Generated {len(recommendations)} recommendations for query: '{query}'")
        
        return {"recommendations": recommendations, "query_analyzed": recommendation_engine.extract_search_intent(query)}
    except Exception as e:
        logger.error(f"Error getting query recommendations for '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/recommendations/similar/{artist_name}")
def get_similar_recommendations(artist_name: str, limit: int = 10):
    """Enhanced similar artist recommendations"""
    try:
        recommendations = recommendation_engine.get_similar_artist_recommendations(artist_name, limit)
        logger.info(f"Generated {len(recommendations)} similar artist recommendations for: '{artist_name}'")
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Error getting similar recommendations for '{artist_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/users/{username}/listening-history")
def add_listening_history(
    username: str,
    track_id: str,
    artist_id: str,
    interaction_type: str = "played",
    db: Session = Depends(get_db)
):
    """Add listening history for a user"""
    try:
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        history = ListeningHistory(
            user_id=profile.id,
            track_id=track_id,
            artist_id=artist_id,
            interaction_type=interaction_type
        )
        db.add(history)
        db.commit()
        
        return {"message": "Listening history added"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding listening history for {username}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)