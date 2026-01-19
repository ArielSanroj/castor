"""
Migration script to update leads table with new columns.
Adds 'interest' and 'location' columns, makes 'candidacy_type' optional.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from config import Config

def migrate_leads_table():
    """Add new columns to leads table."""
    print("Starting migration for leads table...")
    
    if not Config.DATABASE_URL:
        print("❌ ERROR: DATABASE_URL not configured")
        return False
    
    try:
        engine = create_engine(Config.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if interest column exists
            check_interest = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='leads' AND column_name='interest'
            """))
            
            if check_interest.fetchone() is None:
                print("Adding 'interest' column...")
                conn.execute(text("""
                    ALTER TABLE leads 
                    ADD COLUMN interest VARCHAR(50) NOT NULL DEFAULT 'forecast'
                """))
                conn.commit()
                print("✅ 'interest' column added")
            else:
                print("ℹ️  'interest' column already exists")
            
            # Check if location column exists
            check_location = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='leads' AND column_name='location'
            """))
            
            if check_location.fetchone() is None:
                print("Adding 'location' column...")
                conn.execute(text("""
                    ALTER TABLE leads 
                    ADD COLUMN location VARCHAR(120) NOT NULL DEFAULT 'Bogotá'
                """))
                conn.commit()
                print("✅ 'location' column added")
            else:
                print("ℹ️  'location' column already exists")
            
            # Make candidacy_type nullable
            print("Making 'candidacy_type' nullable...")
            conn.execute(text("""
                ALTER TABLE leads 
                ALTER COLUMN candidacy_type DROP NOT NULL
            """))
            conn.commit()
            print("✅ 'candidacy_type' is now nullable")
            
            # Add index on interest if it doesn't exist
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_leads_interest 
                    ON leads(interest)
                """))
                conn.commit()
                print("✅ Index on 'interest' created/verified")
            except Exception as e:
                print(f"ℹ️  Index on 'interest' may already exist: {e}")
            
            print("\n✅ Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ ERROR during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = migrate_leads_table()
    sys.exit(0 if success else 1)

