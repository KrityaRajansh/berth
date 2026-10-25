from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import TrainRun, TrainRunClass
from app.models.enums import RunStatus
from app.repositories.inventory import InventoryRepository
from app.services.layout import Berth, coach_berths
from app.services.schedule import chart_cutoff


@dataclass(frozen=True)
class Availability:
    status: str
    count: int


def booking_open(run: TrainRun, now: datetime) -> bool:
    return run.status == RunStatus.SCHEDULED and now < chart_cutoff(run.run_date)


class BerthAllocator:
    """Works out which berths of a run class are free for a segment."""

    def __init__(self, session: Session) -> None:
        self.inventory = InventoryRepository(session)

    def all_berths(self, run_class: TrainRunClass) -> list[Berth]:
        berths: list[Berth] = []
        for coach in run_class.coaches:
            berths += coach_berths(run_class.travel_class, coach["code"], coach["berths"])
        return berths

    def free_berths(self, run_class: TrainRunClass, from_seq: int, to_seq: int) -> list[Berth]:
        occupied = self.inventory.occupied_berths(run_class.id, from_seq, to_seq)
        return [b for b in self.all_berths(run_class) if (b.coach_code, b.berth_no) not in occupied]


class AvailabilityService:
    def __init__(self, session: Session) -> None:
        self.inventory = InventoryRepository(session)
        self.allocator = BerthAllocator(session)

    def for_segment(
        self,
        run: TrainRun,
        run_class: TrainRunClass,
        from_seq: int,
        to_seq: int,
        now: datetime,
    ) -> Availability:
        if run.status == RunStatus.CANCELLED:
            return Availability("CANCELLED", 0)
        if not booking_open(run, now):
            return Availability("BOOKING_CLOSED", 0)
        free = len(self.allocator.free_berths(run_class, from_seq, to_seq))
        if free:
            return Availability("AVAILABLE", free)
        waitlisted = self.inventory.waitlist_count(run_class.id)
        if waitlisted < run_class.waitlist_limit:
            return Availability("WAITLIST", waitlisted + 1)
        return Availability("NOT_AVAILABLE", 0)
