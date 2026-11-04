---
title: Software Design Document
subtitle: "Berth: Online Train Ticket Reservation System"
version: 1.1
date: 4 November 2026
---

# 1. Introduction

## 1.1 Purpose

This document describes how Berth is designed to meet the requirements in the Software Requirements Specification (SRS) v1.0. It covers the architecture, the modules and their responsibilities, the data design, and the UML models (class, use case, sequence and state diagrams). Requirement identifiers such as `FR-BKG-05` and `BR-06` refer to the SRS.

## 1.2 Design goals

| Goal | How the design addresses it |
|---|---|
| Correct berth inventory (OBJ-3, NFR-03) | Row-level locking per train run and class, plus a database exclusion constraint that rejects overlapping berth allocations |
| Business rules in one place (NFR-14) | All fare, refund, waitlist and cut-off rules live in the service layer; routers and the UI only call services |
| Free to run (NFR-20) | Static frontend and serverless API on Vercel Hobby, PostgreSQL on Neon free plan, daily cron jobs |
| Testable (NFR-15) | Services depend on small interfaces (repositories, payment gateway, clock) that tests can replace |

# 2. System Architecture

## 2.1 Architectural style

Berth uses a **three-tier client-server architecture** with a **layered backend**:

1. **Presentation tier:** a React single-page application (SPA) running in the browser.
2. **Application tier:** a FastAPI application exposing a JSON REST API under `/api/v1`. Inside it, requests pass through four layers, each depending only on the layer below:
    - **Routers** handle HTTP, request validation, authentication and response shaping.
    - **Services** hold all business rules and own database transactions.
    - **Repositories** contain queries, including the locking queries.
    - **Models** map tables to Python classes (SQLAlchemy ORM).
3. **Data tier:** a PostgreSQL database.

Two external actors interact with the API: the **payment gateway** (called through an adapter interface, mocked in this delivery) and the **cron scheduler**, which triggers time-based jobs over HTTPS.

<figure>
<img src="diagrams/component.svg" alt="Component diagram">
<figcaption>Figure 2.1: Component diagram</figcaption>
</figure>

## 2.2 Deployment

The web client is built into static files served from Vercel's CDN. The API runs as a Python serverless function on Vercel. The web project forwards every `/api/*` request to the API, so the browser sees a single origin; this keeps session cookies first-party and avoids cross-origin requests. Vercel Cron calls the job endpoints with a secret bearer token. The database is a Neon PostgreSQL instance reached through its connection-pooling endpoint, which suits short-lived serverless functions.

<figure>
<img src="diagrams/deployment.svg" alt="Deployment diagram">
<figcaption>Figure 2.2: Deployment diagram</figcaption>
</figure>

## 2.3 Repository structure

The code is kept in one repository (monorepo) with separate applications for the API and the web client:

```
berth/
  apps/
    api/                 FastAPI backend
      app/
        api/routes/      routers (HTTP layer)
        services/        business rules
        repositories/    queries and locking
        models/          SQLAlchemy models
        schemas/         Pydantic request and response models
        jobs/            scheduled jobs and job runner
        core/            configuration, database session, security, clock
      migrations/        Alembic migrations
      tests/             unit and integration tests
    web/                 React frontend
      src/
        api/             generated API client and query hooks
        features/        auth, search, booking, bookings, pnr, admin
        components/      shared UI components
        routes/          page routing
  e2e/                   Playwright end-to-end tests
  docs/                  SRS, SDD, test documents, UML sources
```

# 3. Module and Component Description

## 3.1 Backend modules

