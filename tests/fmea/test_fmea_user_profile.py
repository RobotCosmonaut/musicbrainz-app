"""
FMEA Tests: User Profile and Listening History Failure Modes
Failure Modes:
  - Profile save failure (Severity 7)
  - Listening history not saved (Severity 6)
"""

import pytest
import requests
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

GATEWAY_URL = "http://localhost:8000"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/musicbrainz"
)

class TestProfileSaveFailure:

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_profile_save_and_retrieve(self):
        """
        FMEA: Profile should save and be retrievable
        Severity 7: Lost profile = no personalization
        Before Fix: JSON serialization errors caused silent failure
        After Fix: Proper JSON handling with verification
        """
        username = "fmea_test_profile_user"

        payload = {
            "favorite_genres": ["rock", "jazz", "blues"],
            "favorite_artists": ["artist-id-001", "artist-id-002"]
        }

        # Save profile
        save_response = requests.post(
            f"{GATEWAY_URL}/api/users/{username}/profile",
            json=payload,
            timeout=10
        )

        assert save_response.status_code == 200, \
            f"Profile save failed: {save_response.text}"

        # Retrieve profile
        get_response = requests.get(
            f"{GATEWAY_URL}/api/users/{username}/profile",
            timeout=10
        )

        assert get_response.status_code == 200, \
            f"Profile retrieval failed: {get_response.text}"

        data = get_response.json()

        # Verify data integrity
        assert data["favorite_genres"] == payload["favorite_genres"], \
            f"Genres mismatch: saved {payload['favorite_genres']}, got {data['favorite_genres']}"

        assert data["favorite_artists"] == payload["favorite_artists"], \
            f"Artists mismatch"

        print(f"\n✅ Profile save/retrieve working correctly")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_profile_update_overwrites_correctly(self):
        """
        FMEA: Profile update should overwrite, not append
        Severity 7: Data corruption from improper updates
        """
        username = "fmea_test_update_user"

        # Initial save
        requests.post(
            f"{GATEWAY_URL}/api/users/{username}/profile",
            json={"favorite_genres": ["rock"], "favorite_artists": []},
            timeout=10
        )

        # Update
        update_payload = {
            "favorite_genres": ["jazz", "blues"],
            "favorite_artists": []
        }

        requests.post(
            f"{GATEWAY_URL}/api/users/{username}/profile",
            json=update_payload,
            timeout=10
        )

        # Verify
        get_response = requests.get(
            f"{GATEWAY_URL}/api/users/{username}/profile",
            timeout=10
        )

        data = get_response.json()

        # Should only have updated genres, not combined
        assert "rock" not in data["favorite_genres"], \
            "Old genre 'rock' still present after update"

        assert set(data["favorite_genres"]) == {"jazz", "blues"}, \
            f"Expected ['jazz', 'blues'], got {data['favorite_genres']}"

        print(f"\n✅ Profile update overwrites correctly")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_profile_json_serialization(self):
        """
        FMEA: Profile genres should serialize/deserialize correctly
        Severity 7: JSON errors = silent data loss
        Before Fix: json.dumps/loads errors not caught
        After Fix: Proper error handling around JSON operations
        """
        from shared.models import UserProfile
        from shared.database import SessionLocal

        session = SessionLocal()

        try:
            # Simulate what the service does
            genres = ["rock", "jazz", "blues with special chars: é à ü"]
            artists = ["artist-001", "artist-002"]

            # Create profile
            profile = UserProfile(
                username="fmea_json_test_user",
                favorite_genres=json.dumps(genres),
                favorite_artists=json.dumps(artists)
            )
            session.add(profile)
            session.commit()

            # Retrieve and deserialize
            saved = session.query(UserProfile).filter(
                UserProfile.username == "fmea_json_test_user"
            ).first()

            assert saved is not None, "Profile not saved"

            retrieved_genres = json.loads(saved.favorite_genres)
            retrieved_artists = json.loads(saved.favorite_artists)

            assert retrieved_genres == genres, "Genre serialization failed"
            assert retrieved_artists == artists, "Artist serialization failed"

            # Cleanup
            session.delete(saved)
            session.commit()

        finally:
            session.close()

        print(f"\n✅ JSON serialization works correctly")


class TestListeningHistoryNotSaved:

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_listening_history_saved_with_verification(self):
        """
        FMEA: Listening history should be saved and verifiable
        Severity 6: No history = no personalization over time
        Before Fix: FK violations caused silent failures
        After Fix: Profile creation + history with verification
        """
        username = "fmea_history_test_user"

        # First create profile
        requests.post(
            f"{GATEWAY_URL}/api/users/{username}/profile",
            json={"favorite_genres": ["rock"], "favorite_artists": []},
            timeout=10
        )

        # Add listening history
        history_response = requests.post(
            f"{GATEWAY_URL}/api/users/{username}/listening-history",
            params={
                "track_id": "fmea-test-track-001",
                "artist_id": "fmea-test-artist-001",
                "interaction_type": "liked"
            },
            timeout=10
        )

        assert history_response.status_code == 200, \
            f"History save failed: {history_response.text}"

        data = history_response.json()

        # Check verification count from service
        assert "verification_count" in data, \
            "Missing verification_count - history may not be saved"

        assert data["verification_count"] > 0, \
            "verification_count is 0 - history not actually saved"

        print(f"\n✅ Listening history saved and verified")
        print(f"   Verification count: {data['verification_count']}")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_history_without_existing_profile(self):
        """
        FMEA: History save should create profile if not exists
        Severity 6: FK violation crashes service
        Before Fix: FK violation on missing user_id
        After Fix: Auto-creates profile if needed
        """
        # Use unique username with no pre-existing profile
        username = f"fmea_no_profile_user_{int(time.time())}"

        import time

        history_response = requests.post(
            f"{GATEWAY_URL}/api/users/{username}/listening-history",
            params={
                "track_id": "test-track-001",
                "artist_id": "test-artist-001",
                "interaction_type": "played"
            },
            timeout=10
        )

        # Should not fail with FK violation (500)
        assert history_response.status_code != 500, \
            "FK violation on missing profile - auto-create failed"

        assert history_response.status_code == 200, \
            f"History save failed: {history_response.status_code}"

        print(f"\n✅ History saves without pre-existing profile")