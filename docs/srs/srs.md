---
title: Software Requirements Specification
subtitle: "Berth: Online Train Ticket Reservation System"
version: 1.0
date: 26 October 2026
---

# 1. Introduction

## 1.1 Purpose

This document specifies the requirements for **Berth**, a web-based online train ticket reservation system. It is the reference for the design (Software Design Document), the implementation, and the test plan. Every requirement carries an identifier so that design elements and test cases can be traced back to it.

## 1.2 Intended audience

| Reader | Use of this document |
|---|---|
| Course instructor / evaluator | Assess completeness and quality of the requirements |
| Developers (project group) | Build the system against stated requirements |
| Testers (project group) | Derive test cases and acceptance criteria |

## 1.3 Definitions and abbreviations

| Term | Meaning |
|---|---|
| Station | A railway station identified by a unique code (e.g. `NDLS`) |
| Train | A scheduled service with a number, name, ordered list of stops, coach composition and days of operation |
| Train run | One instance of a train running from its origin on a specific date |
| Class | Travel class: `SL` (Sleeper), `3A` (AC 3 Tier), `2A` (AC 2 Tier), `1A` (AC First Class) |
| Berth | A reservable seat/bunk in a coach, e.g. `B1-23` |
| Segment | The part of a train's route between a boarding and a destination station |
| PNR | Passenger Name Record: a unique 10-digit number identifying a booking |
| CNF | Confirmed: the passenger has an allocated berth |
| WL | Waitlisted: the passenger has no berth yet and holds a waitlist position |
| CAN | Cancelled |
| Chart preparation | The point after which bookings for a train run are closed and remaining waitlisted passengers are cancelled |
| ARP | Advance Reservation Period: how far ahead bookings open |
| IST | Indian Standard Time (UTC+05:30); all times in the system are IST |
| MoSCoW | Priority scheme: **M**ust, **S**hould, **C**ould have |

## 1.4 References

1. IEEE Std 830-1998, *Recommended Practice for Software Requirements Specifications*.
2. ISO/IEC/IEEE 29148:2018, *Systems and software engineering: Life cycle processes, Requirements engineering*.
3. I. Sommerville, *Software Engineering*, 10th ed., Pearson.
4. CSC702 Software Engineering assignment brief, Assignment 3.

## 1.5 Document overview

Sections 2–4 describe the problem, objectives and scope. Sections 5–8 contain the requirements: functional, non-functional, user and system requirements. Section 9 lists hardware and software requirements, and Section 10 records assumptions and constraints. Appendix A maps user requirements to functional requirements.

# 2. Problem Statement

Booking a reserved train ticket involves several decisions that depend on live data: which trains connect two stations on a given date, which classes still have berths, what the fare is, and what happens when a train is full. When this information is handled at a counter or through disconnected tools, passengers face long queues, cannot compare options, and receive little visibility into waitlist status or refunds.

From the operator's side, the core difficulty is **inventory correctness**. A berth on a train run is a limited resource that many passengers try to reserve at the same time. A booking system must never allocate the same berth to two passengers for overlapping parts of a journey, must reuse berths that become free after a passenger alights, must promote waitlisted passengers fairly when someone cancels, and must close bookings and settle the waitlist at a fixed time before departure.

The problem is therefore to build a system that lets passengers search, book, pay for and cancel train tickets online, while guaranteeing consistent berth allocation under concurrent use and applying the operator's fare, waitlist and refund rules automatically.

# 3. Objectives

| ID | Objective | Measure of success |
|---|---|---|
| OBJ-1 | Let passengers find trains between two stations for a date | Search returns all running trains with times, duration, availability and fare per class |
| OBJ-2 | Allow end-to-end booking online | A registered passenger can go from search to a confirmed PNR and e-ticket in one session |
| OBJ-3 | Guarantee correct berth inventory | No berth is ever allocated to two passengers for overlapping segments, including under concurrent requests |
| OBJ-4 | Handle full trains fairly | When berths run out, passengers are waitlisted and promoted in order when cancellations occur |
| OBJ-5 | Automate cancellation and refunds | Refund amount is computed from published rules without manual work |
| OBJ-6 | Automate time-based operations | Chart preparation and journey completion happen on schedule without operator action |
| OBJ-7 | Give administrators control of master data | Stations, trains, routes, coaches and train runs can be managed through an admin interface |

