from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import module.EmplyeeDB as EmplyeeDB
from Auth.router import get_current_user
from Auth.models import User

router = APIRouter(
    tags=["ManagerPort_Leave"],
    prefix="/manager/leave"
)

@router.get("/employee-leaves")
def get_employee_leaves(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    role = (current_user.role or "employee").lower()
    if role not in ["manager", "tl", "tlm", "team_lead", "teamlead", "lead", "hr", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to view employee leaves")
    
    # Fetch all leave requests
    requests = db.query(EmplyeeDB.LeaveHistoryDB).order_by(EmplyeeDB.LeaveHistoryDB.id.desc()).all()
    
    return [
        {
            "id": r.id,
            "Emp_id": r.Emp_id,
            "employee_name": r.employee_name,
            "Duration": r.Duration,
            "Reason": r.Reason,
            "from_date": r.from_date,
            "to_date": r.to_date,
            "Days": r.Days,
            "applayDate": r.applayDate,
            "leave_type": r.leave_type,
            "status": r.status
        } for r in requests
    ]
