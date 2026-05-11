from pydantic import BaseModel, field_validator, ConfigDict
from datetime import date
from typing import List, Optional, Any


def parse_date_flexible(v: Any) -> Optional[date]:
    if not v or v == "":
        return None
    if isinstance(v, date):
        return v
    s = str(v).strip()
    if len(s) == 4 and s.isdigit():
        return date(int(s), 1, 1)
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


# ─── Nominee ─────────────────────────────────────────────────────────────────

class NomineeCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nominee_name: str = ""
    nominee_aadhar: str = ""


# ─── Education ────────────────────────────────────────────────────────────────

class EducationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    degree: str = ""
    institution: str = ""
    graduationYear: Optional[date] = None

    @field_validator("graduationYear", mode="before")
    @classmethod
    def validate_date(cls, v):
        return parse_date_flexible(v)


# ─── Work Experience ──────────────────────────────────────────────────────────

class WorkExpCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    company_name: str = ""
    position: str = ""
    FromDate: Optional[date] = None
    ToDate: Optional[date] = None

    @field_validator("FromDate", "ToDate", mode="before")
    @classmethod
    def validate_date(cls, v):
        return parse_date_flexible(v)


# ─── Family ───────────────────────────────────────────────────────────────────


class FamilyCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person_name: str = ""
    relationship_type: str = ""
    contact: str = ""
    person_dob: Optional[date] = None
    nominees: List[NomineeCreate] = []   

    @field_validator("person_dob", mode="before")
    @classmethod
    def validate_date(cls, v):
        return parse_date_flexible(v)


class FamilyResponse(FamilyCreate):
    id: int
    nominees: List[NomineeCreate] = []


# ─── Employee ─────────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    f_name: str
    l_name: str
    gender: str = ""
    dob: Optional[date] = None
    phone: str = ""
    email: str = ""
    Status: str = "Active"

    apply_esi: Optional[str] = ""
    uan_number: str = ""
    pf_id: str = ""
    insurance_no: str = ""
    aadhar_no: str = ""
    esi_no: str = ""
    esi_name: str = ""
    insurance_provider: str = ""

    Department: str = ""
    designation: str = ""
    emp_type: str = ""
    DateOfJoining: Optional[date] = None

    Street: str = ""
    City: str = ""
    State: str = ""
    Pin_Code: int = 0
    p_Street: str = ""
    p_City: str = ""
    p_State: str = ""
    p_Pin_Code: int = 0

    WorkExp: List[WorkExpCreate] = []
    education: List[EducationCreate] = []


    Familys: List[FamilyCreate] = []    

    provider: str = ""
    payType: str = ""
    currency: str = ""
    payFrequency: str = ""
    annualSalary: float = 0.0
    bonus_Type: str = ""
    bonus_CalculationMode: str = "percentage"
    bonus_Value: float = 0.0
    bankName: str = ""
    accountNumber: str = ""
    ifscCode: str = ""
    panNumber: str = ""

    @field_validator("dob", "DateOfJoining", mode="before")
    @classmethod
    def validate_dates(cls, v):
        return parse_date_flexible(v)

    @field_validator("annualSalary", "bonus_Value", mode="before")
    @classmethod
    def coerce_floats(cls, v: Any) -> float:
        try:
            return float(v) if v not in (None, "") else 0.0
        except Exception:
            return 0.0

    @field_validator("Pin_Code", "p_Pin_Code", mode="before")
    @classmethod
    def coerce_ints(cls, v: Any) -> int:
        try:
            return int(v) if v not in (None, "") else 0
        except Exception:
            return 0


# ─── Response models ──────────────────────────────────────────────────────────

class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Emp_id: str
    f_name: Optional[str] = ""
    l_name: Optional[str] = ""
    name: Optional[str] = ""
    gender: Optional[str] = ""
    dob: Optional[date] = None
    phone: Optional[str] = ""
    email: Optional[str] = ""
    Department: Optional[str] = ""
    designation: Optional[str] = ""
    emp_type: Optional[str] = ""
    DateOfJoining: Optional[date] = None
    Status: Optional[str] = "Active"

    apply_esi: Optional[str] = ""
    uan_number: Optional[str] = ""
    pf_id: Optional[str] = ""
    insurance_no: Optional[str] = ""
    aadhar_no: Optional[str] = ""
    esi_no: Optional[str] = ""
    esi_name: Optional[str] = ""
    insurance_provider: Optional[str] = ""

    Street: Optional[str] = ""
    City: Optional[str] = ""
    State: Optional[str] = ""
    Pin_Code: Optional[int] = 0
    p_Street: Optional[str] = ""
    p_City: Optional[str] = ""
    p_State: Optional[str] = ""
    p_Pin_Code: Optional[int] = 0

    provider: Optional[str] = ""
    payType: Optional[str] = ""
    currency: Optional[str] = ""
    payFrequency: Optional[str] = ""
    annualSalary: Optional[float] = 0.0
    bonus_Type: Optional[str] = ""
    bonus_CalculationMode: Optional[str] = "percentage"
    bonus_Value: Optional[float] = 0.0
    bankName: Optional[str] = ""
    accountNumber: Optional[str] = ""
    ifscCode: Optional[str] = ""
    panNumber: Optional[str] = ""

    education: List[EducationCreate] = []
    Familys: List[FamilyResponse] = []
    Work: List[WorkExpCreate] = []


class ComponentBreakdown(BaseModel):
    name: str
    type: Optional[str] = None
    value: float
    amount: float

class EmployeeDetailResponse(BaseModel):
    Employee: EmployeeResponse
    base_salary: float
    gross_salary: float
    total_earnings: float
    total_deductions: float
    net_salary: float
    earnings_breakdown: List[ComponentBreakdown] = []
    deductions_breakdown: List[ComponentBreakdown] = []


# ─── Attendance / Leave ───────────────────────────────────────────────────────

class AttendanceCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Emp_id: str
    employee_name: Optional[str] = None
    date: date
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    status: str


class Leave(BaseModel):
    Emp_id: str
    status: str
    employee_name: str
    Total_Leave: int
    Available: int
    Used: int


class LeaveHistory(BaseModel):
    Emp_id: str
    employee_name: str
    Duration: str
    Reason: str
    Days: int
    applayDate: str
    from_date: str
    to_date: str
    status: str
    leave_type: str