# 4. Scope of the System

## 4.1 In scope

- Passenger registration, login and profile.
- Station lookup and train search by source, destination and date.
- Segment-aware seat availability and fare calculation per class.
- Booking for up to six passengers, with mixed confirmed / waitlisted outcome.
- Simulated online payment through a mock payment gateway.
- PNR generation, booking confirmation and downloadable PDF e-ticket with QR code.
- Public PNR status enquiry.
- Full or partial cancellation with rule-based refund calculation.
- Automatic waitlist promotion on cancellation.
- Scheduled jobs: train-run generation, chart preparation, journey completion and clean-up of unpaid bookings.
- Administration of stations, trains, routes, coach composition and train runs.

## 4.2 Out of scope

- Real payment processing and real money movement (a mock gateway is used).
- Tatkal / premium quotas, concessions, RAC (Reservation Against Cancellation) and ladies/senior quotas.
- Unreserved and general-class ticketing.
- SMS and e-mail delivery (confirmation is shown on screen and as a PDF).
- Live train running status and platform information.
- Integration with real railway reservation systems; all train data is seeded or entered by administrators.

## 4.3 Users of the system

| User class | Description |
|---|---|
| Guest | Any visitor. Can search trains, view availability and fares, and check PNR status |
| Passenger | Registered user. Can book, pay, view and cancel own bookings, and download e-tickets |
| Administrator | Operator staff. Manages master data and train runs, and views passenger charts |
| Scheduler | Automated system actor that runs time-based jobs |
| Payment gateway | External system (mocked) that authorises payments and records refunds |

# 5. Functional Requirements

Priority uses MoSCoW: **M** = Must, **S** = Should, **C** = Could.

## 5.1 Accounts and authentication (AUTH)

| ID | Requirement | Priority |
|---|---|---|
| FR-AUTH-01 | The system shall allow a guest to register with full name, e-mail, mobile number and password. | M |
| FR-AUTH-02 | The system shall reject registration if the e-mail or mobile number is already registered. | M |
| FR-AUTH-03 | The system shall authenticate a user with e-mail and password and start a session. | M |
| FR-AUTH-04 | The system shall allow a logged-in user to log out, ending the session. | M |
| FR-AUTH-05 | The system shall assign each account a role of `PASSENGER` or `ADMIN` and restrict functions by role. | M |
| FR-AUTH-06 | The system shall allow a passenger to view and update their name and mobile number. | S |
| FR-AUTH-07 | The system shall allow a logged-in user to change their password after re-entering the current password. | S |

## 5.2 Stations and train search (SRCH)

| ID | Requirement | Priority |
|---|---|---|
| FR-SRCH-01 | The system shall suggest stations matching a partial station name or code as the user types. | M |
| FR-SRCH-02 | The system shall search trains given a source station, destination station and journey date. | M |
| FR-SRCH-03 | The search shall return only trains whose route visits the source before the destination and that run on the journey date at the source station. | M |
| FR-SRCH-04 | Each result shall show train number and name, departure and arrival times, journey duration and distance. | M |
| FR-SRCH-05 | The system shall reject searches where source equals destination, or the date is in the past or beyond the ARP. | M |
| FR-SRCH-06 | The user shall be able to filter results by class and sort them by departure time or duration. | S |

## 5.3 Availability and fare (AVL)

| ID | Requirement | Priority |
|---|---|---|
| FR-AVL-01 | For each result and class, the system shall show availability as `AVAILABLE n`, `WL n` or `NOT AVAILABLE`. | M |
| FR-AVL-02 | Availability shall be computed for the searched segment, so that a berth freed after a station can be sold for later segments. | M |
| FR-AVL-03 | The system shall compute the fare per passenger for a class and segment according to BR-04. | M |
| FR-AVL-04 | The system shall show a fare breakdown (base fare, reservation charge, GST, total) before payment. | M |
| FR-AVL-05 | The system shall show `BOOKING CLOSED` for train runs whose chart has been prepared or that are cancelled. | M |

## 5.4 Booking (BKG)

