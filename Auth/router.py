from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db

# Absolute imports starting from root package
from Auth.models import User
from Auth.Schema import UserCreate, UserLogin, Token, TokenRefreshRequest, UserResponse
from Auth.Token import create_access_token, create_refresh_token, verify_token, verify_refresh_token
from Auth.Encrypt import hash_password, verify_password

# Router
router = APIRouter(
    prefix="/Auth",
    tags=["Authentication"]
)

# Security scheme for Bearer token
security = HTTPBearer()

# Dependency to get current user based on verified token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    email = verify_token(token)  # Decodes with ACCESS_SECRET_KEY. Raises 401 if invalid.
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


# ✅ REGISTER ENDPOINT
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_pwd = hash_password(user_data.password)
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password=hashed_pwd,
        role=user_data.role,
        emp_id=user_data.emp_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ✅ LOGIN ENDPOINT (POST)
@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create tokens
    access = create_access_token(user.email)
    refresh = create_refresh_token(user.email)
    
    return Token(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        role=user.role,
        email=user.email,
        emp_id=user.emp_id
    )


# ✅ LOGIN ENDPOINT (GET) for backward compatibility
@router.get("/Login")
def Login():
    return {"message": "Employee API is active"}


# ✅ REFRESH ENDPOINT
@router.post("/refresh", response_model=Token)
def refresh(refresh_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    # Verify the refresh token. Raises 401 if invalid.
    email = verify_refresh_token(refresh_data.refresh_token)
    
    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    # Generate new tokens
    access = create_access_token(user.email)
    refresh = create_refresh_token(user.email)
    
    return Token(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        role=user.role,
        email=user.email,
        emp_id=user.emp_id
    )


# ✅ ME ENDPOINT (Profile)
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ✅ GET ALL EMPLOYEES PORTAL STATUS
@router.get("/employee-portal-status")
def get_employee_portal_status(db: Session = Depends(get_db)):
    from module.EmplyeeDB import Employee
    employees = db.query(Employee).all()
    users = db.query(User).all()
    
    # Map emp_id to User record
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
            "has_portal_access": has_access,
            "portal_email": user_map[emp.Emp_id].email if has_access else None,
            "portal_role": user_map[emp.Emp_id].role if has_access else None
        })
    return result


# ✅ REVOKE USER PORTAL ACCESS
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

