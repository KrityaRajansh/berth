---
title: Software Test Plan and Report
subtitle: "Berth: Online Train Ticket Reservation System"
version: 1.0
date: 26 October 2026
---

# 1. Testing Objectives

| ID | Objective |
|---|---|
| TO-1 | Verify that every **Must** functional requirement in SRS v1.0 is implemented correctly, and every **Should** requirement that was built. |
| TO-2 | Verify the business rules (BR-01 to BR-10) with exact expected values, including boundary cases such as refunds at exactly 48 and 12 hours. |
| TO-3 | Demonstrate that berth inventory stays correct under concurrent use: no double allocation, correct waitlist promotion (NFR-03, NFR-04). |
| TO-4 | Verify the scheduled jobs: correct effect, and no change when run twice (FR-JOB-05). |
| TO-5 | Check the measurable non-functional requirements: performance, security, usability, accessibility and maintainability. |
| TO-6 | Confirm with end-to-end scenarios that the system meets the user requirements (UR-01 to UR-14), so the group can accept it. |
| TO-7 | Find, record and track defects until they are fixed and re-tested. |

# 2. Testing Scope

## 2.1 In scope

- Backend: all service-layer business rules, repositories, REST API endpoints, scheduled jobs, the database exclusion constraint.
- Frontend: search, booking, payment, my bookings, cancellation, PNR status, admin pages.
- End-to-end flows through the deployed stack (browser, API, database).
- Non-functional requirements with measurable criteria: NFR-01, 03, 05, 06, 07, 10, 11, 12, 13, 15, 16.

## 2.2 Out of scope

- Real payment gateways (only the mock gateway exists; SRS 4.2).
- Load beyond the concurrency test in ST-09; the free hosting tier is not suited to load testing.
- Browsers other than Chromium for automated tests; Firefox, Safari and Edge are checked manually once (NFR-17).
- Penetration testing beyond the security checks listed in Section 6.
- Third-party services (Vercel, Neon) themselves.

# 3. Testing Strategy

## 3.1 Approach

Testing follows the **V-model**: each development phase has a matching test level, and the test cases were written from the SRS and SDD **before** implementation. Every test case is linked to a requirement, so coverage of the requirements can be checked directly (Appendix A).

| Development phase | Test level | Based on |
|---|---|---|
| Requirements (SRS) | Acceptance testing | User requirements, Section 7 |
| System design (SDD architecture) | System testing | Functional and non-functional requirements, Section 6 |
| Module design (SDD modules, sequences) | Integration testing | API, sequence diagrams, Section 5 |
| Implementation | Unit testing | Service classes and business rules, Section 4 |

Black-box techniques are used throughout: **equivalence partitioning** (valid and invalid inputs), **boundary value analysis** (passenger count 1 and 6, refund slabs at 48 h and 12 h, waitlist limit 20) and **state transition testing** (booking, passenger and train run states from SDD Section 8). Unit tests also use white-box statement coverage, measured with pytest-cov.

## 3.2 Tools

| Purpose | Tool |
|---|---|
| Backend unit and integration tests | pytest, httpx test client, pytest-cov |
| Frontend component tests | Vitest, React Testing Library |
| End-to-end system tests | Playwright (Chromium), @axe-core/playwright for accessibility |
| Concurrency and performance scripts | Python asyncio with httpx |
| Continuous integration | GitHub Actions: lint, unit, integration and e2e tests on every push |
| Defect tracking | GitHub Issues with severity and priority labels |

## 3.3 Test environments

| Environment | Description | Used for |
|---|---|---|
| Local | Windows 11, Python 3.12, Node 22, PostgreSQL 18 in Docker | Unit, integration, e2e during development |
| CI | GitHub Actions Ubuntu runner with a PostgreSQL service container | All automated tests on each push |
| Deployed | Vercel (web and API) with a Neon database branch for testing | System and acceptance tests, performance |

Each integration test runs inside a database transaction that is rolled back afterwards, so tests do not affect each other. A fixed clock is injected wherever time matters (refunds, cut-offs, expiry, jobs).

## 3.4 Test data

The automated tests use a small fixed dataset so that expected values can be calculated by hand:

