# locustfiles/cold_start.py
from __future__ import annotations
from locust import HttpUser, task, constant
from config import POSTCODE_LOOKUP, POSTCODE_HAPPY_PATH


class ColdStartUser(HttpUser):
    """
    Single-user test to measure Vercel cold start latency.
    
    Vercel free tier suspends inactive deployments. The first request
    after suspension experiences a cold start penalty (~3-5 seconds).
    This test captures that baseline.
    
    1 user, 60 seconds — measures first-hit time explicitly.
    """
    wait_time = constant(5)   # 5-second spacing between requests

    @task
    def measure_cold_start(self) -> None:
        """Single postcode lookup to measure response time"""
        with self.client.post(
            POSTCODE_LOOKUP,
            json={"postcode": POSTCODE_HAPPY_PATH},
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="cold_start_hit",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Cold start hit failed: {r.status_code}")
                return
            r.success()
