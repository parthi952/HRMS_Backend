from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from Auth import roles as roles_util
from Auth.models import User
from Auth.router import get_current_user
from database import get_db
from Festival import common
from Festival.BirthdayService import is_active_employee
from Festival.WorkAnniversaryService import (
    WORK_ANNIVERSARY_SEND_HOUR,
    WORK_ANNIVERSARY_SEND_MINUTE,
    WORK_ANNIVERSARY_TIMEZONE,
    anniversary_in_year,
    completed_years_on,
    get_or_create_work_anniversary_settings,
    today_in_work_anniversary_timezone,
)
import module.EmplyeeDB as EmployeeDB
import module.FestivalDB as FestivalDB


router = APIRouter(prefix="/work-anniversaries", tags=["Employee Work Anniversaries"])


class WorkAnniversarySettingsUpdate(BaseModel):
    subject_template: str = Field(min_length=1, max_length=200)
    message_html: str = Field(min_length=1, max_length=100_000)
    template_id: int | None = None

    @field_validator("subject_template", "message_html")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip()


def _require_admin_or_hr(user: User) -> None:
    if not roles_util.has_role(user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Admin or HR access required.")


def next_work_anniversary(joining_date: date, today: date) -> date:
    candidate = anniversary_in_year(joining_date, today.year)
    # A joining date today is not a completed anniversary; the first is next year.
    if candidate >= today and today.year > joining_date.year:
        return candidate
    return anniversary_in_year(joining_date, max(today.year + 1, joining_date.year + 1))


def _serialize_settings(settings, db: Session):
    resolved_template = common.get_template(settings.template_id, db)
    return {
        "subject_template": settings.subject_template,
        "message_html": settings.message_html,
        "template_id": settings.template_id,
        "resolved_template_id": resolved_template.id if resolved_template else None,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }


def _serialize_layout(template):
    return {
        "id": template.id,
        "name": template.name,
        "header_html": template.header_html,
        "header_bg_color": template.header_bg_color,
        "highlight_html": template.highlight_html or "",
        "highlight_bg_color": template.highlight_bg_color,
        "footer_html": template.footer_html,
        "footer_bg_color": template.footer_bg_color,
        "is_default": template.is_default,
        "logo_url": template.logo_url or "",
        "logo_width": template.logo_width or 120,
        "logo_align": template.logo_align or "center",
    }


@router.get("/settings")
def get_work_anniversary_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin_or_hr(current_user)
    return _serialize_settings(get_or_create_work_anniversary_settings(db), db)


@router.get("/layouts")
def list_work_anniversary_layouts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin_or_hr(current_user)
    templates = db.query(FestivalDB.WishTemplate).order_by(FestivalDB.WishTemplate.name).all()
    return [_serialize_layout(template) for template in templates]


@router.put("/settings")
def update_work_anniversary_settings(
    payload: WorkAnniversarySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin_or_hr(current_user)
    if payload.template_id is not None:
        template_exists = (
            db.query(FestivalDB.WishTemplate.id)
            .filter(FestivalDB.WishTemplate.id == payload.template_id)
            .first()
        )
        if not template_exists:
            raise HTTPException(status_code=400, detail="The selected email layout no longer exists.")

    settings = get_or_create_work_anniversary_settings(db)
    settings.subject_template = payload.subject_template
    settings.message_html = payload.message_html
    settings.template_id = payload.template_id
    db.commit()
    db.refresh(settings)
    return _serialize_settings(settings, db)


@router.get("/overview")
def work_anniversary_overview(
    days: int = Query(90, ge=1, le=366),
    history_limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin_or_hr(current_user)
    today = today_in_work_anniversary_timezone()
    employees = db.query(EmployeeDB.Employee).all()
    active_employees = [employee for employee in employees if is_active_employee(employee)]
    upcoming = []
    missing_joining_date = 0
    missing_email = 0
    next_30_days = 0

    for employee in active_employees:
        email = (employee.email or "").strip()
        if not email:
            missing_email += 1
        if not employee.DateOfJoining:
            missing_joining_date += 1
            continue

        anniversary = next_work_anniversary(employee.DateOfJoining, today)
        days_until = (anniversary - today).days
        years_completed = completed_years_on(employee.DateOfJoining, anniversary)
        if days_until <= 30:
            next_30_days += 1
        if days_until <= days:
            upcoming.append({
                "employee_id": employee.Emp_id,
                "employee_name": (employee.name or employee.f_name or employee.Emp_id).strip(),
                "email": email,
                "department": employee.Department or "",
                "designation": employee.designation or "",
                "date_of_joining": employee.DateOfJoining.isoformat(),
                "next_anniversary": anniversary.isoformat(),
                "years_completed": years_completed,
                "days_until": days_until,
                "email_ready": bool(email),
            })
    upcoming.sort(key=lambda item: (item["days_until"], item["employee_name"].lower()))

    logs = (
        db.query(FestivalDB.WorkAnniversaryWishLog)
        .order_by(FestivalDB.WorkAnniversaryWishLog.created_at.desc())
        .limit(history_limit)
        .all()
    )
    history = [{
        "id": item.id,
        "employee_id": item.emp_id,
        "employee_name": item.employee_name or "",
        "email": item.to_email,
        "anniversary_date": item.anniversary_date.isoformat(),
        "years_completed": item.years_completed,
        "status": item.status,
        "error": item.error,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
    } for item in logs]

    return {
        "schedule": {
            "timezone": WORK_ANNIVERSARY_TIMEZONE,
            "hour": WORK_ANNIVERSARY_SEND_HOUR,
            "minute": WORK_ANNIVERSARY_SEND_MINUTE,
            "display": (
                f"Daily at {WORK_ANNIVERSARY_SEND_HOUR:02d}:"
                f"{WORK_ANNIVERSARY_SEND_MINUTE:02d} ({WORK_ANNIVERSARY_TIMEZONE})"
            ),
        },
        "summary": {
            "active_employees": len(active_employees),
            "today": sum(item["days_until"] == 0 for item in upcoming),
            "next_30_days": next_30_days,
            "missing_date_of_joining": missing_joining_date,
            "missing_email": missing_email,
            "sent": sum(item.status == "sent" for item in logs),
            "failed": sum(item.status == "failed" for item in logs),
        },
        "upcoming": upcoming,
        "history": history,
    }