| Item | Data |
|---|---|
| Stations | `STA` Alpha, `STB` Bravo, `STC` Charlie, `STD` Delta |
| Train | `90001` Fixture Express, runs Monday, Wednesday, Friday |
| Route | STA (seq 1, dep 06:00, 0 km) → STB (seq 2, 100 km) → STC (seq 3, 250 km) → STD (seq 4, arr 20:00, 400 km), all on day 0 |
| Coaches | `S1` (SL), `B1` (3A), `A1` (2A), `H1` (1A); capacity tests override a coach to 2 berths |
| Long-distance train | `90002` Long Haul Mail, STA → STD, 1400 km, 3A only, used for refund tests |
| Users | `passenger1@test.local`, `passenger2@test.local` (PASSENGER), `admin@test.local` (ADMIN) |
| Payment | Approve: card `4111 1111 1111 1111`, UPI `success@berth`. Decline: card `4000 0000 0000 0002`, UPI `failure@berth` |

System and acceptance tests on the deployed site use the seed dataset of real station names and invented trains loaded by `scripts/seed`.

## 3.5 Entry and exit criteria

| | Criteria |
|---|---|
| Entry | Code builds; database migrations apply cleanly; seed or fixture data loads; the test case is marked ready. |
| Suspension | A critical defect blocks a whole flow (e.g. login or payment); testing of that flow pauses until it is fixed. |
| Exit | All Must-priority test cases executed and passing; no open Critical or Major defects; service-layer line coverage at least 80%; CI green on `main`. |

## 3.6 Roles

| Member | Role |
|---|---|
| Kritya Rajansh | Test lead: plan, test data, defect triage, report |
| Esha Biswas | Unit tests: fares, refunds, inventory |
| Krishna Singh | Integration tests: API, booking and cancellation flows, jobs |
| Nitesh Jha | System and acceptance tests: Playwright scenarios, non-functional checks |

## 3.7 Risks

| Risk | Mitigation |
|---|---|
| Time-dependent rules give flaky results | Inject a fixed clock; never use the real time in assertions |
| Concurrency defects do not show up in sequential tests | Dedicated concurrency test (IT-36, ST-09) with parallel requests |
| Free-tier cold starts distort timing | Warm up before measuring; measure p95 excluding the first request (NFR-01) |
| Tight schedule | Must-priority test cases are run first; automated tests run in CI on every push |

# 4. Unit Testing

Unit tests check single classes with no database or network. They cover the parts of the system where the business rules live: `FareCalculator`, `RefundPolicy`, `CoachLayout`, `BerthAllocator` (with an in-memory list of occupied berths), `PnrGenerator`, input validation, `PasswordHasher`, running-day and cut-off calculations, and `MockPaymentGateway`. Test cases: UT-01 to UT-24 (Section 8.1).

# 5. Integration Testing

Integration tests call the REST API through the FastAPI test client, which runs routers, services and repositories against a real PostgreSQL database. They follow the flows in the SDD sequence diagrams: search, book and pay, cancel and promote, and each scheduled job. Integration follows a **bottom-up** order: repositories and inventory first, then booking and payment, then cancellation and waitlist, then jobs and admin. Test cases: IT-01 to IT-36 (Section 8.2).

# 6. System Testing

System tests run against the complete application in a browser using Playwright, plus scripted checks for non-functional requirements:

- **Functional:** complete user journeys for guests, passengers and administrators (ST-01 to ST-07).
- **Usability and accessibility:** responsive layout at 360 px, number of screens in the booking flow, automated WCAG checks with axe (ST-08, ST-13, ST-14).
- **Concurrency and performance:** parallel payments for the last berth; search response time (ST-09, ST-10).
- **Security:** password storage, cookie flags, injection attempts, access control (ST-11, ST-12, and IT-04, IT-18).
- **Maintainability:** lint, formatting and coverage gates in CI (ST-15).

Test cases: ST-01 to ST-15 (Section 8.3).

# 7. Acceptance Testing

Acceptance tests are scenario-based and are carried out on the deployed system by group members acting as the user classes in SRS Section 4.3. Each scenario covers one or more user requirements, and the system is accepted when every scenario passes. Test cases: AT-01 to AT-08 (Section 8.4).

# 8. Test Cases, Expected and Actual Results

Status values: **Pass**, **Fail**, **Blocked**, **Not run**. Actual results are recorded when each test is executed; a failed test references its defect ID (Section 10).

