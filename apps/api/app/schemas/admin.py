from datetime import date

from pydantic import model_validator

from app.models.enums import JobStatus, RunStatus, TravelClass
from app.schemas.common import IstDatetime, Schema


class RunClassOut(Schema):
    travel_class: TravelClass
    berth_capacity: int
    confirmed: int
    waitlisted: int


class RunOut(Schema):
    id: int
    train_number: str
    train_name: str
    run_date: date
    status: RunStatus
    chart_prepared_at: IstDatetime | None
    classes: list[RunClassOut]


class GenerateRunsRequest(Schema):
    start: date
    end: date
    train_number: str | None = None

    @model_validator(mode="after")
    def ordered(self) -> "GenerateRunsRequest":
        if self.end < self.start:
            raise ValueError("End date must not be before start date.")
        if (self.end - self.start).days > 90:
            raise ValueError("Generate at most 90 days at a time.")
        return self


class GenerateRunsResult(Schema):
    created: int


class ChartRow(Schema):
    pnr: str
    passenger: str
    age: int
    gender: str
    travel_class: TravelClass
    from_code: str
    to_code: str
    status: str
    coach_code: str | None
    berth_no: int | None
    berth_type: str | None


class JobRunOut(Schema):
    id: int
    job_name: str
    triggered_by: str
    started_at: IstDatetime
    finished_at: IstDatetime | None
    status: JobStatus
    items_processed: int
    detail: str | None


class StatsOut(Schema):
    start: date
    end: date
    bookings: int
    passengers: int
    cancellations: int
    revenue_paise: int
    refunds_paise: int
