# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship

from database import Base
import module.DepartmentDB
import module.payrollProvider
import module.PayrollDB
from module.EmplyeeDB import Employee

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, index=True, nullable=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    password      = Column(String, nullable=False)
    # Effective (highest-privilege) role: admin, hr, developer, recruiter, manager, employee
    role          = Column(String, default="employee")
    # Every role the person was granted, comma-separated, e.g. "developer,hr"
    roles         = Column(String, nullable=True)
    # Explicit salary viewing permission toggle: True = can view unmasked salary/CTC, False = masked
    can_view_salary = Column(Boolean, default=False, nullable=True)
    # Custom allowed modules (comma-separated or JSON list)
    allowed_modules = Column(String, nullable=True)
    emp_id        = Column(String, ForeignKey("employees.Emp_id", ondelete="SET NULL"), nullable=True)

    # Relationship back to Employee profile if linked
    employee = relationship("Employee")
