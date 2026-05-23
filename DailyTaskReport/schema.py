from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional


# ─── Daily Task Report (logs of work done by employees) ───────────────────────

class DailyTaskReportCreate(BaseModel):
    Date: Optional[date] = None
    Category: str
    Description: str
    Hours_Spent: Optional[float] = None


class DailyTaskReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID: int
    Emp_id: str
    Date: date
    Category: str
    Description: str
    Hours_Spent: Optional[float] = None


# ─── Task Assign (ledger of tasks delegated to employees or departments) ──────

class TaskAssignCreate(BaseModel):
    Emp_id: Optional[str] = None
    Department: Optional[str] = None
    Task_Name: str
    Task_Description: str
    Start_Date: date
    End_Date: date
    Priority: Optional[str] = "Medium"
    Status: Optional[str] = "Pending"


class TaskAssignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID: int
    Emp_id: Optional[str] = None
    Department: Optional[str] = None
    Task_Name: str
    Task_Description: str
    Start_Date: date
    End_Date: date
    Priority: str
    Status: str
    Assigned_By: Optional[str] = None
    Employee_Name: Optional[str] = "Unassigned"


class TaskStatusUpdate(BaseModel):
    Status: str
