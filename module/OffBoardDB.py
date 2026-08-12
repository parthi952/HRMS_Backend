from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey, Text
from database import Base


class ExitRequest(Base):
    __tablename__ = "exit_requests"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)
    employee_name = Column(String)
    department = Column(String)
    designation = Column(String)
    resignation_date = Column(Date)
    last_working_day = Column(Date)
    reason = Column(Text)
    status = Column(String, default="Pending")  # Pending, Approved, Rejected
    created_at = Column(Date)
