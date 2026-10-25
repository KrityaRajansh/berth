from datetime import timedelta

from app.models.enums import TravelClass
from tests.integration.conftest import MONDAY, START, TUESDAY, WEDNESDAY
from tests.integration.support import resize, run_class


def search(api, frm, to, day, **params):
    return api.get(
        "/trains/search", params={"from": frm, "to": to, "date": day.isoformat(), **params}
    )


def test_it05_station_suggestions(guest, network):
    response = guest.get("/stations", params={"q": "bra"})

    assert [s["code"] for s in response.json()] == ["STB"]


def test_it06_search_returns_segment_details(guest, runs):
    results = search(guest, "STB", "STD", WEDNESDAY).json()

    assert [r["train_number"] for r in results] == ["90001"]
    result = results[0]
    assert result["distance_km"] == 300
    assert result["departure_at"].startswith("2026-11-04T08:05")
    assert result["arrival_at"].startswith("2026-11-04T20:00")
    assert result["duration_minutes"] == 11 * 60 + 55
    assert [c["travel_class"] for c in result["classes"]] == ["SL", "3A", "2A", "1A"]
    assert result["classes"][0]["status"] == "AVAILABLE"
    assert result["classes"][0]["fare"]["total_paise"] == 155_00

    assert search(guest, "STD", "STB", WEDNESDAY).json() == []


def test_it07_train_not_listed_on_non_running_day(guest, runs):
    numbers = [r["train_number"] for r in search(guest, "STA", "STD", TUESDAY).json()]

    assert "90001" not in numbers
    assert numbers == ["90002"]


def test_it08_search_validation(guest, runs):
    same = search(guest, "STA", "STA", MONDAY)
    past = search(guest, "STA", "STD", START.date() - timedelta(days=1))
    beyond = search(guest, "STA", "STD", START.date() + timedelta(days=61))

    assert same.status_code == past.status_code == beyond.status_code == 422
    assert same.json()["error"]["code"] == "SAME_STATION"
    assert past.json()["error"]["code"] == "DATE_IN_PAST"
    assert beyond.json()["error"]["code"] == "DATE_BEYOND_ARP"


def test_it09_berths_are_reused_after_passengers_alight(guest, p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    resize(db, sl, 2)
    p1.book_and_pay(sl, 2, frm="STA", to="STB")

    later = search(guest, "STB", "STD", MONDAY, cls="SL").json()[0]["classes"][0]
    overlapping = search(guest, "STA", "STC", MONDAY, cls="SL").json()[0]["classes"][0]

    assert (later["status"], later["count"]) == ("AVAILABLE", 2)
    assert (overlapping["status"], overlapping["count"]) == ("WAITLIST", 1)


def test_class_filter_and_closed_runs(guest, runs, clock):
    filtered = search(guest, "STA", "STD", MONDAY, cls="2A").json()
    assert [c["travel_class"] for c in filtered[0]["classes"]] == ["2A"]

    clock.advance(hours=12)  # 18:00 on Sunday: Monday's chart cut-off
    closed = search(guest, "STA", "STD", MONDAY).json()
    assert {c["status"] for r in closed for c in r["classes"]} == {"BOOKING_CLOSED"}


def test_train_route_is_public(guest, network):
    route = guest.get("/trains/90001/route").json()

    assert [s["station_code"] for s in route["stops"]] == ["STA", "STB", "STC", "STD"]
    assert route["running_days"] == [0, 2, 4]
