from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from Auth import roles as roles_util
from Auth.models import User
from Auth.router import get_current_user
from database import get_db
from EmployeePort.EmployeeBulkService import (
    build_csv_template,
    import_valid_rows,
    public_preview,
    read_import_rows,
    validate_import_rows,
)


router = APIRouter(prefix="/employee/bulk", tags=["Employee Bulk Import"])


def _require_admin_or_hr(user: User) -> None:
    if not roles_util.has_role(user, "admin", "hr"):
        raise HTTPException(status_code=403, detail="Admin or HR access required.")


async def _read_and_validate(file: UploadFile, db: Session):
    try:
        source_rows = read_import_rows(file.filename or "", await file.read())
        return validate_import_rows(db, source_rows)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/template")
def download_employee_template(current_user: User = Depends(get_current_user)):
    _require_admin_or_hr(current_user)
    return Response(
        content=build_csv_template(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="employee_import_template.csv"'},
    )


@router.post("/preview")
async def preview_employee_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin_or_hr(current_user)
    return public_preview(await _read_and_validate(file, db))


@router.post("/import")
async def import_employees(
    file: UploadFile = File(...),
    update_existing: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin_or_hr(current_user)
    validation = await _read_and_validate(file, db)
    if validation["summary"]["valid"] == 0:
        raise HTTPException(status_code=400, detail="The file has no valid employee rows to import.")
    try:
        result = import_valid_rows(db, validation, update_existing)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Employee import failed; no rows were committed.") from exc
    result["preview"] = public_preview(validation)
    return result
