import unittest

from ccnu_reservation.errors import InvalidWindow
from ccnu_reservation.timeutil import Window


class WindowParsingTest(unittest.TestCase):
    def test_parses_absolute_window(self):
        window = Window.from_strings("2026-11-18", "12:30", "13:30")
        self.assertEqual(window.date_string, "2026-11-18")
        self.assertEqual(window.start_minute, 750)
        self.assertEqual(window.end_minute, 810)
        self.assertEqual(window.duration_minutes, 60)

    def test_accepts_single_digit_hour(self):
        window = Window.from_strings("2026-11-18", "9:05", "10:05")
        self.assertEqual(window.start_minute, 545)

    def test_accepts_midnight_end(self):
        window = Window.from_strings("2026-11-18", "23:00", "24:00")
        self.assertEqual(window.end_minute, 1440)

    def test_rejects_bad_date(self):
        with self.assertRaises(InvalidWindow):
            Window.from_strings("2026/11/18", "12:00", "13:00")

    def test_rejects_bad_time(self):
        for start, end in (("25:00", "26:00"), ("12:60", "13:00"), ("1200", "13:00")):
            with self.assertRaises(InvalidWindow):
                Window.from_strings("2026-11-18", start, end)

    def test_rejects_reversed_or_empty_window(self):
        for start, end in (("13:00", "13:00"), ("14:00", "13:00")):
            with self.assertRaises(InvalidWindow):
                Window.from_strings("2026-11-18", start, end)


class WindowValidationTest(unittest.TestCase):
    def setUp(self):
        self.window = Window.from_strings("2026-11-18", "12:30", "13:30")

    def test_accepts_aligned_window_within_max(self):
        self.window.validate(step=30, max_duration=240)

    def test_rejects_misaligned_start_or_end(self):
        with self.assertRaises(InvalidWindow):
            Window.from_strings("2026-11-18", "12:35", "13:35").validate(30, 240)

    def test_rejects_longer_than_max_duration(self):
        with self.assertRaises(InvalidWindow):
            self.window.validate(30, 30)

    def test_ignores_unset_rules(self):
        self.window.validate(0, 0)


if __name__ == "__main__":
    unittest.main()
