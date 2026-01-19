"""
Initialize database tables.
Run this script to create all database tables.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.database_service import DatabaseService
from config import Config

def main():
    """Initialize database."""
    print("Initializing CASTOR ELECCIONES database...")
    
    try:
        # Validate config
        Config.validate()
        
        # Initialize database service
        db_service = DatabaseService()
        
        # Create tables
        db_service.init_db()
        
        print("✅ Database initialized successfully!")
        print(f"Database URL: {Config.DATABASE_URL}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

