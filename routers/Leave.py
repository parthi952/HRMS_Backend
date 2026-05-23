from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import module.EmplyeeDB as EmplyeeDB, Schemas.employeeSceema as employeeSceema
from database import get_db

router = APIRouter(
    prefix="/leave",
    tags=["Leave Management"]
)

# ==============================
# ✅ HELPER: EXTRACT DATES & COUNT DAYS
# ==============================
def get_leave_details(duration_str: str):
    try:
        # Split "2026-04-06 to 2026-04-08"
        start_str, end_str = duration_str.split(" to ")
        start_clean = start_str.strip()
        end_clean = end_str.strip()

        start_date = datetime.strptime(start_clean, "%Y-%m-%d")
        end_date = datetime.strptime(end_clean, "%Y-%m-%d")

        if end_date < start_date:
            raise HTTPException(status_code=400, detail="End date cannot be before start date")

        days = (end_date - start_date).days + 1 
        return days, start_clean, end_clean
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Use format: YYYY-MM-DD to YYYY-MM-DD")

# ==============================
# ✅ GET ALL BALANCES
# ==============================
@router.get("/all-balances")
def get_all_leave_balances(db: Session = Depends(get_db)):
    results = db.query(
        EmplyeeDB.Employee.Emp_id,
        EmplyeeDB.Employee.name,
        EmplyeeDB.LeaveDB.Total_Leave,
        EmplyeeDB.LeaveDB.Used,
        EmplyeeDB.LeaveDB.Available
    ).outerjoin(EmplyeeDB.LeaveDB, EmplyeeDB.Employee.Emp_id == EmplyeeDB.LeaveDB.Emp_id).all()

    return [
        {
            "Emp_id": r.Emp_id,
            "employee_name": r.name,
            "Total_Leave": r.Total_Leave if r.Total_Leave is not None else 36,
            "Used": r.Used if r.Used is not None else 0,
            "Available": r.Available if r.Available is not None else 36
        } for r in results
    ]

# ==============================
# ✅ APPLY LEAVE (With Date Logic)
# ==============================
@router.post("/apply")
def apply_leave(leave_his: employeeSceema.LeaveHistory, db: Session = Depends(get_db)):
    # 1. Generate dates from duration
    days_count, f_date, t_date = get_leave_details(leave_his.Duration)
    
    # 2. Generate current application date
    today_date = datetime.now().strftime("%Y-%m-%d")

    # 3. Check 12-day limit per type
    used_for_type = db.query(func.sum(EmplyeeDB.LeaveHistoryDB.Days))\
        .filter(EmplyeeDB.LeaveHistoryDB.Emp_id == leave_his.Emp_id)\
        .filter(EmplyeeDB.LeaveHistoryDB.leave_type == leave_his.leave_type)\
        .filter(EmplyeeDB.LeaveHistoryDB.status == "Approved")\
        .scalar() or 0

    if (used_for_type + days_count) > 12:
        raise HTTPException(status_code=400, detail=f"Insufficient {leave_his.leave_type} balance.")

    # 4. Save to Database
    new_entry = EmplyeeDB.LeaveHistoryDB(
        Emp_id=leave_his.Emp_id,
        employee_name=leave_his.employee_name,
        Duration=leave_his.Duration,
        from_date=f_date,        # Saved separately
        to_date=t_date,          # Saved separately
        applayDate=today_date,   # Auto-generated
        Reason=leave_his.Reason,
        Days=days_count,
        leave_type=leave_his.leave_type,
        status="Pending"
    )

    db.add(new_entry)
    db.commit()
    return {"message": "Leave applied", "applayDate": today_date, "days": days_count}


# UPDATE STATUS (Approval Logic with Role Hierarchy)

from Auth.router import get_current_user
from Auth.models import User

