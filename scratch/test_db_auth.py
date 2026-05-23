import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import engine, Base
import Auth.models as AuthDB
import module.EmplyeeDB as EmplyeeDB

def main():
    print("Loading environment variables...")
    load_dotenv()
    db_url = os.getenv("URL_DB")
    print(f"Connecting to database: {db_url}")
    
    try:
        # Create all tables including our new Users table
        print("Creating all tables in database...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        
        # Verify table exists in the metadata
        if "users" in Base.metadata.tables:
            print("Verified: 'users' table is present in SQLAlchemy metadata!")
            print("Schema columns:")
            for col in Base.metadata.tables["users"].columns:
                print(f"  - {col.name}: {col.type}")
        else:
            print("Warning: 'users' table not found in metadata.")
            
    except Exception as e:
        print(f"Error occurred during table creation: {e}")

if __name__ == "__main__":
    main()