| ID | Requirement | Priority |
|---|---|---|
| FR-BKG-01 | The system shall allow only logged-in passengers to create a booking. | M |
| FR-BKG-02 | A booking shall contain 1 to 6 passengers, each with name, age and gender. | M |
| FR-BKG-03 | The system shall validate passenger details (name 2–50 letters, age 1–120, gender `M`/`F`/`T`). | M |
| FR-BKG-04 | The system shall create the booking in `PENDING_PAYMENT` state and show the amount payable. | M |
| FR-BKG-05 | After successful payment, the system shall allocate a berth to each passenger in order while berths are available for the segment, and waitlist the remaining passengers (BR-05). | M |
| FR-BKG-06 | The system shall reject the booking and refund the payment if the combined berth and waitlist capacity cannot accommodate all passengers. | M |
| FR-BKG-07 | Allocation shall be performed so that concurrent bookings never receive the same berth for overlapping segments. | M |
| FR-BKG-08 | The system shall allow the passenger to choose "book only if all berths are confirmed"; if not possible, the booking shall be rejected and refunded. | C |
| FR-BKG-09 | The system shall try to honour each passenger's berth preference (lower, middle, upper, side lower, side upper) when allocating. | C |

## 5.5 Payment (PAY)

| ID | Requirement | Priority |
|---|---|---|
| FR-PAY-01 | The system shall hand the payable amount to the payment gateway and record the payment attempt. | M |
| FR-PAY-02 | The system shall mark the booking `BOOKED` only after the gateway reports success. | M |
| FR-PAY-03 | On payment failure, the booking shall remain `PENDING_PAYMENT` and the passenger may retry until it expires (BR-08). | M |
| FR-PAY-04 | The system shall record every refund with amount, reason and status. | M |
| FR-PAY-05 | The system shall process a payment confirmation for a booking at most once, even if the request is repeated. | M |

## 5.6 Tickets and PNR (TKT)

| ID | Requirement | Priority |
|---|---|---|
| FR-TKT-01 | The system shall assign each paid booking a unique 10-digit PNR. | M |
| FR-TKT-02 | The system shall show a booking confirmation with PNR, train, segment, date, passengers, status and berth of each passenger, and amount paid. | M |
| FR-TKT-03 | The system shall let the passenger download an e-ticket as a PDF containing the confirmation details and a QR code encoding the PNR. | M |
| FR-TKT-04 | The system shall list a passenger's bookings, separated into upcoming and past journeys. | M |
| FR-TKT-05 | Any user shall be able to check PNR status by entering a PNR; passenger names shall be partially masked. | S |

## 5.7 Cancellation and refund (CAN)

| ID | Requirement | Priority |
|---|---|---|
| FR-CAN-01 | The system shall allow a passenger to cancel an entire booking or selected passengers of it. | M |
| FR-CAN-02 | The system shall show the refund amount for the selection before the passenger confirms cancellation. | M |
| FR-CAN-03 | The refund shall be computed according to BR-06. | M |
| FR-CAN-04 | The system shall not allow cancellation after chart preparation or after departure. | M |
| FR-CAN-05 | When all passengers of a booking are cancelled, the booking shall move to `CANCELLED`. | M |

## 5.8 Waitlist and chart (WL)

| ID | Requirement | Priority |
|---|---|---|
| FR-WL-01 | Waitlisted passengers shall be numbered in order of booking for each train run and class. | M |
| FR-WL-02 | When a confirmed berth is released, the system shall attempt to confirm waitlisted passengers in waitlist order whose segment fits the freed berth (BR-07). | M |
| FR-WL-03 | Promotion shall happen in the same transaction as the cancellation that released the berth. | M |
| FR-WL-04 | At chart preparation, the system shall close bookings for the train run and cancel all still-waitlisted passengers with a full refund. | M |

## 5.9 Administration (ADM)

| ID | Requirement | Priority |
|---|---|---|
| FR-ADM-01 | An administrator shall be able to create, edit and deactivate stations. | M |
| FR-ADM-02 | An administrator shall be able to create and edit trains: number, name, days of operation and coach composition per class. | M |
| FR-ADM-03 | An administrator shall be able to define a train's route as an ordered list of stops with arrival time, departure time, day offset and distance from origin. | M |
| FR-ADM-04 | An administrator shall be able to generate train runs for a date range. | M |
| FR-ADM-05 | An administrator shall be able to cancel a train run; all active bookings on it shall be cancelled with full refund. | S |
| FR-ADM-06 | An administrator shall be able to view the passenger chart of a train run (berth, passenger, segment, status). | S |
| FR-ADM-07 | An administrator shall be able to trigger any scheduled job manually. | S |
| FR-ADM-08 | An administrator shall see a dashboard with counts of bookings, cancellations and revenue for a date range. | C |

