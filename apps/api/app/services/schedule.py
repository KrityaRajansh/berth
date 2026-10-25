"""Time-based business rules (BR-01, BR-02, BR-08, BR-09)."""

from datetime import date, datetime, time, timedelta

from app.core.clock import ist
from app.models.network import RouteStop

ADVANCE_RESERVATION_DAYS = 60
CHART_TIME = time(18, 0)
PAYMENT_WINDOW = timedelta(minutes=15)


def chart_cutoff(run_date: date) -> datetime:
    """Charts for a run starting on D are prepared at 18:00 IST on D-1."""
    return ist(run_date - timedelta(days=1), CHART_TIME)


def stop_arrival_at(run_date: date, stop: RouteStop) -> datetime:
    at = stop.arrival or stop.departure
    assert at is not None, "a stop has an arrival or a departure time"
    return ist(run_date + timedelta(days=stop.day_offset), at)


def stop_departure_at(run_date: date, stop: RouteStop) -> datetime:
    at = stop.departure or stop.arrival
    assert at is not None, "a stop has an arrival or a departure time"
    day = run_date + timedelta(days=stop.day_offset)
    # day_offset counts from the arrival; a departure after midnight is a day later.
    if stop.arrival and stop.departure and stop.departure < stop.arrival:
        day += timedelta(days=1)
    return ist(day, at)


def journey_date(run_date: date, stop: RouteStop) -> date:
    """The date a passenger boarding at `stop` travels on (BR-09)."""
    return stop_departure_at(run_date, stop).date()
