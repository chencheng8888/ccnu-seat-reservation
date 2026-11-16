import unittest

from ccnu_reservation.errors import InvalidWindow
from ccnu_reservation.reservation import reserve_path, scalar_string
from ccnu_reservation.timeutil import Window


class ReservePathTest(unittest.TestCase):
    def test_builds_upstream_path(self):
        window = Window.from_strings("2026-11-18", "12:30", "13:30")
        self.assertEqual(
            reserve_path("1995338594917990400", window, "capToken"),
            "/static/frontApi/make/freeBook/1995338594917990400/"
            "2026-11-18/750/810?capToken=capToken",
        )

    def test_escapes_seat_and_cap_token(self):
        window = Window.from_strings("2026-11-18", "12:30", "13:30")
        self.assertEqual(
            reserve_path("a b", window, "x&y"),
            "/static/frontApi/make/freeBook/a%20b/2026-11-18/750/810?capToken=x%26y",
        )


class ScalarStringTest(unittest.TestCase):
    def test_handles_upstream_scalar_shapes(self):
        self.assertEqual(scalar_string(None), "")
        self.assertEqual(scalar_string(""), "")
        self.assertEqual(scalar_string(" 42 "), "42")
        self.assertEqual(scalar_string(42), "42")
        self.assertEqual(scalar_string(42.0), "42")


class ValidateWindowTest(unittest.TestCase):
    def test_reserve_validation_matches_upstream_rules(self):
        window = Window.from_strings("2026-11-18", "12:30", "13:30")
        window.validate(30, 120)
        with self.assertRaises(InvalidWindow):
            window.validate(60, 120)


if __name__ == "__main__":
    unittest.main()
