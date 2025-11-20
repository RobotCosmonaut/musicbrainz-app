from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
import httpx
import uvicorn
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MusicBrainz API Gateway", version="1.0.0")

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

# Service URLs
ARTIST_SERVICE_URL = os.getenv("ARTIST_SERVICE_URL", "http://localhost:8001")
ALBUM_SERVICE_URL = os.getenv("ALBUM_SERVICE_URL", "http://localhost:8002")
RECOMMENDATION_SERVICE_URL = os.getenv("RECOMMENDATION_SERVICE_URL", "http://localhost:8003")

# Timeout configuration
TIMEOUT_CONFIG = httpx.Timeout(
    connect=5.0,    # 5 seconds to connect
    read=30.0,      # 30 seconds to read response
    write=10.0,     # 10 seconds to write request
    pool=10.0       # 10 seconds to get connection from pool
)

class ProfileCreate(BaseModel):
    """Request body model for creating/updating user profiles"""
    favorite_genres: list = []
    favorite_artists: list = []

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "api-gateway"}

# Artist endpoints
@app.get("/api/artists/search")
async def search_artists(query: str, limit: int = 25):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(f"{ARTIST_SERVICE_URL}/artists/search", params={"query": query, "limit": limit})
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail="Service unavailable")
    except httpx.TimeoutException:
        logger.error("Artist service timeout")
        raise HTTPException(status_code=504, detail="Artist service timeout")
    except Exception as e:
        logger.error(f"Artist service error: {e}")
        raise HTTPException(status_code=503, detail="Artist service unavailable")

@app.get("/api/artists/{artist_id}")
async def get_artist(artist_id: str):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(f"{ARTIST_SERVICE_URL}/artists/{artist_id}")
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail="Artist not found")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Artist service timeout")
    except Exception as e:
        logger.error(f"Get artist error: {e}")
        raise HTTPException(status_code=503, detail="Artist service unavailable")

@app.get("/api/artists")
async def list_artists(skip: int = 0, limit: int = 100):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(f"{ARTIST_SERVICE_URL}/artists", params={"skip": skip, "limit": limit})
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail="Service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Artist service timeout")
    except Exception as e:
        logger.error(f"List artists error: {e}")
        raise HTTPException(status_code=503, detail="Artist service unavailable")

# Album endpoints
@app.get("/api/albums/search")
async def search_albums(artist_name: str = "", album_title: str = "", limit: int = 25):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(f"{ALBUM_SERVICE_URL}/albums/search", 
                                      params={"artist_name": artist_name, "album_title": album_title, "limit": limit})
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail="Service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Album service timeout")
    except Exception as e:
        logger.error(f"Album search error: {e}")
        raise HTTPException(status_code=503, detail="Album service unavailable")

@app.get("/api/albums/{album_id}")
async def get_album(album_id: str):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(f"{ALBUM_SERVICE_URL}/albums/{album_id}")
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail="Album not found")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Album service timeout")
    except Exception as e:
        logger.error(f"Get album error: {e}")
        raise HTTPException(status_code=503, detail="Album service unavailable")

# Recommendation endpoints with enhanced error handling
@app.get("/api/recommendations/query")
async def get_query_recommendations(query: str, limit: int = 10):
    try:
        logger.info(f"Gateway: Getting recommendations for '{query}' with limit {limit}")
        
        # Extended timeout for recommendation service since it calls external APIs
        extended_timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,   # 60 seconds for MusicBrainz API calls
            write=10.0,
            pool=10.0
        )
        
        async with httpx.AsyncClient(timeout=extended_timeout) as client:
            response = await client.get(
                f"{RECOMMENDATION_SERVICE_URL}/recommendations/query", 
                params={"query": query, "limit": limit}
            )
            
            logger.info(f"Gateway: Recommendation service responded with status {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                raise HTTPException(status_code=400, detail="Invalid query parameters")
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="No recommendations found")
            else:
                logger.error(f"Recommendation service error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Recommendation service error")
                
    except httpx.TimeoutException:
        logger.error("Recommendation service timeout")
        raise HTTPException(status_code=504, detail="Recommendation service timeout - try a simpler query")
    except httpx.ConnectError:
        logger.error("Cannot connect to recommendation service")
        raise HTTPException(status_code=503, detail="Recommendation service unavailable")
    except Exception as e:
        logger.error(f"Recommendation service error: {e}")
        raise HTTPException(status_code=503, detail="Recommendation service unavailable")

@app.get("/api/recommendations/profile/{username}")
async def get_profile_recommendations(username: str, limit: int = 10):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(f"{RECOMMENDATION_SERVICE_URL}/recommendations/profile/{username}", 
                                      params={"limit": limit})
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="User profile not found")
            else:
                raise HTTPException(status_code=response.status_code, detail="Profile service error")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Profile service timeout")
    except Exception as e:
        logger.error(f"Profile recommendations error: {e}")
        raise HTTPException(status_code=503, detail="Profile service unavailable")

@app.get("/api/recommendations/similar/{artist_name}")
async def get_similar_recommendations(artist_name: str, limit: int = 10):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(f"{RECOMMENDATION_SERVICE_URL}/recommendations/similar/{artist_name}", 
                                      params={"limit": limit})
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Similar recommendations service error")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Similar recommendations timeout")
    except Exception as e:
        logger.error(f"Similar recommendations error: {e}")
        raise HTTPException(status_code=503, detail="Similar recommendations unavailable")

@app.post("/api/users/{username}/profile")
async def create_user_profile(username: str, profile: ProfileCreate):
    """
    Create or update a user profile
    
    Args:
        username: Username from URL path
        profile: Profile data from request body (JSON)
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            # Forward the request to recommendation service
            response = await client.post(
                f"{RECOMMENDATION_SERVICE_URL}/users/{username}/profile", 
                json={
                    "favorite_genres": profile.favorite_genres,
                    "favorite_artists": profile.favorite_artists
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Profile creation failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Profile creation failed: {response.text}"
                )
    except httpx.TimeoutException:
        logger.error("Profile service timeout")
        raise HTTPException(status_code=504, detail="Profile service timeout")
    except Exception as e:
        logger.error(f"Create profile error: {e}")
        raise HTTPException(status_code=503, detail=f"Profile service unavailable: {str(e)}")

@app.get("/api/users/{username}/profile")
async def get_user_profile(username: str):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(f"{RECOMMENDATION_SERVICE_URL}/users/{username}/profile")
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="Profile not found")
            else:
                raise HTTPException(status_code=response.status_code, detail="Profile service error")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Profile service timeout")
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=503, detail="Profile service unavailable")

@app.post("/api/users/{username}/listening-history")
async def add_listening_history(username: str, track_id: str, artist_id: str, interaction_type: str = "played"):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.post(f"{RECOMMENDATION_SERVICE_URL}/users/{username}/listening-history",
                                       params={"track_id": track_id, "artist_id": artist_id, "interaction_type": interaction_type})
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="History service error")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="History service timeout")
    except Exception as e:
        logger.error(f"Add history error: {e}")
        raise HTTPException(status_code=503, detail="History service unavailable")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)