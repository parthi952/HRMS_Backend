from pydantic import BaseModel
from typing import Optional


class DepartmentBase(BaseModel):
    Dep_name: str
    Dep_head: str
    Dep_icon: str
    bg_color: str
    icon_color: str


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentResponse(BaseModel):
    """Lenient about everything except the identifiers.

    These columns are nullable and rows created by the SSO sync carry only a
    name, so inheriting the strict create-schema meant one incomplete row
    failed validation and took the entire department list down with a 500.
    """
    Dep_id: str
    Dep_name: str
    Dep_head: Optional[str] = None
    Dep_icon: Optional[str] = None
    bg_color: Optional[str] = None
    icon_color: Optional[str] = None
    Total_employees: Optional[int] = 0

    class Config:
        from_attributes = True


class DepartmentEmployeeItem(BaseModel):
    """Same reasoning — an employee with no phone or designation recorded must
    not break the listing for their whole department."""
    Emp_id: str
    name: Optional[str] = None
    designation: Optional[str] = None
    emp_type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    Status: Optional[str] = None

    class Config:
        from_attributes = True