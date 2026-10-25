# Berth

Online train ticket reservation system. Passengers search trains between stations, check seat availability by class, book tickets, cancel them and download an e-ticket with a PNR. Administrators manage trains, stations and schedules.

Built as the group project for CSC702 Software Engineering (Group 13, Assignment 3).

**Live site:** https://berth-76rn.vercel.app (API at https://berth-ebon.vercel.app/api/docs). Payments are simulated: card `4111 1111 1111 1111` or UPI `success@berth` approves, card `4000 0000 0000 0002` or UPI `failure@berth` declines.

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

1. Copy `apps/api/.env.example` to `apps/api/.env` and fill in `DATABASE_URL` (local Docker or Neon) and the secrets.
2. Install and prepare:

   ```sh
   pnpm install
   cd apps/api
   uv sync
   uv run alembic upgrade head
   uv run python -m scripts.seed
   ```

3. From the repository root, start the API (http://localhost:8000, docs at `/api/docs`) and the web app (http://localhost:5173) together:

   ```sh
   pnpm dev
   ```

For a local database instead of Neon, run `docker compose up -d` first.

## Tests and checks

```sh
pnpm test:api     # unit and integration tests (needs the Docker database)
pnpm test:web     # frontend unit tests
pnpm test:e2e     # Playwright end-to-end tests (needs the Docker database)
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
