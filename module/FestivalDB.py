from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text
from datetime import datetime
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
    cc_emails = Column(String, nullable=True)  # comma-separated
    from_email = Column(String, nullable=True)  # overrides GRAPH_SENDER_EMAIL if set


class WishContact(Base):
    __tablename__ = "wish_contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)


class WishSendLog(Base):
    __tablename__ = "wish_send_log"

    id = Column(Integer, primary_key=True, index=True)
    wish_id = Column(Integer, nullable=False)
    wish_name = Column(String, nullable=False)
    recipient_name = Column(String, nullable=True)
    to_email = Column(String, nullable=False)
    cc_emails = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    status = Column(String, nullable=False)  # "sent" | "failed"
    error = Column(String, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
