from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import module.EmplyeeDB as EmplyeeDB
from database import get_db
from Auth.router import get_current_user
from Auth.models import User
from Auth import roles as roles_util

router = APIRouter(prefix="/shifts", tags=["Shift Roster"])


class ShiftIn(BaseModel):
    name: str
    start_time: str
    end_time: str
    full_day_hours: float
    half_day_hours: float


def _require_admin_or_hr(current_user: User):
    if not roles_util.has_role(current_user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Access denied. HR or Admin role required.")


@router.get("/")
def list_shifts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(EmplyeeDB.Shift).order_by(EmplyeeDB.Shift.name).all()


@router.post("/")
def create_shift(payload: ShiftIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin_or_hr(current_user)
    if payload.half_day_hours <= 0 or payload.full_day_hours <= payload.half_day_hours:
        raise HTTPException(status_code=400, detail="full_day_hours must be greater than half_day_hours, both positive")
    shift = EmplyeeDB.Shift(**payload.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


@router.put("/{shift_id}")
def update_shift(shift_id: int, payload: ShiftIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin_or_hr(current_user)
    if payload.half_day_hours <= 0 or payload.full_day_hours <= payload.half_day_hours:
        raise HTTPException(status_code=400, detail="full_day_hours must be greater than half_day_hours, both positive")
    shift = db.query(EmplyeeDB.Shift).filter(EmplyeeDB.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    for key, value in payload.model_dump().items():
        setattr(shift, key, value)
    db.commit()
    db.refresh(shift)
    return shift


@router.delete("/{shift_id}")
def delete_shift(shift_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin_or_hr(current_user)
    shift = db.query(EmplyeeDB.Shift).filter(EmplyeeDB.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.shift_id == shift_id).update({"shift_id": None})
    db.delete(shift)
    db.commit()
    return {"message": "Shift deleted"}
