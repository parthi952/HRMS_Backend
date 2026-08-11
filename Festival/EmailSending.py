import asyncio
import base64
import json
import mimetypes
import os
import re
import uuid
from email.mime.text import MIMEText

import httpx
from sqlalchemy.orm import Session

import module.FestivalDB as FestivalDB

import io
import urllib.parse
from bs4 import BeautifulSoup
from PIL import Image

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads"))


def _prepare_html_and_inline_images(html: str):
    """
    Parses HTML content for <img> tags using BeautifulSoup.
    Converts base64 data URIs, local upload URLs (/uploads/...), and remote image URLs
    into inline CID attachments.
    Returns (processed_html, inline_images_list)
    where inline_images_list contains dicts:
    [{'cid': 'img_xxx', 'bytes': b'...', 'content_type': 'image/png', 'name': 'image_xxx.png'}]
    """
    if not html or "<img" not in html.lower():
        return html, []

    inline_images = []
    soup = BeautifulSoup(html, "html.parser")
    img_tags = soup.find_all("img")

    for img in img_tags:
        src = img.get("src")
        if not src or src.lower().startswith("cid:"):
            continue

        img_bytes = None
        content_type = "image/png"
        filename = f"image_{len(inline_images) + 1}.png"

        # Case 1: Base64 data URI
        if src.lower().startswith("data:image/"):
            try:
                header, base64_str = src.split(",", 1)
                mime = header.split(";")[0].replace("data:", "").strip()
                if mime:
                    content_type = mime
                    ext = mimetypes.guess_extension(content_type) or ".png"
                    if ext == ".jpe":
                        ext = ".jpg"
                    filename = f"image_{len(inline_images) + 1}{ext}"
                clean_b64 = re.sub(r"\s+", "", base64_str)
                img_bytes = base64.b64decode(clean_b64)
            except Exception:
                img_bytes = None

        # Case 2: Local uploads folder (check multiple possible relative / server paths)
        if img_bytes is None and ("/uploads/" in src or "uploads/" in src):
            try:
                rel_part = src.split("/uploads/")[-1] if "/uploads/" in src else src.split("uploads/")[-1]
                rel_part = rel_part.split("?")[0]
                rel_part = urllib.parse.unquote(rel_part)

                candidate_paths = [
                    os.path.normpath(os.path.join(UPLOADS_DIR, rel_part.replace("/", os.sep))),
                    os.path.normpath(os.path.join(UPLOADS_DIR, "..", rel_part.replace("/", os.sep))),
                    os.path.normpath(os.path.join(os.getcwd(), "uploads", rel_part.replace("/", os.sep))),
                    os.path.normpath(os.path.join(os.getcwd(), rel_part.replace("/", os.sep))),
                ]

                for local_path in candidate_paths:
                    if os.path.exists(local_path) and os.path.isfile(local_path):
                        with open(local_path, "rb") as f:
                            img_bytes = f.read()
                        guessed_mime = mimetypes.guess_type(local_path)[0]
                        if guessed_mime:
                            content_type = guessed_mime
                        filename = os.path.basename(local_path)
                        break
            except Exception:
                img_bytes = None

        # Case 3: Remote HTTP/HTTPS URL
        if img_bytes is None and (src.lower().startswith("http://") or src.lower().startswith("https://")):
            parsed = urllib.parse.urlparse(src)
            is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0")
            if not is_localhost:
                try:
                    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                        resp = client.get(src)
                        if resp.status_code == 200:
                            img_bytes = resp.content
                            ct = resp.headers.get("Content-Type")
                            if ct:
                                content_type = ct.split(";")[0].strip()
                            ext = mimetypes.guess_extension(content_type) or ".png"
                            if ext == ".jpe":
                                ext = ".jpg"
                            filename = f"image_{len(inline_images) + 1}{ext}"
                except Exception:
                    img_bytes = None

        # Convert webp images to PNG (Outlook desktop/mobile cannot render webp)
        if img_bytes and (content_type == "image/webp" or filename.endswith(".webp")):
            try:
                im = Image.open(io.BytesIO(img_bytes))
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                content_type = "image/png"
                if filename.endswith(".webp"):
                    filename = filename[:-5] + ".png"
            except Exception:
                pass

        if img_bytes:
            cid = f"img_{uuid.uuid4().hex[:12]}"
            inline_images.append({
                "cid": cid,
                "bytes": img_bytes,
                "content_type": content_type,
                "name": filename
            })
            img["src"] = f"cid:{cid}"

    processed_html = str(soup)
    return processed_html, inline_images


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

    processed_html, inline_images = _prepare_html_and_inline_images(html)

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": processed_html},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": "true",
    }
    if cc_list:
        payload["message"]["ccRecipients"] = [{"emailAddress": {"address": c}} for c in cc_list]

    if inline_images:
        attachments = []
        for img in inline_images:
            attachments.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": img["name"],
                "contentType": img["content_type"],
                "contentBytes": base64.b64encode(img["bytes"]).decode("utf-8"),
                "contentId": img["cid"],
                "isInline": True,
            })
        payload["message"]["attachments"] = attachments

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    if resp.status_code == 202:
        return True, None

    err_text = resp.text
    try:
        err_json = resp.json()
        code = err_json.get("error", {}).get("code")
        msg = err_json.get("error", {}).get("message")
        if code == "ErrorAccessDenied" or resp.status_code in (401, 403):
            err_text = f"Microsoft Graph Access Denied ({code}): {msg}. Please check: 1) Grant Admin Consent for 'Mail.Send' in Azure AD App Registrations. 2) Ensure Sender Email '{sender}' is a valid M365 mailbox. 3) Use your M365 Tenant ID instead of 'common'."
    except Exception:
        pass

    return False, err_text


def _send_via_google_sync(cfg, subject, html, to_email, cc_list, sender_override=None):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from email.mime.multipart import MIMEMultipart
    from email.mime.image import MIMEImage

    sender = (sender_override or cfg.google_sender_email or "").strip()
    if not cfg.google_service_account_json or not sender:
        return False, "Google email sending is not fully configured (Celebrations > Email Settings)"
    try:
        sa_info = json.loads(cfg.google_service_account_json)
        creds = service_account.Credentials.from_service_account_info(
            sa_info, scopes=["https://www.googleapis.com/auth/gmail.send"], subject=sender
        )
        service = build("gmail", "v1", credentials=creds)

        processed_html, inline_images = _prepare_html_and_inline_images(html)

        if inline_images:
            message = MIMEMultipart("related")
            message["to"] = to_email
            message["from"] = sender
            message["subject"] = subject
            if cc_list:
                message["cc"] = ", ".join(cc_list)

            msg_alt = MIMEMultipart("alternative")
            message.attach(msg_alt)

            html_part = MIMEText(processed_html, "html", "utf-8")
            msg_alt.attach(html_part)

            for img in inline_images:
                subtype = img["content_type"].split("/")[-1] if "/" in img["content_type"] else "png"
                if subtype == "jpeg":
                    subtype = "jpg"
                img_part = MIMEImage(img["bytes"], _subtype=subtype)
                img_part.add_header("Content-ID", f"<{img['cid']}>")
                img_part.add_header("Content-Disposition", "inline", filename=img["name"])
                message.attach(img_part)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        else:
            message = MIMEText(processed_html, "html", "utf-8")
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

