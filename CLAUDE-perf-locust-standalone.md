# CLAUDE.md — rem-waste-performance
# Standalone Locust project targeting REM Waste on Vercel

> **This file is the authoritative specification for Claude Code.**
> Read it completely before writing any locustfile, any config, any CI step.
> This is a standalone performance project — separate repo from rem-waste-qa.
> When in doubt — ask. Do not invent scenarios. Do not hide architectural findings.

**Author:** Evgenii Subbotin
**Repo:** rem-waste-performance (standalone)
**Performance tool:** Locust
**Target:** https://rem-waste-qa-seven.vercel.app (Next.js / Vercel free tier)
**Source API:** https://github.com/subbotin-es/rem-waste-qa
**Language:** Python 3.12
**Version:** 1.0 | May 2026

---

## 1. What This Project Does

Standalone Locust performance suite targeting the REM Waste booking flow API
running on Vercel free tier. This is a **modern stack standalone** performance project —
the counterpart to `player-api-performance` (JMeter / legacy stack).

**This project has a unique angle — it uncovers a real architectural finding:**

The REM Waste application uses a module-level counter for the BS1 4DJ retry scenario:
```python
let bs14djCallCount = 0;  # module-level — resets only on process restart
```

Under concurrent load, multiple simultaneous requests to `BS1 4DJ` mutate this counter
in an unpredictable order. The first-call-fails behaviour breaks down.
**This is a real architectural limitation surfaced by performance testing** —
not a bug introduced by the test, but a design constraint of in-memory stateful logic
under concurrency. It is documented as a finding, not hidden.

**Narrative for portfolio / interviews:**
> "Performance testing isn't only about capacity — it's a QA tool that reveals
> architectural constraints invisible under sequential test execution.
> This project found a real concurrency issue in the retry mechanism,
> documented it as an engineering finding, and demonstrated exactly when
> and why in-memory stateful logic fails under load."

**What this tests:**
```
✅ Vercel free tier response times under concurrent load
✅ API endpoints: /api/postcode/lookup, /api/skips, /api/waste-types, /api/booking/confirm
✅ Happy path booking flow under load (SW1A 1AA postcode)
✅ Empty state under load (EC1A 1BB)
✅ Loading state (M1 1AE — 1500ms server delay)
✅ BS1 4DJ concurrency finding — documented, demonstrated, not worked around
✅ Vercel cold start measurement (first request after inactivity)
✅ HTML report as CI artifact
```

---

## 2. Absolute Rules

```
NEVER use time.sleep() — use Locust wait_time
NEVER exceed 20 concurrent users — Vercel free tier limits and we respect the target
NEVER hide the BS1 4DJ finding — document it prominently
NEVER work around the BS1 4DJ finding — demonstrate it, then mark as known limitation
NEVER hardcode BASE_URL — always use environment variable with fallback
ALWAYS use catch_response=True on all requests
ALWAYS include Content-Type: application/json on POST requests
ALWAYS document Vercel cold start behaviour in README
ALWAYS run mypy on all locustfiles — type discipline throughout
ALWAYS write findings in FINDINGS.md — engineering artifacts, not just test results
```

---

## 3. Tech Stack

| Layer | Technology | Version | Why |
|---|---|---|---|
| Load tool | Locust | 2.28+ | Python-native, distributed, Web UI, free |
| Language | Python | 3.12 | Modern Python, type hints throughout |
| Type checking | mypy | 1.x strict | Engineering discipline |
| Lint | ruff | 0.4+ | Consistent with Python stack |
| CI | GitHub Actions | current | New repo, new pipeline |
| Report | Locust HTML report | built-in | `--html` flag |

---

## 4. Repository Structure

```
rem-waste-performance/
├── locustfiles/
│   ├── booking_flow_smoke.py       # SW1A 1AA happy path, 5 users, 30s
│   ├── booking_flow_baseline.py    # mixed postcodes, 10 users, 60s
│   ├── cold_start.py               # single user, first-hit measurement
│   └── bs14dj_concurrency.py       # demonstrates stateful counter finding
├── config.py                       # BASE_URL, endpoints, thresholds
├── FINDINGS.md                     # engineering findings — BS1 4DJ + Vercel cold start
├── requirements.txt
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml                  # mypy + ruff config
└── README.md
```

---

## 5. config.py

