from pydantic import BaseModel, field_validator, model_validator
from datetime import date
from typing import List, Optional, Any


class EducationCreate(BaseModel):
    degree: str = ""
    institution: str = ""
    graduationYear: Optional[date] = None 

    @field_validator("graduationYear", mode="before")
    @classmethod
    def parse_graduation_year(cls, v: Any) -> Optional[date]:
        """Accept '', None, 'YYYY', or 'YYYY-MM-DD'."""
        if not v or v == "":
            return None
        if isinstance(v, date):
            return v
        s = str(v).strip()

        if len(s) == 4 and s.isdigit():
            return date(int(s), 1, 1)
        # Full ISO date
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None

    class Config:
        from_attributes = True


class DependentCreate(BaseModel):
    person_name: str = ""
    relationship_type: str = ""
    contact: str = ""
    person_dob: Optional[date] = None  

    @field_validator("person_dob", mode="before")
    @classmethod
    def parse_dob(cls, v: Any) -> Optional[date]:
        if not v or v == "":
            return None
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v).strip())
        except ValueError:
            return None

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    # Personal
    Emp_id: str
    f_name: str
    l_name: str
    name: str
    gender: str = ""
    dob: Optional[date] = None
    phone: str = ""
    email: str = ""
    Status: str = "Active"

    # Job
    Department: str = ""
    designation: str = ""
    emp_type: str = ""
    DateOfJoining: Optional[date] = None

    # Previous company — kept as plain strings (no date validation needed)
    company_name: str = ""
    position: str = ""
    FromDate: str = ""
    ToDate: str = ""

    # Current address
    Street: str = ""
    City: str = ""
    State: str = ""
    Pin_Code: int = 0

    # Permanent address
    p_Street: str = ""
    p_City: str = ""
    p_State: str = ""
    p_Pin_Code: int = 0

    # Nested lists
    education: List[EducationCreate] = []
    dependents: List[DependentCreate] = []

    # Salary
    provider: str = ""
    payType: str = ""
    currency: str = ""
    payFrequency: str = ""
    annualSalary: float = 0.0
    bonus_Type: str = ""
    bonus_CalculationMode: str = "percentage"
    bonus_Value: float = 0.0

    # Bank
    bankName: str = ""
    accountNumber: str = ""
    ifscCode: str = ""
    panNumber: str = ""


 

    # --- Coerce empty strings / None → sensible defaults ---

    @field_validator("dob", "DateOfJoining", mode="before")
    @classmethod
    def parse_top_level_dates(cls, v: Any) -> Optional[date]:
        if not v or v == "":
            return None
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v).strip())
        except ValueError:
            return None

    @field_validator("annualSalary", "bonus_Value", mode="before")
    @classmethod
    def coerce_floats(cls, v: Any) -> float:
        if v is None or v == "":
            return 0.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    @field_validator("Pin_Code", "p_Pin_Code", mode="before")
    @classmethod
    def coerce_ints(cls, v: Any) -> int:
        if v is None or v == "":
            return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    class Config:
        from_attributes = True


# attendance schema

class AttendanceCreate(BaseModel):
    Emp_id: str
    employee_name: Optional[str] = None # <--- ADD THIS
    date: date
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class Leave(BaseModel):

    Emp_id: str
    status : str
    employee_name : str
    Total_Leave : int
    Available : int
    Used : int
    