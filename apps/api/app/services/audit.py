import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent


class AuditLog:
    """Append-only record of booking, payment, cancellation and admin events (NFR-19)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        actor_id: uuid.UUID | None,
        event_type: str,
        entity: str,
        entity_id: object,
        at: datetime,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            AuditEvent(
                actor_id=actor_id,
                event_type=event_type,
                entity=entity,
                entity_id=str(entity_id),
                data=data or {},
                created_at=at,
            )
        )
