import os
import uuid
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import httpx

from database import get_db, SessionLocal
from Auth.models import User
from Auth.router import get_current_user
from Auth.sso_router import _load_config as _load_sso_config
from FileUpload.BlobFile import upload_file
import module.FestivalDB as FestivalDB
import module.EmplyeeDB as EmplyeeDB

router = APIRouter(prefix="/festivals", tags=["Festival Wishes"])

# Automated startup migration for columns added after the table already
# existed in production (Base.metadata.create_all only creates new tables,
# it never alters existing ones).
try:
    from database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        for col in [
            "ALTER TABLE festival_wishes ADD COLUMN audience VARCHAR DEFAULT 'employees';",
            "ALTER TABLE festival_wishes ADD COLUMN cc_emails VARCHAR;",
            "ALTER TABLE festival_wishes ADD COLUMN from_email VARCHAR;",
        ]:
            try:
                conn.execute(text(col))
                conn.commit()
            except Exception:
                conn.rollback()
except Exception:
    pass


def _is_today(wish: FestivalDB.FestivalWish, today: date) -> bool:
    if wish.recurs_yearly:
        return wish.date.month == today.month and wish.date.day == today.day
    return wish.date == today


def _serialize(w: FestivalDB.FestivalWish):
    return {
        "id": w.id,
        "name": w.name,
        "date": w.date.isoformat(),
        "message": w.message,
        "recurs_yearly": w.recurs_yearly,
        "enabled": w.enabled,
        "audience": w.audience or "employees",
        "cc_emails": w.cc_emails or "",
        "from_email": w.from_email or "",
    }


def _serialize_log(log: FestivalDB.WishSendLog):
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


def _serialize_contact(c: FestivalDB.WishContact):
    return {"id": c.id, "name": c.name, "email": c.email, "enabled": c.enabled}


@router.get("/today")
def get_today_wish(db: Session = Depends(get_db)):
    today = date.today()
    wishes = db.query(FestivalDB.FestivalWish).filter(FestivalDB.FestivalWish.enabled == True).all()
    for w in wishes:
        if _is_today(w, today):
            return _serialize(w)
    return None


@router.get("")
def list_wishes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    wishes = db.query(FestivalDB.FestivalWish).order_by(FestivalDB.FestivalWish.date).all()
    return [_serialize(w) for w in wishes]


