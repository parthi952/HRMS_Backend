from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class OptionCategory(Base):
    __tablename__ = "option_categories"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)  # gender, payType, etc

    options = relationship("OptionItem", back_populates="category", cascade="all, delete")


class OptionItem(Base):
    __tablename__ = "option_items"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String)
    value = Column(String)
    symbol = Column(String, nullable=True)

    category_id = Column(Integer, ForeignKey("option_categories.id"))
    category = relationship("OptionCategory", back_populates="options")