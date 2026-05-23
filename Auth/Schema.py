from typing import clear_overloads
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional

class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: str
    password: str
    role: Optional[str] = "employee"  # admin, hr, manager, employee
    emp_id: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    role: str
    email: str
    emp_id: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str
    emp_id: Optional[str] = None
