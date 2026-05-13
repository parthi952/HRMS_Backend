import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import SessionLocal
from sqlalchemy import text

def inspect():
    db = SessionLocal()
    try:
        res = db.execute(text('SELECT DISTINCT "Department", LENGTH("Department") FROM employees'))
        print('Employee Depts:', res.all())
        res2 = db.execute(text('SELECT DISTINCT "Dep_name", LENGTH("Dep_name") FROM departments'))
        print('Departments:', res2.all())
    except Exception as e:
        print(f"Inspection failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect()
