# Performance Testing Findings — REM Waste

## Finding 1: BS1 4DJ Stateful Counter Under Concurrency

**Severity:** Medium (architectural constraint)
**Type:** Concurrency issue in stateful in-memory logic
**Discovered by:** bs14dj_concurrency.py — 10 concurrent users

### What happens

rem-waste-qa uses a module-level counter to simulate the retry scenario:

```javascript
let bs14djCallCount = 0;
export function getBs14djResponse() {
  bs14djCallCount++;
  return { shouldFail: bs14djCallCount === 1 };
}
```

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
