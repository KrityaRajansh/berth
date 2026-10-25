from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    options: dict[str, Any] = {
        "pool_pre_ping": True,
        # Neon's pooler runs PgBouncer in transaction mode, where server-side
        # prepared statements are not safe to reuse across transactions.
        "connect_args": {"prepare_threshold": None},
    }
    if settings.environment == "production":
        # Each serverless instance is short-lived; Neon does the pooling.
        options["poolclass"] = NullPool
    return create_engine(settings.database_url, **options)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with get_sessionmaker()() as session:
        yield session
