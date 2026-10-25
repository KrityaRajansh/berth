from fractions import Fraction
from math import floor


def round_to_rupee(paise: int | Fraction) -> int:
    """Round an amount in paise to the nearest whole rupee, halves rounding up."""
    return floor(Fraction(paise) / 100 + Fraction(1, 2)) * 100


def percent_of(paise: int, percent: int) -> int:
    """`percent`% of an amount, rounded to the nearest paisa (halves up)."""
    return floor(Fraction(paise * percent, 100) + Fraction(1, 2))


def format_inr(paise: int) -> str:
    rupees, rem = divmod(paise, 100)
    return f"₹{rupees:,}" if rem == 0 else f"₹{rupees:,}.{rem:02d}"
