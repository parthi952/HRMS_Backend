"""Validation and persistence for employee CSV/XLSX imports.

Preview and import share the same parser so the confirmation screen reflects
what the server will actually write. Only core employee-master fields are
handled here; payroll, bank, insurance, family, and education data continue to
use their dedicated workflows.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from Caluclation.IdCustom import generate_next_empid
import module.DepartmentDB as DepartmentDB
import module.EmplyeeDB as EmployeeDB


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 1000
ALLOWED_EXTENSIONS = (".csv", ".xlsx")

TEMPLATE_HEADERS = [
    "Employee ID",
    "First Name",
    "Last Name",
    "Email",
    "Phone",
    "Gender",
    "Date of Birth",
    "Department",
    "Designation",
    "Employee Type",
    "Date of Joining",
    "Status",
]

ALIASES = {
    "emp_id": ("employee_id", "emp_id", "employee_code", "id"),
    "f_name": ("first_name", "f_name", "firstname"),
    "l_name": ("last_name", "l_name", "lastname", "surname"),
    "name": ("employee_name", "full_name", "name"),
    "email": ("email", "email_address", "work_email", "official_email"),
    "phone": ("phone", "phone_number", "mobile", "mobile_number"),
    "gender": ("gender",),
    "dob": ("date_of_birth", "dob", "birth_date", "birthday"),
    "Department": ("department", "department_name", "dept"),
    "designation": ("designation", "job_title", "title", "position"),
    "emp_type": ("employee_type", "emp_type", "employment_type"),
    "DateOfJoining": ("date_of_joining", "joining_date", "doj"),
    "Status": ("status", "employee_status"),
}

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
INACTIVE_STATUSES = {"inactive": "Inactive", "terminated": "Terminated", "resigned": "Terminated"}


def _normalise_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _field(row: dict[str, Any], key: str) -> str:
    for alias in ALIASES[key]:
        if alias in row:
            return _text(row[alias])
    return ""


def _parse_date(value: Any) -> tuple[date | None, str | None]:
    if value in (None, ""):
        return None, None
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    raw = _text(value)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date(), None
        except ValueError:
            pass
    return None, f"Invalid date '{raw}'. Use YYYY-MM-DD."


def _split_name(first_name: str, last_name: str, full_name: str) -> tuple[str, str]:
    if first_name or last_name:
        return first_name, last_name
    parts = full_name.split(maxsplit=1)
    return (parts[0], parts[1] if len(parts) > 1 else "") if parts else ("", "")


def read_import_rows(filename: str, content: bytes) -> list[dict[str, Any]]:
    lower_name = (filename or "").lower()
    if not lower_name.endswith(ALLOWED_EXTENSIONS):
        raise ValueError("Only .csv and .xlsx files are supported.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("The uploaded file exceeds the 5 MB limit.")

    rows: list[dict[str, Any]] = []
    if lower_name.endswith(".csv"):
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        if not reader.fieldnames:
            raise ValueError("The CSV file has no header row.")
        for source_row in reader:
            rows.append({_normalise_header(k): v for k, v in source_row.items() if k})
    else:
        try:
            import openpyxl
        except ImportError as exc:
            raise ValueError("Excel support is not installed on the server.") from exc
        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        headers = next(iterator, None)
        if not headers:
            raise ValueError("The workbook has no header row.")
        normalised_headers = [_normalise_header(value) for value in headers]
        for values in iterator:
            if not any(value not in (None, "") for value in values):
                continue
            rows.append({key: value for key, value in zip(normalised_headers, values) if key})

    if not rows:
        raise ValueError("The file contains no employee rows.")
    if len(rows) > MAX_IMPORT_ROWS:
        raise ValueError(f"A maximum of {MAX_IMPORT_ROWS} employees can be imported at once.")
    return rows


def validate_import_rows(db: Session, source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    existing_employees = {
        employee.Emp_id: employee
        for employee in db.query(EmployeeDB.Employee).all()
    }
    existing_email_ids = {
        (employee.email or "").strip().lower(): employee.Emp_id
        for employee in existing_employees.values()
        if (employee.email or "").strip()
    }
    department_names = {
        item[0]
        for item in db.query(DepartmentDB.Department.Dep_name).all()
        if item[0]
    }
    department_lookup = {name.lower(): name for name in department_names}
    seen_ids: set[str] = set()
    seen_emails: set[str] = set()
    preview_rows: list[dict[str, Any]] = []

    for index, source in enumerate(source_rows, start=2):
        emp_id = _field(source, "emp_id")
        first_name, last_name = _split_name(
            _field(source, "f_name"),
            _field(source, "l_name"),
            _field(source, "name"),
        )
        email = _field(source, "email").lower()
        department_input = _field(source, "Department")
        department = department_lookup.get(department_input.lower(), department_input)
        dob, dob_error = _parse_date(next((source[a] for a in ALIASES["dob"] if a in source), ""))
        joining_date, joining_error = _parse_date(
            next((source[a] for a in ALIASES["DateOfJoining"] if a in source), "")
        )
        raw_status = _field(source, "Status").strip().lower()
        status = INACTIVE_STATUSES.get(raw_status, "Active" if raw_status == "active" else "")
        errors: list[str] = []

        if not first_name:
            errors.append("First Name is required.")
        if not email or not EMAIL_RE.match(email):
            errors.append("A valid Email is required.")
        if dob_error:
            errors.append(dob_error)
        if joining_error:
            errors.append(joining_error)
        if department and department not in department_names:
            errors.append(f"Department '{department}' does not exist.")
        if raw_status and not status:
            errors.append("Status must be Active, Inactive, Terminated, or Resigned.")
        if emp_id and emp_id in seen_ids:
            errors.append(f"Employee ID '{emp_id}' appears more than once in the file.")
        if email and email in seen_emails:
            errors.append(f"Email '{email}' appears more than once in the file.")

        existing_id_for_email = existing_email_ids.get(email)
        if existing_id_for_email and existing_id_for_email != emp_id:
            errors.append(f"Email already belongs to employee {existing_id_for_email}.")

        if emp_id:
            seen_ids.add(emp_id)
        if email:
            seen_emails.add(email)

        action = "update" if emp_id and emp_id in existing_employees else "create"
        preview_rows.append({
            "row_number": index,
            "action": "error" if errors else action,
            "employee_id": emp_id or None,
            "name": " ".join(part for part in (first_name, last_name) if part),
            "email": email,
            "date_of_birth": dob.isoformat() if dob else None,
            "department": department or None,
            "status": status or _field(source, "Status"),
            "errors": errors,
            "values": {
                "f_name": first_name,
                "l_name": last_name,
                "email": email,
                "phone": _field(source, "phone"),
                "gender": _field(source, "gender"),
                "dob": dob,
                "Department": department,
                "designation": _field(source, "designation"),
                "emp_type": _field(source, "emp_type"),
                "DateOfJoining": joining_date,
                "Status": status,
            },
        })

    valid_rows = [row for row in preview_rows if not row["errors"]]
    return {
        "summary": {
            "total": len(preview_rows),
            "valid": len(valid_rows),
            "errors": len(preview_rows) - len(valid_rows),
            "creates": sum(row["action"] == "create" for row in valid_rows),
            "updates": sum(row["action"] == "update" for row in valid_rows),
        },
        "rows": preview_rows,
    }


def public_preview(validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": validation["summary"],
        "rows": [{key: value for key, value in row.items() if key != "values"} for row in validation["rows"]],
    }


def import_valid_rows(db: Session, validation: dict[str, Any], update_existing: bool) -> dict[str, Any]:
    created = 0
    updated = 0
    skipped = 0
    for row in validation["rows"]:
        if row["errors"]:
            skipped += 1
            continue
        values = row["values"]
        if row["action"] == "update":
            if not update_existing:
                skipped += 1
                continue
            employee = db.query(EmployeeDB.Employee).filter(
                EmployeeDB.Employee.Emp_id == row["employee_id"]
            ).first()
            if not employee:
                skipped += 1
                continue
            # A blank spreadsheet cell is treated as "leave unchanged" for an
            # update. This prevents a partial bulk-update sheet from wiping DOB,
            # department, designation, or other existing master data.
            for key, value in values.items():
                if value not in (None, ""):
                    setattr(employee, key, value)
            employee.name = " ".join(part for part in (employee.f_name, employee.l_name) if part)
            updated += 1
        else:
            employee_id = row["employee_id"] or generate_next_empid(db)
            create_values = {key: value for key, value in values.items() if value not in (None, "")}
            create_values.setdefault("Status", "Active")
            employee = EmployeeDB.Employee(Emp_id=employee_id, **create_values)
            employee.name = " ".join(part for part in (employee.f_name, employee.l_name) if part)
            db.add(employee)
            db.flush()
            created += 1
    db.commit()
    return {
        "message": f"Employee import completed: {created} created, {updated} updated, {skipped} skipped.",
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "validation_errors": validation["summary"]["errors"],
    }


def build_csv_template() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerow([
        "",
        "Sample",
        "Employee",
        "sample.employee@example.com",
        "9876543210",
        "Female",
        "1995-08-14",
        "",
        "Software Engineer",
        "Full Time",
        "2026-01-15",
        "Active",
    ])
    return output.getvalue()
