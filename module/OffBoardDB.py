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


class OffboardingAsset(Base):
    __tablename__ = "offboarding_assets"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, nullable=False, index=True)
    emp_name = Column(String, nullable=False)
    asset_name = Column(String, nullable=False)
    asset_id = Column(String, nullable=False)
    status = Column(String, default="Pending")  # Pending, Returned
    returned_at = Column(String, nullable=True)


class OffboardingAccess(Base):
    __tablename__ = "offboarding_access"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, nullable=False, index=True)
    emp_name = Column(String, nullable=False)
    system = Column(String, nullable=False)
    access_id = Column(String, nullable=False)
    status = Column(String, default="Active")  # Active, Deactivated
    deactivated_at = Column(String, nullable=True)


class OffboardingKT(Base):
    __tablename__ = "offboarding_kt"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, nullable=False, index=True)
    emp_name = Column(String, nullable=False)
    task_name = Column(String, nullable=False)
    successor = Column(String, nullable=False)
    status = Column(String, default="In Progress")  # In Progress, Completed
    link = Column(String, default="N/A")


class OffboardingClearance(Base):
    __tablename__ = "offboarding_clearances"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, nullable=False, index=True)
    emp_name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    dept = Column(String, nullable=False)  # e.g., 'IT & Assets', 'Knowledge Transfer', 'Finance / Accounts', 'Human Resources'
    status = Column(String, default="Pending")  # Cleared, Pending, Action Required
    cleared_by = Column(String, default="-")


class OffboardingSettlement(Base):
    __tablename__ = "offboarding_settlements"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, nullable=False, index=True)
    emp_name = Column(String, nullable=False)
    designation = Column(String, nullable=True)
    last_working_day = Column(String, nullable=True)
    status = Column(String, default="Draft")  # Draft, Processed
    lines_json = Column(Text, nullable=False)  # JSON string of SettlementLine items
    net_amount = Column(Float, default=0.0)


class OffboardingDocument(Base):
    __tablename__ = "offboarding_documents"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, nullable=False, index=True)
    emp_name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="Exit Letter")  # Policy, Exit Letter, Experience, Tax
    status = Column(String, default="Pending")  # Generated, Pending, Signed
    file_url = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)
