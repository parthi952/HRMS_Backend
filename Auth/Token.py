import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import HTTPException
from jose import jwt, JWTError

load_dotenv()

ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY") or "hrms-access-secret-key-apex-365-token"
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY") or "hrms-refresh-secret-key-apex-365-token"

ALGORITHM = "HS256"

# Expiration periods (defaults aligned with frontend session lifetime)
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_DAYS  # Backward compatibility alias
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def create_access_token(email: str):
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": email,
        "exp": expire
    }
    return jwt.encode(payload, ACCESS_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(email: str):
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": email,
        "exp": expire
    }
    return jwt.encode(payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, ACCESS_SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid or Expired Token")
        return sub
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or Expired Token")


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid or Expired Refresh Token")
        return sub
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or Expired Refresh Token")
