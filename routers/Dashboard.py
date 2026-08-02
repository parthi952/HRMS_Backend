from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from database import get_db
import module.EmplyeeDB as EmplyeeDB
import module.CandidateDB as CandidateDB
import module.DepartmentDB as DepartmentDB

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)
    week_end = today + timedelta(days=7)
    total_employees = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Status == "Active").count()
    new_hires = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.DateOfJoining >= month_start
    ).count()
    joining_this_week = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.DateOfJoining >= today,
        EmplyeeDB.Employee.DateOfJoining <= week_end,
    ).count()
    recruited_count = db.query(CandidateDB.Candidate).filter(
        CandidateDB.Candidate.Candidate_status == "Recruited"
    ).count()
    return {
        "newHiresMTD": new_hires,
        "joiningThisWeek": joining_this_week,
        "hardwareReady": total_employees,
        "offerAcceptance": recruited_count,
    }


@router.get("/onboarding/pipeline")
def get_onboarding_pipeline(db: Session = Depends(get_db)):
    recruited = (
        db.query(CandidateDB.Candidate)
        .filter(CandidateDB.Candidate.Candidate_status == "Recruited")
        .order_by(CandidateDB.Candidate.id.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": c.Candidate_ID,
            "name": c.Candidate_name,
            "role": c.Job_title,
            "date": "TBD",
            "stage": "Recruited",
            "progress": 100,
            "status": "Ready",
        }
        for c in recruited
    ]


@router.get("/dashboard/employee-summary")
def get_employee_management_summary(db: Session = Depends(get_db)):
    today = date.today()

    total_employees = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Status == "Active").count()

    on_leave_today = db.query(EmplyeeDB.LeaveHistoryDB).filter(
        EmplyeeDB.LeaveHistoryDB.status == "Approved",
        EmplyeeDB.LeaveHistoryDB.from_date <= str(today),
        EmplyeeDB.LeaveHistoryDB.to_date >= str(today),
    ).count()

    present_today = db.query(EmplyeeDB.Attendance).filter(
        EmplyeeDB.Attendance.date == today,
        EmplyeeDB.Attendance.status == "Present",
    ).count()

    departments_count = db.query(DepartmentDB.Department).count()

    # Present-count for each of the last 5 weekdays (Mon-Fri)
    weekly_attendance = []
    days_collected = []
    day = today
    while len(days_collected) < 5:
        if day.weekday() < 5:
            days_collected.append(day)
        day -= timedelta(days=1)
    days_collected.reverse()
    for d in days_collected:
        count = db.query(EmplyeeDB.Attendance).filter(
            EmplyeeDB.Attendance.date == d,
            EmplyeeDB.Attendance.status == "Present",
        ).count()
        weekly_attendance.append({"day": d.strftime("%a"), "value": count})

    dept_rows = (
        db.query(EmplyeeDB.Employee.Department, func.count(EmplyeeDB.Employee.Emp_id))
        .filter(EmplyeeDB.Employee.Status == "Active")
        .group_by(EmplyeeDB.Employee.Department)
        .all()
    )
    department_distribution = [{"name": name or "Unassigned", "value": count} for name, count in dept_rows]

    type_rows = (
        db.query(EmplyeeDB.Employee.emp_type, func.count(EmplyeeDB.Employee.Emp_id))
        .filter(EmplyeeDB.Employee.Status == "Active")
        .group_by(EmplyeeDB.Employee.emp_type)
        .all()
    )
    type_total = sum(c for _, c in type_rows) or 1
    employment_types = {(t or "Unspecified"): round(c / type_total * 100) for t, c in type_rows}

    attendance_percent = round((present_today / total_employees) * 100) if total_employees else 0

    recent_activity = []
    recent_leaves = (
        db.query(EmplyeeDB.LeaveHistoryDB)
        .order_by(EmplyeeDB.LeaveHistoryDB.id.desc())
        .limit(3)
        .all()
    )
    for lv in recent_leaves:
        recent_activity.append(f"Leave request submitted by {lv.employee_name or lv.Emp_id}")

    recent_joiners = (
        db.query(EmplyeeDB.Employee)
        .filter(EmplyeeDB.Employee.DateOfJoining.isnot(None))
        .order_by(EmplyeeDB.Employee.DateOfJoining.desc())
        .limit(3)
        .all()
    )
    for emp in recent_joiners:
        recent_activity.append(f"{emp.name or emp.Emp_id} joined as {emp.designation or 'employee'}")

    return {
        "totalEmployees": total_employees,
        "onLeave": on_leave_today,
        "presentToday": present_today,
        "departments": departments_count,
        "weeklyAttendance": weekly_attendance,
        "departmentDistribution": department_distribution,
        "employmentTypes": employment_types,
        "attendancePercent": attendance_percent,
        "recentActivity": recent_activity[:5],
    }