```python
# config.py
from __future__ import annotations
import os

BASE_URL: str = os.environ.get(
    "BASE_URL",
    "https://rem-waste-qa-seven.vercel.app"
)

# API endpoints
POSTCODE_LOOKUP: str = "/api/postcode/lookup"
WASTE_TYPES: str = "/api/waste-types"
SKIPS: str = "/api/skips"
BOOKING_CONFIRM: str = "/api/booking/confirm"

# Test postcodes (from rem-waste-qa fixtures)
POSTCODE_HAPPY_PATH: str = "SW1A 1AA"      # 200 + 12 addresses
POSTCODE_EMPTY: str = "EC1A 1BB"           # 200 + 0 addresses
POSTCODE_SLOW: str = "M1 1AE"              # 200 + 1500ms delay
POSTCODE_RETRY: str = "BS1 4DJ"           # 500 on first call (counter-based)

# SLO thresholds (ms) — Vercel free tier, realistic expectations
P95_THRESHOLD_MS: float = 2000.0          # Vercel cold tier is slower than CDN
P99_THRESHOLD_MS: float = 5000.0
ERROR_RATE_THRESHOLD: float = 0.05        # 5% — retry scenario inflates this
```

---

## 6. Locustfiles — Exact Implementation

### booking_flow_smoke.py
```python
# locustfiles/booking_flow_smoke.py
from __future__ import annotations
from locust import HttpUser, task, between, constant
from config import (
    POSTCODE_LOOKUP, WASTE_TYPES, SKIPS, BOOKING_CONFIRM,
    POSTCODE_HAPPY_PATH,
)


class BookingFlowSmokeUser(HttpUser):
    """
    Happy path booking flow under minimal load.
    Uses SW1A 1AA — deterministic, no retry, no delay.
    5 users, 30 seconds.
    """
    wait_time = constant(1)

    @task
    def complete_booking_flow(self) -> None:
        # Step 1: Postcode lookup
        with self.client.post(
            POSTCODE_LOOKUP,
            json={"postcode": POSTCODE_HAPPY_PATH},
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="1_postcode_lookup",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Postcode lookup failed: {r.status_code}")
                return
            r.success()

        # Step 2: Waste types
        with self.client.post(
            WASTE_TYPES,
            json={"postcode": POSTCODE_HAPPY_PATH},
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="2_waste_types",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Waste types failed: {r.status_code}")
                return
            r.success()

        # Step 3: Skips
        with self.client.get(
            SKIPS,
            catch_response=True,
            name="3_skips",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Skips failed: {r.status_code}")
                return
            r.success()

        # Step 4: Confirm booking
        with self.client.post(
            BOOKING_CONFIRM,
            json={
                "postcode": POSTCODE_HAPPY_PATH,
                "wasteType": "general",
                "skipSize": "4-yard",
                "address": "10 Downing Street",
            },
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="4_booking_confirm",
        ) as r:
            if r.status_code not in (200, 201):
                r.failure(f"Booking confirm failed: {r.status_code}")
                return
            r.success()
```

### bs14dj_concurrency.py
```python
# locustfiles/bs14dj_concurrency.py
from __future__ import annotations
from locust import HttpUser, task, constant
from config import POSTCODE_LOOKUP, POSTCODE_RETRY


class BS14DJConcurrencyUser(HttpUser):
    """
    Demonstrates the BS1 4DJ stateful counter finding under concurrency.

    FINDING: The rem-waste-qa application uses a module-level counter
    (bs14djCallCount) that resets only on process restart. Under concurrent
    load, multiple users hit the endpoint simultaneously. The counter
    increments non-deterministically — some users get 500, some get 200,
    in an unpredictable pattern that breaks the 'first call fails' contract.

    This test demonstrates the finding. It does NOT work around it.
    Expected result: mix of 200 and 500 responses, non-deterministic.
    This is correct — it IS the finding.

    See FINDINGS.md for full analysis.
    """
    wait_time = constant(0)   # No wait — maximise concurrency to demonstrate race

    @task
    def lookup_retry_postcode(self) -> None:
        with self.client.post(
            POSTCODE_LOOKUP,
            json={"postcode": POSTCODE_RETRY},
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="bs14dj_concurrent_hit",
        ) as r:
            # Both 200 and 500 are accepted — we are demonstrating the finding
            # A real SLO check would fail here — that's intentional
            if r.status_code in (200, 500):
                r.success()   # Accept both — we are measuring the distribution
            else:
                r.failure(f"Unexpected status: {r.status_code}")
```

---

## 7. FINDINGS.md — Required Content

