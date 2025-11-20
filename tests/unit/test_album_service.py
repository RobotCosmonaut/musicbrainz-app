import pytest
from shared.models import Album

class TestAlbumService:
    def test_album_search_empty_query(self, album_client):
        """Test album search with empty parameters"""
        response = album_client.get("/albums/search")
        # Should handle gracefully
        assert response.status_code in [200, 400]
    
    def test_album_creation(self, test_db, sample_album_data):
        """Test creating album in database"""
        album = Album(**sample_album_data)
        test_db.add(album)
        test_db.commit()
        
        retrieved = test_db.query(Album).filter(
            Album.id == sample_album_data["id"]
        ).first()
        assert retrieved is not None
        assert retrieved.title == sample_album_data["title"]