from fastapi import FastAPI, HTTPException
import httpx
import uvicorn
import os

app = FastAPI(title="MusicBrainz API Gateway", version="1.0.0")

# Service URLs
ARTIST_SERVICE_URL = os.getenv("ARTIST_SERVICE_URL", "http://localhost:8001")
ALBUM_SERVICE_URL = os.getenv("ALBUM_SERVICE_URL", "http://localhost:8002")
RECOMMENDATION_SERVICE_URL = os.getenv("RECOMMENDATION_SERVICE_URL", "http://localhost:8003")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "api-gateway"}

# Artist endpoints
@app.get("/api/artists/search")
async def search_artists(query: str, limit: int = 25):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ARTIST_SERVICE_URL}/artists/search", params={"query": query, "limit": limit})
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Service unavailable")

@app.get("/api/artists/{artist_id}")
async def get_artist(artist_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ARTIST_SERVICE_URL}/artists/{artist_id}")
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Artist not found")

@app.get("/api/artists")
async def list_artists(skip: int = 0, limit: int = 100):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ARTIST_SERVICE_URL}/artists", params={"skip": skip, "limit": limit})
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Service unavailable")

# Album endpoints
@app.get("/api/albums/search")
async def search_albums(artist_name: str = "", album_title: str = "", limit: int = 25):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ALBUM_SERVICE_URL}/albums/search", 
                                  params={"artist_name": artist_name, "album_title": album_title, "limit": limit})
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Service unavailable")

@app.get("/api/albums/{album_id}")
async def get_album(album_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ALBUM_SERVICE_URL}/albums/{album_id}")
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Album not found")

# Recommendation endpoints
@app.get("/api/recommendations/query")
async def get_query_recommendations(query: str, limit: int = 10):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{RECOMMENDATION_SERVICE_URL}/recommendations/query", 
                                  params={"query": query, "limit": limit})
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Service unavailable")

@app.get("/api/recommendations/profile/{username}")
async def get_profile_recommendations(username: str, limit: int = 10):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{RECOMMENDATION_SERVICE_URL}/recommendations/profile/{username}", 
                                  params={"limit": limit})
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Profile not found")

@app.get("/api/recommendations/similar/{artist_name}")
async def get_similar_recommendations(artist_name: str, limit: int = 10):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{RECOMMENDATION_SERVICE_URL}/recommendations/similar/{artist_name}", 
                                  params={"limit": limit})
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Service unavailable")

@app.post("/api/users/{username}/profile")
async def create_user_profile(username: str, favorite_genres: list = [], favorite_artists: list = []):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{RECOMMENDATION_SERVICE_URL}/users/{username}/profile", 
                                   json={"favorite_genres": favorite_genres, "favorite_artists": favorite_artists})
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Service unavailable")

@app.get("/api/users/{username}/profile")
async def get_user_profile(username: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{RECOMMENDATION_SERVICE_URL}/users/{username}/profile")
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Profile not found")

@app.post("/api/users/{username}/listening-history")
async def add_listening_history(username: str, track_id: str, artist_id: str, interaction_type: str = "played"):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{RECOMMENDATION_SERVICE_URL}/users/{username}/listening-history",
                                   params={"track_id": track_id, "artist_id": artist_id, "interaction_type": interaction_type})
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Service unavailable")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
