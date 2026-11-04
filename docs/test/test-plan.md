---
title: Software Test Plan
subtitle: "Berth: Online Train Ticket Reservation System"
version: 1.1
date: 29 October 2026
---

# 1. Testing Objectives

| ID | Objective |
|---|---|
| TO-1 | Verify that every **Must** functional requirement in the SRS is implemented correctly, together with every **Should** requirement that is built. |
| TO-2 | Verify the business rules (BR-01 to BR-10) with exact expected values, including boundaries such as refunds at exactly 48 and 12 hours. |
| TO-3 | Show that berth inventory stays correct under concurrent use: no double allocation and correct waitlist promotion (NFR-03, NFR-04). |
| TO-4 | Verify the scheduled jobs: correct effect, and no further change when run twice (FR-JOB-05). |
| TO-5 | Check the measurable non-functional requirements: performance, security, usability, accessibility and maintainability. |
| TO-6 | Confirm through end-to-end scenarios that the system meets the user requirements (UR-01 to UR-14). |
| TO-7 | Record, fix and re-test every defect found. |

# 2. Testing Scope

<div class="cols" markdown="1">
<div markdown="1">

**In scope**

- Service-layer business rules, repositories and the database exclusion constraint
- Every REST API endpoint and the scheduled jobs
- All web pages: search, booking, payment, my bookings, cancellation, PNR status, admin
- End-to-end flows across browser, API and database
- Measurable NFRs: 01, 03, 05, 06, 07, 10, 11, 12, 13, 15, 16

</div>
<div markdown="1">

**Out of scope**

- Real payment gateways (only the mock gateway exists, SRS 4.2)
- Load beyond the concurrency tests IT-36 and ST-09
- Automated runs on browsers other than Chromium
- Penetration testing beyond the checks in Section 6
- The hosting services themselves (Vercel, Neon)

</div>
</div>

# 3. Testing Strategy

## 3.1 Approach

Testing follows the **V-model**: every development phase has a matching test level, and the test cases in Sections 4 to 7 were written from the SRS and SDD **before** the code (Figure 3.1). Each test case names the requirement it verifies, so requirement coverage can be read directly from Appendix A.

<figure>
<img src="diagrams/v-model.svg" alt="V-model">
<figcaption>Figure 3.1: V-model mapping of development phases to test levels</figcaption>
</figure>

Test cases are designed with black-box techniques: **equivalence partitioning** (valid and invalid inputs), **boundary value analysis** (1 and 6 passengers, refunds at exactly 48 h and 12 h, a waitlist of exactly 20) and **state transition testing** (the booking, passenger and train run state diagrams in SDD Section 8). Unit tests are also measured for statement coverage.

## 3.2 Tools and environments

| Purpose | Tool | Environment |
|---|---|---|
| Backend unit and integration tests | pytest, pytest-cov, FastAPI test client | Python 3.12, PostgreSQL 18 in Docker |
| Frontend unit tests | Vitest, React Testing Library | Node 22, jsdom |
| End-to-end, system and acceptance tests | Playwright (Chromium), axe-core | Local deployment on a freshly seeded database |
| Deployed checks | Python scripts over HTTPS | Vercel (web and API) with Neon PostgreSQL |
| Continuous integration | GitHub Actions: lint, tests, e2e on every push | Ubuntu runners with a PostgreSQL service |
| Defect tracking | GitHub Issues and the Test Report | |

Integration tests run inside a transaction that is rolled back after each test, so tests never affect each other. Wherever time matters (refunds, cut-offs, expiry, jobs) a fixed clock is injected.

## 3.3 Test data

| Item | Data |
|---|---|
| Stations | `STA` Alpha, `STB` Bravo, `STC` Charlie, `STD` Delta |
| Train 90001 | Fixture Express, Mon/Wed/Fri: STA 06:00, STB 100 km, STC 250 km, STD 20:00 (400 km); coaches S1, B1, A1, H1 |
| Train 90002 | Long Haul Mail, daily, STA to STD overnight, 1400 km, 3A only (refund cases) |
| Users | `passenger1@example.com`, `passenger2@example.com`, `admin@example.com` |
| Clock | A fixed Sunday, 06:00 IST: Monday's run departs in 24 h, Wednesday's in 72 h |
| End-to-end data | 22 real station codes and 10 invented trains loaded by `scripts/seed.py` |
| Payment | Approve: card `4111 1111 1111 1111` or UPI `success@berth`. Decline: card `4000 0000 0000 0002` or UPI `failure@berth` |

## 3.4 Entry and exit criteria

| | Criteria |
|---|---|
| Entry | Code builds; migrations apply cleanly; fixture or seed data loads; the test case is written |
| Suspension | A critical defect blocks a whole flow (login or payment); that flow pauses until it is fixed |
| Exit | All Must-priority cases executed and passing; no open Critical or Major defects; backend coverage of at least 80%; lint and format checks pass |

