#!/usr/bin/env python3
"""
options_trader_v4/warehouse/counter_pop.py — v1.0
v1.0  2026-09-26  r436 / S3.25 — THE NARROW COUNTER REPAIR. Removes ledger
      entries for prefixes that hold ZERO objects in S3, and refuses every
      other shape.

🔴 WHY THIS EXISTS AND WHY `--reconcile` IS THE WRONG TOOL. S3.25's rule is
that any deletion from `raw/` must reset the counters it invalidates, in the
same run. It has been violated three times: r314's epoch strip (S3.24), the
08-25 shadow purge (S3.13), and the 09-23 WH.20 refile, which moved 515 objects
to their correct `dt=` partitions and left **31 source prefixes empty that the
counters still claim**. The blanket `--reconcile` would fix those AND silently
agree with any genuine gap elsewhere on the box — S3.25's own words. This tool
cannot do that, because it only ever removes entries whose prefix is EMPTY.

🔑 THE SELECTION RULE IS THE SAFETY RULE, NOT A PRECONDITION BOLTED ON TOP.
Only `got == 0` qualifies. A prefix that is merely SHORT (`got < exp`, `got > 0`)
is REFUSED and named, because r180's heal repairs exactly that case on the next
clean drain and will report it as `HEALED <prefix> ledger N -> M`. Popping it
here would take a repair the system performs correctly and make it permanent
and unlogged.
📊 MEASURED, SOFI 2026-09-26: ten short prefixes — six at `got=0` and four
partial (`27/26`, `29/28`, `29/28`, `2/1`). The four partials are genuine
one-object losses that heal themselves. Only the six qualify. An earlier
reading of mine called all ten emptied; the peer session caught it.

⚠️ AN EMPTIED PREFIX NEVER HEALS, WHICH IS THE WHOLE PROBLEM. `s3_push`'s heal
is gated on `if _got > 0`, so a prefix with nothing in the bucket stays SHORT
forever. It then lands in the drift classifier, and because its gap equals its
whole expected count — usually 1 — it is labelled COUNTER DRIFT: *"objects
present"*. That sentence is FALSE for these prefixes, and `self_close` treats
the drift label as permission to purge and halt rather than hold.

⚠️ IT TAKES THE PUSH LOCK. r349 records what happens without it: a fleet
reconcile at 19:16 collided with `s3-push.timer`, lost the race, returned 0,
printed nothing and exited 0 — an operator-initiated repair indistinguishable
from a box with nothing to say, while the fleet stayed HELD for three nights.

⚠️ DRY BY DEFAULT. `--apply` arms it. It prints the full plan either way, and
every refusal is named rather than counted.

Usage:
    python3 warehouse/counter_pop.py            # plan only
    python3 warehouse/counter_pop.py --apply    # pop the qualifying entries
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import s3_push as P                                              # noqa: E402


def plan(counters: dict, short: list) -> tuple[list, list]:
    """(pop, refuse) — pop only `got == 0`; refuse everything else, by name."""
    pop, refuse = [], []
    for row in short:
        pfx, exp, got = row[0], row[1], row[2]
        if got != 0:
            refuse.append((pfx, exp, got,
                           "partial — r180's heal repairs this on the next "
                           "clean drain"))
        elif pfx not in counters:
            refuse.append((pfx, exp, got,
                           "not in the ledger — nothing to pop"))
        else:
            pop.append((pfx, exp, got))
    return pop, refuse


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="narrow counter repair (S3.25)")
    ap.add_argument("--apply", action="store_true",
                    help="arm it; without this nothing is written")
    args = ap.parse_args(argv)

    import boto3
    s3 = boto3.client("s3", region_name=P.REGION)

    # ⚠️ THE LOCK FIRST. A repair that loses a race to the pusher and exits 0
    # is indistinguishable from a box with nothing to repair (r349).
    lock = P.acquire_lock(P.LOCK_WAIT)
    if not lock:
        print("  REFUSED: could not take the push lock within "
              f"{P.LOCK_WAIT}s — the pusher is running. Nothing was read or "
              "written. Re-run when it is idle.")
        return 3
    try:
        counters = P.load_ledger(P.COUNTERS_PATH)
        short, n_local, n_s3 = P.verify(s3, P.BUCKET, counters)
        pop, refuse = plan(counters, short)

        print(f"  ledger entries {len(counters)} · short {len(short)} · "
              f"local {n_local} · s3 {n_s3}")
        for pfx, exp, got, why in refuse:
            print(f"  REFUSE  {pfx}  exp {exp} got {got}  — {why}")
        for pfx, exp, got in pop:
            print(f"  POP     {pfx}  exp {exp} got {got}  (empty in S3)")
        if not pop:
            print("  nothing qualifies — no entry removed.")
            return 0
        if not args.apply:
            print(f"  [dry] {len(pop)} entry(ies) WOULD be removed. "
                  f"Re-run with --apply.")
            return 0

        before = len(counters)
        for pfx, _e, _g in pop:
            counters.pop(pfx, None)
        if not P.save_ledger(counters, P.COUNTERS_PATH):
            print("  🔴 SAVE FAILED — the ledger is unchanged.")
            return 1
        after = len(P.load_ledger(P.COUNTERS_PATH))
        print(f"  ledger {before} -> {after} entries "
              f"({before - after} removed, expected {len(pop)})")
        return 0 if before - after == len(pop) else 1
    finally:
        # `acquire_lock` returns the open file handle; flock is released when
        # it closes. s3_push itself relies on process exit for this — a tool
        # that may be imported must not.
        try:
            lock.close()
        except Exception:                                         # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main())
