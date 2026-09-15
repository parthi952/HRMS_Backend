from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import module.EmplyeeDB as EmplyeeDB
from database import get_db
from Auth.router import get_current_user
from Auth.models import User
from Auth import roles as roles_util
from Caluclation.AttendanceHours import hours_worked

router = APIRouter(prefix="/attendance/report", tags=["Attendance Report"])


@router.get("/summary")
def attendance_summary(
    start_date: date_type = Query(...),
    end_date: date_type = Query(...),
    department: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not roles_util.has_role(current_user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Access denied. HR or Admin role required.")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

    employees_query = db.query(EmplyeeDB.Employee)
    if department:
        employees_query = employees_query.filter(EmplyeeDB.Employee.Department == department)
    employees = employees_query.all()
    emp_by_id = {e.Emp_id: e for e in employees}

    records = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.date >= start_date,
        EmplyeeDB.Attendance.date <= end_date,
        EmplyeeDB.Attendance.Emp_id.in_(emp_by_id.keys()),
    ).all() if emp_by_id else []

    summary = {
        emp_id: {
            "Emp_id": emp_id,
            "employee_name": emp.name,
            "Department": emp.Department,
            "full_day": 0, "half_day": 0, "absent": 0, "week_off": 0, "pending": 0,
            "total_hours": 0.0,
        }
        for emp_id, emp in emp_by_id.items()
    }

    for r in records:
        row = summary.get(r.Emp_id)
        if not row:
            continue
        day_type = r.day_type or "Pending"
        if day_type == "Full Day":
            row["full_day"] += 1
        elif day_type == "Half Day":
            row["half_day"] += 1
        elif day_type == "Absent":
            row["absent"] += 1
        elif day_type == "Week Off":
            row["week_off"] += 1
        else:
            row["pending"] += 1

        worked = hours_worked(r.check_in, r.check_out)
        if worked:
            row["total_hours"] = round(row["total_hours"] + worked, 2)

    return sorted(summary.values(), key=lambda r: r["employee_name"] or "")
