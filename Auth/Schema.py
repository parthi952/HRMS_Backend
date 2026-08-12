from typing import clear_overloads, List
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
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
    # Older clients submit `email`; some newer clients label the same value as
    # `username`. Accept both so a frontend/backend version mismatch cannot turn
    # a login attempt into a server error.
    email: Optional[str] = None
    username: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.username:
            raise ValueError("Email or username is required")
        if self.email:
            self.email = self.email.strip().lower()
        if self.username:
            self.username = self.username.strip()
        return self


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    role: str
    roles: Optional[List[str]] = None
    email: str
    emp_id: Optional[str] = None
    name: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: Optional[str] = None
    email: str
    role: str
    roles: Optional[List[str]] = None
    emp_id: Optional[str] = None
    name: Optional[str] = None
