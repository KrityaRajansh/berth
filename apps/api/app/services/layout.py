"""Coach layouts (SRS A-02, SDD 3.2): berth numbering and berth types per class."""

from dataclasses import dataclass, field

from app.models.enums import BerthType, TravelClass

LB, MB, UB, SL, SU = BerthType.LB, BerthType.MB, BerthType.UB, BerthType.SL, BerthType.SU

BAY_PATTERN: dict[TravelClass, tuple[BerthType, ...]] = {
    TravelClass.SL: (LB, MB, UB, LB, MB, UB, SL, SU),
    TravelClass.AC3: (LB, MB, UB, LB, MB, UB, SL, SU),
    TravelClass.AC2: (LB, UB, LB, UB, SL, SU),
    TravelClass.AC1: (LB, UB, LB, UB),
}

DEFAULT_BERTHS: dict[TravelClass, int] = {
    TravelClass.SL: 72,
    TravelClass.AC3: 64,
    TravelClass.AC2: 48,
    TravelClass.AC1: 24,
}

COACH_PREFIX: dict[TravelClass, str] = {
    TravelClass.SL: "S",
    TravelClass.AC3: "B",
    TravelClass.AC2: "A",
    TravelClass.AC1: "H",
}


@dataclass(frozen=True, order=True)
class Berth:
    coach_code: str
    berth_no: int
    berth_type: BerthType = field(compare=False)

    @property
    def label(self) -> str:
        return f"{self.coach_code}/{self.berth_no}/{self.berth_type}"


def berth_type(travel_class: TravelClass, berth_no: int) -> BerthType:
    pattern = BAY_PATTERN[travel_class]
    return pattern[(berth_no - 1) % len(pattern)]


def coach_berths(travel_class: TravelClass, coach_code: str, berth_count: int) -> list[Berth]:
    return [Berth(coach_code, n, berth_type(travel_class, n)) for n in range(1, berth_count + 1)]


def overlaps(a_from: int, a_to: int, b_from: int, b_to: int) -> bool:
    """Whether two half-open stop intervals [from, to) share any part of the route."""
    return a_from < b_to and b_from < a_to
