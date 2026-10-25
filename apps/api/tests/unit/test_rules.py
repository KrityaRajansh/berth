from datetime import date, datetime, time

from app.core.clock import IST
from app.core.security import hash_password, verify_password
from app.models.network import RouteStop, Train
from app.services.payment_gateway import MockPaymentGateway
from app.services.pnr import generate_pnr, mask_name
from app.services.schedule import chart_cutoff, stop_departure_at

MON_WED_FRI = 0b0010101


def test_ut18_pnrs_are_ten_digits_and_unique():
    pnrs = [generate_pnr() for _ in range(10_000)]

    assert all(len(p) == 10 and p.isdigit() and p[0] != "0" for p in pnrs)
    assert len(set(pnrs)) == len(pnrs)


def test_ut20_password_hashing():
    hashed = hash_password("Secret@123")

    assert hashed.startswith("$2b$")
    assert hashed != "Secret@123"
    assert verify_password("Secret@123", hashed)
    assert not verify_password("secret@123", hashed)


def test_ut21_running_days():
    train = Train(number="90001", name="Fixture Express", running_days=MON_WED_FRI)

    assert train.runs_on(date(2026, 11, 2))  # Monday
    assert not train.runs_on(date(2026, 11, 3))  # Tuesday


def test_ut22_chart_cutoff():
    assert chart_cutoff(date(2026, 11, 10)) == datetime(2026, 11, 9, 18, 0, tzinfo=IST)


def test_departure_after_midnight_moves_to_next_day():
    stop = RouteStop(arrival=time(23, 50), departure=time(0, 5), day_offset=0)

    assert stop_departure_at(date(2026, 11, 10), stop) == datetime(2026, 11, 11, 0, 5, tzinfo=IST)


def test_ut23_name_masking():
    assert mask_name("Rahul Sharma") == "Ra*** Sh****"


def test_ut24_mock_gateway():
    gateway = MockPaymentGateway()

    for instrument in ("4111 1111 1111 1111", "success@berth"):
        result = gateway.charge(500_00, "ref", instrument)
        assert result.approved
        assert result.reference
    for instrument in ("4000 0000 0000 0002", "failure@berth"):
        assert not gateway.charge(500_00, "ref", instrument).approved
    assert gateway.refund("PAY-1", 100_00).approved
