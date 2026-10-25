import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import ClockDep, CurrentUser, GatewayDep, SessionDep
from app.schemas.booking import (
    BookingCreate,
    BookingOut,
    BookingSummary,
    CancellationRequest,
    PaymentRequest,
    RefundQuote,
)
from app.services.booking import BookingService
from app.services.cancellation import CancellationService
from app.services.tickets import TicketService
from app.services.views import BookingPresenter

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_booking(
    body: BookingCreate,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    gateway: GatewayDep,
) -> BookingOut:
    booking = BookingService(session, clock, gateway).create(user, body)
    return BookingPresenter(session).detail(booking, clock.now())


@router.get("")
def list_bookings(
    user: CurrentUser, session: SessionDep, clock: ClockDep, gateway: GatewayDep
) -> list[BookingSummary]:
    presenter = BookingPresenter(session)
    return [presenter.summary(b) for b in BookingService(session, clock, gateway).list_for(user)]


@router.get("/{booking_id}")
def get_booking(
    booking_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    gateway: GatewayDep,
) -> BookingOut:
    booking = BookingService(session, clock, gateway).get(booking_id, user)
    return BookingPresenter(session).detail(booking, clock.now())


@router.post("/{booking_id}/payments")
def pay_for_booking(
    booking_id: uuid.UUID,
    body: PaymentRequest,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    gateway: GatewayDep,
) -> BookingOut:
    booking = BookingService(session, clock, gateway).pay(booking_id, user, body)
    return BookingPresenter(session).detail(booking, clock.now())


@router.post("/{booking_id}/cancellation-quote")
def cancellation_quote(
    booking_id: uuid.UUID,
    body: CancellationRequest,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    gateway: GatewayDep,
) -> RefundQuote:
    return CancellationService(session, clock, gateway).quote(booking_id, user, body.passenger_ids)


@router.post("/{booking_id}/cancellations")
def cancel_passengers(
    booking_id: uuid.UUID,
    body: CancellationRequest,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    gateway: GatewayDep,
) -> BookingOut:
    booking = CancellationService(session, clock, gateway).cancel(
        booking_id, user, body.passenger_ids
    )
    return BookingPresenter(session).detail(booking, clock.now())


@router.get("/{booking_id}/ticket.pdf", response_class=Response)
def download_ticket(
    booking_id: uuid.UUID, user: CurrentUser, session: SessionDep, clock: ClockDep
) -> Response:
    filename, content = TicketService(session, clock).pdf(booking_id, user)
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
