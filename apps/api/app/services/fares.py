"""Fare rules (SRS BR-04, Table 8.1). All amounts are in paise."""

from dataclasses import dataclass
from fractions import Fraction

from app.models.enums import TravelClass
from app.services.money import round_to_rupee


@dataclass(frozen=True)
class ClassRates:
    rate_per_km: int
    min_base: int
    reservation: int
    gst_percent: int
    cancellation_fee: int


RATES: dict[TravelClass, ClassRates] = {
    TravelClass.SL: ClassRates(45, 100_00, 20_00, 0, 120_00),
    TravelClass.AC3: ClassRates(120, 300_00, 40_00, 5, 180_00),
    TravelClass.AC2: ClassRates(175, 450_00, 50_00, 5, 200_00),
    TravelClass.AC1: ClassRates(300, 800_00, 60_00, 5, 240_00),
}


@dataclass(frozen=True)
class FareBreakdown:
    base: int
    reservation: int
    gst: int
    total: int


def calculate_fare(travel_class: TravelClass, distance_km: int) -> FareBreakdown:
    rates = RATES[travel_class]
    base = round_to_rupee(max(rates.min_base, distance_km * rates.rate_per_km))
    taxable = base + rates.reservation
    total = round_to_rupee(Fraction(taxable * (100 + rates.gst_percent), 100))
    return FareBreakdown(
        base=base,
        reservation=rates.reservation,
        gst=total - taxable,
        total=total,
    )
