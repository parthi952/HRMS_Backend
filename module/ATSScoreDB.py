from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class CandidateATSScore(Base):
    __tablename__ = "candidate_ats_scores"

    id = Column(Integer, primary_key=True, index=True)

    # Candidate reference
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    Candidate_name = Column(String, nullable=False)

    # Job Post reference
    PostId = Column(String, nullable=False)

    # ATS Score results
    final_score = Column(Float, nullable=False)
    skills_score = Column(Float, nullable=True)
    semantic_score = Column(Float, nullable=True)
    experience_score = Column(Float, nullable=True)
    education_score = Column(Float, nullable=True)
    methodologies_score = Column(Float, nullable=True)

    # Summary fields
    matched_skills = Column(String, nullable=True)   # comma-separated
    missing_skills = Column(String, nullable=True)   # comma-separated
    suggestions = Column(String, nullable=True)      # comma-separated

    scored_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to Candidate
    candidate = relationship("Candidate", backref="ats_scores")
