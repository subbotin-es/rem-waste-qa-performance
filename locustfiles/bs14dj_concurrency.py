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
