"""Payment gateway adapter (SR-04). The delivered system uses the mock gateway."""

import secrets
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GatewayResult:
    approved: bool
    reference: str | None
    message: str


class PaymentGateway(Protocol):
    def charge(self, amount_paise: int, reference: str, instrument: str) -> GatewayResult: ...

    def refund(self, gateway_ref: str, amount_paise: int) -> GatewayResult: ...


class MockPaymentGateway:
    """Behaves like a real gateway for a fixed set of test cards and UPI IDs."""

    APPROVE = frozenset({"4111111111111111", "success@berth"})
    DECLINE = frozenset({"4000000000000002", "failure@berth"})

    @staticmethod
    def normalise(instrument: str) -> str:
        return instrument.replace(" ", "").replace("-", "").lower()

    def charge(self, amount_paise: int, reference: str, instrument: str) -> GatewayResult:
        key = self.normalise(instrument)
        if key in self.APPROVE:
            return GatewayResult(True, f"PAY-{secrets.token_hex(6).upper()}", "Approved")
        if key in self.DECLINE:
            return GatewayResult(False, None, "Declined by the issuing bank.")
        return GatewayResult(False, None, "Unknown test card or UPI ID.")

    def refund(self, gateway_ref: str, amount_paise: int) -> GatewayResult:
        return GatewayResult(True, f"RFD-{secrets.token_hex(6).upper()}", "Refunded")


def get_payment_gateway() -> PaymentGateway:
    return MockPaymentGateway()
