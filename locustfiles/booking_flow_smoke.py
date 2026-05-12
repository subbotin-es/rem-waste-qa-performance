# locustfiles/booking_flow_smoke.py
from __future__ import annotations
from locust import HttpUser, task, constant
from config import (
    POSTCODE_LOOKUP, WASTE_TYPES, SKIPS, BOOKING_CONFIRM,
    POSTCODE_HAPPY_PATH,
)

_HEAVY_WASTE = False
_PLASTERBOARD = False


class BookingFlowSmokeUser(HttpUser):
    """
    Happy path booking flow under minimal load.
    Uses SW1A 1AA — deterministic, no retry, no delay.
    5 users, 30 seconds.
    """
    wait_time = constant(1)

    @task
    def complete_booking_flow(self) -> None:
        # Step 1: Postcode lookup — extract addressId for later steps
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
            addresses = r.json().get("addresses", [])
            if not addresses:
                r.failure("Postcode lookup returned no addresses")
                return
            address_id = addresses[0]["id"]
            r.success()

        # Step 2: Waste types
        with self.client.post(
            WASTE_TYPES,
            json={"postcode": POSTCODE_HAPPY_PATH, "heavyWaste": _HEAVY_WASTE, "plasterboard": _PLASTERBOARD},
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="2_waste_types",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Waste types failed: {r.status_code}")
                return
            r.success()

        # Step 3: Skips — extract price for booking confirm
        with self.client.get(
            SKIPS,
            params={"postcode": POSTCODE_HAPPY_PATH, "heavyWaste": "false", "plasterboard": "false"},
            catch_response=True,
            name="3_skips",
        ) as r:
            if r.status_code != 200:
                r.failure(f"Skips failed: {r.status_code}")
                return
            skips = r.json().get("skips", [])
            skip = next((s for s in skips if s["size"] == "4-yard"), skips[0] if skips else None)
            if skip is None:
                r.failure("Skips response returned no skips")
                return
            skip_price = skip["price"]
            r.success()

        # Step 4: Confirm booking
        with self.client.post(
            BOOKING_CONFIRM,
            json={
                "postcode": POSTCODE_HAPPY_PATH,
                "addressId": address_id,
                "wasteType": "general",
                "skipSize": "4-yard",
                "heavyWaste": _HEAVY_WASTE,
                "plasterboard": _PLASTERBOARD,
                "plasterboardOption": "none",
                "price": skip_price,
            },
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="4_booking_confirm",
        ) as r:
            if r.status_code not in (200, 201):
                r.failure(f"Booking confirm failed: {r.status_code}")
                return
            r.success()
