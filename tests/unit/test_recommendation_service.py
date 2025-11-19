"""
Unit tests for Recommendation Service
"""

import pytest
from unittest.mock import Mock, patch

class TestRecommendationService:
    """Test suite for recommendation service"""
    
    def test_health_check(self, recommendation_client):
        """Test health endpoint"""
        response = recommendation_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "features" in data
    
    def test_query_recommendations_missing_query(self, recommendation_client):
        """Test recommendations without query parameter"""
        response = recommendation_client.get("/recommendations/query")
        assert response.status_code == 422  # Missing required parameter
    
    def test_query_recommendations_empty_query(self, recommendation_client):
        """Test recommendations with empty query"""
        response = recommendation_client.get("/recommendations/query", params={"query": ""})
        assert response.status_code == 400
        assert "Query parameter is required" in response.json()["detail"]
    
    @pytest.mark.parametrize("limit", [1, 5, 10, 20])
    def test_query_recommendations_limit_bounds(self, recommendation_client, limit):
        """Test recommendation limits"""
        with patch('services.recommendation_service.get_diverse_recommendations') as mock_rec:
            mock_rec.return_value = {
                "recommendations": [],
                "query_analyzed": {},
                "algorithm_version": "test"
            }
            
            response = recommendation_client.get(
                "/recommendations/query",
                params={"query": "test", "limit": limit}
            )
            assert response.status_code == 200
    
    def test_create_profile_new_user(self, recommendation_client):
        """Test creating a new user profile"""
        profile_data = {
            "favorite_genres": ["rock", "jazz"],
            "favorite_artists": ["artist-id-1", "artist-id-2"]
        }
        
        response = recommendation_client.post(
            "/users/testuser/profile",
            json=profile_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert "rock" in data["favorite_genres"]
        assert "jazz" in data["favorite_genres"]
    
    def test_get_profile_not_found(self, recommendation_client):
        """Test getting non-existent profile"""
        response = recommendation_client.get("/users/nonexistent/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["favorite_genres"] == []
        assert data["favorite_artists"] == []

class TestGenreDetection:
    """Test genre detection logic"""
    
    @pytest.mark.parametrize("query,expected_genre", [
        ("old school rap", "hip-hop"),
        ("hip hop beats", "hip-hop"),
        ("rock music", "rock"),
        ("relaxing jazz", "jazz"),
        ("electronic dance", "electronic"),
        ("country ballads", "country"),
    ])
    def test_genre_detection(self, query, expected_genre):
        """Test genre detection from queries"""
        from services.recommendation_service import detect_genre_enhanced
        detected = detect_genre_enhanced(query)
        assert detected == expected_genre