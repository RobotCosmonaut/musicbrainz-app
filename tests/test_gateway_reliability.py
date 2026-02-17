"""
Reliability tests for API Gateway
Measures: Routing Reliability, Timeout Handling, Error Propagation
"""

import pytest
import requests
import concurrent.futures

BASE_URL = "http://localhost:8000"

class TestGatewayReliability:
    
    @pytest.mark.reliability
    def test_routing_reliability(self):
        """Gateway should route to all services reliably"""
        endpoints = [
            ("/api/artists/search", {"query": "test"}),
            ("/api/albums/search", {"artist_name": "test"}),
            ("/api/recommendations/query", {"query": "test", "limit": 5}),
        ]
        
        failures = 0
        total_requests = 0
        
        for endpoint, params in endpoints:
            for _ in range(20):
                total_requests += 1
                try:
                    response = requests.get(
                        f"{BASE_URL}{endpoint}",
                        params=params,
                        timeout=30
                    )
                    # Success if not 5xx error
                    if response.status_code >= 500:
                        failures += 1
                except:
                    failures += 1
        
        reliability = ((total_requests - failures) / total_requests) * 100
        assert reliability >= 95, f"Gateway reliability {reliability}% < 95%"
        
        print(f"\n🚦 Gateway Reliability: {reliability:.1f}%")
    
    @pytest.mark.reliability
    def test_concurrent_routing(self):
        """Gateway should handle concurrent requests to different services"""
        def make_mixed_requests():
            endpoints = [
                "/api/artists/search?query=test",
                "/api/albums/search?artist_name=test",
                "/api/recommendations/query?query=rock&limit=5",
            ]
            
            results = []
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
                    results.append(response.status_code < 500)
                except:
                    results.append(False)
            
            return all(results)
        
        # 15 concurrent users hitting different endpoints
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(make_mixed_requests) for _ in range(15)]
            results = [f.result() for f in futures]
        
        success_rate = (sum(results) / len(results)) * 100
        assert success_rate >= 90, \
            f"Mixed concurrent requests only {success_rate}% successful"
    
    @pytest.mark.reliability
    def test_error_propagation(self):
        """Gateway should properly propagate backend errors"""
        # Invalid artist ID
        response = requests.get(
            f"{BASE_URL}/api/artists/invalid-id-12345",
            timeout=10
        )
        
        # Should get 404, not 500 (proper error propagation)
        assert response.status_code == 404
    
    @pytest.mark.reliability  
    def test_timeout_isolation(self):
        """One slow service shouldn't block others"""
        # Start a potentially slow recommendation request
        slow_response = None
        try:
            slow_response = requests.get(
                f"{BASE_URL}/api/recommendations/query",
                params={"query": "complex query", "limit": 20},
                timeout=1  # Force timeout
            )
        except requests.exceptions.Timeout:
            pass  # Expected
        
        # Fast artist search should still work
        fast_response = requests.get(
            f"{BASE_URL}/api/artists/search",
            params={"query": "Beatles"},
            timeout=5
        )
        
        assert fast_response.status_code == 200, \
            "Fast endpoint blocked by slow endpoint"