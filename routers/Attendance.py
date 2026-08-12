from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date as date_type
from typing import Dict, Any
import module.EmplyeeDB as EmplyeeDB
from database import get_db
from Auth.router import get_current_user
from Auth.models import User
from Auth import roles as roles_util

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/")
def get_attendance(
    attendance_date: date_type,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not roles_util.has_role(current_user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Access denied. HR or Admin role required.")
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not roles_util.has_role(current_user, "admin", "hr") and emp_id != current_user.emp_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only update your own attendance.")
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
def AttendanceofEmployee(
    emp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not roles_util.has_role(current_user, "admin", "hr") and emp_id != current_user.emp_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only view your own attendance history.")
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == emp_id
    ).all()
    return record

@router.get("/check-status")
def check_attendance_status(
    attendance_date: date_type,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not roles_util.has_role(current_user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Access denied. HR or Admin role required.")
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

@router.put("/check-in")
def admin_check_in(payload: dict, db: Session = Depends(get_db)):
    emp_id = payload.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=400, detail="emp_id is required")
    emp = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    today = date_type.today()
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == emp_id,
        EmplyeeDB.Attendance.date == today
    ).first()
    if not record:
        record = EmplyeeDB.Attendance(
            Emp_id=emp_id,
            employee_name=emp.name,
            date=today,
            status="Pending",
            check_in=None,
            check_out=None
        )
        db.add(record)
    from datetime import datetime
    now_str = datetime.now().strftime("%I:%M %p")
    record.check_in = now_str
    record.status = "Present"
    db.commit()
    return {"message": "Check-in recorded", "check_in": now_str}


@router.put("/check-out")
def admin_check_out(payload: dict, db: Session = Depends(get_db)):
    emp_id = payload.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=400, detail="emp_id is required")
    today = date_type.today()
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == emp_id,
        EmplyeeDB.Attendance.date == today
    ).first()
    if not record or not record.check_in:
        raise HTTPException(status_code=400, detail="Must check in before checking out")
    from datetime import datetime
    now_str = datetime.now().strftime("%I:%M %p")
    record.check_out = now_str
    db.commit()
    return {"message": "Check-out recorded", "check_out": now_str}


@router.put("/update")
def admin_update_attendance(payload: dict, db: Session = Depends(get_db)):
    emp_id = payload.get("Emp_id") or payload.get("emp_id")
    att_date_str = payload.get("date")
    if not emp_id or not att_date_str:
        raise HTTPException(status_code=400, detail="Emp_id and date are required")
    try:
        att_date = date_type.fromisoformat(att_date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == emp_id,
        EmplyeeDB.Attendance.date == att_date
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if "check_in" in payload:
        record.check_in = payload["check_in"]
    if "check_out" in payload:
        record.check_out = payload["check_out"]
    if "status" in payload:
        record.status = payload["status"]
    db.commit()
    return {"message": "Attendance updated"}


@router.post("/bulk")
def bulk_upsert_attendance(records: list, db: Session = Depends(get_db)):
    from datetime import datetime as dt
    count = 0
    for rec in records:
        emp_id = rec.get("Emp_id") or rec.get("emp_id")
        att_date_str = rec.get("date")
        if not emp_id or not att_date_str:
            continue
        try:
            att_date = date_type.fromisoformat(att_date_str)
        except ValueError:
            continue
        record = db.query(EmplyeeDB.Attendance).filter(
            EmplyeeDB.Attendance.Emp_id == emp_id,
            EmplyeeDB.Attendance.date == att_date
        ).first()
        if not record:
            emp = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
            record = EmplyeeDB.Attendance(
                Emp_id=emp_id,
                employee_name=emp.name if emp else emp_id,
                date=att_date,
            )
            db.add(record)
        if "check_in" in rec:
            record.check_in = rec["check_in"]
        if "check_out" in rec:
            record.check_out = rec["check_out"]
        if "status" in rec:
            record.status = rec["status"]
        count += 1
    db.commit()
    return {"message": f"{count} attendance records saved"}


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
