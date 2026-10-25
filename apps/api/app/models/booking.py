import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, SmallInteger, String, column, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    BerthType,
    BookingStatus,
    Gender,
    PassengerStatus,
    PaymentStatus,
    RefundReason,
    TravelClass,
    db_enum,
)
from app.models.network import Station
from app.models.run import TrainRun, TrainRunClass


class Booking(Base):
    __tablename__ = "booking"
    __table_args__ = (Index(None, "user_id", "journey_date"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pnr: Mapped[str | None] = mapped_column(String(10), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("train_run.id"))
    run_class_id: Mapped[int] = mapped_column(ForeignKey("train_run_class.id"))
    travel_class: Mapped[TravelClass] = mapped_column(db_enum(TravelClass))
    from_station_id: Mapped[int] = mapped_column(ForeignKey("station.id"))
    to_station_id: Mapped[int] = mapped_column(ForeignKey("station.id"))
    from_seq: Mapped[int] = mapped_column(SmallInteger)
    to_seq: Mapped[int] = mapped_column(SmallInteger)
    journey_date: Mapped[date]
    departure_at: Mapped[datetime]
    arrival_at: Mapped[datetime]
    distance_km: Mapped[int]
    status: Mapped[BookingStatus] = mapped_column(
        db_enum(BookingStatus), default=BookingStatus.PENDING_PAYMENT
    )
    total_fare_paise: Mapped[int]
    confirm_only: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]

    run: Mapped[TrainRun] = relationship()
    run_class: Mapped[TrainRunClass] = relationship()
    from_station: Mapped[Station] = relationship(foreign_keys=[from_station_id])
    to_station: Mapped[Station] = relationship(foreign_keys=[to_station_id])
    passengers: Mapped[list["Passenger"]] = relationship(
        back_populates="booking", order_by="Passenger.seq_no", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(order_by="Payment.created_at")
    refunds: Mapped[list["Refund"]] = relationship(order_by="Refund.created_at")


class Passenger(Base):
    __tablename__ = "passenger"
    __table_args__ = (
        # The database itself refuses two confirmed passengers on the same berth
        # for overlapping parts of the route (SDD section 4, NFR-03).
        ExcludeConstraint(
            (column("run_class_id"), "="),
            (column("coach_code"), "="),
            (column("berth_no"), "="),
            (func.int4range(column("from_seq"), column("to_seq")), "&&"),
            name="ex_passenger_berth_overlap",
            using="gist",
            where=text("status = 'CNF'"),
        ),
        Index(None, "run_class_id", "status", "wl_seq"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"))
    run_class_id: Mapped[int] = mapped_column(ForeignKey("train_run_class.id"))
    from_seq: Mapped[int] = mapped_column(SmallInteger)
    to_seq: Mapped[int] = mapped_column(SmallInteger)
    seq_no: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column(SmallInteger)
    gender: Mapped[Gender] = mapped_column(db_enum(Gender))
    berth_pref: Mapped[BerthType | None] = mapped_column(db_enum(BerthType))
    # None until the booking is paid for.
    status: Mapped[PassengerStatus | None] = mapped_column(db_enum(PassengerStatus))
    coach_code: Mapped[str | None] = mapped_column(String(4))
    berth_no: Mapped[int | None] = mapped_column(SmallInteger)
    berth_type: Mapped[BerthType | None] = mapped_column(db_enum(BerthType))
    wl_seq: Mapped[int | None]
    booking_status_label: Mapped[str | None] = mapped_column(String(20))
    fare_paise: Mapped[int]
    refund_paise: Mapped[int] = mapped_column(default=0)
    cancelled_at: Mapped[datetime | None]

    booking: Mapped[Booking] = relationship(back_populates="passengers")


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking.id"), index=True)
    amount_paise: Mapped[int]
    method: Mapped[str] = mapped_column(String(10))
    instrument: Mapped[str] = mapped_column(String(40))
    status: Mapped[PaymentStatus] = mapped_column(db_enum(PaymentStatus))
    gateway_ref: Mapped[str | None] = mapped_column(String(40))
    failure_reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime]


class Refund(Base):
    __tablename__ = "refund"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking.id"), index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment.id"))
    amount_paise: Mapped[int]
    reason: Mapped[RefundReason] = mapped_column(db_enum(RefundReason))
    status: Mapped[str] = mapped_column(String(20))
    gateway_ref: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime]
