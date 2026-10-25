from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, Passenger, TrainRunClass
from app.models.enums import PassengerStatus


class InventoryRepository:
    """Queries over berths and waitlists for one train run and class."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_run_class(self, run_class_id: int) -> TrainRunClass:
        stmt = (
            select(TrainRunClass)
            .where(TrainRunClass.id == run_class_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.session.execute(stmt).scalar_one()

    def lock_run_classes(self, run_id: int) -> list[TrainRunClass]:
        stmt = (
            select(TrainRunClass)
            .where(TrainRunClass.run_id == run_id)
            .order_by(TrainRunClass.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return list(self.session.scalars(stmt))

    def occupied_berths(
        self, run_class_id: int, from_seq: int, to_seq: int
    ) -> set[tuple[str, int]]:
        stmt = select(Passenger.coach_code, Passenger.berth_no).where(
            Passenger.run_class_id == run_class_id,
            Passenger.status == PassengerStatus.CNF,
            Passenger.from_seq < to_seq,
            Passenger.to_seq > from_seq,
        )
        return {(coach, berth) for coach, berth in self.session.execute(stmt)}

    def waitlist_count(self, run_class_id: int) -> int:
        stmt = select(func.count()).where(
            Passenger.run_class_id == run_class_id,
            Passenger.status == PassengerStatus.WL,
        )
        return self.session.scalar(stmt) or 0

    def confirmed_count(self, run_class_id: int) -> int:
        stmt = select(func.count()).where(
            Passenger.run_class_id == run_class_id,
            Passenger.status == PassengerStatus.CNF,
        )
        return self.session.scalar(stmt) or 0

    def waitlisted(self, run_class_id: int) -> list[Passenger]:
        stmt = (
            select(Passenger)
            .where(
                Passenger.run_class_id == run_class_id,
                Passenger.status == PassengerStatus.WL,
            )
            .order_by(Passenger.wl_seq)
        )
        return list(self.session.scalars(stmt))

    def waitlisted_on_run(self, run_id: int) -> list[Passenger]:
        stmt = (
            select(Passenger)
            .join(Booking, Booking.id == Passenger.booking_id)
            .where(Booking.run_id == run_id, Passenger.status == PassengerStatus.WL)
            .order_by(Passenger.wl_seq)
        )
        return list(self.session.scalars(stmt))

    def last_wl_seq(self, run_class_id: int) -> int:
        stmt = select(func.max(Passenger.wl_seq)).where(Passenger.run_class_id == run_class_id)
        return self.session.scalar(stmt) or 0

    def waitlist_position(self, passenger: Passenger) -> int:
        stmt = select(func.count()).where(
            Passenger.run_class_id == passenger.run_class_id,
            Passenger.status == PassengerStatus.WL,
            Passenger.wl_seq <= passenger.wl_seq,
        )
        return self.session.scalar(stmt) or 0
