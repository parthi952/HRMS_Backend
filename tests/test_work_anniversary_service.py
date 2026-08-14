import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
import module.DepartmentDB
import module.payrollProvider
import module.PayrollDB
import module.EmplyeeDB as EmployeeDB
import module.FestivalDB as FestivalDB
from Festival.WorkAnniversaryRouter import next_work_anniversary
from Festival.WorkAnniversaryService import (
    has_work_anniversary_on,
    send_today_work_anniversary_wishes,
)


class WorkAnniversaryServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(FestivalDB.WishTemplate(
            name="Anniversary Test Template",
            header_html="<h1>{{festival_name}}</h1>",
            footer_html="<p>TIBOS</p>",
            is_default=True,
        ))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_employee(self, emp_id, joining_date, *, status="Active", email=None, name=None):
        employee = EmployeeDB.Employee(
            Emp_id=emp_id,
            name=name or emp_id,
            email=email or f"{emp_id.lower()}@example.com",
            DateOfJoining=joining_date,
            Status=status,
        )
        self.db.add(employee)
        self.db.commit()
        return employee

    def test_requires_one_completed_year_and_matches_observed_date(self):
        existing = self.add_employee("EMP001", date(2024, 8, 14))
        new_joiner = self.add_employee("EMP002", date(2026, 8, 14))
        self.assertTrue(has_work_anniversary_on(existing, date(2026, 8, 14)))
        self.assertFalse(has_work_anniversary_on(existing, date(2026, 8, 15)))
        self.assertFalse(has_work_anniversary_on(new_joiner, date(2026, 8, 14)))

    def test_next_anniversary_and_leap_day_observation(self):
        self.assertEqual(
            next_work_anniversary(date(2024, 8, 14), date(2026, 8, 14)),
            date(2026, 8, 14),
        )
        self.assertEqual(
            next_work_anniversary(date(2024, 2, 29), date(2026, 1, 1)),
            date(2026, 2, 28),
        )

    async def test_sends_only_eligible_employee_and_merges_years(self):
        target = date(2026, 8, 14)
        self.add_employee("EMP001", date(2023, 8, 14), name="Ann Employee")
        self.add_employee("EMP002", date(2025, 8, 15))
        self.add_employee("EMP003", date(2024, 8, 14), status="Inactive")
        deliveries = []

        async def fake_send(db, subject, body, to_email, cc_list, sender_override):
            deliveries.append((subject, body, to_email))
            return True, None

        settings = FestivalDB.WorkAnniversarySettings(
            id=1,
            subject_template="{{name}} completes {{years}} years",
            message_html="<p>Congratulations {{name}} on {{years}} years.</p>",
        )
        self.db.add(settings)
        self.db.commit()

        result = await send_today_work_anniversary_wishes(
            target_date=target,
            db=self.db,
            send_email_fn=fake_send,
        )

        self.assertEqual(result["eligible"], 1)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(deliveries[0][0], "Ann Employee completes 3 years")
        self.assertIn("Congratulations Ann Employee on 3 years", deliveries[0][1])
        log = self.db.query(FestivalDB.WorkAnniversaryWishLog).one()
        self.assertEqual(log.years_completed, 3)
        self.assertEqual(log.status, "sent")

    async def test_duplicate_run_does_not_send_twice(self):
        target = date(2026, 8, 14)
        self.add_employee("EMP001", date(2024, 8, 14))
        deliveries = []

        async def fake_send(*args):
            deliveries.append(args)
            return True, None

        first = await send_today_work_anniversary_wishes(
            target_date=target, db=self.db, send_email_fn=fake_send
        )
        second = await send_today_work_anniversary_wishes(
            target_date=target, db=self.db, send_email_fn=fake_send
        )

        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["duplicates"], 1)
        self.assertEqual(len(deliveries), 1)


if __name__ == "__main__":
    unittest.main()
