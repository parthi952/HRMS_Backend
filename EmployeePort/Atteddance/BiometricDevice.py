import logging
import os
from datetime import datetime

from fastapi import APIRouter, Query, Request, Response

import module.EmplyeeDB as EmplyeeDB
from database import SessionLocal
from Caluclation.AttendanceHours import apply_day_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iclock", tags=["Biometric Device"])

# Comma-separated list of device serial numbers allowed to push data.
# Leave BIOMETRIC_DEVICE_SERIALS unset to accept any device (fine for a single office terminal).
_ALLOWED_SERIALS = {
    s.strip() for s in os.getenv("BIOMETRIC_DEVICE_SERIALS", "").split(",") if s.strip()
}


def _device_allowed(serial: str) -> bool:
    return not _ALLOWED_SERIALS or serial in _ALLOWED_SERIALS


def _apply_punch(db, device_pin: str, punched_at: datetime) -> bool:
    """Map a raw fingerprint punch to check-in/check-out on the day's attendance record."""
    employee = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.device_pin == device_pin
    ).first()
    if not employee:
        logger.warning("Biometric punch from unmapped device PIN %s", device_pin)
        return False

    punch_date = punched_at.date()
    time_str = punched_at.strftime("%I:%M %p")

    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == employee.Emp_id,
        EmplyeeDB.Attendance.date == punch_date,
    ).first()

    if not record:
        record = EmplyeeDB.Attendance(
            Emp_id=employee.Emp_id,
            employee_name=employee.name,
            date=punch_date,
            status="Present",
            check_in=time_str,
            check_out=None,
        )
        db.add(record)
        apply_day_type(db, record)
        return True

    if not record.check_in:
        record.check_in = time_str
        record.status = "Present"
    else:
        # Later punch the same day is treated as the check-out.
        record.check_out = time_str
    apply_day_type(db, record)
    return True


@router.get("/cdata")
def device_handshake(SN: str = Query(default="")):
    """Initial handshake a ZKTeco/eSSL ADMS-compatible terminal makes on boot / reconnect."""
    if not _device_allowed(SN):
        return Response(content="", status_code=403)

    body = (
        f"GET OPTION FROM: {SN}\n"
        "Stamp=9999\n"
        "OpStamp=9999\n"
        "ErrorDelay=30\n"
        "Delay=10\n"
        "TransFlag=1111000000\n"
        "Realtime=1\n"
        "Encrypt=0\n"
    )
    return Response(content=body, media_type="text/plain")


@router.post("/cdata")
async def device_push(request: Request, SN: str = Query(default=""), table: str = Query(default="")):
    """Receives ATTLOG (punch) and OPERLOG (user enrolment) pushes from the device."""
    if not _device_allowed(SN):
        return Response(content="", status_code=403)

    raw = (await request.body()).decode("utf-8", errors="ignore")

    if table.upper() != "ATTLOG":
        # Not a punch batch (e.g. OPERLOG user sync) - acknowledge without processing.
        return Response(content="OK", media_type="text/plain")

    db = SessionLocal()
    processed = 0
    try:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            device_pin, time_str = parts[0], parts[1]
            try:
                punched_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if _apply_punch(db, device_pin, punched_at):
                processed += 1
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed processing biometric ATTLOG push from SN=%s", SN)
    finally:
        db.close()

    return Response(content=str(processed), media_type="text/plain")


@router.get("/getrequest")
def device_poll(SN: str = Query(default="")):
    """The device polls this for pending remote commands - we never queue any."""
    return Response(content="OK", media_type="text/plain")


@router.post("/devicecmd")
async def device_cmd_result(request: Request):
    """The device reports command execution results here - nothing to do with them."""
    await request.body()
    return Response(content="OK", media_type="text/plain")
