from sqlalchemy.orm import Session
from sqlalchemy import func
from moduels import DepartmentDB
import moduels.EmplyeeDB as EmplyeeDB
import moduels.CustomIDDB as CustomIDDB

def get_active_config(db: Session, category: str):
    """Helper to fetch active settings from the database"""
    return db.query(CustomIDDB.IDConfig).filter(
        CustomIDDB.IDConfig.category == category,
        CustomIDDB.IDConfig.isActive == True
    ).first()

# 1. Dynamic Employee ID Generation
def generate_next_empid(db: Session):
    # Fetch rules from CustomIDDB
    config = get_active_config(db, "EMP")
    
    # Fallback to defaults if no active config is found
    prefix = config.prefix if config else "EMP"
    separator = config.separator if config else "-"
    digit = config.digit if config else 4
    
    # Find the next number
    count = db.query(func.count(EmplyeeDB.Employee.Emp_id)).scalar()
    next_num = (count or 0) + 1
    
    # Use zfill with the dynamic 'digit' value
    return f"{prefix}{separator}{str(next_num).zfill(digit)}"

# 2. Dynamic Department ID Generation
def generate_next_dep_id(db: Session):
    # Fetch rules from CustomIDDB
    config = get_active_config(db, "DEP")
    
    prefix = config.prefix if config else "DEP"
    separator = config.separator if config else "/"
    digit = config.digit if config else 3
    
    count = db.query(func.count(DepartmentDB.Department.Dep_id)).scalar()
    next_num = (count or 0) + 1
    
    return f"{prefix}{separator}{str(next_num).zfill(digit)}"