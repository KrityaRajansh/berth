from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import Booking, Payment, Refund
from app.models.enums import PaymentStatus, RefundReason
from app.services.payment_gateway import PaymentGateway


def describe_instrument(method: str, instrument: str) -> str:
    if method == "card":
        return f"Card ending {instrument.replace(' ', '')[-4:]}"
    return instrument.lower()


class PaymentService:
    def __init__(self, session: Session, clock: Clock, gateway: PaymentGateway) -> None:
        self.session = session
        self.clock = clock
        self.gateway = gateway

    def charge(self, booking: Booking, method: str, instrument: str) -> Payment:
        """Charge through the gateway and return the payment record, not yet saved.

        The caller decides when to add it, because a declined charge is saved
        after the booking's tentative allocation has been rolled back.
        """
        result = self.gateway.charge(booking.total_fare_paise, str(booking.id), instrument)
        return Payment(
            booking_id=booking.id,
            amount_paise=booking.total_fare_paise,
            method=method,
            instrument=describe_instrument(method, instrument),
            status=PaymentStatus.SUCCESS if result.approved else PaymentStatus.FAILED,
            gateway_ref=result.reference,
            failure_reason=None if result.approved else result.message,
            created_at=self.clock.now(),
        )

    def refund(self, booking: Booking, amount_paise: int, reason: RefundReason) -> Refund | None:
        if amount_paise <= 0:
            return None
        payment = self.session.scalar(
            select(Payment).where(
                Payment.booking_id == booking.id, Payment.status == PaymentStatus.SUCCESS
            )
        )
        if payment is None or payment.gateway_ref is None:
            raise RuntimeError(f"booking {booking.id} has no successful payment to refund")
        result = self.gateway.refund(payment.gateway_ref, amount_paise)
        refund = Refund(
            booking_id=booking.id,
            payment_id=payment.id,
            amount_paise=amount_paise,
            reason=reason,
            status="PROCESSED" if result.approved else "FAILED",
            gateway_ref=result.reference or "",
            created_at=self.clock.now(),
        )
        self.session.add(refund)
        return refund
