from datetime import datetime, date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import module.EmplyeeDB as EmplyeeDB
import Schemas.employeeSceema as employeeSceema
from database import get_db
from Auth.router import get_current_user
from Auth.models import User
from Auth import roles as roles_util
from Caluclation.AttendanceHours import get_attendance_settings, apply_day_type

router = APIRouter(prefix="/attendance", tags=["Attendance Regularization"])

_APPROVER_ROLES = ("admin", "hr", "manager", "tl", "team_lead", "teamlead", "lead")


def _is_approver(current_user: User) -> bool:
    role = (current_user.role or "employee").lower()
    return role in _APPROVER_ROLES or roles_util.has_role(current_user, "admin", "hr")


# ─── Settings (customizable full-day / half-day hour thresholds) ─────────────

@router.get("/settings")
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = get_attendance_settings(db)
    return {"full_day_hours": settings.full_day_hours, "half_day_hours": settings.half_day_hours}


@router.put("/settings")
def update_settings(
    payload: employeeSceema.AttendanceSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not roles_util.has_role(current_user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Access denied. HR or Admin role required.")
    if payload.half_day_hours <= 0 or payload.full_day_hours <= payload.half_day_hours:
        raise HTTPException(status_code=400, detail="full_day_hours must be greater than half_day_hours, both positive")

    settings = get_attendance_settings(db)
    settings.full_day_hours = payload.full_day_hours
    settings.half_day_hours = payload.half_day_hours
    db.commit()
    return {"message": "Attendance rules updated", "full_day_hours": settings.full_day_hours, "half_day_hours": settings.half_day_hours}


# ─── Employee: submit / view own regularization requests ─────────────────────

@router.post("/regularize")
def submit_regularization(
    payload: employeeSceema.RegularizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not roles_util.has_role(current_user, "admin", "hr") and payload.Emp_id != current_user.emp_id:
        raise HTTPException(status_code=403, detail="You can only request regularization for your own attendance.")
    if payload.date > date_type.today():
        raise HTTPException(status_code=400, detail="Cannot request regularization for a future date")

    existing_pending = db.query(EmplyeeDB.AttendanceRegularization).filter(
        EmplyeeDB.AttendanceRegularization.Emp_id == payload.Emp_id,
        EmplyeeDB.AttendanceRegularization.date == payload.date,
        EmplyeeDB.AttendanceRegularization.status == "Pending",
    ).first()
    if existing_pending:
        raise HTTPException(status_code=400, detail="A pending regularization request already exists for this date")

    employee = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == payload.Emp_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    request = EmplyeeDB.AttendanceRegularization(
        Emp_id=payload.Emp_id,
        employee_name=employee.name,
        date=payload.date,
        reason=payload.reason,
        requested_check_in=payload.requested_check_in,
        requested_check_out=payload.requested_check_out,
        status="Pending",
        created_at=datetime.now(),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return {"message": "Regularization request submitted", "id": request.id}


@router.get("/regularize/mine")
def my_regularizations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.emp_id:
        return []
    return db.query(EmplyeeDB.AttendanceRegularization).filter(
        EmplyeeDB.AttendanceRegularization.Emp_id == current_user.emp_id
    ).order_by(EmplyeeDB.AttendanceRegularization.created_at.desc()).all()


# ─── Manager/HR/Admin: review requests ────────────────────────────────────────

@router.get("/regularize")
def list_regularizations(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_approver(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view regularization requests")
    query = db.query(EmplyeeDB.AttendanceRegularization)
    if status:
        query = query.filter(EmplyeeDB.AttendanceRegularization.status == status)
    return query.order_by(EmplyeeDB.AttendanceRegularization.created_at.desc()).all()


@router.put("/regularize/{request_id}")
def decide_regularization(
    request_id: int,
    decision: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_approver(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to approve regularization requests")
    if decision not in ("Approved", "Rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'Approved' or 'Rejected'")

    req = db.query(EmplyeeDB.AttendanceRegularization).filter(
        EmplyeeDB.AttendanceRegularization.id == request_id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Regularization request not found")
    if req.status != "Pending":
        raise HTTPException(status_code=400, detail="This request has already been decided")

    req.status = decision
    req.decided_by = current_user.email or current_user.username
    req.decided_at = datetime.now()

    if decision == "Approved":
        record = db.query(EmplyeeDB.Attendance).filter(
            EmplyeeDB.Attendance.Emp_id == req.Emp_id,
            EmplyeeDB.Attendance.date == req.date,
        ).first()
        if not record:
            record = EmplyeeDB.Attendance(
                Emp_id=req.Emp_id,
                employee_name=req.employee_name,
                date=req.date,
                status="Present",
            )
            db.add(record)

        if req.requested_check_in:
            record.check_in = req.requested_check_in
        if req.requested_check_out:
            record.check_out = req.requested_check_out
        record.status = "Present"

        # Regularization always resolves the day as a Full Day, overriding the raw hours check.
        apply_day_type(db, record)
        record.day_type = "Full Day"

    db.commit()
    return {"message": f"Regularization request {decision.lower()}"}
