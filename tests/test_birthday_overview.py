import unittest
from datetime import date

from Festival.BirthdayRouter import next_birthday


class BirthdayOverviewTests(unittest.TestCase):
    def test_returns_this_year_when_birthday_is_upcoming(self):
        self.assertEqual(next_birthday(date(1995, 8, 14), date(2026, 8, 13)), date(2026, 8, 14))

    def test_returns_next_year_after_birthday(self):
        self.assertEqual(next_birthday(date(1995, 8, 12), date(2026, 8, 13)), date(2027, 8, 12))

    def test_february_29_uses_february_28_in_non_leap_year(self):
        self.assertEqual(next_birthday(date(1996, 2, 29), date(2026, 1, 1)), date(2026, 2, 28))


if __name__ == "__main__":
    unittest.main()