## 5.10 Scheduled jobs (JOB)

| ID | Requirement | Priority |
|---|---|---|
| FR-JOB-01 | A daily job shall create train runs so that runs exist for every operating day within the ARP. | M |
| FR-JOB-02 | A daily job shall prepare charts for all train runs starting on the next day (BR-02). | M |
| FR-JOB-03 | A daily job shall mark bookings of train runs that have completed their journey as `COMPLETED`. | M |
| FR-JOB-04 | A job shall mark bookings left in `PENDING_PAYMENT` beyond the payment window as `EXPIRED`. | M |
| FR-JOB-05 | Every job shall be idempotent: running it twice for the same date shall not change the result. | M |
| FR-JOB-06 | Every job execution shall be logged with start time, end time, items processed and outcome. | S |

# 6. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Performance | Train search and availability for a date shall respond within 2 s at the 95th percentile on the seeded dataset, excluding serverless cold start. |
| NFR-02 | Performance | Booking confirmation (payment success to PNR) shall complete within 3 s at the 95th percentile. |
| NFR-03 | Consistency | Under 20 concurrent booking requests for the last available berth, exactly one shall receive it; no berth shall be double-allocated. |
| NFR-04 | Reliability | Every booking, cancellation and promotion shall run in a single database transaction; a failure shall leave no partial changes. |
| NFR-05 | Security | Passwords shall be stored only as salted bcrypt hashes. |
| NFR-06 | Security | Sessions shall use signed tokens in `HttpOnly`, `Secure`, `SameSite` cookies, expiring after 24 hours. |
| NFR-07 | Security | All input shall be validated on the server; database access shall use parameterised queries only. |
| NFR-08 | Security | A user shall be able to access only their own bookings; admin endpoints shall require the `ADMIN` role. |
| NFR-09 | Security | Secrets (database URL, signing keys) shall be supplied through environment variables and never committed to the repository. |
| NFR-10 | Security | Repeated failed logins shall be rate-limited to 5 attempts per minute per account. |
| NFR-11 | Usability | A passenger shall be able to complete a booking from the search page in no more than 5 screens. |
| NFR-12 | Usability | The interface shall be usable on screens from 360 px to 1920 px wide. |
| NFR-13 | Accessibility | Forms shall have labels, be keyboard-operable and meet WCAG 2.1 AA colour contrast. |
| NFR-14 | Maintainability | The backend shall follow a layered structure (routes, services, repositories, models); business rules shall live only in the service layer. |
| NFR-15 | Maintainability | Automated tests shall cover at least 80% of backend service-layer lines. |
| NFR-16 | Maintainability | Code shall pass the configured linters and formatters in continuous integration before merge. |
| NFR-17 | Portability | The web client shall work on the latest two versions of Chrome, Edge, Firefox and Safari. |
| NFR-18 | Availability | The deployed system shall be reachable through a public HTTPS URL during the evaluation period, within free-tier limits of the hosting providers. |
| NFR-19 | Auditability | Booking, payment, cancellation, refund and promotion events shall be recorded with timestamp and actor. |
| NFR-20 | Cost | The system shall be developed, tested and hosted using only free software and free-tier services. |

# 7. User Requirements

User requirements describe, in plain language, what each class of user needs from the system. Each is refined into the functional requirements listed against it (see Appendix A).

## 7.1 Guest

| ID | User requirement |
|---|---|
| UR-01 | As a guest, I want to find trains between two stations on a date so that I can plan a journey. |
| UR-02 | As a guest, I want to see seat availability and fare for each class before I register. |
| UR-03 | As a guest, I want to check the status of a PNR without logging in. |
| UR-04 | As a guest, I want to create an account so that I can book tickets. |

## 7.2 Passenger

| ID | User requirement |
|---|---|
| UR-05 | As a passenger, I want to book tickets for myself and up to five others in one booking. |
| UR-06 | As a passenger, I want to pay online and immediately know whether each traveller is confirmed or waitlisted. |
| UR-07 | As a passenger, I want a printable e-ticket to show during travel. |
| UR-08 | As a passenger, I want to see all my past and upcoming bookings in one place. |
| UR-09 | As a passenger, I want to cancel a whole booking or some travellers and know the refund before I confirm. |
| UR-10 | As a waitlisted passenger, I want to be confirmed automatically if a berth becomes free. |

