from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import date, datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from database import get_db
import module.EmplyeeDB as EmplyeeDB
import module.CandidateDB as CandidateDB
import module.DepartmentDB as DepartmentDB
import module.OnboardingDB as OnboardingDB

import secrets

router = APIRouter(tags=["Dashboard"])


class NewHireCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    joining_date: Optional[str] = None  # e.g. "2026-09-15"
    stage: Optional[str] = "Ready to Join"
    status: Optional[str] = "Ready"
    progress: Optional[int] = None
    notes: Optional[str] = None
    provision_m365: Optional[bool] = False
    m365_temp_password: Optional[str] = "Welcome!2026Temp"


@router.post("/onboarding/new-hire", status_code=status.HTTP_201_CREATED)
async def create_new_hire(payload: NewHireCreate, db: Session = Depends(get_db)):
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    # Generate custom hire ID (NH-1001, NH-1002, ...)
    last_hire = db.query(OnboardingDB.OnboardingHire).order_by(OnboardingDB.OnboardingHire.id.desc()).first()
    next_num = 1001 if not last_hire else (last_hire.id + 1001)
    hire_code = f"NH-{next_num}"

    # Parse joining date
    join_dt = None
    if payload.joining_date:
        try:
            join_dt = datetime.strptime(payload.joining_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    if not join_dt:
        join_dt = date.today() + timedelta(days=7)

    # Calculate default progress from stage if not supplied
    stage_progress_map = {
        "Pre-boarding": 40,
        "Documentation": 60,
        "Ready to Join": 85,
        "Offer Accepted": 70,
        "Recruited": 100,
    }
    prog = payload.progress if payload.progress is not None else stage_progress_map.get(payload.stage or "", 75)

    new_hire = OnboardingDB.OnboardingHire(
        hire_id=hire_code,
        name=payload.name.strip(),
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        role=payload.role.strip() if payload.role else "Team Member",
        department=payload.department.strip() if payload.department else None,
        joining_date=join_dt,
        stage=payload.stage or "Ready to Join",
        progress=prog,
        status=payload.status or "Ready",
        notes=payload.notes,
        created_at=date.today(),
    )
    db.add(new_hire)

    # Also synchronize with Candidate table with status 'Recruited' if candidate doesn't already exist
    existing_candidate = None
    if payload.email:
        existing_candidate = db.query(CandidateDB.Candidate).filter(CandidateDB.Candidate.Candidate_Email == payload.email.strip()).first()
    
    if not existing_candidate:
        can_code = f"CAN-{next_num}"
        sync_candidate = CandidateDB.Candidate(
            Candidate_ID=can_code,
            Candidate_name=payload.name.strip(),
            Candidate_Email=payload.email.strip() if payload.email else None,
            Candidate_Phone=payload.phone.strip() if payload.phone else None,
            Job_title=payload.role.strip() if payload.role else "Team Member",
            Candidate_status="Recruited",
        )
        db.add(sync_candidate)

    db.commit()
    db.refresh(new_hire)

    m365_result = None
    if payload.provision_m365 and payload.email:
        from routers.Requirement import create_m365_user
        m365_result = await create_m365_user(
            name=payload.name,
            email=payload.email,
            job_title=payload.role or "Team Member",
            department=payload.department or "Engineering",
            temp_password=payload.m365_temp_password or "Welcome!2026Temp"
        )

    return {
        "message": "New hire created successfully",
        "hire_id": new_hire.hire_id,
        "name": new_hire.name,
        "role": new_hire.role,
        "department": new_hire.department,
        "joining_date": str(new_hire.joining_date),
        "stage": new_hire.stage,
        "progress": new_hire.progress,
        "status": new_hire.status,
        "m365": m365_result
    }


@router.delete("/onboarding/pipeline/{hire_id}")
def delete_new_hire(hire_id: str, db: Session = Depends(get_db)):
    hire = db.query(OnboardingDB.OnboardingHire).filter(
        or_(OnboardingDB.OnboardingHire.hire_id == hire_id, OnboardingDB.OnboardingHire.id == hire_id)
    ).first()
    if not hire:
        raise HTTPException(status_code=404, detail="New hire not found")
    db.delete(hire)
    db.commit()
    return {"message": "New hire removed successfully"}


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)
    week_end = today + timedelta(days=7)

    total_employees = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Status == "Active").count()

    emp_new_hires = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.DateOfJoining >= month_start
    ).count()
    onboard_new_hires = db.query(OnboardingDB.OnboardingHire).filter(
        OnboardingDB.OnboardingHire.joining_date >= month_start
    ).count()

    emp_joining_this_week = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.DateOfJoining >= today,
        EmplyeeDB.Employee.DateOfJoining <= week_end,
    ).count()
    onboard_joining_this_week = db.query(OnboardingDB.OnboardingHire).filter(
        OnboardingDB.OnboardingHire.joining_date >= today,
        OnboardingDB.OnboardingHire.joining_date <= week_end,
    ).count()

    recruited_count = db.query(CandidateDB.Candidate).filter(
        CandidateDB.Candidate.Candidate_status == "Recruited"
    ).count()
    onboard_count = db.query(OnboardingDB.OnboardingHire).count()

    return {
        "newHiresMTD": emp_new_hires + onboard_new_hires,
        "joiningThisWeek": emp_joining_this_week + onboard_joining_this_week,
        "hardwareReady": total_employees,
        "offerAcceptance": max(recruited_count, onboard_count),
    }


