from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db

# Auth imports
from Auth.models import User
from Auth.Schema import UserCreate, UserResponse
from Auth.Encrypt import hash_password

# Password generator
from UserPassword.genarateAuto import generate_password

# Email sender
from Email.SendMail import send_email

from UserPassword.Template import mailTemplate

import os
from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel

router = APIRouter(
    tags=["PortAccses"]
)

class GrantAccessRequest(BaseModel):
    emp_id: str
    email: str
    role: str = "employee"


# ─────────────────────────────────────────────
# ✅ MANUAL REGISTER ENDPOINT (custom password or generated)
# ─────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a user with a manually provided or generated password and email it."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # If password is 'generate', auto-generate it using employee Name and DOB
    raw_password = user_data.password
    if raw_password.lower() == "generate":
        from module.EmplyeeDB import Employee
        emp_record = db.query(Employee).filter(Employee.Emp_id == user_data.emp_id).first()
        emp_name = emp_record.name if emp_record else "User"
        emp_dob = emp_record.dob if emp_record else None
        raw_password = generate_password(name=emp_name, dob=emp_dob)

    hashed_pwd = hash_password(raw_password)

    new_user = User(
        email=user_data.email,
        password=hashed_pwd,
        role=user_data.role,
        emp_id=user_data.emp_id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Build email body using the template
    email_body = f"""{mailTemplate(user_data.email , raw_password , user_data.role , user_data.emp_id)}"""

    # Send credentials via email
    try:
        await send_email(
            client_ip="server",
            receiver_emails=[user_data.email],
            subject="🔐 Your HRMS Portal Access Credentials",
            body=email_body,
            is_html=True,
            tenant_id=os.getenv("tenant_id"),
            client_id=os.getenv("client_id"),
            client_secret=os.getenv("client_secret"),
            sender_email=os.getenv("sender_email"),
        )
    except Exception as e:
        # Rollback user creation if email fails
        db.delete(new_user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User created but email failed to send: {str(e)}"
        )

    return new_user


# ─────────────────────────────────────────────
# ✅ GRANT ACCESS — Auto-generate password & email it
# ─────────────────────────────────────────────
@router.post("/grant-access", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def grant_portal_access(
    req: GrantAccessRequest,
    db: Session = Depends(get_db)
):
    """
    Grant portal access to an employee:
    1. Auto-generates a strong password using Name and DOB
    2. Creates a User record in the database
    3. Emails the credentials to the employee
    """
    # Check if portal access already exists
    existing = db.query(User).filter(
        (User.email == req.email) | (User.emp_id == req.emp_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portal access already granted for this employee or email"
        )

    # Get employee details for password generation
    from module.EmplyeeDB import Employee
    emp_record = db.query(Employee).filter(Employee.Emp_id == req.emp_id).first()
    emp_name = emp_record.name if emp_record else "User"
    emp_dob = emp_record.dob if emp_record else None

    # Auto-generate password based on Name and DOB
    raw_password = generate_password(name=emp_name, dob=emp_dob)
    hashed_pwd   = hash_password(raw_password)

    # Create user record
    new_user = User(
        email=req.email,
        password=hashed_pwd,
        role=req.role,
        emp_id=req.emp_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Build email body
    email_body = mailTemplate(req.email , raw_password , req.role , req.emp_id)

    # Send credentials via email
    try:
        await send_email(
            client_ip="server",
            receiver_emails=[req.email],
            subject="🔐 Your HRMS Portal Access Credentials",
            body=email_body,
            is_html=True,
            tenant_id=os.getenv("tenant_id"),
            client_id=os.getenv("client_id"),
            client_secret=os.getenv("client_secret"),
            sender_email=os.getenv("sender_email"),
        )
    except Exception as e:
        # Rollback user creation if email fails
        db.delete(new_user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User created but email failed to send: {str(e)}"
        )

    return new_user


# ─────────────────────────────────────────────
# ✅ GET ALL EMPLOYEES PORTAL STATUS
# ─────────────────────────────────────────────
@router.get("/employee-portal-status")
def get_employee_portal_status(db: Session = Depends(get_db)):
    from module.EmplyeeDB import Employee
    employees = db.query(Employee).all()
    users     = db.query(User).all()

    user_map = {u.emp_id: u for u in users if u.emp_id}

    result = []
    for emp in employees:
        has_access = emp.Emp_id in user_map
        result.append({
            "Emp_id":             emp.Emp_id,
            "name":               emp.name,
            "email":              emp.email,
            "Department":         emp.Department,
            "designation":        emp.designation,
            "dob":                emp.dob.isoformat() if emp.dob else None,
            "has_portal_access":  has_access,
            "portal_email":       user_map[emp.Emp_id].email if has_access else None,
            "portal_role":        user_map[emp.Emp_id].role  if has_access else None,
        })
    return result


# ─────────────────────────────────────────────
# ✅ REVOKE USER PORTAL ACCESS
# ─────────────────────────────────────────────
@router.delete("/revoke/{emp_id}")
def revoke_portal_access(emp_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.emp_id == emp_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal access not found for this employee"
        )
    db.delete(user)
    db.commit()
    return {"message": "Successfully revoked portal access"}
