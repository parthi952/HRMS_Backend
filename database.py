from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("URL_DB", "sqlite:///./hrms.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# Auto-migrate schema on boot for SQLite & PostgreSQL
try:
    from sqlalchemy import text as _sa_text
    with engine.connect() as _conn:
        is_pg = "postgres" in str(engine.url).lower()
        
        try:
            _conn.execute(_sa_text("ALTER TABLE users ADD COLUMN IF NOT EXISTS roles VARCHAR;" if is_pg else "ALTER TABLE users ADD COLUMN roles VARCHAR;"))
            _conn.commit()
        except Exception:
            _conn.rollback()

        try:
            _conn.execute(_sa_text("ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_salary BOOLEAN DEFAULT FALSE;" if is_pg else "ALTER TABLE users ADD COLUMN can_view_salary BOOLEAN DEFAULT 0;"))
            _conn.commit()
        except Exception:
            _conn.rollback()

        try:
            _conn.execute(_sa_text("ALTER TABLE users ADD COLUMN IF NOT EXISTS allowed_modules VARCHAR;" if is_pg else "ALTER TABLE users ADD COLUMN allowed_modules VARCHAR;"))
            _conn.commit()
        except Exception:
            _conn.rollback()

        try:
            _conn.execute(_sa_text("UPDATE users SET roles = role WHERE roles IS NULL AND role IS NOT NULL;"))
            _conn.commit()
        except Exception:
            _conn.rollback()
except Exception:
    pass
