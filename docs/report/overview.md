---
title: About this Report
version: 1.1
date: 4 November 2026
---

# About this Report

## The project

**Berth** is an online train ticket reservation system built for Assignment 3. Passengers search trains between stations, see berth availability and fares by class, book for up to six travellers, pay through a simulated gateway, download a PDF e-ticket and cancel with a rule-based refund. Waitlisted passengers are confirmed automatically when berths are released, and daily jobs prepare charts and open bookings 60 days ahead. Administrators manage stations, trains, routes, coaches and train runs.

The report follows the engineering sequence the group used: requirements (Part I), then design (Part II), then a test plan written before implementation (Part III), and finally the report of executing that plan (Part IV). The system described is built, tested and deployed.

| | |
|---|---|
| Live system | https://berth-76rn.vercel.app |
| API documentation | https://berth-ebon.vercel.app/api/docs |
| Source code | https://github.com/KrityaRajansh/berth |
| Technology | React and TypeScript, Python FastAPI, PostgreSQL; hosted on Vercel and Neon at no cost |
| Testing | 83 planned test cases, all passed; 130 automated tests; 95% backend coverage |
| Trying it | Payments are simulated: card `4111 1111 1111 1111` approves, `4000 0000 0000 0002` declines |

## How this report covers the brief

<div class="cols3" markdown="1">
<div markdown="1">

**Requirements (Part I)**

| Brief item | Section |
|---|---|
| Introduction | I-1 |
| Problem statement | I-2 |
| Objectives | I-3 |
| Scope of the system | I-4 |
| Functional requirements | I-5 |
| Non-functional requirements | I-6 |
| User requirements | I-7 |
| System requirements | I-8 |
| Hardware and software requirements | I-9 |
| Assumptions and constraints | I-10 |

</div>
<div markdown="1">

**Design (Part II)**

| Brief item | Section |
|---|---|
| System architecture | II-2 |
| Module and component description | II-3 |
| Database design (optional) | II-4 |
| Class diagram | II-5 |
| Use case diagram | II-6 |
| Sequence diagram | II-7 |
| State diagram | II-8 |

</div>
<div markdown="1">

**Testing (Parts III and IV)**

| Brief item | Section |
|---|---|
| Testing objectives | III-1 |
| Testing scope | III-2 |
| Testing strategy | III-3 |
| Unit testing | III-4, IV-3 |
| Integration testing | III-5, IV-4 |
| System testing | III-6, IV-5 |
| Acceptance testing | III-7, IV-6 |
| Test cases | III-4 to 7 |
| Expected results | III-4 to 7 |
| Actual results | IV-3 to 6 |
| Pass/Fail status | IV-2 to 6 |
| Defect reporting | III-8, IV-7 |

</div>
</div>

## Diagrams in this report

| Part | Diagrams |
|---|---|
| I. Requirements | System context; functional areas |
| II. Design | Component (architecture); deployment; entity relationship; class (domain, services, jobs); use case (passenger, operations); activity (booking); sequence (search, booking, cancellation, chart preparation); state (booking, passenger, train run) |
| III. Test Plan | V-model; defect lifecycle |
| IV. Test Report | Test pyramid; coverage by module; screenshots of executed scenarios |
