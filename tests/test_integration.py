"""Read-only integration checks against the real upstream.

Run with credentials configured (``ccnu login`` or CCNU_STUID / CCNU_PASSWORD):

    CCNU_INTEGRATION=1 python3 -m unittest tests.test_integration -v

These tests never create or cancel a Reservation.
"""

import datetime
import os
import unittest

from ccnu_reservation.client import build_reserver
from ccnu_reservation.config import load_credentials
from ccnu_reservation.errors import NotConfigured
from ccnu_reservation.timeutil import SHANGHAI, Window


def _reserver_or_none():
    try:
        credentials = load_credentials()
    except NotConfigured:
        return None
    return build_reserver(lambda: credentials)


def _target_date(catalog):
    today = datetime.datetime.now(SHANGHAI).date()
    for value in catalog.dates:
        try:
            day = datetime.date.fromisoformat(value)
        except ValueError:
            continue
        if day >= today:
            return day
    return None


@unittest.skipUnless(
    os.environ.get("CCNU_INTEGRATION") == "1",
    "set CCNU_INTEGRATION=1 to run read-only upstream checks",
)
class ReadOnlyIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.reserver = _reserver_or_none()
        if self.reserver is None:
            self.skipTest("no credentials configured")

    def test_login_and_catalog(self):
        catalog = self.reserver.catalog()
        self.assertTrue(catalog.buildings)
        self.assertTrue(catalog.dates)

    def test_spaces_and_free_seats(self):
        catalog = self.reserver.catalog()
        day = _target_date(catalog)
        if day is None:
            self.skipTest("catalog has no future dates")
        window = Window.from_strings(day.isoformat(), "12:30", "13:30")
        building = next(
            (item for item in catalog.buildings if "南湖" in item.name), None
        )
        if building is None or not building.floors:
            self.skipTest("catalog has no 南湖分馆 floors")
        floor = next(
            (item for item in building.floors if "一楼" in item.name),
            building.floors[0],
        )
        spaces = self.reserver.list_spaces(building.id, floor.id, window)
        self.assertTrue(spaces)
        seats = self.reserver.list_free_seats(spaces[0].id, window)
        self.assertIsInstance(seats, list)

    def test_user_info(self):
        info = self.reserver.user_info()
        self.assertIn("username", info)


if __name__ == "__main__":
    unittest.main()
