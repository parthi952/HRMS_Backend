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
    template_id = Column(Integer, nullable=True)  # FK to wish_templates.id (nullable — falls back to the default template)


class WishTemplate(Base):
    __tablename__ = "wish_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    header_html = Column(Text, nullable=False)      # supports {{festival_name}}
    header_bg_color = Column(String, default="#9EE4FF")
    highlight_html = Column(Text, nullable=True)     # the "from us" callout box
    highlight_bg_color = Column(String, default="#9EE4FF")
    footer_html = Column(Text, nullable=False)       # contact details / sign-off
    footer_bg_color = Column(String, default="#FAFBFD")
    is_default = Column(Boolean, default=False)
    logo_url = Column(String, nullable=True)
    logo_width = Column(Integer, default=120)   # px
    logo_align = Column(String, default="center")  # "left" | "center" | "right"


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


class CommercialEmail(Base):
    """One-off / ad-hoc commercial email campaigns — same send pipeline as
    Festival Wishes (audience, template, CC, from-email, mail-merge) but
    with no date or yearly recurrence."""
    __tablename__ = "commercial_emails"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    audience = Column(String, default="employees")  # "employees" | "customers" | "both"
    cc_emails = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    template_id = Column(Integer, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommercialSendLog(Base):
    __tablename__ = "commercial_send_log"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, nullable=False)
    email_name = Column(String, nullable=False)
    recipient_name = Column(String, nullable=True)
    to_email = Column(String, nullable=False)
    cc_emails = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    status = Column(String, nullable=False)
    error = Column(String, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)


class EmailProviderConfig(Base):
    """Singleton-style row (id=1) holding which OAuth provider sends mail
    and its credentials, editable from Celebrations > Email Settings
    instead of server env vars."""
    __tablename__ = "email_provider_config"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=True)  # "microsoft" | "google"
    ms_client_id = Column(String, nullable=True)
    ms_client_secret = Column(String, nullable=True)
    ms_tenant = Column(String, default="common")
    ms_sender_email = Column(String, nullable=True)
    google_service_account_json = Column(Text, nullable=True)
    google_sender_email = Column(String, nullable=True)
