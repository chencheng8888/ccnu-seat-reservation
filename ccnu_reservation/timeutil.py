"""Reservation Window: a date plus a minute-of-day range (Asia/Shanghai)."""

import datetime
import re

from .errors import InvalidWindow

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None


def _load_shanghai():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Shanghai")
        except Exception:
            pass
    return datetime.timezone(datetime.timedelta(hours=8))


SHANGHAI = _load_shanghai()

_TIME_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})$")


def _parse_minutes(value, allow_24=False):
    match = _TIME_PATTERN.match(value.strip())
    if not match:
        raise InvalidWindow("时间格式应为 HH:MM：%s" % value)
    hour = int(match.group(1))
    minute = int(match.group(2))
    if minute > 59:
        raise InvalidWindow("分钟必须在 00-59 之间：%s" % value)
    if hour == 24 and minute == 0 and allow_24:
        return 24 * 60
    if hour > 23:
        raise InvalidWindow("小时必须在 00-23 之间：%s" % value)
    return hour * 60 + minute


class Window:
    """A date and a minute-of-day range, e.g. 2026-11-18 12:30-13:30."""

    __slots__ = ("date", "start_minute", "end_minute")

    def __init__(self, date, start_minute, end_minute):
        self.date = date
        self.start_minute = start_minute
        self.end_minute = end_minute

    @classmethod
    def from_strings(cls, date_string, start_string, end_string):
        try:
            day = datetime.date.fromisoformat(date_string.strip())
        except ValueError:
            raise InvalidWindow("日期格式应为 YYYY-MM-DD：%s" % date_string)
        start = _parse_minutes(start_string)
        end = _parse_minutes(end_string, allow_24=True)
        if start >= end:
            raise InvalidWindow("开始时间必须早于结束时间")
        return cls(day, start, end)

    def __eq__(self, other):
        if not isinstance(other, Window):
            return NotImplemented
        return (
            self.date == other.date
            and self.start_minute == other.start_minute
            and self.end_minute == other.end_minute
        )

    def __repr__(self):
        return "Window(%s, %d, %d)" % (
            self.date_string,
            self.start_minute,
            self.end_minute,
        )

    @property
    def date_string(self):
        return self.date.isoformat()

    @property
    def duration_minutes(self):
        return self.end_minute - self.start_minute

    def validate(self, step, max_duration):
        """Reject windows the upstream Step or Max Duration rules forbid."""
        if not (0 <= self.start_minute < self.end_minute <= 24 * 60):
            raise InvalidWindow("起止分钟必须在同一天内")
        if step > 0 and (self.start_minute % step or self.end_minute % step):
            raise InvalidWindow("起止时间必须对齐 %d 分钟步长" % step)
        if max_duration > 0 and self.duration_minutes > max_duration:
            raise InvalidWindow("时长不能超过 %d 分钟" % max_duration)
