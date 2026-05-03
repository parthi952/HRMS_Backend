from sqlalchemy.orm import Session
from sqlalchemy import func
from moduels import DepartmentDB
import moduels.EmplyeeDB as EmplyeeDB


# emp id generate function
def generate_next_empid(db: Session):
    # 1. Rules (In a real app, fetch these from your Settings table)
    prefix = "EMP"
    separator = "-"
    
    # 2. Find the next number by counting existing records
    count = db.query(func.count(EmplyeeDB.Employee.Emp_id)).scalar()
    next_num = (count or 0) + 1
    
    # 3. Format it: EMP-001, EMP-002, etc.
    return f"{prefix}{separator}{str(next_num).zfill(3)}"



    # department id generation


def generate_next_dep_id(db: Session):
    prefix = "DEP"
    separator = "-"
    
    # EmplyeeDB-ku badhula DepartmentDB use pannanum
    count = db.query(func.count(DepartmentDB.Department.Dep_id)).scalar()
    next_num = (count or 0) + 1
    
    return f"{prefix}{separator}{str(next_num).zfill(3)}"