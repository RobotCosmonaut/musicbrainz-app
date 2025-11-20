import pytest
from fastapi.testclient import TestClient

def test_gateway_health():
    """Test gateway health endpoint"""
    from gateway.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"