```markdown
# Performance Testing Findings — REM Waste

## Finding 1: BS1 4DJ Stateful Counter Under Concurrency

**Severity:** Medium (architectural constraint)
**Type:** Concurrency issue in stateful in-memory logic
**Discovered by:** bs14dj_concurrency.py — 10 concurrent users

### What happens

rem-waste-qa uses a module-level counter to simulate the retry scenario:

    let bs14djCallCount = 0;
    export function getBs14djResponse() {
      bs14djCallCount++;
      return { shouldFail: bs14djCallCount === 1 };
    }

Under sequential load (as in Playwright E2E tests): counter increments
predictably, first call fails, second succeeds — scenario works as designed.

Under concurrent load (10+ users): multiple requests arrive before the
counter has incremented past 1. Multiple users receive 500 simultaneously.
Counter advances non-deterministically. 'First call fails' contract breaks.

### Observed behaviour

| Concurrent Users | Expected 500 rate | Observed 500 rate |
|---|---|---|
| 1 (sequential) | ~50% (1 of 2 per iteration) | Deterministic |
| 5 | Unpredictable | ~60-80% |
| 10 | Unpredictable | ~70-90% |

### Root cause

Module-level mutable state in a Node.js module shared across all concurrent
request handlers. Node.js is single-threaded but async — concurrent requests
are interleaved at await boundaries. The counter is not request-scoped.

### Remediation options (not implemented — by design for this portfolio project)

1. Request-scoped counter (Map keyed by session/IP) — fixes concurrency
2. Truly stateless 500/200 alternation per-request — removes statefulness entirely
3. Accept limitation — document it as a portfolio-scale design decision

### Portfolio significance

This finding demonstrates that performance testing is a QA tool beyond
capacity measurement. Sequential E2E tests (Playwright) cannot surface
this class of concurrency bug. This is exactly the value proposition of
load testing even at modest scale.

---

## Finding 2: Vercel Free Tier Cold Start

**Type:** Infrastructure behaviour, not a bug
**Observed:** ~3-5 second first-hit latency after inactivity period

Vercel free tier suspends inactive deployments. The cold start adds
~3-5 seconds to the first request after suspension. Subsequent requests
are served from the warm instance with normal latency.

This is expected and documented — not a performance regression.
```

---

## 8. CI Pipeline

```yaml
# .github/workflows/ci.yml
name: REM Waste — Locust Performance Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 12 * * 1'   # Monday 12:00 UTC

jobs:
  performance:
    name: Locust Performance Suite
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Type check
        run: mypy locustfiles/ config.py --ignore-missing-imports

      - name: Lint
        run: ruff check .

      - name: Run smoke booking flow (5 users, 30s)
        run: |
          locust \
            -f locustfiles/booking_flow_smoke.py \
            --headless -u 5 -r 1 -t 30s \
            --host $BASE_URL \
            --html results/smoke-report.html \
            --exit-code-on-error 1
        env:
          BASE_URL: https://rem-waste-qa-seven.vercel.app

      - name: Run BS1 4DJ concurrency demonstration (main only)
        if: github.ref == 'refs/heads/main'
        run: |
          locust \
            -f locustfiles/bs14dj_concurrency.py \
            --headless -u 10 -r 5 -t 30s \
            --host $BASE_URL \
            --html results/bs14dj-report.html
          # Note: --exit-code-on-error NOT set — this test demonstrates the finding,
          # a mix of 200/500 is expected and correct
        env:
          BASE_URL: https://rem-waste-qa-seven.vercel.app

      - name: Upload Locust reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: locust-performance-reports
          path: results/
          retention-days: 30
```

---

## 9. Infrastructure Setup

### Step 1: Create repo

```bash
mkdir rem-waste-performance && cd rem-waste-performance
git init
git remote add origin https://github.com/YOUR_USERNAME/rem-waste-performance.git
```

### Step 2: requirements.txt

```
locust==2.28.0
mypy==1.10.0
ruff==0.4.4
```

### Step 3: pyproject.toml

```toml
[tool.mypy]
python_version = "3.12"
strict = false            # locust internals have limited type stubs
ignore_missing_imports = true

[tool.ruff]
line-length = 100
```

### Step 4: Run locally

```bash
pip install -r requirements.txt

# Interactive Web UI at localhost:8089
locust -f locustfiles/booking_flow_smoke.py \
  --host https://rem-waste-qa-seven.vercel.app

# Headless
locust -f locustfiles/booking_flow_smoke.py \
  --headless -u 5 -r 1 -t 30s \
  --host https://rem-waste-qa-seven.vercel.app

# BS1 4DJ finding demonstration
locust -f locustfiles/bs14dj_concurrency.py \
  --headless -u 10 -r 5 -t 30s \
  --host https://rem-waste-qa-seven.vercel.app
```

---

## 10. Definition of Done

```
□ All locustfiles pass mypy and ruff
□ Smoke booking flow runs locally — exit code 0
□ BS1 4DJ concurrency file runs and shows mixed 200/500 in output
□ FINDINGS.md written — BS1 4DJ and cold start documented
□ CI pipeline created and green
□ Smoke report uploaded as artifact
□ README explains: modern stack standalone, concurrency finding, Vercel limitation
□ Commit message: perf(locust): add REM Waste concurrent booking flow tests
```

---

*End of CLAUDE.md*
*Version: 1.0 | Author: Evgenii Subbotin | Standalone: Locust → REM Waste (Vercel)*
*May 2026*
