from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from Auth.models import User
from Auth.router import get_current_user
import module.FestivalDB as FestivalDB
from Festival import common
from Festival import EmailSending

router = APIRouter(prefix="/commercial", tags=["Commercial Emails"])


import asyncio

def _serialize(e: FestivalDB.CommercialEmail):
    return {
        "id": e.id,
        "name": e.name,
        "subject": e.subject,
        "message": e.message,
        "audience": e.audience or "employees",
        "to_emails": e.to_emails or "",
        "cc_emails": e.cc_emails or "",
        "from_email": e.from_email or "",
        "template_id": e.template_id,
        "enabled": e.enabled,
    }


def _serialize_log(log: FestivalDB.CommercialSendLog):
    return {
        "id": log.id,
        "recipient_name": log.recipient_name,
        "to_email": log.to_email,
        "cc_emails": log.cc_emails,
        "from_email": log.from_email,
        "status": log.status,
        "error": log.error,
        "sent_at": log.sent_at.isoformat() if log.sent_at else None,
    }


@router.get("")
def list_emails(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    emails = db.query(FestivalDB.CommercialEmail).order_by(FestivalDB.CommercialEmail.created_at.desc()).all()
    return [_serialize(e) for e in emails]


@router.post("")
def create_email(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if not data.get("name", "").strip():
        raise HTTPException(status_code=400, detail="name is required")
    audience = data.get("audience", "employees")
    if audience not in ("employees", "customers", "both"):
        audience = "employees"
    email = FestivalDB.CommercialEmail(
        name=data["name"].strip(),
        subject=data.get("subject", "").strip() or data["name"].strip(),
        message=data.get("message", "").strip() or "Hello!",
        audience=audience,
        to_emails=data.get("to_emails", "").strip() or None,
        cc_emails=data.get("cc_emails", "").strip() or None,
        from_email=data.get("from_email", "").strip() or None,
        template_id=data.get("template_id") or None,
        enabled=bool(data.get("enabled", True)),
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return _serialize(email)


@router.put("/{email_id}")
def update_email(email_id: int, data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    email = db.query(FestivalDB.CommercialEmail).filter(FestivalDB.CommercialEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Not found")
    if "name" in data:
        email.name = data["name"].strip() or email.name
    if "subject" in data:
        email.subject = data["subject"].strip() or email.subject
    if "message" in data:
        email.message = data["message"].strip() or email.message
    if "audience" in data and data["audience"] in ("employees", "customers", "both"):
        email.audience = data["audience"]
    if "to_emails" in data:
        email.to_emails = data["to_emails"].strip() or None
    if "cc_emails" in data:
        email.cc_emails = data["cc_emails"].strip() or None
    if "from_email" in data:
        email.from_email = data["from_email"].strip() or None
    if "template_id" in data:
        email.template_id = data["template_id"] or None
    if "enabled" in data:
        email.enabled = bool(data["enabled"])
    db.commit()
    db.refresh(email)
    return _serialize(email)


@router.delete("/{email_id}")
def delete_email(email_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    email = db.query(FestivalDB.CommercialEmail).filter(FestivalDB.CommercialEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(email)
    db.commit()
    return {"message": "Deleted"}


@router.get("/{email_id}/logs")
def get_email_logs(email_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    logs = (
        db.query(FestivalDB.CommercialSendLog)
        .filter(FestivalDB.CommercialSendLog.email_id == email_id)
        .order_by(FestivalDB.CommercialSendLog.sent_at.desc())
        .all()
    )
    return [_serialize_log(l) for l in logs]


async def send_commercial_email(email: FestivalDB.CommercialEmail, db: Session):
    recipients = common.get_recipients(email.audience, db, email.cc_emails or "", email.to_emails or "")
    if not recipients:
        return False, "No recipient emails found. Please add active employees in Employee Management, or add customer emails under Customer Contacts below."

    template = common.get_template(email.template_id, db)
    if not template:
        return False, "No email template configured — add one from Celebrations > Email Templates"

    cfg = EmailSending.get_or_create_config(db)
    batch_size = cfg.batch_size or 30
    delay_seconds = cfg.delay_seconds or 0

    sender_override = (email.from_email or "").strip() or None
    cc_list = [c.strip() for c in (email.cc_emails or "").split(",") if c.strip()]
    sent, failed = 0, 0
    total = len(recipients)

    for idx, (name, to_addr) in enumerate(recipients):
        body_html = common.build_email_html(email.name, template, common.merge_message(email.message, name))
        ok, err = await EmailSending.send_email(db, email.subject, body_html, to_addr, cc_list, sender_override)
        db.add(FestivalDB.CommercialSendLog(
            email_id=email.id,
            email_name=email.name,
            recipient_name=name,
            to_email=to_addr,
            cc_emails=email.cc_emails,
            from_email=sender_override,
            status="sent" if ok else "failed",
            error=None if ok else err,
        ))
        if ok:
            sent += 1
        else:
            failed += 1

        # Batch delay: pause if batch_size reached and more recipients remain
        if (idx + 1) % batch_size == 0 and (idx + 1) < total and delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

    db.commit()

    if sent == 0:
        return False, f"All {failed} email(s) failed to send"
    return True, f"Sent to {sent} recipient(s)" + (f", {failed} failed" if failed else "")


@router.post("/send-now/{email_id}")
async def send_now(email_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    email = db.query(FestivalDB.CommercialEmail).filter(FestivalDB.CommercialEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Not found")
    ok, detail = await send_commercial_email(email, db)
    if not ok:
        raise HTTPException(status_code=502, detail=f"Email not sent: {detail}")
    return {"message": detail}
