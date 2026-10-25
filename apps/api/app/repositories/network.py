from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Station, Train


class StationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, station_id: int) -> Station | None:
        return self.session.get(Station, station_id)

    def by_code(self, code: str) -> Station | None:
        return self.session.scalar(select(Station).where(Station.code == code.upper()))

    def suggest(self, query: str, limit: int = 10) -> list[Station]:
        q = query.strip()
        pattern = f"%{q}%"
        stmt = (
            select(Station)
            .where(
                Station.is_active,
                or_(Station.code.ilike(f"{q}%"), Station.name.ilike(pattern)),
            )
            # Exact code matches first, then alphabetical.
            .order_by((func.upper(Station.code) == q.upper()).desc(), Station.name)
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def all(self) -> list[Station]:
        return list(self.session.scalars(select(Station).order_by(Station.code)))


class TrainRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _with_details(self):
        return select(Train).options(selectinload(Train.stops), selectinload(Train.coaches))

    def get(self, train_id: int) -> Train | None:
        return self.session.scalar(self._with_details().where(Train.id == train_id))

    def by_number(self, number: str) -> Train | None:
        return self.session.scalar(self._with_details().where(Train.number == number))

    def all(self, active_only: bool = False) -> list[Train]:
        stmt = self._with_details().order_by(Train.number)
        if active_only:
            stmt = stmt.where(Train.is_active)
        return list(self.session.scalars(stmt))
