from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Department(Base):
    __tablename__ = "departments"
    Dep_id = Column(String, primary_key=True, index=True)
    Dep_name = Column(String, unique=True)
    Dep_head = Column(String)
    Dep_icon = Column(String)
    bg_color = Column(String)
    icon_color = Column(String)

    employees = relationship("Employee", back_populates="department", cascade="all, delete")