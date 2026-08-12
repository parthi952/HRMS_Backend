import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("URL_DB")
engine = create_engine(db_url)

with engine.connect() as conn:
    trans = conn.begin()
    try:
        # 1. Update existing NULL Dep_id rows with random values
        print("Updating existing NULL Dep_id rows...")
        conn.execute(text("UPDATE departments SET \"Dep_id\" = 'DEP-TMP-' || floor(random() * 1000)::int::text WHERE \"Dep_id\" IS NULL;"))
        
        # 2. Make the column NOT NULL
        print("Setting Dep_id to NOT NULL...")
        conn.execute(text('ALTER TABLE departments ALTER COLUMN "Dep_id" SET NOT NULL;'))
        
        # 3. Add the Primary Key constraint
        print("Adding PRIMARY KEY constraint...")
        conn.execute(text('ALTER TABLE departments ADD PRIMARY KEY ("Dep_id");'))
        
        trans.commit()
        print("Database properly fixed! (Primary Key added to Dep_id)")
    except Exception as e:
        trans.rollback()
        print("Error:", str(e))
