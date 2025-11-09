#!/usr/bin/env python3
"""Simple database setup script.

Initializes the Supabase (PostgreSQL) database schema for the conversation agent system.
"""

import os
import sys
from pathlib import Path

# Add back_end/speech to path so we can import DatabaseManager
project_root = Path(__file__).parent.parent
speech_path = project_root / "back_end" / "speech"
sys.path.insert(0, str(speech_path))

from dotenv import load_dotenv
from conversation.database import DatabaseManager

# Load environment variables from .env file
load_dotenv()


def main():
    """Main setup function."""
    print("=" * 60)
    print("Database Setup Script")
    print("=" * 60)
    print()
    
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found!")
        print()
        print("Please set DATABASE_URL in your .env file or environment:")
        print()
        print("For Supabase:")
        print("  DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres")
        print()
        print("You can find your connection string in Supabase Dashboard:")
        print("  Settings → Database → Connection string → URI")
        print()
        return 1
    
    print(f"✓ Found DATABASE_URL")
    print(f"  Connection: {database_url.split('@')[-1] if '@' in database_url else 'hidden'}")
    print()
    
    # Try to connect and initialize schema
    try:
        print("Connecting to database...")
        db = DatabaseManager()
        print("✓ Connected successfully")
        print()
        
        print("Initializing schema...")
        db.initialize_schema()
        print("✓ Schema initialized successfully")
        print()
        
        print("=" * 60)
        print("✅ Database setup complete!")
        print("=" * 60)
        print()
        print("Tables created:")
        print("  - person_memories")
        print("  - todos")
        print("  - faces")
        print("  - summaries")
        print()
        
        return 0
        
    except ImportError as e:
        print(f"❌ ERROR: Missing dependency: {e}")
        print()
        print("Please install required packages:")
        print("  pip install psycopg2-binary python-dotenv")
        print()
        return 1
        
    except ConnectionError as e:
        print(f"❌ ERROR: Failed to connect to database: {e}")
        print()
        print("Please check:")
        print("  1. Your Supabase project is active")
        print("  2. DATABASE_URL is correct (from Supabase Dashboard)")
        print("  3. Your IP is allowed in Supabase (Settings → Database → Connection Pooling)")
        print()
        print("Get your connection string from:")
        print("  Supabase Dashboard → Settings → Database → Connection string → URI")
        print()
        return 1
        
    except RuntimeError as e:
        print(f"❌ ERROR: Failed to initialize schema: {e}")
        print()
        print("The migration SQL may have failed. Please check the error above.")
        return 1
        
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Clean up connection
        try:
            if 'db' in locals():
                db.close()
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())

