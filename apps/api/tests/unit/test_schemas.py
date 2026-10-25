import pytest
from pydantic import ValidationError

from app.schemas.booking import BookingCreate, PassengerIn, PaymentRequest

VALID = {"name": "Asha Rao", "age": 34, "gender": "F"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "A"),
        ("age", 0),
        ("age", 121),
        ("gender", "X"),
        ("name", "<script>alert(1)</script>"),
    ],
)
def test_ut19_invalid_passenger_details_are_rejected(field, value):
    with pytest.raises(ValidationError) as exc:
        PassengerIn(**{**VALID, field: value})

    assert exc.value.errors()[0]["loc"] == (field,)


def test_ut19_passenger_count_limits():
    base = {"run_id": 1, "travel_class": "SL", "from_code": "STA", "to_code": "STD"}

    assert len(BookingCreate(**base, passengers=[VALID] * 6).passengers) == 6
    with pytest.raises(ValidationError):
        BookingCreate(**base, passengers=[VALID] * 7)
    with pytest.raises(ValidationError):
        BookingCreate(**base, passengers=[])


def test_passenger_name_whitespace_is_normalised():
    assert PassengerIn(**{**VALID, "name": "  Asha   Rao "}).name == "Asha Rao"


def test_payment_request_checks_instrument():
    assert PaymentRequest(method="upi", upi_id="success@berth").instrument == "success@berth"
    with pytest.raises(ValidationError):
        PaymentRequest(method="card", card_number="1234")
    with pytest.raises(ValidationError):
        PaymentRequest(method="upi", upi_id="not-an-upi-id")
