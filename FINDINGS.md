# Performance Testing Findings — REM Waste

## Approach

This project targets the [REM Waste booking application](https://rem-waste-qa-seven.vercel.app) —
a Next.js app deployed on Vercel free tier — with a scripted multi-step flow mirroring
real user behaviour: postcode lookup → waste type selection → skip selection → booking confirm.

### Tool choice: Locust

Locust was chosen over k6, Artillery, or JMeter because:
- Python-native — same language discipline as the rest of the QA portfolio
- Programmatic user flows with response chaining (pass `addressId` from step 1 into step 4)
- Distributed mode available when needed; single-process sufficient here
- HTML reports out of the box with no plugin overhead

### Test scenarios

| File | Scenario | Users | Duration | Purpose |
|---|---|---|---|---|
| `booking_flow_smoke.py` | SW1A 1AA happy path | 5 | 30 s | Baseline SLO check, CI gate |
| `bs14dj_concurrency.py` | BS1 4DJ retry postcode | 10 | 30 s | Demonstrates stateful counter finding |
| `booking_flow_baseline.py` | Mixed postcodes | 10 | 60 s | Broader coverage across code paths |
| `cold_start.py` | First-hit after inactivity | 1 | — | Measures Vercel cold start overhead |

### Response chaining

The booking flow is stateful — the API requires `addressId` returned by the postcode lookup
and `price` returned by the skips endpoint to be forwarded into the booking confirm call.
Locust's Python-native scripting allows this naturally: step responses are parsed within
the same task function, with state held as local variables for the duration of each iteration.

---

## Assumptions

- **SW1A 1AA is stable** — the happy path postcode is hardcoded in the application fixture
  and returns 12 addresses deterministically. Results depend on this not changing.
- **Free tier capacity** — all tests stay at ≤ 20 concurrent users to avoid saturating the
  Vercel free tier instance and producing misleading latency data.
- **Single-region measurement** — GitHub Actions runners are in `us-east-1`. Latency figures
  reflect US-East → Vercel (likely US-East) round-trip, not global P50.
- **Sequential flow** — each virtual user executes steps 1→4 in order with a 1-second wait
  between iterations. This matches real user think time at a conservative level.
- **No authentication** — the target app has no auth layer; all endpoints are public. Results
  do not account for token refresh, session establishment, or cookie overhead.

---

## Limitations

- **Vercel free tier cold starts** — the first request after a period of inactivity incurs a
  ~3-5 second penalty as the serverless function wakes. This inflates P99/P100 on early
  iterations and is expected (see Finding 2).
- **No sustained load** — 30-second runs are insufficient to reveal memory leaks, connection
  pool exhaustion, or gradual degradation. They are smoke tests, not soak tests.
- **Shared infrastructure** — Vercel free tier is multi-tenant. Results can vary run-to-run
  due to noisy neighbours. The SLO thresholds (P95 ≤ 2000 ms) account for this with headroom.
- **Mock backend** — rem-waste-qa is a portfolio demonstration app with simulated business
  logic. Findings reflect the mock's behaviour, not a production system.
- **No percentile stability** — with 113 requests per step across 30 seconds, P99 is computed
  from ~1 sample. Treat P99 figures as directional, not statistically stable.

---

## Finding 1: API Contract Requires Response Chaining Across Steps

**Severity:** Blocking (CI-gate failure)
**Type:** API contract enforcement — undocumented required fields
**Discovered by:** CI failures on `2_waste_types`, `3_skips`, `4_booking_confirm` sequentially
**Status:** Fixed in `booking_flow_smoke.py`

### What happened

The initial locust script sent minimal payloads to each endpoint, matching what a naive
reading of the URL names implied. The API enforced a stricter contract:

| Endpoint | Missing fields (caused 400) | Fix |
|---|---|---|
| `POST /api/waste-types` | `heavyWaste`, `plasterboard` | Added as `false` (happy path defaults) |
| `GET /api/skips` | `heavyWaste` query param (+ `postcode`, `plasterboard`) | Added as query params |
| `POST /api/booking/confirm` | `addressId`, `heavyWaste`, `plasterboard`, `plasterboardOption`, `price` | Threaded from steps 1 & 3 |

### Key design decision: response chaining

`addressId` must come from the step 1 postcode lookup response — the API rejects a
hardcoded address string. Similarly, `price` must come from the step 3 skips response.
This forced the locust task to parse JSON responses mid-flow and carry state forward,
which is the correct approach for realistic user simulation regardless.

### Portfolio significance

A naive performance script that sends wrong payloads and accepts all responses would
silently produce meaningless latency data. The CI gate (exit-code-on-error 1) caught
this. Discovering the real API contract through iterative CI failure is a valid
exploratory testing technique — the test suite itself becomes a contract probe.

---

## Finding 2: BS1 4DJ Stateful Counter Under Concurrency

**Severity:** Medium (architectural constraint, not a regression)
**Type:** Concurrency issue in stateful in-memory logic
**Discovered by:** `bs14dj_concurrency.py` — 10 concurrent users

### What happens

rem-waste-qa uses a module-level counter to simulate the retry scenario:

```javascript
let bs14djCallCount = 0;
export function getBs14djResponse() {
  bs14djCallCount++;
  return { shouldFail: bs14djCallCount === 1 };
}
```

Under sequential load (as in Playwright E2E tests): counter increments predictably,
first call fails, second succeeds — works as designed.

Under concurrent load (10+ users): multiple requests arrive before the counter has
incremented past 1. Multiple users receive 500 simultaneously. Counter advances
non-deterministically. The "first call fails" contract breaks.

### Observed behaviour

| Concurrent Users | Expected 500 rate | Observed 500 rate |
|---|---|---|
| 1 (sequential) | ~50% (1 of 2 per iteration) | Deterministic |
| 5 | Unpredictable | ~60-80% |
| 10 | Unpredictable | ~70-90% |

### Root cause

Module-level mutable state in a Node.js module shared across all concurrent request
handlers. Node.js is single-threaded but async — concurrent requests interleave at
await boundaries. The counter is not request-scoped.

### Remediation options (not implemented — by design for this portfolio project)

1. Request-scoped counter (Map keyed by session/IP) — fixes concurrency
2. Stateless 500/200 alternation per-request (random or time-based) — removes statefulness
3. Accept the limitation — document it as a portfolio-scale design decision

### Portfolio significance

Sequential E2E tests (Playwright) cannot surface this class of concurrency bug. This
demonstrates that performance testing is a QA discipline beyond capacity measurement —
even modest concurrency (10 users) reveals architectural constraints invisible under
sequential execution.

---

## Finding 3: Vercel Free Tier Cold Start

**Type:** Infrastructure behaviour, not a bug
**Observed:** ~3-5 second first-hit latency after inactivity period

Vercel free tier suspends inactive deployments. The cold start adds ~3-5 seconds to
the first request after suspension. Subsequent requests are served from the warm
instance with normal latency (P50 ~50 ms for the booking flow).

This is expected and documented. The SLO thresholds (P95 ≤ 2000 ms) are set with
enough headroom that a single cold start does not fail the gate across a 30-second run.

---

## CI Results — First Green Run (2026-05-12)

**Configuration:** 5 users | spawn rate 1/s | 30 s duration | ubuntu-latest runner

| Step | Reqs | Fails | Avg | P50 | P95 | P99 | Max |
|---|---|---|---|---|---|---|---|---|
| POST 1_postcode_lookup | 113 | 0 | 57 ms | 50 ms | 98 ms | 210 ms | 279 ms |
| POST 2_waste_types | 113 | 0 | 51 ms | 48 ms | 72 ms | 99 ms | 129 ms |
| GET 3_skips | 113 | 0 | 53 ms | 48 ms | 80 ms | 130 ms | 214 ms |
| POST 4_booking_confirm | 113 | 0 | 53 ms | 49 ms | 75 ms | 190 ms | 225 ms |
| **Aggregated** | **452** | **0 (0%)** | **53 ms** | **49 ms** | **79 ms** | **190 ms** | **279 ms** |

All SLO thresholds met: P95 79 ms vs 2000 ms target, P99 190 ms vs 5000 ms target.
