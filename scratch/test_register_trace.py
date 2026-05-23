import os
import sys
import traceback
from dotenv import load_dotenv

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

# Pre-import all database modules to avoid SQLAlchemy mapper compilation errors
import module.EmplyeeDB
import module.PayrollDB
import module.ATSScoreDB
import module.CandidateDB
import module.RequirementDB

from database import SessionLocal
from Auth.router import register
from Auth.Schema import UserCreate

def run_test():
    print("Initializing test database session...")
    db = SessionLocal()
    
    # We will try to call the register function directly
    user_data = UserCreate(
        email="test_traceback@example.com",
        password="securepassword123",
        role="employee",
        emp_id=None
    )
    
    try:
        print("Calling register function...")
        res = register(user_data=user_data, db=db)
        print("Success! Created user:", res.email)
        # Clean up the test user
        db.delete(res)
        db.commit()
        print("Cleaned up test user successfully.")
    except Exception as e:
        print("\n--- ERROR DETECTED ---")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
