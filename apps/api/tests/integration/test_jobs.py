from datetime import timedelta

from sqlalchemy import select

from app.models import Refund, TrainRun
from app.models.enums import TravelClass
from app.services.runs import RunService
from tests.integration.conftest import MONDAY, START
from tests.integration.support import resize, run_class


def run_job(admin, name):
    response = admin.post(f"/admin/jobs/{name}/run")
    assert response.status_code == 200, response.text
    return response.json()


def test_it27_chart_preparation_cancels_waitlist_with_full_refund(admin, p1, db, runs, clock):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    resize(db, sl, 1)
    booking = p1.book_and_pay(sl, 3)  # 1 confirmed, 2 waitlisted

    clock.at = START.replace(hour=18)
    first = run_job(admin, "chart-preparation")
    second = run_job(admin, "chart-preparation")

    after = p1.get(f"/bookings/{booking['id']}").json()
    statuses = [p["current_status"] for p in after["passengers"]]
    assert statuses[0].startswith("CNF") and statuses[1:] == ["CAN", "CAN"]
    assert [p["refund_paise"] for p in after["passengers"]] == [0, 200_00, 200_00]
    assert after["chart_prepared"] is True
    refunds = db.scalars(select(Refund).where(Refund.booking_id == after["id"])).all()
    assert [(r.reason, r.amount_paise) for r in refunds] == [("CHART_PREPARED", 400_00)]
    # Due at Sun 18:00: 90001 on Monday, and 90002 on Sunday and Monday.
    assert first["status"] == "SUCCEEDED" and first["items_processed"] == 3
    assert second["items_processed"] == 0


def test_chart_preparation_waits_for_cutoff(admin, db, runs, clock):
    clock.at = START.replace(hour=17, minute=59)

    result = run_job(admin, "chart-preparation")

    assert result["items_processed"] == 1  # only Sunday's 90002 run is due


def test_it28_run_generation_creates_runs_on_running_days_only(admin, db, network):
    first = run_job(admin, "run-generation")
    second = run_job(admin, "run-generation")

    window = [START.date() + timedelta(days=i) for i in range(61)]
    expected = sum(1 for d in window if d.weekday() in (0, 2, 4)) + len(window)
    assert first["items_processed"] == expected
    assert second["items_processed"] == 0
    run_dates = db.scalars(
        select(TrainRun.run_date).join(TrainRun.train).where(TrainRun.train.has(number="90001"))
    ).all()
    assert {d.weekday() for d in run_dates} == {0, 2, 4}


def test_it29_journey_completion(admin, p1, db, runs, clock):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking = p1.book_and_pay(sl, 1)

    clock.at = START.replace(hour=18)
    run_job(admin, "chart-preparation")
    clock.at = START.replace(day=2, hour=19, minute=59)  # Monday, before arrival at 20:00
    admin.login("admin@example.com")  # the session from Sunday morning has expired
    early = run_job(admin, "journey-completion")
    clock.at = START.replace(day=2, hour=20, minute=1)
    done = run_job(admin, "journey-completion")

    assert early["items_processed"] == 0
    assert done["items_processed"] == 1  # 90001 Monday; 90002 Sunday arrives Monday 21:00
    p1.login("passenger1@example.com")
    assert p1.get(f"/bookings/{booking['id']}").json()["status"] == "COMPLETED"


def test_it30_payment_expiry(admin, p1, db, runs, clock):
    sl = run_class(db, "90001", MONDAY, TravelClass.SL)
    booking_id = p1.book(sl, 1).json()["id"]

    clock.advance(minutes=20)
    result = run_job(admin, "payment-expiry")

    assert result["items_processed"] == 1
    assert p1.get(f"/bookings/{booking_id}").json()["status"] == "EXPIRED"


def test_it31_cron_endpoints_need_the_secret(guest, network):
    assert guest.get("/jobs/nightly").status_code == 401
    wrong = guest.get("/jobs/nightly", headers={"Authorization": "Bearer wrong"})
    assert wrong.status_code == 401

    right = guest.get("/jobs/nightly", headers={"Authorization": "Bearer test-cron-secret"})
    assert right.status_code == 200
    assert [j["job_name"] for j in right.json()] == [
        "run-generation",
        "chart-preparation",
        "journey-completion",
        "payment-expiry",
    ]


def test_job_history_and_unknown_job(admin, network):
    run_job(admin, "payment-expiry")

    history = admin.get("/admin/jobs").json()

    assert history[0]["job_name"] == "payment-expiry"
    assert history[0]["triggered_by"] == "admin"
    assert admin.post("/admin/jobs/nope/run").status_code == 404


def test_generated_runs_snapshot_coach_composition(db, network):
    RunService(db).generate(MONDAY, MONDAY)

    sl = run_class(db, "90001", MONDAY, TravelClass.SL)

    assert sl.coaches == [{"code": "S1", "berths": 72}]
    assert sl.berth_capacity == 72
    assert run_class(db, "90001", MONDAY, TravelClass.AC3).berth_capacity == 64
