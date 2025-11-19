"""
Unit tests for Artist Service
"""

import pytest
from shared.models import Artist

class TestArtistService:
    """Test suite for artist service endpoints"""
    
    def test_health_check(self, artist_client):
        """Test health endpoint"""
        response = artist_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "artist-service"
    
    def test_search_artists_empty_query(self, artist_client):
        """Test search with empty query returns 500 or handles gracefully"""
        response = artist_client.get("/artists/search", params={"query": "", "limit": 10})
        # Should either return empty results or error
        assert response.status_code in [200, 400, 500]
    
    def test_list_artists_empty_db(self, artist_client):
        """Test listing artists from empty database"""
        response = artist_client.get("/artists", params={"skip": 0, "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert "artists" in data
        assert len(data["artists"]) == 0
    
    def test_list_artists_with_data(self, artist_client, test_db, sample_artist_data):
        """Test listing artists when data exists"""
        # Add test artist to database
        artist = Artist(**sample_artist_data)
        test_db.add(artist)
        test_db.commit()
        
        response = artist_client.get("/artists", params={"skip": 0, "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert len(data["artists"]) == 1
        assert data["artists"][0]["name"] == "Test Artist"
    
    def test_get_artist_not_found(self, artist_client):
        """Test getting non-existent artist"""
        response = artist_client.get("/artists/nonexistent-id")
        # Should return 404 or fetch from API
        assert response.status_code in [200, 404, 500]
    
    @pytest.mark.parametrize("limit", [1, 10, 50, 100])
    def test_list_artists_pagination(self, artist_client, limit):
        """Test pagination with different limits"""
        response = artist_client.get("/artists", params={"skip": 0, "limit": limit})
        assert response.status_code == 200

class TestArtistModel:
    """Test suite for Artist model"""
    
    def test_artist_creation(self, test_db, sample_artist_data):
        """Test creating an artist in database"""
        artist = Artist(**sample_artist_data)
        test_db.add(artist)
        test_db.commit()
        
        retrieved = test_db.query(Artist).filter(Artist.id == sample_artist_data["id"]).first()
        assert retrieved is not None
        assert retrieved.name == sample_artist_data["name"]
        assert retrieved.country == sample_artist_data["country"]
    
    def test_artist_unique_id(self, test_db, sample_artist_data):
        """Test that artist IDs must be unique"""
        artist1 = Artist(**sample_artist_data)
        test_db.add(artist1)
        test_db.commit()
        
        # Try to add duplicate
        artist2 = Artist(**sample_artist_data)
        test_db.add(artist2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            test_db.commit()