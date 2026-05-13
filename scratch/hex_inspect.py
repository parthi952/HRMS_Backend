import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import SessionLocal
from sqlalchemy import text

def hex_inspect():
    db = SessionLocal()
    try:
        res = db.execute(text("SELECT DISTINCT \"Department\", encode(\"Department\"::bytea, 'hex') FROM employees WHERE \"Department\" LIKE 'IT%'"))
        print('Employee IT Depts Hex:', res.all())
        res2 = db.execute(text("SELECT DISTINCT \"Dep_name\", encode(\"Dep_name\"::bytea, 'hex') FROM departments WHERE \"Dep_name\" LIKE 'IT%'"))
        print('Departments IT Hex:', res2.all())
    except Exception as e:
        print(f"Inspection failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    hex_inspect()
