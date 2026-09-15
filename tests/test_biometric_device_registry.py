import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
import module.DepartmentDB
import module.payrollProvider
import module.PayrollDB
import module.EmplyeeDB as EmployeeDB
from EmployeePort.Atteddance.BiometricDevice import _device_allowed, _touch_device, _apply_punch


class DeviceRegistryTests(unittest.TestCase):
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

    def test_any_device_allowed_when_registry_empty(self):
        self.assertTrue(_device_allowed(self.db, "SOME_RANDOM_SN"))

    def test_only_registered_active_devices_allowed_once_registry_used(self):
        self.db.add(EmployeeDB.BiometricDevice(name="HO Entrance", location="Chennai", serial_number="SN123", is_active=True))
        self.db.add(EmployeeDB.BiometricDevice(name="Branch", location="Coimbatore", serial_number="SN456", is_active=False))
        self.db.commit()

        self.assertTrue(_device_allowed(self.db, "SN123"))
        self.assertFalse(_device_allowed(self.db, "SN456"))  # inactive
        self.assertFalse(_device_allowed(self.db, "SN_UNKNOWN"))

    def test_touch_device_updates_last_seen(self):
        device = EmployeeDB.BiometricDevice(name="HO Entrance", serial_number="SN123", is_active=True)
        self.db.add(device)
        self.db.commit()
        self.assertIsNone(device.last_seen)

        _touch_device(self.db, "SN123")
        self.db.commit()
        self.assertIsNotNone(device.last_seen)

    def test_punch_records_source_device_serial(self):
        self.db.add(EmployeeDB.Employee(Emp_id="EMP1", name="Test", device_pin="7", Status="Active"))
        self.db.commit()
        _apply_punch(self.db, "7", datetime(2026, 9, 15, 9, 0), device_serial="SN123")
        self.db.commit()
        record = self.db.query(EmployeeDB.Attendance).filter(EmployeeDB.Attendance.Emp_id == "EMP1").first()
        self.assertEqual(record.device_serial, "SN123")


if __name__ == "__main__":
    unittest.main()
