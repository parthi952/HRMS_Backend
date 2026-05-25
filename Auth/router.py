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