## 7.3 Administrator

| ID | User requirement |
|---|---|
| UR-11 | As an administrator, I want to maintain stations, trains, routes and coach composition. |
| UR-12 | As an administrator, I want bookings to open automatically for upcoming dates. |
| UR-13 | As an administrator, I want to see who is travelling in which berth on a train run. |
| UR-14 | As an administrator, I want to cancel a train run and have all passengers refunded automatically. |

## 7.4 User characteristics

Passengers are members of the public with basic smartphone or computer skills; no training can be assumed, so the booking flow must be self-explanatory. Administrators are operator staff who receive a short briefing and are familiar with railway terms such as class, berth and chart.

# 8. System Requirements

This section states requirements on the system as a whole: its external interfaces and the business rules that the functional requirements depend on.

## 8.1 External interface requirements

| ID | Interface | Requirement |
|---|---|---|
| SR-01 | User interface | A responsive single-page web application served over HTTPS. |
| SR-02 | Application interface | A JSON REST API over HTTPS, versioned under `/api/v1`, with machine-readable OpenAPI 3 documentation. |
| SR-03 | Database interface | A PostgreSQL 15 or later relational database accessed through a connection pool. |
| SR-04 | Payment gateway interface | A payment gateway adapter exposing `charge(amount, reference)` and `refund(payment_id, amount)`; the delivered system uses a mock implementation with deterministic test cards. |
| SR-05 | Scheduler interface | Scheduled jobs shall be triggered by authenticated HTTPS calls from the hosting platform's cron service, protected by a shared secret. |
| SR-06 | Document output | E-tickets shall be generated as PDF files of A4 size. |

## 8.2 Business rules

| ID | Rule |
|---|---|
| BR-01 | **Advance reservation period.** Bookings open 60 days before the journey date, excluding the journey date. |
| BR-02 | **Chart preparation.** The chart for a train run that starts from its origin on date D is prepared at 18:00 IST on D−1. No bookings or cancellations are accepted for the run after that. |
| BR-03 | **Passengers per booking.** A booking contains between 1 and 6 passengers. |
| BR-04 | **Fare.** Per passenger: base fare = max(minimum fare, distance × rate per km) for the class; total = base fare + reservation charge + GST (5% of base fare + reservation charge for AC classes, 0% for SL), rounded to the nearest rupee. Rates in Table 8.1. |
| BR-05 | **Waitlist capacity.** Each train run and class accepts at most 20 waitlisted passengers at any time. |
| BR-06 | **Refund.** For each cancelled confirmed passenger, measured from scheduled departure at the boarding station: more than 48 h: fare minus the flat fee for the class; 12 to 48 h: fare minus 25% (at least the flat fee); less than 12 h: 50% of fare. A cancelled waitlisted passenger is refunded the fare minus ₹60. Waitlisted passengers cancelled at chart preparation, and passengers on a train run cancelled by an administrator, are refunded in full. |
| BR-07 | **Waitlist promotion.** Waitlisted passengers are considered in increasing waitlist number; a passenger is confirmed if a berth is free for their whole segment. Remaining waitlist numbers are renumbered after promotion. |
| BR-08 | **Payment window.** A booking in `PENDING_PAYMENT` expires 15 minutes after creation. |
| BR-09 | **Journey date.** The journey date entered by a user is the date of departure from the boarding station. |
| BR-10 | **Berth occupancy.** A berth is occupied from the boarding station up to, but not including, the destination station, and may be allocated again from that station onward. |

**Table 8.1: Fare parameters**

| Class | Rate per km (₹) | Minimum base fare (₹) | Reservation charge (₹) | GST | Cancellation flat fee (₹) |
|---|---|---|---|---|---|
| SL | 0.45 | 100 | 20 | 0% | 120 |
| 3A | 1.20 | 300 | 40 | 5% | 180 |
| 2A | 1.75 | 450 | 50 | 5% | 200 |
| 1A | 3.00 | 800 | 60 | 5% | 240 |

# 9. Hardware and Software Requirements

