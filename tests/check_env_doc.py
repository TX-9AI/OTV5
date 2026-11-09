#!/usr/bin/env python3
"""
tests/check_env_doc.py  v5.2
v5.2  2026-11-09  OTV5 r103 (RETIRE.5 step 2) — E2's core list swaps OT_GEX_BUTTERFLY (no longer read: the GEX fly is removed) for OT_HUNT (plan_state's Hunt switch). E1 unchanged.
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — E2's core list swaps OT_ORCS and OT_CONTRACT_SCALE (no longer read: ORCS is removed)
      for OT_ORB_BUDGET_USD (the ramp TOP) and OT_GEX_BUTTERFLY.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-04  OTV4TEST r250 (DOC.31 item 4) — docs/ENV.md MATCHES THE CODE.
  E1  tests/gen_env_doc.py --check: every OT_* read in the tree is in docs/ENV.md, with its default and file:line, and nothing stale
  E2  the doc names the known core switches (OT_INSTRUMENT, OT_RISK_USD, OT_DAILY_LOSS_LIMIT, OT_ORB_BUDGET_USD, OT_HUNT) - a scan that
      silently found nothing would otherwise "match" an empty doc
Run: python3 tests/check_env_doc.py
"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "gen_env_doc.py"), "--check"],
                   capture_output=True, text=True, timeout=120)
check("E1 docs/ENV.md is generated from the code and current", r.returncode == 0, (r.stdout + r.stderr)[-400:])
try:
    doc = open(os.path.join(ROOT, "docs", "ENV.md"), encoding="utf-8").read()
except OSError as exc:
    doc = ""
missing = [v for v in ("OT_INSTRUMENT", "OT_RISK_USD", "OT_DAILY_LOSS_LIMIT", "OT_ORB_BUDGET_USD", "OT_HUNT")   # r103: OT_GEX_BUTTERFLY no longer read
           if f"| `{v}` |" not in doc]
check("E2 the core switches are in it (the scan found real reads)", not missing, f"missing {missing}")
if FAILED:
    print(f"\nRED — {FAILED}"); sys.exit(1)
print("\nGREEN — docs/ENV.md says what the code reads"); sys.exit(0)
