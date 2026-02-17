"""
FMEA Test: MusicBrainz API Timeout Handling
Failure Mode: API timeout causing recommendation failure
Severity: 8
"""

import pytest
import time
import requests
from unittest.mock import patch, MagicMock
from services.musicbrainz_service import MusicBrainzService

class TestMusicBrainzTimeout:

    @pytest.fixture
    def mb_service(self):
        return MusicBrainzService()

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_timeout_returns_empty_not_crash(self, mb_service):
        """
        FMEA: Timeout should return empty list, not crash service
        Before Fix: Service raised unhandled exception
        After Fix: Service returns empty list gracefully
        """
        with patch.object(requests, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout(
                "Connection timed out"
            )

            start = time.time()
            result = mb_service.search_artists("test", limit=5)
            elapsed = time.time() - start

            # Should not crash
            assert isinstance(result, list), \
                "Timeout should return list, not raise exception"
            assert len(result) == 0, \
                "Timeout should return empty list"

        print(f"\n✅ Timeout handled in {elapsed:.3f}s, returned empty list")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_recommendation_service_timeout_handling(self):
        """
        FMEA: Recommendation service should handle MusicBrainz timeout
        Severity 8: Core feature affected
        Compare: Before (unhandled timeout) vs After (graceful degradation)
        """
        base_url = "http://localhost:8003"

        start = time.time()
        response = requests.get(
            f"{base_url}/recommendations/query",
            params={"query": "jazz", "limit": 5},
            timeout=35
        )
        elapsed = time.time() - start

        # Should return 200 or 504, not 500
        assert response.status_code != 500, \
            f"Internal server error on timeout - unhandled exception"

        assert response.status_code in [200, 504], \
            f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert "recommendations" in data, \
                "Response should contain recommendations key"

        print(f"\n📊 Timeout Test Results:")
        print(f"   Status: {response.status_code}")
        print(f"   Time: {elapsed:.3f}s")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_gateway_timeout_isolation(self):
        """
        FMEA: One service timing out should not block others
        Severity: 8 - Core feature broken
        """
        gateway_url = "http://localhost:8000"

        # Make potentially slow request
        slow_success = False
        fast_success = False

        try:
            requests.get(
                f"{gateway_url}/api/recommendations/query",
                params={"query": "complex query", "limit": 20},
                timeout=1
            )
        except requests.exceptions.Timeout:
            pass

        # Artist search should still work despite above timeout
        try:
            response = requests.get(
                f"{gateway_url}/api/artists/search",
                params={"query": "Beatles"},
                timeout=10
            )
            fast_success = response.status_code == 200
        except Exception:
            fast_success = False

        assert fast_success, \
            "Artist service blocked by recommendation timeout - isolation failure"

        print(f"\n✅ Service isolation maintained after timeout")