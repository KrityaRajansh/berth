import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.errors import Conflict, InvalidInput, NotFound
from app.models import Booking, Passenger, TrainRun, User
from app.models.enums import (
    BookingStatus,
    PassengerStatus,
    RefundReason,
    RunStatus,
)
from app.repositories.bookings import BookingRepository
from app.repositories.inventory import InventoryRepository
from app.repositories.runs import RunRepository
from app.schemas.booking import RefundLine, RefundQuote
from app.services.audit import AuditLog
from app.services.inventory import booking_open
from app.services.payment_gateway import PaymentGateway
from app.services.payments import PaymentService
from app.services.refunds import cancellation_refund
from app.services.schedule import stop_departure_at
from app.services.waitlist import WaitlistService

ACTIVE = (PassengerStatus.CNF, PassengerStatus.WL)


class CancellationService:
    def __init__(self, session: Session, clock: Clock, gateway: PaymentGateway) -> None:
        self.session = session
        self.clock = clock
        self.bookings = BookingRepository(session)
        self.runs = RunRepository(session)
        self.inventory = InventoryRepository(session)
        self.payments = PaymentService(session, clock, gateway)
        self.waitlist = WaitlistService(session, clock)
        self.audit = AuditLog(session)

    # Passenger cancellations (FR-CAN-01 to 05)

    def quote(self, booking_id: uuid.UUID, user: User, passenger_ids: list[int]) -> RefundQuote:
        booking = self._owned(booking_id, user)
        now = self.clock.now()
        self._check_cancellable(booking, now)
        lines = [
            RefundLine(
                passenger_id=p.id,
                name=p.name,
                status=str(p.status),
                refund_paise=self._refund(booking, p, now),
            )
            for p in self._select(booking, passenger_ids)
        ]
        return RefundQuote(lines=lines, total_refund_paise=sum(x.refund_paise for x in lines))

    def cancel(self, booking_id: uuid.UUID, user: User, passenger_ids: list[int]) -> Booking:
        snapshot = self._owned(booking_id, user)
        run_class = self.inventory.lock_run_class(snapshot.run_class_id)
        booking = self.bookings.lock(booking_id)
        now = self.clock.now()
        self._check_cancellable(booking, now)
        selected = self._select(booking, passenger_ids)

        released_berth = False
        total_refund = 0
        for passenger in selected:
            refund = self._refund(booking, passenger, now)
            released_berth |= passenger.status == PassengerStatus.CNF
            passenger.status = PassengerStatus.CAN
            passenger.refund_paise = refund
            passenger.cancelled_at = now
            total_refund += refund
        self.session.flush()

        promoted = self.waitlist.promote(run_class) if released_berth else []
        self.payments.refund(booking, total_refund, RefundReason.USER_CANCELLATION)
        if not any(p.status in ACTIVE for p in booking.passengers):
            booking.status = BookingStatus.CANCELLED
        self.audit.record(
            actor_id=user.id,
            event_type="PASSENGERS_CANCELLED",
            entity="booking",
            entity_id=booking.id,
            at=now,
            data={
                "passengers": [p.id for p in selected],
                "refund_paise": total_refund,
                "promoted": [p.id for p in promoted],
            },
        )
        self.session.commit()
        refreshed = self.bookings.get(booking_id)
        assert refreshed is not None
        return refreshed

    # Run-level operations (FR-ADM-05, FR-WL-04)

    def cancel_run(self, run_id: int, admin: User) -> int:
        run = self.runs.get(run_id)
        if run is None:
            raise NotFound("Train run not found.")
        now = self.clock.now()
        if run.status in (RunStatus.CANCELLED, RunStatus.COMPLETED):
            raise Conflict(f"This run is already {run.status}.", code="RUN_NOT_CANCELLABLE")
        if stop_departure_at(run.run_date, run.train.stops[0]) <= now:
            raise Conflict("The train has already departed.", code="RUN_DEPARTED")

        self.inventory.lock_run_classes(run.id)
        run = self.runs.lock(run.id)
        affected = 0
        for booking in self.bookings.on_run(
            run.id, (BookingStatus.BOOKED, BookingStatus.PENDING_PAYMENT)
        ):
            if booking.status == BookingStatus.PENDING_PAYMENT:
                booking.status = BookingStatus.FAILED
                continue
            self._cancel_with_full_refund(
                booking,
                [p for p in booking.passengers if p.status in ACTIVE],
                RefundReason.RUN_CANCELLED,
                now,
            )
            affected += 1
        run.status = RunStatus.CANCELLED
        self.audit.record(
            actor_id=admin.id,
            event_type="RUN_CANCELLED",
            entity="train_run",
            entity_id=run.id,
            at=now,
            data={"bookings": affected},
        )
        self.session.commit()
        return affected

    def prepare_chart(self, run: TrainRun) -> int:
        """Close bookings for a run and cancel remaining waitlisted passengers with full refund."""
        now = self.clock.now()
        self.inventory.lock_run_classes(run.id)
        run = self.runs.lock(run.id)
        if run.status != RunStatus.SCHEDULED:
            self.session.commit()
            return 0

        by_booking: dict[uuid.UUID, list[Passenger]] = defaultdict(list)
        for passenger in self.inventory.waitlisted_on_run(run.id):
            by_booking[passenger.booking_id].append(passenger)
        for booking_id, passengers in by_booking.items():
            booking = self.bookings.lock(booking_id)
            self._cancel_with_full_refund(booking, passengers, RefundReason.CHART_PREPARED, now)

        run.status = RunStatus.CHART_PREPARED
        run.chart_prepared_at = now
        self.audit.record(
            actor_id=None,
            event_type="CHART_PREPARED",
            entity="train_run",
            entity_id=run.id,
            at=now,
            data={"waitlist_cancelled": sum(len(v) for v in by_booking.values())},
        )
        self.session.commit()
        return 1

    # Helpers

    def _owned(self, booking_id: uuid.UUID, user: User) -> Booking:
        booking = self.bookings.get(booking_id)
        if booking is None or booking.user_id != user.id:
            raise NotFound("Booking not found.")
        return booking

    def _check_cancellable(self, booking: Booking, now: datetime) -> None:
        if booking.status != BookingStatus.BOOKED:
            raise Conflict("Only booked tickets can be cancelled.", code="NOT_CANCELLABLE")
        if not booking_open(booking.run, now):
            raise Conflict(
                "Online cancellation has closed for this train.", code="CANCELLATION_CLOSED"
            )

    def _select(self, booking: Booking, passenger_ids: list[int]) -> list[Passenger]:
        active = {p.id: p for p in booking.passengers if p.status in ACTIVE}
        wanted = list(dict.fromkeys(passenger_ids))
        if any(pid not in active for pid in wanted):
            raise InvalidInput(
                "Some selected passengers are not active on this booking.",
                code="INVALID_PASSENGERS",
            )
        return [active[pid] for pid in wanted]

    def _refund(self, booking: Booking, passenger: Passenger, now: datetime) -> int:
        assert passenger.status is not None
        return cancellation_refund(
            status=passenger.status,
            travel_class=booking.travel_class,
            fare=passenger.fare_paise,
            departure_at=booking.departure_at,
            now=now,
        )

    def _cancel_with_full_refund(
        self,
        booking: Booking,
        passengers: list[Passenger],
        reason: RefundReason,
        now: datetime,
    ) -> None:
        total = 0
        for passenger in passengers:
            passenger.status = PassengerStatus.CAN
            passenger.refund_paise = passenger.fare_paise
            passenger.cancelled_at = now
            total += passenger.fare_paise
        self.session.flush()
        self.payments.refund(booking, total, reason)
        if not any(p.status in ACTIVE for p in booking.passengers):
            booking.status = BookingStatus.CANCELLED
