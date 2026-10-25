import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, TrainRun
from app.models.enums import BookingStatus


class BookingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _with_details(self):
        return select(Booking).options(
            selectinload(Booking.passengers),
            selectinload(Booking.run).selectinload(TrainRun.train),
            selectinload(Booking.from_station),
            selectinload(Booking.to_station),
            selectinload(Booking.refunds),
        )

    def get(self, booking_id: uuid.UUID) -> Booking | None:
        return self.session.scalar(self._with_details().where(Booking.id == booking_id))

    def lock(self, booking_id: uuid.UUID) -> Booking:
        stmt = (
            select(Booking)
            .where(Booking.id == booking_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.session.execute(stmt).scalar_one()

    def by_pnr(self, pnr: str) -> Booking | None:
        return self.session.scalar(self._with_details().where(Booking.pnr == pnr))

    def pnr_exists(self, pnr: str) -> bool:
        return self.session.scalar(select(Booking.id).where(Booking.pnr == pnr)) is not None

    def for_user(self, user_id: uuid.UUID) -> list[Booking]:
        stmt = (
            self._with_details()
            .where(Booking.user_id == user_id, Booking.status != BookingStatus.PENDING_PAYMENT)
            .order_by(Booking.departure_at.desc())
        )
        return list(self.session.scalars(stmt))

    def on_run(self, run_id: int, statuses: tuple[BookingStatus, ...]) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.run_id == run_id, Booking.status.in_(statuses))
            .options(selectinload(Booking.passengers))
            .order_by(Booking.created_at)
            .with_for_update(of=Booking)
        )
        return list(self.session.scalars(stmt))

    def expire_pending(self, now: datetime) -> int:
        stmt = (
            update(Booking)
            .where(Booking.status == BookingStatus.PENDING_PAYMENT, Booking.expires_at <= now)
            .values(status=BookingStatus.EXPIRED)
        )
        return self.session.execute(stmt).rowcount or 0
