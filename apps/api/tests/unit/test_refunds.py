from datetime import UTC, datetime, timedelta

import pytest

from app.models.enums import PassengerStatus, TravelClass
from app.services.refunds import cancellation_refund

DEPARTURE = datetime(2026, 11, 20, 6, 0, tzinfo=UTC)


def refund(status, travel_class, fare, hours_before):
    return cancellation_refund(
        status=status,
        travel_class=travel_class,
        fare=fare,
        departure_at=DEPARTURE,
        now=DEPARTURE - timedelta(hours=hours_before),
    )


@pytest.mark.parametrize(
    ("case", "hours_before", "expected"),
    [
        ("UT-05", 72, 1626_00),
        ("UT-06", 48, 1354_50),
        ("UT-07", 12, 1354_50),
        ("UT-08", 6, 903_00),
    ],
)
def test_ut05_to_ut08_confirmed_refund_slabs(case, hours_before, expected):
    assert refund(PassengerStatus.CNF, TravelClass.AC3, 1806_00, hours_before) == expected


def test_just_over_48_hours_uses_flat_fee():
    assert refund(PassengerStatus.CNF, TravelClass.AC3, 1806_00, 48.01) == 1626_00


def test_ut09_flat_fee_is_the_minimum_deduction():
    assert refund(PassengerStatus.CNF, TravelClass.SL, 200_00, 24) == 80_00


def test_ut10_waitlisted_refund_keeps_clerkage():
    assert refund(PassengerStatus.WL, TravelClass.AC3, 546_00, 24) == 486_00


def test_refund_is_never_negative():
    assert refund(PassengerStatus.WL, TravelClass.SL, 50_00, 24) == 0
