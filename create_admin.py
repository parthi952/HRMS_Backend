"""
Run this script to create or update the admin user in the database using direct SQL.
Usage: python create_admin.py
"""

import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from database import engine
from Auth.Encrypt import hash_password

ADMIN_USERNAME = "admin"
ADMIN_EMAIL    = "admin@hrms.local"
ADMIN_PASSWORD = "Admin12345"
ADMIN_ROLE     = "admin"

def create_admin():
    hashed_pwd = hash_password(ADMIN_PASSWORD)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Check if user exists
            res = conn.execute(
                text("SELECT id FROM users WHERE username = :u OR email = :e"),
                {"u": ADMIN_USERNAME, "e": ADMIN_EMAIL}
            ).fetchone()
            
            if res:
                conn.execute(
                    text("UPDATE users SET username = :u, password = :p, role = :r WHERE id = :id"),
                    {"u": ADMIN_USERNAME, "p": hashed_pwd, "r": ADMIN_ROLE, "id": res[0]}
                )
                print("[SUCCESS] Admin user updated!")
            else:
                conn.execute(
                    text("INSERT INTO users (username, email, password, role) VALUES (:u, :e, :p, :r)"),
                    {"u": ADMIN_USERNAME, "e": ADMIN_EMAIL, "p": hashed_pwd, "r": ADMIN_ROLE}
                )
                print("[SUCCESS] Admin user created!")
            
            trans.commit()
            print("-" * 40)
            print(f"Username : {ADMIN_USERNAME}")
            print(f"Password : {ADMIN_PASSWORD}")
            print(f"Role     : {ADMIN_ROLE}")
            print(f"Email    : {ADMIN_EMAIL}")
            print("-" * 40)
        except Exception as e:
            trans.rollback()
            print(f"[ERROR] {e}")
            raise

if __name__ == "__main__":
    create_admin()
