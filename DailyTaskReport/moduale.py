from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from database import Base
import datetime


class DailyTaskReport(Base):
    __tablename__ = "daily_task_report"

    ID          = Column(Integer, primary_key=True, index=True)
    Emp_id      = Column(String, ForeignKey("employees.Emp_id", ondelete="CASCADE"), nullable=False)
    Date        = Column(Date, nullable=False, default=datetime.date.today)
    Category    = Column(String(50), nullable=False)
    Description = Column(String(500), nullable=False)
    Hours_Spent = Column(Float, nullable=True)

    employee = relationship("Employee", foreign_keys=[Emp_id])


class TaskAssign(Base):
    __tablename__ = "task_assign"

    ID               = Column(Integer, primary_key=True, index=True)
    Emp_id           = Column(String, ForeignKey("employees.Emp_id", ondelete="CASCADE"), nullable=True)
    Department       = Column(String, ForeignKey("departments.Dep_name", ondelete="CASCADE"), nullable=True)
    Task_Name        = Column(String(100), nullable=False)
    Task_Description = Column(String(1000), nullable=False)
    Start_Date       = Column(Date, nullable=False)
    End_Date         = Column(Date, nullable=False)
    Priority         = Column(String(15), nullable=False, default="Medium")
    Status           = Column(String(15), nullable=False, default="Pending")
    Assigned_By      = Column(String, nullable=True)

    employee = relationship("Employee", foreign_keys=[Emp_id])
    department_rel = relationship("Department", foreign_keys=[Department])

    @property
    def Employee_Name(self) -> str:
        if self.employee:
            return self.employee.name or f"{self.employee.f_name} {self.employee.l_name}".strip()
        return "Unassigned"