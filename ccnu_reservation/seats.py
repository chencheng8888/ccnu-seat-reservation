"""Free Seats: Seats free for the entire Reservation Window."""

import urllib.parse
from dataclasses import dataclass


@dataclass(frozen=True)
class FreeSeat:
    id: str
    label: str
    name: str
    space_id: str


def seats_body(window):
    return {
        "beginMinute": window.start_minute,
        "endMinute": window.end_minute,
        "minMinute": 0,
    }


def seats_path(space_id, window):
    return "/static/frontApi/res/freeSeatIdsDuration/%s/%s" % (
        urllib.parse.quote(space_id, safe=""),
        window.date_string,
    )


UNAVAILABLE_STATUSES = {"IN_USE", "AWAY", "BOOKED"}


def parse_free_seats(data, space_id):
    # The upstream returns every seat in the Space, keyed by seat ID, with a
    # status; only free ones may be offered. Older responses omit ``status``
    # and contain free seats only, so a missing status stays included.
    if not isinstance(data, dict):
        return []
    seats = []
    for item in data.values():
        if not isinstance(item, dict):
            continue
        seat_id = item.get("id")
        if not seat_id:
            continue
        status = item.get("status")
        if isinstance(status, str) and status.upper() in UNAVAILABLE_STATUSES:
            continue
        seats.append(
            FreeSeat(
                id=str(seat_id),
                label=item.get("label") or "",
                name=item.get("name") or "",
                space_id=space_id,
            )
        )
    seats.sort(key=lambda seat: (seat.label, seat.id))
    return seats
