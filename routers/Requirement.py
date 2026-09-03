from typing import List, Optional
from datetime import date
import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pydantic import BaseModel

import module.RequirementDB as RequirementDB
import module.CandidateDB as CandidateDB
import module.EmplyeeDB as EmplyeeDB
import module.DepartmentDB as DepartmentDB
import module.OnboardingDB as OnboardingDB
import Auth.models as AuthModels
from Auth.Encrypt import hash_password
import Schemas.RequirementSchemas as RequirementSchemas
from database import get_db

router = APIRouter(prefix="/requirement", tags=["Requirement"])


class FinalizeOnboardingIn(BaseModel):
    emp_id: Optional[str] = None
    date_of_joining: Optional[date] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    emp_type: Optional[str] = "Full Time"
    annual_salary: Optional[float] = None
    create_login: Optional[bool] = True
    initial_leave_balance: Optional[int] = 24
    provision_m365: Optional[bool] = False
    m365_email: Optional[str] = None
    m365_temp_password: Optional[str] = "Welcome!2026Temp"


async def create_m365_user(
    name: str,
    email: str,
    job_title: str,
    department: str,
    temp_password: str = "Welcome!2026Temp"
) -> dict:
    """Creates a user account in Microsoft 365 / Entra ID via Microsoft Graph API."""
    from Auth.sso_router import _load_config
    cfg = _load_config()
    m = cfg.get("microsoft", {})
    if not (m.get("enabled") and m.get("client_id") and m.get("client_secret")):
        return {
            "success": False,
            "configured": False,
            "message": "Microsoft 365 SSO is not configured in Admin Settings. Account created in local HRMS only."
        }

    tenant = m.get("tenant", "common")
    name_parts = (name or "Employee").strip().split(" ")
    given_name = name_parts[0]
    surname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    user_principal = email.strip()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "client_id": m["client_id"],
                    "client_secret": m["client_secret"],
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            tokens = token_resp.json()
            if "access_token" not in tokens:
                return {
                    "success": False,
                    "configured": True,
                    "message": tokens.get("error_description", "Failed to obtain Microsoft Graph token")
                }

            access_token = tokens["access_token"]
            create_payload = {
                "accountEnabled": True,
                "displayName": name.strip(),
                "mailNickname": user_principal.split("@")[0],
                "userPrincipalName": user_principal,
                "givenName": given_name.strip() if given_name else name.strip(),
                "jobTitle": job_title or "Employee",
                "department": department or "General",
                "passwordProfile": {
                    "forceChangePasswordNextSignIn": True,
                    "password": temp_password
                }
            }
            if surname and surname.strip():
                create_payload["surname"] = surname.strip()
            res = await client.post(
                "https://graph.microsoft.com/v1.0/users",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=create_payload
            )
            if res.status_code in (200, 201):
                user_data = res.json()
                return {
                    "success": True,
                    "configured": True,
                    "m365_id": user_data.get("id"),
                    "m365_email": user_data.get("userPrincipalName") or user_principal,
                    "message": f"Successfully provisioned Microsoft 365 account for {user_principal}"
                }
            else:
                err_data = res.json()
                error_msg = err_data.get("error", {}).get("message", "Microsoft Graph user creation failed")
                return {
                    "success": False,
                    "configured": True,
                    "message": error_msg
                }
    except Exception as e:
        return {
            "success": False,
            "configured": True,
            "message": str(e)
        }


