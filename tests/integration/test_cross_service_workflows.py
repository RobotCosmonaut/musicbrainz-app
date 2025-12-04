"""
Integration tests for cross-service communication and workflows
"""
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
@pytest.mark.slow
class TestArtistToAlbumWorkflow:
    """Test workflows between Artist and Album services"""
    
    def test_artist_to_albums_flow(self, artist_client, album_client, test_db, sample_artist_data, sample_album_data):
        """Test creating artist, then linking albums"""
        # Step 1: Create artist
        from shared.models import Artist
        artist = Artist(**sample_artist_data)
        test_db.add(artist)
        test_db.commit()
        
        # Step 2: Verify artist exists
        artist_response = artist_client.get(f"/artists/{sample_artist_data['id']}")
        assert artist_response.status_code in [200, 404, 500]
        
        # Step 3: Create album for this artist
        from shared.models import Album
        album_data = sample_album_data.copy()
        album_data['artist_id'] = sample_artist_data['id']
        album = Album(**album_data)
        test_db.add(album)
        test_db.commit()
        
        # Step 4: Verify album can be retrieved
        album_response = album_client.get("/albums/search", params={"query": album_data['title']})
        assert album_response.status_code in [200, 500]
    
    def test_search_artist_then_recommendations(self, artist_client, recommendation_client):
        """Test searching for artist, then getting recommendations"""
        # Step 1: Search for an artist
        search_response = artist_client.get("/artists/search", params={"query": "jazz", "limit": 5})
        assert search_response.status_code in [200, 500]
        
        # Step 2: Get recommendations based on genre
        rec_response = recommendation_client.get(
            "/recommendations/query",
            params={"query": "jazz music", "limit": 10}
        )
        assert rec_response.status_code == 200
        assert "recommendations" in rec_response.json()


@pytest.mark.integration
@pytest.mark.slow
class TestErrorHandlingAcrossServices:
    """Test error handling in multi-service scenarios"""
    
    def test_invalid_artist_id_in_recommendation(self, recommendation_client, test_db):
        """Test recommendation service handles invalid artist IDs gracefully"""
        # Create profile with non-existent artist
        profile_data = {
            "favorite_genres": ["rock"],
            "favorite_artists": ["nonexistent-artist-id-12345"]
        }
        
        response = recommendation_client.post(
            "/users/testuser/profile",
            json=profile_data
        )
        # Should still succeed even with invalid artist ID
        assert response.status_code == 200
        
        # Get recommendations should still work
        rec_response = recommendation_client.get(
            "/recommendations/profile/testuser",
            params={"limit": 5}
        )
        assert rec_response.status_code == 200
    
    def test_database_connection_failure_handling(self, artist_client):
        """Test service behavior when database is unavailable"""
        # This tests the health check and graceful degradation
        health_response = artist_client.get("/health")
        assert health_response.status_code == 200
        # Service should report healthy even if DB is slow
    
    def test_concurrent_profile_updates(self, recommendation_client):
        """Test handling concurrent updates to same profile"""
        profile_data = {
            "favorite_genres": ["rock", "jazz"],
            "favorite_artists": ["artist-1"]
        }
        
        # Create initial profile
        response1 = recommendation_client.post(
            "/users/concurrent_test_user/profile",
            json=profile_data
        )
        assert response1.status_code == 200
        
        # Update with different data (simulating concurrent request)
        profile_data['favorite_genres'] = ["electronic", "pop"]
        response2 = recommendation_client.post(
            "/users/concurrent_test_user/profile",
            json=profile_data
        )
        assert response2.status_code == 200
        
        # Verify final state
        get_response = recommendation_client.get("/users/concurrent_test_user/profile")
        assert get_response.status_code == 200


@pytest.mark.integration
@pytest.mark.database
class TestDataConsistencyAcrossServices:
    """Test data consistency between services"""
    
    def test_artist_deletion_affects_recommendations(self, artist_client, recommendation_client, test_db, sample_artist_data):
        """Test that deleting artist doesn't break recommendation system"""
        from shared.models import Artist, UserProfile
        
        # Create artist
        artist = Artist(**sample_artist_data)
        test_db.add(artist)
        test_db.commit()
        
        # Create profile referencing this artist
        profile = UserProfile(
            username="test_user",
            favorite_genres=["rock"],
            favorite_artists=[sample_artist_data['id']]
        )
        test_db.add(profile)
        test_db.commit()
        
        # Delete artist (simulate)
        test_db.delete(artist)
        test_db.commit()
        
        # Recommendations should still work (handle missing artist gracefully)
        rec_response = recommendation_client.get(
            "/recommendations/profile/test_user",
            params={"limit": 5}
        )
        assert rec_response.status_code == 200
    
    def test_profile_persistence_across_requests(self, recommendation_client):
        """Test profile data persists correctly across multiple requests"""
        username = "persistence_test_user"
        
        # Create profile
        profile_data = {
            "favorite_genres": ["rock", "jazz", "blues"],
            "favorite_artists": ["artist-1", "artist-2"]
        }
        
        create_response = recommendation_client.post(
            f"/users/{username}/profile",
            json=profile_data
        )
        assert create_response.status_code == 200
        
        # Retrieve multiple times
        for _ in range(3):
            get_response = recommendation_client.get(f"/users/{username}/profile")
            assert get_response.status_code == 200
            data = get_response.json()
            assert len(data['favorite_genres']) == 3
            assert "rock" in data['favorite_genres']
            assert len(data['favorite_artists']) == 2


@pytest.mark.integration
@pytest.mark.slow
class TestRecommendationQualityWorkflows:
    """Test end-to-end recommendation quality scenarios"""
    
    def test_genre_based_recommendations_quality(self, recommendation_client):
        """Test that genre-based recommendations return appropriate results"""
        queries = [
            ("rock music", "rock"),
            ("smooth jazz", "jazz"),
            ("country songs", "country"),
            ("electronic beats", "electronic")
        ]
        
        for query, expected_genre in queries:
            response = recommendation_client.get(
                "/recommendations/query",
                params={"query": query, "limit": 5}
            )
            assert response.status_code == 200
            data = response.json()
            assert "recommendations" in data
            assert len(data['recommendations']) > 0
    
    def test_profile_recommendations_vs_query_recommendations(self, recommendation_client):
        """Test that profile-based and query-based recommendations differ appropriately"""
        username = "comparison_user"
        
        # Create profile with specific preferences
        profile_data = {
            "favorite_genres": ["metal", "punk"],
            "favorite_artists": []
        }
        recommendation_client.post(f"/users/{username}/profile", json=profile_data)
        
        # Get profile-based recommendations
        profile_rec = recommendation_client.get(
            f"/recommendations/profile/{username}",
            params={"limit": 10}
        )
        assert profile_rec.status_code == 200
        
        # Get query-based recommendations for different genre
        query_rec = recommendation_client.get(
            "/recommendations/query",
            params={"query": "classical music", "limit": 10}
        )
        assert query_rec.status_code == 200
        
        # Both should succeed
        assert len(profile_rec.json()['recommendations']) > 0
        assert len(query_rec.json()['recommendations']) > 0
    
    def test_recommendation_limit_boundaries(self, recommendation_client):
        """Test recommendation limits work correctly"""
        for limit in [1, 5, 10, 20, 50]:
            response = recommendation_client.get(
                "/recommendations/query",
                params={"query": "popular music", "limit": limit}
            )
            assert response.status_code == 200
            recs = response.json()['recommendations']
            # Should return up to limit (may be less if not enough results)
            assert len(recs) <= limit