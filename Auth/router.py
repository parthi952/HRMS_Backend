from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db, engine
import json

# Absolute imports starting from root package
from Auth.models import User
from Auth.Schema import UserCreate, UserLogin, Token, TokenRefreshRequest, UserResponse, UserPermissionUpdate
from Auth.Token import create_access_token, create_refresh_token, verify_token, verify_refresh_token
from Auth.Encrypt import hash_password, verify_password
from Auth import roles as roles_util

# create_all never alters an existing table, so new columns need adding by hand.
try:
    from sqlalchemy import text as _sa_text
    with engine.connect() as _conn:
        try:
            _conn.execute(_sa_text("ALTER TABLE users ADD COLUMN roles VARCHAR;"))
            _conn.commit()
        except Exception:
            _conn.rollback()
        try:
            _conn.execute(_sa_text("ALTER TABLE users ADD COLUMN can_view_salary BOOLEAN DEFAULT 0;"))
            _conn.commit()
        except Exception:
            _conn.rollback()
        try:
            _conn.execute(_sa_text("ALTER TABLE users ADD COLUMN allowed_modules VARCHAR;"))
            _conn.commit()
        except Exception:
            _conn.rollback()
        try:
            # Backfill roles from role if roles is null
            _conn.execute(_sa_text("UPDATE users SET roles = role WHERE roles IS NULL AND role IS NOT NULL;"))
            _conn.commit()
        except Exception:
            _conn.rollback()
except Exception:
    pass

# Router
router = APIRouter(
    prefix="/Auth",
    tags=["Authentication"]
)

# Security scheme for Bearer token
security = HTTPBearer()

def link_employee_profile(user: User, db: Session):
    """Attach the login to its employee record when it isn't linked yet."""
    if user.emp_id or not user.email:
        return user
    try:
        import module.EmplyeeDB as EmplyeeDB
        from sqlalchemy import func
        emp = db.query(EmplyeeDB.Employee).filter(
            func.lower(EmplyeeDB.Employee.email) == user.email.strip().lower()
        ).first()
        if emp:
            user.emp_id = emp.Emp_id
            db.commit()
            db.refresh(user)
    except Exception:
        db.rollback()
    return user


def ensure_default_users(db: Session):
    """
    Ensure default Admin & HR accounts exist in the backend database.
    """
    try:
        from sqlalchemy import func
        admin_user = db.query(User).filter(
            (func.lower(User.email) == "admin@hrms.com") | (func.lower(User.username) == "admin")
        ).first()
        if not admin_user:
            admin_user = User(
                email="admin@hrms.com",
                username="admin",
                password=hash_password("password123"),
                role="admin",
                can_view_salary=True,
                emp_id=None
            )
            roles_util.set_roles(admin_user, ["admin"])
            db.add(admin_user)
        else:
            if not admin_user.username:
                admin_user.username = "admin"
            roles_util.set_roles(admin_user, ["admin"])
            admin_user.can_view_salary = True

        hr_user = db.query(User).filter(
            (func.lower(User.email) == "hr@hrms.com") | (func.lower(User.username) == "hr")
        ).first()
        if not hr_user:
            hr_user = User(
                email="hr@hrms.com",
                username="hr",
                password=hash_password("password123"),
                role="hr",
                can_view_salary=True,
                emp_id=None
            )
            roles_util.set_roles(hr_user, ["hr"])
            db.add(hr_user)
        else:
            if not hr_user.username:
                hr_user.username = "hr"
            if hr_user.can_view_salary is None:
                hr_user.can_view_salary = True

        db.commit()
    except Exception as e:
        db.rollback()
        print("Default users seed notice:", e)


# Dependency to get current user based on verified token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    ensure_default_users(db)
    token = credentials.credentials
    email = verify_token(token)  # Decodes with ACCESS_SECRET_KEY. Raises 401 if invalid.
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not roles_util.has_role(current_user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required."
        )
    return current_user


