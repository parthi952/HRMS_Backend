# schemas.py

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, time, datetime


# -----------------------------
# Stage Master
# -----------------------------

class StageBase(BaseModel):
    Stage_name: str
    Stage_index: int

class StageResponse(StageBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

# -----------------------------
# Candidate
# -----------------------------

class CandidateBase(BaseModel):
    Candidate_name: str
    Job_title: str
    Candidate_Email: str
    Candidate_Phone: str
    Resume_path: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateResponse(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    Candidate_ID: str # Alphanumeric code
    Candidate_status: str
    current_candidate_stage: Optional[str] = None # Calculated dynamically in router
    completed_stages_count: Optional[int] = None
    total_stages_count: Optional[int] = None
    stages_list: Optional[List[dict]] = None

class CandidateUpdate(BaseModel):
    Candidate_name: Optional[str] = None
    Job_title: Optional[str] = None
    Candidate_Email: Optional[str] = None
    Candidate_Phone: Optional[str] = None
    Resume_path: Optional[str] = None
    Candidate_status: Optional[str] = None

# -----------------------------
# Interview
# -----------------------------

class InterviewCreate(BaseModel):
    candidate_id: int
    stage_id: int
    Interview_date: date
    Interview_time: time

class InterviewUpdate(BaseModel):
    Interview_status: Optional[str] = None
    Interview_score: Optional[float] = None
    Interview_feedback: Optional[str] = None
    Final_decision: Optional[str] = None
    Rejection_reason: Optional[str] = None
    Interview_date: Optional[date] = None
    Interview_time: Optional[time] = None

class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    stage_id: int
    Interview_status: str
    Interview_date: date
    Interview_time: time
    Interview_ID: Optional[str] = None
    
    # Optional nested data for UI
    candidate_name: Optional[str] = None
    candidate_role: Optional[str] = None
    Candidate_ID: Optional[str] = None
    current_candidate_stage: Optional[str] = None

class BulkInterviewCreate(BaseModel):
    Candidate_ids: List[int]
    Stage_name: str
    Interview_date: date
    Interview_time: time
    Interviewer_name: Optional[str] = "HR Team"

# -----------------------------
# Candidate Stage
# -----------------------------

class CandidateStageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    stage_id: int
    Stage_status: str
    
    # Optional nested data
    Stage_name: Optional[str] = None