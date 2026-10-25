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

        # One query for what already exists, instead of one per train per day.
        existing = self.runs.existing_dates([t.id for t in trains], start, end)
        new_runs = []
        for train in trains:
            if len(train.stops) < 2 or not train.coaches:
                continue
            day = start
            while day <= end:
                if train.runs_on(day) and (train.id, day) not in existing:
                    new_runs.append(self._new_run(train, day))
                day += timedelta(days=1)
        self.session.add_all(new_runs)
        self.session.commit()
        return len(new_runs)

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
