import pytest

from app.models.enums import BerthType, TravelClass
from app.services.allocation import AllocationRejected, plan_allocation
from app.services.layout import DEFAULT_BERTHS, Berth, berth_type, coach_berths, overlaps

LB, MB, UB, SL, SU = BerthType.LB, BerthType.MB, BerthType.UB, BerthType.SL, BerthType.SU


def test_ut11_sleeper_layout():
    types = [berth_type(TravelClass.SL, n) for n in range(1, 9)]

    assert types == [LB, MB, UB, LB, MB, UB, SL, SU]
    assert berth_type(TravelClass.SL, 72) == SU
    assert DEFAULT_BERTHS[TravelClass.SL] == 72


def test_ut12_two_tier_layout_and_three_tier_size():
    assert berth_type(TravelClass.AC2, 5) == SL
    assert DEFAULT_BERTHS[TravelClass.AC3] == 64


def test_ut13_segment_overlap():
    assert not overlaps(1, 3, 3, 4)
    assert overlaps(1, 3, 2, 4)


def test_ut14_extra_passengers_are_waitlisted():
    free = coach_berths(TravelClass.SL, "S1", 4)

    plan = plan_allocation(free, [None] * 6, waitlisted_now=0, waitlist_limit=20)

    confirmed = [b for b in plan.berths if b]
    assert len(confirmed) == 4
    assert len(set(confirmed)) == 4
    assert plan.berths[4:] == [None, None]


def test_ut15_berth_preference_is_honoured():
    free = [Berth("S1", 2, MB), Berth("S1", 4, LB)]

    plan = plan_allocation(free, [LB], waitlisted_now=0, waitlist_limit=20)

    assert plan.berths == [Berth("S1", 4, LB)]


def test_ut16_confirm_only_rejects_partial_confirmation():
    free = coach_berths(TravelClass.SL, "S1", 2)

    with pytest.raises(AllocationRejected) as exc:
        plan_allocation(free, [None] * 3, waitlisted_now=0, waitlist_limit=20, confirm_only=True)

    assert exc.value.code == "CONFIRMATION_UNAVAILABLE"


def test_ut17_waitlist_limit_is_enforced():
    with pytest.raises(AllocationRejected) as exc:
        plan_allocation([], [None, None], waitlisted_now=19, waitlist_limit=20)

    assert exc.value.code == "NOT_AVAILABLE"


def test_waitlist_can_be_filled_exactly_to_the_limit():
    plan = plan_allocation([], [None], waitlisted_now=19, waitlist_limit=20)

    assert plan.berths == [None]


def test_group_is_seated_in_the_coach_with_most_free_berths():
    free = coach_berths(TravelClass.SL, "S1", 1) + coach_berths(TravelClass.SL, "S2", 3)

    plan = plan_allocation(free, [None, None, None], waitlisted_now=0, waitlist_limit=20)

    assert {b.coach_code for b in plan.berths if b} == {"S2"}
