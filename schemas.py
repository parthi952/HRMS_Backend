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

class NomineeCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nominee_name: str = ""
    nominee_aadhar: str = ""

class EducationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    degree: str = ""
    institution: str = ""
    graduationYear: Optional[date] = None 

    @field_validator("graduationYear", mode="before")
    @classmethod
    def validate_date(cls, v): return parse_date_flexible(v)

class WorkExpCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    company_name: str = ""
    position: str = ""
    FromDate: Optional[date] = None   
    ToDate: Optional[date] = None

    @field_validator("FromDate", "ToDate", mode="before")
    @classmethod
    def validate_date(cls, v): return parse_date_flexible(v)

class FamilyCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person_name: str = ""
    relationship_type: str = ""
    contact: str = ""
    person_dob: Optional[date] = None  

    @field_validator("person_dob", mode="before")
    @classmethod
    def validate_date(cls, v): return parse_date_flexible(v)

class EmployeeCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Emp_id: str
    f_name: str
    l_name: str
    gender: str = ""
    dob: Optional[date] = None
    phone: str = ""
    email: str = ""
    Status: str = "Active"

    apply_esi: str = ""
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

    Street: str = ""; City: str = ""; State: str = ""; Pin_Code: int = 0
    p_Street: str = ""; p_City: str = ""; p_State: str = ""; p_Pin_Code: int = 0

    WorkExp: List[WorkExpCreate] = []
    education: List[EducationCreate] = []
    Familys: List[FamilyCreate] = []
    nominee: List[NomineeCreate] = []

    provider: str = ""; payType: str = ""; currency: str = ""; payFrequency: str = ""
    annualSalary: float = 0.0
    bonus_Type: str = ""; bonus_CalculationMode: str = "percentage"; bonus_Value: float = 0.0
    bankName: str = ""; accountNumber: str = ""; ifscCode: str = ""; panNumber: str = ""

    @field_validator("dob", "DateOfJoining", mode="before")
    @classmethod
    def validate_dates(cls, v): return parse_date_flexible(v)

    @field_validator("annualSalary", "bonus_Value", mode="before")
    @classmethod
    def coerce_floats(cls, v: Any) -> float:
        try: return float(v) if v not in (None, "") else 0.0
        except: return 0.0

    @field_validator("Pin_Code", "p_Pin_Code", mode="before")
    @classmethod
    def coerce_ints(cls, v: Any) -> int:
        try: return int(v) if v not in (None, "") else 0
        except: return 0

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