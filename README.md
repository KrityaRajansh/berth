# Berth

Online train ticket reservation system. Passengers search trains between stations, check seat availability by class, book tickets, cancel them and download an e-ticket with a PNR. Administrators manage trains, stations and schedules.

Built as the group project for CSC702 Software Engineering (Group 13, Assignment 3).

## Repository layout

```
apps/
  api/           FastAPI backend (Python 3.12, SQLAlchemy, Alembic, PostgreSQL)
    app/
      api/routes/    HTTP routers
      services/      business rules
      repositories/  queries and locking
      models/        database models
      schemas/       request and response models
      jobs/          scheduled jobs
      core/          configuration, database, security
    tests/           unit and integration tests
  web/           React frontend (TypeScript, Vite, Tailwind CSS)
    src/
      features/      pages grouped by feature
      components/    shared components
      routes/        routing
e2e/             end-to-end tests (Playwright)
docs/            SRS, SDD, test plan and report, UML sources
```

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js 22 and [pnpm](https://pnpm.io/)
- Docker (for a local PostgreSQL), or a Neon database
- Java and Edge or Chrome (only to build the PDF documents)

## Running locally

```sh
# Database
docker compose up -d

# API on http://localhost:8000 (docs at /api/docs)
cd apps/api
cp .env.example .env        # then fill in the secrets
uv sync
uv run uvicorn app.main:app --reload

# Web app on http://localhost:5173 (proxies /api to the API)
pnpm install
pnpm dev:web
```

## Tests and checks

```sh
cd apps/api && uv run pytest && uv run ruff check . && uv run ruff format --check .
pnpm test:web && pnpm lint:web
```

## Documents

The SRS, SDD and test plan are written in Markdown under `docs/` with PlantUML diagrams. Build the PDFs into `docs/dist/` with:

```sh
uv run docs/build.py
```

## Team

| Name           | Registration no. |
|----------------|------------------|
| Esha Biswas    | CSE/23047/1095   |
| Krishna Singh  | CSE/23062/1110   |
| Kritya Rajansh | CSE/23063/1111   |
| Nitesh Jha     | CSE/23070/1118   |
