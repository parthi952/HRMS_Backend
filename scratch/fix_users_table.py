import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()
db_url = os.getenv("URL_DB")
engine = create_engine(db_url)

print("Dropping 'users' table if it exists...")
with engine.connect() as conn:
    trans = conn.begin()
    try:
        # Drop table users
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        trans.commit()
        print("Dropped table 'users' successfully!")
    except Exception as e:
        trans.rollback()
        print("Failed to drop table:", e)
        sys.exit(1)

# Now import Base and models, and recreate
from database import Base
import Auth.models

print("\nRecreating all tables using metadata...")
try:
    Base.metadata.create_all(bind=engine)
    print("Tables re-created successfully!")
except Exception as e:
    print("Failed to recreate tables:", e)
