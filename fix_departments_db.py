import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
import module.DepartmentDB as DepartmentDB
from database import Base

load_dotenv()
db_url = os.getenv("URL_DB")
engine = create_engine(db_url)

print("Dropping departments table...")
DepartmentDB.Department.__table__.drop(engine, checkfirst=True)

print("Recreating departments table with correct constraints (Primary Key, Unique)...")
DepartmentDB.Department.__table__.create(engine, checkfirst=True)

print("Done! Database fixed.")
