from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Payroll(Base):
    __tablename__ = "payroll"

    id = Column(Integer, primary_key=True, index=True)

    Payroll_id = Column("Payroll_id", Integer, unique=True, index=True, nullable=False)  

    provider_id = Column(String, ForeignKey("PayRollProviders.provider_id"), nullable=False)

    emp_id = Column("Emp_id", String, ForeignKey("employees.Emp_id"), nullable=False)  

    annual_salary = Column("annualSalary", Float, nullable=False)
    monthly_salary = Column("monthlySalary", Float, nullable=False)

    employee = relationship("Employee", back_populates="payroll")
    provider = relationship("PayRollProvider", back_populates="payroll")


from sqlalchemy import DateTime
from datetime import datetime

class PayslipReport(Base):
    __tablename__ = "payslip_reports"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column("Emp_id", String, ForeignKey("employees.Emp_id", ondelete="CASCADE"), nullable=False)
    month = Column(String(50), nullable=False)
    blob_url = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", foreign_keys=[emp_id])