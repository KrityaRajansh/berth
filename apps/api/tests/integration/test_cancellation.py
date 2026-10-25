from io import BytesIO

from pypdf import PdfReader

from app.models.enums import TravelClass
from tests.integration.conftest import MONDAY, START, WEDNESDAY
from tests.integration.support import resize, run_class


def cancel(api, booking, *indexes):
    ids = [booking["passengers"][i]["id"] for i in indexes]
    return api.post(f"/bookings/{booking['id']}/cancellations", {"passenger_ids": ids})


def test_it19_quote_matches_refund_rules(p1, db, runs):
    sl = run_class(db, "90001", WEDNESDAY, TravelClass.SL)  # departs in 72 hours
    booking = p1.book_and_pay(sl, 1)

    quote = p1.post(
        f"/bookings/{booking['id']}/cancellation-quote",
        {"passenger_ids": [booking["passengers"][0]["id"]]},
    ).json()

    assert quote["total_refund_paise"] == 80_00


def test_it20_partial_cancellation(p1, db, runs):
    sl = run_class(db, "90001", WEDNESDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 2)

    updated = cancel(p1, booking, 0).json()

    assert updated["status"] == "BOOKED"
    assert updated["passengers"][0]["current_status"] == "CAN"
    assert updated["passengers"][0]["refund_paise"] == 80_00
    assert updated["passengers"][1]["current_status"].startswith("CNF")
    assert updated["refunded_paise"] == 80_00


def test_it21_cancellation_promotes_waitlist_in_order(p1, p2, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    resize(db, sl, 2)
    confirmed = p1.book_and_pay(sl, 2)
    waitlisted = p2.book_and_pay(sl, 2)
    assert [p["current_status"] for p in waitlisted["passengers"]] == ["WL 1", "WL 2"]

    released = confirmed["passengers"][0]["current_status"]
    cancel(p1, confirmed, 0)

    after = p2.get(f"/bookings/{waitlisted['id']}").json()
    assert after["passengers"][0]["current_status"] == released
    assert after["passengers"][1]["current_status"] == "WL 1"
    assert after["passengers"][0]["booking_status"] == "WL 1"


def test_it22_promotion_respects_segments(p1, p2, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    resize(db, sl, 1)
    first_leg = p1.book_and_pay(sl, 1, frm="STA", to="STB")
    p1.book_and_pay(sl, 1, frm="STB", to="STD")  # same berth, later segment
    whole_route = p2.book_and_pay(sl, 1, frm="STA", to="STD")
    short_hop = p2.book_and_pay(sl, 1, frm="STA", to="STB")

    cancel(p1, first_leg, 0)

    assert p2.get(f"/bookings/{whole_route['id']}").json()["passengers"][0]["current_status"] == (
        "WL 1"
    )
    assert (
        p2.get(f"/bookings/{short_hop['id']}")
        .json()["passengers"][0]["current_status"]
        .startswith("CNF/S1/1/")
    )


def test_it23_cancelling_everyone_cancels_the_booking(p1, db, runs):
    sl = run_class(db, "90001", WEDNESDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 2)

    updated = cancel(p1, booking, 0, 1).json()

    assert updated["status"] == "CANCELLED"
    assert updated["can_cancel"] is False


def test_it24_no_cancellation_after_chart_cutoff(p1, db, runs, clock):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 1)

    clock.at = START.replace(hour=18)
    response = cancel(p1, booking, 0)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CANCELLATION_CLOSED"
    assert (
        p1.get(f"/bookings/{booking['id']}")
        .json()["passengers"][0]["current_status"]
        .startswith("CNF")
    )


def test_cancelled_passenger_cannot_be_cancelled_again(p1, db, runs):
    sl = run_class(db, "90001", WEDNESDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 2)
    cancel(p1, booking, 0)

    again = cancel(p1, booking, 0)

    assert again.status_code == 422
    assert again.json()["error"]["code"] == "INVALID_PASSENGERS"


def test_it25_ticket_pdf(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 2)

    response = p1.get(f"/bookings/{booking['id']}/ticket.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    text = "".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
    assert booking["pnr"] in text
    assert "Asha Rao" in text and "Vikram Das" in text


def test_ticket_unavailable_before_payment(p1, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking_id = p1.book(sl, 1).json()["id"]

    response = p1.get(f"/bookings/{booking_id}/ticket.pdf")

    assert response.status_code == 409


def test_it26_public_pnr_status_masks_names(p1, guest, db, runs):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 1)

    status = guest.get(f"/pnr/{booking['pnr']}").json()

    assert status["passengers"][0]["name"] == "As** Ra*"
    assert status["passengers"][0]["current_status"].startswith("CNF")
    assert guest.get("/pnr/123").status_code == 422
    assert guest.get("/pnr/1234567890").status_code == 404