## 3.5 Roles and schedule

| Member | Role |
|---|---|
| Kritya Rajansh | Test lead: plan, test data, defect triage, Test Report |
| Esha Biswas | Unit tests: fares, refunds, inventory |
| Krishna Singh | Integration tests: API, booking and cancellation flows, jobs |
| Nitesh Jha | System and acceptance tests: Playwright scenarios, non-functional checks |

Unit and integration tests are written alongside each module and run on every push; system and acceptance tests run once the web client is complete and again before submission.

## 3.6 Risks

| Risk | Mitigation |
|---|---|
| Time-dependent rules give flaky results | Inject a fixed clock; never assert against the real time |
| Concurrency defects hide in sequential tests | Dedicated parallel tests IT-36 (10 threads) and ST-09 (20 HTTP requests) |
| Free-tier cold starts distort timing | Warm up before measuring; report the 95th percentile |
| Shared live database | Destructive tests run locally on a fresh database; live checks use the demo account |

# 4. Unit Testing

Unit tests check single classes with no database or network: `FareCalculator`, `RefundPolicy`, `CoachLayout`, the allocation planner, `PnrGenerator`, request validation, password hashing, running-day and cut-off rules, and `MockPaymentGateway`. On the frontend, Vitest covers the formatters, form validation, the post-login redirect guard and status colours.

<!-- cases:UT:plan -->

# 5. Integration Testing

Integration tests call the REST API through the FastAPI test client, which runs routers, services and repositories against a real PostgreSQL database. They follow the SDD sequence diagrams in **bottom-up** order: inventory, then booking and payment, then cancellation and waitlist, then jobs and administration.

<!-- cases:IT:plan -->

# 6. System Testing

Playwright drives Chromium through complete journeys on a local deployment with a freshly seeded database. Non-functional requirements are checked by script, against the deployed site where noted.

| Area | Test cases |
|---|---|
| Functional journeys (guest, passenger, administrator) | ST-01 to ST-07 |
| Usability and accessibility | ST-08, ST-13, ST-14 |
| Concurrency and performance | ST-09, ST-10 |
| Security | ST-11, ST-12 |
| Maintainability | ST-15 |

<!-- cases:ST:plan -->

# 7. Acceptance Testing

Acceptance tests are user scenarios, one per user requirement group, written from the point of view of the user classes in SRS 4.3. They are scripted in Playwright (`e2e/tests/acceptance.spec.ts`) so the group can repeat them on demand. The system is accepted when every scenario passes.

<!-- cases:AT:plan -->

# 8. Defect Management

Defects are recorded as GitHub Issues, labelled with severity and priority and linked to the failing test case, and listed in the Test Report. A defect is closed only when its test case passes and the full automated suite is green.

<figure>
<img src="diagrams/defect-lifecycle.svg" alt="Defect lifecycle" style="max-width:150mm">
<figcaption>Figure 8.1: Defect lifecycle</figcaption>
</figure>

<div class="cols" markdown="1">
<div markdown="1">

| Severity | Meaning |
|---|---|
| Critical | Data corruption, security breach, core flow unusable |
| Major | A requirement not met, no workaround |
| Minor | Partly met, or a workaround exists |
| Trivial | Cosmetic |

</div>
<div markdown="1">

| Priority | Meaning |
|---|---|
| P1 | Fix before further testing |
| P2 | Fix before release |
| P3 | Fix if time allows |

</div>
</div>

Each defect report records: ID, title, the test case that found it, the requirement affected, severity and priority, environment, steps to reproduce, expected and actual result, root cause and fix (with commit), and status.

# Appendix A. Requirements Coverage

| Requirement group | Test cases |
|---|---|
| FR-AUTH | IT-01 to IT-04, UT-20, AT-01 |
| FR-SRCH | IT-05 to IT-08, UT-21, ST-01 |
| FR-AVL, BR-04 | UT-01 to UT-04, IT-09, IT-10, ST-01, AT-01 |
| FR-BKG, BR-03, BR-05, BR-10 | UT-13 to UT-17, UT-19, IT-09 to IT-17, IT-36, ST-02, ST-09, AT-02 |
| FR-PAY, BR-08 | UT-24, IT-11 to IT-15, ST-04 |
| FR-TKT | UT-18, UT-23, IT-25, IT-26, ST-02, ST-05, AT-05 |
| FR-CAN, BR-06 | UT-05 to UT-10, IT-19 to IT-24, ST-03, AT-04 |
| FR-WL, BR-07 | IT-16, IT-21, IT-22, IT-27, AT-03 |
| FR-ADM | IT-32, IT-34, IT-35, ST-06, ST-07, AT-06 to AT-08 |
| FR-JOB, BR-02 | UT-22, IT-27 to IT-31 |
| Non-functional | ST-08 to ST-15, IT-03, IT-33, IT-36 |
| User requirements | AT-01 to AT-08 |
