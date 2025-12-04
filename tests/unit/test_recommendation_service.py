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

@pytest.mark.unit
class TestGenreDetectionEdgeCases:
    """Test genre detection with edge cases"""
    
    @pytest.mark.parametrize("query,expected", [
        ("", None),
        ("   ", None),
        ("xyzabc", None),  # Gibberish
        ("ROCK MUSIC", "rock"),  # Uppercase
        ("RoCk MuSiC", "rock"),  # Mixed case
        ("rock rock rock", "rock"),  # Repeated
    ])
    def test_genre_detection_edge_cases(self, query, expected):
        """Test genre detection with various edge cases"""
        from services.recommendation_service import detect_genre_enhanced
        result = detect_genre_enhanced(query)
        if expected is None:
            assert result in [None, "pop"]  # Default genre
        else:
            assert result == expected


@pytest.mark.unit
@pytest.mark.api
class TestRecommendationServiceInputValidation:
    """Test input validation and error handling"""
    
    def test_profile_creation_with_empty_lists(self, recommendation_client):
        """Test creating profile with empty favorite lists"""
        profile_data = {
            "favorite_genres": [],
            "favorite_artists": []
        }
        response = recommendation_client.post("/users/empty_user/profile", json=profile_data)
        assert response.status_code == 200
    
    def test_profile_creation_with_duplicate_genres(self, recommendation_client):
        """Test profile handles duplicate genres"""
        profile_data = {
            "favorite_genres": ["rock", "rock", "rock"],
            "favorite_artists": []
        }
        response = recommendation_client.post("/users/dup_user/profile", json=profile_data)
        assert response.status_code == 200
    
    @pytest.mark.parametrize("username", [
        "user-with-dashes",
        "user_with_underscores",
        "user123",
        "USER",
        "a",  # Single character
    ])
    def test_profile_with_various_usernames(self, recommendation_client, username):
        """Test profile creation with various username formats"""
        profile_data = {
            "favorite_genres": ["rock"],
            "favorite_artists": []
        }
        response = recommendation_client.post(f"/users/{username}/profile", json=profile_data)
        assert response.status_code == 200
    
    def test_recommendations_with_negative_limit(self, recommendation_client):
        """Test recommendations with negative limit"""
        response = recommendation_client.get(
            "/recommendations/query",
            params={"query": "test", "limit": -5}
        )
        # Should handle gracefully (422 validation error or default to positive)
        assert response.status_code in [200, 422]


@pytest.mark.unit
class TestRecommendationAlgorithmLogic:
    """Test recommendation algorithm logic in isolation"""
    
    def test_diversity_algorithm_with_mock_data(self):
        """Test that diversity algorithm produces varied results"""
        from services.recommendation_service import get_diverse_recommendations
        
        with patch('services.recommendation_service.DiverseMusicBrainzClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.search_recordings_diverse.return_value = [
                {'id': f'track-{i}', 'title': f'Song {i}', 
                 'artist-credit': [{'artist': {'name': f'Artist {i}'}}]}
                for i in range(20)
            ]
            
            result = get_diverse_recommendations("test query", limit=10)
            
            assert 'recommendations' in result
            assert len(result['recommendations']) <= 10
            assert 'query_analyzed' in result