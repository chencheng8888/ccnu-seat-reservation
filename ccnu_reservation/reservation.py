"""Reservation rules, request paths and response parsing."""

import urllib.parse
from dataclasses import dataclass

DEFAULT_CAP_TOKEN = "capToken"


@dataclass
class Reservation:
    id: str
    seat_id: str
    window: object


def validate_window(window, step, max_duration):
    window.validate(step, max_duration)


def reserve_path(seat_id, window, cap_token=DEFAULT_CAP_TOKEN):
    return "/static/frontApi/make/freeBook/%s/%s/%d/%d?capToken=%s" % (
        urllib.parse.quote(seat_id, safe=""),
        window.date_string,
        window.start_minute,
        window.end_minute,
        urllib.parse.quote(cap_token, safe=""),
    )


def cancel_path(reservation_id):
    return "/static/frontApi/make/cancel/" + urllib.parse.quote(reservation_id, safe="")


def last_make_path():
    return "/static/frontApi/user/lastMake"


def history_path(page_size, page):
    return "/static/frontApi/user/history/%d/%d" % (page_size, page)


def user_info_path():
    return "/static/frontApi/user/getUserInfo"


def scalar_string(value):
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, (int, str)):
        return str(value).strip().strip('"')
    return ""


def parse_reservation_id(data):
    if not isinstance(data, dict):
        return ""
    return scalar_string(data.get("id")) or scalar_string(data.get("makeId"))


def parse_last_make(data):
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]
