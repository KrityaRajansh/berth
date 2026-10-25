from datetime import date
from typing import Literal

from app.models.enums import TravelClass
from app.schemas.common import IstDatetime, Schema, StationRef

AvailabilityStatus = Literal[
    "AVAILABLE", "WAITLIST", "NOT_AVAILABLE", "BOOKING_CLOSED", "CANCELLED"
]


class FareOut(Schema):
    base_paise: int
    reservation_paise: int
    gst_paise: int
    total_paise: int


class ClassAvailability(Schema):
    travel_class: TravelClass
    status: AvailabilityStatus
    # Free berths when AVAILABLE; the waitlist number a new passenger would get when WAITLIST.
    count: int
    fare: FareOut


class SearchResult(Schema):
    run_id: int
    train_number: str
    train_name: str
    from_station: StationRef
    to_station: StationRef
    journey_date: date
    departure_at: IstDatetime
    arrival_at: IstDatetime
    duration_minutes: int
    distance_km: int
    classes: list[ClassAvailability]
