"""
SSO Router for HRMS — Google & Microsoft OAuth 2.0 Authorization Code Flow.
Config stored as JSON on disk, temporary codes in a shared file store.
"""
import os
import json
import secrets
import time
import fcntl
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
CODES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sso_codes.json")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://hrm.tibostech.in")
API_URL = os.getenv("API_URL", "https://hrm-api.tibostech.in")


def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {"google": {"enabled": False}, "microsoft": {"enabled": False}}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def _save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _with_codes_lock(mutate_fn):
    # Gunicorn runs multiple worker processes; an in-memory dict would not be
    # shared between them, so SSO state/codes are persisted to a locked file
    # that every worker reads and writes.
    if not os.path.exists(CODES_PATH):
        open(CODES_PATH, "a").close()
    with open(CODES_PATH, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            content = f.read().strip()
            codes = json.loads(content) if content else {}
            result = mutate_fn(codes)
            f.seek(0)
            f.truncate()
            json.dump(codes, f)
            return result
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _set_code(key: str, value: dict):
    def mutate(codes):
        codes[key] = value
    _with_codes_lock(mutate)


def _pop_code(key: str):
    def mutate(codes):
        return codes.pop(key, None)
    return _with_codes_lock(mutate)


def _cleanup_codes():
    def mutate(codes):
        now = time.time()
        for k in [k for k, v in codes.items() if v["expires"] < now]:
            del codes[k]
    _with_codes_lock(mutate)


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
    _set_code(f"state:{state}", {"provider": "google", "expires": time.time() + 600})
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
    _set_code(f"state:{state}", {"provider": "microsoft", "expires": time.time() + 600})
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
    state_data = _pop_code(f"state:{state}")
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
    state_data = _pop_code(f"state:{state}")
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
        _set_code(sso_code, {"email": email, "expires": time.time() + 120})
        return RedirectResponse(f"{FRONTEND_URL}/login?sso_code={sso_code}")
    finally:
        db.close()


# Mailboxes a tenant carries that are not people — rooms, shared boxes,
# automation accounts. Matched against the local part of the address.
_NON_HUMAN_HINTS = (
    "noreply", "no-reply", "donotreply", "do-not-reply", "postmaster", "mailer-daemon",
    "admin@", "administrator", "helpdesk", "support@", "info@", "sales@", "contact@",
    "billing@", "accounts@", "careers@", "hr@", "service", "svc-", "svc_", "sync",
    "test@", "demo@", "backup", "room", "meeting", "conference", "equipment",
    "discoverysearchmailbox", "healthmailbox", "systemmailbox", "spam", "abuse@",
)


def _directory_skip_reason(u: dict, email: str) -> str | None:
    """Decide whether a directory entry represents a real employee.

    A tenant is full of guests, shared mailboxes, room resources and service
    accounts. Provisioning all of them fills the employee directory with rows
    nobody wants, so filter them out and report why.
    """
    if not email or "@" not in email:
        return "no email address"
    if (u.get("userType") or "Member").strip().lower() == "guest":
        return "guest account"
    if "#ext#" in (u.get("userPrincipalName") or "").lower():
        return "external/guest account"
    if not (u.get("mail") or "").strip():
        return "no mailbox (mail attribute empty)"
    # Rooms, shared mailboxes and service accounts carry no user licence
    if "assignedLicenses" in u and not (u.get("assignedLicenses") or []):
        return "no assigned licence (shared mailbox / room / service account)"
    local = email.split("@")[0].lower()
    for hint in _NON_HUMAN_HINTS:
        needle = hint.rstrip("@")
        if needle and (local == needle or needle in local):
            return f"looks like a non-person mailbox ({needle})"
    return None


def _clean_display_name(display_name, given, surname, email) -> str:
    """Pick the best available human name.

    Directory display names are sometimes blank or carry the address itself, so
    fall back to given+surname and finally to the local part of the email —
    never leave the record showing a raw address.
    """
    name = (display_name or "").strip()
    if name and "@" not in name:
        return name
    built = " ".join(p for p in [(given or "").strip(), (surname or "").strip()] if p).strip()
    if built:
        return built
    if name:
        name = name.split("@")[0]
    local = (name or (email or "").split("@")[0] or "User").replace(".", " ").replace("_", " ").replace("-", " ")
    return " ".join(w.capitalize() for w in local.split() if w) or "User"


def _as_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _ensure_department(db: Session, name: str):
    """Employees.Department is a FK onto departments.Dep_name, so a directory
    department has to exist as a row before it can be assigned. Returns the
    stored name (matched case-insensitively) or None."""
    name = (name or "").strip()
    if not name:
        return None
    import module.DepartmentDB as DepartmentDB
    from sqlalchemy import func as sa_func
    dep = db.query(DepartmentDB.Department).filter(
        sa_func.lower(DepartmentDB.Department.Dep_name) == name.lower()
    ).first()
    if dep:
        return dep.Dep_name
    from Caluclation.IdCustom import generate_next_dep_id
    dep = DepartmentDB.Department(Dep_id=generate_next_dep_id(db), Dep_name=name)
    db.add(dep)
    db.flush()
    return dep.Dep_name


def _upsert_employee_from_directory(db: Session, user: User, attrs: dict):
    """Copy directory attributes onto the person's employee profile.

    Existing values entered by HR always win — only blank fields are filled —
    so running the sync repeatedly never overwrites curated data.
    Returns "created", "updated" or "unchanged".
    """
    import module.EmplyeeDB as EmplyeeDB
    from sqlalchemy import func as sa_func

    email = (user.email or "").strip()
    if not email:
        return "unchanged"

    emp = db.query(EmplyeeDB.Employee).filter(
        sa_func.lower(EmplyeeDB.Employee.email) == email.lower()
    ).first()

    department = _ensure_department(db, attrs.get("department"))
    outcome = "unchanged"

    if not emp:
        from Caluclation.IdCustom import generate_next_empid
        emp = EmplyeeDB.Employee(
            Emp_id=generate_next_empid(db),
            email=email,
            name=attrs.get("name") or email.split("@")[0],
            f_name=attrs.get("first_name"),
            l_name=attrs.get("last_name"),
            phone=attrs.get("phone"),
            designation=attrs.get("job_title"),
            Department=department,
            Status="Active" if attrs.get("active", True) else "Inactive",
            Street=attrs.get("street"),
            City=attrs.get("city"),
            State=attrs.get("state"),
            Pin_Code=_as_int(attrs.get("postal_code")),
        )
        db.add(emp)
        db.flush()
        outcome = "created"
    else:
        # The display name is the directory's to own — earlier syncs left
        # placeholders built from the email local part, and those must heal.
        directory_name = (attrs.get("name") or "").strip()
        current_name = (emp.name or "").strip()
        if directory_name and directory_name != current_name and (
            not current_name or "@" in current_name or current_name.lower() == email.split("@")[0].lower()
        ):
            emp.name = directory_name
            outcome = "updated"

        fillable = {
            "name": attrs.get("name"),
            "f_name": attrs.get("first_name"),
            "l_name": attrs.get("last_name"),
            "phone": attrs.get("phone"),
            "designation": attrs.get("job_title"),
            "Department": department,
            "Street": attrs.get("street"),
            "City": attrs.get("city"),
            "State": attrs.get("state"),
        }
        for field, value in fillable.items():
            if value and not (getattr(emp, field, None) or "").strip():
                setattr(emp, field, value)
                outcome = "updated"
        if emp.Pin_Code is None and _as_int(attrs.get("postal_code")) is not None:
            emp.Pin_Code = _as_int(attrs.get("postal_code"))
            outcome = "updated"

    # Link the login so "My Profile" resolves without waiting for the next sign-in
    if not user.emp_id:
        user.emp_id = emp.Emp_id
        if outcome == "unchanged":
            outcome = "updated"

    return outcome


@router.post("/sync")
async def sso_sync_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    cfg = _load_config()
    synced = []
    skipped = []
    errors = []

    if cfg.get("microsoft", {}).get("enabled"):
        m = cfg["microsoft"]
        tenant = m.get("tenant", "common")
        try:
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
                    errors.append({"provider": "microsoft", "error": tokens.get("error_description", "Failed to get app token. Ensure 'User.Read.All' application permission is granted.")})
                else:
                    url = (
                        "https://graph.microsoft.com/v1.0/users"
                        "?$select=id,displayName,givenName,surname,mail,userPrincipalName,jobTitle,"
                        "department,mobilePhone,businessPhones,officeLocation,city,state,"
                        "streetAddress,postalCode,accountEnabled,userType,assignedLicenses&$top=999"
                    )
                    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
                    # Graph pages at 999 — follow @odata.nextLink or a big tenant
                    # silently loses everyone past the first page.
                    while url:
                        users_resp = await client.get(url, headers=headers)
                        if users_resp.status_code == 403:
                            errors.append({"provider": "microsoft", "error": "Microsoft Graph denied listing users. Add the 'User.Read.All' APPLICATION permission to the Azure app registration and grant admin consent."})
                            break
                        users_data = users_resp.json()
                        for u in users_data.get("value", []):
                            email = (u.get("mail") or u.get("userPrincipalName") or "").lower().strip()
                            reason = _directory_skip_reason(u, email)
                            if reason:
                                skipped.append({"email": email or "(no email)", "name": u.get("displayName") or "", "provider": "microsoft", "reason": reason})
                                continue
                            business_phones = u.get("businessPhones") or []
                            display_name = _clean_display_name(u.get("displayName"), u.get("givenName"), u.get("surname"), email)
                            attrs = {
                                "name": display_name,
                                "first_name": u.get("givenName"),
                                "last_name": u.get("surname"),
                                "job_title": u.get("jobTitle"),
                                "department": u.get("department"),
                                "phone": u.get("mobilePhone") or (business_phones[0] if business_phones else None),
                                "street": u.get("streetAddress") or u.get("officeLocation"),
                                "city": u.get("city"),
                                "state": u.get("state"),
                                "postal_code": u.get("postalCode"),
                                "active": u.get("accountEnabled", True),
                            }
                            existing = db.query(User).filter(User.email == email).first()
                            if not existing:
                                from Auth.Encrypt import hash_password
                                existing = User(
                                    email=email,
                                    password=hash_password(secrets.token_urlsafe(16)),
                                    role="employee",
                                )
                                db.add(existing)
                                db.flush()
                                status_label = "created"
                            else:
                                status_label = "exists"
                            profile = _upsert_employee_from_directory(db, existing, attrs)
                            synced.append({
                                "email": email,
                                "name": display_name,
                                "provider": "microsoft",
                                "status": status_label,
                                "profile": profile,
                            })
                        db.commit()
                        url = users_data.get("@odata.nextLink")
        except Exception as e:
            errors.append({"provider": "microsoft", "error": str(e)})

    if cfg.get("google", {}).get("enabled"):
        g = cfg["google"]
        try:
            async with httpx.AsyncClient() as client:
                token_resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": g["client_id"],
                        "client_secret": g["client_secret"],
                        "grant_type": "client_credentials",
                        "scope": "https://www.googleapis.com/auth/admin.directory.user.readonly",
                    },
                )
                tokens = token_resp.json()
                if "access_token" not in tokens:
                    errors.append({"provider": "google", "error": "Google Directory API requires Workspace Admin SDK with domain-wide delegation. Use Microsoft SSO sync or add users manually."})
                else:
                    domain = g.get("domain", "")
                    users_resp = await client.get(
                        f"https://admin.googleapis.com/admin/directory/v1/users?domain={domain}&maxResults=500",
                        headers={"Authorization": f"Bearer {tokens['access_token']}"},
                    )
                    users_data = users_resp.json()
                    for u in users_data.get("users", []):
                        email = u.get("primaryEmail", "").lower().strip()
                        # Google exposes mailbox kind differently — reuse the same
                        # rules by presenting the entry in Graph's shape.
                        reason = _directory_skip_reason(
                            {"userType": "Guest" if u.get("isGuest") else "Member",
                             "userPrincipalName": email, "mail": email},
                            email,
                        )
                        if reason:
                            skipped.append({"email": email or "(no email)", "name": (u.get("name") or {}).get("fullName", ""), "provider": "google", "reason": reason})
                            continue
                        name_obj = u.get("name") or {}
                        orgs = u.get("organizations") or []
                        org = orgs[0] if orgs else {}
                        phones = u.get("phones") or []
                        addresses = u.get("addresses") or []
                        addr = addresses[0] if addresses else {}
                        display_name = _clean_display_name(
                            name_obj.get("fullName"), name_obj.get("givenName"), name_obj.get("familyName"), email
                        )
                        attrs = {
                            "name": display_name,
                            "first_name": name_obj.get("givenName"),
                            "last_name": name_obj.get("familyName"),
                            "job_title": org.get("title"),
                            "department": org.get("department"),
                            "phone": phones[0].get("value") if phones else None,
                            "street": addr.get("streetAddress"),
                            "city": addr.get("locality"),
                            "state": addr.get("region"),
                            "postal_code": addr.get("postalCode"),
                            "active": not u.get("suspended", False),
                        }
                        existing = db.query(User).filter(User.email == email).first()
                        if not existing:
                            from Auth.Encrypt import hash_password
                            existing = User(
                                email=email,
                                password=hash_password(secrets.token_urlsafe(16)),
                                role="employee",
                            )
                            db.add(existing)
                            db.flush()
                            status_label = "created"
                        else:
                            status_label = "exists"
                        profile = _upsert_employee_from_directory(db, existing, attrs)
                        synced.append({
                            "email": email,
                            "name": display_name,
                            "provider": "google",
                            "status": status_label,
                            "profile": profile,
                        })
        except Exception as e:
            errors.append({"provider": "google", "error": str(e)})

    db.commit()
    created_count = len([s for s in synced if s["status"] == "created"])
    existing_count = len([s for s in synced if s["status"] == "exists"])
    profiles_created = len([s for s in synced if s.get("profile") == "created"])
    profiles_updated = len([s for s in synced if s.get("profile") == "updated"])
    return {
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
        "created": created_count,
        "existing": existing_count,
        "skipped_count": len(skipped),
        "profiles_created": profiles_created,
        "profiles_updated": profiles_updated,
    }


@router.get("/users")
def sso_list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "emp_id": u.emp_id,
            "name": u.employee.name if u.employee else u.email.split("@")[0],
        }
        for u in users
    ]


@router.put("/users/{user_id}/role")
def sso_update_role(user_id: int, data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_role = data.get("role", "employee")
    if new_role not in ("admin", "hr", "manager", "employee"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = new_role
    db.commit()
    return {"message": f"Role updated to {new_role}"}


@router.post("/exchange")
def sso_exchange(data: dict):
    _cleanup_codes()
    code = data.get("code", "")
    code_data = _pop_code(code)
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
        from Auth.router import link_employee_profile
        link_employee_profile(user, db)
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
