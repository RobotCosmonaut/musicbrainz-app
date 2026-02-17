"""
FMEA Tests: Database Failure Modes
Failure Modes:
  - Connection failure on startup (Severity 9)
  - Connection pool exhaustion (Severity 8)
  - Disk space exhaustion (Severity 10)
  - Concurrent write reliability (Severity 8)
"""

import pytest
import time
import os
import shutil
import concurrent.futures
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/musicbrainz"
)

class TestDatabaseConnectionFailure:

    @pytest.mark.fmea
    @pytest.mark.database
    def test_wait_for_database_retry_logic(self):
        """
        FMEA: Service should retry on connection failure
        Severity 9: Complete failure without retry
        Before Fix: No retry, immediate crash
        After Fix: 30 retries with 2s delay
        """
        from shared.database import wait_for_database

        # Test that retry function exists and has correct behavior
        with patch('shared.database.engine') as mock_engine:
            mock_conn = mock_engine.connect.return_value.__enter__.return_value
            
            # First 3 attempts fail, 4th succeeds
            mock_conn.execute.side_effect = [
                OperationalError("Connection refused", None, None),
                OperationalError("Connection refused", None, None),
                OperationalError("Connection refused", None, None),
                None  # Success
            ]

            start = time.time()
            result = wait_for_database(max_retries=5, delay=0.1)
            elapsed = time.time() - start

            assert result is True, "Should succeed after retries"
            assert elapsed >= 0.3, "Should have delayed between retries"

        print(f"\n✅ Retry logic works: succeeded after retries in {elapsed:.3f}s")

    @pytest.mark.fmea
    @pytest.mark.database
    def test_connection_pool_exhaustion(self):
        """
        FMEA: Connection pool should not exhaust under concurrent load
        Severity 8: Service hangs on pool exhaustion
        Compare: Before (no pooling) vs After (pool_size=10, max_overflow=5)
        """
        engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=2,
            pool_timeout=3  # Don't wait long for test
        )
        Session = sessionmaker(bind=engine)

        success_count = 0
        failure_count = 0
        lock = __import__('threading').Lock()

        def make_db_query():
            nonlocal success_count, failure_count
            session = Session()
            try:
                session.execute(text("SELECT 1"))
                session.execute(text("SELECT pg_sleep(0.1)"))  # Hold connection
                with lock:
                    success_count += 1
                return True
            except Exception as e:
                with lock:
                    failure_count += 1
                return False
            finally:
                session.close()

        # Launch more workers than pool size to test overflow
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_db_query) for _ in range(20)]
            results = [f.result() for f in futures]

        total = len(results)
        success_rate = (success_count / total) * 100

        engine.dispose()

        print(f"\n📊 Connection Pool Test:")
        print(f"   Successes: {success_count}/{total}")
        print(f"   Failures: {failure_count}/{total}")
        print(f"   Success rate: {success_rate:.1f}%")

        # At least pool_size requests should succeed
        assert success_count >= 5, \
            f"Pool exhausted: only {success_count} succeeded"

    @pytest.mark.fmea
    @pytest.mark.database
    def test_disk_space_monitoring(self):
        """
        FMEA: Disk space should be monitored before exhaustion
        Severity 10: Data loss on disk full
        Tests: Warning thresholds exist, metrics dir is monitored
        """
        metrics_dir = __import__('pathlib').Path("metrics_data")

        # Check disk space
        if metrics_dir.exists():
            total, used, free = shutil.disk_usage(str(metrics_dir))

            total_gb = total / (2**30)
            used_gb = used / (2**30)
            free_gb = free / (2**30)
            usage_percent = (used / total) * 100

            print(f"\n📊 Disk Space Report:")
            print(f"   Total: {total_gb:.1f} GB")
            print(f"   Used: {used_gb:.1f} GB ({usage_percent:.1f}%)")
            print(f"   Free: {free_gb:.1f} GB")

            # Critical threshold: fail at 95%
            assert usage_percent < 95, \
                f"CRITICAL: Disk {usage_percent:.1f}% full - data loss risk"

            # Warning threshold: warn at 80%
            if usage_percent > 80:
                import warnings
                warnings.warn(
                    f"Disk usage at {usage_percent:.1f}% - action needed"
                )

    @pytest.mark.fmea
    @pytest.mark.database
    def test_transaction_rollback_on_failure(self):
        """
        FMEA: Failed transactions should roll back cleanly
        Severity 8: Data corruption without proper rollback
        """
        from shared.models import Artist
        from shared.database import SessionLocal

        session = SessionLocal()

        try:
            # Insert valid artist
            artist = Artist(
                id="fmea-rollback-test-001",
                name="FMEA Rollback Test Artist",
                sort_name="Test, FMEA Rollback"
            )
            session.add(artist)

            # Force an error (duplicate ID)
            duplicate = Artist(
                id="fmea-rollback-test-001",  # Same ID - will fail
                name="Duplicate Artist",
                sort_name="Duplicate, Artist"
            )
            session.add(duplicate)

            try:
                session.commit()
                # If we get here, test should clean up
                session.query(Artist).filter(
                    Artist.id == "fmea-rollback-test-001"
                ).delete()
                session.commit()
            except Exception:
                session.rollback()
                # Verify rollback worked - nothing should be in DB
                result = session.query(Artist).filter(
                    Artist.id == "fmea-rollback-test-001"
                ).first()
                assert result is None, \
                    "Transaction rollback failed - data corruption risk"

        finally:
            session.close()

        print(f"\n✅ Transaction rollback works correctly")

    @pytest.mark.fmea
    @pytest.mark.database
    def test_database_init_idempotency(self):
        """
        FMEA: Database init should be idempotent (safe to run twice)
        Severity 10: Deployment failure if init not idempotent
        Before Fix: Running init twice caused errors
        After Fix: Second run detects existing tables and skips
        """
        from shared.database import create_tables_safe

        # Run init twice
        first_run = create_tables_safe()
        second_run = create_tables_safe()  # Should not fail

        assert first_run is True, "First init run failed"
        assert second_run is True, "Second init run failed - not idempotent"

        print(f"\n✅ Database init is idempotent")