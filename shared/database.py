import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError
from shared.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/musicbrainz")

# Create engine with connection pooling and retry logic
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    echo=False           # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def wait_for_database(max_retries=30, delay=2):
    """Wait for database to be ready"""
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database is ready!")
            return True
        except OperationalError as e:
            logger.info(f"Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(delay)
    
    logger.error("Database failed to become ready!")
    return False

def create_tables_safe():
    """Safely create tables with proper error handling"""
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            # Wait for database first
            if not wait_for_database():
                raise Exception("Database not available")
            
            logger.info(f"Creating tables (attempt {attempt + 1})...")
            
            # Use a transaction to create tables atomically
            with engine.begin() as conn:
                # Check if tables already exist
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'artists'
                """))
                
                if result.fetchone():
                    logger.info("Tables already exist, skipping creation")
                    return True
                
                # Create all tables
                Base.metadata.create_all(bind=engine)
                logger.info("Tables created successfully!")
                return True
                
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error("Failed to create tables after all retries")
                raise e
    
    return False

# Alias for backward compatibility
def create_tables():
    return create_tables_safe()
