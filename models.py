from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base



# employee model

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    Emp_id = Column(String, unique=True, nullable=False)
    f_name = Column(String)
    l_name = Column(String)
    name = Column(String)
    gender = Column(String)
    dob = Column(Date, nullable=True)          
    phone = Column(String)
    email = Column(String)
    Department = Column(String)
    designation = Column(String)
    emp_type = Column(String)
    DateOfJoining = Column(Date, nullable=True)  # nullable
    Status = Column(String, default="Active")  # New field with default value

    # INS & FD

    apply_esi = Column(String)
    uan_number = Column(String)
    pf_id = Column(String)
    insurance_no = Column(String)
    aadhar_no = Column(String)
    esi_no = Column(String)
    esi_name = Column(String)
    insurance_provider = Column(String)
#   Nominees :Nominees[];


    # Current address
    Street = Column(String)
    City = Column(String)
    State = Column(String)
    Pin_Code = Column(Integer)

    # Permanent address
    p_Street = Column(String)
    p_City = Column(String)
    p_State = Column(String)
    p_Pin_Code = Column(Integer)

    # Salary
    provider = Column(String)
    payType = Column(String)
    currency = Column(String)
    payFrequency = Column(String)
    annualSalary = Column(Float)
    bonus_Type = Column(String)
    bonus_CalculationMode = Column(String)
    bonus_Value = Column(Float)

    # Bank
    bankName = Column(String)
    accountNumber = Column(String)
    ifscCode = Column(String)
    panNumber = Column(String)


    education = relationship("Education", back_populates="employee", cascade="all, delete-orphan")
    Familys = relationship("Familys", back_populates="employee", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")
    Work = relationship("WorkExpriance", back_populates="employee", cascade="all, delete-orphan")
    leaves = relationship("LeaveDB", back_populates="employee", cascade="all, delete-orphan")
    leavehistory = relationship("LeaveHistoryDB", back_populates="employee", cascade="all, delete-orphan")


class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)

    degree = Column(String)
    institution = Column(String)
    graduationYear = Column(Date, nullable=True)  # nullable — schema sends None for empty

    employee = relationship("Employee", back_populates="education")

class WorkExpriance(Base):
    
    __tablename__ = "Work"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)
    company_name = Column(String)
    position = Column(String)
    FromDate = Column(String)   
    ToDate = Column(String)

    employee = relationship("Employee", back_populates="Work")


class Familys(Base):
    __tablename__ = "Familys"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)

    person_name = Column(String)
    relationship_type = Column(String)
    contact = Column(String)
    person_dob = Column(Date, nullable=True)  # nullable

    employee = relationship("Employee", back_populates="Familys")
    nominees = relationship("Nominees", back_populates="family")



class Nominees(Base):
    __tablename__ = "nominee"
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("Familys.id"), nullable=False)
    nominee_name = Column(String)
    nominee_aadhar = Column(String)

    family = relationship("Familys", back_populates="nominees")


# attendance model
class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    Emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in = Column(String)
    check_out = Column(String)
    status = Column(String, nullable=False)
    employee_name = Column(String)

    employee = relationship("Employee", back_populates="attendance_records")


# employee leave page
class LeaveDB(Base):
    __tablename__ = "leave"

    id = Column(Integer, primary_key=True, index=True)
    Emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)
    employee_name = Column(String)
    Total_Leave = Column(Integer)
    Available = Column(Integer)
    Used = Column(Integer)
    employee = relationship("Employee", back_populates="leaves")


# employee leeve history
class LeaveHistoryDB(Base):
    __tablename__ = "leavehistory"
    id = Column(Integer, primary_key=True, index=True)
    Emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)
    employee_name = Column(String)
    Duration = Column(String)
    Reason = Column(String)
    from_date = Column(String)
    to_date = Column(String)
    Days = Column(Integer) 
    applayDate = Column(String)
    status = Column(String)        
    leave_type = Column(String) 
    status = Column(String)

    employee = relationship("Employee", back_populates="leavehistory")


    
class Payroll(Base):
    __tablename__ = "PayRoll"

    id = Column(Integer, primary_key=True, index=True)
    Emp_id = Column(String, ForeignKey("employees.Emp_id"), nullable=False)
    employee_name = Column(String)
    currency = Column(String)
    payFrequency = Column(String)
    annualSalary = Column(Float)
    monthlySalary = Column(Float)
    EPF = Column(Float)
    EPS = Column(Float)


