import json
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import module.OffBoardDB as OffBoardDB
import module.EmplyeeDB as EmplyeeDB

router = APIRouter(tags=["Offboarding"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ExitRequestCreate(BaseModel):
    emp_id: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    resignation_date: Optional[date] = None
    last_working_day: Optional[date] = None
    reason: Optional[str] = None


class AssetCreate(BaseModel):
    emp_id: str
    emp_name: str
    asset_name: str
    asset_id: str


class AccessCreate(BaseModel):
    emp_id: str
    emp_name: str
    system: str
    access_id: str


class KTTaskCreate(BaseModel):
    emp_id: str
    emp_name: str
    task_name: str
    successor: str
    link: Optional[str] = "N/A"


class ClearanceSignOff(BaseModel):
    status: str = "Cleared"
    cleared_by: Optional[str] = "Admin"


class SettlementLineItem(BaseModel):
    label: str
    amount: float
    type: str  # "addition" | "deduction"


class SettlementCreate(BaseModel):
    emp_id: str
    emp_name: str
    designation: Optional[str] = None
    last_working_day: Optional[str] = None
    lines: List[SettlementLineItem]


class DocumentCreate(BaseModel):
    emp_id: str
    emp_name: str
    department: str
    name: str
    category: str = "Exit Letter"
    status: str = "Generated"


# ── Seed Default Data ─────────────────────────────────────────────────────────

def seed_default_offboarding_data(db: Session):
    try:
        # 1. Exit requests
        if db.query(OffBoardDB.ExitRequest).count() == 0:
            sample_requests = [
                OffBoardDB.ExitRequest(
                    emp_id="EMP-001",
                    employee_name="Arun Kumar",
                    department="Engineering",
                    designation="Senior Developer",
                    resignation_date=date(2026, 4, 10),
                    last_working_day=date(2026, 5, 10),
                    reason="Personal reasons / Career growth",
                    status="Pending",
                    created_at=date(2026, 4, 10),
                ),
                OffBoardDB.ExitRequest(
                    emp_id="EMP-002",
                    employee_name="Priya Sharma",
                    department="Product",
                    designation="Product Designer",
                    resignation_date=date(2026, 4, 12),
                    last_working_day=date(2026, 5, 12),
                    reason="Higher studies & relocation",
                    status="Approved",
                    created_at=date(2026, 4, 12),
                ),
                OffBoardDB.ExitRequest(
                    emp_id="EMP-003",
                    employee_name="Vijay Raj",
                    department="Marketing",
                    designation="Growth Lead",
                    resignation_date=date(2026, 4, 15),
                    last_working_day=date(2026, 5, 15),
                    reason="Exploring new venture",
                    status="Pending",
                    created_at=date(2026, 4, 15),
                ),
            ]
            db.add_all(sample_requests)
            db.commit()

        # 2. Assets
        if db.query(OffBoardDB.OffboardingAsset).count() == 0:
            sample_assets = [
                OffBoardDB.OffboardingAsset(emp_id="EMP-001", emp_name="Arun Kumar", asset_name="MacBook Pro 16", asset_id="LAP-1029", status="Pending"),
                OffBoardDB.OffboardingAsset(emp_id="EMP-001", emp_name="Arun Kumar", asset_name="iPhone 13 Test Device", asset_id="MOB-8821", status="Returned", returned_at="2026-04-20"),
                OffBoardDB.OffboardingAsset(emp_id="EMP-001", emp_name="Arun Kumar", asset_name="Building Access Card", asset_id="KEY-0019", status="Pending"),
                OffBoardDB.OffboardingAsset(emp_id="EMP-002", emp_name="Priya Sharma", asset_name="Dell UltraSharp Monitor", asset_id="MON-9912", status="Pending"),
                OffBoardDB.OffboardingAsset(emp_id="EMP-002", emp_name="Priya Sharma", asset_name="Magic Keyboard & Mouse", asset_id="ACC-4410", status="Returned", returned_at="2026-04-22"),
            ]
            db.add_all(sample_assets)
            db.commit()

        # 3. Access deactivations
        if db.query(OffBoardDB.OffboardingAccess).count() == 0:
            sample_access = [
                OffBoardDB.OffboardingAccess(emp_id="EMP-001", emp_name="Arun Kumar", system="Corporate Email (M365)", access_id="arun@tibostech.in", status="Active"),
                OffBoardDB.OffboardingAccess(emp_id="EMP-001", emp_name="Arun Kumar", system="AWS Cloud Console", access_id="arun_dev_admin", status="Deactivated", deactivated_at="2026-04-18"),
                OffBoardDB.OffboardingAccess(emp_id="EMP-001", emp_name="Arun Kumar", system="Slack / Teams Workspace", access_id="@arunk", status="Active"),
                OffBoardDB.OffboardingAccess(emp_id="EMP-002", emp_name="Priya Sharma", system="VPN Corporate Tunnel", access_id="VPN-7788", status="Active"),
                OffBoardDB.OffboardingAccess(emp_id="EMP-002", emp_name="Priya Sharma", system="HRMS Portal Admin Role", access_id="PRIYA_HR", status="Deactivated", deactivated_at="2026-04-21"),
            ]
            db.add_all(sample_access)
            db.commit()

        # 4. KT tasks
        if db.query(OffBoardDB.OffboardingKT).count() == 0:
            sample_kt = [
                OffBoardDB.OffboardingKT(emp_id="EMP-001", emp_name="Arun Kumar", task_name="Core Architecture & Codebase Walkthrough", successor="Suresh M", status="Completed", link="https://docs.tibos.in/arch"),
                OffBoardDB.OffboardingKT(emp_id="EMP-001", emp_name="Arun Kumar", task_name="API Gateway & Microservices Handover", successor="Suresh M", status="In Progress", link="https://docs.tibos.in/api"),
                OffBoardDB.OffboardingKT(emp_id="EMP-001", emp_name="Arun Kumar", task_name="Production Cloud Secrets & Key Vault", successor="Deepika R", status="In Progress", link="N/A"),
                OffBoardDB.OffboardingKT(emp_id="EMP-002", emp_name="Priya Sharma", task_name="Design System Figma Libraries & Assets", successor="Rahul V", status="Completed", link="https://figma.com/file/tibos"),
            ]
            db.add_all(sample_kt)
            db.commit()

        # 5. Clearance
        if db.query(OffBoardDB.OffboardingClearance).count() == 0:
            sample_clearance = [
                OffBoardDB.OffboardingClearance(emp_id="EMP-001", emp_name="Arun Kumar", department="Engineering", dept="IT & Assets", status="Cleared", cleared_by="IT Admin"),
                OffBoardDB.OffboardingClearance(emp_id="EMP-001", emp_name="Arun Kumar", department="Engineering", dept="Knowledge Transfer", status="Pending", cleared_by="—"),
                OffBoardDB.OffboardingClearance(emp_id="EMP-001", emp_name="Arun Kumar", department="Engineering", dept="Finance / Accounts", status="Action Required", cleared_by="—"),
                OffBoardDB.OffboardingClearance(emp_id="EMP-001", emp_name="Arun Kumar", department="Engineering", dept="Human Resources", status="Pending", cleared_by="—"),
                OffBoardDB.OffboardingClearance(emp_id="EMP-002", emp_name="Priya Sharma", department="Product", dept="IT & Assets", status="Cleared", cleared_by="IT Admin"),
                OffBoardDB.OffboardingClearance(emp_id="EMP-002", emp_name="Priya Sharma", department="Product", dept="Knowledge Transfer", status="Cleared", cleared_by="Lead_Design"),
                OffBoardDB.OffboardingClearance(emp_id="EMP-002", emp_name="Priya Sharma", department="Product", dept="Finance / Accounts", status="Cleared", cleared_by="Finance_Lead"),
                OffBoardDB.OffboardingClearance(emp_id="EMP-002", emp_name="Priya Sharma", department="Product", dept="Human Resources", status="Pending", cleared_by="—"),
            ]
            db.add_all(sample_clearance)
            db.commit()

        # 6. Settlement
        if db.query(OffBoardDB.OffboardingSettlement).count() == 0:
            s1_lines = [
                {"label": "Base Salary (Pro-rata)", "amount": 45000, "type": "addition"},
                {"label": "Leave Encashment (6 Days)", "amount": 12500, "type": "addition"},
                {"label": "Gratuity Benefit", "amount": 25000, "type": "addition"},
                {"label": "Income Tax Deductions (TDS)", "amount": 4200, "type": "deduction"},
            ]
            s2_lines = [
                {"label": "Base Salary (Pro-rata)", "amount": 38000, "type": "addition"},
                {"label": "Bonus Carryover", "amount": 5000, "type": "addition"},
                {"label": "Notice Period Buyout", "amount": 15000, "type": "deduction"},
            ]
            sample_settlement = [
                OffBoardDB.OffboardingSettlement(
                    emp_id="EMP-001",
                    emp_name="Arun Kumar",
                    designation="Senior Developer",
                    last_working_day="May 10, 2026",
                    status="Draft",
                    lines_json=json.dumps(s1_lines),
                    net_amount=78300.0,
                ),
                OffBoardDB.OffboardingSettlement(
                    emp_id="EMP-002",
                    emp_name="Priya Sharma",
                    designation="Product Designer",
                    last_working_day="May 12, 2026",
                    status="Processed",
                    lines_json=json.dumps(s2_lines),
                    net_amount=28000.0,
                ),
            ]
            db.add_all(sample_settlement)
            db.commit()

        # 7. Documents
        if db.query(OffBoardDB.OffboardingDocument).count() == 0:
            sample_docs = [
                OffBoardDB.OffboardingDocument(emp_id="EMP-001", emp_name="Arun Kumar", department="Engineering", name="Resignation Acceptance Letter", category="Exit Letter", status="Signed", updated_at="Apr 20, 2026"),
                OffBoardDB.OffboardingDocument(emp_id="EMP-001", emp_name="Arun Kumar", department="Engineering", name="Relieving Letter", category="Exit Letter", status="Generated", updated_at="Apr 25, 2026"),
                OffBoardDB.OffboardingDocument(emp_id="EMP-001", emp_name="Arun Kumar", department="Engineering", name="Experience Certificate", category="Experience", status="Pending", updated_at="—"),
                OffBoardDB.OffboardingDocument(emp_id="EMP-001", emp_name="Arun Kumar", department="Engineering", name="Form 16 Tax Certificate", category="Tax", status="Generated", updated_at="Apr 26, 2026"),
                OffBoardDB.OffboardingDocument(emp_id="EMP-002", emp_name="Priya Sharma", department="Product", name="Relieving Letter", category="Exit Letter", status="Signed", updated_at="Apr 28, 2026"),
                OffBoardDB.OffboardingDocument(emp_id="EMP-002", emp_name="Priya Sharma", department="Product", name="Exit Interview Summary", category="Exit Letter", status="Signed", updated_at="Apr 22, 2026"),
            ]
            db.add_all(sample_docs)
            db.commit()
    except Exception as e:
        print(f"Error seeding offboarding data: {e}")
        db.rollback()


# ── Dashboard & Pipeline Endpoints ───────────────────────────────────────────

@router.get("/offboarding/stats")
def get_offboarding_stats(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)

    pending_exits = db.query(OffBoardDB.ExitRequest).filter(OffBoardDB.ExitRequest.status == "Pending").count()
    active_exits = db.query(OffBoardDB.ExitRequest).count()
    pending_assets = db.query(OffBoardDB.OffboardingAsset).filter(OffBoardDB.OffboardingAsset.status == "Pending").count()
    access_revokes = db.query(OffBoardDB.OffboardingAccess).filter(OffBoardDB.OffboardingAccess.status == "Active").count()
    finalized_mtd = db.query(OffBoardDB.ExitRequest).filter(OffBoardDB.ExitRequest.status == "Approved").count()

    return {
        "activeExits": max(active_exits, 1),
        "pendingAssets": pending_assets,
        "accessRevokes": access_revokes,
        "finalizedMTD": finalized_mtd,
    }


@router.get("/offboarding/pipeline")
def get_offboarding_pipeline(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)

    requests = db.query(OffBoardDB.ExitRequest).order_by(OffBoardDB.ExitRequest.created_at.desc()).all()
    pipeline = []
    for r in requests:
        is_approved = r.status == "Approved"
        clearances = db.query(OffBoardDB.OffboardingClearance).filter(OffBoardDB.OffboardingClearance.emp_id == r.emp_id).all()
        if clearances:
            cleared = sum(1 for c in clearances if c.status == "Cleared")
            prog = int((cleared / len(clearances)) * 100)
        else:
            prog = 100 if is_approved else 45

        stage = "Completed" if is_approved and prog == 100 else ("Clearance" if prog < 100 else "Settlement")
        status_label = "Completed" if is_approved else ("On Track" if prog >= 40 else "Action Required")

        pipeline.append({
            "id": r.emp_id or str(r.id),
            "name": r.employee_name or "Unknown",
            "dept": r.department or "General",
            "stage": stage,
            "progress": prog,
            "status": status_label,
        })
    return pipeline


# ── Exit Requests Endpoints ───────────────────────────────────────────────────

@router.get("/exit-requests")
def list_exit_requests(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)
    requests = db.query(OffBoardDB.ExitRequest).order_by(OffBoardDB.ExitRequest.created_at.desc()).all()
    return [
        {
            "id": str(r.id),
            "emp_id": r.emp_id,
            "emp_name": r.employee_name or "Unknown",
            "department": r.department or "",
            "designation": r.designation or "",
            "resignation_date": str(r.resignation_date) if r.resignation_date else "",
            "last_working_day": str(r.last_working_day) if r.last_working_day else "",
            "reason": r.reason or "",
            "status": r.status or "Pending",
        }
        for r in requests
    ]


@router.post("/exit-requests")
def create_exit_request(payload: ExitRequestCreate, db: Session = Depends(get_db)):
    emp_name = payload.employee_name
    dept = payload.department
    desig = payload.designation

    if not emp_name:
        emp = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == payload.emp_id).first()
        if emp:
            emp_name = emp.name
            dept = emp.Department
            desig = emp.designation

    new_req = OffBoardDB.ExitRequest(
        emp_id=payload.emp_id,
        employee_name=emp_name or "Employee",
        department=dept or "General",
        designation=desig or "Team Member",
        resignation_date=payload.resignation_date or date.today(),
        last_working_day=payload.last_working_day,
        reason=payload.reason or "Resignation submitted",
        status="Pending",
        created_at=date.today(),
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return {"message": "Exit request submitted successfully", "id": new_req.id}


@router.patch("/exit-requests/{request_id}/approve")
def approve_exit_request(request_id: str, db: Session = Depends(get_db)):
    req = db.query(OffBoardDB.ExitRequest).filter(
        (OffBoardDB.ExitRequest.id == int(request_id)) if request_id.isdigit() else (OffBoardDB.ExitRequest.emp_id == request_id)
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Exit request not found")

    req.status = "Approved"
    emp = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == req.emp_id).first()
    if emp:
        emp.Status = "Inactive"

    db.commit()
    return {"message": "Exit request approved", "status": "Approved", "emp_id": req.emp_id}


@router.patch("/exit-requests/{request_id}/reject")
def reject_exit_request(request_id: str, db: Session = Depends(get_db)):
    req = db.query(OffBoardDB.ExitRequest).filter(
        (OffBoardDB.ExitRequest.id == int(request_id)) if request_id.isdigit() else (OffBoardDB.ExitRequest.emp_id == request_id)
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Exit request not found")

    req.status = "Rejected"
    db.commit()
    return {"message": "Exit request rejected", "status": "Rejected", "emp_id": req.emp_id}


# ── Asset Recovery Endpoints ──────────────────────────────────────────────────

@router.get("/offboarding/assets")
def list_offboarding_assets(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)
    assets = db.query(OffBoardDB.OffboardingAsset).all()

    grouped = {}
    for a in assets:
        if a.emp_id not in grouped:
            grouped[a.emp_id] = {
                "emp_id": a.emp_id,
                "emp_name": a.emp_name,
                "assets": [],
            }
        grouped[a.emp_id]["assets"].append({
            "id": a.id,
            "asset_name": a.asset_name,
            "asset_id": a.asset_id,
            "status": a.status,
            "returned_at": a.returned_at,
        })
    return list(grouped.values())


@router.post("/offboarding/assets")
def add_offboarding_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    asset = OffBoardDB.OffboardingAsset(
        emp_id=payload.emp_id,
        emp_name=payload.emp_name,
        asset_name=payload.asset_name,
        asset_id=payload.asset_id,
        status="Pending",
    )
    db.add(asset)
    db.commit()
    return {"message": "Asset added to recovery list"}


@router.patch("/offboarding/assets/{asset_id}/return")
def mark_asset_returned(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(OffBoardDB.OffboardingAsset).filter(
        (OffBoardDB.OffboardingAsset.asset_id == asset_id) |
        (OffBoardDB.OffboardingAsset.id == int(asset_id) if asset_id.isdigit() else False)
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.status = "Returned"
    asset.returned_at = datetime.now().strftime("%Y-%m-%d")
    db.commit()
    return {"message": "Asset marked as returned", "asset_id": asset.asset_id}


# ── System Access Deactivation Endpoints ─────────────────────────────────────

@router.get("/offboarding/access")
def list_offboarding_access(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)
    items = db.query(OffBoardDB.OffboardingAccess).all()

    grouped = {}
    for item in items:
        if item.emp_id not in grouped:
            grouped[item.emp_id] = {
                "emp_id": item.emp_id,
                "emp_name": item.emp_name,
                "accessList": [],
            }
        grouped[item.emp_id]["accessList"].append({
            "id": str(item.id),
            "system": item.system,
            "access_id": item.access_id,
            "status": item.status,
            "deactivated_at": item.deactivated_at,
        })
    return list(grouped.values())


@router.post("/offboarding/access")
def add_offboarding_access(payload: AccessCreate, db: Session = Depends(get_db)):
    acc = OffBoardDB.OffboardingAccess(
        emp_id=payload.emp_id,
        emp_name=payload.emp_name,
        system=payload.system,
        access_id=payload.access_id,
        status="Active",
    )
    db.add(acc)
    db.commit()
    return {"message": "Access permission record created"}


@router.patch("/offboarding/access/{access_id}/deactivate")
def deactivate_system_access(access_id: str, db: Session = Depends(get_db)):
    item = db.query(OffBoardDB.OffboardingAccess).filter(
        (OffBoardDB.OffboardingAccess.id == int(access_id)) if access_id.isdigit() else (OffBoardDB.OffboardingAccess.access_id == access_id)
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Access record not found")

    item.status = "Deactivated" if item.status == "Active" else "Active"
    item.deactivated_at = datetime.now().strftime("%Y-%m-%d") if item.status == "Deactivated" else None
    db.commit()
    return {"message": f"Access status updated to {item.status}", "status": item.status}


# ── Knowledge Transfer (KT) Endpoints ─────────────────────────────────────────

@router.get("/offboarding/kt-tasks")
def list_kt_tasks(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)
    items = db.query(OffBoardDB.OffboardingKT).all()

    grouped = {}
    for item in items:
        if item.emp_id not in grouped:
            grouped[item.emp_id] = {
                "emp_id": item.emp_id,
                "emp_name": item.emp_name,
                "kt_tasks": [],
            }
        grouped[item.emp_id]["kt_tasks"].append({
            "id": str(item.id),
            "task_name": item.task_name,
            "successor": item.successor,
            "status": item.status,
            "link": item.link,
        })
    return list(grouped.values())


@router.post("/offboarding/kt-tasks")
def add_kt_task(payload: KTTaskCreate, db: Session = Depends(get_db)):
    kt = OffBoardDB.OffboardingKT(
        emp_id=payload.emp_id,
        emp_name=payload.emp_name,
        task_name=payload.task_name,
        successor=payload.successor,
        status="In Progress",
        link=payload.link or "N/A",
    )
    db.add(kt)
    db.commit()
    return {"message": "Knowledge transfer task created"}


@router.patch("/offboarding/kt-tasks/{task_id}/complete")
def complete_kt_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(OffBoardDB.OffboardingKT).filter(
        OffBoardDB.OffboardingKT.id == int(task_id) if task_id.isdigit() else False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="KT Task not found")

    task.status = "Completed"
    db.commit()
    return {"message": "KT task completed successfully", "status": "Completed"}


# ── Department Clearance Endpoints ───────────────────────────────────────────

@router.get("/offboarding/clearance")
def list_clearance_status(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)
    items = db.query(OffBoardDB.OffboardingClearance).all()

    grouped = {}
    for item in items:
        if item.emp_id not in grouped:
            grouped[item.emp_id] = {
                "emp_id": item.emp_id,
                "emp_name": item.emp_name,
                "department": item.department,
                "clearanceList": [],
            }
        grouped[item.emp_id]["clearanceList"].append({
            "id": item.id,
            "dept": item.dept,
            "status": item.status,
            "clearedBy": item.cleared_by,
        })
    return list(grouped.values())


@router.patch("/offboarding/clearance/{clearance_id}/sign-off")
def sign_off_clearance(clearance_id: int, payload: ClearanceSignOff, db: Session = Depends(get_db)):
    item = db.query(OffBoardDB.OffboardingClearance).filter(
        OffBoardDB.OffboardingClearance.id == clearance_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Clearance record not found")

    item.status = payload.status
    item.cleared_by = payload.cleared_by or "Admin"
    db.commit()
    return {"message": f"Department clearance marked as {item.status}", "status": item.status}


# ── Final Settlement (F&F) Endpoints ─────────────────────────────────────────

@router.get("/offboarding/settlement")
def list_settlements(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)
    items = db.query(OffBoardDB.OffboardingSettlement).all()

    result = []
    for s in items:
        try:
            lines = json.loads(s.lines_json)
        except Exception:
            lines = []
        result.append({
            "id": s.id,
            "emp_id": s.emp_id,
            "emp_name": s.emp_name,
            "designation": s.designation or "",
            "last_working_day": s.last_working_day or "",
            "status": s.status,
            "lines": lines,
            "net_amount": s.net_amount,
        })
    return result


@router.post("/offboarding/settlement")
def create_settlement(payload: SettlementCreate, db: Session = Depends(get_db)):
    net = sum(l.amount if l.type == "addition" else -l.amount for l in payload.lines)
    existing = db.query(OffBoardDB.OffboardingSettlement).filter(
        OffBoardDB.OffboardingSettlement.emp_id == payload.emp_id
    ).first()

    if existing:
        existing.emp_name = payload.emp_name
        existing.designation = payload.designation
        existing.last_working_day = payload.last_working_day
        existing.lines_json = json.dumps([l.dict() for l in payload.lines])
        existing.net_amount = net
    else:
        new_s = OffBoardDB.OffboardingSettlement(
            emp_id=payload.emp_id,
            emp_name=payload.emp_name,
            designation=payload.designation,
            last_working_day=payload.last_working_day,
            status="Draft",
            lines_json=json.dumps([l.dict() for l in payload.lines]),
            net_amount=net,
        )
        db.add(new_s)

    db.commit()
    return {"message": "Settlement ledger updated", "net_amount": net}


@router.patch("/offboarding/settlement/{settlement_id}/process")
def process_settlement(settlement_id: str, db: Session = Depends(get_db)):
    s = db.query(OffBoardDB.OffboardingSettlement).filter(
        (OffBoardDB.OffboardingSettlement.id == int(settlement_id)) if settlement_id.isdigit() else (OffBoardDB.OffboardingSettlement.emp_id == settlement_id)
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Settlement record not found")

    s.status = "Processed" if s.status == "Draft" else "Draft"
    db.commit()
    return {"message": f"Settlement status changed to {s.status}", "status": s.status}


# ── Exit Documents Endpoints ──────────────────────────────────────────────────

@router.get("/offboarding/documents")
def list_exit_documents(db: Session = Depends(get_db)):
    seed_default_offboarding_data(db)
    docs = db.query(OffBoardDB.OffboardingDocument).all()

    grouped = {}
    for d in docs:
        if d.emp_id not in grouped:
            grouped[d.emp_id] = {
                "emp_id": d.emp_id,
                "emp_name": d.emp_name,
                "department": d.department,
                "documents": [],
            }
        grouped[d.emp_id]["documents"].append({
            "id": str(d.id),
            "name": d.name,
            "category": d.category,
            "status": d.status,
            "updatedAt": d.updated_at or "Recent",
        })
    return list(grouped.values())


@router.post("/offboarding/documents/{doc_id}/generate")
def generate_exit_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(OffBoardDB.OffboardingDocument).filter(
        (OffBoardDB.OffboardingDocument.id == int(doc_id)) if doc_id.isdigit() else False
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = "Generated"
    doc.updated_at = datetime.now().strftime("%b %d, %Y")
    db.commit()
    return {"message": f"{doc.name} generated successfully", "status": "Generated"}


@router.post("/offboarding/documents")
def create_exit_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    doc = OffBoardDB.OffboardingDocument(
        emp_id=payload.emp_id,
        emp_name=payload.emp_name,
        department=payload.department,
        name=payload.name,
        category=payload.category,
        status=payload.status,
        updated_at=datetime.now().strftime("%b %d, %Y"),
    )
    db.add(doc)
    db.commit()
    return {"message": "Exit document record created"}