@router.post("")
def create_wish(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    try:
        wish_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    audience = data.get("audience", "employees")
    if audience not in ("employees", "customers", "both"):
        audience = "employees"
    wish = FestivalDB.FestivalWish(
        name=data.get("name", "").strip() or "Festival",
        date=wish_date,
        message=data.get("message", "").strip() or "Wishing you a happy celebration!",
        recurs_yearly=bool(data.get("recurs_yearly", True)),
        enabled=bool(data.get("enabled", True)),
        audience=audience,
        cc_emails=data.get("cc_emails", "").strip() or None,
        from_email=data.get("from_email", "").strip() or None,
    )
    db.add(wish)
    db.commit()
    db.refresh(wish)
    return _serialize(wish)


@router.put("/{wish_id}")
def update_wish(wish_id: int, data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    wish = db.query(FestivalDB.FestivalWish).filter(FestivalDB.FestivalWish.id == wish_id).first()
    if not wish:
        raise HTTPException(status_code=404, detail="Not found")
    if "name" in data:
        wish.name = data["name"].strip() or wish.name
    if "date" in data:
        try:
            wish.date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    if "message" in data:
        wish.message = data["message"].strip() or wish.message
    if "recurs_yearly" in data:
        wish.recurs_yearly = bool(data["recurs_yearly"])
    if "enabled" in data:
        wish.enabled = bool(data["enabled"])
    if "audience" in data and data["audience"] in ("employees", "customers", "both"):
        wish.audience = data["audience"]
    if "cc_emails" in data:
        wish.cc_emails = data["cc_emails"].strip() or None
    if "from_email" in data:
        wish.from_email = data["from_email"].strip() or None
    db.commit()
    db.refresh(wish)
    return _serialize(wish)


@router.delete("/{wish_id}")
def delete_wish(wish_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    wish = db.query(FestivalDB.FestivalWish).filter(FestivalDB.FestivalWish.id == wish_id).first()
    if not wish:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(wish)
    db.commit()
    return {"message": "Deleted"}


# ── Customer / external contacts (audience for "customers" / "both" sends) ──

@router.get("/contacts")
def list_contacts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    contacts = db.query(FestivalDB.WishContact).order_by(FestivalDB.WishContact.name).all()
    return [_serialize_contact(c) for c in contacts]


@router.post("/contacts")
def create_contact(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    if not name or not email:
        raise HTTPException(status_code=400, detail="name and email are required")
    contact = FestivalDB.WishContact(name=name, email=email, enabled=bool(data.get("enabled", True)))
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _serialize_contact(contact)


@router.put("/contacts/{contact_id}")
def update_contact(contact_id: int, data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    contact = db.query(FestivalDB.WishContact).filter(FestivalDB.WishContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Not found")
    if "name" in data:
        contact.name = data["name"].strip() or contact.name
    if "email" in data:
        contact.email = data["email"].strip() or contact.email
    if "enabled" in data:
        contact.enabled = bool(data["enabled"])
    db.commit()
    db.refresh(contact)
    return _serialize_contact(contact)


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    contact = db.query(FestivalDB.WishContact).filter(FestivalDB.WishContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(contact)
    db.commit()
    return {"message": "Deleted"}


@router.post("/upload-image")
def upload_wish_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    url = upload_file(file.file, file.filename or f"{uuid.uuid4()}.png", folder="festival_images")
    return {"url": url}


@router.get("/{wish_id}/logs")
def get_wish_logs(wish_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    logs = (
        db.query(FestivalDB.WishSendLog)
        .filter(FestivalDB.WishSendLog.wish_id == wish_id)
        .order_by(FestivalDB.WishSendLog.sent_at.desc())
        .all()
    )
    return [_serialize_log(l) for l in logs]


async def _get_graph_token(m: dict):
    tenant = m.get("tenant", "common")
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": m["client_id"],
                "client_secret": m["client_secret"],
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
        )
        tokens = token_resp.json()
        return tokens.get("access_token"), tokens.get("error_description")


async def _send_single_email(
    client: httpx.AsyncClient,
    access_token: str,
    sender: str,
    subject: str,
    body_html: str,
    to_email: str,
    cc_list: list = None,
):
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": "true",
    }
    if cc_list:
        payload["message"]["ccRecipients"] = [{"emailAddress": {"address": c}} for c in cc_list]
    resp = await client.post(
        f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
        headers={"Authorization": f"Bearer {access_token}"},
        json=payload,
    )
    return resp.status_code == 202, (resp.text if resp.status_code != 202 else None)


def _merge_message(message: str, name: str) -> str:
    """Simple mail-merge: replaces {{name}} / {name} placeholders with the recipient's name."""
    return (
        message
        .replace("{{name}}", name).replace("{{Name}}", name)
        .replace("{name}", name).replace("{Name}", name)
    )


def _build_wish_html(wish: FestivalDB.FestivalWish, message: str = None) -> str:
    message = message if message is not None else wish.message
    return f"""
<table cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;width:525pt;max-width:100%;font-family:Aptos, Calibri, Helvetica, sans-serif;">
  <tr>
    <td style="background-color:#9EE4FF;padding:22.5pt 15pt 18.75pt;text-align:center;color:#000;">
      <div style="line-height:120%;margin:0 0 8pt;font-family:Verdana, Geneva, sans-serif;font-size:18pt;font-weight:bold;">{wish.name}</div>
      <div style="line-height:120%;margin:0 0 8pt;font-family:'Trebuchet MS', Trebuchet, sans-serif;font-size:20pt;font-weight:bold;">🎉 Wishing You a Very Happy {wish.name}! 🎉</div>
    </td>
  </tr>
  <tr>
    <td style="padding:26.25pt 26.25pt 11.25pt;">
      <div style="line-height:1.38;margin:0 0 8pt;font-size:11pt;color:#000;">{message}</div>
    </td>
  </tr>
  <tr>
    <td style="padding:11.25pt 26.25pt 18.75pt;">
      <table cellspacing="0" cellpadding="0" border="0" style="width:100%;">
        <tr>
          <td style="background-color:#9EE4FF;padding:15pt 18.75pt;color:#000;text-align:center;">
            <div style="line-height:1.38;margin:0 0 8pt;font-size:11pt;font-weight:bold;">From all of us at TIBOS 💛</div>
            <div style="line-height:1.38;font-size:11pt;">Wishing you and your family joy, prosperity and togetherness.</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr><td style="background-color:#E8EDF4;height:0.75pt;">&nbsp;</td></tr>
  <tr>
    <td style="background-color:#FAFBFD;padding:26.25pt;">
      <div style="line-height:1.38;margin:0 0 8pt;font-size:11pt;font-weight:bold;color:#000;">TIBOS Solutions &amp; Services Pvt. Ltd.</div>
      <div style="line-height:1.38;margin:0 0 8pt;font-size:11pt;">
        <span>🌐 </span><span style="color:#467886;"><a href="http://www.tibos.co.in" style="color:#467886;">www.tibos.co.in</a></span>
        <span>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;📧&nbsp;</span><span style="color:#467886;"><a href="mailto:secure@tibos.in" style="color:#467886;">secure@tibos.in</a></span>
        <span>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;📞&nbsp;+91 92821 09750</span>
      </div>
      <div style="line-height:1.38;font-size:11pt;color:#000;">Wishing our entire team a joyful and safe celebration.</div>
    </td>
  </tr>
</table>
""".strip()


def _get_recipients(wish: FestivalDB.FestivalWish, db: Session):
    audience = wish.audience or "employees"
    recipients = []
    if audience in ("employees", "both"):
        emp_rows = db.query(EmplyeeDB.Employee.name, EmplyeeDB.Employee.email).filter(
            EmplyeeDB.Employee.Status == "Active", EmplyeeDB.Employee.email.isnot(None)
        ).all()
        recipients += [(name or "Team Member", email) for name, email in emp_rows if email]
    if audience in ("customers", "both"):
        cust_rows = db.query(FestivalDB.WishContact.name, FestivalDB.WishContact.email).filter(
            FestivalDB.WishContact.enabled == True
        ).all()
        recipients += [(name or "Valued Customer", email) for name, email in cust_rows if email]
    return recipients


async def send_wish_email(wish: FestivalDB.FestivalWish, db: Session):
    recipients = _get_recipients(wish, db)
    if not recipients:
        return False, "No recipients found for this wish's audience"

    cfg = _load_sso_config()
    m = cfg.get("microsoft", {})
    if not m.get("enabled") or not m.get("client_id") or not m.get("client_secret"):
        return False, "Microsoft SSO is not configured (Admin > SSO Settings)"
    sender = (wish.from_email or "").strip() or os.getenv("GRAPH_SENDER_EMAIL")
    if not sender:
        return False, "No from-email set — set one on the wish, or set GRAPH_SENDER_EMAIL on the server"

    access_token, error = await _get_graph_token(m)
    if not access_token:
        return False, error or "Failed to authenticate with Microsoft Graph"

    cc_list = [c.strip() for c in (wish.cc_emails or "").split(",") if c.strip()]
    subject = f"🎉 {wish.name} Wishes from TIBOS"
    sent, failed = 0, 0
    async with httpx.AsyncClient() as client:
        for name, email in recipients:
            body_html = _build_wish_html(wish, _merge_message(wish.message, name))
            ok, err = await _send_single_email(client, access_token, sender, subject, body_html, email, cc_list)
            db.add(FestivalDB.WishSendLog(
                wish_id=wish.id,
                wish_name=wish.name,
                recipient_name=name,
                to_email=email,
                cc_emails=wish.cc_emails,
                from_email=sender,
                status="sent" if ok else "failed",
                error=None if ok else err,
            ))
            if ok:
                sent += 1
            else:
                failed += 1
        db.commit()

    if sent == 0:
        return False, f"All {failed} email(s) failed to send"
    return True, f"Sent to {sent} recipient(s)" + (f", {failed} failed" if failed else "")


@router.post("/send-now/{wish_id}")
async def send_now(wish_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    wish = db.query(FestivalDB.FestivalWish).filter(FestivalDB.FestivalWish.id == wish_id).first()
    if not wish:
        raise HTTPException(status_code=404, detail="Not found")
    ok, detail = await send_wish_email(wish, db)
    if not ok:
        raise HTTPException(status_code=502, detail=f"Email not sent: {detail}")
    wish.last_email_sent_year = date.today().year
    db.commit()
    return {"message": detail}


async def run_daily_festival_check():
    """Called once a day by the scheduler. Safe to run from multiple worker
    processes: the DB UPDATE only affects a row for the worker that gets
    there first, so the email only goes out once per festival per year."""
    today = date.today()
    db = SessionLocal()
    try:
        wishes = db.query(FestivalDB.FestivalWish).filter(FestivalDB.FestivalWish.enabled == True).all()
        for w in wishes:
            if not _is_today(w, today):
                continue
            claimed = db.query(FestivalDB.FestivalWish).filter(
                FestivalDB.FestivalWish.id == w.id,
                (FestivalDB.FestivalWish.last_email_sent_year.is_(None))
                | (FestivalDB.FestivalWish.last_email_sent_year != today.year),
            ).update({"last_email_sent_year": today.year}, synchronize_session=False)
            db.commit()
            if claimed:
                ok, detail = await send_wish_email(w, db)
                if not ok:
                    print(f"[festival] email for '{w.name}' not sent: {detail}")
    finally:
        db.close()


def seed_default_festivals():
    """Seeds a handful of fixed-date national holidays. Festivals that move
    every year (Diwali, Holi, Eid, Pongal, etc.) are intentionally left out —
    add them with the correct date for the year from Admin > Festival Wishes."""
    db = SessionLocal()
    try:
        if db.query(FestivalDB.FestivalWish).count() > 0:
            return
        defaults = [
            ("New Year", date(2026, 1, 1), "Wishing you a very Happy New Year! May this year bring success and happiness to you and your family."),
            ("Republic Day", date(2026, 1, 26), "Happy Republic Day! Celebrating the spirit of our nation together."),
            ("Independence Day", date(2026, 8, 15), "Happy Independence Day! Proud to celebrate this day with our team."),
            ("Gandhi Jayanti", date(2026, 10, 2), "Happy Gandhi Jayanti! Remembering the values of truth and non-violence."),
            ("Christmas", date(2026, 12, 25), "Merry Christmas! Wishing you and your family a joyful holiday season."),
        ]
        for name, d, msg in defaults:
            db.add(FestivalDB.FestivalWish(name=name, date=d, message=msg, recurs_yearly=True, enabled=True))
        db.commit()
    finally:
        db.close()
