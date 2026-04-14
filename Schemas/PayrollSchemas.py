from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from enum import Enum



class ComponentType(str, Enum):
    fixed = "fixed"
    percentage = "percentage"




class PayrollComponentBase(BaseModel):
    """Shared base for earnings and deductions to avoid duplication."""
    name: str
    type: Optional[ComponentType] = None
    value: float = Field(ge=0, description="Value must be zero or positive")


# --- Earning Schemas ---

class EarningBase(PayrollComponentBase):
    pass


class EarningOut(EarningBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- Deduction Schemas ---

class DeductionBase(PayrollComponentBase):
    pass


class DeductionOut(DeductionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- PayRoll Provider Schemas ---

class PayRollProviderCreate(BaseModel):
    providername: str = Field(min_length=1, description="Provider name cannot be empty")
    description: Optional[str] = None
    earnings: List[EarningBase] = []
    deductions: List[DeductionBase] = []


class PayRollProviderOut(BaseModel):
    provider_id: str
    providername: str
    description: Optional[str]
    earnings: List[EarningOut]
    deductions: List[DeductionOut]
    model_config = ConfigDict(from_attributes=True)


# --- Payroll Record Schemas ---

class PayrollCreate(BaseModel):
    payroll_id: int
    provider_id: str
    emp_id: str
    annual_salary: float = Field(gt=0, description="Annual salary must be positive")
    monthly_salary: float = Field(gt=0, description="Monthly salary must be positive")


class PayrollOut(PayrollCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)