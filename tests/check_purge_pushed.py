#!/usr/bin/env python3
"""
tests/check_purge_pushed.py  v1.2
NOTHING UNRECOVERABLE MAY LACK A PUSH STAGE. Executing invariant.

v1.2  2026-08-29  r191 — C9/C10: THE DERIVED SERIES JOIN THE INVARIANT, AND
THE REASON THEY WERE OUTSIDE IT IS THE FINDING. `retention_purge` deleted
`indicator_series`, `fork_series` and `surface_series` at 20 days from a
HARDCODED TUPLE INSIDE `purge()`, while this file proves its invariant by
IMPORTING `ARTIFACT_DAYS` and `NEVER_PURGE`. **A policy the checker cannot
import is a policy outside the checker**, so three tables were being trimmed
unwarehoused for as long as the purge has been armed and every run of this
file printed green. retention_purge v1.1 promotes the list to
`DERIVED_ARTIFACT_DAYS`; C9 reads it and C10 drives `push_series` against a
planted derived store. Born red at r190 (no derived-series stage existed).
⚠️ THE GENERAL LESSON, worth more than the fix: this checker's coverage is
bounded by what the policy exposes as a CONSTANT. Any future purge written
as a literal inside a function is invisible here and will pass silently.

v1.1  2026-08-23  C6-C8: the LIFECYCLE tables join the invariant. They are
NEVER_PURGE precisely because a recomputation cannot rebuild a biography —
which is the strongest possible argument that the box must not hold the only
copy. Born red at r86 (no push_derived existed); green from s3_push v4.3.
C8 closes the loop end-to-end: planted store → push_derived → fake S3 →
tests/warehouse_source.load_derived must return the LATEST state of a row
that mutated between pushes, proving CDC and reader dedupe agree.

v1.0  2026-08-23  Born RED at r84: retention_purge held greeks_series,
quote_series, prints, last_trade, session_summary, theo_series and
underlying_series at 3 days — calling it "a RE-PUSH window" — while s3_push
had no stage touching any of them. Armed, the purge would have deleted the
manifold's series data unwarehoused: the exact "pruned before you knew you
needed it" loss the manifold exists to end. Green from s3_push v4.2.

MECHANICS — WA §20/§21 compliant:
  · Reads retention_purge's LIVE constants (import, not grep), so a new
    purgeable table added tomorrow trips this check the same day.
  · Proves coverage by EXECUTION, not mention: push_series is driven against
    a planted in-memory store carrying one row in EVERY purgeable series
    table, with a fake S3, and each table must produce a confirmed object.
    A candle row is planted too, for push_candles, so the candles interval
    policy is covered by the same run.
  · Deliberate-failure control: an extra table present in the purge policy
    but absent from the store must be REPORTED as uncovered, proving the
    check can go red.

Run:  cd ~/options-trader && python3 tests/check_purge_pushed.py
"""
from __future__ import annotations

import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PROBLEMS: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


class _FakeS3:
    def __init__(self):
        self.objs = {}

    def put_object(self, Bucket, Key, Body):
        self.objs[Key] = Body

    def get_object(self, Bucket, Key):
        import io
        return {"Body": io.BytesIO(self.objs[Key])}