## 8.1 Unit test cases

<div class="tc" markdown="1">

| ID | Req. | Test case and input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| UT-01 | BR-04 | Fare, SL, 400 km | Base ₹180, reservation ₹20, GST ₹0, total ₹200 | | Not run |
| UT-02 | BR-04 | Fare, 3A, 400 km | Base ₹480, reservation ₹40, GST ₹26, total ₹546 | | Not run |
| UT-03 | BR-04 | Fare, 2A, 250 km (437.50 below minimum) | Base ₹450 (minimum applies), reservation ₹50, GST ₹25, total ₹525 | | Not run |
| UT-04 | BR-04 | Fare, 1A, 250 km | Base ₹800 (minimum), reservation ₹60, GST ₹43, total ₹903 | | Not run |
| UT-05 | BR-06 | Refund, CNF, 3A fare ₹1806, 72 h before departure | Deduction ₹180 (flat fee), refund ₹1626.00 | | Not run |
| UT-06 | BR-06 | Refund, CNF, 3A fare ₹1806, exactly 48 h before | 25% slab: deduction ₹451.50, refund ₹1354.50 | | Not run |
| UT-07 | BR-06 | Refund, CNF, 3A fare ₹1806, exactly 12 h before | 25% slab: refund ₹1354.50 | | Not run |
| UT-08 | BR-06 | Refund, CNF, 3A fare ₹1806, 6 h before | 50% slab: refund ₹903.00 | | Not run |
| UT-09 | BR-06 | Refund, CNF, SL fare ₹200, 24 h before (25% = ₹50 is below the flat fee) | Deduction ₹120 (flat fee floor), refund ₹80.00 | | Not run |
| UT-10 | BR-06 | Refund, WL passenger, fare ₹546 | Refund ₹486.00 (fare minus ₹60) | | Not run |
| UT-11 | A-02 | CoachLayout, SL coach: types of berths 1 to 8, and berth 72 | LB, MB, UB, LB, MB, UB, SL, SU; berth 72 is SU; coach has 72 berths | | Not run |
| UT-12 | A-02 | CoachLayout, 2A coach: berth 5; 3A coach size | Berth 5 is SL; 3A coach has 64 berths | | Not run |
| UT-13 | BR-10 | Segment overlap: [1,3) with [3,4); [1,3) with [2,4) | First pair does not overlap; second pair overlaps | | Not run |
| UT-14 | FR-BKG-05 | Allocate 6 passengers with 4 free berths, waitlist empty | 4 passengers CNF with distinct berths, 2 WL | | Not run |
| UT-15 | FR-BKG-09 | Allocate 1 passenger preferring LB; free berths 2 (MB) and 4 (LB) | Berth 4 (LB) allocated | | Not run |
| UT-16 | FR-BKG-08 | Allocate 3 passengers with "confirm only", 2 free berths | Plan rejected; no berths allocated | | Not run |
| UT-17 | BR-05 | Allocate 2 passengers, 0 free berths, 19 already waitlisted | Plan rejected (would make 21 waitlisted) | | Not run |
| UT-18 | FR-TKT-01 | Generate 10,000 PNRs | Each is 10 digits, first digit 1 to 9; all unique | | Not run |
| UT-19 | FR-BKG-02, 03 | Validate passengers: name "A"; age 0; age 121; gender "X"; 7 passengers; 6 valid passengers | First five rejected with field errors; 6 valid passengers accepted | | Not run |
| UT-20 | NFR-05 | Hash "Secret@123", verify with "Secret@123" and "secret@123" | Hash starts with `$2b$` and differs from the input; first verifies, second does not | | Not run |
| UT-21 | FR-SRCH-03 | Train running Mon/Wed/Fri: `runs_on` for a Monday and a Tuesday | True for Monday, false for Tuesday | | Not run |
| UT-22 | BR-02 | Chart cut-off for run date 10 Nov 2026 | 9 Nov 2026 18:00 IST | | Not run |
| UT-23 | FR-TKT-05 | Mask name "Rahul Sharma" | "Ra*** Sh****" | | Not run |
| UT-24 | SR-04 | MockPaymentGateway with each test card and UPI ID; refund | Approve cards/IDs succeed with a reference; decline ones fail; refund succeeds | | Not run |

