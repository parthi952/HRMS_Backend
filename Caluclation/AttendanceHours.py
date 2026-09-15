from datetime import date as date_type, datetime
from typing import Optional

from sqlalchemy.orm import Session

import module.EmplyeeDB as EmplyeeDB

_TIME_FORMAT = "%I:%M %p"


def is_weekly_off(day: date_type, settings: EmplyeeDB.AttendanceSettings) -> bool:
    off_days = {d.strip().lower() for d in (settings.weekly_off_days or "").split(",") if d.strip()}
    return day.strftime("%A").lower() in off_days


def is_on_approved_leave(db: Session, emp_id: str, day: date_type) -> bool:
    day_str = day.isoformat()
    return db.query(EmplyeeDB.LeaveHistoryDB).filter(
        EmplyeeDB.LeaveHistoryDB.Emp_id == emp_id,
        EmplyeeDB.LeaveHistoryDB.status == "Approved",
        EmplyeeDB.LeaveHistoryDB.from_date <= day_str,
        EmplyeeDB.LeaveHistoryDB.to_date >= day_str,
    ).first() is not None


def parse_punch_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), _TIME_FORMAT)
    except ValueError:
        return None


def hours_worked(check_in: Optional[str], check_out: Optional[str]) -> Optional[float]:
    """Hours between check-in and check-out on the same day. None if either is missing/unparsable."""
    start = parse_punch_time(check_in)
    end = parse_punch_time(check_out)
    if not start or not end:
        return None
    delta = (end - start).total_seconds() / 3600
    if delta < 0:
        # Handles a check-out logged just after midnight relative to check-in.
        delta += 24
    return round(delta, 2)


def get_attendance_settings(db: Session) -> EmplyeeDB.AttendanceSettings:
    settings = db.query(EmplyeeDB.AttendanceSettings).first()
    if not settings:
        settings = EmplyeeDB.AttendanceSettings(
            full_day_hours=8.5, half_day_hours=4.0,
            shift_start="09:30 AM", shift_end="06:30 PM", weekly_off_days="Sunday",
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def classify_day(
    check_in: Optional[str],
    check_out: Optional[str],
    settings: EmplyeeDB.AttendanceSettings,
    day: Optional[date_type] = None,
    shift: Optional[EmplyeeDB.Shift] = None,
    on_leave: bool = False,
) -> str:
    if day is not None and is_weekly_off(day, settings):
        return "Week Off"
    if on_leave:
        return "Leave"
    if not check_in:
        return "Absent"
    if not check_out:
        return "Pending"
    worked = hours_worked(check_in, check_out)
    if worked is None:
        return "Pending"
    full_day_hours = shift.full_day_hours if shift else settings.full_day_hours
    half_day_hours = shift.half_day_hours if shift else settings.half_day_hours
    if worked >= full_day_hours:
        return "Full Day"
    if worked >= half_day_hours:
        return "Half Day"
    return "Absent"


def apply_day_type(db: Session, record: EmplyeeDB.Attendance) -> None:
    """Recompute and set day_type on an Attendance row from its current check_in/check_out.

    Uses the employee's assigned shift's Full/Half Day hour thresholds when they
    have one, otherwise falls back to the global AttendanceSettings thresholds.
    """
    settings = get_attendance_settings(db)
    employee = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == record.Emp_id).first()
    shift = None
    if employee and employee.shift_id:
        shift = db.query(EmplyeeDB.Shift).filter(EmplyeeDB.Shift.id == employee.shift_id).first()
    on_leave = is_on_approved_leave(db, record.Emp_id, record.date)
    record.day_type = classify_day(record.check_in, record.check_out, settings, record.date, shift, on_leave)
