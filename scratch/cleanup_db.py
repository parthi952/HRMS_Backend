import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import SessionLocal
import module.EmplyeeDB
import module.DepartmentDB
import module.CandidateDB
import module.PayrollDB
# Import all to avoid mapper errors
from sqlalchemy import text

def cleanup():
    db = SessionLocal()
    try:
        # Trim whitespace from Department names in employees table
        db.execute(text("UPDATE employees SET \"Department\" = TRIM(\"Department\")"))
        
        # Check if all departments in employees exist in departments table
        # If not, we might need to add them or set them to null/something else.
        # For now, let's just trim and see.
        
        db.commit()
        print("Cleanup successful: Trimmed Department names in employees table.")
    except Exception as e:
        db.rollback()
        print(f"Cleanup failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()
