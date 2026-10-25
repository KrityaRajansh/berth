from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.clock import Clock, today_ist
from app.core.errors import InvalidInput
from app.models.enums import TravelClass
from app.repositories.network import StationRepository
from app.repositories.runs import RunRepository
from app.schemas.common import StationRef
from app.schemas.search import ClassAvailability, FareOut, SearchResult
from app.services.fares import calculate_fare
from app.services.inventory import AvailabilityService
from app.services.schedule import (
    ADVANCE_RESERVATION_DAYS,
    journey_date,
    stop_arrival_at,
    stop_departure_at,
)

CLASS_ORDER = list(TravelClass)


def check_journey_date(day: date, today: date) -> None:
    if day < today:
        raise InvalidInput("The journey date is in the past.", code="DATE_IN_PAST")
    if day > today + timedelta(days=ADVANCE_RESERVATION_DAYS):
        raise InvalidInput(
            f"Bookings open {ADVANCE_RESERVATION_DAYS} days before the journey date.",
            code="DATE_BEYOND_ARP",
        )


class SearchService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self.clock = clock
        self.stations = StationRepository(session)
        self.runs = RunRepository(session)
        self.availability = AvailabilityService(session)

    def search(
        self, from_code: str, to_code: str, day: date, travel_class: TravelClass | None = None
    ) -> list[SearchResult]:
        if from_code.upper() == to_code.upper():
            raise InvalidInput("Source and destination must be different.", code="SAME_STATION")
        check_journey_date(day, today_ist(self.clock))
        origin = self.stations.by_code(from_code)
        destination = self.stations.by_code(to_code)
        if origin is None or destination is None:
            raise InvalidInput("Unknown station code.", code="UNKNOWN_STATION")

        now = self.clock.now()
        results: list[SearchResult] = []
        for run, from_stop, to_stop in self.runs.candidates_for_segment(
            origin.id, destination.id, day
        ):
            if journey_date(run.run_date, from_stop) != day:
                continue
            departure = stop_departure_at(run.run_date, from_stop)
            arrival = stop_arrival_at(run.run_date, to_stop)
            distance = to_stop.distance_km - from_stop.distance_km

            classes = []
            for run_class in sorted(run.classes, key=lambda c: CLASS_ORDER.index(c.travel_class)):
                if travel_class and run_class.travel_class != travel_class:
                    continue
                availability = self.availability.for_segment(
                    run, run_class, from_stop.seq, to_stop.seq, now
                )
                fare = calculate_fare(run_class.travel_class, distance)
                classes.append(
                    ClassAvailability(
                        travel_class=run_class.travel_class,
                        status=availability.status,  # type: ignore[arg-type]
                        count=availability.count,
                        fare=FareOut(
                            base_paise=fare.base,
                            reservation_paise=fare.reservation,
                            gst_paise=fare.gst,
                            total_paise=fare.total,
                        ),
                    )
                )
            if not classes:
                continue
            results.append(
                SearchResult(
                    run_id=run.id,
                    train_number=run.train.number,
                    train_name=run.train.name,
                    from_station=StationRef(code=origin.code, name=origin.name),
                    to_station=StationRef(code=destination.code, name=destination.name),
                    journey_date=day,
                    departure_at=departure,
                    arrival_at=arrival,
                    duration_minutes=int((arrival - departure).total_seconds() // 60),
                    distance_km=distance,
                    classes=classes,
                )
            )
        return sorted(results, key=lambda r: r.departure_at)
