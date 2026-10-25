"""Test data (test plan section 3.4) and a small API client wrapper."""

from datetime import date, time
from functools import cache
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Coach, RouteStop, Station, Train, TrainRun, TrainRunClass, User
from app.models.enums import Role, TravelClass

PASSWORD = "Passw0rd!"
APPROVE_CARD = "4111 1111 1111 1111"
DECLINE_CARD = "4000 0000 0000 0002"
MON_WED_FRI = 0b0010101
DAILY = 0b1111111


@cache
def password_hash() -> str:
    return hash_password(PASSWORD)


def build_network(db: Session) -> None:
    stations = {
        code: Station(code=code, name=name, city=name)
        for code, name in [("STA", "Alpha"), ("STB", "Bravo"), ("STC", "Charlie"), ("STD", "Delta")]
    }
    db.add_all(stations.values())
    db.flush()

    fixture = Train(number="90001", name="Fixture Express", running_days=MON_WED_FRI)
    fixture.stops = [
        RouteStop(seq=1, station_id=stations["STA"].id, departure=time(6, 0), distance_km=0),
        RouteStop(
            seq=2,
            station_id=stations["STB"].id,
            arrival=time(8, 0),
            departure=time(8, 5),
            distance_km=100,
        ),
        RouteStop(
            seq=3,
            station_id=stations["STC"].id,
            arrival=time(11, 0),
            departure=time(11, 5),
            distance_km=250,
        ),
        RouteStop(seq=4, station_id=stations["STD"].id, arrival=time(20, 0), distance_km=400),
    ]
    fixture.coaches = [
        Coach(code="S1", travel_class=TravelClass.SL, berth_count=72),
        Coach(code="B1", travel_class=TravelClass.AC3, berth_count=64),
        Coach(code="A1", travel_class=TravelClass.AC2, berth_count=48),
        Coach(code="H1", travel_class=TravelClass.AC1, berth_count=24),
    ]

    long_haul = Train(number="90002", name="Long Haul Mail", running_days=DAILY)
    long_haul.stops = [
        RouteStop(seq=1, station_id=stations["STA"].id, departure=time(22, 0), distance_km=0),
        RouteStop(
            seq=2,
            station_id=stations["STD"].id,
            arrival=time(21, 0),
            day_offset=1,
            distance_km=1400,
        ),
    ]
    long_haul.coaches = [Coach(code="B1", travel_class=TravelClass.AC3, berth_count=64)]

    db.add_all([fixture, long_haul])
    db.add_all(
        [
            User(
                full_name=name,
                email=email,
                mobile=mobile,
                password_hash=password_hash(),
                role=role,
            )
            for name, email, mobile, role in [
                ("Passenger One", "passenger1@example.com", "9000000001", Role.PASSENGER),
                ("Passenger Two", "passenger2@example.com", "9000000002", Role.PASSENGER),
                ("Admin User", "admin@example.com", "9000000003", Role.ADMIN),
            ]
        ]
    )
    db.commit()


def run_class(db: Session, train_number: str, run_date: date, cls: TravelClass) -> TrainRunClass:
    stmt = (
        select(TrainRunClass)
        .join(TrainRun)
        .join(Train)
        .where(
            Train.number == train_number,
            TrainRun.run_date == run_date,
            TrainRunClass.travel_class == cls,
        )
    )
    return db.execute(stmt).scalar_one()


def resize(db: Session, rc: TrainRunClass, berths: int, waitlist_limit: int = 20) -> None:
    """Shrink a run class to a few berths so capacity cases are quick to set up."""
    code = rc.coaches[0]["code"] if rc.coaches else "S1"
    rc.coaches = [{"code": code, "berths": berths}] if berths else []
    rc.berth_capacity = berths
    rc.waitlist_limit = waitlist_limit
    db.commit()


def passengers(n: int, **overrides: Any) -> list[dict[str, Any]]:
    names = ["Asha Rao", "Vikram Das", "Meera Iyer", "Rohan Gupta", "Neha Singh", "Kabir Khan"]
    return [
        {"name": names[i], "age": 30 + i, "gender": "F" if i % 2 == 0 else "M", **overrides}
        for i in range(n)
    ]


class Api:
    def __init__(self, client: TestClient) -> None:
        self.client = client

    def login(self, email: str, password: str = PASSWORD) -> "Api":
        response = self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return self

    def get(self, path: str, **kwargs: Any):
        return self.client.get(f"/api/v1{path}", **kwargs)

    def post(self, path: str, json: Any = None, **kwargs: Any):
        return self.client.post(f"/api/v1{path}", json=json, **kwargs)

    def put(self, path: str, json: Any = None):
        return self.client.put(f"/api/v1{path}", json=json)

    def book(
        self,
        run_class_: TrainRunClass,
        n: int = 1,
        frm: str = "STA",
        to: str = "STD",
        confirm_only: bool = False,
        pax: list[dict[str, Any]] | None = None,
    ):
        return self.post(
            "/bookings",
            {
                "run_id": run_class_.run_id,
                "travel_class": str(run_class_.travel_class),
                "from_code": frm,
                "to_code": to,
                "passengers": pax or passengers(n),
                "confirm_only": confirm_only,
            },
        )

    def pay(self, booking_id: str, card: str = APPROVE_CARD):
        return self.post(
            f"/bookings/{booking_id}/payments", {"method": "card", "card_number": card}
        )

    def book_and_pay(self, run_class_: TrainRunClass, n: int = 1, **kwargs: Any) -> dict[str, Any]:
        created = self.book(run_class_, n, **kwargs)
        assert created.status_code == 201, created.text
        paid = self.pay(created.json()["id"])
        assert paid.status_code == 200, paid.text
        return paid.json()
