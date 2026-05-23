
from datetime import datetime
from fastapi import APIRouter, HTTPException
from jose import jwt, JWTError
from datetime import  timedelta

from dotenv import load_dotenv
import os

load_dotenv()

ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 7
REFRESH_TOKEN_EXPIRE_DAYS = 30


# Create Access Token
def create_access_token(email: str):

    expire = datetime.utcnow() + timedelta(
        days=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": email,
        "exp": expire
    }

    access_token = jwt.encode(
        payload,
        ACCESS_SECRET_KEY,
        algorithm=ALGORITHM
    )

    return access_token


# Create Refresh Token
def create_refresh_token(email: str):

    expire = datetime.utcnow() + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": email,
        "exp": expire
    }

 
    refresh_token = jwt.encode(
        payload,
        REFRESH_SECRET_KEY,
        algorithm=ALGORITHM
    )

    return refresh_token


# Verify Token
def verify_token(token: str):

    try:

        payload = jwt.decode(
            token,
            ACCESS_SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload.get("sub")

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or Expired Token"
        )


# Verify Refresh Token
def verify_refresh_token(token: str):

    try:

        payload = jwt.decode(
            token,
            REFRESH_SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload.get("sub")

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or Expired Refresh Token"
        )


