from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, time, datetime

# --- Stage Details Schemas ---
class StageBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Stage_name: str
    Stage_status: str

class StageCreate(StageBase):
    Candidate_id: str
    Stage_id: Optional[str] = None # Optional if generated

class StageUpdate(BaseModel):
    Stage_name: Optional[str] = None
    Stage_status: Optional[str] = None

class Stage(StageBase):
    id: int
    Candidate_id: str
    Stage_id: str
    created_at: datetime

# --- Interview Schemas ---
class InterviewBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Interview_date: date
    Interview_time: time
    Interview_status: str # Round type
    Stage_status: str = "Pending"
    Interviewer_name: Optional[str] = None
    Interview_score: Optional[float] = None
    Interviewer_feedback: Optional[str] = None
    Final_decision: Optional[str] = None
    Rejection_reason: Optional[str] = None
    Selected_date: Optional[datetime] = None

class InterviewCreate(InterviewBase):
    Candidate_id: str
    Interview_id: Optional[str] = None

class InterviewUpdate(BaseModel):
    Interview_date: Optional[date] = None
    Interview_time: Optional[time] = None
    Interview_status: Optional[str] = None
    Stage_status: Optional[str] = None
    Interviewer_name: Optional[str] = None
    Interview_score: Optional[float] = None
    Interviewer_feedback: Optional[str] = None
    Final_decision: Optional[str] = None
    Rejection_reason: Optional[str] = None
    Selected_date: Optional[datetime] = None

class Interview(InterviewBase):
    id: int
    Candidate_id: str
    Interview_id: str
    created_at: datetime

# --- Candidate Schemas ---
class CandidateBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Candidate_name: str
    Job_title: str
    Candidate_Phone: str
    Candidate_Email: str
    Candidate_Skills: str
    Candidate_Source: str
    Resume_path: str
    Status: str
    Current_Stage: str = "Applied"

class CandidateCreate(CandidateBase):
    Candidate_id: Optional[str] = None

class CandidateUpdate(BaseModel):
    Candidate_name: Optional[str] = None
    Job_title: Optional[str] = None
    Candidate_Phone: Optional[str] = None
    Candidate_Email: Optional[str] = None
    Candidate_Skills: Optional[str] = None
    Candidate_Source: Optional[str] = None
    Resume_path: Optional[str] = None
    Status: Optional[str] = None

class Candidate(CandidateBase):
    id: int
    Candidate_id: str
    stages: List[Stage] = []
    interviews: List[Interview] = []

class BulkInterviewCreate(BaseModel):
    Candidate_ids: List[str]
    Interview_date: date
    Interview_time: time
    Interview_status: str # Round type
    Interviewer_name: Optional[str] = None
    Stage_status: str = "Pending"
