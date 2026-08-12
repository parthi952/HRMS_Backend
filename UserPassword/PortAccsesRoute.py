from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db

from Auth.models import User
from Auth.Schema import UserCreate, UserResponse
from Auth.Encrypt import hash_password

from UserPassword.genarateAuto import generate_password
from UserPassword.Template import mailTemplate

from Email.SendMail import send_email

from pydantic import BaseModel

router = APIRouter(tags=["PortAccses"])


class GrantAccessRequest(BaseModel):
    emp_id: str
    email: str
    role: str = "employee"


# -------------------------------------------------------
# Register User
# -------------------------------------------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    raw_password = user_data.password

    if raw_password.lower() == "generate":
        from module.EmplyeeDB import Employee

        emp = db.query(Employee).filter(
            Employee.Emp_id == user_data.emp_id
        ).first()

        emp_name = emp.name if emp else "User"
        emp_dob = emp.dob if emp else None

        raw_password = generate_password(
            name=emp_name,
            dob=emp_dob
        )

    hashed_password = hash_password(raw_password)

    new_user = User(
        email=user_data.email,
        password=hashed_password,
        role=user_data.role,
        emp_id=user_data.emp_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    email_body = mailTemplate(
        user_data.email,
        raw_password,
        user_data.role,
        user_data.emp_id,
    )

    try:

        send_email(
            receiver_emails=[user_data.email],
            subject="🔐 Your HRMS Portal Access Credentials",
            body=email_body,
            is_html=True,
        )

    except Exception as e:

        db.delete(new_user)
        db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Email failed : {str(e)}"
        )

    return new_user


# -------------------------------------------------------
# Grant Portal Access
# -------------------------------------------------------
@router.post("/grant-access", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def grant_portal_access(
    req: GrantAccessRequest,
    db: Session = Depends(get_db)
):

    existing = db.query(User).filter(
        (User.email == req.email) |
        (User.emp_id == req.emp_id)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Portal access already granted."
        )

    from module.EmplyeeDB import Employee

    emp = db.query(Employee).filter(
        Employee.Emp_id == req.emp_id
    ).first()

    emp_name = emp.name if emp else "User"
    emp_dob = emp.dob if emp else None

    raw_password = generate_password(
        name=emp_name,
        dob=emp_dob
    )

    hashed_password = hash_password(raw_password)

    new_user = User(
        email=req.email,
        password=hashed_password,
        role=req.role,
        emp_id=req.emp_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    email_body = mailTemplate(
        req.email,
        raw_password,
        req.role,
        req.emp_id,
    )

    try:

        send_email(
            receiver_emails=[req.email],
            subject="🔐 Your HRMS Portal Access Credentials",
            body=email_body,
            is_html=True,
        )

    except Exception as e:

        db.delete(new_user)
        db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Email failed : {str(e)}"
        )

    return new_user


# -------------------------------------------------------
# Employee Portal Status
# -------------------------------------------------------
@router.get("/employee-portal-status")
def get_employee_portal_status(db: Session = Depends(get_db)):

    from module.EmplyeeDB import Employee

    employees = db.query(Employee).all()
    users = db.query(User).all()

    user_map = {u.emp_id: u for u in users if u.emp_id}

    result = []

    for emp in employees:

        has_access = emp.Emp_id in user_map

        result.append({
            "Emp_id": emp.Emp_id,
            "name": emp.name,
            "email": emp.email,
            "Department": emp.Department,
            "designation": emp.designation,
            "dob": emp.dob.isoformat() if emp.dob else None,
            "has_portal_access": has_access,
            "portal_email": user_map[emp.Emp_id].email if has_access else None,
            "portal_role": user_map[emp.Emp_id].role if has_access else None,
        })

    return result


# -------------------------------------------------------
# Revoke Portal Access
# -------------------------------------------------------
@router.delete("/revoke/{emp_id}")
def revoke_portal_access(emp_id: str, db: Session = Depends(get_db)):

    user = db.query(User).filter(
        User.emp_id == emp_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Portal access not found."
        )

    db.delete(user)
    db.commit()

    return {
        "message": "Portal access revoked successfully."
    }