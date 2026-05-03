from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import moduels.DepartmentDB as DepartmentDB
from Schemas.DepartmentSchema import DepartmentCreate, DepartmentResponse
from Caluclation.IdCustom import generate_next_dep_id

router = APIRouter(prefix="/departments", tags=["Departments"])


# ✅ GET ALL
@router.get("/", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    return db.query(DepartmentDB.Department).all()

# ✅ GET BY ID (FIXED → str)
@router.get("/{dep_id}", response_model=DepartmentResponse)
def get_department_by_id(dep_id: str, db: Session = Depends(get_db)):
    dept = db.query(DepartmentDB.Department).filter(
        DepartmentDB.Department.Dep_id == dep_id
    ).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    return dept


# ✅ CREATE
@router.post("/", response_model=DepartmentResponse)
def create_department(dept_data: DepartmentCreate, db: Session = Depends(get_db)):
    new_id = generate_next_dep_id(db)

    new_dept = DepartmentDB.Department(
        Dep_id=new_id,
        Dep_name=dept_data.Dep_name,
        Dep_head=dept_data.Dep_head,
        Dep_icon=dept_data.Dep_icon,
        bg_color=dept_data.bg_color,
        icon_color=dept_data.icon_color
    )

    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    return new_dept


# ✅ UPDATE (FIXED → str)
@router.put("/{dep_id}", response_model=DepartmentResponse)
def update_department(dep_id: str, dept_data: DepartmentCreate, db: Session = Depends(get_db)):
    db_dept = db.query(DepartmentDB.Department).filter(
        DepartmentDB.Department.Dep_id == dep_id
    ).first()

    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")

    db_dept.Dep_name = dept_data.Dep_name
    db_dept.Dep_head = dept_data.Dep_head
    db_dept.Dep_icon = dept_data.Dep_icon
    db_dept.bg_color = dept_data.bg_color
    db_dept.icon_color = dept_data.icon_color

    db.commit()
    db.refresh(db_dept)
    return db_dept


# ✅ DELETE (FIXED → str)
@router.delete("/{dep_id}")
def delete_department(dep_id: str, db: Session = Depends(get_db)):
    dept = db.query(DepartmentDB.Department).filter(
        DepartmentDB.Department.Dep_id == dep_id
    ).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    db.delete(dept)
    db.commit()

    return {"message": f"Department {dep_id} deleted successfully"}