| Module | Responsibility | Main components | Requirements |
|---|---|---|---|
| Auth | Registration, login, logout, profile, password change, role checks, login rate limiting | `AuthService`, `PasswordHasher` (bcrypt), `TokenService` (signed JWT in cookie), `current_user` and `require_admin` dependencies | FR-AUTH-01 to 07, NFR-05, 06, 08, 10 |
| Stations | Station lookup and administration | `StationService`, `StationRepository` | FR-SRCH-01, FR-ADM-01 |
| Trains | Trains, routes (ordered stops), coach composition | `TrainService`, `TrainRepository` | FR-ADM-02, 03 |
| Search | Find runs serving a segment on a date | `SearchService` | FR-SRCH-02 to 06 |
| Inventory | Berth layout, free berths for a segment, allocation plans, availability | `CoachLayout`, `BerthAllocator`, `AvailabilityService`, `InventoryRepository` | FR-AVL-01, 02, 05, FR-BKG-05, 07, 09 |
| Fares | Fare and refund calculation | `FareCalculator`, `RefundPolicy` | FR-AVL-03, 04, FR-CAN-03, BR-04, BR-06 |
| Booking | Create bookings, take payment, allocate, assign PNR | `BookingService`, `BookingRepository`, `PnrGenerator` | FR-BKG-01 to 08, FR-TKT-01, 02, 04 |
| Payment | Charge and refund through a gateway adapter; record payments and refunds | `PaymentService`, `PaymentGateway` (interface), `MockPaymentGateway` | FR-PAY-01 to 05 |
| Cancellation | Refund quotes, full or partial cancellation, train run cancellation | `CancellationService` | FR-CAN-01 to 05, FR-ADM-05 |
| Waitlist | Waitlist ordering, current position, promotion | `WaitlistService` | FR-WL-01 to 03, BR-07 |
| Tickets | PDF e-ticket with QR code, public PNR status | `TicketService`, `TicketPdfRenderer` | FR-TKT-03, 05 |
| Jobs | Run generation, chart preparation, journey completion, payment expiry | `JobRunner`, `Job` implementations | FR-JOB-01 to 06, FR-WL-04, FR-ADM-07 |
| Admin | Train runs, passenger chart, dashboard | `AdminService` | FR-ADM-04 to 08 |
| Audit | Append-only event log | `AuditLog` | NFR-19 |

## 3.2 Key component behaviour

**CoachLayout.** Generates the berths of a coach from its class. Berth types repeat per bay: SL and 3A use `LB, MB, UB, LB, MB, UB, SL, SU` (8 per bay; SL has 72 berths, 3A has 64); 2A uses `LB, UB, LB, UB, SL, SU` (48 berths); 1A uses `LB, UB, LB, UB` (24 berths). Coach codes follow class: `S1` for SL, `B1` for 3A, `A1` for 2A, `H1` for 1A.

**BerthAllocator.** A journey segment is the half-open interval of stop numbers `[from_seq, to_seq)` (BR-10). A berth is free for a segment if no confirmed passenger on it has an overlapping interval. To build an allocation plan, the allocator lists all berths of the class, removes occupied ones, and assigns berths to passengers in order, preferring each passenger's berth preference and keeping a booking's passengers in the same coach where possible. Passengers who cannot be given a berth are waitlisted if the waitlist has room (BR-05).

**FareCalculator.** Implements BR-04. All money is stored and computed as integer paise, so there are no rounding errors from floating point; rounding to whole rupees happens once, at the end.

**RefundPolicy.** Implements BR-06 using the scheduled departure from the boarding station and the current time from an injectable clock, so tests can check every refund slab with fixed times.

**PaymentGateway.** An interface with `charge` and `refund`. `MockPaymentGateway` approves card `4111 1111 1111 1111` and UPI ID `success@berth`, declines card `4000 0000 0000 0002` and UPI ID `failure@berth`, and returns a generated gateway reference. A real gateway can replace it without changing any service.

**PnrGenerator.** Produces random 10-digit numbers (first digit non-zero) using a cryptographically secure generator, so PNRs cannot be guessed from one another. A unique index on `booking.pnr` catches the rare collision, and the generator retries.

**JobRunner.** Records each job execution in `job_run` (start, end, status, items processed) and runs the job's work. Each job is written to be idempotent (FR-JOB-05): it only selects rows that are still in the state it changes.

## 3.3 REST API

All endpoints are under `/api/v1`. Errors use a single JSON shape: `{"error": {"code": "BOOKING_EXPIRED", "message": "..."}}`.

