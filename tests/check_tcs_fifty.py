#!/usr/bin/env python3
"""
tests/check_tcs_fifty.py  v2.0
v2.0  2026-09-09  OTV4TEST r9 — RETIRED, NOT PATCHED. F1–F3 pinned r238's trigger
      (the ORB's fifty_accepted), the spot anchor and the widest wing. The
      trigger and the anchor are gone with the TCS spec (PLAN_SPEC §34); the
      widest-wing rule survives and is pinned in check_tcs_plan T2b. This file
      delegates so a stale CHECK line still runs the live pins.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.check_tcs_plan import main  # noqa: E402
if __name__ == "__main__":
    sys.exit(main())
