#!/usr/bin/env python3
"""
tests/check_env_doc.py  v1.0
v1.0  2026-10-04  OTV4TEST r250 (DOC.31 item 4) — docs/ENV.md MATCHES THE CODE.
  E1  tests/gen_env_doc.py --check: every OT_* read in the tree is in docs/ENV.md, with its default and file:line, and nothing stale
  E2  the doc names the known core switches (OT_INSTRUMENT, OT_RISK_USD, OT_DAILY_LOSS_LIMIT, OT_ORCS, OT_CONTRACT_SCALE) - a scan that
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
missing = [v for v in ("OT_INSTRUMENT", "OT_RISK_USD", "OT_DAILY_LOSS_LIMIT", "OT_ORCS", "OT_CONTRACT_SCALE")
           if f"| `{v}` |" not in doc]
check("E2 the core switches are in it (the scan found real reads)", not missing, f"missing {missing}")
if FAILED:
    print(f"\nRED — {FAILED}"); sys.exit(1)
print("\nGREEN — docs/ENV.md says what the code reads"); sys.exit(0)
