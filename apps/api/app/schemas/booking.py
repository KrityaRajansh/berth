import re
import uuid
from datetime import date
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.models.enums import BerthType, BookingStatus, Gender, TravelClass
from app.schemas.common import IstDatetime, Schema, StationRef

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .']*[A-Za-z.]$")


class PassengerIn(Schema):
    name: str = Field(min_length=2, max_length=50)
    age: int = Field(ge=1, le=120)
    gender: Gender
    berth_pref: BerthType | None = None

    @field_validator("name")
    @classmethod
    def letters_only(cls, name: str) -> str:
        if not NAME_PATTERN.match(name):
            raise ValueError("Name may contain only letters, spaces, dots and apostrophes.")
        return re.sub(r"\s+", " ", name)


class BookingCreate(Schema):
    run_id: int
    travel_class: TravelClass
    from_code: str
    to_code: str
    passengers: list[PassengerIn] = Field(min_length=1, max_length=6)
    confirm_only: bool = False


class PaymentRequest(Schema):
    method: Literal["card", "upi"]
    card_number: str | None = None
    upi_id: str | None = None

    @model_validator(mode="after")
    def instrument_matches_method(self) -> "PaymentRequest":
        if self.method == "card":
            digits = (self.card_number or "").replace(" ", "")
            if not re.fullmatch(r"\d{16}", digits):
                raise ValueError("Enter a 16-digit card number.")
        elif not re.fullmatch(r"[\w.\-]{2,64}@[A-Za-z]{2,32}", self.upi_id or ""):
            raise ValueError("Enter a UPI ID such as name@bank.")
        return self

    @property
    def instrument(self) -> str:
        return self.card_number if self.method == "card" else self.upi_id  # type: ignore[return-value]


class PassengerOut(Schema):
    id: int
    seq_no: int
    name: str
    age: int
    gender: Gender
    berth_pref: BerthType | None
    booking_status: str | None
    current_status: str
    fare_paise: int
    refund_paise: int


class BookingOut(Schema):
    id: uuid.UUID
    pnr: str | None
    status: BookingStatus
    train_number: str
    train_name: str
    travel_class: TravelClass
    from_station: StationRef
    to_station: StationRef
    journey_date: date
    departure_at: IstDatetime
    arrival_at: IstDatetime
    distance_km: int
    total_fare_paise: int
    refunded_paise: int
    confirm_only: bool
    created_at: IstDatetime
    expires_at: IstDatetime
    chart_prepared: bool
    can_cancel: bool
    passengers: list[PassengerOut]


class BookingSummary(Schema):
    id: uuid.UUID
    pnr: str | None
    status: BookingStatus
    train_number: str
    train_name: str
    travel_class: TravelClass
    from_station: StationRef
    to_station: StationRef
    journey_date: date
    departure_at: IstDatetime
    passenger_count: int
    total_fare_paise: int


class CancellationRequest(Schema):
    passenger_ids: list[int] = Field(min_length=1, max_length=6)


class RefundLine(Schema):
    passenger_id: int
    name: str
    status: str
    refund_paise: int


class RefundQuote(Schema):
    lines: list[RefundLine]
    total_refund_paise: int


class PnrPassenger(Schema):
    seq_no: int
    name: str
    booking_status: str | None
    current_status: str


class PnrStatusOut(Schema):
    pnr: str
    train_number: str
    train_name: str
    travel_class: TravelClass
    from_station: StationRef
    to_station: StationRef
    journey_date: date
    departure_at: IstDatetime
    arrival_at: IstDatetime
    booking_status: BookingStatus
    chart_prepared: bool
    passengers: list[PnrPassenger]
