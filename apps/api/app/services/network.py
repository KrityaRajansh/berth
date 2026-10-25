from itertools import pairwise

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, InvalidInput, NotFound
from app.models import Booking, Coach, RouteStop, Station, Train, TrainRun
from app.repositories.network import StationRepository, TrainRepository
from app.schemas.network import (
    CoachIn,
    CoachOut,
    RouteStopIn,
    RouteStopOut,
    StationIn,
    TrainIn,
    TrainOut,
)


def days_to_mask(days: list[int]) -> int:
    mask = 0
    for day in days:
        mask |= 1 << day
    return mask


def mask_to_days(mask: int) -> list[int]:
    return [d for d in range(7) if mask & (1 << d)]


def train_out(train: Train) -> TrainOut:
    return TrainOut(
        id=train.id,
        number=train.number,
        name=train.name,
        running_days=mask_to_days(train.running_days),
        is_active=train.is_active,
        stops=[
            RouteStopOut(
                seq=s.seq,
                station_code=s.station.code,
                station_name=s.station.name,
                arrival=s.arrival,
                departure=s.departure,
                day_offset=s.day_offset,
                distance_km=s.distance_km,
            )
            for s in train.stops
        ],
        coaches=[CoachOut.model_validate(c) for c in train.coaches],
    )


class NetworkService:
    """Administration of stations, trains, routes and coach composition (FR-ADM-01 to 03)."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.stations = StationRepository(session)
        self.trains = TrainRepository(session)

    # Stations

    def create_station(self, data: StationIn) -> Station:
        if self.stations.by_code(data.code):
            raise Conflict(f"Station {data.code} already exists.", code="STATION_EXISTS")
        station = Station(**data.model_dump())
        self.session.add(station)
        self.session.commit()
        return station

    def update_station(self, station_id: int, data: StationIn) -> Station:
        station = self.stations.get(station_id)
        if station is None:
            raise NotFound("Station not found.")
        other = self.stations.by_code(data.code)
        if other and other.id != station.id:
            raise Conflict(f"Station {data.code} already exists.", code="STATION_EXISTS")
        for field, value in data.model_dump().items():
            setattr(station, field, value)
        self.session.commit()
        return station

    # Trains

    def get_train(self, number: str) -> Train:
        train = self.trains.by_number(number)
        if train is None:
            raise NotFound(f"Train {number} not found.")
        return train

    def create_train(self, data: TrainIn) -> Train:
        if self.trains.by_number(data.number):
            raise Conflict(f"Train {data.number} already exists.", code="TRAIN_EXISTS")
        train = Train(
            number=data.number,
            name=data.name,
            running_days=days_to_mask(data.running_days),
            is_active=data.is_active,
        )
        self.session.add(train)
        self.session.commit()
        return self.get_train(train.number)

    def update_train(self, number: str, data: TrainIn) -> Train:
        train = self.get_train(number)
        if data.number != train.number and self.trains.by_number(data.number):
            raise Conflict(f"Train {data.number} already exists.", code="TRAIN_EXISTS")
        train.number = data.number
        train.name = data.name
        train.running_days = days_to_mask(data.running_days)
        train.is_active = data.is_active
        self.session.commit()
        return self.get_train(train.number)

    def set_route(self, number: str, stops: list[RouteStopIn]) -> Train:
        train = self.get_train(number)
        self._validate_route(stops)
        if self._has_bookings(train):
            raise Conflict(
                "The route cannot change once tickets have been booked on this train.",
                code="ROUTE_LOCKED",
            )
        stations = {}
        for stop in stops:
            station = self.stations.by_code(stop.station_code)
            if station is None:
                raise InvalidInput(f"Unknown station {stop.station_code}.", code="UNKNOWN_STATION")
            stations[stop.station_code] = station

        train.stops.clear()
        self.session.flush()
        for seq, stop in enumerate(stops, start=1):
            train.stops.append(
                RouteStop(
                    seq=seq,
                    station_id=stations[stop.station_code].id,
                    arrival=None if seq == 1 else stop.arrival,
                    departure=None if seq == len(stops) else stop.departure,
                    day_offset=stop.day_offset,
                    distance_km=stop.distance_km,
                )
            )
        self.session.commit()
        self.session.expire(train)
        return self.get_train(number)

    def set_coaches(self, number: str, coaches: list[CoachIn]) -> Train:
        """Applies to train runs generated afterwards; existing runs keep their composition."""
        train = self.get_train(number)
        codes = [c.code for c in coaches]
        if len(set(codes)) != len(codes):
            raise InvalidInput("Coach codes must be unique.", code="DUPLICATE_COACH")
        train.coaches.clear()
        self.session.flush()
        for coach in coaches:
            train.coaches.append(Coach(**coach.model_dump()))
        self.session.commit()
        self.session.expire(train)
        return self.get_train(number)

    @staticmethod
    def _validate_route(stops: list[RouteStopIn]) -> None:
        if len(stops) < 2:
            raise InvalidInput("A route needs at least two stops.", code="ROUTE_TOO_SHORT")
        codes = [s.station_code for s in stops]
        if len(set(codes)) != len(codes):
            raise InvalidInput("A station can appear only once on a route.", code="ROUTE_REPEAT")
        if stops[0].distance_km != 0:
            raise InvalidInput("The first stop must be at 0 km.", code="ROUTE_DISTANCE")
        for prev, cur in pairwise(stops):
            if cur.distance_km <= prev.distance_km:
                raise InvalidInput(
                    "Distances must increase along the route.", code="ROUTE_DISTANCE"
                )
            if cur.day_offset < prev.day_offset:
                raise InvalidInput(
                    "Day offsets cannot decrease along the route.", code="ROUTE_DAYS"
                )
        if stops[0].departure is None or stops[-1].arrival is None:
            raise InvalidInput(
                "The first stop needs a departure time and the last an arrival time.",
                code="ROUTE_TIMES",
            )

    def _has_bookings(self, train: Train) -> bool:
        stmt = select(exists().where(Booking.run_id == TrainRun.id, TrainRun.train_id == train.id))
        return bool(self.session.scalar(stmt))