All software listed is free and open source or available on a free tier (NFR-20).

## 9.1 Client side

| Item | Minimum requirement |
|---|---|
| Device | Any desktop, laptop or smartphone able to run a current web browser |
| Screen | 360 px wide or more |
| Browser | Latest two versions of Chrome, Edge, Firefox or Safari, with JavaScript enabled |
| PDF viewer | Any PDF viewer (built into all supported browsers) for e-tickets |
| Network | Internet connection of 1 Mbps or faster |

## 9.2 Server side (deployment)

| Item | Choice |
|---|---|
| Web hosting | Vercel (Hobby plan): static hosting for the web client, serverless Python functions for the API, cron jobs |
| Database | Neon serverless PostgreSQL (free plan) |
| Source control and CI | GitHub, GitHub Actions |

## 9.3 Development environment

| Item | Minimum requirement |
|---|---|
| Processor | 64-bit dual-core CPU |
| Memory | 8 GB RAM |
| Storage | 5 GB free disk space |
| Operating system | Windows 10/11, macOS 13+ or a current Linux distribution |

## 9.4 Software stack

| Layer | Software |
|---|---|
| Backend language | Python 3.12 |
| Backend framework | FastAPI, Pydantic |
| Data access | SQLAlchemy 2, Alembic (migrations), psycopg 3 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query |
| PDF and QR | ReportLab, qrcode |
| Testing | pytest, pytest-cov, Vitest, React Testing Library, Playwright |
| Code quality | Ruff, ESLint, Prettier |
| Package managers | uv (Python), pnpm (JavaScript) |
| Documentation | Markdown, PlantUML |

# 10. Assumptions and Constraints

## 10.1 Assumptions

| ID | Assumption |
|---|---|
| A-01 | Train, station and route data is entered by administrators or seeded; it is not imported from any real railway system. |
| A-02 | Each coach of a class has the same berth layout (SL and 3A: 72 berths; 2A: 48 berths; 1A: 24 berths). |
| A-03 | Train timings are fixed per schedule; delays are not modelled. |
| A-04 | Users have a valid e-mail address, but the system does not verify it by sending mail. |
| A-05 | The mock payment gateway behaves like a real one: it can succeed or fail, and refunds are recorded immediately. |
| A-06 | All users and trains are in a single time zone (IST). |

## 10.2 Constraints

| ID | Constraint |
|---|---|
| C-01 | **Cost:** no paid software, service or infrastructure may be used. |
| C-02 | **Schedule:** requirements, design, implementation and testing must be completed by 31 October 2026. |
| C-03 | **Team:** four developers. |
| C-04 | **Hosting:** serverless functions have no persistent local disk and limited execution time; all state must be in the database and each request must finish within the platform limit. |
| C-05 | **Scheduling:** free-tier cron runs jobs at most once per day, so time-based rules (BR-02, FR-JOB-01 to 04) are designed around daily execution, with expiry of unpaid bookings also enforced when bookings are read. |
| C-06 | **Database:** the free database tier limits storage to 0.5 GB and may suspend when idle, adding a short delay to the first request. |
| C-07 | **Regulatory:** because payment is simulated, no card data is stored or processed and PCI-DSS does not apply. |

# Appendix A. Traceability: User Requirements to Functional Requirements

| User requirement | Functional requirements |
|---|---|
| UR-01 | FR-SRCH-01 to FR-SRCH-06 |
| UR-02 | FR-AVL-01 to FR-AVL-05 |
| UR-03 | FR-TKT-05 |
| UR-04 | FR-AUTH-01, FR-AUTH-02, FR-AUTH-03 |
| UR-05 | FR-BKG-01 to FR-BKG-04, FR-BKG-09 |
| UR-06 | FR-PAY-01 to FR-PAY-05, FR-BKG-05 to FR-BKG-08, FR-TKT-01, FR-TKT-02 |
| UR-07 | FR-TKT-03 |
| UR-08 | FR-TKT-04 |
| UR-09 | FR-CAN-01 to FR-CAN-05 |
| UR-10 | FR-WL-01 to FR-WL-03 |
| UR-11 | FR-ADM-01, FR-ADM-02, FR-ADM-03 |
| UR-12 | FR-ADM-04, FR-JOB-01 |
| UR-13 | FR-ADM-06 |
| UR-14 | FR-ADM-05 |
