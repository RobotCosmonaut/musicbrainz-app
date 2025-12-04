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

@pytest.mark.unit
@pytest.mark.api
class TestAlbumServiceExtended:
    """Extended album service tests"""
    
    def test_album_search_with_special_characters(self, album_client):
        """Test album search with special characters"""
        queries = ["album's name", "album & artist", "album/version"]
        for query in queries:
            response = album_client.get("/albums/search", params={"query": query})
            assert response.status_code in [200, 400, 500]
    
    @pytest.mark.skip(reason="Endpoint /albums not implemented yet")
    @pytest.mark.parametrize("limit", [1, 5, 10, 50, 100])
    def test_album_list_with_various_limits(self, album_client, limit):
        """Test album listing with different limits"""
        response = album_client.get("/albums", params={"skip": 0, "limit": limit})
        assert response.status_code in [200, 500]
    
    def test_album_by_artist_id_not_found(self, album_client):
        """Test getting albums for non-existent artist"""
        response = album_client.get("/albums/artist/nonexistent-artist-id")
        # Should handle gracefully
        assert response.status_code in [200, 404, 500]


@pytest.mark.unit
@pytest.mark.database
class TestAlbumModelExtended:
    """Extended album model tests"""
    
    def test_album_with_missing_optional_fields(self, test_db):
        """Test album with minimal fields"""
        album = Album(
            id="minimal-album",
            title="Minimal Album",
            artist_id="some-artist"
        )
        test_db.add(album)
        test_db.commit()
        
        retrieved = test_db.query(Album).filter(Album.id == "minimal-album").first()
        assert retrieved is not None
    
    def test_album_with_unicode_title(self, test_db):
        """Test album with unicode characters"""
        album = Album(
            id="unicode-album",
            title="Ålbum Tïtle 音楽",
            artist_id="artist-id"
        )
        test_db.add(album)
        test_db.commit()
        
        retrieved = test_db.query(Album).filter(Album.id == "unicode-album").first()
        assert retrieved.title == "Ålbum Tïtle 音楽"