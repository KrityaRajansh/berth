from sqlalchemy import func, select

from app.models import Payment
from app.models.enums import PaymentStatus, TravelClass
from tests.integration.conftest import MONDAY, START
from tests.integration.support import DECLINE_CARD, passengers, resize, run_class


def payments(db, booking_id, status=None):
    stmt = select(func.count()).select_from(Payment).where(Payment.booking_id == booking_id)
    if status:
        stmt = stmt.where(Payment.status == status)
    return db.scalar(stmt)


def test_it10_create_booking_is_pending_with_total(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)

    response = p1.book(sl, 2)

    assert response.status_code == 201
    booking = response.json()
    assert booking["status"] == "PENDING_PAYMENT"
    assert booking["total_fare_paise"] == 400_00
    assert booking["pnr"] is None
    assert booking["expires_at"] == "2026-11-01T06:15:00+05:30"
    assert [p["current_status"] for p in booking["passengers"]] == ["PENDING", "PENDING"]


def test_it11_payment_confirms_with_pnr_and_berths(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)

    booking = p1.book_and_pay(sl, 2)

    assert booking["status"] == "BOOKED"
    assert len(booking["pnr"]) == 10 and booking["pnr"].isdigit()
    statuses = [p["current_status"] for p in booking["passengers"]]
    assert all(s.startswith("CNF/S1/") for s in statuses)
    assert len(set(statuses)) == 2
    assert [p["booking_status"] for p in booking["passengers"]] == statuses


def test_it12_and_it13_declined_payment_can_be_retried(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking_id = p1.book(sl, 1).json()["id"]

    declined = p1.pay(booking_id, card=DECLINE_CARD)
    assert declined.status_code == 402
    assert declined.json()["error"]["code"] == "PAYMENT_DECLINED"
    assert p1.get(f"/bookings/{booking_id}").json()["status"] == "PENDING_PAYMENT"
    assert payments(db, booking_id, PaymentStatus.FAILED) == 1

    retried = p1.pay(booking_id)
    assert retried.status_code == 200
    assert retried.json()["status"] == "BOOKED"


def test_it14_repeated_payment_is_processed_once(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking_id = p1.book(sl, 1).json()["id"]

    first = p1.pay(booking_id).json()
    second = p1.pay(booking_id).json()

    assert first == second
    assert payments(db, booking_id, PaymentStatus.SUCCESS) == 1


def test_it15_payment_after_window_expires(p1, db, runs, clock):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking_id = p1.book(sl, 1).json()["id"]

    clock.advance(minutes=16)
    response = p1.pay(booking_id)

    assert response.status_code == 410
    assert p1.get(f"/bookings/{booking_id}").json()["status"] == "EXPIRED"
    assert payments(db, booking_id) == 0


def test_it16_passengers_beyond_capacity_are_waitlisted(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    resize(db, sl, 2)

    booking = p1.book_and_pay(sl, 3)

    statuses = [p["current_status"] for p in booking["passengers"]]
    assert statuses[0].startswith("CNF") and statuses[1].startswith("CNF")
    assert statuses[2] == "WL 1"
    assert booking["passengers"][2]["booking_status"] == "WL 1"


def test_it17_full_train_and_waitlist_rejects_without_charge(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    resize(db, sl, 0)
    for _ in range(3):
        p1.book_and_pay(sl, 6)
    p1.book_and_pay(sl, 2)  # waitlist now holds 20

    booking_id = p1.book(sl, 1).json()["id"]
    response = p1.pay(booking_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_AVAILABLE"
    assert p1.get(f"/bookings/{booking_id}").json()["status"] == "FAILED"
    assert payments(db, booking_id) == 0


def test_confirm_only_booking_is_rejected_without_charge(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    resize(db, sl, 1)
    booking_id = p1.book(sl, 2, confirm_only=True).json()["id"]

    response = p1.pay(booking_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFIRMATION_UNAVAILABLE"
    assert payments(db, booking_id) == 0


def test_it18_other_users_cannot_see_a_booking(p1, p2, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 1)

    assert p2.get(f"/bookings/{booking['id']}").status_code == 404
    assert p2.get(f"/bookings/{booking['id']}/ticket.pdf").status_code == 404


def test_booking_validation_errors(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)

    wrong_way = p1.book(sl, 1, frm="STD", to="STA")
    too_many = p1.book(sl, pax=passengers(6) + passengers(1))

    assert wrong_way.status_code == 422
    assert wrong_way.json()["error"]["code"] == "INVALID_SEGMENT"
    assert too_many.status_code == 422


def test_booking_closes_at_chart_cutoff(p1, db, runs, clock):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    clock.at = START.replace(hour=18)

    response = p1.book(sl, 1)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BOOKING_CLOSED"


def test_my_bookings_lists_paid_bookings_only(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    paid = p1.book_and_pay(sl, 1)
    p1.book(sl, 1)  # left unpaid

    listed = p1.get("/bookings").json()

    assert [b["id"] for b in listed] == [paid["id"]]
    assert listed[0]["passenger_count"] == 1


def test_overnight_journey_arrives_next_day(p1, db, runs):
    long_haul = run_class(db, "90002", MONDAY, TravelClass.AC3)

    booking = p1.book_and_pay(long_haul, 1)

    assert booking["journey_date"] == MONDAY.isoformat()
    assert booking["departure_at"] == "2026-11-02T22:00:00+05:30"
    assert booking["arrival_at"] == "2026-11-03T21:00:00+05:30"
    assert booking["total_fare_paise"] == 1806_00


def test_todays_runs_are_closed_by_the_chart_rule(p1, db, runs):
    today = run_class(db, "90002", START.date(), TravelClass.AC3)

    response = p1.book(today, 1)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BOOKING_CLOSED"
