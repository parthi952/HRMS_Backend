import unittest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
import module.DepartmentDB  # Registers Employee foreign-key target.
import module.payrollProvider  # Registers Payroll foreign-key target.
import module.PayrollDB  # Registers the Employee.payroll relationship.
import module.EmplyeeDB as EmployeeDB
from Caluclation.AttendanceHours import (
    classify_day,
    get_attendance_settings,
    hours_worked,
    apply_day_type,
    is_weekly_off,
    is_on_approved_leave,
)


class AttendanceHoursTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_hours_worked_basic(self):
        self.assertEqual(hours_worked("09:00 AM", "05:30 PM"), 8.5)

    def test_hours_worked_missing_punch(self):
        self.assertIsNone(hours_worked("09:00 AM", None))

    def test_classify_full_day(self):
        settings = get_attendance_settings(self.db)
        self.assertEqual(classify_day("09:00 AM", "05:30 PM", settings), "Full Day")

    def test_classify_half_day(self):
        settings = get_attendance_settings(self.db)
        self.assertEqual(classify_day("09:00 AM", "01:30 PM", settings), "Half Day")

    def test_classify_absent_short_hours(self):
        settings = get_attendance_settings(self.db)
        self.assertEqual(classify_day("09:00 AM", "10:00 AM", settings), "Absent")

    def test_classify_pending_no_checkout(self):
        settings = get_attendance_settings(self.db)
        self.assertEqual(classify_day("09:00 AM", None, settings), "Pending")

    def test_classify_absent_no_checkin(self):
        settings = get_attendance_settings(self.db)
        self.assertEqual(classify_day(None, None, settings), "Absent")

    def test_custom_thresholds_respected(self):
        settings = get_attendance_settings(self.db)
        settings.full_day_hours = 9
        settings.half_day_hours = 5
        self.db.commit()
        # 8 hours no longer qualifies as Full Day once the threshold is raised to 9.
        self.assertEqual(classify_day("09:00 AM", "05:00 PM", settings), "Half Day")

    def test_sunday_is_week_off_by_default(self):
        settings = get_attendance_settings(self.db)
        sunday = date(2026, 9, 13)  # a Sunday
        self.assertTrue(is_weekly_off(sunday, settings))
        self.assertEqual(classify_day("09:30 AM", None, settings, day=sunday), "Week Off")

    def test_saturday_is_a_working_day_by_default(self):
        settings = get_attendance_settings(self.db)
        saturday = date(2026, 9, 12)
        self.assertFalse(is_weekly_off(saturday, settings))
        self.assertEqual(classify_day(None, None, settings, day=saturday), "Absent")

    def test_classify_day_leave_overrides_absent(self):
        settings = get_attendance_settings(self.db)
        self.assertEqual(classify_day(None, None, settings, on_leave=True), "Leave")

    def test_is_on_approved_leave_true_within_range(self):
        self.db.add(EmployeeDB.Employee(Emp_id="EMP3", name="Leaver", Status="Active"))
        self.db.add(EmployeeDB.LeaveHistoryDB(
            Emp_id="EMP3", employee_name="Leaver", Duration="2026-09-10 to 2026-09-12",
            from_date="2026-09-10", to_date="2026-09-12", Days=3, applayDate="2026-09-01",
            leave_type="Casual", status="Approved",
        ))
        self.db.commit()
        self.assertTrue(is_on_approved_leave(self.db, "EMP3", date(2026, 9, 11)))
        self.assertFalse(is_on_approved_leave(self.db, "EMP3", date(2026, 9, 13)))

    def test_is_on_approved_leave_false_when_pending(self):
        self.db.add(EmployeeDB.Employee(Emp_id="EMP4", name="Pending Leaver", Status="Active"))
        self.db.add(EmployeeDB.LeaveHistoryDB(
            Emp_id="EMP4", employee_name="Pending Leaver", Duration="2026-09-10 to 2026-09-12",
            from_date="2026-09-10", to_date="2026-09-12", Days=3, applayDate="2026-09-01",
            leave_type="Casual", status="Pending",
        ))
        self.db.commit()
        self.assertFalse(is_on_approved_leave(self.db, "EMP4", date(2026, 9, 11)))

    def test_apply_day_type_marks_approved_leave_day(self):
        self.db.add(EmployeeDB.Employee(Emp_id="EMP5", name="OnLeave", Status="Active"))
        self.db.add(EmployeeDB.LeaveHistoryDB(
            Emp_id="EMP5", employee_name="OnLeave", Duration="2026-09-16 to 2026-09-16",
            from_date="2026-09-16", to_date="2026-09-16", Days=1, applayDate="2026-09-01",
            leave_type="Sick", status="Approved",
        ))
        record = EmployeeDB.Attendance(
            Emp_id="EMP5", employee_name="OnLeave", date=date(2026, 9, 16),
            status="Pending", check_in=None, check_out=None,
        )
        self.db.add(record)
        self.db.commit()
        apply_day_type(self.db, record)
        self.db.commit()
        self.assertEqual(record.day_type, "Leave")

    def test_shift_overrides_global_thresholds(self):
        settings = get_attendance_settings(self.db)  # global: full 8.5, half 4
        shift = EmployeeDB.Shift(name="Early Shift", start_time="09:00 AM", end_time="06:00 PM", full_day_hours=9, half_day_hours=5)
        # 8.5 hours would be Full Day globally, but Half Day under a 9h shift.
        self.assertEqual(classify_day("09:00 AM", "05:30 PM", settings, shift=shift), "Half Day")
        self.assertEqual(classify_day("09:00 AM", "06:00 PM", settings, shift=shift), "Full Day")

    def test_apply_day_type_uses_employees_assigned_shift(self):
        shift = EmployeeDB.Shift(name="Early Shift", start_time="09:00 AM", end_time="06:00 PM", full_day_hours=9, half_day_hours=5)
        self.db.add(shift)
        self.db.commit()
        self.db.add(EmployeeDB.Employee(Emp_id="EMP2", name="Shifted", Status="Active", shift_id=shift.id))
        record = EmployeeDB.Attendance(
            Emp_id="EMP2", employee_name="Shifted", date=date(2026, 9, 15),
            status="Present", check_in="09:00 AM", check_out="05:30 PM",  # 8.5h
        )
        self.db.add(record)
        self.db.commit()
        apply_day_type(self.db, record)
        self.db.commit()
        self.assertEqual(record.day_type, "Half Day")  # would be Full Day without the shift override

    def test_apply_day_type_marks_week_off_record(self):
        self.db.add(EmployeeDB.Employee(Emp_id="EMP1", name="Test", Status="Active"))
        record = EmployeeDB.Attendance(
            Emp_id="EMP1", employee_name="Test", date=date(2026, 9, 13),  # Sunday
            status="Pending", check_in=None, check_out=None,
        )
        self.db.add(record)
        self.db.commit()
        apply_day_type(self.db, record)
        self.db.commit()
        self.assertEqual(record.day_type, "Week Off")

    def test_apply_day_type_updates_record(self):
        self.db.add(EmployeeDB.Employee(Emp_id="EMP1", name="Test", Status="Active"))
        record = EmployeeDB.Attendance(
            Emp_id="EMP1", employee_name="Test", date=date(2026, 9, 15),
            status="Present", check_in="09:00 AM", check_out="05:30 PM",
        )
        self.db.add(record)
        self.db.commit()
        apply_day_type(self.db, record)
        self.db.commit()
        self.assertEqual(record.day_type, "Full Day")


class RegularizationApprovalTests(unittest.TestCase):
    """Covers the same override logic used by PUT /attendance/regularize/{id}."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(EmployeeDB.Employee(Emp_id="EMP1", name="Test", Status="Active"))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_approval_forces_full_day_even_under_threshold(self):
        record = EmployeeDB.Attendance(
            Emp_id="EMP1", employee_name="Test", date=date(2026, 9, 15),
            status="Pending", check_in="09:00 AM", check_out="11:00 AM",
        )
        self.db.add(record)
        self.db.commit()

        # Simulates what decide_regularization() does on Approved.
        apply_day_type(self.db, record)
        self.assertEqual(record.day_type, "Absent")  # only 2 hours worked
        record.day_type = "Full Day"
        record.status = "Present"
        self.db.commit()

        self.assertEqual(record.day_type, "Full Day")
        self.assertEqual(record.status, "Present")


if __name__ == "__main__":
    unittest.main()
