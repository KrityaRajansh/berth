"""Refund rules for cancellations by the passenger (SRS BR-06). Amounts in paise."""

from datetime import datetime, timedelta

from app.models.enums import PassengerStatus, TravelClass
from app.services.fares import RATES
from app.services.money import percent_of

WAITLIST_CLERKAGE = 60_00


def cancellation_refund(
    *,
    status: PassengerStatus,
    travel_class: TravelClass,
    fare: int,
    departure_at: datetime,
    now: datetime,
) -> int:
    if status == PassengerStatus.WL:
        return max(0, fare - WAITLIST_CLERKAGE)
    if status != PassengerStatus.CNF:
        return 0

    hours_left = (departure_at - now) / timedelta(hours=1)
    flat_fee = RATES[travel_class].cancellation_fee
    if hours_left > 48:
        deduction = flat_fee
    elif hours_left >= 12:
        deduction = max(percent_of(fare, 25), flat_fee)
    else:
        deduction = fare - percent_of(fare, 50)
    return max(0, fare - deduction)
