import logging
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import JobRun
from app.models.enums import JobStatus
from app.services.payment_gateway import PaymentGateway

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobContext:
    session: Session
    clock: Clock
    gateway: PaymentGateway


class Job(Protocol):
    name: str

    def execute(self, ctx: JobContext) -> int:
        """Do the work and return how many items were processed."""
        ...


class JobRunner:
    """Runs a job and records the outcome in job_run (FR-JOB-06)."""

    def __init__(self, ctx: JobContext) -> None:
        self.ctx = ctx

    def run(self, job: Job, triggered_by: str) -> JobRun:
        session, clock = self.ctx.session, self.ctx.clock
        record = JobRun(
            job_name=job.name,
            triggered_by=triggered_by,
            started_at=clock.now(),
            status=JobStatus.RUNNING,
        )
        session.add(record)
        session.commit()
        try:
            processed = job.execute(self.ctx)
        except Exception as exc:
            session.rollback()
            log.exception("job %s failed", job.name)
            record.status = JobStatus.FAILED
            record.detail = f"{type(exc).__name__}: {exc}"[:500]
        else:
            record.status = JobStatus.SUCCEEDED
            record.items_processed = processed
        record.finished_at = clock.now()
        session.commit()
        return record
