from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List, Optional

from database import get_db
from Auth.router import get_current_user
from Auth.models import User
import module.EmplyeeDB as EmplyeeDB
from DailyTaskReport.moduale import DailyTaskReport, TaskAssign
from DailyTaskReport.schema import (
    DailyTaskReportCreate,
    DailyTaskReportResponse,
    TaskAssignCreate,
    TaskAssignResponse,
    TaskStatusUpdate,
)

router = APIRouter(prefix="/daily-tasks", tags=["Daily Task Assignment & Reports"])


# ─── Task Assignment Endpoints ───────────────────────────────────────────────

@router.post("/assign", response_model=TaskAssignResponse, status_code=status.HTTP_201_CREATED)
def assign_task(
    payload: TaskAssignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign a task to either an individual employee (via Emp_id) or an entire department.
    """
    if not payload.Emp_id and not payload.Department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must specify either an employee ID (Emp_id) or a Department for assignment."
        )

    # If employee specified, verify they exist
    if payload.Emp_id:
        emp = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == payload.Emp_id).first()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {payload.Emp_id} does not exist."
            )

    # If department specified, verify it exists
    if payload.Department:
        # Check departments by name (case-insensitive or exact match)
        dept = db.query(EmplyeeDB.Department).filter(EmplyeeDB.Department.Dep_name == payload.Department).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department '{payload.Department}' does not exist in the database."
            )

    assigned_by_name = current_user.email
    if current_user.emp_id:
        emp_profile = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == current_user.emp_id).first()
        if emp_profile:
            assigned_by_name = emp_profile.name or f"{emp_profile.f_name} {emp_profile.l_name}".strip()

    # Create new task assignment
    new_task = TaskAssign(
        Emp_id=payload.Emp_id,
        Department=payload.Department,
        Task_Name=payload.Task_Name,
        Task_Description=payload.Task_Description,
        Start_Date=payload.Start_Date,
        End_Date=payload.End_Date,
        Priority=payload.Priority or "Medium",
        Status=payload.Status or "Pending",
        Assigned_By=assigned_by_name
    )

    db.add(new_task)
    try:
        db.commit()
        db.refresh(new_task)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save task assignment: {str(e)}"
        )

    return new_task


@router.get("/my-tasks", response_model=List[TaskAssignResponse])
def get_my_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all tasks assigned to the current employee, either directly or via their department.
    """
    if not current_user.emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Currently logged-in user is not associated with any Employee ID."
        )

    # Resolve employee profile to get department name
    employee = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == current_user.emp_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found."
        )

    # Retrieve tasks belonging to either the individual employee or the employee's department
    tasks = db.query(TaskAssign).filter(
        (TaskAssign.Emp_id == employee.Emp_id) | 
        ((TaskAssign.Department == employee.Department) & (TaskAssign.Department != None) & (TaskAssign.Department != ""))
    ).all()

    return tasks


# ─── Daily Task Report Endpoints ──────────────────────────────────────────────

@router.post("/report", response_model=DailyTaskReportResponse, status_code=status.HTTP_201_CREATED)
def submit_daily_report(
    payload: DailyTaskReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows employees to log their daily task accomplishments.
    """
    if not current_user.emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Currently logged-in user is not associated with any Employee ID."
        )

    report_date = payload.Date if payload.Date else date.today()

    new_report = DailyTaskReport(
        Emp_id=current_user.emp_id,
        Date=report_date,
        Category=payload.Category,
        Description=payload.Description,
        Hours_Spent=payload.Hours_Spent
    )

    db.add(new_report)
    try:
        db.commit()
        db.refresh(new_report)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit daily report: {str(e)}"
        )

    return new_report


@router.get("/my-reports", response_model=List[DailyTaskReportResponse])
def get_my_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch all reports submitted by the logged-in employee.
    """
    if not current_user.emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to an employee profile."
        )

    reports = db.query(DailyTaskReport).filter(DailyTaskReport.Emp_id == current_user.emp_id).order_by(DailyTaskReport.Date.desc()).all()
    return reports


@router.get("/all-reports", response_model=List[DailyTaskReportResponse])
def get_all_reports(
    emp_id: Optional[str] = None,
    report_date: Optional[date] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch all submitted daily reports. (Admin/Manager visibility with support for dynamic filtering)
    """
    query = db.query(DailyTaskReport)

    if emp_id:
        query = query.filter(DailyTaskReport.Emp_id == emp_id)
    if report_date:
        query = query.filter(DailyTaskReport.Date == report_date)
    if category:
        query = query.filter(DailyTaskReport.Category == category)

    reports = query.order_by(DailyTaskReport.Date.desc()).all()
    return reports


# ─── Additional Task Endpoints for Manager Assignments ────────────────────────

@router.get("/all-tasks", response_model=List[TaskAssignResponse])
def get_all_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve tasks based on user role.
    - Admin/HR see all tasks.
    - Manager sees department tasks, tasks assigned to themselves, or tasks they assigned.
    - Employees see tasks assigned to them or their department.
    """
    if current_user.role in ["admin", "hr"]:
        return db.query(TaskAssign).all()

    # Get employee profile
    employee = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == current_user.emp_id).first()
    if not employee:
        # User has no linked employee profile
        return db.query(TaskAssign).filter(TaskAssign.Assigned_By == current_user.email).all()

    if current_user.role == "manager":
        # Managers see:
        # 1. Tasks in their department
        # 2. Tasks they assigned
        # 3. Tasks assigned to their employee profile
        assigned_by_name = employee.name or f"{employee.f_name} {employee.l_name}".strip()
        dept_filter = (TaskAssign.Department == employee.Department) if employee.Department else (TaskAssign.Department == "None")
        
        return db.query(TaskAssign).filter(
            dept_filter |
            (TaskAssign.Emp_id == employee.Emp_id) |
            (TaskAssign.Assigned_By == assigned_by_name) |
            (TaskAssign.Assigned_By == current_user.email)
        ).all()
    else:
        # Regular employee sees:
        # 1. Tasks assigned directly to them
        # 2. Tasks assigned to their department
        dept_filter = ((TaskAssign.Department == employee.Department) & (TaskAssign.Department != None) & (TaskAssign.Department != ""))
        return db.query(TaskAssign).filter(
            (TaskAssign.Emp_id == employee.Emp_id) | dept_filter
        ).all()


@router.get("/team-members", response_model=List[dict])
def get_team_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch all team members in the logged-in user's department.
    """
    # Find employee profile of logged-in user
    if not current_user.emp_id:
        # Fallback to returning all active employees
        employees = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Status == "Active").all()
    else:
        emp = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == current_user.emp_id).first()
        if emp and emp.Department:
            # Get members in the same department
            employees = db.query(EmplyeeDB.Employee).filter(
                (EmplyeeDB.Employee.Department == emp.Department) &
                (EmplyeeDB.Employee.Status == "Active")
            ).all()
        else:
            employees = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Status == "Active").all()

    return [
        {
            "Emp_id": e.Emp_id,
            "name": e.name or f"{e.f_name} {e.l_name}".strip(),
            "email": e.email,
            "Department": e.Department,
            "designation": e.designation
        }
        for e in employees
    ]


@router.put("/task/{task_id}/status", response_model=TaskAssignResponse)
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the completion status of a specific task.
    """
    task = db.query(TaskAssign).filter(TaskAssign.ID == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} does not exist."
        )

    task.Status = payload.Status
    try:
        db.commit()
        db.refresh(task)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task status: {str(e)}"
        )

    return task
