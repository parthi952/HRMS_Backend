import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import main to ensure all routers, models and relations (like Payroll) are fully imported/registered on SQLAlchemy metadata
import main

from database import SessionLocal
from Caluclation.IdCustom import (
    generate_next_empid,
    generate_next_dep_id,
    generate_next_candidate_id,
    generate_next_interview_id
)

def test_generators():
    db = SessionLocal()
    try:
        next_empid = generate_next_empid(db)
        print(f"Generated Next Employee ID: {next_empid}")

        next_depid = generate_next_dep_id(db)
        print(f"Generated Next Department ID: {next_depid}")

        next_candidateid = generate_next_candidate_id(db)
        print(f"Generated Next Candidate ID: {next_candidateid}")

        next_interviewid = generate_next_interview_id(db)
        print(f"Generated Next Interview ID: {next_interviewid}")

    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_generators()
