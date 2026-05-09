from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class IDConfig(Base):
    __tablename__ = "id_configs"

    # Use the long numeric string from image_afa65b.png as the primary key
    id = Column(String, primary_key=True, index=True) 
    category = Column(String)  # This will be "EMP" or "DEP"
    prefix = Column(String)
    separator = Column(String)
    digit = Column(Integer)
    isActive = Column(Boolean, default=False)