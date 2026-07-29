"""
SSO Router for HRMS — Google & Microsoft OAuth 2.0 Authorization Code Flow.
Config stored as JSON on disk, temporary codes in memory.
"""
import os
import json
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx

from database import get_db
from Auth.models import User
from Auth.Token import create_access_token, create_refresh_token
from Auth.router import get_current_user

router = APIRouter(prefix="/Auth/sso", tags=["SSO"])

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sso_config.json")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://hrm.tibostech.in")
API_URL = os.getenv("API_URL", "https://hrm-api.tibostech.in")

_sso_codes: dict = {}


def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {"google": {"enabled": False}, "microsoft": {"enabled": False}}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def _save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _cleanup_codes():
    now = time.time()
    expired = [k for k, v in _sso_codes.items() if v["expires"] < now]
    for k in expired:
        del _sso_codes[k]


@router.get("/config/public")
def sso_config_public():
    cfg = _load_config()
    return {
        "google": cfg.get("google", {}).get("enabled", False),
        "microsoft": cfg.get("microsoft", {}).get("enabled", False),
    }


@router.get("/config")
def sso_config_get(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    cfg = _load_config()
    return {
        "google": {
            "enabled": cfg.get("google", {}).get("enabled", False),
            "client_id": cfg.get("google", {}).get("client_id", ""),
            "client_secret": "",
            "client_secret_set": bool(cfg.get("google", {}).get("client_secret")),
        },
        "microsoft": {
            "enabled": cfg.get("microsoft", {}).get("enabled", False),
            "client_id": cfg.get("microsoft", {}).get("client_id", ""),
            "client_secret": "",
            "client_secret_set": bool(cfg.get("microsoft", {}).get("client_secret")),
            "tenant": cfg.get("microsoft", {}).get("tenant", "common"),
        },
        "redirect_uris": {
            "google": f"{API_URL}/Auth/sso/callback/google",
            "microsoft": f"{API_URL}/Auth/sso/callback/microsoft",
        },
    }


@router.post("/config")
def sso_config_save(data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    cfg = _load_config()
    for provider in ("google", "microsoft"):
        incoming = data.get(provider, {})
        if provider not in cfg:
            cfg[provider] = {}
        cfg[provider]["enabled"] = incoming.get("enabled", False)
        if incoming.get("client_id"):
            cfg[provider]["client_id"] = incoming["client_id"]
        if incoming.get("client_secret"):
            cfg[provider]["client_secret"] = incoming["client_secret"]
        if provider == "microsoft" and incoming.get("tenant"):
            cfg[provider]["tenant"] = incoming["tenant"]
    _save_config(cfg)
    return {"message": "SSO configuration saved"}


@router.get("/login/google")
def sso_login_google():
    cfg = _load_config()
    g = cfg.get("google", {})
    if not g.get("enabled"):
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=sso_disabled")
    state = secrets.token_urlsafe(32)
    _sso_codes[f"state:{state}"] = {"provider": "google", "expires": time.time() + 600}
    params = {
        "client_id": g["client_id"],
        "redirect_uri": f"{API_URL}/Auth/sso/callback/google",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/login/microsoft")
def sso_login_microsoft():
    cfg = _load_config()
    m = cfg.get("microsoft", {})
    if not m.get("enabled"):
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=sso_disabled")
    tenant = m.get("tenant", "common")
    state = secrets.token_urlsafe(32)
    _sso_codes[f"state:{state}"] = {"provider": "microsoft", "expires": time.time() + 600}
    params = {
        "client_id": m["client_id"],
        "redirect_uri": f"{API_URL}/Auth/sso/callback/microsoft",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback/google")
async def sso_callback_google(code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=token_exchange_failed")
    _cleanup_codes()
    state_data = _sso_codes.pop(f"state:{state}", None)
    if not state_data or state_data["provider"] != "google":
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=invalid_state")

    cfg = _load_config()
    g = cfg.get("google", {})
    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": g["client_id"],
                "client_secret": g["client_secret"],
                "redirect_uri": f"{API_URL}/Auth/sso/callback/google",
                "grant_type": "authorization_code",
            })
            tokens = token_resp.json()
            if "access_token" not in tokens:
                return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=token_exchange_failed")
            userinfo_resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo",
                                             headers={"Authorization": f"Bearer {tokens['access_token']}"})
            userinfo = userinfo_resp.json()
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=token_exchange_failed")

    email = userinfo.get("email", "").lower()
    if not email:
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=invalid_id_token")
    return _finish_sso(email)


@router.get("/callback/microsoft")
async def sso_callback_microsoft(code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=token_exchange_failed")
    _cleanup_codes()
    state_data = _sso_codes.pop(f"state:{state}", None)
    if not state_data or state_data["provider"] != "microsoft":
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=invalid_state")

    cfg = _load_config()
    m = cfg.get("microsoft", {})
    tenant = m.get("tenant", "common")
    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data={
                "code": code,
                "client_id": m["client_id"],
                "client_secret": m["client_secret"],
                "redirect_uri": f"{API_URL}/Auth/sso/callback/microsoft",
                "grant_type": "authorization_code",
                "scope": "openid email profile",
            })
            tokens = token_resp.json()
            if "access_token" not in tokens:
                return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=token_exchange_failed")
            userinfo_resp = await client.get("https://graph.microsoft.com/v1.0/me",
                                             headers={"Authorization": f"Bearer {tokens['access_token']}"})
            userinfo = userinfo_resp.json()
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=token_exchange_failed")

    email = (userinfo.get("mail") or userinfo.get("userPrincipalName") or "").lower()
    if not email:
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=invalid_id_token")
    return _finish_sso(email)


def _finish_sso(email: str):
    from database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return RedirectResponse(f"{FRONTEND_URL}/login?sso_error=user_not_provisioned")
        sso_code = secrets.token_urlsafe(48)
        _sso_codes[sso_code] = {"email": email, "expires": time.time() + 120}
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_code={sso_code}")
    finally:
        db.close()


@router.post("/exchange")
def sso_exchange(data: dict):
    _cleanup_codes()
    code = data.get("code", "")
    code_data = _sso_codes.pop(code, None)
    if not code_data or "email" not in code_data:
        raise HTTPException(status_code=400, detail="Invalid or expired SSO code")
    if code_data["expires"] < time.time():
        raise HTTPException(status_code=400, detail="SSO code expired")

    email = code_data["email"]
    from database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        access = create_access_token(user.email)
        refresh = create_refresh_token(user.email)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "user_name": user.employee.name if user.employee else email.split("@")[0],
            "user_email": user.email,
            "user_role": user.role,
            "emp_id": user.emp_id,
        }
    finally:
        db.close()
