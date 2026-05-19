import sys
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from module.JobPosterDB import ATS_KeySkills
import uuid

db: Session = SessionLocal()
try:
    new_ats = ATS_KeySkills(
        id=str(uuid.uuid4()),
        PostId="JP-TEST-12345",
        Title="Test",
        Skills="test",
        Education="test",
        Experience="test",
        Abilities="test",
        Weight_Tech=30,
        Weight_Abilities=20,
        Weight_Experience=20,
        Weight_Education=15,
        Weight_Soft=15,
    )
    db.add(new_ats)
    db.commit()
    print("SUCCESS")
except Exception as e:
    db.rollback()
    print("ERROR:", str(e))
finally:
    db.close()
