import unittest

from ccnu_reservation.catalog import parse_catalog
from ccnu_reservation.reservation import parse_last_make, parse_reservation_id
from ccnu_reservation.seats import parse_free_seats
from ccnu_reservation.spaces import parse_spaces


class CatalogParseTest(unittest.TestCase):
    def test_parses_buildings_floors_and_dates(self):
        catalog = parse_catalog(
            {
                "buildings": [
                    {
                        "id": "b1",
                        "name": "南湖分馆",
                        "floors": [{"id": "f1", "name": "一楼"}],
                    }
                ],
                "dates": ["2026-11-18"],
            }
        )
        self.assertEqual(catalog.buildings[0].name, "南湖分馆")
        self.assertEqual(catalog.buildings[0].floors[0].building_id, "b1")
        self.assertEqual(catalog.dates, ["2026-11-18"])

    def test_tolerates_null_and_malformed_items(self):
        catalog = parse_catalog({"buildings": None, "dates": None})
        self.assertEqual(catalog.buildings, [])
        self.assertEqual(catalog.dates, [])


class SpacesParseTest(unittest.TestCase):
    def test_parses_page_list_with_id_fallbacks(self):
        spaces = parse_spaces(
            {
                "pageList": [
                    {
                        "id": "s1",
                        "name": "中庭",
                        "seatTotal": 40,
                        "seatFree": 12,
                    }
                ]
            },
            "b1",
            "f1",
        )
        self.assertEqual(spaces[0].building_id, "b1")
        self.assertEqual(spaces[0].floor_id, "f1")
        self.assertEqual(spaces[0].seat_total, 40)
        self.assertEqual(spaces[0].seat_free, 12)


class FreeSeatsParseTest(unittest.TestCase):
    def test_parses_map_and_sorts_by_label(self):
        seats = parse_free_seats(
            {
                "2": {"id": "2", "label": "B02", "name": "B02", "status": 1},
                "1": {"id": "1", "label": "A01", "name": "A01", "status": 1},
            },
            "s1",
        )
        self.assertEqual([seat.id for seat in seats], ["1", "2"])
        self.assertEqual(seats[0].space_id, "s1")

    def test_skips_seats_that_are_not_free(self):
        seats = parse_free_seats(
            {
                "1": {"id": "1", "label": "A01", "status": "FREE"},
                "2": {"id": "2", "label": "A02", "status": "IN_USE"},
                "3": {"id": "3", "label": "A03", "status": "AWAY"},
                "4": {"id": "4", "label": "A04", "status": "BOOKED"},
                "5": {"id": "5", "label": "A05"},
            },
            "s1",
        )
        self.assertEqual([seat.id for seat in seats], ["1", "5"])

    def test_treats_empty_shapes_as_no_seats(self):
        for data in (None, "", [], {}):
            self.assertEqual(parse_free_seats(data, "s1"), [])


class ReservationParseTest(unittest.TestCase):
    def test_id_falls_back_to_make_id(self):
        self.assertEqual(parse_reservation_id({"id": " 9 "}), "9")
        self.assertEqual(parse_reservation_id({"makeId": 10}), "10")
        self.assertEqual(parse_reservation_id({}), "")

    def test_last_make_requires_a_list(self):
        self.assertEqual(parse_last_make(None), [])
        self.assertEqual(parse_last_make([{"id": "1"}, "bad"]), [{"id": "1"}])


if __name__ == "__main__":
    unittest.main()
