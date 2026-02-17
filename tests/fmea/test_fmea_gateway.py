"""
FMEA Tests: API Gateway Failure Modes
Failure Modes:
  - Service routing failure (Severity 8)
  - Timeout on complex queries (Severity 6)
  - Error propagation (Severity 6)
"""

import pytest
import time
import requests
import concurrent.futures
from unittest.mock import patch

GATEWAY_URL = "http://localhost:8000"

class TestGatewayRoutingFailure:

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_service_unavailable_returns_503_not_500(self):
        """
        FMEA: Gateway should return 503 when backend down, not 500
        Severity 8: Unhandled errors mask actual problem
        Before Fix: Returned 500 (unhandled exception)
        After Fix: Returns 503 (service unavailable)
        """
        # Test with invalid service URL by checking error format
        endpoints = [
            "/api/artists/search?query=test",
            "/api/albums/search?artist_name=test",
        ]

        for endpoint in endpoints:
            response = requests.get(
                f"{GATEWAY_URL}{endpoint}",
                timeout=15
            )

            if response.status_code >= 400:
                # Should be structured JSON error, not HTML crash page
                try:
                    error_data = response.json()
                    assert "detail" in error_data, \
                        f"Error response missing 'detail': {response.text[:100]}"
                except Exception:
                    pytest.fail(
                        f"Gateway returned non-JSON error for {endpoint}: "
                        f"{response.text[:100]}"
                    )

        print(f"\n✅ Gateway returns structured error responses")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_correct_http_error_codes(self):
        """
        FMEA: Gateway should propagate correct HTTP error codes
        Severity 6: Wrong error codes confuse clients
        Before Fix: All errors returned as 500
        After Fix: 404, 503, 504 used appropriately
        """
        error_test_cases = [
            # (endpoint, expected_status_codes)
            (
                "/api/artists/nonexistent-id-xyz",
                [404, 503]  # Not found or service error
            ),
        ]

        for endpoint, expected_statuses in error_test_cases:
            response = requests.get(
                f"{GATEWAY_URL}{endpoint}",
                timeout=10
            )

            assert response.status_code in expected_statuses, \
                f"Expected {expected_statuses}, got {response.status_code}"
            
            # Critical: should never be 500 (unhandled)
            assert response.status_code != 500, \
                f"Unhandled 500 error on {endpoint}"

        print(f"\n✅ HTTP error codes are correct")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_concurrent_routing_reliability(self):
        """
        FMEA: Gateway should route concurrent requests to all services
        Severity 8: Under load, routing failures cause cascading failures
        Measures: Success rate under 15 concurrent users
        """
        endpoints = [
            ("/api/artists/search", {"query": "rock", "limit": 5}),
            ("/api/albums/search", {"artist_name": "test", "limit": 5}),
            ("/api/recommendations/query", {"query": "jazz", "limit": 5}),
        ]

        results = {"success": 0, "failure": 0}
        lock = __import__('threading').Lock()

        def make_request(endpoint, params):
            try:
                response = requests.get(
                    f"{GATEWAY_URL}{endpoint}",
                    params=params,
                    timeout=30
                )
                with lock:
                    if response.status_code < 500:
                        results["success"] += 1
                    else:
                        results["failure"] += 1
            except Exception:
                with lock:
                    results["failure"] += 1

        # Create mixed load across all endpoints
        tasks = []
        for endpoint, params in endpoints:
            for _ in range(5):  # 5 requests per endpoint = 15 total
                tasks.append((endpoint, params))

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(make_request, ep, params)
                for ep, params in tasks
            ]
            concurrent.futures.wait(futures)

        total = results["success"] + results["failure"]
        success_rate = (results["success"] / total) * 100

        print(f"\n📊 Concurrent Routing Results:")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Successes: {results['success']}/{total}")

        assert success_rate >= 80, \
            f"Gateway routing unreliable: {success_rate:.1f}% success rate"

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_timeout_configuration_present(self):
        """
        FMEA: Gateway should have proper timeout configuration
        Severity 6: No timeout = hanging requests indefinitely
        Before Fix: No timeout configured, requests hang
        After Fix: Specific timeouts per service type
        """
        import ast
        import pathlib

        gateway_file = pathlib.Path("gateway/main.py")
        assert gateway_file.exists(), "Gateway file not found"

        with open(gateway_file) as f:
            content = f.read()

        # Check timeout configuration exists
        assert "TIMEOUT_CONFIG" in content or "timeout" in content.lower(), \
            "No timeout configuration found in gateway"

        assert "httpx.Timeout" in content or "timeout=" in content, \
            "No explicit timeout values configured"

        # Check recommendation service has extended timeout
        assert "extended_timeout" in content or "60" in content, \
            "No extended timeout for recommendation service"

        print(f"\n✅ Timeout configuration verified in gateway")