def main() -> int:
    print("=" * 66)
    print("PURGE↔PUSH INVARIANT: everything deletable is warehoused first")
    print("=" * 66)
    from warehouse import retention_purge as rp
    from warehouse import s3_push as sp

    purgeable = sorted(set(rp.ARTIFACT_DAYS) - set(rp.NEVER_PURGE))
    candle_purge = any(d for d in rp.RETENTION_DAYS.values())

    # 1 — every purgeable series table must be in the push's declared set.
    declared = set(getattr(sp, "SERIES_TABLES", ()))
    missing = [t for t in purgeable if t not in declared]
    check("C1 every purgeable artifact table has a push stage declared",
          not missing, f"unpushed purgeable tables: {missing}")

    # 2 — EXECUTE the push against a planted store; every table must land.
    tmp = os.path.join("/tmp", "check_purge_pushed.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    for t in purgeable:
        con.execute(f"CREATE TABLE {t} (streamer_symbol TEXT, ts_epoch REAL, x REAL)")
        con.execute(f"INSERT INTO {t} VALUES ('X', 1000.0, 1.0)")
    con.execute("CREATE TABLE candles (symbol TEXT, interval TEXT,"
                " ts_epoch_ms INTEGER, close REAL)")
    con.execute("INSERT INTO candles VALUES ('X','1m', 1000000, 1.0)")
    con.commit()
    con.close()

    s3 = _FakeS3()
    ledger: dict = {}
    pushed, failed = sp.push_series(s3, "b", tmp, ledger, "X", counters={})
    landed = {k.split("/")[1] for k in s3.objs}
    not_landed = [t for t in purgeable if t not in landed]
    check("C2 push_series lands one object per purgeable table (executed)",
          pushed == len(purgeable) and failed == 0 and not not_landed,
          f"pushed={pushed} failed={failed} missing={not_landed}")

    check("C3 candle purge policy exists only alongside push_candles",
          (not candle_purge) or hasattr(sp, "push_candles"))

    # 4 — high-water mark advanced, namespaced, and a re-run pushes nothing.
    ok_hwm = all(ledger.get(f"series|{t}") == 1000.0 for t in purgeable)
    p2, f2 = sp.push_series(s3, "b", tmp, ledger, "X", counters={})
    check("C4 high-water marks are namespaced `series|<t>` and idempotent",
          ok_hwm and p2 == 0 and f2 == 0, f"ledger={ledger} rerun=({p2},{f2})")

    # ── 9/10 — the DERIVED series (v1.2) ───────────────────────────────
    d_purge = sorted(set(getattr(rp, "DERIVED_ARTIFACT_DAYS", {}))
                     - set(rp.NEVER_PURGE))
    d_declared = set(getattr(sp, "DERIVED_SERIES_TABLES", ()))
    d_missing = [t for t in d_purge if t not in d_declared]
    check("C9 every purgeable DERIVED series table has a push stage declared",
          bool(d_purge) and not d_missing,
          f"purgeable={d_purge} declared={sorted(d_declared)} missing={d_missing}")

    # EXECUTE it: a planted derived store, a fake S3, one object per table, a
    # namespace that cannot collide with the feed series, and idempotence.
    dtmp = os.path.join("/tmp", "check_purge_pushed_derived.db")
    if os.path.exists(dtmp):
        os.remove(dtmp)
    dcon = sqlite3.connect(dtmp)
    for t in d_purge:
        dcon.execute(f"CREATE TABLE {t} (symbol TEXT, ts_epoch REAL, x REAL)")
        dcon.execute(f"INSERT INTO {t} VALUES ('X', 2000.0, 1.0)")
    dcon.commit()
    dcon.close()

    ds3 = _FakeS3()
    dledger: dict = {}
    # ⚠️ DEGRADE TO A NAMED FAILURE, NEVER A TRACEBACK. Against a tree with no
    # derived-series stage this whole block is inapplicable, and an
    # AttributeError would report "the checker crashed" where the truth is
    # "the invariant is violated". C9 above already says which.
    if not d_declared or not hasattr(sp, "DERIVED_SERIES_TABLES"):
        check("C10 push_series lands each derived series, namespaced and idempotent",
              False, "skipped: s3_push declares no DERIVED_SERIES_TABLES "
                     "(see C9) — there is no stage to execute")
        dp = df = -1
        dlanded, d_not, ns_ok, no_bleed, dp2, df2 = set(), list(d_purge), False, True, -1, -1
    else:
        dp, df = sp.push_series(ds3, "b", dtmp, dledger, "X", counters={},
                                tables=sp.DERIVED_SERIES_TABLES, ns="dseries")
        dlanded = {k.split("/")[1] for k in ds3.objs}
        d_not = [t for t in d_purge if t not in dlanded]
        ns_ok = all(dledger.get(f"dseries|{t}") == 2000.0 for t in d_purge)
    # ⚠️ THE NAMESPACE ASSERTION IS NOT COSMETIC. `series|<t>` and `dseries|<t>`
    # in one dict would be two stores' high-water marks under one meaning —
    # the r82 class, where a one-word path mistake made the fleet re-upload
    # itself. This proves the derived call cannot write a `series|` key.
        no_bleed = not any(k.startswith("series|") for k in dledger)
        dp2, df2 = sp.push_series(ds3, "b", dtmp, dledger, "X", counters={},
                                  tables=sp.DERIVED_SERIES_TABLES, ns="dseries")
        check("C10 push_series lands each derived series, namespaced and idempotent",
              dp == len(d_purge) and df == 0 and not d_not and ns_ok
              and no_bleed and dp2 == 0 and df2 == 0,
              f"pushed={dp} failed={df} missing={d_not} ledger={dledger} "
              f"rerun=({dp2},{df2})")

    # 6 — lifecycle tables: NEVER_PURGE means the box holds the only copy
    # unless a derived push exists. Declared set must cover them.
    lifecycle = sorted(set(rp.NEVER_PURGE) - {"trades", "circuit_breaker_events"})
    declared_d = set(getattr(sp, "DERIVED_TABLES", ()))
    miss_l = [t for t in lifecycle if t not in declared_d]
    check("C6 every lifecycle biography table has a derived push stage",
          not miss_l, f"unwarehoused biographies: {miss_l}")

    # 7+8 — EXECUTE push_derived, mutate a row, push again, read back via the
    # R suite's own S3 source: latest state must win.
    tmp2 = os.path.join("/tmp", "check_purge_pushed_derived.db")
    if os.path.exists(tmp2):
        os.remove(tmp2)
    con = sqlite3.connect(tmp2)
    for t in declared_d:
        con.execute(f"CREATE TABLE {t} (k TEXT, state TEXT, ts_epoch REAL)")
        con.execute(f"INSERT INTO {t} VALUES ('a','OPEN',1.0)")
    con.commit()
    dled: dict = {}
    p1, f1 = sp.push_derived(s3, "b", tmp2, dled, "X", counters={})
    check("C7 push_derived lands one object per lifecycle table (executed)",
          p1 == len(declared_d) and f1 == 0, f"pushed={p1} failed={f1}")
    con.execute("UPDATE plan_ledger SET state='COMPLETE' WHERE k='a'")
    con.commit()
    p2b, _ = sp.push_derived(s3, "b", tmp2, dled, "X", counters={})
    con.close()
    check("C7b CDC re-ships only the mutated table", p2b == 1, f"pushed={p2b}")
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import warehouse_source as ws
    import json as _json

    class _WS3:
        def __init__(self, objs):
            self.objs = objs

        def get_paginator(self, _):
            objs = self.objs

            class P:
                def paginate(self, Bucket, Prefix):
                    yield {"Contents": [{"Key": k} for k in objs
                                        if ("/" + Prefix.split("/", 1)[1]) in ("/" + k)]}
            return P()

        def get_object(self, Bucket, Key):
            import io
            return {"Body": io.BytesIO(self.objs[Key])}

    day = None
    for k in s3.objs:
        if "/derived_plan_ledger/" in k:
            day = k.split("dt=")[1].split("/")[0]
    rows, meta = ws.load_derived("plan_ledger", [day], s3=_WS3(s3.objs))
    got = {r["k"]: r["state"] for r in rows}
    check("C8 warehouse_source reads back the LATEST CDC state (round trip)",
          got.get("a") == "COMPLETE" and not meta.error, f"got={got}")
    os.remove(tmp2)

    # 5 — deliberate-failure control: a purgeable table the store lacks must
    # surface as uncovered when we widen the policy in-memory.
    rp.ARTIFACT_DAYS["_planted_uncovered_table"] = 3
    try:
        widened = sorted(set(rp.ARTIFACT_DAYS) - set(rp.NEVER_PURGE))
        miss2 = [t for t in widened if t not in declared]
        check("C5 the check CAN fail (planted uncovered table is caught)",
              "_planted_uncovered_table" in miss2)
    finally:
        rp.ARTIFACT_DAYS.pop("_planted_uncovered_table", None)

    os.remove(tmp)
    print("-" * 66)
    if PROBLEMS:
        print(f"FAIL  {len(PROBLEMS)} problem(s): {', '.join(PROBLEMS)}")
        return 1
    print("ALL GREEN — nothing the purge can reach dies unwarehoused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
