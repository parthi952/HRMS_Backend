from sqlalchemy import Column, Integer, String, Date, Boolean, Text
from database import Base


class FestivalWish(Base):
    __tablename__ = "festival_wishes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    message = Column(Text, nullable=False)
    recurs_yearly = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)
    last_email_sent_year = Column(Integer, nullable=True)
    audience = Column(String, default="employees")  # "employees" | "customers" | "both"


class WishContact(Base):
    __tablename__ = "wish_contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
