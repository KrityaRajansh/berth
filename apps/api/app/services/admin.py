from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import ist
from app.core.errors import NotFound
from app.models import Booking, JobRun, Passenger, Payment, Refund, Station
from app.models.enums import BookingStatus, PassengerStatus, PaymentStatus
from app.repositories.inventory import InventoryRepository
from app.repositories.runs import RunRepository
from app.schemas.admin import ChartRow, RunClassOut, RunOut, StatsOut


class AdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.runs = RunRepository(session)
        self.inventory = InventoryRepository(session)

    def list_runs(self, run_date: date | None, train_number: str | None) -> list[RunOut]:
        return [
            RunOut(
                id=run.id,
                train_number=run.train.number,
                train_name=run.train.name,
                run_date=run.run_date,
                status=run.status,
                chart_prepared_at=run.chart_prepared_at,
                classes=[
                    RunClassOut(
                        travel_class=c.travel_class,
                        berth_capacity=c.berth_capacity,
                        confirmed=self.inventory.confirmed_count(c.id),
                        waitlisted=self.inventory.waitlist_count(c.id),
                    )
                    for c in run.classes
                ],
            )
            for run in self.runs.list(run_date, train_number)
        ]

    def chart(self, run_id: int) -> list[ChartRow]:
        """Passenger chart of a run (FR-ADM-06)."""
        if self.runs.get(run_id) is None:
            raise NotFound("Train run not found.")
        from_station = select(Station.code).where(Station.id == Booking.from_station_id)
        to_station = select(Station.code).where(Station.id == Booking.to_station_id)
        stmt = (
            select(
                Booking.pnr,
                Passenger,
                Booking.travel_class,
                from_station.scalar_subquery(),
                to_station.scalar_subquery(),
            )
            .join(Booking, Booking.id == Passenger.booking_id)
            .where(Booking.run_id == run_id, Passenger.status.is_not(None))
            .order_by(
                Booking.travel_class, Passenger.coach_code, Passenger.berth_no, Passenger.wl_seq
            )
        )
        return [
            ChartRow(
                pnr=pnr or "",
                passenger=p.name,
                age=p.age,
                gender=p.gender,
                travel_class=cls,
                from_code=from_code,
                to_code=to_code,
                status=str(p.status),
                coach_code=p.coach_code,
                berth_no=p.berth_no,
                berth_type=p.berth_type,
            )
            for pnr, p, cls, from_code, to_code in self.session.execute(stmt)
        ]

    def stats(self, start: date, end: date) -> StatsOut:
        """Dashboard figures for bookings made between start and end, inclusive (FR-ADM-08)."""
        since: datetime = ist(start, datetime.min.time())
        until: datetime = ist(end + timedelta(days=1), datetime.min.time())
        paid = select(Booking.id).where(
            Booking.created_at >= since,
            Booking.created_at < until,
            Booking.status.in_(
                (BookingStatus.BOOKED, BookingStatus.CANCELLED, BookingStatus.COMPLETED)
            ),
        )
        bookings = self.session.scalar(select(func.count()).select_from(paid.subquery())) or 0
        passengers = self.session.scalar(select(func.count()).where(Passenger.booking_id.in_(paid)))
        cancellations = self.session.scalar(
            select(func.count()).where(
                Passenger.booking_id.in_(paid), Passenger.status == PassengerStatus.CAN
            )
        )
        revenue = self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(
                Payment.status == PaymentStatus.SUCCESS,
                Payment.created_at >= since,
                Payment.created_at < until,
            )
        )
        refunds = self.session.scalar(
            select(func.coalesce(func.sum(Refund.amount_paise), 0)).where(
                Refund.created_at >= since, Refund.created_at < until
            )
        )
        return StatsOut(
            start=start,
            end=end,
            bookings=bookings,
            passengers=passengers or 0,
            cancellations=cancellations or 0,
            revenue_paise=revenue or 0,
            refunds_paise=refunds or 0,
        )

    def job_history(self, limit: int = 50) -> list[JobRun]:
        stmt = select(JobRun).order_by(JobRun.started_at.desc(), JobRun.id.desc()).limit(limit)
        return list(self.session.scalars(stmt))
