# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, ForeignKey
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship

from database import Base
# pyrefly: ignore [missing-import]
from module.EmplyeeDB import Employee

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, index=True, nullable=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    password      = Column(String, nullable=False)
    # Effective (highest-privilege) role. Every existing permission check reads
    # this, so it stays a single value derived from `roles`.
    role          = Column(String, default="employee")  # options: admin, hr, manager, employee
    # Every role the person was granted, comma-separated, e.g. "admin,hr".
    roles         = Column(String, nullable=True)
    emp_id        = Column(String, ForeignKey("employees.Emp_id", ondelete="SET NULL"), nullable=True)

    # Relationship back to Employee profile if linked
    employee = relationship("Employee")