"""Automatic employee birthday email delivery.

The scheduler calls ``send_today_birthday_wishes`` once per day. Eligibility,
delivery claiming, email rendering, and audit logging live here so main.py only
contains scheduling concerns.
"""

import html
import logging
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import SessionLocal
from Festival import EmailSending, common
import module.EmplyeeDB as EmployeeDB
import module.FestivalDB as FestivalDB


logger = logging.getLogger(__name__)

BIRTHDAY_TIMEZONE = os.getenv("BIRTHDAY_TIMEZONE", "Asia/Kolkata")
BIRTHDAY_SEND_HOUR = int(os.getenv("BIRTHDAY_SEND_HOUR", "9"))
BIRTHDAY_SEND_MINUTE = int(os.getenv("BIRTHDAY_SEND_MINUTE", "0"))

_INACTIVE_STATUSES = {"inactive", "terminated", "resigned", "disabled"}


def today_in_birthday_timezone() -> date:
    """Return the calendar date used by birthday matching."""
    return datetime.now(ZoneInfo(BIRTHDAY_TIMEZONE)).date()


def is_active_employee(employee: EmployeeDB.Employee) -> bool:
    status = (employee.Status or "Active").strip().lower()
    return status not in _INACTIVE_STATUSES


def has_birthday_on(employee: EmployeeDB.Employee, target_date: date) -> bool:
    """Match month/day only so the employee's birth year is ignored."""
    return bool(
        employee.dob
        and employee.dob.month == target_date.month
        and employee.dob.day == target_date.day
    )


def _display_name(employee: EmployeeDB.Employee) -> str:
    name = (employee.name or employee.f_name or "Team Member").strip()
    # Prevent stored newlines from leaking into the email subject header.
    return " ".join(name.split()) or "Team Member"


def _eligible_employees(db: Session, target_date: date):
    employees = (
        db.query(EmployeeDB.Employee)
        .filter(
            EmployeeDB.Employee.dob.isnot(None),
            EmployeeDB.Employee.email.isnot(None),
            EmployeeDB.Employee.email != "",
        )
        .all()
    )
    return [
        employee
        for employee in employees
        if is_active_employee(employee) and has_birthday_on(employee, target_date)
    ]


def _claim_delivery(
    db: Session,
    employee: EmployeeDB.Employee,
    birthday_date: date,
) -> FestivalDB.BirthdayWishLog | None:
    """Atomically claim one employee/date delivery.

    Concurrent workers may both find the employee, but only one can commit this
    unique row. The loser rolls back and skips the email.
    """
    log = FestivalDB.BirthdayWishLog(
        emp_id=employee.Emp_id,
        employee_name=_display_name(employee),
        to_email=employee.email.strip(),
        birthday_date=birthday_date,
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


def _birthday_html(name: str, template) -> str:
    safe_name = html.escape(name)
    message = (
        f"Dear {safe_name},<br/><br/>"
        "Wishing you a very Happy Birthday! May the year ahead bring you "
        "happiness, success, good health, and many wonderful moments."
        "<br/><br/>Best wishes from the entire TIBOS team."
    )
    return common.build_email_html("Happy Birthday", template, message)


async def send_today_birthday_wishes(
    *,
    target_date: date | None = None,
    db: Session | None = None,
    send_email_fn=None,
) -> dict:
    """Send birthday wishes to active employees whose DOB matches today.

    ``target_date``, ``db``, and ``send_email_fn`` are injectable for tests.
    Production callers should use the defaults.
    """
    birthday_date = target_date or today_in_birthday_timezone()
    owns_session = db is None
    session = db or SessionLocal()
    sender = send_email_fn or EmailSending.send_email
    result = {
        "date": birthday_date.isoformat(),
        "eligible": 0,
        "sent": 0,
        "failed": 0,
        "duplicates": 0,
    }

    try:
        employees = _eligible_employees(session, birthday_date)
        result["eligible"] = len(employees)
        if not employees:
            return result

        template = common.get_template(None, session)
        if not template:
            logger.error("Birthday wishes skipped: no email template configured")
            result["failed"] = len(employees)
            return result

        for employee in employees:
            delivery = _claim_delivery(session, employee, birthday_date)
            if delivery is None:
                result["duplicates"] += 1
                continue

            name = _display_name(employee)
            try:
                ok, error = await sender(
                    session,
                    f"Happy Birthday, {name}!",
                    _birthday_html(name, template),
                    employee.email.strip(),
                    [],
                    None,
                )
            except Exception as exc:
                logger.exception("Birthday email failed for employee %s", employee.Emp_id)
                ok, error = False, str(exc)

            delivery.status = "sent" if ok else "failed"
            delivery.error = None if ok else (error or "Unknown email delivery error")
            delivery.sent_at = datetime.utcnow() if ok else None
            session.commit()

            if ok:
                result["sent"] += 1
            else:
                result["failed"] += 1

        logger.info("Birthday email run completed: %s", result)
        return result
    except Exception:
        session.rollback()
        logger.exception("Birthday email run failed for %s", birthday_date)
        raise
    finally:
        if owns_session:
            session.close()
