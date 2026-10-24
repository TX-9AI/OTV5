"""
tools/debug_status.py  v4.2
v4.2  2026-09-26  OTV4TEST r146 — the OT_INSTRUMENT fallback is UNSET, not QQQ (the unit is still read first).
v4.1  2026-09-11  OTV4TEST r14 — moved from the repo root to tools/ (root cleanup); no behaviour change.
Verbose diagnostic status dump.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

debug_status.py — Verbose debug for status.py instrument issue
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""
import os, sys, subprocess, re

sys.path.insert(0, os.path.expanduser("~/options-trader"))

SERVICE_NAME = "optionsbot"

print("=== STEP 1: systemd raw output ===")
result = subprocess.run(
    ["sudo", "systemctl", "show", SERVICE_NAME, "--property=Environment"],
    capture_output=True, text=True
)
print(repr(result.stdout[:300]))
print()

print("=== STEP 2: regex match ===")
m = re.search(r'OT_INSTRUMENT=([^ ]+)', result.stdout)
print("Match:", m.group(1) if m else "NO MATCH")
print()

print("=== STEP 3: get_runtime_env function ===")
def get_runtime_env(key, default=""):
    try:
        r = subprocess.run(
            ["sudo", "systemctl", "show", SERVICE_NAME, "--property=Environment"],
            capture_output=True, text=True
        )
        match = re.search(rf'(?:^| ){re.escape(key)}=([^ ]+)', r.stdout)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Exception: {e}")
    return os.environ.get(key, default)

val = get_runtime_env("OT_INSTRUMENT", "UNSET")
print("get_runtime_env result:", val)
print()

print("=== STEP 4: config import ===")
try:
    from config import DB_PATH, BOT_NAME
    print("DB_PATH:", DB_PATH)
    print("BOT_NAME:", BOT_NAME)
except Exception as e:
    print("Config import error:", e)
print()

print("=== STEP 5: INSTRUMENT after config import ===")
INSTRUMENT = get_runtime_env("OT_INSTRUMENT", "UNSET")
print("INSTRUMENT:", INSTRUMENT)
