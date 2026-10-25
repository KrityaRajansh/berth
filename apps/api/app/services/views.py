"""Turn booking models into API responses, including live waitlist positions."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Booking, Passenger
from app.models.enums import BookingStatus, PassengerStatus, RunStatus
from app.repositories.inventory import InventoryRepository
from app.schemas.booking import (
    BookingOut,
    BookingSummary,
    PassengerOut,
    PnrPassenger,
    PnrStatusOut,
)
from app.schemas.common import StationRef
from app.services.inventory import booking_open
from app.services.pnr import mask_name

ACTIVE = (PassengerStatus.CNF, PassengerStatus.WL)


class BookingPresenter:
    def __init__(self, session: Session) -> None:
        self.inventory = InventoryRepository(session)

    def current_status(self, passenger: Passenger) -> str:
        match passenger.status:
            case PassengerStatus.CNF:
                return f"CNF/{passenger.coach_code}/{passenger.berth_no}/{passenger.berth_type}"
            case PassengerStatus.WL:
                return f"WL {self.inventory.waitlist_position(passenger)}"
            case PassengerStatus.CAN:
                return "CAN"
            case _:
                return "PENDING"

    def can_cancel(self, booking: Booking, now: datetime) -> bool:
        return (
            booking.status == BookingStatus.BOOKED
            and booking_open(booking.run, now)
            and any(p.status in ACTIVE for p in booking.passengers)
        )

    def detail(self, booking: Booking, now: datetime) -> BookingOut:
        return BookingOut(
            id=booking.id,
            pnr=booking.pnr,
            status=booking.status,
            train_number=booking.run.train.number,
            train_name=booking.run.train.name,
            travel_class=booking.travel_class,
            from_station=StationRef.model_validate(booking.from_station),
            to_station=StationRef.model_validate(booking.to_station),
            journey_date=booking.journey_date,
            departure_at=booking.departure_at,
            arrival_at=booking.arrival_at,
            distance_km=booking.distance_km,
            total_fare_paise=booking.total_fare_paise,
            refunded_paise=sum(r.amount_paise for r in booking.refunds),
            confirm_only=booking.confirm_only,
            created_at=booking.created_at,
            expires_at=booking.expires_at,
            chart_prepared=booking.run.status != RunStatus.SCHEDULED,
            can_cancel=self.can_cancel(booking, now),
            passengers=[
                PassengerOut(
                    id=p.id,
                    seq_no=p.seq_no,
                    name=p.name,
                    age=p.age,
                    gender=p.gender,
                    berth_pref=p.berth_pref,
                    booking_status=p.booking_status_label,
                    current_status=self.current_status(p),
                    fare_paise=p.fare_paise,
                    refund_paise=p.refund_paise,
                )
                for p in booking.passengers
            ],
        )

    def summary(self, booking: Booking) -> BookingSummary:
        return BookingSummary(
            id=booking.id,
            pnr=booking.pnr,
            status=booking.status,
            train_number=booking.run.train.number,
            train_name=booking.run.train.name,
            travel_class=booking.travel_class,
            from_station=StationRef.model_validate(booking.from_station),
            to_station=StationRef.model_validate(booking.to_station),
            journey_date=booking.journey_date,
            departure_at=booking.departure_at,
            passenger_count=len(booking.passengers),
            total_fare_paise=booking.total_fare_paise,
        )

    def pnr_status(self, booking: Booking) -> PnrStatusOut:
        assert booking.pnr is not None
        return PnrStatusOut(
            pnr=booking.pnr,
            train_number=booking.run.train.number,
            train_name=booking.run.train.name,
            travel_class=booking.travel_class,
            from_station=StationRef.model_validate(booking.from_station),
            to_station=StationRef.model_validate(booking.to_station),
            journey_date=booking.journey_date,
            departure_at=booking.departure_at,
            arrival_at=booking.arrival_at,
            booking_status=booking.status,
            chart_prepared=booking.run.status != RunStatus.SCHEDULED,
            passengers=[
                PnrPassenger(
                    seq_no=p.seq_no,
                    name=mask_name(p.name),
                    booking_status=p.booking_status_label,
                    current_status=self.current_status(p),
                )
                for p in booking.passengers
            ],
        )
