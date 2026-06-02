import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("URL_DB")
engine = create_engine(db_url)

inspector = inspect(engine)
columns = inspector.get_columns("departments")
print("Columns in departments table:")
for col in columns:
    print(f"- {col['name']} ({col['type']})")
print("PK:", inspector.get_pk_constraint("departments"))