</div>

## 8.2 Integration test cases

<div class="tc" markdown="1">

| ID | Req. | Test case and input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| IT-01 | FR-AUTH-01, 02 | Register new user; register again with same e-mail | 201 Created; second request 409 Conflict | | Not run |
| IT-02 | FR-AUTH-03, 04 | Log in with correct password; wrong password; log out | 200 with session cookie; 401; logout clears cookie | | Not run |
| IT-03 | NFR-10 | Six failed logins for one account within a minute | Attempts 1 to 5 get 401; attempt 6 gets 429 | | Not run |
| IT-04 | FR-AUTH-05, NFR-08 | Call `/bookings` without a session; passenger calls `/admin/stations` | 401; 403 | | Not run |
| IT-05 | FR-SRCH-01 | `GET /stations?q=bra` | Returns STB Bravo | | Not run |
| IT-06 | FR-SRCH-02, 03, 04 | Search STB → STD on a Wednesday; search STD → STB | Train 90001 with departure, arrival, duration, 300 km; reverse search returns nothing | | Not run |
| IT-07 | FR-SRCH-03 | Search STA → STD on a Tuesday | No results (train does not run) | | Not run |
| IT-08 | FR-SRCH-05 | Search STA → STA; a past date; a date 61 days ahead | 422 for each with a validation message | | Not run |
| IT-09 | FR-AVL-02, BR-10 | S1 has 2 berths; book 2 passengers STA → STB; check availability for STB → STD and STA → STC | STB → STD shows AVAILABLE 2; STA → STC shows WL | | Not run |
| IT-10 | FR-BKG-01, 04, FR-AVL-04 | Create booking: 2 passengers, SL, STA → STD | 201; status PENDING_PAYMENT; total ₹400; expires in 15 minutes | | Not run |
| IT-11 | FR-PAY-02, FR-TKT-01, 02 | Pay booking from IT-10 with approve card | 200; status BOOKED; 10-digit PNR; both passengers CNF with distinct berths in S1 | | Not run |
| IT-12 | FR-PAY-03 | Pay with decline card | 402; booking still PENDING_PAYMENT; one FAILED payment recorded | | Not run |
| IT-13 | FR-PAY-03 | After IT-12, pay again with approve card | 200; BOOKED | | Not run |
| IT-14 | FR-PAY-05 | Send the same successful pay request twice | Second response equals the first; exactly one SUCCESS payment exists | | Not run |
| IT-15 | BR-08 | Pay 16 minutes after booking creation | 410; booking EXPIRED; no payment charged | | Not run |
| IT-16 | FR-BKG-05, FR-WL-01 | S1 has 2 berths; book 3 passengers | 2 CNF, third WL with position 1 | | Not run |
| IT-17 | FR-BKG-06 | Berths and waitlist (20) full; book 1 passenger and pay | 409; booking FAILED; no payment record | | Not run |
| IT-18 | NFR-08 | passenger2 opens passenger1's booking and ticket | 404 for both | | Not run |
| IT-19 | FR-CAN-02 | Cancellation quote for a CNF passenger 72 h before departure (SL ₹200) | Refund ₹80.00, matching UT-09 rules | | Not run |
| IT-20 | FR-CAN-01, 03 | Cancel one of two passengers | That passenger CAN with refund; other unchanged; booking BOOKED; refund recorded | | Not run |
| IT-21 | FR-WL-02, 03, BR-07 | S1 full with WL 1 and WL 2; cancel one CNF passenger | WL 1 becomes CNF on the released berth; WL 2 becomes WL 1 | | Not run |
| IT-22 | FR-WL-02, BR-10 | Released berth is free only for STA → STB; WL 1 needs STA → STD, WL 2 needs STA → STB | WL 1 stays waitlisted; WL 2 is confirmed | | Not run |
| IT-23 | FR-CAN-05 | Cancel all passengers of a booking | Booking CANCELLED | | Not run |
| IT-24 | FR-CAN-04, BR-02 | Cancel after the chart cut-off time | 409; nothing changes | | Not run |
| IT-25 | FR-TKT-03 | Download ticket for a BOOKED booking | 200, `application/pdf`; text contains the PNR and passenger names | | Not run |
| IT-26 | FR-TKT-05 | `GET /pnr/{pnr}` without login | 200 with statuses; names masked | | Not run |
| IT-27 | FR-WL-04, FR-JOB-02, 05 | Run chart preparation for tomorrow's run with 2 WL passengers; run it again | WL passengers CAN with full refund; run CHART_PREPARED; second run processes 0 runs | | Not run |
| IT-28 | FR-JOB-01, 05 | Run generation job on an empty schedule; run again | Runs created only for Mon/Wed/Fri within 60 days; second run creates 0 | | Not run |
| IT-29 | FR-JOB-03 | Journey completion after the arrival time of a run | Run COMPLETED; its BOOKED bookings COMPLETED | | Not run |
| IT-30 | FR-JOB-04 | Payment expiry job with a 20-minute-old pending booking | Booking EXPIRED | | Not run |
| IT-31 | SR-05 | Call a job endpoint with no token and with a wrong token | 401 for both; job does not run | | Not run |
| IT-32 | FR-ADM-05 | Admin cancels a run with CNF and WL passengers | All bookings CANCELLED; every passenger refunded in full; run CANCELLED | | Not run |
| IT-33 | NFR-03 | Insert two CNF passengers with the same berth and overlapping segments directly in the database | Second insert rejected by the exclusion constraint | | Not run |
| IT-34 | FR-ADM-01 | Admin creates station with an existing code | 409 | | Not run |
| IT-35 | FR-ADM-03 | Admin saves a route with one stop; with stops out of distance order | 422 for both | | Not run |
| IT-36 | NFR-03, FR-BKG-07 | 10 bookings for the same last berth paid in parallel threads | Exactly 1 CNF, others WL; no duplicate berth | | Not run |

