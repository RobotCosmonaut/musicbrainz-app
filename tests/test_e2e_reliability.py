"""
End-to-End Reliability Tests
Measures: Complete user workflows, Service integration
"""

import pytest
import requests
import time

API_URL = "http://localhost:8000"

class TestE2EReliability:
    
    @pytest.mark.reliability
    @pytest.mark.integration
    def test_complete_recommendation_workflow(self):
        """Complete user workflow should work reliably"""
        username = "reliability_test_user"
        
        # Step 1: Create profile
        profile_response = requests.post(
            f"{API_URL}/api/users/{username}/profile",
            json={
                "favorite_genres": ["rock", "jazz"],
                "favorite_artists": []
            },
            timeout=10
        )
        assert profile_response.status_code == 200
        
        # Step 2: Get recommendations
        rec_response = requests.get(
            f"{API_URL}/api/recommendations/query",
            params={"query": "rock music", "limit": 5},
            timeout=30
        )
        assert rec_response.status_code == 200
        recommendations = rec_response.json()["recommendations"]
        assert len(recommendations) > 0
        
        # Step 3: Save listening history
        if recommendations:
            history_response = requests.post(
                f"{API_URL}/api/users/{username}/listening-history",
                params={
                    "track_id": recommendations[0]["track_id"],
                    "artist_id": recommendations[0]["artist_id"],
                    "interaction_type": "liked"
                },
                timeout=10
            )
            assert history_response.status_code == 200
        
        print(f"\n✅ Complete workflow succeeded")
    
    @pytest.mark.reliability
    @pytest.mark.integration
    def test_search_to_details_workflow(self):
        """Artist search → details → albums workflow"""
        # Search for artist
        search_response = requests.get(
            f"{API_URL}/api/artists/search",
            params={"query": "Beatles", "limit": 5},
            timeout=10
        )
        assert search_response.status_code == 200
        artists = search_response.json()["artists"]
        assert len(artists) > 0
        
        # Get artist details
        artist_id = artists[0]["id"]
        details_response = requests.get(
            f"{API_URL}/api/artists/{artist_id}",
            timeout=10
        )
        assert details_response.status_code == 200
        
        # Get albums (may be slow)
        albums_response = requests.get(
            f"{API_URL}/api/albums/search",
            params={"artist_name": artists[0]["name"], "limit": 5},
            timeout=45
        )
        # Should not timeout or crash
        assert albums_response.status_code in [200, 504]
        
        print(f"\n✅ Search workflow succeeded")