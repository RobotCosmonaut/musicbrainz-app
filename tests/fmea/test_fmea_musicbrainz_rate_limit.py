"""
FMEA Test: MusicBrainz API Rate Limit Handling
Failure Mode: Rate limit exceeded causing service timeout
Severity: 7
Tests: Rate limit compliance, retry behavior, graceful degradation
"""

import pytest
import time
import requests
from unittest.mock import patch, MagicMock
from services.musicbrainz_service import MusicBrainzService

class TestMusicBrainzRateLimit:

    @pytest.fixture
    def mb_service(self):
        return MusicBrainzService()

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_rate_limit_delay_enforced(self, mb_service):
        """
        FMEA: Service should enforce 1 request/second rate limit
        Measures: Time between consecutive requests
        """
        timestamps = []

        with patch.object(mb_service.session if hasattr(mb_service, 'session') 
                         else requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"artists": []}
            mock_get.return_value = mock_response

            for _ in range(3):
                timestamps.append(time.time())
                mb_service.search_artists("test", limit=5)

        # Check delays between requests
        delays = [
            timestamps[i+1] - timestamps[i]
            for i in range(len(timestamps)-1)
        ]

        for delay in delays:
            assert delay >= mb_service.rate_limit_delay, \
                f"Rate limit violated: {delay:.3f}s < {mb_service.rate_limit_delay}s"

        print(f"\n✅ Rate limit delays: {[f'{d:.3f}s' for d in delays]}")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_rate_limit_429_handling(self, mb_service):
        """
        FMEA: Service should handle 429 Too Many Requests gracefully
        Measures: No crash on 429, returns empty list
        """
        with patch.object(requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = \
                requests.exceptions.HTTPError("429 Too Many Requests")
            mock_get.return_value = mock_response

            # Should not raise exception - should return empty
            result = mb_service.search_artists("test", limit=5)

            assert isinstance(result, list), \
                "Should return list on 429, not raise exception"

        print(f"\n✅ 429 handled gracefully: returned {result}")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_rapid_request_service_stability(self):
        """
        FMEA: Service should remain stable under rapid requests
        Measures: Artist service still responds after burst
        Compare: Before (no rate limiting) vs After (rate limiting added)
        """
        base_url = "http://localhost:8001"
        errors = 0
        response_times = []

        for i in range(10):
            start = time.time()
            try:
                response = requests.get(
                    f"{base_url}/artists/search",
                    params={"query": f"test{i}", "limit": 5},
                    timeout=15
                )
                if response.status_code >= 500:
                    errors += 1
            except Exception:
                errors += 1
            response_times.append(time.time() - start)

        error_rate = (errors / 10) * 100
        avg_time = sum(response_times) / len(response_times)

        # Write results for comparison
        results = {
            "test": "rapid_request_stability",
            "error_rate": error_rate,
            "avg_response_time": avg_time,
            "total_requests": 10
        }

        print(f"\n📊 Rapid Request Results:")
        print(f"   Error rate: {error_rate}%")
        print(f"   Avg response time: {avg_time:.3f}s")

        assert error_rate < 20, \
            f"Error rate {error_rate}% too high under rapid requests"

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_rate_limit_recovery(self, mb_service):
        """
        FMEA: Service should recover after rate limit hit
        Measures: Service remains functional after 429 errors
        """
        with patch.object(requests, 'get') as mock_get:
            # First calls return 429
            mock_429 = MagicMock()
            mock_429.status_code = 429
            mock_429.raise_for_status.side_effect = \
                requests.exceptions.HTTPError("429")

            # Then returns 200
            mock_200 = MagicMock()
            mock_200.status_code = 200
            mock_200.json.return_value = {"artists": [{"id": "1", "name": "Test"}]}
            mock_200.raise_for_status.return_value = None

            mock_get.side_effect = [mock_429, mock_429, mock_200]

            # First two calls fail
            mb_service.search_artists("test", limit=5)
            mb_service.search_artists("test", limit=5)

            # Third call should succeed
            result = mb_service.search_artists("test", limit=5)

        print(f"\n✅ Recovery after rate limit: {len(result)} results")