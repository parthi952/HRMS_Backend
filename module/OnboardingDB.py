from sqlalchemy import Column, Integer, String, Date, Text, Boolean
from datetime import date
from database import Base

class OnboardingHire(Base):
    __tablename__ = "onboarding_hires"

    id = Column(Integer, primary_key=True, index=True)
    hire_id = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    role = Column(String)
    department = Column(String)
    joining_date = Column(Date)
    stage = Column(String, default="Ready to Join")
    progress = Column(Integer, default=60)
    status = Column(String, default="Ready")
    notes = Column(Text)
    created_at = Column(Date, default=date.today)


class OfferLetterTemplate(Base):
    __tablename__ = "offer_letter_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_key = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, default="Standard")
    description = Column(Text)
    header_title = Column(String, default="ANTIGRAVITY ENTERPRISE SYSTEMS")
    body_intro = Column(Text)
    terms_clauses = Column(Text)
    benefits_summary = Column(Text)
    signoff_title = Column(String, default="HR Operations • Talent Acquisition")
    is_default = Column(Boolean, default=False)
