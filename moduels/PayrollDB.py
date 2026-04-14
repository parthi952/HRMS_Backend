from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Payroll(Base):
    __tablename__ = "payroll"

    id = Column(Integer, primary_key=True, index=True)
    payroll_id = Column(Integer, unique=True, index=True, nullable=False)  # Fixed: added unique constraint
    provider_id = Column(String, ForeignKey("PayRollProviders.provider_id"), nullable=False)  # Fixed: added ForeignKey
    emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)  # Fixed: consistent snake_case
    annual_salary = Column(Float, nullable=False)   # Fixed: snake_case
    monthly_salary = Column(Float, nullable=False)  # Fixed: snake_case

    # Relationships
    employee = relationship("Employee", back_populates="payroll")
    provider = relationship("PayRollProvider", back_populates="payroll")  # Fixed: added back-reference