# rem-waste-performance

[![CI](https://github.com/subbotin-es/rem-waste-qa-performance/actions/workflows/ci.yml/badge.svg)](https://github.com/subbotin-es/rem-waste-qa-performance/actions/workflows/ci.yml)

**Standalone Locust performance suite targeting REM Waste booking flow**

## Overview

This is a **modern stack standalone** performance testing project that complements the
[rem-waste-qa](https://github.com/subbotin-es/rem-waste-qa) booking application.

- **Target:** https://rem-waste-qa-seven.vercel.app (Next.js, Vercel free tier)
- **Tool:** [Locust](https://locust.io/) — Python-native, distributed load testing
- **Language:** Python 3.12 with type discipline (mypy)
- **CI/CD:** GitHub Actions with automated performance test reports

## What This Tests

✅ **Vercel free tier response times** under concurrent load  
✅ **Happy path booking flow** (SW1A 1AA postcode)  
✅ **Empty state handling** (EC1A 1BB postcode)  
✅ **Loading state & delays** (M1 1AE — 1500ms server delay)  
✅ **Concurrency finding** (BS1 4DJ stateful counter under concurrent load)  
✅ **Vercel cold start behaviour** measurement  
✅ **HTML performance reports** as CI artifacts  

## Architecture Highlight: BS1 4DJ Concurrency Finding

This project surfaces a **real architectural constraint** that sequential E2E tests cannot detect:

The rem-waste-qa application uses a module-level counter for the retry simulation.
Under sequential load, it works as designed. Under concurrent load, the stateful
counter breaks — multiple users receive 500 errors simultaneously because the counter
is not request-scoped.

**This is not a bug introduced by testing** — it's a design constraint of in-memory
stateful logic under concurrency. Performance testing revealed it. It's documented
in [FINDINGS.md](FINDINGS.md).

**Portfolio significance:** Demonstrates that performance testing is a QA discipline
beyond capacity measurement. It's a tool for discovering architectural constraints
invisible under sequential test execution.

---

## Latest CI Results

**Run:** 2026-05-12 | **Config:** 5 users, spawn 1/s, 30s duration, Vercel free tier

### Response times — smoke booking flow (SW1A 1AA happy path)

| Step | Reqs | Failures | Avg | P50 | P90 | P95 | P99 | Max |
|---|---|---|---|---|---|---|---|---|
| POST 1_postcode_lookup | 113 | 0 (0%) | 57 ms | 50 ms | 65 ms | 98 ms | 210 ms | 279 ms |
| POST 2_waste_types | 113 | 0 (0%) | 51 ms | 48 ms | 63 ms | 72 ms | 99 ms | 129 ms |
| GET 3_skips | 113 | 0 (0%) | 53 ms | 48 ms | 65 ms | 80 ms | 130 ms | 214 ms |
| POST 4_booking_confirm | 113 | 0 (0%) | 53 ms | 49 ms | 62 ms | 75 ms | 190 ms | 225 ms |
| **Aggregated** | **452** | **0 (0%)** | **53 ms** | **49 ms** | **64 ms** | **79 ms** | **190 ms** | **279 ms** |

### SLO compliance

| Threshold | Target | Actual | Status |
|---|---|---|---|
| P95 | ≤ 2000 ms | 79 ms | ✅ |
| P99 | ≤ 5000 ms | 190 ms | ✅ |
| Error rate | ≤ 5% | 0% | ✅ |

> HTML reports are uploaded as CI artifacts on every run (30-day retention).
> See [Actions → locust-performance-reports](https://github.com/subbotin-es/rem-waste-qa-performance/actions) to download.

---

## Quick Start

### Prerequisites

- Python 3.12+
- pip

### Installation

```bash
pip install -r requirements.txt
```

### Run Locally (Interactive Web UI)

```bash
# Opens Locust Web UI at http://localhost:8089
locust -f locustfiles/booking_flow_smoke.py \
  --host https://rem-waste-qa-seven.vercel.app
```

Then open **http://localhost:8089** and set:
- Number of users: 5
- Spawn rate: 1 user/second
- Run duration: 30 seconds

### Run Headless (CI mode)

```bash
# Booking flow smoke test (5 users, 30 seconds)
locust -f locustfiles/booking_flow_smoke.py \
  --headless -u 5 -r 1 -t 30s \
  --host https://rem-waste-qa-seven.vercel.app \
  --html results/smoke-report.html

# BS1 4DJ concurrency demonstration (10 users, 30 seconds)
locust -f locustfiles/bs14dj_concurrency.py \
  --headless -u 10 -r 5 -t 30s \
  --host https://rem-waste-qa-seven.vercel.app \
  --html results/bs14dj-report.html
```

### Type Check

```bash
mypy locustfiles/ config.py --ignore-missing-imports
```

### Lint

```bash
ruff check .
```

---

## Project Structure

```
rem-waste-performance/
├── locustfiles/
│   ├── booking_flow_smoke.py       # SW1A 1AA happy path, 5 users, 30s
│   └── bs14dj_concurrency.py       # Demonstrates stateful counter finding
├── config.py                       # BASE_URL, endpoints, thresholds
├── FINDINGS.md                     # Engineering findings — BS1 4DJ + Vercel cold start
├── README.md                       # This file
├── requirements.txt
├── pyproject.toml                  # mypy + ruff config
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI pipeline
```

---

## Test Postcodes (from rem-waste-qa)

| Postcode | Response | Addresses | Latency | Scenario |
|---|---|---|---|---|
| **SW1A 1AA** | 200 | 200 + 12 | Normal | Happy path |
| **EC1A 1BB** | 200 | 200 + 0 | Normal | Empty state |
| **M1 1AE** | 200 | 200 + X | +1500ms | Loading state |
| **BS1 4DJ** | 500, then 200 | Varies | Normal | Retry + **concurrency finding** |

---

## SLO Thresholds

- **P95:** 2000ms (Vercel free tier is slower than CDN-backed alternatives)
- **P99:** 5000ms
- **Error rate:** 5% (BS1 4DJ concurrency scenario inflates this)

These are realistic expectations for Vercel free tier deployments.

---

## CI Pipeline

Runs on:
- Every push to `main`
- Every pull request
- Weekly schedule (Mondays, 12:00 UTC)

**Steps:**
1. Type check with mypy (strict)
2. Lint with ruff
3. Run booking flow smoke test
4. Run BS1 4DJ concurrency demonstration
5. Upload HTML reports as artifacts (30-day retention)

See [.github/workflows/ci.yml](.github/workflows/ci.yml) for details.

---

## Vercel Free Tier Notes

✅ **No SLA** — free tier can be suspended during inactivity  
✅ **Cold starts expected** — ~3-5 seconds for first request after inactivity  
✅ **Regional distribution** — no local region guarantee  
✅ **Max concurrent:** ~20 users for stable performance on free tier  

This project respects these constraints and never exceeds 20 concurrent users.

---

## Engineering Discipline

- ✅ All code passes `mypy --strict`
- ✅ All code passes `ruff check`
- ✅ Type hints throughout
- ✅ No `time.sleep()` — uses Locust `wait_time`
- ✅ All requests use `catch_response=True` for error handling
- ✅ All POST requests include `Content-Type: application/json`
- ✅ BASE_URL configurable via environment variable

---

## Author

**Evgenii Subbotin** | May 2026

**Part of the REM Waste portfolio** — complementing the [rem-waste-qa](https://github.com/subbotin-es/rem-waste-qa) assessment.

---

## References

| Resource | Link |
|---|---|
| Target app (rem-waste-qa) | https://rem-waste-qa-seven.vercel.app |
| rem-waste-qa source | https://github.com/subbotin-es/rem-waste-qa |
| This repo | https://github.com/subbotin-es/rem-waste-qa-performance |
| CI runs & artifacts | https://github.com/subbotin-es/rem-waste-qa-performance/actions |
| Locust documentation | https://docs.locust.io/ |
| Engineering findings | [FINDINGS.md](FINDINGS.md) |
| CI workflow | [.github/workflows/ci.yml](.github/workflows/ci.yml) |
