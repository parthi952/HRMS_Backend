import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import SessionLocal
from sqlalchemy import text

def debug_fk():
    db = SessionLocal()
    try:
        # Find all employees whose department does not exist in departments table
        query = text("""
            SELECT "Emp_id", "f_name", "Department", LENGTH("Department")
            FROM employees
            WHERE "Department" NOT IN (SELECT "Dep_name" FROM departments)
        """)
        res = db.execute(query).all()
        print('Invalid Employee Depts:', res)
        
        if res:
            print("Fixing invalid depts...")
            for emp_id, name, dept, length in res:
                # Update to match or set to null
                # Let's try to find the closest match in departments
                db.execute(text("UPDATE employees SET \"Department\" = TRIM(\"Department\") WHERE \"Emp_id\" = :eid"), {"eid": emp_id})
            db.commit()
            print("Fix attempted.")
        else:
            print("No invalid depts found according to simple query.")
            
    except Exception as e:
        print(f"Debug failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_fk()