@router.put("/update-status/{leave_id}")
def update_status(
    leave_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    leave = db.query(EmplyeeDB.LeaveHistoryDB).filter(EmplyeeDB.LeaveHistoryDB.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if leave.status == "Approved":
        raise HTTPException(status_code=400, detail="Leave already approved and closed")

    role = (current_user.role or "employee").lower()

    if role in ["manager", "tl", "team_lead", "teamlead", "lead"]:
        # Managers and TLs can recommend or reject, but not approve
        if status not in ["Recommended", "Rejected"]:
            raise HTTPException(
                status_code=403,
                detail="Managers and Team Leads can only recommend or reject leaves. Final approval is restricted to HR."
            )
    elif role in ["hr", "admin"]:
        # HR/Admin can approve or reject
        if status not in ["Approved", "Rejected"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status selection for HR."
            )
    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permissions to modify leave status."
        )

    # Master balances are only updated on final HR approval
    if status == "Approved" and role in ["hr", "admin"]:
        master = db.query(EmplyeeDB.LeaveDB).filter(EmplyeeDB.LeaveDB.Emp_id == leave.Emp_id).first()
        if not master:
            master = EmplyeeDB.LeaveDB(Emp_id=leave.Emp_id, employee_name=leave.employee_name, Total_Leave=36, Used=0, Available=36)
            db.add(master)
        
        master.Used += leave.Days
        master.Available -= leave.Days

    leave.status = status
    db.commit()
    return {"message": f"Leave status updated to {status}"}



#  GET INDIVIDUAL HISTORY & BALANCE

@router.get("/history/{emp_id}")
def get_employee_leave_details(emp_id: str, db: Session = Depends(get_db)):
    
    # 1. Fetch Master Balance
    balance = db.query(EmplyeeDB.LeaveDB).filter(EmplyeeDB.LeaveDB.Emp_id == emp_id).first()
    
    # 2. Fetch Detailed History List
    history = db.query(EmplyeeDB.LeaveHistoryDB).filter(EmplyeeDB.LeaveHistoryDB.Emp_id == emp_id).all()

    # 3. Handle case where employee has no leave records yet
    if not balance:
        # Return default values if no balance record exists
        total, used, available = 36, 0, 36
    else:
        total, used, available = balance.Total_Leave, balance.Used, balance.Available

    # 4. Format to match your Frontend 'Empleaves' type
    return {
        "empid": emp_id,
        "name": balance.employee_name if balance else "Employee",
        "total_leave": total,
        "Used": used,
        "available_leaves": available,
        "leave_history": [
            {
                "id": h.id,
                "applayDate": h.applayDate,
                "from_date": h.from_date,
                "to_date": h.to_date,
                "Days": h.Days,
                "status": h.status,
                "Reason": h.Reason,
                "leave_type": h.leave_type
            } for h in history
        ]
    }


# ==============================
# ✅ ADMIN: GET ALL LEAVE REQUESTS
# ==============================
@router.get("/all-requests")
def get_all_leave_requests(db: Session = Depends(get_db)):
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


# ==============================
# ✅ ADMIN: UPDATE STATUS DIRECTLY (Admin Port)
# ==============================
@router.put("/update-status-admin/{leave_id}")
def update_status_admin(
    leave_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    leave = db.query(EmplyeeDB.LeaveHistoryDB).filter(EmplyeeDB.LeaveHistoryDB.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if leave.status == "Approved":
        raise HTTPException(status_code=400, detail="Leave already approved and closed")

    if status not in ["Approved", "Rejected", "Recommended", "Pending"]:
        raise HTTPException(status_code=400, detail="Invalid status value")

    # If approved, update the master balance
    if status == "Approved":
        master = db.query(EmplyeeDB.LeaveDB).filter(EmplyeeDB.LeaveDB.Emp_id == leave.Emp_id).first()
        if not master:
            master = EmplyeeDB.LeaveDB(Emp_id=leave.Emp_id, employee_name=leave.employee_name, Total_Leave=36, Used=0, Available=36)
            db.add(master)
        
        master.Used += leave.Days
        master.Available -= leave.Days

    leave.status = status
    db.commit()
    return {"message": f"Leave status updated to {status}"}

