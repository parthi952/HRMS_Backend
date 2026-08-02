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
