import pytest

from app.models.enums import TravelClass
from app.services.fares import calculate_fare


@pytest.mark.parametrize(
    ("case", "travel_class", "km", "base", "reservation", "gst", "total"),
    [
        ("UT-01", TravelClass.SL, 400, 180_00, 20_00, 0, 200_00),
        ("UT-02", TravelClass.AC3, 400, 480_00, 40_00, 26_00, 546_00),
        ("UT-03", TravelClass.AC2, 250, 450_00, 50_00, 25_00, 525_00),
        ("UT-04", TravelClass.AC1, 250, 800_00, 60_00, 43_00, 903_00),
    ],
)
def test_ut01_to_ut04_fare_breakdown(case, travel_class, km, base, reservation, gst, total):
    fare = calculate_fare(travel_class, km)

    assert (fare.base, fare.reservation, fare.gst, fare.total) == (base, reservation, gst, total)


def test_long_haul_3a_fare_used_by_refund_cases():
    assert calculate_fare(TravelClass.AC3, 1400).total == 1806_00


def test_sl_fare_never_shows_gst_after_rounding():
    # 437 km x Rs 0.45 = Rs 196.65; rounding the base keeps GST at zero for SL.
    fare = calculate_fare(TravelClass.SL, 437)

    assert fare.base == 197_00
    assert fare.gst == 0
    assert fare.total == 217_00
