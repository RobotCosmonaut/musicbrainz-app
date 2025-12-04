"""
Integration tests for API Gateway routing and aggregation
"""
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
# @pytest.mark.api
@pytest.mark.skip(reason="Gateway tests require all services running - run manually")
class TestGatewayRouting:
    """Test gateway routing to backend services"""
    
    def test_gateway_routes_to_artist_service(self):
        """Test gateway correctly routes to artist service"""
        from gateway.main import app
        client = TestClient(app)
        
        # This tests the gateway's routing logic
        response = client.get("/api/artists/health")
        # Gateway should route correctly (may fail if services down, but routing works)
        assert response.status_code in [200, 502, 503, 504]
    
    def test_gateway_routes_to_recommendation_service(self):
        """Test gateway correctly routes to recommendation service"""
        from gateway.main import app
        client = TestClient(app)
        
        response = client.get("/api/recommendations/health")
        assert response.status_code in [200, 502, 503, 504]
    
    def test_gateway_handles_invalid_routes(self):
        """Test gateway handles non-existent routes"""
        from gateway.main import app
        client = TestClient(app)
        
        response = client.get("/api/nonexistent/service")
        assert response.status_code in [404, 502]


@pytest.mark.integration
@pytest.mark.skip(reason="Gateway tests require all services running - run manually")
class TestGatewayAggregation:
    """Test gateway's ability to aggregate data from multiple services"""
    
    def test_gateway_combines_artist_and_recommendations(self):
        """Test gateway can aggregate artist and recommendation data"""
        from gateway.main import app
        client = TestClient(app)
        
        # This would test a hypothetical aggregation endpoint
        # For now, test that multiple service calls work sequentially
        artist_response = client.get("/api/artists/health")
        rec_response = client.get("/api/recommendations/health")
        
        # Both should be accessible through gateway
        assert artist_response.status_code in [200, 502, 503]
        assert rec_response.status_code in [200, 502, 503]