"""Automatic employee work-anniversary email delivery."""

import html
import logging
import os
from calendar import monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import SessionLocal
from Festival import EmailSending, common
from Festival.BirthdayService import is_active_employee
import module.EmplyeeDB as EmployeeDB
import module.FestivalDB as FestivalDB


logger = logging.getLogger(__name__)

WORK_ANNIVERSARY_TIMEZONE = os.getenv(
    "WORK_ANNIVERSARY_TIMEZONE",
    os.getenv("BIRTHDAY_TIMEZONE", "Asia/Kolkata"),
)
WORK_ANNIVERSARY_SEND_HOUR = int(os.getenv("WORK_ANNIVERSARY_SEND_HOUR", "9"))
WORK_ANNIVERSARY_SEND_MINUTE = int(os.getenv("WORK_ANNIVERSARY_SEND_MINUTE", "0"))

DEFAULT_WORK_ANNIVERSARY_SUBJECT = "Happy Work Anniversary, {{name}}!"
DEFAULT_WORK_ANNIVERSARY_MESSAGE_HTML = (
    "Dear {{name}},<br/><br/>"
    "Congratulations on completing {{years}} year(s) with TIBOS! "
    "Thank you for your dedication, hard work, and the value you bring to our team."
    "<br/><br/>We wish you continued success and many more milestones with us."
)


def today_in_work_anniversary_timezone() -> date:
    return datetime.now(ZoneInfo(WORK_ANNIVERSARY_TIMEZONE)).date()


def anniversary_in_year(joining_date: date, year: int) -> date:
    """Return this year's observed date; Feb 29 becomes Feb 28 when needed."""
    day = min(joining_date.day, monthrange(year, joining_date.month)[1])
    return date(year, joining_date.month, day)


def completed_years_on(joining_date: date, target_date: date) -> int:
    return target_date.year - joining_date.year


def has_work_anniversary_on(employee: EmployeeDB.Employee, target_date: date) -> bool:
    joining_date = employee.DateOfJoining
    return bool(
        joining_date
        and completed_years_on(joining_date, target_date) >= 1
        and anniversary_in_year(joining_date, target_date.year) == target_date
    )


def _display_name(employee: EmployeeDB.Employee) -> str:
    name = (employee.name or employee.f_name or "Team Member").strip()
    return " ".join(name.split()) or "Team Member"


def _eligible_employees(db: Session, target_date: date):
    employees = (
        db.query(EmployeeDB.Employee)
        .filter(
            EmployeeDB.Employee.DateOfJoining.isnot(None),
            EmployeeDB.Employee.email.isnot(None),
            EmployeeDB.Employee.email != "",
        )
        .all()
    )
    return [
        employee
        for employee in employees
        if is_active_employee(employee) and has_work_anniversary_on(employee, target_date)
    ]


def get_or_create_work_anniversary_settings(
    db: Session,
) -> FestivalDB.WorkAnniversarySettings:
    settings = (
        db.query(FestivalDB.WorkAnniversarySettings)
        .filter(FestivalDB.WorkAnniversarySettings.id == 1)
        .first()
    )
    if settings:
        return settings

    settings = FestivalDB.WorkAnniversarySettings(
        id=1,
        subject_template=DEFAULT_WORK_ANNIVERSARY_SUBJECT,
        message_html=DEFAULT_WORK_ANNIVERSARY_MESSAGE_HTML,
        template_id=None,
    )
    db.add(settings)
    try:
        db.commit()
        db.refresh(settings)
        return settings
    except IntegrityError:
        db.rollback()
        return (
            db.query(FestivalDB.WorkAnniversarySettings)
            .filter(FestivalDB.WorkAnniversarySettings.id == 1)
            .one()
        )


def _claim_delivery(
    db: Session,
    employee: EmployeeDB.Employee,
    anniversary_date: date,
) -> FestivalDB.WorkAnniversaryWishLog | None:
    log = FestivalDB.WorkAnniversaryWishLog(
        emp_id=employee.Emp_id,
        employee_name=_display_name(employee),
        to_email=employee.email.strip(),
        anniversary_date=anniversary_date,
        years_completed=completed_years_on(employee.DateOfJoining, anniversary_date),
        status="processing",
    )
    db.add(log)
    try:
        db.commit()
        db.refresh(log)
        return log
    except IntegrityError:
        db.rollback()
        return None


def _merge_anniversary_content(content: str, name: str, years: int) -> str:
    merged = content.replace("{{years}}", str(years)).replace("{years}", str(years))
    return common.merge_message(merged, name)


def _anniversary_html(
    name: str,
    years: int,
    template,
    message_html: str = DEFAULT_WORK_ANNIVERSARY_MESSAGE_HTML,
) -> str:
    message = _merge_anniversary_content(
        message_html or DEFAULT_WORK_ANNIVERSARY_MESSAGE_HTML,
        html.escape(name),
        years,
    )
    return common.build_email_html("Happy Work Anniversary", template, message)


def _anniversary_subject(
    name: str,
    years: int,
    subject_template: str = DEFAULT_WORK_ANNIVERSARY_SUBJECT,
) -> str:
    subject = _merge_anniversary_content(
        subject_template or DEFAULT_WORK_ANNIVERSARY_SUBJECT,
        name,
        years,
    )
    return " ".join(subject.split()) or f"Happy Work Anniversary, {name}!"


async def send_today_work_anniversary_wishes(
    *,
    target_date: date | None = None,
    db: Session | None = None,
    send_email_fn=None,
) -> dict:
    """Send wishes only when an active employee completes a full work year."""
    anniversary_date = target_date or today_in_work_anniversary_timezone()
    owns_session = db is None
    session = db or SessionLocal()
    sender = send_email_fn or EmailSending.send_email
    result = {
        "date": anniversary_date.isoformat(),
        "eligible": 0,
        "sent": 0,
        "failed": 0,
        "duplicates": 0,
    }

    try:
        employees = _eligible_employees(session, anniversary_date)
        result["eligible"] = len(employees)
        if not employees:
            return result

        settings = get_or_create_work_anniversary_settings(session)
        template = common.get_template(settings.template_id, session)
        if not template:
            logger.error("Work anniversary wishes skipped: no email template configured")
            result["failed"] = len(employees)
            return result

        for employee in employees:
            delivery = _claim_delivery(session, employee, anniversary_date)
            if delivery is None:
                result["duplicates"] += 1
                continue

            name = _display_name(employee)
            years = delivery.years_completed
            try:
                ok, error = await sender(
                    session,
                    _anniversary_subject(name, years, settings.subject_template),
                    _anniversary_html(name, years, template, settings.message_html),
                    employee.email.strip(),
                    [],
                    None,
                )
            except Exception as exc:
                logger.exception("Work anniversary email failed for employee %s", employee.Emp_id)
                ok, error = False, str(exc)

            delivery.status = "sent" if ok else "failed"
            delivery.error = None if ok else (error or "Unknown email delivery error")
            delivery.sent_at = datetime.utcnow() if ok else None
            session.commit()

            if ok:
                result["sent"] += 1
            else:
                result["failed"] += 1

        logger.info("Work anniversary email run completed: %s", result)
        return result
    except Exception:
        session.rollback()
        logger.exception("Work anniversary email run failed for %s", anniversary_date)
        raise
    finally:
        if owns_session:
            session.close()
