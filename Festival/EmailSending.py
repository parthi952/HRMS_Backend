"""Provider-agnostic email sending, configured from Celebrations > Email
Settings instead of server env vars / SSH. Supports Microsoft 365 (Graph
API, client-credentials app) and Google Workspace (Gmail API via a
service account with domain-wide delegation)."""
import asyncio
import base64
import json
from email.mime.text import MIMEText

import httpx
from sqlalchemy.orm import Session

import module.FestivalDB as FestivalDB


def get_or_create_config(db: Session) -> FestivalDB.EmailProviderConfig:
    cfg = db.query(FestivalDB.EmailProviderConfig).filter(FestivalDB.EmailProviderConfig.id == 1).first()
    if not cfg:
        cfg = FestivalDB.EmailProviderConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


async def _get_ms_token(cfg: FestivalDB.EmailProviderConfig):
    tenant = cfg.ms_tenant or "common"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": cfg.ms_client_id,
                "client_secret": cfg.ms_client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
        )
        tokens = resp.json()
        return tokens.get("access_token"), tokens.get("error_description")


async def _send_via_microsoft(cfg, subject, html, to_email, cc_list, sender_override=None):
    sender = (sender_override or cfg.ms_sender_email or "").strip()
    if not cfg.ms_client_id or not cfg.ms_client_secret or not sender:
        return False, "Microsoft 365 email sending is not fully configured (Celebrations > Email Settings)"
    token, err = await _get_ms_token(cfg)
    if not token:
        return False, err or "Failed to authenticate with Microsoft Graph"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": "true",
    }
    if cc_list:
        payload["message"]["ccRecipients"] = [{"emailAddress": {"address": c}} for c in cc_list]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    return resp.status_code == 202, (None if resp.status_code == 202 else resp.text)


def _send_via_google_sync(cfg, subject, html, to_email, cc_list, sender_override=None):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sender = (sender_override or cfg.google_sender_email or "").strip()
    if not cfg.google_service_account_json or not sender:
        return False, "Google email sending is not fully configured (Celebrations > Email Settings)"
    try:
        sa_info = json.loads(cfg.google_service_account_json)
        creds = service_account.Credentials.from_service_account_info(
            sa_info, scopes=["https://www.googleapis.com/auth/gmail.send"], subject=sender
        )
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(html, "html")
        message["to"] = to_email
        message["from"] = sender
        message["subject"] = subject
        if cc_list:
            message["cc"] = ", ".join(cc_list)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True, None
    except Exception as e:
        return False, str(e)


async def send_email(db: Session, subject: str, html: str, to_email: str, cc_list=None, sender_override=None):
    cfg = get_or_create_config(db)
    if cfg.provider == "microsoft":
        return await _send_via_microsoft(cfg, subject, html, to_email, cc_list, sender_override)
    if cfg.provider == "google":
        return await asyncio.to_thread(_send_via_google_sync, cfg, subject, html, to_email, cc_list, sender_override)
    return False, "No email provider configured — set one up in Celebrations > Email Settings"
