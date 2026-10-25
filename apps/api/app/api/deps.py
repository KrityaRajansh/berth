import hmac
import uuid
from typing import Annotated

from fastapi import Depends, Header, Request, Response
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthorized
from app.core.security import SESSION_COOKIE, SESSION_LIFETIME, decode_session_token
from app.models import User
from app.models.enums import Role
from app.repositories.users import UserRepository
from app.services.payment_gateway import PaymentGateway, get_payment_gateway

SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
GatewayDep = Annotated[PaymentGateway, Depends(get_payment_gateway)]


def optional_user(request: Request, session: SessionDep, clock: ClockDep) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    payload = decode_session_token(token, clock.now())
    if payload is None:
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        return None
    return UserRepository(session).get(user_id)


def current_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if user is None:
        raise Unauthorized("Please log in to continue.")
    return user


def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != Role.ADMIN:
        raise Forbidden("Administrator access is required.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(admin_user)]


def verify_cron_secret(authorization: Annotated[str | None, Header()] = None) -> None:
    secret = get_settings().cron_secret
    if not secret or not hmac.compare_digest(authorization or "", f"Bearer {secret}"):
        raise Unauthorized("Invalid scheduler credentials.")


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=get_settings().environment == "production",
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
