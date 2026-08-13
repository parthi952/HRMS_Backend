import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
import module.DepartmentDB as DepartmentDB
import module.payrollProvider  # Registers Payroll relationships.
import module.PayrollDB
import module.EmplyeeDB as EmployeeDB
from EmployeePort.EmployeeBulkService import (
    import_valid_rows,
    public_preview,
    read_import_rows,
    validate_import_rows,
)


class EmployeeBulkServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(DepartmentDB.Department(Dep_id="DEP-001", Dep_name="Engineering"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_preview_and_import_valid_csv(self):
        content = (
            "Employee ID,First Name,Last Name,Email,Date of Birth,Department,Status\n"
            ",Boomika,K,boomika@example.com,1995-08-14,Engineering,Active\n"
        ).encode()
        source = read_import_rows("employees.csv", content)
        validation = validate_import_rows(self.db, source)
        preview = public_preview(validation)

        self.assertEqual(preview["summary"]["valid"], 1)
        self.assertEqual(preview["summary"]["creates"], 1)
        self.assertNotIn("values", preview["rows"][0])

        result = import_valid_rows(self.db, validation, update_existing=False)
        self.assertEqual(result["created"], 1)
        employee = self.db.query(EmployeeDB.Employee).one()
        self.assertEqual(employee.name, "Boomika K")
        self.assertEqual(employee.dob.isoformat(), "1995-08-14")

    def test_invalid_department_and_duplicate_email_are_rejected(self):
        content = (
            "First Name,Last Name,Email,Department\n"
            "One,Employee,same@example.com,Unknown\n"
            "Two,Employee,same@example.com,Engineering\n"
        ).encode()
        validation = validate_import_rows(self.db, read_import_rows("employees.csv", content))

        self.assertEqual(validation["summary"]["valid"], 0)
        self.assertEqual(validation["summary"]["errors"], 2)
        self.assertTrue(any("does not exist" in error for error in validation["rows"][0]["errors"]))
        self.assertTrue(any("more than once" in error for error in validation["rows"][1]["errors"]))

    def test_existing_employee_requires_update_confirmation(self):
        self.db.add(EmployeeDB.Employee(
            Emp_id="EMP-0001",
            f_name="Old",
            l_name="Name",
            name="Old Name",
            email="old@example.com",
            Department="Engineering",
            Status="Active",
        ))
        self.db.commit()
        content = (
            "Employee ID,First Name,Last Name,Email,Department,Status\n"
            "EMP-0001,Updated,Name,old@example.com,Engineering,Active\n"
        ).encode()
        validation = validate_import_rows(self.db, read_import_rows("employees.csv", content))

        skipped = import_valid_rows(self.db, validation, update_existing=False)
        self.assertEqual(skipped["updated"], 0)
        self.assertEqual(skipped["skipped"], 1)

        applied = import_valid_rows(self.db, validation, update_existing=True)
        self.assertEqual(applied["updated"], 1)
        employee = self.db.get(EmployeeDB.Employee, "EMP-0001")
        self.assertEqual(employee.name, "Updated Name")

    def test_blank_update_cells_do_not_erase_existing_optional_data(self):
        self.db.add(EmployeeDB.Employee(
            Emp_id="EMP-0002",
            f_name="Existing",
            l_name="Employee",
            name="Existing Employee",
            email="existing@example.com",
            phone="9876543210",
            dob=date(1995, 8, 14),
            Department="Engineering",
            designation="Engineer",
            Status="Active",
        ))
        self.db.commit()
        content = (
            "Employee ID,First Name,Last Name,Email,Phone,Date of Birth,Department,Designation,Status\n"
            "EMP-0002,Updated,Employee,existing@example.com,,,,,\n"
        ).encode()

        validation = validate_import_rows(self.db, read_import_rows("employees.csv", content))
        import_valid_rows(self.db, validation, update_existing=True)

        employee = self.db.get(EmployeeDB.Employee, "EMP-0002")
        self.assertEqual(employee.name, "Updated Employee")
        self.assertEqual(employee.phone, "9876543210")
        self.assertEqual(employee.dob.isoformat(), "1995-08-14")
        self.assertEqual(employee.Department, "Engineering")
        self.assertEqual(employee.designation, "Engineer")
        self.assertEqual(employee.Status, "Active")

    def test_rejects_unsupported_and_empty_files(self):
        with self.assertRaisesRegex(ValueError, "Only .csv and .xlsx"):
            read_import_rows("employees.xls", b"data")
        with self.assertRaisesRegex(ValueError, "empty"):
            read_import_rows("employees.csv", b"")


if __name__ == "__main__":
    unittest.main()
