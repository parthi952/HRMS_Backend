import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import engine
from sqlalchemy import text

def clear_version():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM alembic_version"))
        conn.commit()
        print("alembic_version cleared.")

if __name__ == "__main__":
    clear_version()
