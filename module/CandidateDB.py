# models.py

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time, Float

from sqlalchemy.orm import relationship

from database import Base


# =========================================================
# CANDIDATE TABLE
# =========================================================


class Candidate(Base):

    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True)

    Candidate_ID = Column(String, unique=True)

    Candidate_name = Column(String)

    Job_title = Column(String)

    Candidate_Email = Column(String)

    Candidate_Phone = Column(String)

    Resume_path = Column(String)

    # Applied / Interview / Selected / Rejected
    Candidate_status = Column(
        String,
        default="Applied"
    )

    stages = relationship(
        "CandidateStage",
        back_populates="candidate"
    )
# =========================================================
# STAGE MASTER TABLE
# =========================================================


class Stage(Base):

    __tablename__ = "stages"

    id = Column(Integer, primary_key=True)

    Stage_name = Column(String)

    Stage_index = Column(Integer)


# =========================================================
# CANDIDATE STAGE TABLE
# =========================================================

class CandidateStage(Base):

    __tablename__ = "candidate_stages"

    id = Column(Integer, primary_key=True)

    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id")
    )

    stage_id = Column(
        Integer,
        ForeignKey("stages.id")
    )

    # Pending / In Progress / Completed / Rejected
    Stage_status = Column(
        String,
        default="Pending"
    )

    candidate = relationship(
        "Candidate",
        back_populates="stages"
    )

    stage = relationship("Stage")
# =========================================================
# INTERVIEW TABLE
# =========================================================

class Interview(Base):

    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True)

    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id")
    )

    stage_id = Column(
        Integer,
        ForeignKey("stages.id")
    )

    Interview_status = Column(
        String,
        default="Scheduled"
    )

    Interview_date = Column(Date)

    Interview_time = Column(Time)

    candidate = relationship("Candidate")

    stage = relationship("Stage")