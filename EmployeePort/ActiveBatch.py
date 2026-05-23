from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import get_db
from Auth.router import get_current_user
from Auth.models import User

router = APIRouter(prefix="/employee-session", tags=["Employee Sessions"])

# In-memory dictionary to track real-time active sessions
# Key: employee ID (str), Value: last active timestamp (datetime)
ACTIVE_SESSIONS = {}

@router.post("/heartbeat")
def heartbeat(
    current_user: User = Depends(get_current_user)
):
    if not current_user.emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to any Employee profile"
        )
    
    # Update or add the employee's session to the memory map
    ACTIVE_SESSIONS[current_user.emp_id] = datetime.now()
    
    return {
        "status": "active",
        "emp_id": current_user.emp_id,
        "last_active": ACTIVE_SESSIONS[current_user.emp_id].isoformat()
    }


@router.get("/active-list")
def get_active_list():
    cutoff_time = datetime.now() - timedelta(seconds=45)
    active_emp_ids = [
        emp_id for emp_id, last_active in ACTIVE_SESSIONS.items()
        if last_active > cutoff_time
    ]
    return {
        "active_employees": active_emp_ids
    }


@router.get("/status/{emp_id}")
def get_session_status(
    emp_id: str
):
    last_active = ACTIVE_SESSIONS.get(emp_id)
    if not last_active:
        return {
            "emp_id": emp_id,
            "is_online": False,
            "status": "offline"
        }
        
    # Consider the employee online if we received a heartbeat in the last 45 seconds
    cutoff_time = datetime.now() - timedelta(seconds=45)
    is_online = last_active > cutoff_time
    
    return {
        "emp_id": emp_id,
        "is_online": is_online,
        "status": "online" if is_online else "offline",
        "last_active": last_active.isoformat()
    }


@router.get("/my-status")
def get_my_session_status(
    current_user: User = Depends(get_current_user)
):
    if not current_user.emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to any Employee profile"
        )
        
    return get_session_status(current_user.emp_id)