def sync_recruited_candidates_to_requirement(db: Session):
    """Auto-sync candidates who are Recruited or New Hires into Requirement table if not present."""
    try:
        candidates = db.query(CandidateDB.Candidate).filter(
            CandidateDB.Candidate.Candidate_status == "Recruited"
        ).all()

        existing_req_names = {
            r.name.lower().strip() for r in db.query(RequirementDB.Requirement).all() if r.name
        }

        for c in candidates:
            c_name = (c.Candidate_name or "").strip()
            if not c_name or c_name.lower() in existing_req_names:
                continue

            temp_id = f"REG-{c.id:04d}" if c.id else f"REG-{c.Candidate_ID or '0001'}"
            fallback_email = f"{c_name.lower().replace(' ', '.')}@example.com"
            new_req = RequirementDB.Requirement(
                Temp_Id=temp_id,
                name=c_name,
                email=c.Candidate_Email or fallback_email,
                department="Engineering",
                position=c.Job_title or "Team Member",
                Resume=c.Resume_path or ""
            )
            db.add(new_req)
            db.flush()

            # Default marksheets
            default_docs = [
                ("10th Marksheet", "1", "https://example.com/doc/10th.pdf", "Received"),
                ("12th Marksheet", "2", "https://example.com/doc/12th.pdf", "Received"),
                ("Degree Certificate", "3", "https://example.com/doc/degree.pdf", "Received"),
                ("Relieving and Experience Letter", "4", "", "Pending")
            ]
            for dtype, did, link, st in default_docs:
                db.add(RequirementDB.RequirementMarksSheet(
                    requirement_id=new_req.id,
                    doc_type=dtype,
                    doc_id=did,
                    link=link,
                    status=st
                ))

            # Default assets
            default_assets = [
                ("AST-01", "Hardware", "MacBook Pro 14 M3", "false", "New / Sealed", "Day 1 Handover"),
                ("AST-02", "Security", "Smart NFC Keycard", "false", "Active", "Day 1 Handover")
            ]
            for aid, atype, aname, ast, cond, hdate in default_assets:
                db.add(RequirementDB.RequirementAsset(
                    requirement_id=new_req.id,
                    ass_id=aid,
                    Type=atype,
                    Ass_name=aname,
                    status=ast,
                    Conditon=cond,
                    handover_date=hdate
                ))

            # Default access
            default_access = ["Company Google Workspace", "Slack Developer Team", "GitHub Enterprise"]
            for acc in default_access:
                db.add(RequirementDB.RequirementAccess(
                    requirement_id=new_req.id,
                    AccsesName=acc
                ))

            existing_req_names.add(c_name.lower())

        db.commit()
    except Exception as e:
        db.rollback()
        print("[WARN] sync_recruited_candidates_to_requirement:", e)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def create_requirement(
    req_in: RequirementSchemas.RequirementCreate, db: Session = Depends(get_db)
):
    try:
        new_req = RequirementDB.Requirement(
            Temp_Id=req_in.Temp_Id,
            name=req_in.name,
            email=req_in.email,
            department=req_in.department,
            position=req_in.position,
            Resume=req_in.Resume
        )
        db.add(new_req)
        db.flush()

        for ms in req_in.marks_sheets:
            db.add(RequirementDB.RequirementMarksSheet(
                requirement_id=new_req.id,
                doc_type=ms.doc_type,
                doc_id=ms.doc_id,
                link=ms.link,
                status=ms.status
            ))

        for asset in req_in.assets:
            db.add(RequirementDB.RequirementAsset(
                requirement_id=new_req.id,
                ass_id=asset.ass_id,
                Type=asset.Type,
                Ass_name=asset.Ass_name,
                status=asset.status,
                Conditon=asset.Conditon,
                handover_date=asset.handover_date
            ))

        for acc in req_in.access:
            db.add(RequirementDB.RequirementAccess(
                requirement_id=new_req.id,
                AccsesName=acc.AccsesName
            ))

        db.commit()
        return {"message": "Requirement created successfully", "id": new_req.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[RequirementSchemas.RequirementResponse])
def list_requirements(db: Session = Depends(get_db)):
    sync_recruited_candidates_to_requirement(db)
    requirements = db.query(RequirementDB.Requirement).all()
    return requirements


@router.get("/eligible-candidates")
def get_eligible_candidates(db: Session = Depends(get_db)):
    candidates = db.query(CandidateDB.Candidate).filter(
        CandidateDB.Candidate.Candidate_status == "Recruited"
    ).all()
    return candidates