| Method and path | Purpose | Access |
|---|---|---|
| `POST /auth/register` | Create passenger account | Public |
| `POST /auth/login`, `POST /auth/logout` | Start or end session | Public / user |
| `GET /auth/me`, `PATCH /users/me`, `POST /users/me/password` | Profile and password | User |
| `GET /stations?q=` | Station suggestions | Public |
| `GET /trains/search?from=&to=&date=&cls=` | Search with availability and fare | Public |
| `GET /trains/{number}/route` | Train schedule | Public |
| `POST /bookings` | Create booking (pending payment) | Passenger |
| `GET /bookings`, `GET /bookings/{id}` | My bookings, booking detail | Owner |
| `POST /bookings/{id}/payments` | Pay for booking | Owner |
| `POST /bookings/{id}/cancellation-quote` | Refund preview | Owner |
| `POST /bookings/{id}/cancellations` | Cancel passengers | Owner |
| `GET /bookings/{id}/ticket.pdf` | Download e-ticket | Owner |
| `GET /pnr/{pnr}` | PNR status (names masked) | Public |
| `/admin/stations`, `/admin/trains` (CRUD) | Master data | Admin |
| `PUT /admin/trains/{id}/route`, `PUT /admin/trains/{id}/coaches` | Route and composition | Admin |
| `POST /admin/runs/generate`, `GET /admin/runs`, `POST /admin/runs/{id}/cancel` | Train runs | Admin |
| `GET /admin/runs/{id}/chart` | Passenger chart | Admin |
| `GET /admin/jobs`, `POST /admin/jobs/{name}/run` | Job history, manual run | Admin |
| `GET /admin/stats?from=&to=` | Dashboard figures | Admin |
| `GET /jobs/chart-preparation`, `GET /jobs/nightly` | Cron triggers | Cron secret |

## 3.4 Web client

| Area | Pages |
|---|---|
| Public | Search (home), search results, train schedule, PNR status, login, register |
| Passenger | Passenger details, review and pay, booking confirmation, my bookings, booking detail with cancellation, account |
| Admin | Dashboard, stations, trains (route and coach editor), train runs, passenger chart, jobs |

The client uses a TypeScript API client generated from the API's OpenAPI document, so request and response types always match the backend. Server data is fetched and cached with TanStack Query; forms validate input before submitting, and the server validates again (NFR-07).

## 3.5 Scheduled jobs

Vercel's free plan runs cron jobs once a day, so the jobs are grouped into two daily triggers (times in IST; the cron configuration uses UTC):

| Trigger | Time | Jobs |
|---|---|---|
| `chart-preparation` | 18:00 | Chart preparation for runs starting the next day (BR-02, FR-WL-04) |
| `nightly` | 00:00 | Run generation for the ARP window (FR-JOB-01); journey completion (FR-JOB-03); expiry of unpaid bookings (FR-JOB-04) |

Two rules are also enforced at request time, so correctness does not depend on the cron firing on the exact minute. Booking and cancellation check the chart cut-off time directly, and a pending booking past `expires_at` is treated as expired when it is read or paid for.

# 4. Database Design

A full database design is not required by the brief; this section summarises the physical choices that matter to correctness. Figure 4.1 shows the tables and their relationships in crow's-foot notation. The schema is created and versioned through Alembic migrations.

<figure>
<img src="diagrams/erd.svg" alt="Entity relationship diagram">
<figcaption>Figure 4.1: Entity relationship diagram (key columns only)</figcaption>
</figure>

| Table | Key constraints |
|---|---|
| `station` | unique `code` |
| `train` | unique `number`; `running_days` is a 7-bit mask (Monday = bit 0) |
| `route_stop` | unique (`train_id`, `seq`) and (`train_id`, `station_id`) |
| `coach` | unique (`train_id`, `code`) |
| `train_run` | unique (`train_id`, `run_date`) |
| `train_run_class` | unique (`run_id`, `travel_class`); this row is the lock target for bookings and cancellations |
| `booking` | unique `pnr` (nullable until paid); index on (`user_id`, `journey_date`) |
| `passenger` | **exclusion constraint** (below); index on (`run_class_id`, `status`, `wl_seq`) |
| `payment`, `refund` | foreign keys to booking and payment |
| `audit_event`, `job_run` | append-only |

**Double-allocation guard.** Each passenger row stores its `run_class_id`, `from_seq` and `to_seq`. A PostgreSQL exclusion constraint (using the `btree_gist` extension) makes the database itself reject two confirmed passengers on the same berth with overlapping segments:

```sql
EXCLUDE USING gist (
  run_class_id WITH =, coach_code WITH =, berth_no WITH =,
  int4range(from_seq, to_seq) WITH &&
) WHERE (status = 'CNF')
```

Locking prevents conflicts in normal operation; the constraint is a second line of defence if the application ever has a bug.

