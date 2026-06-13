from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date as date_type
from typing import Dict, Any
import module.EmplyeeDB as EmplyeeDB
from database import get_db

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/")
def get_attendance(attendance_date: date_type, db: Session = Depends(get_db)):
    """
    Fetches attendance for a specific date. 
    Restricted to current or past dates only.
    """
    # Prevent fetching/generating attendance for future dates
    if attendance_date > date_type.today():
        return []

    # 1. Fetch all ACTIVE employees
    active_employees = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.Status == "Active"
    ).all()

    # 2. Fetch existing records for this date
    existing_records = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.date == attendance_date
    ).all()
    
    # Map for quick lookup
    existing_emp_ids = {r.Emp_id for r in existing_records}

    # 3. Create missing records for active employees
    new_records_added = False
    for emp in active_employees:
        if emp.Emp_id not in existing_emp_ids:
            new_record = EmplyeeDB.Attendance(
                Emp_id=emp.Emp_id,
                employee_name=emp.name, 
                date=attendance_date,
                status="Pending",
                check_in=None,
                check_out=None
            )
            db.add(new_record)
            new_records_added = True
    
    if new_records_added:
        try:
            db.commit()
            # Re-fetch everything to return the complete list
            return db.query(EmplyeeDB.Attendance).filter(
                EmplyeeDB.Attendance.date == attendance_date
            ).all()
        except Exception as e:
            db.rollback()
            print(f"Error syncing attendance: {e}")
            # If commit fails, return whatever we already had
            return existing_records

    return existing_records

@router.patch("/{emp_id}")
def update_attendance(
    emp_id: str, 
    payload: Dict[str, Any], 
    attendance_date: date_type = Query(...), 
    db: Session = Depends(get_db)
):
    if attendance_date > date_type.today():
        raise HTTPException(status_code=400, detail="Cannot update attendance for future dates")

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

@router.get("/record/{emp_id}")
def AttendanceofEmployee(emp_id:str,db:Session = Depends(get_db)):
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == emp_id
    ).all()
    return record

@router.get("/check-status")
def check_attendance_status(attendance_date: date_type, db: Session = Depends(get_db)):
    """
    Diagnostic endpoint to check the sync status of attendance records.
    """
    if attendance_date > date_type.today():
        return {"error": "Cannot check status for future dates", "status": "Invalid Date"}

    active_employees = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.Status == "Active"
    ).all()
    
    existing_records = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.date == attendance_date
    ).all()
    
    active_ids = {e.Emp_id for e in active_employees}
    existing_ids = {r.Emp_id for r in existing_records}
    
    missing_ids = active_ids - existing_ids
    extra_ids = existing_ids - active_ids # Records for inactive/deleted employees
    
    return {
        "date": attendance_date,
        "total_active_employees": len(active_employees),
        "total_attendance_records": len(existing_records),
        "missing_records_count": len(missing_ids),
        "missing_emp_ids": list(missing_ids),
        "extra_records_count": len(extra_ids),
        "status": "Healthy" if len(missing_ids) == 0 else "Out of Sync"
    }

@router.post("/sync-missing")
def sync_missing_attendance(attendance_date: date_type, db: Session = Depends(get_db)):
    """
    Explicitly adds missing attendance records for all active employees for a given date.
    Works for today, yesterday, or any past date.
    """
    if attendance_date > date_type.today():
        raise HTTPException(status_code=400, detail="Cannot sync future dates")

    active_employees = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.Status == "Active"
    ).all()
    
    existing_records = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.date == attendance_date
    ).all()
    
    existing_ids = {r.Emp_id for r in existing_records}

    added_count = 0
    for emp in active_employees:
        if emp.Emp_id not in existing_ids:
            new_record = EmplyeeDB.Attendance(
                Emp_id=emp.Emp_id,
                employee_name=emp.name, 
                date=attendance_date,
                status="Pending",
                check_in=None,
                check_out=None
            )
            db.add(new_record)
            added_count += 1
    
    try:
        db.commit()
        return {"message": f"Added {added_count} missing records for {attendance_date}", "added_count": added_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
