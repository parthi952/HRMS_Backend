from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Requirement(Base):
    __tablename__ = "Requirement"

    id = Column(Integer, primary_key=True, index=True)
    Temp_Id = Column(String)
    name = Column(String)
    email = Column(String)
    department = Column(String)
    position = Column(String)
    
    # Documents - Resume
    Resume = Column(String)

    # Relationships
    marks_sheets = relationship("RequirementMarksSheet", back_populates="requirement", cascade="all, delete-orphan")
    assets = relationship("RequirementAsset", back_populates="requirement", cascade="all, delete-orphan")
    access = relationship("RequirementAccess", back_populates="requirement", cascade="all, delete-orphan")


class RequirementMarksSheet(Base):
    __tablename__ = "RequirementMarksSheet"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("Requirement.id"))
    
    doc_type = Column(String)  # e.g., "SSLC", "HSC", "Degree", "PostDegree", "Diploma"
    doc_id = Column(String)    # internal id from JSON (e.g., "1", "2")
    link = Column(String)
    status = Column(String)

    requirement = relationship("Requirement", back_populates="marks_sheets")


class RequirementAsset(Base):
    __tablename__ = "RequirementAsset"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("Requirement.id"))
    
    ass_id        = Column(String)
    Type          = Column(String)
    Ass_name      = Column(String)
    status        = Column(String)
    Conditon      = Column(String) # Matching JSON spelling "Conditon"
    handover_date = Column(String) # Keeping as String to match JSON format

    requirement = relationship("Requirement", back_populates="assets")


class RequirementAccess(Base):
    __tablename__ = "RequirementAccess"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("Requirement.id"))
    AccsesName = Column(String)
    requirement = relationship("Requirement", back_populates="access")
    