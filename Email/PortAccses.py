from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db



router = APIRouter(
    prefix="/email",
    tags=["EmailSend"]
)

@router.get("/EMAILGet")
def Login():
    return {"Email.send"}



