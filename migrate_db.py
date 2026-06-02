import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("URL_DB")
engine = create_engine(db_url)

cols_to_add = [
    ("ats_keyskills", "Weight_Tech", "INTEGER DEFAULT 30"),
    ("ats_keyskills", "Weight_Abilities", "INTEGER DEFAULT 20"),
    ("ats_keyskills", "Weight_Experience", "INTEGER DEFAULT 20"),
    ("ats_keyskills", "Weight_Education", "INTEGER DEFAULT 15"),
    ("ats_keyskills", "Weight_Soft", "INTEGER DEFAULT 15"),
    ("departments", "Dep_id", "VARCHAR"),
]

with engine.connect() as conn:
    trans = conn.begin()
    try:
        for table, col, col_type in cols_to_add:
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = :table AND column_name = :col
                );
            """)
            res = conn.execute(check_query, {"table": table, "col": col}).scalar()
            if not res:
                print(f"Adding column '{col}' to table '{table}'...")
                alter_query = text(f'ALTER TABLE {table} ADD COLUMN "{col}" {col_type};')
                conn.execute(alter_query)
                print(f"Successfully added '{col}' to '{table}'!")
            else:
                print(f"Column '{col}' already exists in table '{table}'.")
        trans.commit()
        print("ALL MIGRATIONS COMPLETED SUCCESSFULLY!")
    except Exception as e:
        trans.rollback()
        print("MIGRATION FAILED:", str(e))
