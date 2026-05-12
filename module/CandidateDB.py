from sqlalchemy import Column, Integer, String, ForeignKey, Float, Date, Time, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    Candidate_id = Column(String, unique=True, index=True, nullable=False)
    Candidate_name = Column(String, nullable=False)
    Job_title = Column(String, nullable=False)
    Candidate_Phone = Column(String, nullable=False)
    Candidate_Email = Column(String, nullable=False)
    Candidate_Skills = Column(String, nullable=False)
    Candidate_Source = Column(String, nullable=False)
    Resume_path = Column(String, nullable=False)
    Status = Column(String, nullable=False)
    Current_Stage = Column(String, default="Applied") # New field

    # Relationships
    stages = relationship("Stage_details", back_populates="candidate", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Candidate(id={self.id}, name='{self.Candidate_name}', status='{self.Status}')>"

class Stage_details(Base):
    __tablename__ = "stage_details"

    id = Column(Integer, primary_key=True, index=True)
    Candidate_id = Column(String, ForeignKey("candidates.Candidate_id", ondelete="CASCADE"), nullable=False)
    Stage_id = Column(String, unique=True, index=True, nullable=False)
    Stage_name = Column(String, nullable=False)
    Stage_status = Column(String, nullable=False) # Pending, In Progress, Completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    candidate = relationship("Candidate", back_populates="stages")

class Interview(Base):
    __tablename__ = "interview"

    id = Column(Integer, primary_key=True, index=True)
    Interview_id = Column(String, unique=True, index=True, nullable=False)
    Candidate_id = Column(String, ForeignKey("candidates.Candidate_id", ondelete="CASCADE"), nullable=False)
    Interview_date = Column(Date, nullable=False)
    Interview_time = Column(Time, nullable=False)
    Interview_status = Column(String, nullable=False) # e.g., Technical, HR, Final
    Stage_status = Column(String, default="Pending") # Pending, In Progress, Completed
    Interviewer_name = Column(String, nullable=True)
    Interview_score = Column(Float, nullable=True)
    Interviewer_feedback = Column(String, nullable=True)
    Final_decision = Column(String, nullable=True) # e.g., Passed, Failed
    Rejection_reason = Column(String, nullable=True)
    Selected_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")


