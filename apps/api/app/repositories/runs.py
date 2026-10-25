from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased, selectinload

from app.models import RouteStop, Train, TrainRun
from app.models.enums import RunStatus

MAX_DAY_OFFSET = 6


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, run_id: int) -> TrainRun | None:
        stmt = (
            select(TrainRun)
            .where(TrainRun.id == run_id)
            .options(
                selectinload(TrainRun.classes),
                selectinload(TrainRun.train).selectinload(Train.stops),
            )
        )
        return self.session.scalar(stmt)

    def lock(self, run_id: int) -> TrainRun:
        stmt = (
            select(TrainRun)
            .where(TrainRun.id == run_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.session.execute(stmt).scalar_one()

    def existing_dates(self, train_ids: list[int], start: date, end: date) -> set[tuple[int, date]]:
        stmt = select(TrainRun.train_id, TrainRun.run_date).where(
            TrainRun.train_id.in_(train_ids), TrainRun.run_date.between(start, end)
        )
        return {(train_id, run_date) for train_id, run_date in self.session.execute(stmt)}

    def candidates_for_segment(
        self, from_station_id: int, to_station_id: int, journey_date: date
    ) -> list[tuple[TrainRun, RouteStop, RouteStop]]:
        """Runs whose route visits `from` before `to` and could pass `from` on the date.

        The exact date check (day offsets, departures after midnight) is done by the caller.
        """
        from_stop = aliased(RouteStop)
        to_stop = aliased(RouteStop)
        possible_run_dates = [journey_date - timedelta(days=k) for k in range(MAX_DAY_OFFSET + 2)]
        stmt = (
            select(TrainRun, from_stop, to_stop)
            .join(Train, Train.id == TrainRun.train_id)
            .join(from_stop, from_stop.train_id == Train.id)
            .join(to_stop, to_stop.train_id == Train.id)
            .where(
                Train.is_active,
                from_stop.station_id == from_station_id,
                to_stop.station_id == to_station_id,
                from_stop.seq < to_stop.seq,
                TrainRun.run_date.in_(possible_run_dates),
            )
            .options(
                selectinload(TrainRun.classes),
                selectinload(TrainRun.train).selectinload(Train.stops),
            )
        )
        return [tuple(row) for row in self.session.execute(stmt).unique()]  # type: ignore[misc]

    def scheduled_up_to(self, last_run_date: date) -> list[TrainRun]:
        stmt = (
            select(TrainRun)
            .where(TrainRun.status == RunStatus.SCHEDULED, TrainRun.run_date <= last_run_date)
            .order_by(TrainRun.run_date, TrainRun.id)
        )
        return list(self.session.scalars(stmt))

    def chart_prepared_up_to(self, last_run_date: date) -> list[TrainRun]:
        stmt = (
            select(TrainRun)
            .where(
                TrainRun.status == RunStatus.CHART_PREPARED,
                TrainRun.run_date <= last_run_date,
            )
            .options(selectinload(TrainRun.train).selectinload(Train.stops))
            .order_by(TrainRun.run_date, TrainRun.id)
        )
        return list(self.session.scalars(stmt))

    def list(self, run_date: date | None, train_number: str | None) -> list[TrainRun]:
        stmt = (
            select(TrainRun)
            .join(Train)
            .options(selectinload(TrainRun.classes), selectinload(TrainRun.train))
            .order_by(TrainRun.run_date, Train.number)
            .limit(200)
        )
        if run_date:
            stmt = stmt.where(TrainRun.run_date == run_date)
        if train_number:
            stmt = stmt.where(Train.number == train_number)
        return list(self.session.scalars(stmt))
