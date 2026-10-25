import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import LoginAttempt, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def email_or_mobile_taken(self, email: str, mobile: str) -> bool:
        stmt = select(User.id).where(or_(User.email == email.lower(), User.mobile == mobile))
        return self.session.scalar(stmt.limit(1)) is not None

    def mobile_taken_by_other(self, mobile: str, user_id: uuid.UUID) -> bool:
        stmt = select(User.id).where(User.mobile == mobile, User.id != user_id)
        return self.session.scalar(stmt.limit(1)) is not None

    def failed_logins_since(self, email: str, since: datetime) -> int:
        stmt = select(func.count()).where(
            LoginAttempt.email == email.lower(),
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.attempted_at > since,
        )
        return self.session.scalar(stmt) or 0

    def record_login(self, email: str, succeeded: bool, at: datetime) -> None:
        self.session.add(LoginAttempt(email=email.lower(), succeeded=succeeded, attempted_at=at))
