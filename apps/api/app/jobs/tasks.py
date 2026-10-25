"""Scheduled jobs (SDD 3.5). Each is idempotent: it only touches rows still in the
state it changes, so running it twice has no further effect (FR-JOB-05)."""

from datetime import timedelta

from sqlalchemy import select

from app.core.clock import IST, today_ist
from app.jobs.runner import Job, JobContext
from app.models import Booking
from app.models.enums import BookingStatus, RunStatus
from app.repositories.bookings import BookingRepository
from app.repositories.runs import RunRepository
from app.services.cancellation import CancellationService
from app.services.runs import RunService
from app.services.schedule import ADVANCE_RESERVATION_DAYS, stop_arrival_at


class RunGenerationJob:
    name = "run-generation"

    def execute(self, ctx: JobContext) -> int:
        today = today_ist(ctx.clock)
        return RunService(ctx.session).generate(
            today, today + timedelta(days=ADVANCE_RESERVATION_DAYS)
        )


class ChartPreparationJob:
    name = "chart-preparation"

    def execute(self, ctx: JobContext) -> int:
        # A run starting on D is due once 18:00 IST on D-1 has passed, i.e. when
        # D <= (now + 6 h) as an IST date. Earlier, missed runs are caught up too.
        last_due = (ctx.clock.now().astimezone(IST) + timedelta(hours=6)).date()
        service = CancellationService(ctx.session, ctx.clock, ctx.gateway)
        return sum(
            service.prepare_chart(run)
            for run in RunRepository(ctx.session).scheduled_up_to(last_due)
        )


class JourneyCompletionJob:
    name = "journey-completion"

    def execute(self, ctx: JobContext) -> int:
        now = ctx.clock.now()
        completed = 0
        for run in RunRepository(ctx.session).chart_prepared_up_to(today_ist(ctx.clock)):
            if stop_arrival_at(run.run_date, run.train.stops[-1]) > now:
                continue
            run.status = RunStatus.COMPLETED
            bookings = ctx.session.scalars(
                select(Booking).where(
                    Booking.run_id == run.id, Booking.status == BookingStatus.BOOKED
                )
            )
            for booking in bookings:
                booking.status = BookingStatus.COMPLETED
            completed += 1
        ctx.session.commit()
        return completed


class PaymentExpiryJob:
    name = "payment-expiry"

    def execute(self, ctx: JobContext) -> int:
        expired = BookingRepository(ctx.session).expire_pending(ctx.clock.now())
        ctx.session.commit()
        return expired


JOBS: dict[str, Job] = {
    job.name: job
    for job in (
        RunGenerationJob(),
        ChartPreparationJob(),
        JourneyCompletionJob(),
        PaymentExpiryJob(),
    )
}

# The nightly trigger runs these in order; chart preparation is repeated as a catch-up.
NIGHTLY = ("run-generation", "chart-preparation", "journey-completion", "payment-expiry")
