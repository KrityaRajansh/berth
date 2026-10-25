"""Endpoints called by the cron scheduler (SR-05). Protected by CRON_SECRET."""

from fastapi import APIRouter, Depends

from app.api.deps import ClockDep, GatewayDep, SessionDep, verify_cron_secret
from app.jobs.runner import JobContext, JobRunner
from app.jobs.tasks import JOBS, NIGHTLY
from app.schemas.admin import JobRunOut

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_cron_secret)])


@router.get("/chart-preparation")
def chart_preparation(session: SessionDep, clock: ClockDep, gateway: GatewayDep) -> JobRunOut:
    runner = JobRunner(JobContext(session, clock, gateway))
    return JobRunOut.model_validate(runner.run(JOBS["chart-preparation"], triggered_by="cron"))


@router.get("/nightly")
def nightly(session: SessionDep, clock: ClockDep, gateway: GatewayDep) -> list[JobRunOut]:
    runner = JobRunner(JobContext(session, clock, gateway))
    return [
        JobRunOut.model_validate(runner.run(JOBS[name], triggered_by="cron")) for name in NIGHTLY
    ]
