"""
Shared pytest fixtures for Orchestr8r testing
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, patch, MagicMock  # NEW: Add this import
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.models import Base
from shared.database import get_db

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

# NEW FIXTURE: Mock MusicBrainz API
@pytest.fixture(scope="function")
def mock_musicbrainz():
    """Mock MusicBrainz API for all tests - prevents real API calls"""
    # Mock the DiverseMusicBrainzClient class
    with patch('services.recommendation_service.DiverseMusicBrainzClient') as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        
        # Configure mock to return realistic test data
        mock_instance.search_recordings_diverse.return_value = [
            {
                'id': 'mock-track-1',
                'title': 'Mock Rock Song',
                'artist-credit': [{
                    'artist': {
                        'id': 'mock-artist-1',
                        'name': 'Mock Rock Band'
                    }
                }]
            },
            {
                'id': 'mock-track-2',
                'title': 'Mock Jazz Song',
                'artist-credit': [{
                    'artist': {
                        'id': 'mock-artist-2',
                        'name': 'Mock Jazz Artist'
                    }
                }]
            },
            {
                'id': 'mock-track-3',
                'title': 'Another Rock Track',
                'artist-credit': [{
                    'artist': {
                        'id': 'mock-artist-3',
                        'name': 'Another Rock Band'
                    }
                }]
            }
        ]
        
        yield mock_instance

@pytest.fixture(scope="function")
def artist_client(test_db):
    """Test client for artist service"""
    from services.artist_service import app
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def album_client(test_db):
    """Test client for album service"""
    from services.album_service import app
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

# UPDATED FIXTURE: Now includes mock_musicbrainz
@pytest.fixture(scope="function")
def recommendation_client(test_db, mock_musicbrainz):  # CHANGED: Added mock_musicbrainz parameter
    """Test client for recommendation service with mocked MusicBrainz API"""
    from services.recommendation_service import app
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_artist_data():
    """Sample artist data for testing"""
    return {
        "id": "test-artist-123",
        "name": "Test Artist",
        "sort_name": "Artist, Test",
        "type": "Person",
        "country": "US",
        "begin_date": "1990-01-01",
        "end_date": ""
    }

@pytest.fixture
def sample_album_data():
    """Sample album data for testing"""
    return {
        "id": "test-album-456",
        "title": "Test Album",
        "artist_id": "test-artist-123",
        "release_date": "2020-01-01",
        "status": "Official",
        "country": "US"
    }

@pytest.fixture
def sample_track_data():
    """Sample track data for testing"""
    return {
        "id": "test-track-789",
        "title": "Test Track",
        "album_id": "test-album-456",
        "track_number": 1,
        "length": 180000
    }