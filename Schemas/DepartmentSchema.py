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


class DepartmentResponse(DepartmentBase):
    Dep_id: str
    Total_employees: Optional[int] = 0

    class Config:
        from_attributes = True


class DepartmentEmployeeItem(BaseModel):
    Emp_id: str
    name: str
    designation: str
    emp_type: str
    email: str
    phone: str
    Status: str

    class Config:
        from_attributes = True