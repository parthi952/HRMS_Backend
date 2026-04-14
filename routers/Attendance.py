from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date as date_type
from typing import Dict, Any
import moduels.EmplyeeDB as EmplyeeDB
from database import get_db

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/")
def get_attendance(attendance_date: date_type, db: Session = Depends(get_db)):
    # 1. Fetch existing records for this date
    records = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.date == attendance_date
    ).all()

    # 2. If empty, generate records ONLY for ACTIVE employees
    if not records:
        # ✅ Filter by Status="Active" (ensure 'Status' matches your Employee model field name)
        active_employees = db.query(EmplyeeDB.Employee).filter(
            EmplyeeDB.Employee.Status == "Active"
        ).all()
        
        if not active_employees:
            return []

        for emp in active_employees:
            new_record = EmplyeeDB.Attendance(
                Emp_id=emp.Emp_id,
                employee_name=emp.name, 
                date=attendance_date,
                status="Pending",
                check_in=None,
                check_out=None
            )
            db.add(new_record)
        
        try:
            db.commit()
            records = db.query(EmplyeeDB.Attendance).filter(
                EmplyeeDB.Attendance.date == attendance_date
            ).all()
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            return []

    return records

@router.patch("/{emp_id}")
def update_attendance(
    emp_id: str, 
    payload: Dict[str, Any], 
    attendance_date: date_type = Query(...), 
    db: Session = Depends(get_db)
):
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == emp_id,
        EmplyeeDB.Attendance.date == attendance_date
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Update logic for Status, Check-In, and Check-Out
    if "status" in payload: record.status = payload["status"]
    if "check_in" in payload: record.check_in = payload["check_in"]
    if "check_out" in payload: record.check_out = payload["check_out"]

    db.commit()
    return {"message": "Success"}