@router.get("/{id}", response_model=RequirementSchemas.RequirementResponse)
def get_requirement(id: int, db: Session = Depends(get_db)):
    sync_recruited_candidates_to_requirement(db)
    req = db.query(RequirementDB.Requirement).filter(RequirementDB.Requirement.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req


@router.put("/{id}")
def update_requirement(
    id: int,
    req_in: RequirementSchemas.RequirementCreate,
    db: Session = Depends(get_db)
):
    req = db.query(RequirementDB.Requirement).filter(RequirementDB.Requirement.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    try:
        req.Temp_Id = req_in.Temp_Id
        req.name = req_in.name
        req.email = req_in.email
        req.department = req_in.department
        req.position = req_in.position
        req.Resume = req_in.Resume

        db.query(RequirementDB.RequirementMarksSheet).filter_by(requirement_id=id).delete()
        db.query(RequirementDB.RequirementAsset).filter_by(requirement_id=id).delete()
        db.query(RequirementDB.RequirementAccess).filter_by(requirement_id=id).delete()

        for ms in req_in.marks_sheets:
            db.add(RequirementDB.RequirementMarksSheet(requirement_id=id, **ms.dict()))
        for asset in req_in.assets:
            db.add(RequirementDB.RequirementAsset(requirement_id=id, **asset.dict()))
        for acc in req_in.access:
            db.add(RequirementDB.RequirementAccess(requirement_id=id, **acc.dict()))

        db.commit()
        return {"message": "Requirement updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id}")
def delete_requirement(id: int, db: Session = Depends(get_db)):
    req = db.query(RequirementDB.Requirement).filter(RequirementDB.Requirement.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    try:
        db.delete(req)
        db.commit()
        return {"message": "Requirement deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# FINALIZE ONBOARDING: Convert Candidate into Active Employee
# =========================================================
@router.post("/{id}/finalize")
async def finalize_onboarding(
    id: int,
    payload: Optional[FinalizeOnboardingIn] = None,
    db: Session = Depends(get_db)
):
    req = db.query(RequirementDB.Requirement).filter(RequirementDB.Requirement.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement profile not found")

    try:
        # 1. Determine next Employee ID if not provided
        target_emp_id = (payload.emp_id if payload and payload.emp_id else "").strip()
        if not target_emp_id:
            existing_emp_ids = [e[0] for e in db.query(EmplyeeDB.Employee.Emp_id).all() if e[0]]
            max_num = 0
            for eid in existing_emp_ids:
                nums = re.findall(r"\d+", eid)
                if nums:
                    max_num = max(max_num, int(nums[0]))
            target_emp_id = f"EMP{max_num + 1:03d}"

        # 2. Ensure Department exists in Department master
        dept_name = (payload.department if payload and payload.department else (req.department or "Engineering")).strip()
        dept_exists = db.query(DepartmentDB.Department).filter(DepartmentDB.Department.Dep_name == dept_name).first()
        if not dept_exists:
            dep_id_clean = f"DEP-{dept_name[:3].upper()}"
            db.add(DepartmentDB.Department(
                Dep_id=dep_id_clean,
                Dep_name=dept_name,
                Dep_head="Admin"
            ))
            db.flush()

        # 3. Create or update Employee profile
        name_parts = (req.name or "Employee").strip().split(" ")
        f_name = name_parts[0]
        l_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        emp_email = (payload.m365_email if payload and payload.m365_email else req.email) or f"{f_name.lower()}@tibos.in"

        existing_emp = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == target_emp_id).first()
        if existing_emp:
            existing_emp.name = req.name
            existing_emp.f_name = f_name
            existing_emp.l_name = l_name
            existing_emp.email = emp_email
            existing_emp.Department = dept_name
            existing_emp.designation = payload.designation if payload and payload.designation else (req.position or "Team Member")
            existing_emp.DateOfJoining = payload.date_of_joining if payload and payload.date_of_joining else date.today()
            existing_emp.Status = "Active"
            if payload and payload.annual_salary:
                existing_emp.annualSalary = payload.annual_salary
        else:
            new_emp = EmplyeeDB.Employee(
                Emp_id=target_emp_id,
                name=req.name,
                f_name=f_name,
                l_name=l_name,
                email=emp_email,
                Department=dept_name,
                designation=payload.designation if payload and payload.designation else (req.position or "Team Member"),
                emp_type=payload.emp_type if payload and payload.emp_type else "Full Time",
                DateOfJoining=payload.date_of_joining if payload and payload.date_of_joining else date.today(),
                annualSalary=payload.annual_salary if payload else None,
                Status="Active"
            )
            db.add(new_emp)
            db.flush()

        # 4. Initialize Leave balance in LeaveDB
        existing_leave = db.query(EmplyeeDB.LeaveDB).filter(EmplyeeDB.LeaveDB.Emp_id == target_emp_id).first()
        leave_balance = payload.initial_leave_balance if payload and payload.initial_leave_balance is not None else 24
        if not existing_leave:
            db.add(EmplyeeDB.LeaveDB(
                Emp_id=target_emp_id,
                employee_name=req.name,
                Total_Leave=leave_balance,
                Available=leave_balance,
                Used=0
            ))

        # 5. Provision login user account in users table
        if payload is None or payload.create_login:
            user_by_email = db.query(AuthModels.User).filter(
                func.lower(AuthModels.User.email) == emp_email.strip().lower()
            ).first()
            if not user_by_email:
                uname = emp_email.split("@")[0] if emp_email else target_emp_id.lower()
                db.add(AuthModels.User(
                    email=emp_email,
                    username=uname,
                    password=hash_password("Welcome123"),
                    role="employee",
                    roles="employee",
                    emp_id=target_emp_id
                ))
            else:
                user_by_email.emp_id = target_emp_id

        # 6. Update Candidate & Onboarding pipeline records
        cand = db.query(CandidateDB.Candidate).filter(
            (func.lower(CandidateDB.Candidate.Candidate_name) == req.name.strip().lower()) |
            (func.lower(CandidateDB.Candidate.Candidate_Email) == (req.email or "").strip().lower())
        ).first()
        if cand:
            cand.Candidate_status = "Onboarded"

        hire = db.query(OnboardingDB.OnboardingHire).filter(
            (func.lower(OnboardingDB.OnboardingHire.name) == req.name.strip().lower()) |
            (func.lower(OnboardingDB.OnboardingHire.email) == (req.email or "").strip().lower())
        ).first()
        if hire:
            hire.stage = "Completed"
            hire.progress = 100
            hire.status = "Active"

        db.commit()

        # 7. Microsoft 365 Auto-provisioning (if requested)
        m365_status = None
        if payload and payload.provision_m365:
            m365_status = await create_m365_user(
                name=req.name,
                email=emp_email,
                job_title=payload.designation if payload and payload.designation else (req.position or "Employee"),
                department=dept_name,
                temp_password=payload.m365_temp_password or "Welcome!2026Temp"
            )

        return {
            "message": f"Onboarding finalized! {req.name} is now an active employee with ID {target_emp_id}.",
            "emp_id": target_emp_id,
            "name": req.name,
            "email": emp_email,
            "department": dept_name,
            "designation": payload.designation if payload and payload.designation else (req.position or "Team Member"),
            "status": "Active",
            "m365": m365_status
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
