"""IT-36: parallel payments competing for the last berth (NFR-03, FR-BKG-07).

Unlike the other integration tests this one commits for real, because the point
is to have several database connections race each other. It empties the tables
afterwards so the rest of the suite starts clean.
"""

import threading
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import FixedClock
from app.models import Base, Passenger, User
from app.models.enums import PassengerStatus, TravelClass
from app.schemas.booking import BookingCreate, PassengerIn, PaymentRequest
from app.services.booking import BookingService
from app.services.payment_gateway import MockPaymentGateway
from app.services.runs import RunService
from tests.integration.conftest import MONDAY, START
from tests.integration.support import APPROVE_CARD, build_network, resize, run_class

PARALLEL = 10


@pytest.fixture
def committed(engine: Engine) -> Iterator[sessionmaker[Session]]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def test_it36_parallel_payments_for_the_last_berth(committed):
    clock = FixedClock(START)
    with committed() as setup:
        build_network(setup)
        RunService(setup).generate(MONDAY, MONDAY)
        sl = run_class(setup, "90001", MONDAY, TravelClass.SL)
        resize(setup, sl, 1)
        user = setup.scalar(select(User).where(User.email == "passenger1@example.com"))
        service = BookingService(setup, clock, MockPaymentGateway())
        request = BookingCreate(
            run_id=sl.run_id,
            travel_class=TravelClass.SL,
            from_code="STA",
            to_code="STD",
            passengers=[PassengerIn(name="Racer", age=30, gender="M")],
        )
        booking_ids = [service.create(user, request).id for _ in range(PARALLEL)]
        run_class_id = sl.id

    start = threading.Barrier(PARALLEL)
    errors: list[BaseException] = []

    def pay(booking_id) -> None:
        with committed() as session:
            service = BookingService(session, clock, MockPaymentGateway())
            start.wait()
            try:
                service.pay(
                    booking_id, user, PaymentRequest(method="card", card_number=APPROVE_CARD)
                )
            except BaseException as exc:  # collected and asserted below
                errors.append(exc)

    threads = [threading.Thread(target=pay, args=(b,)) for b in booking_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert errors == []
    with committed() as check:
        passengers = check.scalars(
            select(Passenger).where(Passenger.run_class_id == run_class_id)
        ).all()
    confirmed = [p for p in passengers if p.status == PassengerStatus.CNF]
    waitlisted = [p for p in passengers if p.status == PassengerStatus.WL]
    assert len(confirmed) == 1
    assert (confirmed[0].coach_code, confirmed[0].berth_no) == ("S1", 1)
    assert len(waitlisted) == PARALLEL - 1
    assert sorted(p.wl_seq for p in waitlisted) == list(range(1, PARALLEL))