@router.get("/onboarding/pipeline")
def get_onboarding_pipeline(db: Session = Depends(get_db)):
    # 1. Fetch from Onboarding hires
    hires = (
        db.query(OnboardingDB.OnboardingHire)
        .order_by(OnboardingDB.OnboardingHire.id.desc())
        .limit(20)
        .all()
    )

    results = []
    seen_names = set()

    for h in hires:
        seen_names.add(h.name.lower())
        results.append({
            "id": h.hire_id,
            "name": h.name,
            "role": h.role or "Team Member",
            "date": h.joining_date.strftime("%b %d, %Y") if h.joining_date else "Upcoming",
            "stage": h.stage or "Ready to Join",
            "progress": h.progress if h.progress is not None else 75,
            "status": h.status or "Ready",
            "department": h.department,
            "email": h.email,
        })

    # 2. Add any recruited candidates not yet in OnboardingHire
    recruited = (
        db.query(CandidateDB.Candidate)
        .filter(CandidateDB.Candidate.Candidate_status == "Recruited")
        .order_by(CandidateDB.Candidate.id.desc())
        .limit(10)
        .all()
    )
    for c in recruited:
        if c.Candidate_name and c.Candidate_name.lower() in seen_names:
            continue
        results.append({
            "id": c.Candidate_ID or f"CAN-{c.id}",
            "name": c.Candidate_name or "Candidate",
            "role": c.Job_title or "New Hire",
            "date": "Upcoming",
            "stage": "Recruited",
            "progress": 100,
            "status": "Ready",
            "department": None,
            "email": c.Candidate_Email,
        })

    # 3. Add upcoming employees if any
    today = date.today()
    upcoming_emps = (
        db.query(EmplyeeDB.Employee)
        .filter(EmplyeeDB.Employee.DateOfJoining >= today)
        .order_by(EmplyeeDB.Employee.DateOfJoining.asc())
        .limit(10)
        .all()
    )
    for emp in upcoming_emps:
        emp_name = emp.name or f"{emp.f_name or ''} {emp.l_name or ''}".strip()
        if emp_name and emp_name.lower() in seen_names:
            continue
        results.append({
            "id": emp.Emp_id,
            "name": emp_name or "Employee",
            "role": emp.designation or "Team Member",
            "date": emp.DateOfJoining.strftime("%b %d, %Y") if hasattr(emp.DateOfJoining, "strftime") else str(emp.DateOfJoining),
            "stage": "Employee Registered",
            "progress": 100,
            "status": "Ready",
            "department": emp.Department,
            "email": emp.email,
        })

    return results


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


# =========================================================
# OFFER LETTER TEMPLATES & WORKFLOW
# =========================================================

class OfferTemplateIn(BaseModel):
    template_key: str
    name: str
    category: Optional[str] = "Standard"
    description: Optional[str] = None
    header_title: Optional[str] = "ANTIGRAVITY ENTERPRISE SYSTEMS"
    body_intro: Optional[str] = None
    terms_clauses: Optional[str] = None
    benefits_summary: Optional[str] = None
    signoff_title: Optional[str] = "HR Operations - Talent Acquisition"
    is_default: Optional[bool] = False

class SendOfferIn(BaseModel):
    recipient_name: str
    recipient_email: Optional[str] = None
    role: str
    joining_date: str
    ctc: str
    template_key: str
    location: Optional[str] = "Headquarters / Remote"
    valid_until: Optional[str] = None


