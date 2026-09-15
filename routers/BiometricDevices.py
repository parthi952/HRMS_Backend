from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import module.EmplyeeDB as EmplyeeDB
from database import get_db
from Auth.router import get_current_user
from Auth.models import User
from Auth import roles as roles_util

router = APIRouter(prefix="/biometric-devices", tags=["Biometric Device Registry"])


class DeviceIn(BaseModel):
    name: str
    location: str = ""
    serial_number: str
    is_active: bool = True


def _require_admin_or_hr(current_user: User):
    if not roles_util.has_role(current_user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Access denied. HR or Admin role required.")


def _serialize(device: EmplyeeDB.BiometricDevice) -> dict:
    return {
        "id": device.id,
        "name": device.name,
        "location": device.location,
        "serial_number": device.serial_number,
        "is_active": device.is_active,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
    }


@router.get("/")
def list_devices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin_or_hr(current_user)
    devices = db.query(EmplyeeDB.BiometricDevice).order_by(EmplyeeDB.BiometricDevice.name).all()
    return [_serialize(d) for d in devices]


@router.post("/")
def create_device(payload: DeviceIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin_or_hr(current_user)
    serial = payload.serial_number.strip()
    if not serial:
        raise HTTPException(status_code=400, detail="serial_number is required")
    if db.query(EmplyeeDB.BiometricDevice).filter(EmplyeeDB.BiometricDevice.serial_number == serial).first():
        raise HTTPException(status_code=400, detail="A device with this serial number is already registered")

    device = EmplyeeDB.BiometricDevice(
        name=payload.name, location=payload.location, serial_number=serial, is_active=payload.is_active,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return _serialize(device)


@router.put("/{device_id}")
def update_device(device_id: int, payload: DeviceIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin_or_hr(current_user)
    device = db.query(EmplyeeDB.BiometricDevice).filter(EmplyeeDB.BiometricDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    serial = payload.serial_number.strip()
    duplicate = db.query(EmplyeeDB.BiometricDevice).filter(
        EmplyeeDB.BiometricDevice.serial_number == serial,
        EmplyeeDB.BiometricDevice.id != device_id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="A device with this serial number is already registered")

    device.name = payload.name
    device.location = payload.location
    device.serial_number = serial
    device.is_active = payload.is_active
    db.commit()
    db.refresh(device)
    return _serialize(device)


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin_or_hr(current_user)
    device = db.query(EmplyeeDB.BiometricDevice).filter(EmplyeeDB.BiometricDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    return {"message": "Device deleted"}
