from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime

import module.EmplyeeDB as EmplyeeDB
from database import get_db
from Auth.router import get_current_user
from Auth.models import User

router = APIRouter(prefix="/employee-attendance", tags=["Employee Attendance"])

@router.get("/status")
def get_today_attendance_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to any Employee profile"
        )
    
    # Check if Employee exists
    employee = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == current_user.emp_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    # Get today's attendance record
    today = date.today()
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == current_user.emp_id,
        EmplyeeDB.Attendance.date == today
    ).first()
    
    if not record:
        # Create a default pending record if it doesn't exist yet for today
        record = EmplyeeDB.Attendance(
            Emp_id=employee.Emp_id,
            employee_name=employee.name,
            date=today,
            status="Pending",
            check_in=None,
            check_out=None
        )
        db.add(record)
        try:
            db.commit()
            db.refresh(record)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

    return {
        "emp_id": record.Emp_id,
        "employee_name": record.employee_name,
        "date": record.date.isoformat(),
        "check_in": record.check_in,
        "check_out": record.check_out,
        "status": record.status,
        "clocked_in": record.check_in is not None and record.check_out is None
    }


@router.post("/check-in")
def check_in(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to any Employee profile"
        )
        
    employee = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == current_user.emp_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
        
    today = date.today()
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == current_user.emp_id,
        EmplyeeDB.Attendance.date == today
    ).first()
    
    if not record:
        record = EmplyeeDB.Attendance(
            Emp_id=employee.Emp_id,
            employee_name=employee.name,
            date=today,
            status="Pending",
            check_in=None,
            check_out=None
        )
        db.add(record)
    
    if record.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked in for today"
        )
        
    # Get current local time in "HH:MM AM/PM" format
    current_time_str = datetime.now().strftime("%I:%M %p")
    record.check_in = current_time_str
    record.status = "Present"
    
    try:
        db.commit()
        db.refresh(record)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
        
    return {
        "message": "Successfully checked in",
        "check_in": record.check_in,
        "status": record.status
    }


@router.post("/check-out")
def check_out(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to any Employee profile"
        )
        
    today = date.today()
    record = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.Emp_id == current_user.emp_id,
        EmplyeeDB.Attendance.date == today
    ).first()
    
    if not record or not record.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must check in before checking out"
        )
        
    if record.check_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked out for today"
        )
        
    current_time_str = datetime.now().strftime("%I:%M %p")
    record.check_out = current_time_str
    
    try:
        db.commit()
        db.refresh(record)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
        
    return {
        "message": "Successfully checked out",
        "check_out": record.check_out,
        "status": record.status
    }
