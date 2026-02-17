"""
Reliability tests for PostgreSQL Database
Measures: Connection Pool, Transaction Reliability, Concurrent Access
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import concurrent.futures
import os

DATABASE_URL = os.getenv("DATABASE_URL", 
                        "postgresql://user:password@localhost:5432/musicbrainz")

class TestDatabaseReliability:
    
    @pytest.mark.reliability
    @pytest.mark.database
    def test_connection_pool_reliability(self):
        """Connection pool should handle concurrent connections"""
        engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=5)
        Session = sessionmaker(bind=engine)
        
        def make_query():
            try:
                session = Session()
                result = session.execute(text("SELECT 1"))
                session.close()
                return True
            except:
                return False
        
        # 20 concurrent connections (tests pool + overflow)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_query) for _ in range(20)]
            results = [f.result() for f in futures]
        
        success_rate = (sum(results) / len(results)) * 100
        assert success_rate >= 95, \
            f"Connection pool only {success_rate}% reliable"
    
    @pytest.mark.reliability
    @pytest.mark.database
    def test_transaction_reliability(self):
        """Transactions should be atomic and consistent"""
        from shared.models import Artist
        from shared.database import SessionLocal
        
        session = SessionLocal()
        
        try:
            # Start transaction
            test_artist = Artist(
                id="test-reliability-001",
                name="Test Reliability Artist",
                sort_name="Artist, Test Reliability"
            )
            session.add(test_artist)
            session.commit()
            
            # Verify saved
            found = session.query(Artist).filter(
                Artist.id == "test-reliability-001"
            ).first()
            assert found is not None
            
            # Cleanup
            session.delete(found)
            session.commit()
            
        except Exception as e:
            session.rollback()
            pytest.fail(f"Transaction failed: {e}")
        finally:
            session.close()
    
    @pytest.mark.reliability
    @pytest.mark.database  
    def test_concurrent_write_reliability(self):
        """Database should handle concurrent writes"""
        from shared.models import Artist
        from shared.database import SessionLocal
        
        def insert_artist(artist_id):
            session = SessionLocal()
            try:
                artist = Artist(
                    id=f"concurrent-test-{artist_id}",
                    name=f"Concurrent Test {artist_id}",
                    sort_name=f"Test, Concurrent {artist_id}"
                )
                session.add(artist)
                session.commit()
                return True
            except:
                session.rollback()
                return False
            finally:
                session.close()
        
        # 10 concurrent writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(insert_artist, i) for i in range(10)]
            results = [f.result() for f in futures]
        
        success_rate = (sum(results) / len(results)) * 100
        
        # Cleanup
        session = SessionLocal()
        try:
            session.execute(text(
                "DELETE FROM artists WHERE id LIKE 'concurrent-test-%'"
            ))
            session.commit()
        finally:
            session.close()
        
        assert success_rate >= 90, \
            f"Concurrent writes only {success_rate}% successful"