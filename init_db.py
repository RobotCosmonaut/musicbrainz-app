#!/usr/bin/env python3
"""
Database initialization script
Run this once before starting services
"""

import os
import sys
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with tables"""
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/musicbrainz")
    
    logger.info("Initializing database...")
    logger.info(f"Database URL: {DATABASE_URL.replace('password', '***')}")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Wait for database to be ready
    max_retries = 30
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection successful!")
            break
        except OperationalError as e:
            logger.info(f"Waiting for database (attempt {attempt + 1}/{max_retries})...")
            time.sleep(2)
    else:
        logger.error("Could not connect to database!")
        return False
    
    # Create tables
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialization complete!")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
