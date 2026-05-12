from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db

import module.DepartmentDB as DepartmentDB
from module.EmplyeeDB import Employee

from Schemas.DepartmentSchema import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentEmployeeItem,
)

from Caluclation.IdCustom import generate_next_dep_id

router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)


# =====================================================
# GET ALL DEPARTMENTS + employee count
# =====================================================
@router.get("/", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):

    results = (
        db.query(
            DepartmentDB.Department,
            func.count(Employee.Emp_id).label("total_count")
        )
        .outerjoin(
            Employee,
            func.trim(DepartmentDB.Department.Dep_name) == func.trim(Employee.Department)
        )
        .group_by(DepartmentDB.Department.Dep_id)
        .all()
    )

    departments = []
    for dept, total_count in results:
        dept.Total_employees = total_count
        departments.append(dept)

    return departments


# =====================================================
# GET EMPLOYEES IN A DEPARTMENT
# GET /departments/{dep_name}/employees
# =====================================================
@router.get("/{dep_id}/employees", response_model=List[DepartmentEmployeeItem])
def get_employees_by_department(dep_id: str, db: Session = Depends(get_db)):

    # Find Department first
    dept = (
        db.query(DepartmentDB.Department)
        .filter(DepartmentDB.Department.Dep_id == dep_id)
        .first()
    )

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    # Fetch Employees
    all_employees = db.query(Employee).all()

    matched = [
        emp for emp in all_employees
        if (emp.Department or "").strip().lower()
        == (dept.Dep_name or "").strip().lower()
    ]

    return [
        DepartmentEmployeeItem(
            Emp_id=emp.Emp_id,
            name=emp.name or f"{emp.f_name} {emp.l_name}".strip(),
            designation=emp.designation or "",
            emp_type=emp.emp_type or "",
            email=emp.email or "",
            phone=emp.phone or "",
            Status=emp.Status or "Active",
        )
        for emp in matched
    ]
# =====================================================
# GET SINGLE DEPARTMENT
# =====================================================
@router.get("/{dep_id}", response_model=DepartmentResponse)
def get_department_by_id(dep_id: str, db: Session = Depends(get_db)):

    dept = (
        db.query(DepartmentDB.Department)
        .filter(DepartmentDB.Department.Dep_id == dep_id)
        .first()
    )

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    all_employees = db.query(Employee).all()
    count = sum(
        1 for emp in all_employees
        if (emp.Department or "").strip().lower() == (dept.Dep_name or "").strip().lower()
    )

    dept.Total_employees = count
    return dept


# =====================================================
# CREATE DEPARTMENT
# =====================================================
@router.post("/", response_model=DepartmentResponse)
def create_department(dept_data: DepartmentCreate, db: Session = Depends(get_db)):

    new_id = generate_next_dep_id(db)

    new_dept = DepartmentDB.Department(
        Dep_id=new_id,
        Dep_name=dept_data.Dep_name,
        Dep_head=dept_data.Dep_head,
        Dep_icon=dept_data.Dep_icon,
        bg_color=dept_data.bg_color,
        icon_color=dept_data.icon_color,
    )

    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    new_dept.Total_employees = 0
    return new_dept


# =====================================================
# UPDATE DEPARTMENT
# =====================================================
@router.put("/{dep_id}", response_model=DepartmentResponse)
def update_department(dep_id: str, dept_data: DepartmentCreate, db: Session = Depends(get_db)):

    dept = (
        db.query(DepartmentDB.Department)
        .filter(DepartmentDB.Department.Dep_id == dep_id)
        .first()
    )

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    dept.Dep_name = dept_data.Dep_name
    dept.Dep_head = dept_data.Dep_head
    dept.Dep_icon = dept_data.Dep_icon
    dept.bg_color = dept_data.bg_color
    dept.icon_color = dept_data.icon_color

    db.commit()
    db.refresh(dept)

    all_employees = db.query(Employee).all()
    count = sum(
        1 for emp in all_employees
        if (emp.Department or "").strip().lower() == (dept.Dep_name or "").strip().lower()
    )
    dept.Total_employees = count
    return dept


# =====================================================
# DELETE DEPARTMENT
# =====================================================
@router.delete("/{dep_id}")
def delete_department(dep_id: str, db: Session = Depends(get_db)):

    dept = (
        db.query(DepartmentDB.Department)
        .filter(DepartmentDB.Department.Dep_id == dep_id)
        .first()
    )

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    db.delete(dept)
    db.commit()
    return {"message": "Department deleted successfully"}
