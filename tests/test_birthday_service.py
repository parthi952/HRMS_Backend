import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
import module.DepartmentDB  # Registers Employee foreign-key target.
import module.payrollProvider  # Registers Payroll foreign-key target.
import module.PayrollDB  # Registers the Employee.payroll relationship.
import module.EmplyeeDB as EmployeeDB
import module.FestivalDB as FestivalDB
from Festival.BirthdayService import (
    has_birthday_on,
    is_active_employee,
    send_today_birthday_wishes,
)


class BirthdayServiceTests(unittest.IsolatedAsyncioTestCase):
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
            FestivalDB.WishTemplate(
                name="Birthday Test Template",
                header_html="<h1>{{festival_name}}</h1>",
                footer_html="<p>TIBOS</p>",
                is_default=True,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_employee(
        self,
        emp_id,
        dob,
        *,
        email=None,
        name=None,
        status="Active",
    ):
        employee = EmployeeDB.Employee(
            Emp_id=emp_id,
            name=name or emp_id,
            email=email or f"{emp_id.lower()}@example.com",
            dob=dob,
            Status=status,
        )
        self.db.add(employee)
        self.db.commit()
        return employee

    def test_date_and_active_employee_helpers(self):
        employee = self.add_employee("EMP001", date(1992, 8, 12))
        self.assertTrue(has_birthday_on(employee, date(2026, 8, 12)))
        self.assertFalse(has_birthday_on(employee, date(2026, 8, 13)))
        self.assertTrue(is_active_employee(employee))

        employee.Status = "Terminated"
        self.assertFalse(is_active_employee(employee))

    async def test_sends_only_to_active_employees_born_today(self):
        target = date(2026, 8, 12)
        self.add_employee(
            "EMP001",
            date(1992, 8, 12),
            email="birthday@example.com",
            name="Birthday Employee",
        )
        self.add_employee("EMP002", date(1990, 8, 13), email="tomorrow@example.com")
        self.add_employee(
            "EMP003",
            date(1988, 8, 12),
            email="inactive@example.com",
            status="Inactive",
        )

        deliveries = []

        async def fake_send(db, subject, html, to_email, cc_list, sender_override):
            deliveries.append((subject, html, to_email))
            return True, None

        result = await send_today_birthday_wishes(
            target_date=target,
            db=self.db,
            send_email_fn=fake_send,
        )

        self.assertEqual(result["eligible"], 1)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual([item[2] for item in deliveries], ["birthday@example.com"])
        self.assertEqual(deliveries[0][0], "Happy Birthday, Birthday Employee!")
        self.assertNotIn("Advance", deliveries[0][0])
        self.assertNotIn("tomorrow", deliveries[0][1].lower())

        log = self.db.query(FestivalDB.BirthdayWishLog).one()
        self.assertEqual(log.status, "sent")
        self.assertEqual(log.birthday_date, target)
        self.assertIsNotNone(log.sent_at)

    async def test_duplicate_run_does_not_send_twice(self):
        target = date(2026, 8, 12)
        self.add_employee("EMP001", date(1992, 8, 12))
        deliveries = []

        async def fake_send(*args):
            deliveries.append(args)
            return True, None

        first = await send_today_birthday_wishes(
            target_date=target,
            db=self.db,
            send_email_fn=fake_send,
        )
        second = await send_today_birthday_wishes(
            target_date=target,
            db=self.db,
            send_email_fn=fake_send,
        )

        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertEqual(second["duplicates"], 1)
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(self.db.query(FestivalDB.BirthdayWishLog).count(), 1)

    async def test_delivery_failure_is_recorded(self):
        target = date(2026, 8, 12)
        self.add_employee("EMP001", date(1992, 8, 12))

        async def failed_send(*args):
            return False, "Provider unavailable"

        result = await send_today_birthday_wishes(
            target_date=target,
            db=self.db,
            send_email_fn=failed_send,
        )

        self.assertEqual(result["failed"], 1)
        log = self.db.query(FestivalDB.BirthdayWishLog).one()
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.error, "Provider unavailable")
        self.assertIsNone(log.sent_at)


if __name__ == "__main__":
    unittest.main()
