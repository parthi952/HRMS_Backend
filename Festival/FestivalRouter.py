import os
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx

from database import get_db, SessionLocal
from Auth.models import User
from Auth.router import get_current_user
from Auth.sso_router import _load_config as _load_sso_config
import module.FestivalDB as FestivalDB
import module.EmplyeeDB as EmplyeeDB

router = APIRouter(prefix="/festivals", tags=["Festival Wishes"])


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
    }


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
    wish = FestivalDB.FestivalWish(
        name=data.get("name", "").strip() or "Festival",
        date=wish_date,
        message=data.get("message", "").strip() or "Wishing you a happy celebration!",
        recurs_yearly=bool(data.get("recurs_yearly", True)),
        enabled=bool(data.get("enabled", True)),
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


async def _send_graph_email(subject: str, body_html: str, bcc_recipients: list):
    cfg = _load_sso_config()
    m = cfg.get("microsoft", {})
    if not m.get("enabled") or not m.get("client_id") or not m.get("client_secret"):
        return False, "Microsoft SSO is not configured (Admin > SSO Settings)"
    sender = os.getenv("GRAPH_SENDER_EMAIL")
    if not sender:
        return False, "GRAPH_SENDER_EMAIL environment variable is not set"
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
        if "access_token" not in tokens:
            return False, tokens.get("error_description", "Failed to authenticate with Microsoft Graph")

        message = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": sender}}],
                "bccRecipients": [{"emailAddress": {"address": r}} for r in bcc_recipients],
            },
            "saveToSentItems": "true",
        }
        resp = await client.post(
            f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=message,
        )
        return resp.status_code == 202, (resp.text if resp.status_code != 202 else "sent")


def _build_wish_html(wish: FestivalDB.FestivalWish) -> str:
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
      <div style="line-height:1.38;margin:0 0 8pt;font-size:11pt;color:#000;">{wish.message}</div>
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


async def send_wish_email(wish: FestivalDB.FestivalWish, db: Session):
    recipients = [
        e for (e,) in db.query(EmplyeeDB.Employee.email)
        .filter(EmplyeeDB.Employee.Status == "Active", EmplyeeDB.Employee.email.isnot(None))
        .all()
        if e
    ]
    if not recipients:
        return False, "No active employee emails found"
    body_html = _build_wish_html(wish)
    return await _send_graph_email(f"🎉 {wish.name} Wishes from TIBOS", body_html, recipients)


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
    return {"message": "Wish email sent"}


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