def seed_default_offer_templates(db: Session):
    existing = db.query(OnboardingDB.OfferLetterTemplate).count()
    if existing > 0:
        return

    defaults = [
        OnboardingDB.OfferLetterTemplate(
            template_key="corporate_standard",
            name="Standard Corporate",
            category="General",
            description="Legally verified enterprise employment contract with statutory provident fund, comprehensive medical insurance, and 3-month probation.",
            header_title="APEX SOLUTIONS - ENTERPRISE HRMS",
            body_intro="We are pleased to offer you the position of {role} at Apex Solutions. We were very impressed by your background and achievements, and we are excited about the prospect of you joining our dynamic organization.",
            terms_clauses="Probation: 90 days from the date of joining.\nNotice Period: 30 days during probation, 60 days following confirmation.\nWorking Hours: 40 hours per week with flexible core hours.",
            benefits_summary="Group Health Insurance coverage up to ?5,00,000.\nAnnual Learning & Development Allowance.\n24 Annual Paid Leaves + Public Holidays.",
            signoff_title="HR Operations - Global Talent Acquisition",
            is_default=True,
        ),
        OnboardingDB.OfferLetterTemplate(
            template_key="tech_startup",
            name="Tech & Engineering Fast-Track",
            category="Engineering",
            description="Modern engineering offer with flexible remote working, annual technology stipend, and equity incentive grant.",
            header_title="APEX LABS - ENGINEERING & INNOVATION",
            body_intro="Welcome to the team! We are thrilled to extend an offer for the role of {role}. Our engineers build state-of-the-art products that serve millions, and we know your talent will elevate our craft.",
            terms_clauses="Workplace Model: Hybrid / Fully Remote with flexible hours.\nEquipment: High-end developer workstation (MacBook Pro / Linux) provided on Day 1.\nIP Rights: Inventions created under company scope remain company intellectual property.",
            benefits_summary="Annual Home Office & Technology Stipend (?60,000/yr).\nESOPs Grant: Eligible for Employee Stock Option Plan upon 1 year vesting.\nUnlimited Wellness Days & Comprehensive Health Insurance.",
            signoff_title="VP of Engineering & Talent Operations",
            is_default=False,
        ),
        OnboardingDB.OfferLetterTemplate(
            template_key="executive_leadership",
            name="Executive & Leadership",
            category="Executive",
            description="Designed for Director and Executive hires with performance milestone bonuses, executive medical coverage, and strategic governance clauses.",
            header_title="APEX GLOBAL ENTERPRISES - EXECUTIVE OFFICE",
            body_intro="On behalf of the Board of Directors, we are honored to present this formal offer of appointment for the executive position of {role}. Your strategic vision and leadership will drive our organization into its next phase of market expansion.",
            terms_clauses="Reporting: Direct reporting to the Chief Executive Officer and Executive Board.\nGoverning Law: Confidentiality, non-solicitation, and IP agreements apply per Executive Charter.\nNotice Period: 90 days mutually required for leadership continuity.",
            benefits_summary="Annual Performance Bonus: Up to 30% of Gross CTC based on company KPIs.\nExecutive Family Health Coverage up to ?15,00,000.\nDedicated Executive Travel & Corporate Card Allowance.",
            signoff_title="Executive Office & Board of Directors",
            is_default=False,
        ),
        OnboardingDB.OfferLetterTemplate(
            template_key="internship_trainee",
            name="Internship & Graduate Trainee",
            category="Internship",
            description="Structured 6-month graduate trainee and internship program with mentorship, monthly stipend, and pre-placement offer conversion.",
            header_title="APEX CAMPUS - FUTURE TALENT PROGRAM",
            body_intro="Congratulations! We are delighted to select you for the {role} Internship Program at Apex Solutions. This program is designed to immerse you in real-world projects and accelerate your professional growth.",
            terms_clauses="Program Duration: 6 months with bi-monthly milestone reviews.\nFull-Time Conversion: Eligible for Pre-Placement Offer (PPO) based on internship evaluation.\nMentor: Assigned dedicated senior mentor for 1-on-1 technical coaching.",
            benefits_summary="Monthly Performance Stipend.\nCertificate of Completion & Letter of Recommendation.\nAccess to enterprise learning portals and tech workshops.",
            signoff_title="University Relations & Early Careers Lead",
            is_default=False,
        ),
    ]
    for d in defaults:
        db.add(d)
    db.commit()


@router.get("/onboarding/offer-templates")
def get_offer_templates(db: Session = Depends(get_db)):
    seed_default_offer_templates(db)
    templates = db.query(OnboardingDB.OfferLetterTemplate).order_by(OnboardingDB.OfferLetterTemplate.id.asc()).all()
    return [
        {
            "id": t.id,
            "template_key": t.template_key,
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "header_title": t.header_title,
            "body_intro": t.body_intro,
            "terms_clauses": t.terms_clauses,
            "benefits_summary": t.benefits_summary,
            "signoff_title": t.signoff_title,
            "is_default": t.is_default,
        }
        for t in templates
    ]


