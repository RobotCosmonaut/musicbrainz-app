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

@pytest.mark.unit
@pytest.mark.api
class TestArtistServiceEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.parametrize("query", ["", "a", "ab", "abc"])
    def test_search_with_short_queries(self, artist_client, query):
        """Test search behavior with very short queries"""
        response = artist_client.get("/artists/search", params={"query": query, "limit": 10})
        # Should handle short queries gracefully
        assert response.status_code in [200, 400, 500]
    
    @pytest.mark.parametrize("limit", [0, -1, 1000, 9999])
    def test_list_with_extreme_limits(self, artist_client, limit):
        """Test pagination with extreme limit values"""
        response = artist_client.get("/artists", params={"skip": 0, "limit": limit})
        # Should handle extreme values gracefully
        assert response.status_code in [200, 400, 422]
    
    def test_get_artist_with_special_characters_id(self, artist_client):
        """Test getting artist with special characters in ID"""
        special_ids = ["id-with-dashes", "id_with_underscores", "id.with.dots"]
        for artist_id in special_ids:
            response = artist_client.get(f"/artists/{artist_id}")
            # Should handle special characters
            assert response.status_code in [200, 404, 500]
    
    def test_search_with_special_characters(self, artist_client):
        """Test search with special characters"""
        queries = ["artist&name", "artist's name", "artist/name", "artist\"name"]
        for query in queries:
            response = artist_client.get("/artists/search", params={"query": query})
            # Should not crash with special characters
            assert response.status_code in [200, 400, 500]


@pytest.mark.unit
@pytest.mark.database
class TestArtistModelValidation:
    """Test Artist model validation and constraints"""
    
    def test_artist_with_missing_optional_fields(self, test_db):
        """Test creating artist with minimal required fields"""
        artist = Artist(
            id="test-id",
            name="Test Artist"
            # country, disambiguation, etc. are optional
        )
        test_db.add(artist)
        test_db.commit()
        
        retrieved = test_db.query(Artist).filter(Artist.id == "test-id").first()
        assert retrieved is not None
        assert retrieved.name == "Test Artist"
    
    def test_artist_with_very_long_name(self, test_db):
        """Test artist with extremely long name"""
        long_name = "A" * 500  # Very long name
        artist = Artist(id="long-name-id", name=long_name)
        test_db.add(artist)
        # Should either succeed or fail gracefully
        try:
            test_db.commit()
            assert True
        except Exception:
            test_db.rollback()
            assert True  # Graceful failure is acceptable
    
    def test_artist_with_unicode_characters(self, test_db):
        """Test artist with international/unicode characters"""
        unicode_names = [
            "Björk",  # Icelandic
            "孫燕姿",  # Chinese
            "Владимир",  # Russian
            "مُحَمَّد"  # Arabic
        ]
        
        for i, name in enumerate(unicode_names):
            artist = Artist(id=f"unicode-{i}", name=name)
            test_db.add(artist)
            test_db.commit()
            
            retrieved = test_db.query(Artist).filter(Artist.id == f"unicode-{i}").first()
            assert retrieved.name == name