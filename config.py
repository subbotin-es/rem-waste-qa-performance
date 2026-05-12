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
