import os
from collections.abc import Callable, Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from app.core.clock import IST, FixedClock, get_clock
from app.core.db import get_session
from app.main import app
from app.services.runs import RunService
from tests.integration.support import Api, build_network

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://berth:berth@localhost:5432/berth_test"
)
API_DIR = Path(__file__).resolve().parents[2]

# Sunday 1 November 2026, 06:00 IST. The Monday run of train 90001 departs in
# 24 hours and the Wednesday run in 72 hours.
START = datetime(2026, 11, 1, 6, 0, tzinfo=IST)
MONDAY = date(2026, 11, 2)
TUESDAY = date(2026, 11, 3)
WEDNESDAY = date(2026, 11, 4)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    database = make_url(TEST_DATABASE_URL).database or ""
    if not database.endswith("_test"):
        pytest.exit(f"Refusing to run integration tests against '{database}'", returncode=2)
    engine = create_engine(TEST_DATABASE_URL, connect_args={"prepare_threshold": None})
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config(str(API_DIR / "alembic.ini"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session whose commits become savepoints; everything is rolled back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(START)


@pytest.fixture
def network(db: Session) -> None:
    build_network(db)


@pytest.fixture
def runs(network: None, db: Session) -> None:
    RunService(db).generate(START.date(), START.date() + timedelta(days=60))


@pytest.fixture
def make_api(db: Session, clock: FixedClock) -> Iterator[Callable[[], Api]]:
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_clock] = lambda: clock
    yield lambda: Api(TestClient(app))
    app.dependency_overrides.clear()


@pytest.fixture
def guest(make_api: Callable[[], Api]) -> Api:
    return make_api()


@pytest.fixture
def p1(make_api: Callable[[], Api], network: None) -> Api:
    return make_api().login("passenger1@example.com")


@pytest.fixture
def p2(make_api: Callable[[], Api], network: None) -> Api:
    return make_api().login("passenger2@example.com")


@pytest.fixture
def admin(make_api: Callable[[], Api], network: None) -> Api:
    return make_api().login("admin@example.com")
