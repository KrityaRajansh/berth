"""Berth allocation planning (FR-BKG-05 to 09, BR-05).

This module is pure: it decides who gets which free berth, given the free
berths for a segment. Finding the free berths and saving the result is done
by the booking and waitlist services while holding the inventory lock.
"""

from collections import Counter
from dataclasses import dataclass

from app.models.enums import BerthType
from app.services.layout import Berth


class AllocationRejected(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AllocationPlan:
    # One entry per passenger, in passenger order; None means waitlisted.
    berths: list[Berth | None]

    @property
    def waitlisted_count(self) -> int:
        return sum(1 for b in self.berths if b is None)


def choose_berth(
    free: list[Berth], preference: BerthType | None, coach: str | None
) -> Berth | None:
    if not free:
        return None
    same_coach = [b for b in free if b.coach_code == coach] if coach else []
    if preference:
        for pool in (same_coach, free):
            for berth in pool:
                if berth.berth_type == preference:
                    return berth
    return same_coach[0] if same_coach else free[0]


def plan_allocation(
    free: list[Berth],
    preferences: list[BerthType | None],
    *,
    waitlisted_now: int,
    waitlist_limit: int,
    confirm_only: bool = False,
) -> AllocationPlan:
    remaining = sorted(free)
    # Seat a group together: start in the coach with the most free berths.
    coach = None
    if len(preferences) > 1 and remaining:
        coach = Counter(b.coach_code for b in remaining).most_common(1)[0][0]

    chosen: list[Berth | None] = []
    for preference in preferences:
        berth = choose_berth(remaining, preference, coach)
        if berth is not None:
            remaining.remove(berth)
            coach = coach or berth.coach_code
        chosen.append(berth)

    plan = AllocationPlan(chosen)
    if confirm_only and plan.waitlisted_count:
        raise AllocationRejected(
            "CONFIRMATION_UNAVAILABLE",
            "Not enough confirmed berths for every passenger.",
        )
    if waitlisted_now + plan.waitlisted_count > waitlist_limit:
        raise AllocationRejected(
            "NOT_AVAILABLE",
            "Not enough berths or waitlist places for every passenger.",
        )
    return plan