</div>

## 8.3 System test cases

<div class="tc" markdown="1">

| ID | Req. | Test case | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| ST-01 | UR-01, UR-02 | Guest searches between two seeded stations for a valid date | Result list shows trains, times, duration, availability and fare per class | | Not run |
| ST-02 | UR-05 to 07 | Register, log in, search, book 2 passengers, pay with approve card, download ticket | Confirmation page shows PNR and berths; PDF downloads and opens | | Not run |
| ST-03 | UR-08, UR-09 | Open My bookings; cancel one passenger | Booking listed under upcoming; refund shown before confirm; status updates after | | Not run |
| ST-04 | FR-PAY-03 | Pay with decline card, then with approve card | Clear error after first attempt; booking confirmed after second | | Not run |
| ST-05 | UR-03 | Guest checks PNR status of the booking from ST-02 | Statuses shown; names masked | | Not run |
| ST-06 | UR-11, UR-12 | Admin creates a station and a train with route and coaches, generates runs | New train appears in search for its running days | | Not run |
| ST-07 | UR-13 | Admin opens the passenger chart of the run from ST-02 | Chart lists passengers with coach, berth, segment and status | | Not run |
| ST-08 | NFR-12 | Run ST-02 at 360 px viewport width | All steps complete; no horizontal scrolling | | Not run |
| ST-09 | NFR-03 | Script sends 20 parallel pay requests for 20 bookings competing for 1 remaining berth on the deployed API | Exactly 1 passenger CNF on that berth | | Not run |
| ST-10 | NFR-01 | 50 sequential searches after warm-up on the deployed API | 95th percentile response time under 2 s | | Not run |
| ST-11 | NFR-05, 06 | Inspect stored user row; inspect session cookie | Password column holds a bcrypt hash; cookie is HttpOnly, Secure, SameSite=Lax | | Not run |
| ST-12 | NFR-07 | Station search with `' OR 1=1 --`; booking with script tag in name | Empty result, no server error; name rejected by validation | | Not run |
| ST-13 | NFR-13 | axe scan of search, booking, payment and my bookings pages | No serious or critical violations | | Not run |
| ST-14 | NFR-11 | Count screens from search results to confirmation | 5 or fewer | | Not run |
| ST-15 | NFR-15, 16 | CI run on `main` | Lint and format checks pass; service-layer coverage at least 80% | | Not run |

</div>

## 8.4 Acceptance test cases

<div class="tc" markdown="1">

