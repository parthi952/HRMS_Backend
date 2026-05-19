from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class JobPostDetailes(Base):
    __tablename__ = "jobpost_detailes"
    id = Column(String, primary_key=True, index=True)
    PostId = Column(String, unique=True)
    title = Column(String)
    department = Column(String)
    location = Column(String)
    stack = Column(String)
    salary = Column(String)
    experience = Column(String)
    education = Column(String)
    methods = Column(String)
    perks = Column(String)
    Description = Column(String)
    applyLink = Column(String)

    # Job lifecycle fields
    expire_date    = Column(Date, nullable=True)     # auto-disables when this date is crossed
    interview_date = Column(Date, nullable=True)     # scheduled interview date
    is_active      = Column(Boolean, default=True)   # manually toggle or auto-set by expire_date

    ats_keyskills = relationship("ATS_KeySkills", back_populates="job_post")
    ai_job_post = relationship("AiJobPost", back_populates="job_post")

class ATS_KeySkills(Base):
    __tablename__ = "ats_keyskills"
    id = Column(String, primary_key=True, index=True)
    PostId = Column(String, ForeignKey("jobpost_detailes.PostId"))
    Title = Column(String)
    Skills = Column(String)
    Education = Column(String)
    Experience = Column(String)
    Abilities = Column(String)
    
    # Custom category weights for HR
    Weight_Tech = Column(Integer, default=30)
    Weight_Abilities = Column(Integer, default=20)
    Weight_Experience = Column(Integer, default=20)
    Weight_Education = Column(Integer, default=15)
    Weight_Soft = Column(Integer, default=15)
    
    job_post = relationship("JobPostDetailes", back_populates="ats_keyskills")

class education_Options(Base):
    __tablename__ = "education_options"
    id = Column(String, primary_key=True, index=True)
    Edu_name = Column(String)

class AI_Model(Base):
    __tablename__ = "ai_model"
    id = Column(String, primary_key=True, index=True)
    Model_Name = Column(String)
    Bot_Type = Column(String, default="General Assistant")
    Avatar = Column(String, default="bottts")
    Icon = Column(String, default="Bot")
    Tone_Prompt = Column(String, nullable=True)
    Tone_Id = Column(String, nullable=True)


    modes = relationship("AIMode", back_populates="model")
    checklists = relationship("SelectionCheckList", back_populates="model")

class AIMode(Base):
    __tablename__ = "ai_mode"
    id = Column(String, primary_key=True, index=True)
    Mode_Type = Column(String)
    Prompt = Column(String)
    Icon = Column(String, default="Bot")
    model_id = Column(String, ForeignKey("ai_model.id"))
    
    model = relationship("AI_Model", back_populates="modes")

class SelectionCheckList(Base):
    __tablename__ = "selection_checklist"
    id = Column(String, primary_key=True, index=True)
    CheckList_Name = Column(String)
    enable = Column(Boolean)
    model_id = Column(String, ForeignKey("ai_model.id"))

    model = relationship("AI_Model", back_populates="checklists")
    
class AiJobPost(Base):
    __tablename__ = "ai_job_post"
    id = Column(String, primary_key=True, index=True)
    PostId = Column(String, ForeignKey("jobpost_detailes.PostId"))
    Title = Column(String)
    Poster = Column(String)
    job_post = relationship("JobPostDetailes", back_populates="ai_job_post")
