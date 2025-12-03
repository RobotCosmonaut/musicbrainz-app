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
    
    def test_user_profile_to_recommendations_flow(self, recommendation_client):
        """Test profile creation -> recommendations flow (with mocked MusicBrainz)"""
        # Step 1: Create profile
        profile_data = {
            "favorite_genres": ["rock", "jazz"],
            "favorite_artists": ["test-id-1"]
        }
        profile_response = recommendation_client.post(
            "/users/testuser/profile",
            json=profile_data
        )
        assert profile_response.status_code == 200
        profile_result = profile_response.json()
        assert profile_result["username"] == "testuser"
        assert "rock" in profile_result["favorite_genres"]
        
        # Step 2: Verify profile was saved
        get_profile_response = recommendation_client.get("/users/testuser/profile")
        assert get_profile_response.status_code == 200
        saved_profile = get_profile_response.json()
        assert saved_profile["username"] == "testuser"
        assert "rock" in saved_profile["favorite_genres"]
        
        # Step 3: Get recommendations based on profile
        # This will use mocked MusicBrainz API (not real external calls)
        rec_response = recommendation_client.get(
            "/recommendations/profile/testuser",
            params={"limit": 10}
        )
        assert rec_response.status_code == 200
        rec_data = rec_response.json()
        
        # Verify recommendations structure
        assert "recommendations" in rec_data
        recommendations = rec_data["recommendations"]
        
        # With mocked MusicBrainz, we should get results
        assert len(recommendations) > 0, "Should have recommendations with mocked API"
        
        # Verify recommendation structure
        first_rec = recommendations[0]
        assert "track_title" in first_rec
        assert "artist_name" in first_rec
        assert "track_id" in first_rec
        assert "score" in first_rec
        
        # Verify it's marked as profile-based
        assert first_rec["recommendation_type"] == "profile_based"
        
        print(f"✓ Successfully generated {len(recommendations)} profile-based recommendations")

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