| ID | User req. | Scenario | Acceptance criterion | Actual result | Status |
|---|---|---|---|---|---|
| AT-01 | UR-01, 02, 04 | A new visitor plans a trip, compares classes and registers | Visitor finds a train, sees fares and availability, and creates an account without help | | Not run |
| AT-02 | UR-05, 06, 07 | A passenger books for a family of four and prints the ticket | Booking confirmed in one session; ticket PDF shows all four travellers | | Not run |
| AT-03 | UR-06, UR-10 | A passenger books on a nearly full train and is waitlisted; another passenger cancels | First passenger sees WL status, then CNF after the cancellation | | Not run |
| AT-04 | UR-08, UR-09 | A passenger cancels one traveller from an upcoming trip | Refund shown before confirming matches the published rules | | Not run |
| AT-05 | UR-03 | A relative checks a PNR without an account | Status shown without login; names masked | | Not run |
| AT-06 | UR-11, UR-12 | Administrator adds a new train and opens it for booking | Train bookable within the ARP without technical help | | Not run |
| AT-07 | UR-13 | Administrator checks who is travelling on a run | Passenger chart is complete and matches bookings | | Not run |
| AT-08 | UR-14 | Administrator cancels a train run | Every affected passenger sees the cancellation and a full refund | | Not run |

</div>

# 9. Test Summary

This section is completed after test execution.

| Level | Planned | Executed | Passed | Failed | Blocked |
|---|---|---|---|---|---|
| Unit | 24 | | | | |
| Integration | 36 | | | | |
| System | 15 | | | | |
| Acceptance | 8 | | | | |
| **Total** | **83** | | | | |

# 10. Defect Reporting

## 10.1 Process

Defects are recorded as GitHub Issues in the project repository, labelled with severity and priority, and linked to the failing test case. Each defect moves through this lifecycle:

**New** → **Assigned** → **Fixed** → **Retest** → **Closed**, or back to **Reopened** if the retest fails.

A defect is closed only after the failing test case passes and the full automated suite still passes.

## 10.2 Severity and priority

| Severity | Meaning | Example |
|---|---|---|
| Critical | Data corruption, security breach, or a core flow unusable | Same berth allocated twice |
| Major | A requirement not met, with no workaround | Wrong refund amount |
| Minor | A requirement partly met, or a workaround exists | Sort order ignored |
| Trivial | Cosmetic | Misaligned label |

| Priority | Meaning |
|---|---|
| P1 | Fix before any further testing |
| P2 | Fix before release |
| P3 | Fix if time allows |

## 10.3 Defect report fields

| Field | Content |
|---|---|
| Defect ID | DEF-nn |
| Title | One-line summary |
| Test case | ID of the test that found it |
| Requirement | Requirement ID affected |
| Severity, priority | From Section 10.2 |
| Environment | Local, CI or deployed; browser if relevant |
| Steps to reproduce | Numbered steps |
| Expected and actual result | As observed |
| Root cause and fix | Filled in when fixed, with commit reference |
| Status | Current lifecycle state |

## 10.4 Defect log

This log is completed during test execution.

| Defect ID | Title | Test case | Severity | Priority | Status | Fix |
|---|---|---|---|---|---|---|
| | | | | | | |

# Appendix A. Requirements Coverage

| Requirement group | Test cases |
|---|---|
| FR-AUTH | IT-01 to IT-04, UT-20 |
| FR-SRCH | IT-05 to IT-08, UT-21, ST-01 |
| FR-AVL, BR-04 | UT-01 to UT-04, IT-09, IT-10, ST-01 |
| FR-BKG, BR-03, BR-05, BR-10 | UT-13 to UT-17, UT-19, IT-09 to IT-17, IT-36, ST-02 |
| FR-PAY, BR-08 | UT-24, IT-11 to IT-15, ST-04 |
| FR-TKT | UT-18, UT-23, IT-25, IT-26, ST-02, ST-05 |
| FR-CAN, BR-06 | UT-05 to UT-10, IT-19 to IT-24, ST-03 |
| FR-WL, BR-07 | IT-16, IT-21, IT-22, IT-27, AT-03 |
| FR-ADM | IT-32, IT-34, IT-35, ST-06, ST-07 |
| FR-JOB, BR-02 | UT-22, IT-27 to IT-31 |
| Non-functional | ST-08 to ST-15, IT-03, IT-33, IT-36 |
| User requirements | AT-01 to AT-08 |
