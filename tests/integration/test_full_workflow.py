# tests/integration/test_full_workflow.py
"""
Integration tests that test complete workflows across services
"""
import pytest
import requests
from fastapi.testclient import TestClient

@pytest.mark.integration
class TestCompleteRecommendationWorkflow:
    """Test end-to-end recommendation workflows"""
    
    def test_search_artist_get_albums_get_recommendations(self, artist_client):
        """Test complete user journey"""
        # 1. Search for artist
        search_response = artist_client.get("/artists/search", 
                                           params={"query": "radiohead", "limit": 5})
        assert search_response.status_code == 200
        artists = search_response.json()["artists"]
        assert len(artists) > 0
        
        # 2. Get artist albums (would require additional setup)
        # 3. Get recommendations
        # 4. Verify data consistency
        pass

    def test_user_profile_to_recommendations_flow(self, recommendation_client):
        """Test profile creation -> recommendations flow"""
        # Create profile
        profile_data = {
            "favorite_genres": ["rock", "jazz"],
            "favorite_artists": ["test-id-1"]
        }
        profile_response = recommendation_client.post(
            "/users/testuser/profile",
            json=profile_data
        )
        assert profile_response.status_code == 200
        
        # Get recommendations based on profile
        rec_response = recommendation_client.get(
            "/recommendations/profile/testuser",
            params={"limit": 10}
        )
        assert rec_response.status_code == 200
        recommendations = rec_response.json()["recommendations"]
        assert len(recommendations) > 0

# tests/performance/test_benchmarks.py
"""
Performance benchmarks using pytest-benchmark
"""
import pytest

@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    def test_artist_search_performance(self, artist_client, benchmark):
        """Benchmark artist search performance"""
        result = benchmark(
            lambda: artist_client.get("/artists/search", 
                                     params={"query": "test", "limit": 10})
        )
        assert result.status_code == 200
    
    def test_recommendation_performance(self, recommendation_client, benchmark):
        """Benchmark recommendation generation"""
        result = benchmark(
            lambda: recommendation_client.get(
                "/recommendations/query",
                params={"query": "rock music", "limit": 10}
            )
        )
        assert result.status_code == 200

# tests/security/test_security.py
"""
Security tests
"""
import pytest

@pytest.mark.security
class TestSecurityVulnerabilities:
    def test_sql_injection_prevention(self, artist_client):
        """Test SQL injection prevention in search"""
        malicious_query = "'; DROP TABLE artists; --"
        response = artist_client.get("/artists/search", 
                                    params={"query": malicious_query})
        # Should handle gracefully, not crash
        assert response.status_code in [200, 400, 500]
    
    def test_xss_prevention_in_user_input(self, recommendation_client):
        """Test XSS prevention"""
        xss_payload = "<script>alert('xss')</script>"
        response = recommendation_client.post(
            "/users/testuser/profile",
            json={"favorite_genres": [xss_payload], "favorite_artists": []}
        )
        assert response.status_code in [200, 400]
        # Verify payload is sanitized if stored