@router.post("/onboarding/offer-templates")
def save_offer_template(payload: OfferTemplateIn, db: Session = Depends(get_db)):
    existing = db.query(OnboardingDB.OfferLetterTemplate).filter(
        OnboardingDB.OfferLetterTemplate.template_key == payload.template_key
    ).first()

    if existing:
        existing.name = payload.name
        existing.category = payload.category or existing.category
        existing.description = payload.description or existing.description
        existing.header_title = payload.header_title or existing.header_title
        existing.body_intro = payload.body_intro or existing.body_intro
        existing.terms_clauses = payload.terms_clauses or existing.terms_clauses
        existing.benefits_summary = payload.benefits_summary or existing.benefits_summary
        existing.signoff_title = payload.signoff_title or existing.signoff_title
        if payload.is_default:
            db.query(OnboardingDB.OfferLetterTemplate).update({OnboardingDB.OfferLetterTemplate.is_default: False})
            existing.is_default = True
    else:
        if payload.is_default:
            db.query(OnboardingDB.OfferLetterTemplate).update({OnboardingDB.OfferLetterTemplate.is_default: False})
        existing = OnboardingDB.OfferLetterTemplate(
            template_key=payload.template_key,
            name=payload.name,
            category=payload.category or "Custom",
            description=payload.description,
            header_title=payload.header_title,
            body_intro=payload.body_intro,
            terms_clauses=payload.terms_clauses,
            benefits_summary=payload.benefits_summary,
            signoff_title=payload.signoff_title,
            is_default=payload.is_default or False,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return {"message": "Offer template saved successfully", "template_key": existing.template_key}


@router.get("/onboarding/offer-recipients")
def get_offer_recipients(db: Session = Depends(get_db)):
    recipients = []
    seen_names = set()

    # 1. New hires in pipeline
    hires = db.query(OnboardingDB.OnboardingHire).order_by(OnboardingDB.OnboardingHire.id.desc()).all()
    for h in hires:
        seen_names.add(h.name.lower())
        recipients.append({
            "id": h.hire_id,
            "name": h.name,
            "email": h.email,
            "role": h.role or "Team Member",
            "department": h.department,
            "joining_date": str(h.joining_date) if h.joining_date else "",
            "type": "New Hire",
        })

    # 2. Recruited candidates
    candidates = db.query(CandidateDB.Candidate).filter(
        CandidateDB.Candidate.Candidate_status.in_(["Recruited", "Selected", "Applied"])
    ).order_by(CandidateDB.Candidate.id.desc()).limit(15).all()
    for c in candidates:
        if c.Candidate_name and c.Candidate_name.lower() in seen_names:
            continue
        recipients.append({
            "id": c.Candidate_ID or f"CAN-{c.id}",
            "name": c.Candidate_name or "Candidate",
            "email": c.Candidate_Email,
            "role": c.Job_title or "Team Member",
            "department": None,
            "joining_date": "",
            "type": "Candidate",
        })

    return recipients


@router.post("/onboarding/send-offer")
def send_offer(payload: SendOfferIn, db: Session = Depends(get_db)):
    # Update candidate or new hire stage to 'Offer Sent' if found
    matched_hire = db.query(OnboardingDB.OnboardingHire).filter(
        func.lower(OnboardingDB.OnboardingHire.name) == payload.recipient_name.strip().lower()
    ).first()
    if matched_hire:
        matched_hire.stage = "Offer Accepted"
        matched_hire.progress = max(matched_hire.progress or 0, 75)
        db.commit()

    matched_cand = db.query(CandidateDB.Candidate).filter(
        func.lower(CandidateDB.Candidate.Candidate_name) == payload.recipient_name.strip().lower()
    ).first()
    if matched_cand:
        matched_cand.Candidate_status = "Recruited"
        db.commit()

    ref_num = f"OFFER-{datetime.now().year}-{secrets.randbelow(900) + 100}"
    return {
        "message": f"Offer letter successfully issued to {payload.recipient_name}!",
        "offer_reference": ref_num,
        "recipient": payload.recipient_name,
        "role": payload.role,
        "ctc": payload.ctc,
        "joining_date": payload.joining_date,
        "template_key": payload.template_key,
        "status": "Offer Released",
    }