# 🔑 LOGIN ENDPOINT (POST)
@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    ensure_default_users(db)

    # Get identifier from username or email field
    raw_id = (login_data.username or login_data.email or "").strip().lower()
    if not raw_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is required"
        )

    # Search user by username OR email (case-insensitive)
    from sqlalchemy import func
    user = db.query(User).filter(
        (func.lower(User.email) == raw_id) | (func.lower(User.username) == raw_id)
    ).first()

    # Fallback: if identifier has no @, try matching local part of email
    if not user and "@" not in raw_id:
        user = db.query(User).filter(
            func.lower(User.email).like(f"{raw_id}@%")
        ).first()

    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create tokens
    access = create_access_token(user.email)
    refresh = create_refresh_token(user.email)

    link_employee_profile(user, db)

    # Resolve real name from linked employee profile
    emp_name = None
    if user.employee:
        emp_name = user.employee.name
    if not emp_name:
        emp_name = user.username or user.email.split("@")[0]

    return Token(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        role=user.role,
        roles=roles_util.get_roles(user),
        can_view_salary=roles_util.can_view_salary(user),
        allowed_modules=roles_util.get_allowed_modules(user),
        email=user.email,
        emp_id=user.emp_id,
        name=emp_name
    )


# 🔑 LOGIN ENDPOINT (GET) for backward compatibility
@router.get("/Login")
def Login():
    return {"message": "Employee API is active"}


# 🔑 REFRESH ENDPOINT
@router.post("/refresh", response_model=Token)
def refresh(refresh_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    ensure_default_users(db)
    email = verify_refresh_token(refresh_data.refresh_token)
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    access = create_access_token(user.email)
    refresh_tok = create_refresh_token(user.email)

    link_employee_profile(user, db)

    emp_name = None
    if user.employee:
        emp_name = user.employee.name
    if not emp_name:
        emp_name = user.username or user.email.split("@")[0]

    return Token(
        access_token=access,
        refresh_token=refresh_tok,
        token_type="bearer",
        role=user.role,
        roles=roles_util.get_roles(user),
        can_view_salary=roles_util.can_view_salary(user),
        allowed_modules=roles_util.get_allowed_modules(user),
        email=user.email,
        emp_id=user.emp_id,
        name=emp_name
    )


# 🔑 ME ENDPOINT (Profile)
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    link_employee_profile(current_user, db)

    emp_name = None
    if current_user.employee:
        emp_name = current_user.employee.name
    if not emp_name:
        emp_name = current_user.username or current_user.email.split("@")[0]

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        roles=roles_util.get_roles(current_user),
        can_view_salary=roles_util.can_view_salary(current_user),
        allowed_modules=roles_util.get_allowed_modules(current_user),
        emp_id=current_user.emp_id,
        name=emp_name
    )


# 🛡️ ADMIN: Get All Users and Permissions
@router.get("/users/permissions")
def list_user_permissions(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    result = []
    for u in users:
        emp_name = u.employee.name if u.employee else (u.username or u.email.split("@")[0])
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "roles": roles_util.get_roles(u),
            "can_view_salary": roles_util.can_view_salary(u),
            "allowed_modules": roles_util.get_allowed_modules(u),
            "emp_id": u.emp_id,
            "name": emp_name
        })
    return result


# 🛡️ ADMIN: Update Specific User Permissions & Roles
@router.put("/users/{user_id}/permissions")
def update_user_permissions(
    user_id: int,
    payload: UserPermissionUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.roles is not None:
        roles_util.set_roles(user, payload.roles)
    elif payload.role is not None:
        roles_util.set_roles(user, [payload.role])

    if payload.can_view_salary is not None:
        user.can_view_salary = payload.can_view_salary

    if payload.allowed_modules is not None:
        if isinstance(payload.allowed_modules, list):
            user.allowed_modules = json.dumps(payload.allowed_modules)
        else:
            user.allowed_modules = str(payload.allowed_modules)

    try:
        db.commit()
        db.refresh(user)
        return {
            "message": f"Permissions updated successfully for user {user.email}",
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "roles": roles_util.get_roles(user),
                "can_view_salary": roles_util.can_view_salary(user),
                "allowed_modules": roles_util.get_allowed_modules(user),
                "emp_id": user.emp_id
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
