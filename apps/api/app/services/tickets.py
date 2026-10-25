import re
import uuid

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.errors import Conflict, InvalidInput, NotFound
from app.models import User
from app.repositories.bookings import BookingRepository
from app.schemas.booking import PnrStatusOut
from app.services.ticket_pdf import render_ticket
from app.services.views import BookingPresenter


class TicketService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self.clock = clock
        self.bookings = BookingRepository(session)
        self.presenter = BookingPresenter(session)

    def pdf(self, booking_id: uuid.UUID, user: User) -> tuple[str, bytes]:
        booking = self.bookings.get(booking_id)
        if booking is None or booking.user_id != user.id:
            raise NotFound("Booking not found.")
        if booking.pnr is None:
            raise Conflict("The ticket is available once payment succeeds.", code="NOT_TICKETED")
        detail = self.presenter.detail(booking, self.clock.now())
        return f"berth-ticket-{booking.pnr}.pdf", render_ticket(detail)

    def pnr_status(self, pnr: str) -> PnrStatusOut:
        if not re.fullmatch(r"\d{10}", pnr):
            raise InvalidInput("A PNR has 10 digits.", code="INVALID_PNR")
        booking = self.bookings.by_pnr(pnr)
        if booking is None:
            raise NotFound("No booking found for this PNR.")
        return self.presenter.pnr_status(booking)
