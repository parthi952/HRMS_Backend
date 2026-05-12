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