from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, ClockDep, GatewayDep, SessionDep
from app.core.errors import NotFound
from app.jobs.runner import JobContext, JobRunner
from app.jobs.tasks import JOBS
from app.repositories.network import StationRepository, TrainRepository
from app.schemas.admin import (
    ChartRow,
    GenerateRunsRequest,
    GenerateRunsResult,
    JobRunOut,
    RunOut,
    StatsOut,
)
from app.schemas.network import CoachIn, RouteStopIn, StationIn, StationOut, TrainIn, TrainOut
from app.services.admin import AdminService
from app.services.cancellation import CancellationService
from app.services.network import NetworkService, train_out
from app.services.runs import RunService

router = APIRouter(prefix="/admin", tags=["admin"])


# Stations


@router.get("/stations")
def list_stations(_: AdminUser, session: SessionDep) -> list[StationOut]:
    return [StationOut.model_validate(s) for s in StationRepository(session).all()]


@router.post("/stations", status_code=status.HTTP_201_CREATED)
def create_station(body: StationIn, _: AdminUser, session: SessionDep) -> StationOut:
    return StationOut.model_validate(NetworkService(session).create_station(body))


@router.put("/stations/{station_id}")
def update_station(
    station_id: int, body: StationIn, _: AdminUser, session: SessionDep
) -> StationOut:
    return StationOut.model_validate(NetworkService(session).update_station(station_id, body))


# Trains


@router.get("/trains")
def list_trains(_: AdminUser, session: SessionDep) -> list[TrainOut]:
    return [train_out(t) for t in TrainRepository(session).all()]


@router.post("/trains", status_code=status.HTTP_201_CREATED)
def create_train(body: TrainIn, _: AdminUser, session: SessionDep) -> TrainOut:
    return train_out(NetworkService(session).create_train(body))


@router.get("/trains/{number}")
def get_train(number: str, _: AdminUser, session: SessionDep) -> TrainOut:
    return train_out(NetworkService(session).get_train(number))


@router.put("/trains/{number}")
def update_train(number: str, body: TrainIn, _: AdminUser, session: SessionDep) -> TrainOut:
    return train_out(NetworkService(session).update_train(number, body))


@router.put("/trains/{number}/route")
def set_route(number: str, body: list[RouteStopIn], _: AdminUser, session: SessionDep) -> TrainOut:
    return train_out(NetworkService(session).set_route(number, body))


@router.put("/trains/{number}/coaches")
def set_coaches(number: str, body: list[CoachIn], _: AdminUser, session: SessionDep) -> TrainOut:
    return train_out(NetworkService(session).set_coaches(number, body))


# Train runs


@router.get("/runs")
def list_runs(
    _: AdminUser,
    session: SessionDep,
    run_date: Annotated[date | None, Query(alias="date")] = None,
    train: str | None = None,
) -> list[RunOut]:
    return AdminService(session).list_runs(run_date, train)


@router.post("/runs/generate")
def generate_runs(
    body: GenerateRunsRequest, _: AdminUser, session: SessionDep
) -> GenerateRunsResult:
    created = RunService(session).generate(body.start, body.end, body.train_number)
    return GenerateRunsResult(created=created)


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: int, admin: AdminUser, session: SessionDep, clock: ClockDep, gateway: GatewayDep
) -> dict[str, int]:
    affected = CancellationService(session, clock, gateway).cancel_run(run_id, admin)
    return {"bookings_cancelled": affected}


@router.get("/runs/{run_id}/chart")
def passenger_chart(run_id: int, _: AdminUser, session: SessionDep) -> list[ChartRow]:
    return AdminService(session).chart(run_id)


# Jobs and dashboard


@router.get("/jobs")
def job_history(_: AdminUser, session: SessionDep) -> list[JobRunOut]:
    return [JobRunOut.model_validate(j) for j in AdminService(session).job_history()]


@router.post("/jobs/{name}/run")
def run_job(
    name: str, _: AdminUser, session: SessionDep, clock: ClockDep, gateway: GatewayDep
) -> JobRunOut:
    job = JOBS.get(name)
    if job is None:
        raise NotFound(f"Unknown job {name}.")
    record = JobRunner(JobContext(session, clock, gateway)).run(job, triggered_by="admin")
    return JobRunOut.model_validate(record)


@router.get("/stats")
def stats(
    _: AdminUser,
    session: SessionDep,
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
) -> StatsOut:
    return AdminService(session).stats(start, end)
