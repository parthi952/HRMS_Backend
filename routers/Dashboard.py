from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from database import get_db
import module.EmplyeeDB as EmplyeeDB
import module.CandidateDB as CandidateDB

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)
    total_employees = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Status == "Active").count()
    new_hires = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.DateOfJoining >= month_start
    ).count()
    recruited_count = db.query(CandidateDB.Candidate).filter(
        CandidateDB.Candidate.Candidate_status == "Recruited"
    ).count()
    return {
        "newHiresMTD": new_hires,
        "joiningThisWeek": 0,
        "hardwareReady": total_employees,
        "offerAcceptance": recruited_count,
    }


@router.get("/onboarding/pipeline")
def get_onboarding_pipeline(db: Session = Depends(get_db)):
    stages = db.query(CandidateDB.Stage).order_by(CandidateDB.Stage.Stage_index).all()
    pipeline = []
    for stage in stages:
        count = db.query(CandidateDB.CandidateStage).filter(
            CandidateDB.CandidateStage.stage_id == stage.id,
            CandidateDB.CandidateStage.Stage_status == "In Progress"
        ).count()
        pipeline.append({
            "stage_name": stage.Stage_name,
            "count": count,
            "stage_index": stage.Stage_index,
        })
    recruited_count = db.query(CandidateDB.Candidate).filter(
        CandidateDB.Candidate.Candidate_status == "Recruited"
    ).count()
    pipeline.append({
        "stage_name": "Recruited",
        "count": recruited_count,
        "stage_index": len(stages) + 1,
    })
    return pipeline
