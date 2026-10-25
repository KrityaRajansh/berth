from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class Role(StrEnum):
    PASSENGER = "PASSENGER"
    ADMIN = "ADMIN"


class TravelClass(StrEnum):
    SL = "SL"
    AC3 = "3A"
    AC2 = "2A"
    AC1 = "1A"


class BerthType(StrEnum):
    LB = "LB"
    MB = "MB"
    UB = "UB"
    SL = "SL"
    SU = "SU"


class Gender(StrEnum):
    M = "M"
    F = "F"
    T = "T"


class RunStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    CHART_PREPARED = "CHART_PREPARED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BookingStatus(StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    BOOKED = "BOOKED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class PassengerStatus(StrEnum):
    CNF = "CNF"
    WL = "WL"
    CAN = "CAN"


class PaymentStatus(StrEnum):
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RefundReason(StrEnum):
    USER_CANCELLATION = "USER_CANCELLATION"
    CHART_PREPARED = "CHART_PREPARED"
    RUN_CANCELLED = "RUN_CANCELLED"


class JobStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


def db_enum(enum_cls: type[StrEnum]) -> SAEnum:
    """Store enums as their string values in a VARCHAR column."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )
