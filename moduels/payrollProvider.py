from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from moduels.PayrollDB import Payroll
from database import Base


class PayRollProvider(Base):
    __tablename__ = "PayRollProviders"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String, unique=True, index=True, nullable=False)
    providername = Column(String, unique=True, nullable=False)  # Fixed: added unique constraint
    description = Column(String)

    # Relationships
    earnings = relationship("Earning", back_populates="provider", cascade="all, delete-orphan")
    deductions = relationship("Deduction", back_populates="provider", cascade="all, delete-orphan")
    payroll = relationship(Payroll, back_populates="provider")


class Earning(Base):
    __tablename__ = "earnings"

    id = Column(Integer, primary_key=True, index=True)
    provider_id_fk = Column(String, ForeignKey("PayRollProviders.provider_id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String)   # e.g. "fixed" or "percentage"
    value = Column(Float, nullable=False)

    provider = relationship("PayRollProvider", back_populates="earnings")


class Deduction(Base):
    __tablename__ = "deductions"

    id = Column(Integer, primary_key=True, index=True)
    provider_id_fk = Column(String, ForeignKey("PayRollProviders.provider_id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String)   # e.g. "fixed" or "percentage"
    value = Column(Float, nullable=False)

    provider = relationship("PayRollProvider", back_populates="deductions")



