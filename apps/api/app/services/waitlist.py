from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import Passenger, TrainRunClass
from app.models.enums import PassengerStatus
from app.repositories.inventory import InventoryRepository
from app.services.allocation import choose_berth
from app.services.audit import AuditLog
from app.services.inventory import BerthAllocator


class WaitlistService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.inventory = InventoryRepository(session)
        self.allocator = BerthAllocator(session)
        self.audit = AuditLog(session)

    def promote(self, run_class: TrainRunClass) -> list[Passenger]:
        """Confirm waitlisted passengers, in waitlist order, whose whole segment has a free berth.

        The caller must hold the lock on `run_class` (BR-07, FR-WL-02, FR-WL-03).
        """
        promoted: list[Passenger] = []
        for passenger in self.inventory.waitlisted(run_class.id):
            free = self.allocator.free_berths(run_class, passenger.from_seq, passenger.to_seq)
            berth = choose_berth(free, passenger.berth_pref, None)
            if berth is None:
                continue
            passenger.status = PassengerStatus.CNF
            passenger.coach_code = berth.coach_code
            passenger.berth_no = berth.berth_no
            passenger.berth_type = berth.berth_type
            self.session.flush()
            promoted.append(passenger)
            self.audit.record(
                actor_id=None,
                event_type="WAITLIST_PROMOTED",
                entity="passenger",
                entity_id=passenger.id,
                at=self.clock.now(),
                data={"berth": berth.label},
            )
        return promoted