**Time and money.** Timestamps are stored as `timestamptz` in UTC and converted to IST for business rules and display. Amounts are stored as integer paise.

# 5. Class Diagram

## 5.1 Domain model

The domain model shows the persistent entities. `Train` is composed of its `RouteStop`s and `Coach`es. Each `TrainRun` is one dated instance of a train and owns one `TrainRunClass` per class it carries; that row holds the class capacity and is the object locked during booking. A `Booking` belongs to one user and one run, covers a segment (`from_seq`, `to_seq`), and is composed of one to six `Passenger`s.

<figure>
<img src="diagrams/class-domain.svg" alt="Domain class diagram">
<figcaption>Figure 5.1: Domain class diagram</figcaption>
</figure>

## 5.2 Service layer

The service classes implement the business rules. Services depend on repositories and on the `PaymentGateway` interface rather than on concrete infrastructure, which keeps them unit-testable.

<figure>
<img src="diagrams/class-services.svg" alt="Service layer class diagram">
<figcaption>Figure 5.2: Service layer class diagram</figcaption>
</figure>

## 5.3 Scheduled jobs

Each job implements the `Job` interface and is executed by `JobRunner`, which records a `JobRun` for every execution.

<figure>
<img src="diagrams/class-jobs.svg" alt="Jobs class diagram">
<figcaption>Figure 5.3: Scheduled jobs class diagram</figcaption>
</figure>

# 6. Use Case Diagram

The use cases are split into two diagrams for readability: services used by guests and passengers, and operations performed by administrators and the scheduler. `Passenger` specialises `Guest`, so a passenger can do everything a guest can.

<figure>
<img src="diagrams/use-case.svg" alt="Passenger use case diagram">
<figcaption>Figure 6.1: Use cases for guests and passengers</figcaption>
</figure>

<figure>
<img src="diagrams/use-case-admin.svg" alt="Operations use case diagram">
<figcaption>Figure 6.2: Use cases for administrators and the scheduler</figcaption>
</figure>

## 6.1 Use case specification: Book ticket

| Field | Description |
|---|---|
| Actors | Passenger (primary), Payment gateway |
| Preconditions | Passenger is logged in; the train run is open for booking |
| Main flow | 1. Passenger selects a train, class and segment from search results. 2. Passenger enters 1 to 6 travellers. 3. System validates details and shows the fare breakdown. 4. System creates the booking in `PENDING_PAYMENT`. 5. Passenger pays. 6. System locks the run's class inventory, allocates berths, charges the payment, assigns a PNR and confirms. 7. System shows the confirmation with each traveller's status. |
| Alternative flows | 6a. Not enough berths: remaining travellers are waitlisted (Join waitlist). 6b. Berths and waitlist cannot hold everyone: booking is rejected, no charge. 6c. Payment declined: booking stays pending; passenger may retry until it expires. |
| Postconditions | Booking is `BOOKED` with a PNR; each traveller is `CNF` with a berth or `WL` with a position |
| Requirements | FR-BKG-01 to 08, FR-PAY-01 to 05, FR-TKT-01, 02 |

## 6.2 Use case specification: Cancel ticket

| Field | Description |
|---|---|
| Actors | Passenger (primary), Payment gateway |
| Preconditions | Booking is `BOOKED` and belongs to the passenger; chart not yet prepared |
| Main flow | 1. Passenger opens the booking and selects travellers to cancel. 2. System shows the refund. 3. Passenger confirms. 4. System locks the inventory and booking, cancels the travellers, records the refund, and promotes waitlisted travellers into released berths. 5. System shows the updated booking. |
| Alternative flows | 4a. All travellers cancelled: booking becomes `CANCELLED`. 4b. Chart already prepared: request is refused. |
| Postconditions | Selected travellers are `CAN`; refund recorded; eligible waitlisted travellers confirmed |
| Requirements | FR-CAN-01 to 05, FR-WL-01 to 03 |

## 6.3 Activity diagram: Book ticket

Figure 6.3 shows the same use case as a flow across the passenger, the system and the payment gateway, including every exit where the passenger is not charged.

<figure>
<img src="diagrams/activity-booking.svg" alt="Booking activity diagram">
<figcaption>Figure 6.3: Booking flow with decision points</figcaption>
</figure>

# 7. Sequence Diagrams

## 7.1 Search trains

