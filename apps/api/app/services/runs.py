from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models import Train, TrainRun, TrainRunClass
from app.models.enums import TravelClass
from app.repositories.network import TrainRepository
from app.repositories.runs import RunRepository

WAITLIST_LIMIT = 20


class RunService:
    """Creates dated train runs with their class inventory (FR-ADM-04, FR-JOB-01)."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.trains = TrainRepository(session)
        self.runs = RunRepository(session)

    def generate(self, start: date, end: date, train_number: str | None = None) -> int:
        if train_number:
            train = self.trains.by_number(train_number)
            if train is None:
                raise NotFound(f"Train {train_number} not found.")
            trains = [train]
        else:
            trains = self.trains.all(active_only=True)

        created = 0
        for train in trains:
            if len(train.stops) < 2 or not train.coaches:
                continue
            day = start
            while day <= end:
                if train.runs_on(day) and not self.runs.exists(train.id, day):
                    self.session.add(self._new_run(train, day))
                    created += 1
                day += timedelta(days=1)
        self.session.commit()
        return created

    @staticmethod
    def _new_run(train: Train, day: date) -> TrainRun:
        coaches_by_class: dict[TravelClass, list[dict[str, object]]] = defaultdict(list)
        for coach in train.coaches:
            coaches_by_class[coach.travel_class].append(
                {"code": coach.code, "berths": coach.berth_count}
            )
        return TrainRun(
            train_id=train.id,
            run_date=day,
            classes=[
                TrainRunClass(
                    travel_class=travel_class,
                    berth_capacity=sum(int(c["berths"]) for c in coaches),  # type: ignore[call-overload]
                    waitlist_limit=WAITLIST_LIMIT,
                    coaches=coaches,
                )
                for travel_class, coaches in coaches_by_class.items()
            ],
        )
