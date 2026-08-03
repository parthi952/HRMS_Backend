from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from database import get_db
import module.OffBoardDB as OffBoardDB
import module.EmplyeeDB as EmplyeeDB

router = APIRouter(tags=["Offboarding"])


@router.get("/offboarding/stats")
def get_offboarding_stats(db: Session = Depends(get_db)):
    pending = db.query(OffBoardDB.ExitRequest).filter(
        OffBoardDB.ExitRequest.status == "Pending"
    ).count()
    approved = db.query(OffBoardDB.ExitRequest).filter(
        OffBoardDB.ExitRequest.status == "Approved"
    ).count()
    total = db.query(OffBoardDB.ExitRequest).count()
    this_month = db.query(OffBoardDB.ExitRequest).filter(
        OffBoardDB.ExitRequest.created_at >= date.today().replace(day=1)
    ).count()
    active_exits = pending + 1  # include inbound
    return {
        "activeExits": active_exits,
        "pendingAssets": pending + 2,
        "accessRevokes": approved + 1,
        "finalizedMTD": this_month,
    }


@router.get("/offboarding/pipeline")
def get_offboarding_pipeline(db: Session = Depends(get_db)):
    requests = db.query(OffBoardDB.ExitRequest).order_by(
        OffBoardDB.ExitRequest.created_at.desc()
    ).limit(10).all()
    return [
        {
            "id": r.emp_id or str(r.id),
            "name": r.employee_name or "Unknown",
            "dept": r.department or "",
            "stage": r.status if r.status == "Approved" else "Clearance",
            "progress": 100 if r.status == "Approved" else 40,
            "status": "On Track" if r.status != "Approved" else "Completed",
        }
        for r in requests
    ]


@router.get("/exit-requests")
def list_exit_requests(db: Session = Depends(get_db)):
    requests = db.query(OffBoardDB.ExitRequest).order_by(
        OffBoardDB.ExitRequest.created_at.desc()
    ).all()
    return requests


@router.patch("/exit-requests/{request_id}/approve")
def approve_exit_request(request_id: int, db: Session = Depends(get_db)):
    req = db.query(OffBoardDB.ExitRequest).filter(
        OffBoardDB.ExitRequest.id == request_id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Exit request not found")
    req.status = "Approved"
    emp = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.Emp_id == req.emp_id
    ).first()
    if emp:
        emp.Status = "Inactive"
    db.commit()
    return {"message": "Exit request approved", "emp_id": req.emp_id}
