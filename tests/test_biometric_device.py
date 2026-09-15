import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
import module.DepartmentDB  # Registers Employee foreign-key target.
import module.payrollProvider  # Registers Payroll foreign-key target.
import module.PayrollDB  # Registers the Employee.payroll relationship.
import module.EmplyeeDB as EmployeeDB
from EmployeePort.Atteddance.BiometricDevice import _apply_punch


class BiometricDeviceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(
            EmployeeDB.Employee(
                Emp_id="EMP1",
                name="Test Employee",
                device_pin="7",
                Status="Active",
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_first_punch_of_day_is_check_in(self):
        ok = _apply_punch(self.db, "7", datetime(2026, 9, 15, 9, 3))
        self.db.commit()
        self.assertTrue(ok)
        record = self.db.query(EmployeeDB.Attendance).filter(
            EmployeeDB.Attendance.Emp_id == "EMP1"
        ).first()
        self.assertEqual(record.status, "Present")
        self.assertIsNotNone(record.check_in)
        self.assertIsNone(record.check_out)

    def test_second_punch_same_day_is_check_out(self):
        _apply_punch(self.db, "7", datetime(2026, 9, 15, 9, 3))
        _apply_punch(self.db, "7", datetime(2026, 9, 15, 18, 30))
        self.db.commit()
        record = self.db.query(EmployeeDB.Attendance).filter(
            EmployeeDB.Attendance.Emp_id == "EMP1"
        ).first()
        self.assertIsNotNone(record.check_in)
        self.assertIsNotNone(record.check_out)

    def test_unmapped_device_pin_is_ignored(self):
        ok = _apply_punch(self.db, "999", datetime(2026, 9, 15, 9, 3))
        self.db.commit()
        self.assertFalse(ok)
        self.assertEqual(self.db.query(EmployeeDB.Attendance).count(), 0)


if __name__ == "__main__":
    unittest.main()
