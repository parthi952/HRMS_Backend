import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load from .env directly to avoid local import issues
load_dotenv()
URL_DB = os.getenv("URL_DB")

def migrate():
    if not URL_DB:
        print("URL_DB not found in .env")
        return
        
    engine = create_engine(URL_DB)
    try:
        with engine.connect() as conn:
            print(f"Connecting to {URL_DB.split('@')[-1]}...")
            conn.execute(text('ALTER TABLE interviews ADD COLUMN IF NOT EXISTS "Interview_ID" VARCHAR'))
            conn.commit()
            print("Successfully added Interview_ID column.")
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
