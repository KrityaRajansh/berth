"""Start the API on a freshly created and seeded database for end-to-end tests.

    uv run python -m scripts.e2e_server

Uses E2E_DATABASE_URL (default: the local Docker server, database berth_e2e).
The database is dropped and recreated on every start, so it must end in _e2e.
"""

import os

E2E_DATABASE_URL = os.environ.get(
    "E2E_DATABASE_URL", "postgresql+psycopg://berth:berth@localhost:5432/berth_e2e"
)

# Settings are read once, so the environment must be set before importing the app.
os.environ.update(
    {
        "ENVIRONMENT": "development",
        "DATABASE_URL": E2E_DATABASE_URL,
        "JWT_SECRET": "e2e-only-jwt-secret-of-at-least-32-bytes",
        "CRON_SECRET": "e2e-cron-secret",
        "SEED_ADMIN_PASSWORD": os.environ.get("SEED_ADMIN_PASSWORD", "Admin-e2e-123"),
        "SEED_DEMO_PASSWORD": os.environ.get("SEED_DEMO_PASSWORD", "Demo-e2e-123"),
    }
)

from pathlib import Path  # noqa: E402

import uvicorn  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, make_url, text  # noqa: E402

from scripts.seed import seed  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]


def recreate_database() -> None:
    url = make_url(E2E_DATABASE_URL)
    if not (url.database or "").endswith("_e2e"):
        raise SystemExit(f"Refusing to recreate '{url.database}': name must end in _e2e")
    server = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    server.dispose()

    config = Config(str(API_DIR / "alembic.ini"))
    config.attributes["database_url"] = E2E_DATABASE_URL
    command.upgrade(config, "head")


if __name__ == "__main__":
    recreate_database()
    seed()
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
