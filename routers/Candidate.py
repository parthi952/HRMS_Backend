from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import module.CandidateDB as CandidateDB
import Schemas.CandidateSchemas as CandidateSchemas
from Caluclation.IdCustom import generate_next_candidate_id, generate_next_interview_id

router = APIRouter(prefix="/candidates", tags=["Candidates"])

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
    for key, value in update_data.items():
        setattr(db_candidate, key, value)
    
    try:
        db.commit()
        return {"message": "Candidate updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- Interview Endpoints ---

@router.get("/interviews/all", response_model=List[CandidateSchemas.Interview])
def list_all_interviews(db: Session = Depends(get_db)):
    return db.query(CandidateDB.Interview).all()

@router.post("/interviews/Schedule", status_code=status.HTTP_201_CREATED)
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

# --- Resource Fetching (Filters/Dropdowns) ---

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
