import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Booking, Passenger
from app.models.enums import Gender, PassengerStatus, TravelClass
from tests.integration.conftest import MONDAY, START, WEDNESDAY
from tests.integration.support import resize, run_class


def test_it32_cancelling_a_run_refunds_everyone_in_full(admin, p1, db, runs):
    sl = run_class(db, "90001", WEDNESDAY, TravelClass.SL)
    resize(db, sl, 1)
    booking = p1.book_and_pay(sl, 2)  # one confirmed, one waitlisted

    response = admin.post(f"/admin/runs/{sl.run_id}/cancel")

    assert response.json() == {"bookings_cancelled": 1}
    after = p1.get(f"/bookings/{booking['id']}").json()
    assert after["status"] == "CANCELLED"
    assert [p["refund_paise"] for p in after["passengers"]] == [200_00, 200_00]
    assert after["refunded_paise"] == 400_00
    assert admin.post(f"/admin/runs/{sl.run_id}/cancel").status_code == 409


def test_it33_database_rejects_overlapping_berths(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking_id = p1.book(sl, 1).json()["id"]  # unpaid, so no berth is held yet

    def confirmed_on_s1_1(from_seq, to_seq):
        return Passenger(
            booking_id=Booking.id.type.python_type(booking_id),
            run_class_id=sl.id,
            from_seq=from_seq,
            to_seq=to_seq,
            seq_no=9,
            name="Direct Insert",
            age=40,
            gender=Gender.M,
            status=PassengerStatus.CNF,
            coach_code="S1",
            berth_no=1,
            fare_paise=0,
        )

    # STA-STC and STC-STD only touch at STC, so both may hold the berth.
    db.add_all([confirmed_on_s1_1(1, 3), confirmed_on_s1_1(3, 4)])
    db.flush()

    with pytest.raises(IntegrityError) as exc, db.begin_nested():
        db.add(confirmed_on_s1_1(2, 4))  # STB-STD overlaps both
        db.flush()
    assert "ex_passenger_berth_overlap" in str(exc.value)


def test_it34_duplicate_station_code(admin, network):
    response = admin.post("/admin/stations", {"code": "STA", "name": "Again", "city": "Again"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATION_EXISTS"


def test_it35_route_validation(admin, network):
    one_stop = [{"station_code": "STA", "departure": "06:00", "day_offset": 0, "distance_km": 0}]
    backwards = [
        {"station_code": "STA", "departure": "06:00", "day_offset": 0, "distance_km": 0},
        {
            "station_code": "STB",
            "arrival": "07:00",
            "departure": "07:05",
            "day_offset": 0,
            "distance_km": 90,
        },
        {"station_code": "STC", "arrival": "08:00", "day_offset": 0, "distance_km": 50},
    ]

    first = admin.put("/admin/trains/90001/route", one_stop)
    second = admin.put("/admin/trains/90001/route", backwards)

    assert first.status_code == second.status_code == 422
    assert first.json()["error"]["code"] == "ROUTE_TOO_SHORT"
    assert second.json()["error"]["code"] == "ROUTE_DISTANCE"


def test_admin_creates_a_train_that_becomes_bookable(admin, guest, db, network, clock):
    admin.post("/admin/stations", {"code": "STE", "name": "Echo", "city": "Echo"})
    created = admin.post(
        "/admin/trains", {"number": "90003", "name": "Echo Link", "running_days": [0]}
    )
    assert created.status_code == 201
    route = admin.put(
        "/admin/trains/90003/route",
        [
            {"station_code": "STA", "departure": "09:00", "day_offset": 0, "distance_km": 0},
            {"station_code": "STE", "arrival": "12:00", "day_offset": 0, "distance_km": 180},
        ],
    )
    assert route.status_code == 200
    coaches = admin.put(
        "/admin/trains/90003/coaches",
        [{"code": "C1", "travel_class": "2A", "berth_count": 48}],
    )
    assert coaches.status_code == 200
    generated = admin.post(
        "/admin/runs/generate",
        {"start": START.date().isoformat(), "end": MONDAY.isoformat(), "train_number": "90003"},
    )
    assert generated.json() == {"created": 1}

    results = guest.get(
        "/trains/search", params={"from": "STA", "to": "STE", "date": MONDAY.isoformat()}
    ).json()
    assert [r["train_number"] for r in results] == ["90003"]
    assert results[0]["classes"][0]["fare"]["total_paise"] == 525_00


def test_route_locked_after_bookings(admin, p1, db, runs):
    p1.book_and_pay(run_class(db, "90001", MONDAY, TravelClass.SL), 1)
    stops = [
        {"station_code": "STA", "departure": "06:00", "day_offset": 0, "distance_km": 0},
        {"station_code": "STD", "arrival": "20:00", "day_offset": 0, "distance_km": 400},
    ]

    response = admin.put("/admin/trains/90001/route", stops)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ROUTE_LOCKED"


def test_passenger_chart_and_stats(admin, p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 2)

    chart = admin.get(f"/admin/runs/{sl.run_id}/chart").json()
    stats = admin.get(
        "/admin/stats", params={"start": START.date().isoformat(), "end": MONDAY.isoformat()}
    ).json()
    runs_list = admin.get("/admin/runs", params={"date": MONDAY.isoformat(), "train": "90001"})

    assert [row["pnr"] for row in chart] == [booking["pnr"]] * 2
    assert {row["coach_code"] for row in chart} == {"S1"}
    assert stats["bookings"] == 1 and stats["passengers"] == 2
    assert stats["revenue_paise"] == 400_00
    sl_row = next(c for c in runs_list.json()[0]["classes"] if c["travel_class"] == "SL")
    assert sl_row["confirmed"] == 2
