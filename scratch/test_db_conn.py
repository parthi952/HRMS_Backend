import os
import sys
from dotenv import load_dotenv

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from database import engine, SessionLocal, Base
from Auth.models import User

print("1. Checking connection...")
try:
    db = SessionLocal()
    count = db.query(User).count()
    print(f"Connection successful! User count: {count}")
except Exception as e:
    print(f"Error occurred: {e}")
    print("Trying to create tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("create_all completed!")
    except Exception as create_e:
        print(f"Error during create_all: {create_e}")
finally:
    db.close()
