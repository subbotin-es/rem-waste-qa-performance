# locustfiles/booking_flow_baseline.py
from __future__ import annotations
from locust import HttpUser, task, constant
from config import (
    POSTCODE_LOOKUP, WASTE_TYPES, SKIPS, BOOKING_CONFIRM,
    POSTCODE_HAPPY_PATH, POSTCODE_EMPTY, POSTCODE_SLOW,
)


class BookingFlowBaselineUser(HttpUser):
    """
    Mixed booking flow under moderate load.
    Uses multiple postcode scenarios to stress different code paths.
    10 users, 60 seconds.
    """
    wait_time = constant(1)

    @task(2)
    def complete_happy_path_flow(self) -> None:
        """SW1A 1AA — happy path, 200 addresses"""
        self._execute_booking_flow(POSTCODE_HAPPY_PATH, "general", "4-yard")

    @task(1)
    def complete_empty_state_flow(self) -> None:
        """EC1A 1BB — empty state, 0 addresses"""
        self._execute_booking_flow(POSTCODE_EMPTY, "heavy", "6-yard")

    @task(1)
    def complete_slow_flow(self) -> None:
        """M1 1AE — slow response, 1500ms delay"""
        self._execute_booking_flow(POSTCODE_SLOW, "garden", "8-yard")

    def _execute_booking_flow(
        self, postcode: str, waste_type: str, skip_size: str
    ) -> None:
        """Internal method to execute a complete booking flow"""
        # Step 1: Postcode lookup
        with self.client.post(
            POSTCODE_LOOKUP,
            json={"postcode": postcode},
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="postcode_lookup",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Postcode lookup failed: {r.status_code}")
                return
            r.success()

        # Step 2: Waste types
        with self.client.post(
            WASTE_TYPES,
            json={"postcode": postcode},
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="waste_types",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Waste types failed: {r.status_code}")
                return
            r.success()

        # Step 3: Skips
        with self.client.get(
            SKIPS,
            catch_response=True,
            name="skips",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Skips failed: {r.status_code}")
                return
            r.success()

        # Step 4: Confirm booking
        with self.client.post(
            BOOKING_CONFIRM,
            json={
                "postcode": postcode,
                "wasteType": waste_type,
                "skipSize": skip_size,
                "address": "Test Address",
            },
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="booking_confirm",
        ) as r:
            if r.status_code not in (200, 201):
                r.failure(f"Booking confirm failed: {r.status_code}")
                return
            r.success()
