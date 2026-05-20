from sqlalchemy.orm import Session
from sqlalchemy import func
from module import DepartmentDB
import module.EmplyeeDB as EmplyeeDB
import module.CustomIDDB as CustomIDDB
import module.CandidateDB as CandidateDB


def get_active_config(db: Session, category: str):
    """Helper to fetch active settings from the database"""
    return (
        db.query(CustomIDDB.IDConfig)
        .filter(
            CustomIDDB.IDConfig.category == category,
            CustomIDDB.IDConfig.isActive == True,
        )
        .first()
    )


def generate_next_id(db: Session, category: str, id_column, default_prefix: str, default_separator: str, default_digit: int):
    # Fetch rules from CustomIDDB
    config = get_active_config(db, category)

    prefix = config.prefix if config else default_prefix
    separator = config.separator if config else default_separator
    digit = config.digit if config else default_digit

    # Fetch all existing IDs from the given column
    existing_ids = [r[0] for r in db.query(id_column).all() if r[0]]
    
    max_num = 0
    # Parse the IDs to find the maximum suffix
    expected_start = f"{prefix}{separator}"
    for eid in existing_ids:
        if isinstance(eid, str) and eid.startswith(expected_start):
            num_part = eid[len(expected_start):]
            if num_part.isdigit():
                max_num = max(max_num, int(num_part))
    
    next_num = max_num + 1

    # Ensure the generated ID is completely unique (safety check loop)
    while True:
        candidate_id = f"{prefix}{separator}{str(next_num).zfill(digit)}"
        # Double check if this candidate_id actually exists in the database
        exists = db.query(id_column).filter(id_column == candidate_id).first()
        if not exists:
            return candidate_id
        next_num += 1


# 1. Dynamic Employee ID Generation
def generate_next_empid(db: Session):
    return generate_next_id(
        db=db,
        category="EMP",
        id_column=EmplyeeDB.Employee.Emp_id,
        default_prefix="EMP",
        default_separator="-",
        default_digit=4
    )


# 2. Dynamic Department ID Generation
def generate_next_dep_id(db: Session):
    return generate_next_id(
        db=db,
        category="DEP",
        id_column=DepartmentDB.Department.Dep_id,
        default_prefix="DEP",
        default_separator="/",
        default_digit=3
    )


# 3. Dynamic Candidate ID Generation
def generate_next_candidate_id(db: Session):
    return generate_next_id(
        db=db,
        category="CAN",
        id_column=CandidateDB.Candidate.Candidate_ID,
        default_prefix="CAN",
        default_separator="-",
        default_digit=4
    )


# 4. Dynamic Interview ID Generation
def generate_next_interview_id(db: Session):
    return generate_next_id(
        db=db,
        category="INT",
        id_column=CandidateDB.Interview.Interview_ID,
        default_prefix="INT",
        default_separator="-",
        default_digit=4
    )
