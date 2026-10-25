import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.errors import Conflict, Gone, InvalidInput, NotFound, PaymentDeclined
from app.models import Booking, Passenger, User
from app.models.enums import BookingStatus, PassengerStatus, PaymentStatus
from app.repositories.bookings import BookingRepository
from app.repositories.inventory import InventoryRepository
from app.repositories.runs import RunRepository
from app.schemas.booking import BookingCreate, PaymentRequest
from app.services.allocation import AllocationRejected, plan_allocation
from app.services.audit import AuditLog
from app.services.fares import calculate_fare
from app.services.inventory import BerthAllocator, booking_open
from app.services.payment_gateway import PaymentGateway
from app.services.payments import PaymentService
from app.services.pnr import generate_pnr
from app.services.schedule import (
    PAYMENT_WINDOW,
    journey_date,
    stop_arrival_at,
    stop_departure_at,
)


class BookingService:
    def __init__(self, session: Session, clock: Clock, gateway: PaymentGateway) -> None:
        self.session = session
        self.clock = clock
        self.bookings = BookingRepository(session)
        self.runs = RunRepository(session)
        self.inventory = InventoryRepository(session)
        self.allocator = BerthAllocator(session)
        self.payments = PaymentService(session, clock, gateway)
        self.audit = AuditLog(session)

    def get(self, booking_id: uuid.UUID, user: User) -> Booking:
        booking = self.bookings.get(booking_id)
        if booking is None or booking.user_id != user.id:
            raise NotFound("Booking not found.")
        if (
            booking.status == BookingStatus.PENDING_PAYMENT
            and booking.expires_at <= self.clock.now()
        ):
            booking.status = BookingStatus.EXPIRED
            self.session.commit()
        return booking

    def list_for(self, user: User) -> list[Booking]:
        return self.bookings.for_user(user.id)

    def create(self, user: User, request: BookingCreate) -> Booking:
        run = self.runs.get(request.run_id)
        if run is None:
            raise NotFound("Train run not found.")
        run_class = next((c for c in run.classes if c.travel_class == request.travel_class), None)
        if run_class is None:
            raise InvalidInput(f"This train has no {request.travel_class} class.")
        stops = {stop.station.code: stop for stop in run.train.stops}
        from_stop = stops.get(request.from_code.upper())
        to_stop = stops.get(request.to_code.upper())
        if from_stop is None or to_stop is None or from_stop.seq >= to_stop.seq:
            raise InvalidInput(
                f"Train {run.train.number} does not run from {request.from_code} "
                f"to {request.to_code}.",
                code="INVALID_SEGMENT",
            )

        now = self.clock.now()
        if not booking_open(run, now):
            raise Conflict("Booking is closed for this train.", code="BOOKING_CLOSED")

        distance = to_stop.distance_km - from_stop.distance_km
        fare = calculate_fare(run_class.travel_class, distance)
        booking = Booking(
            user_id=user.id,
            run_id=run.id,
            run_class_id=run_class.id,
            travel_class=run_class.travel_class,
            from_station_id=from_stop.station_id,
            to_station_id=to_stop.station_id,
            from_seq=from_stop.seq,
            to_seq=to_stop.seq,
            journey_date=journey_date(run.run_date, from_stop),
            departure_at=stop_departure_at(run.run_date, from_stop),
            arrival_at=stop_arrival_at(run.run_date, to_stop),
            distance_km=distance,
            status=BookingStatus.PENDING_PAYMENT,
            total_fare_paise=fare.total * len(request.passengers),
            confirm_only=request.confirm_only,
            created_at=now,
            expires_at=now + PAYMENT_WINDOW,
            passengers=[
                Passenger(
                    run_class_id=run_class.id,
                    from_seq=from_stop.seq,
                    to_seq=to_stop.seq,
                    seq_no=i,
                    name=p.name,
                    age=p.age,
                    gender=p.gender,
                    berth_pref=p.berth_pref,
                    fare_paise=fare.total,
                )
                for i, p in enumerate(request.passengers, start=1)
            ],
        )
        self.session.add(booking)
        self.session.flush()
        self.audit.record(
            actor_id=user.id,
            event_type="BOOKING_CREATED",
            entity="booking",
            entity_id=booking.id,
            at=now,
            data={"passengers": len(request.passengers), "amount_paise": booking.total_fare_paise},
        )
        self.session.commit()
        return self.get(booking.id, user)

    def pay(self, booking_id: uuid.UUID, user: User, request: PaymentRequest) -> Booking:
        snapshot = self.get(booking_id, user)
        if snapshot.status == BookingStatus.BOOKED:
            return snapshot

        # Lock order: run class first, then booking (SDD 7.2). Every inventory
        # change follows the same order, so concurrent requests cannot deadlock.
        run_class = self.inventory.lock_run_class(snapshot.run_class_id)
        booking = self.bookings.lock(booking_id)
        now = self.clock.now()

        if booking.status == BookingStatus.BOOKED:
            self.session.commit()
            return self.get(booking_id, user)
        if booking.status == BookingStatus.EXPIRED:
            self.session.rollback()
            raise Gone("The payment window has closed. Please book again.", code="BOOKING_EXPIRED")
        if booking.status != BookingStatus.PENDING_PAYMENT:
            self.session.rollback()
            raise Conflict(
                f"This booking can no longer be paid for ({booking.status}).",
                code="BOOKING_NOT_PAYABLE",
            )
        if booking.expires_at <= now:
            booking.status = BookingStatus.EXPIRED
            self.session.commit()
            raise Gone("The payment window has closed. Please book again.", code="BOOKING_EXPIRED")
        if not booking_open(booking.run, now):
            self._fail(booking, "BOOKING_CLOSED")
            raise Conflict("Booking is closed for this train.", code="BOOKING_CLOSED")

        passengers = list(booking.passengers)
        try:
            plan = plan_allocation(
                self.allocator.free_berths(run_class, booking.from_seq, booking.to_seq),
                [p.berth_pref for p in passengers],
                waitlisted_now=self.inventory.waitlist_count(run_class.id),
                waitlist_limit=run_class.waitlist_limit,
                confirm_only=booking.confirm_only,
            )
        except AllocationRejected as exc:
            self._fail(booking, exc.code)
            raise Conflict(exc.message, code=exc.code) from exc

        # Save the allocation before charging, so the database constraint gets the
        # final say on berths and a passenger is never charged for a clash.
        waitlisted_now = self.inventory.waitlist_count(run_class.id)
        next_wl_seq = self.inventory.last_wl_seq(run_class.id)
        for passenger, berth in zip(passengers, plan.berths, strict=True):
            if berth is not None:
                passenger.status = PassengerStatus.CNF
                passenger.coach_code = berth.coach_code
                passenger.berth_no = berth.berth_no
                passenger.berth_type = berth.berth_type
                passenger.booking_status_label = f"CNF/{berth.label}"
            else:
                next_wl_seq += 1
                waitlisted_now += 1
                passenger.status = PassengerStatus.WL
                passenger.wl_seq = next_wl_seq
                passenger.booking_status_label = f"WL {waitlisted_now}"
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise Conflict(
                "Another booking took these berths. Please try again.", code="BERTH_CONFLICT"
            ) from exc

        payment = self.payments.charge(booking, request.method, request.instrument)
        if payment.status == PaymentStatus.FAILED:
            # Undo the allocation; the booking stays pending so the passenger can retry.
            self.session.rollback()
            self.session.add(payment)
            self.audit.record(
                actor_id=user.id,
                event_type="PAYMENT_FAILED",
                entity="booking",
                entity_id=booking_id,
                at=now,
                data={"reason": payment.failure_reason},
            )
            self.session.commit()
            raise PaymentDeclined(payment.failure_reason or "Payment declined.")

        self.session.add(payment)
        booking.pnr = self._new_pnr()
        booking.status = BookingStatus.BOOKED
        self.audit.record(
            actor_id=user.id,
            event_type="BOOKING_CONFIRMED",
            entity="booking",
            entity_id=booking.id,
            at=now,
            data={
                "pnr": booking.pnr,
                "confirmed": sum(1 for b in plan.berths if b),
                "waitlisted": plan.waitlisted_count,
            },
        )
        self.session.commit()
        return self.get(booking_id, user)

    def _fail(self, booking: Booking, reason: str) -> None:
        booking.status = BookingStatus.FAILED
        self.audit.record(
            actor_id=booking.user_id,
            event_type="BOOKING_FAILED",
            entity="booking",
            entity_id=booking.id,
            at=self.clock.now(),
            data={"reason": reason},
        )
        self.session.commit()

    def _new_pnr(self) -> str:
        for _ in range(5):
            pnr = generate_pnr()
            if not self.bookings.pnr_exists(pnr):
                return pnr
        raise RuntimeError("could not generate a unique PNR")
