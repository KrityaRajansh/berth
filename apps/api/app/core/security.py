import uuid
from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

SESSION_COOKIE = "berth_session"
SESSION_LIFETIME = timedelta(hours=24)
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_session_token(user_id: uuid.UUID, role: str, now: datetime) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + SESSION_LIFETIME).timestamp()),
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=_ALGORITHM)


def decode_session_token(token: str, now: datetime) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[_ALGORITHM],
            # Time claims are checked below against the injected clock, not the system
            # clock, so behaviour is the same in tests and in production.
            options={"verify_exp": False, "verify_iat": False, "verify_nbf": False},
        )
    except jwt.InvalidTokenError:
        return None
    if payload.get("exp", 0) <= now.timestamp():
        return None
    return payload
