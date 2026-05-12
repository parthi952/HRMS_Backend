from database import engine
from sqlalchemy import text

def fix_database():
    with engine.connect() as conn:
        print("Checking and fixing database columns...")
        
        # 1. Fix "Work" table
        try:
            conn.execute(text("ALTER TABLE \"Work\" ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY"))
            print("Successfully added 'id' to 'Work' table (or it already existed).")
        except Exception as e:
            print(f"Error updating 'Work' table: {e}")
            
        # 2. Fix "nominee" table
        try:
            # Check if family_id exists
            conn.execute(text("ALTER TABLE nominee ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY"))
            conn.execute(text("ALTER TABLE nominee ADD COLUMN IF NOT EXISTS family_id INTEGER REFERENCES \"Familys\"(id)"))
            
            # Remove emp_id if it exists (optional but cleaner as per user requirement)
            try:
                conn.execute(text("ALTER TABLE nominee DROP COLUMN IF EXISTS emp_id"))
                print("Dropped 'emp_id' from 'nominee' table.")
            except:
                pass
                
            print("Successfully updated 'nominee' table.")
        except Exception as e:
            print(f"Error updating 'nominee' table: {e}")
            
        conn.commit()
        print("Database sync complete.")

if __name__ == "__main__":
    fix_database()
