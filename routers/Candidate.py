from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import module.CandidateDB as CandidateDB
import Schemas.CandidateSchemas as CandidateSchemas
from Caluclation.IdCustom import generate_next_candidate_id, generate_next_interview_id

router = APIRouter(prefix="/candidates", tags=["Candidates"])

@router.get("/GetAllInterviews", response_model=List[CandidateSchemas.Interview])
def list_all_interviews(db: Session = Depends(get_db)):
    return db.query(CandidateDB.Interview).all()

# --- Candidate CRUD ---

@router.post("/Register", status_code=status.HTTP_201_CREATED)
def create_candidate(candidate_in: CandidateSchemas.CandidateCreate, db: Session = Depends(get_db)):
    try:
        # Use provided ID or generate a new one
        new_id = candidate_in.Candidate_id or generate_next_candidate_id(db)
        
        # Filter out Candidate_id from the dict to avoid duplication if it's in the schema
        candidate_data = candidate_in.dict(exclude={"Candidate_id"})
        
        db_candidate = CandidateDB.Candidate(
            Candidate_id=new_id,
            **candidate_data
        )
        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)
        return {"message": "Candidate registered successfully", "Candidate_id": new_id}
    except Exception as e:
        db.rollback()
        print(f"Error registering candidate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all", response_model=List[CandidateSchemas.Candidate])
def list_candidates(db: Session = Depends(get_db)):
    return db.query(CandidateDB.Candidate).all()

@router.get("/{candidate_id}", response_model=CandidateSchemas.Candidate)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.query(CandidateDB.Candidate).filter(CandidateDB.Candidate.Candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@router.put("/Update/{candidate_id}")
def update_candidate(candidate_id: str, candidate_in: CandidateSchemas.CandidateUpdate, db: Session = Depends(get_db)):
    db_candidate = db.query(CandidateDB.Candidate).filter(CandidateDB.Candidate.Candidate_id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    update_data = candidate_in.dict(exclude_unset=True)
    
    # Validation: Only allow "Recruited" if current stage was Final Round
    if update_data.get("Status") == "Recruited":
        if db_candidate.Current_Stage != "Final Round" and db_candidate.Status != "Recruited":
             raise HTTPException(status_code=400, detail="Candidate must complete Final Round before being Recruited.")
    
    for key, value in update_data.items():
        setattr(db_candidate, key, value)
    
    try:
        db.commit()
        return {"message": "Candidate updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- Interview Endpoints ---

@router.post("/ScheduleInterview", status_code=status.HTTP_201_CREATED)
def schedule_interview(interview_in: CandidateSchemas.InterviewCreate, db: Session = Depends(get_db)):
    try:
        new_int_id = interview_in.Interview_id or generate_next_interview_id(db)
        interview_data = interview_in.dict(exclude={"Interview_id"})
        
        db_interview = CandidateDB.Interview(
            Interview_id=new_int_id,
            **interview_data
        )
        db.add(db_interview)
        db.commit()
        db.refresh(db_interview)
        return {"message": "Interview scheduled successfully", "Interview_id": new_int_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/UpdateInterview/{interview_id}")
def update_interview(interview_id: str, interview_in: CandidateSchemas.InterviewUpdate, db: Session = Depends(get_db)):
    db_interview = db.query(CandidateDB.Interview).filter(CandidateDB.Interview.Interview_id == interview_id).first()
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    update_data = interview_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_interview, key, value)
    
    try:
        db.commit()
        return {"message": "Interview updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/BulkSchedule", status_code=status.HTTP_201_CREATED)
def bulk_schedule_interviews(bulk_in: CandidateSchemas.BulkInterviewCreate, db: Session = Depends(get_db)):
    try:
        success_count = 0
        for candidate_id in bulk_in.Candidate_ids:
            # 1. Check if candidate exists
            db_candidate = db.query(CandidateDB.Candidate).filter(CandidateDB.Candidate.Candidate_id == candidate_id).first()
            if not db_candidate:
                continue
            
            # 2. Update Status to "Interview" and update Stage
            db_candidate.Status = "Interview"
            # If round type matches our pipeline stages, update it
            if bulk_in.Interview_status in ["Screening", "HR Round", "Technical Round", "Final Round"]:
                db_candidate.Current_Stage = bulk_in.Interview_status
            elif db_candidate.Current_Stage == "Applied":
                db_candidate.Current_Stage = "Screening"
            
            # 3. Create Interview Record
            new_int_id = generate_next_interview_id(db)
            db_interview = CandidateDB.Interview(
                Interview_id=new_int_id,
                Candidate_id=candidate_id,
                Interview_date=bulk_in.Interview_date,
                Interview_time=bulk_in.Interview_time,
                Interview_status=bulk_in.Interview_status,
                Interviewer_name=bulk_in.Interviewer_name,
                Stage_status=bulk_in.Stage_status
            )
            db.add(db_interview)
            success_count += 1
            
        db.commit()
        return {"message": f"Successfully scheduled {success_count} interviews", "count": success_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- Stage Endpoints ---

@router.post("/AddStage", status_code=status.HTTP_201_CREATED)
def add_stage(stage_in: CandidateSchemas.StageCreate, db: Session = Depends(get_db)):
    try:
        # Generate Stage_id if not provided (e.g., STG-001)
        if not stage_in.Stage_id:
            count = db.query(CandidateDB.Stage_details).count()
            stage_in.Stage_id = f"STG-{str(count + 1).zfill(3)}"
            
        db_stage = CandidateDB.Stage_details(**stage_in.dict())
        db.add(db_stage)
        db.commit()
        db.refresh(db_stage)
        return db_stage
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stages/{candidate_id}", response_model=List[CandidateSchemas.Stage])
def get_candidate_stages(candidate_id: str, db: Session = Depends(get_db)):
    return db.query(CandidateDB.Stage_details).filter(CandidateDB.Stage_details.Candidate_id == candidate_id).all()

# # --- Resource Fetching (Filters/Dropdowns) ---

@router.get("/resources/sources")
def get_candidate_sources(db: Session = Depends(get_db)):
    """Fetch unique candidate sources for filtering."""
    sources = db.query(CandidateDB.Candidate.Candidate_Source).distinct().all()
    return [s[0] for s in sources if s[0]]

@router.get("/resources/job-titles")
def get_job_titles(db: Session = Depends(get_db)):
    """Fetch unique job titles for filtering."""
    jobs = db.query(CandidateDB.Candidate.Job_title).distinct().all()
    return [j[0] for j in jobs if j[0]]