<figure>
<img src="diagrams/seq-search.svg" alt="Search sequence diagram">
<figcaption>Figure 7.1: Searching trains with availability and fare</figcaption>
</figure>

## 7.2 Book and pay

The payment step takes locks in a fixed order (run class first, then booking). Every operation that changes inventory follows the same order, which rules out deadlocks between concurrent bookings, cancellations and the chart job. Capacity is checked before the gateway is charged, so a passenger is never charged for a booking that cannot be fulfilled (FR-BKG-06).

<figure>
<img src="diagrams/seq-booking.svg" alt="Booking sequence diagram">
<figcaption>Figure 7.2: Creating a booking and paying for it</figcaption>
</figure>

## 7.3 Cancel and promote waitlist

<figure>
<img src="diagrams/seq-cancellation.svg" alt="Cancellation sequence diagram">
<figcaption>Figure 7.3: Cancelling passengers and promoting the waitlist</figcaption>
</figure>

## 7.4 Chart preparation job

<figure>
<img src="diagrams/seq-chart.svg" alt="Chart preparation sequence diagram">
<figcaption>Figure 7.4: Scheduled chart preparation</figcaption>
</figure>

# 8. State Diagrams

## 8.1 Booking

<figure>
<img src="diagrams/state-booking.svg" alt="Booking state diagram">
<figcaption>Figure 8.1: Booking lifecycle</figcaption>
</figure>

## 8.2 Passenger ticket

<figure>
<img src="diagrams/state-passenger.svg" alt="Passenger state diagram">
<figcaption>Figure 8.2: Passenger (ticket) status</figcaption>
</figure>

## 8.3 Train run

<figure>
<img src="diagrams/state-train-run.svg" alt="Train run state diagram">
<figcaption>Figure 8.3: Train run lifecycle</figcaption>
</figure>

# 9. Design Decisions

| ID | Decision | Alternatives considered | Reason |
|---|---|---|---|
| DD-01 | Lock one `train_run_class` row per booking or cancellation | Lock individual berth rows; optimistic retries | One small lock per run and class is simple, and booking volume per run is low enough that serialising it costs nothing noticeable |
| DD-02 | Database exclusion constraint on berth and segment | Application checks only | Guarantees NFR-03 even if application logic is wrong |
| DD-03 | Check capacity before charging the gateway | Charge first, refund on failure | No refunds needed for rejected bookings; simpler for passengers |
| DD-04 | Segment-aware allocation using stop numbers | Allocate berths for the whole train journey | Matches real reservation practice; more berths can be sold (BR-10) |
| DD-05 | Daily cron plus request-time checks | Frequent cron (every few minutes) | Free plan allows daily cron; request-time checks keep cut-offs exact |
| DD-06 | Money as integer paise | Decimal or float rupees | Exact arithmetic, simple storage |
| DD-07 | Single origin through Vercel rewrites | Separate API domain with CORS | First-party cookies, no CORS configuration, simpler security |
| DD-08 | Neon for PostgreSQL | Supabase, Render PostgreSQL | Free plan does not pause projects after inactivity or expire, and offers a pooled endpoint for serverless use |

# 10. Requirements Traceability

| Requirement group | Design elements |
|---|---|
| FR-AUTH | Auth module; Section 3.1 |
| FR-SRCH, FR-AVL | `SearchService`, `AvailabilityService`, `FareCalculator`; Figure 7.1 |
| FR-BKG, FR-PAY, FR-TKT-01/02 | `BookingService`, `BerthAllocator`, `PaymentService`, `PnrGenerator`; Figure 7.2, Figure 8.1 |
| FR-TKT-03 to 05 | `TicketService`, `TicketPdfRenderer` |
| FR-CAN, FR-WL-01 to 03 | `CancellationService`, `WaitlistService`, `RefundPolicy`; Figure 7.3, Figure 8.2 |
| FR-WL-04, FR-JOB | `JobRunner`, job classes; Figure 5.3, Figure 7.4, Figure 8.3 |
| FR-ADM | Admin, Stations and Trains modules; Figure 6.2 |
| NFR-03, NFR-04 | DD-01, DD-02; Section 4 |
| NFR-05 to NFR-10 | Auth module; DD-07 |
| NFR-14 to NFR-16 | Layered architecture; Section 2.1 |
| NFR-20 | Deployment; Section 2.2, DD-05, DD-08 |
