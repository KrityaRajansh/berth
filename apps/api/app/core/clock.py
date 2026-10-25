from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock that only moves when told to. Used by tests."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FixedClock needs a timezone-aware datetime")
        self.at = at

    def now(self) -> datetime:
        return self.at

    def advance(self, **delta: float) -> None:
        self.at += timedelta(**delta)


def get_clock() -> Clock:
    return SystemClock()


def today_ist(clock: Clock) -> date:
    return clock.now().astimezone(IST).date()


def ist(day: date, at: time) -> datetime:
    return datetime.combine(day, at, tzinfo=IST)
