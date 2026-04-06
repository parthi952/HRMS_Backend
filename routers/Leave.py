from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func,select

import models, schemas
from database import get_db

router = APIRouter(
    prefix="/Leave",
    tags=["Leave"]
)

@router.get("/leave")
def leave (emp_Leave:schemas.Leave, db:Session=Depends(get_db)):
    try:
        leave_history=models.emp_Leave(
            Emp_id = emp_Leave.Emp_id,
            status = emp_Leave.status,
            employee_name = emp_Leave.employee_name,

            Total_Leave = emp_Leave.Total_Leave,

            Available =emp_Leave.Available,
            Used = emp_Leave.Used
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Employee ID '{leave_history.Emp_id}' already exists."
        )
    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


