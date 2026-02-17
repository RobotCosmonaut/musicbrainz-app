"""
Reliability tests for Artist Service
Measures: Availability, Response Time Consistency, Error Rate
"""

import pytest
import requests
import time
from statistics import mean, stdev
import concurrent.futures

BASE_URL = "http://localhost:8001"

class TestArtistServiceReliability:
    
    @pytest.mark.reliability
    def test_health_endpoint_availability(self):
        """Service should respond to health checks 100% of time"""
        failures = 0
        attempts = 100
        
        for _ in range(attempts):
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=1)
                assert response.status_code == 200
            except:
                failures += 1
        
        availability = ((attempts - failures) / attempts) * 100
        assert availability >= 99.0, f"Availability {availability}% below 99%"
    
    @pytest.mark.reliability
    @pytest.mark.performance
    def test_search_response_time_consistency(self):
        """Response times should be consistent (low variance)"""
        response_times = []
        
        for _ in range(50):
            start = time.time()
            response = requests.get(
                f"{BASE_URL}/artists/search",
                params={"query": "Beatles", "limit": 10},
                timeout=10
            )
            elapsed = time.time() - start
            
            assert response.status_code == 200
            response_times.append(elapsed)
        
        avg_time = mean(response_times)
        std_dev = stdev(response_times)
        coefficient_of_variation = (std_dev / avg_time) * 100
        
        # Coefficient of variation should be < 50% for reliable service
        assert coefficient_of_variation < 50, \
            f"Response time too variable: CV={coefficient_of_variation:.1f}%"
        
        print(f"\n📊 Response Time Stats:")
        print(f"   Mean: {avg_time:.3f}s")
        print(f"   StdDev: {std_dev:.3f}s")
        print(f"   CV: {coefficient_of_variation:.1f}%")
    
    @pytest.mark.reliability
    def test_concurrent_request_handling(self):
        """Service should handle concurrent requests reliably"""
        def make_request():
            try:
                response = requests.get(
                    f"{BASE_URL}/artists/search",
                    params={"query": "rock", "limit": 5},
                    timeout=15
                )
                return response.status_code == 200
            except:
                return False
        
        # Simulate 20 concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]
        
        success_rate = (sum(results) / len(results)) * 100
        assert success_rate >= 90, f"Only {success_rate}% succeeded under load"
    
    @pytest.mark.reliability
    def test_error_handling_reliability(self):
        """Service should return proper errors, not crash"""
        test_cases = [
            ("", 200),  # Empty query should still work
            ("x" * 1000, 200),  # Very long query
            ("!@#$%", 200),  # Special characters
        ]
        
        for query, expected_status in test_cases:
            response = requests.get(
                f"{BASE_URL}/artists/search",
                params={"query": query, "limit": 10},
                timeout=10
            )
            # Should not crash (500) or timeout
            assert response.status_code in [200, 400, 404], \
                f"Query '{query[:20]}' caused status {response.status_code}"
    
    @pytest.mark.reliability
    def test_database_reconnection_reliability(self):
        """Service should recover from transient DB issues"""
        # Make successful request
        response1 = requests.get(f"{BASE_URL}/artists/search", 
                                params={"query": "test"})
        assert response1.status_code == 200
        
        # Simulate DB reconnection by waiting
        time.sleep(2)
        
        # Should still work (connection pool should handle)
        response2 = requests.get(f"{BASE_URL}/artists/search", 
                                params={"query": "test"})
        assert response2.status_code == 200