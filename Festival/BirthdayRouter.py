from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from Auth import roles as roles_util
from Auth.models import User
from Auth.router import get_current_user
from database import get_db
from Festival.BirthdayService import (
    BIRTHDAY_SEND_HOUR,
    BIRTHDAY_SEND_MINUTE,
    BIRTHDAY_TIMEZONE,
    is_active_employee,
    today_in_birthday_timezone,
)
import module.EmplyeeDB as EmployeeDB
import module.FestivalDB as FestivalDB


router = APIRouter(prefix="/birthdays", tags=["Employee Birthdays"])


def _require_admin_or_hr(user: User) -> None:
    if not roles_util.has_role(user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Admin or HR access required.")


def _birthday_in_year(dob: date, year: int) -> date:
    day = min(dob.day, monthrange(year, dob.month)[1])
    return date(year, dob.month, day)


def next_birthday(dob: date, today: date) -> date:
    candidate = _birthday_in_year(dob, today.year)
    return candidate if candidate >= today else _birthday_in_year(dob, today.year + 1)


@router.get("/overview")
def birthday_overview(
    days: int = Query(90, ge=1, le=366),
    history_limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin_or_hr(current_user)
    today = today_in_birthday_timezone()
    employees = db.query(EmployeeDB.Employee).all()
    active_employees = [employee for employee in employees if is_active_employee(employee)]
    upcoming = []
    missing_dob = 0
    missing_email = 0
    next_30_days = 0

    for employee in active_employees:
        if not (employee.email or "").strip():
            missing_email += 1
        if not employee.dob:
            missing_dob += 1
            continue
        birthday = next_birthday(employee.dob, today)
        days_until = (birthday - today).days
        if days_until <= 30:
            next_30_days += 1
        if days_until <= days:
            upcoming.append({
                "employee_id": employee.Emp_id,
                "employee_name": (employee.name or employee.f_name or employee.Emp_id).strip(),
                "email": (employee.email or "").strip(),
                "department": employee.Department or "",
                "designation": employee.designation or "",
                "date_of_birth": employee.dob.isoformat(),
                "next_birthday": birthday.isoformat(),
                "days_until": days_until,
                "email_ready": bool((employee.email or "").strip()),
            })
    upcoming.sort(key=lambda item: (item["days_until"], item["employee_name"].lower()))

    logs = (
        db.query(FestivalDB.BirthdayWishLog)
        .order_by(FestivalDB.BirthdayWishLog.created_at.desc())
        .limit(history_limit)
        .all()
    )
    history = [{
        "id": item.id,
        "employee_id": item.emp_id,
        "employee_name": item.employee_name or "",
        "email": item.to_email,
        "birthday_date": item.birthday_date.isoformat(),
        "status": item.status,
        "error": item.error,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
    } for item in logs]

    return {
        "schedule": {
            "timezone": BIRTHDAY_TIMEZONE,
            "hour": BIRTHDAY_SEND_HOUR,
            "minute": BIRTHDAY_SEND_MINUTE,
            "display": f"Daily at {BIRTHDAY_SEND_HOUR:02d}:{BIRTHDAY_SEND_MINUTE:02d} ({BIRTHDAY_TIMEZONE})",
        },
        "summary": {
            "active_employees": len(active_employees),
            "today": sum(item["days_until"] == 0 for item in upcoming),
            "next_30_days": next_30_days,
            "missing_date_of_birth": missing_dob,
            "missing_email": missing_email,
            "sent": sum(item.status == "sent" for item in logs),
            "failed": sum(item.status == "failed" for item in logs),
        },
        "upcoming": upcoming,
        "history": history,
    }
