#!/usr/bin/env python3
"""
tests/check_ledger_paths.py  v4.1
Two ledgers, two files. Neither may be written to the other's path.

v4.1  2026-08-24  L5 generalises the rule. L1/L2 pinned the ONE call site that
existed when the bug was found; there are now SIX ledger constants
(chain/trades/counters/misc/candle/derived) and a NEW explicit save with a
mismatched one would have passed. L5 checks every explicit save against the
constant its variable was loaded from.

v4.0  2026-08-23  Written after `--reconcile` wrote the PREFIX COUNTERS over
`chain_ledger.json` — the FILE-OFFSET ledger — instead of
`prefix_counters.json`.

🔴 THE DAMAGE, and it escalated every time it ran. `chain_ledger` maps SOURCE
PATH -> lines already pushed; `counters` maps S3 PREFIX -> objects confirmed.
Overwriting the first with the second means the next `push_file` looks up its
source path, FINDS NOTHING, resumes at line 0 and RE-PUSHES THE ENTIRE FILE.
So each reconcile destroyed the record of what had been sent, and the next
`--verify` (which drains first) re-sent everything — inflating the very counter
the reconcile had just corrected. Observed live: 222 -> 300 while S3 held 74.

⚠️ NOTHING WAS LOST. Keys are content-hashed, so the re-pushes overwrote
identical objects. The cost was PUT charges and a number that got worse the
harder we tried to fix it.

🔑 THE FAILURE CLASS: TWO STATE FILES WITH THE SAME SHAPE AND DIFFERENT
MEANINGS, written through the same helper. `save_ledger(x, PATH)` accepts
either dict happily — nothing in the type system or the function signature
distinguishes an offset map from a count map, so a one-word path mistake is
invisible at every layer until the fleet re-uploads itself.

Run:  cd ~/options-trader && python3 tests/check_ledger_paths.py
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "warehouse", "s3_push.py")
PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def main() -> int:
    print("=" * 62)
    print("LEDGER PATHS: offsets and counters never share a file")
    print("=" * 62)
    src = open(SRC, encoding="utf-8").read()

    # L1 — the counters dict is only ever saved to COUNTERS_PATH.
    # ⚠️ MATCHES THE CALL SITE, NOT THE CONSTANT. Asserting that both names
    # exist would have passed against the bug: both DID exist, and the wrong
    # one was passed.
    bad = re.findall(r"save_ledger\(\s*counters\s*,\s*([A-Z_]+)\s*\)", src)
    check("L1 counters are saved ONLY to COUNTERS_PATH",
          bad and all(p == "COUNTERS_PATH" for p in bad),
          f"counters written to: {bad}")

    # L2 — the file-offset ledgers are never handed the counters dict.
    bad2 = re.findall(r"save_ledger\(\s*(\w+)\s*,\s*LEDGER_PATH\s*\)", src)
    check("L2 nothing but the chain ledger is saved to LEDGER_PATH",
          all(v in ("ledger", "chain_ledger") for v in bad2),
          f"written to LEDGER_PATH: {bad2}")

    # L3 — every load pairs with the same constant it saves to.
    loads = set(re.findall(r"counters\s*=\s*load_ledger\((\w+)\)", src))
    check("L3 counters LOAD from COUNTERS_PATH",
          loads == {"COUNTERS_PATH"}, f"loaded from: {sorted(loads)}")

    # L4 — the two constants are genuinely different files.
    m1 = re.search(r"LEDGER_PATH\s*=.*?\"([^\"]+)\"", src)
    m2 = re.search(r"COUNTERS_PATH\s*=.*?\"([^\"]+)\"", src)
    check("L4 the two ledgers are different filenames",
          bool(m1 and m2 and m1.group(1) != m2.group(1)),
          f"{m1.group(1) if m1 else '?'} vs {m2.group(1) if m2 else '?'}")

    # L5 — GENERIC: every EXPLICIT save_ledger(var, CONST) must save to the
    # constant that variable was LOADED from.
    # ⚠️ L1/L2 pin the ONE call that existed when the r82 bug was found. There
    # are now SIX ledger constants; a NEW explicit save with a mismatched one
    # would pass both. `flush_all` is safe by construction — it iterates
    # path->data pairs established at load time — so only explicit calls can
    # reproduce the bug, and this rule covers all of them, present and future.
    loads = dict(re.findall(r"(\w+)\s*=\s*load_ledger\((\w+)\)", src))
    saves = re.findall(r"save_ledger\(\s*(\w+)\s*,\s*([A-Z_]+)\s*\)", src)
    mismatched = [(v, c, loads.get(v))
                  for v, c in saves
                  if v in loads and loads[v] != c]
    check("L5 every explicit save pairs with the constant it loaded from",
          not mismatched,
          "; ".join(f"{v} loaded from {ld} but saved to {c}"
                    for v, c, ld in mismatched))

    print("=" * 62)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  ALL GREEN — a reconcile cannot erase the push offsets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
