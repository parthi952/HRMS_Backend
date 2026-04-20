from sqlalchemy.orm import Session
from sqlalchemy import func
import moduels.EmplyeeDB as EmplyeeDB

def generate_next_empid(db: Session):
    # 1. Rules (In a real app, fetch these from your Settings table)
    prefix = "EMP"
    separator = "-"
    
    # 2. Find the next number by counting existing records
    count = db.query(func.count(EmplyeeDB.Employee.Emp_id)).scalar()
    next_num = (count or 0) + 1
    
    # 3. Format it: EMP-001, EMP-002, etc.
    return f"{prefix}{separator}{str(next_num).zfill(3)}"