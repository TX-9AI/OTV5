#!/usr/bin/env python3
"""
tests/warehouse_source.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.5  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.4  2026-09-20  OTV4TEST r69 (S3.14) — `stream_series()` ADDED. `load_series`
materialises a whole date (~230k prints per symbol-day, hundreds of MB) and a
19-session corpus run was OOM-reaped on a box with 908 MB of physical RAM.
`_envelopes` was already a generator, so the accumulator was the only ceiling.
Same path, same dedupe posture, peak footprint of one object. `load_series` is
unchanged, so every existing caller is byte-for-byte unaffected.

v1.3  2026-09-07  r301 - DAY_ONE 2026-08-25 -> 2026-09-01, epoch 3. Moves in
lockstep with day_trader_pro's ENGINE_EPOCH: two constants in two repos meaning
one thing is the drift this codebase keeps finding, so they ship together.
v1.2  2026-09-07  r298 - IT SAYS WHAT IT IS DOING. r297 widened the default
window from one day to day-one-onward and this reader printed NOTHING until
every date was done - ~3,700 sequential get_object calls and minutes of dead
terminal, which the operator killed with ^C because it looked hung. A line per
date now, worded exactly as report 46 words it. WIDENING A DEFAULT IS A CHANGE
TO WHAT THE OPERATOR WAITS THROUGH, not only to what it covers, and I changed
one without the other.
v1.1  2026-09-07  r297 - DATES ARE VALIDATED, AND THE DEFAULT IS DAY ONE.
`--date` was returned VERBATIM and never parsed, so the menu passing
"2026-08-31 2026-09-04" became an S3 prefix that cannot exist - and the SOURCE
banner then called it "a real, empty result - not a missing path". It could not
know that. `_valid()` raises and names the string; `_et_today()` replaces a
naive `date.today()` that rolled at 20:00 ET on UTC boxes; the default window
is DAY ONE ONWARD rather than today, matching report 41.
v1.0  (original)
THE R SUITE'S S3 SOURCE. Control reads the bucket; boxes are never touched.

v1.0  2026-08-23  Operator's baseline requirement, verbatim in effect: reports
run on CONTROL, the target is S3, nothing runs on a trading instance and
nothing is pulled to control to digest. This module is the one place the four
R tools get data, so the rule lives in one file instead of four.

DESIGN RULES
  1. STDLIB + boto3 ONLY, same as s3_push. No repo imports, no pandas. It
     must run under control's system python and under the dtp venv alike.
  2. ⚠️ DEDUPE IS MANDATORY AND LIVES HERE. trades and the derived CDC tables
     are pushed on every state change, so S3 holds several objects per key.
     `latest wins by pushed_at_utc` — without it every ratio in the suite
     inflates silently. (Same contract as day_trader_pro's warehouse_reader;
     re-implemented because a module never imports from a sibling repo.)
  3. ⚠️ "EMPTY" AND "UNREACHABLE" ARE DIFFERENT FACTS. Every loader returns
     (rows, meta) where meta carries objects listed, objects read, and any
     error string. banner() renders it, and every tool prints it — a flat day
     and a broken credential must never look alike (this conflation has cost
     the project twice in one week).

KEY LAYOUT READ (must match warehouse/s3_push.py):
  raw/trades/dt=<D>/sym=<S>/...            envelope.record = trade row (CDC)
  raw/<series>/dt=<D>/sym=<S>/...          envelope.record = [rows] (batch)
  raw/derived_<table>/dt=<D>/sym=<S>/...   envelope.record = [rows w/ _rid] (CDC batch)

Run:  python3 tests/warehouse_source.py --selftest
"""
from __future__ import annotations

import json
import os

BUCKET = os.environ.get("OT_S3_BUCKET", "vertigo-warehouse-tx9ai")
REGION = os.environ.get("OT_S3_REGION", "us-east-2")
PREFIX = os.environ.get("OT_S3_PREFIX", "raw")


class Meta:
    def __init__(self, what):
        self.what = what
        self.listed = 0
        self.read = 0
        self.bad = 0
        self.error = ""

    def banner(self) -> str:
        if self.error:
            return (f"SOURCE: s3://{BUCKET}/{PREFIX} [{self.what}] — "
                    f"🔴 COULD NOT READ THE WAREHOUSE: {self.error}")
        return (f"SOURCE: s3://{BUCKET}/{PREFIX} [{self.what}] — "
                f"{self.listed} object(s) listed, {self.read} read"
                + (f", {self.bad} unreadable" if self.bad else "")
                + ("  (a real, empty result — not a missing path)"
                   if self.listed == 0 else ""))


def client():
    import boto3
    return boto3.client("s3", region_name=REGION)


def _iter(s3, prefix, meta):
    pg = s3.get_paginator("list_objects_v2")
    for page in pg.paginate(Bucket=BUCKET, Prefix=prefix):
        for o in page.get("Contents", []) or []:
            meta.listed += 1
            yield o["Key"]


def _envelopes(s3, datatype, dates, meta, symbols=None):
    # 🔴 r298 — IT SAYS WHAT IT IS DOING. r297 widened the default window from
    # ONE day to day-one-onward without asking what that costs: this reads one
    # object per key, sequentially, and printed NOTHING until every date was
    # done. At ~264 objects and ~11s per session that is ~3,700 calls and
    # minutes of dead terminal, and the operator correctly killed it with ^C
    # because it looked hung.
    # ⚠️ THE STANDING RULE WAS ALREADY WRITTEN: any operation running more than
    # a few seconds must say what it is doing. `pnl_s3` obeys it through a
    # different reader and prints a line per date; this path never did, and
    # nobody noticed while the default was a single day. WIDENING A DEFAULT IS
    # A CHANGE TO WHAT THE OPERATOR WAITS THROUGH, not just to what it covers.
    # ⚠️ Wording matches report 46's deliberately, so the two readers do not
    # describe the same work differently.
    import sys as _sys, time as _time
    _multi = len(dates) > 1
    for d in dates:
        _t0 = _time.monotonic()
        try:
            keys = list(_iter(s3, f"{PREFIX}/{datatype}/dt={d}/", meta))
        except Exception as exc:                                # noqa: BLE001
            meta.error = f"{type(exc).__name__}: {exc}"
            return
        if _multi:
            # Printed BEFORE the reads, so a slow date is visible WHILE it is
            # slow rather than after it finishes. A progress line that only
            # appears on completion is a receipt, not progress.
            print(f"  {datatype} {d}: {len(keys)} object(s)", end="", flush=True)
        for k in keys:
            if symbols:
                sym = next((p[4:] for p in k.split("/") if p.startswith("sym=")), "")
                if sym not in symbols:
                    continue
            try:
                body = s3.get_object(Bucket=BUCKET, Key=k)["Body"].read()
                meta.read += 1
                yield json.loads(body)
            except Exception:                                   # noqa: BLE001
                meta.bad += 1
        if _multi:
            print(f"  in {_time.monotonic() - _t0:.0f}s", flush=True)


def load_trades(dates, s3=None):
    """Deduped closed+open trade rows for the dates. -> (rows, Meta)."""
    meta = Meta(f"trades {dates[0]}..{dates[-1]}")
    s3 = s3 or client()
    best = {}
    for env in _envelopes(s3, "trades", dates, meta):
        rec = env.get("record") or {}
        tid = rec.get("trade_id")
        if tid is None:
            continue
        stamp = str(env.get("pushed_at_utc") or "")
        if tid not in best or stamp >= best[tid][0]:
            best[tid] = (stamp, rec)
    return [rec for _s, rec in best.values()], meta


def load_series(table, dates, symbols=None, s3=None):
    """Rows of one manifold series table (batched objects). -> (rows, Meta)."""
    meta = Meta(f"{table} {dates[0]}..{dates[-1]}")
    s3 = s3 or client()
    rows = []
    for env in _envelopes(s3, table, dates, meta, symbols):
        rec = env.get("record")
        if isinstance(rec, list):
            rows.extend(r for r in rec if isinstance(r, dict))
    return rows, meta


def stream_series(table, dates, symbols=None, s3=None, meta=None):
    """Yield series rows ONE AT A TIME. Same source, same dedupe posture, a
    fraction of the memory. -> generator of dict; pass `meta` to read the
    objects-listed/read counters afterwards.

    🔴 r69 — WHY THIS EXISTS. `load_series` materialises a whole date into a
    list: ~230,000 prints for ONE symbol-day, several hundred MB of Python
    dicts. This box has 908 MB of PHYSICAL RAM (measured; the 2 GB swapfile is
    separate), and a 19-session × 3-symbol corpus run was reaped by the OOM
    killer mid-study on 2026-09-20. The rows were never needed all at once —
    every consumer so far folds them into per-interval buckets immediately.
    🔑 `_envelopes` WAS ALREADY A GENERATOR and each object carries only ~2,400
    rows, so the ceiling was `load_series`'s accumulator and nothing else.
    Peak footprint becomes one object plus the caller's buckets.
    ⚠️ THE CALLER MUST NOT RE-ACCUMULATE. `list(stream_series(...))` is
    `load_series` with extra steps and the same OOM; the point is to fold as
    you go. Said here because the failure mode is a one-word change at the call
    site that silently restores the ceiling.
    ⚠️ IT IS THE SAME PATH, NOT A SECOND ONE (§38.1, §36a). It reuses
    `_envelopes` and the same record-shape handling as `load_series`, so a
    change to either reaches both; it is not a parallel reader that can drift.
    """
    meta = meta if meta is not None else Meta(f"{table} {dates[0]}..{dates[-1]}")
    s3 = s3 or client()
    for env in _envelopes(s3, table, dates, meta, symbols):
        rec = env.get("record")
        if isinstance(rec, list):
            for r in rec:
                if isinstance(r, dict):
                    yield r


def load_derived(table, dates, s3=None):
    """Rows of one derived CDC table, latest state per _rid. -> (rows, Meta)."""
    meta = Meta(f"derived_{table} {dates[0]}..{dates[-1]}")
    s3 = s3 or client()
    best = {}
    for env in _envelopes(s3, f"derived_{table}", dates, meta):
        stamp = str(env.get("pushed_at_utc") or "")
        sym = env.get("symbol") or "?"
        for r in (env.get("record") or []):
            if not isinstance(r, dict):
                continue
            key = (sym, r.get("_rid"))
            if key not in best or stamp >= best[key][0]:
                best[key] = (stamp, r)
    return [r for _s, r in best.values()], meta


# 🔴 r297 — THE ENGINE EPOCH. r187 established it for report 41: anything
# before this is the OLD engines, and pooling two systems in one table has
# already produced one wrong conclusion quoted as evidence. The bucket holds
# trades back to 2026-07-06, so an unqualified "everything" is contaminated by
# construction.
DAY_ONE = "2026-09-01"   # epoch 3 (r301) — see trade_report.ENGINE_EPOCH


def _valid(d: str) -> str:
    """Return an ISO date, or RAISE naming what was passed.

    🔴 r297 — THIS DID NOT EXIST AND THE COST WAS A LIE IN THE PROVENANCE LINE.
    `--date` was returned VERBATIM, unparsed, so the menu passing
    `"2026-08-31 2026-09-04"` (two dates, one field) became an S3 prefix that
    cannot exist — and `Meta.banner` then printed *"0 object(s) listed  (a real,
    empty result — not a missing path)"*. It could not know that. A malformed
    date and a genuinely quiet session are different facts, and the banner
    asserted the harmless one with no way to tell them apart.
    ⚠️ RAISES rather than falling back to today or to the epoch: a silent
    substitution is how you end up reading the wrong window and believing it.
    """
    from datetime import datetime
    t = str(d).strip()
    try:
        return datetime.strptime(t, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise SystemExit(
            f"  🔴 NOT A DATE: {t!r}\n"
            f"     Expected YYYY-MM-DD. A range is two separate values "
            f"(--from A --to B), never one field holding both.\n"
            f"     Refusing rather than reporting an empty window, which "
            f"would read as a quiet session.")


def _et_today() -> str:
    """Today as the EXCHANGE sees it. The boxes and control run UTC, so a
    naive `date.today()` rolls at 20:00 ET — the operator's long-standing
    symptom that a report for 'today' run after the close comes back empty."""
    from datetime import datetime, timezone
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:                                            # noqa: BLE001
        return datetime.now(timezone.utc).date().isoformat()


def _span(d0: str, d1: str) -> list:
    from datetime import datetime, timedelta
    a = datetime.strptime(d0, "%Y-%m-%d").date()
    b = datetime.strptime(d1, "%Y-%m-%d").date()
    if b < a:
        a, b = b, a
    out, d = [], a
    while d <= b:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def dates_of(argns) -> list:
    """--date / --from/--to / --all-history -> ISO list.

    ⚠️ DEFAULT IS DAY ONE ONWARD, NOT TODAY (r297, operator's instruction that
    ENTER should mean the whole record rather than one session). It matches
    report 41's default exactly, which is the point — the R suite and the trade
    breakdown should not disagree about what an unqualified run covers.
    ⚠️ AND IT IS NOT LITERALLY ALL TIME. `--all-history` is the explicit
    override and reaches back through the v3 engines; the default stops at the
    epoch, because that is the boundary r187 exists to hold.
    """
    if getattr(argns, "date", None):
        return [_valid(argns.date)]
    frm, to = getattr(argns, "frm", None), getattr(argns, "to", None)
    if frm or to:
        # ⚠️ ONE END IS ENOUGH. A half-specified range used to fall through to
        # "today" silently, which is the substitution this function now refuses.
        return _span(_valid(frm) if frm else DAY_ONE,
                     _valid(to) if to else _et_today())
    if getattr(argns, "all_history", False):
        return _span("2026-07-06", _et_today())
    return _span(DAY_ONE, _et_today())


# ── selftest ────────────────────────────────────────────────────────────
class _FakeS3:
    def __init__(self, objs):
        self.objs = objs

    def get_paginator(self, _):
        objs = self.objs

        class P:
            def paginate(self, Bucket, Prefix):
                yield {"Contents": [{"Key": k} for k in objs if k.startswith(Prefix)]}
        return P()

    def get_object(self, Bucket, Key):
        import io
        return {"Body": io.BytesIO(self.objs[Key])}


def selftest() -> int:
    def env(dt, rec, stamp, sym="X", datatype="trades"):
        return json.dumps({"datatype": datatype, "symbol": sym, "dt": dt,
                           "pushed_at_utc": stamp, "record": rec}).encode()
    objs = {
        # same trade pushed twice — the LATER state must win
        f"{PREFIX}/trades/dt=2026-08-24/sym=X/1-aa.json":
            env("2026-08-24", {"trade_id": "t1", "status": "open", "pnl_usd": None}, "T1"),
        f"{PREFIX}/trades/dt=2026-08-24/sym=X/2-bb.json":
            env("2026-08-24", {"trade_id": "t1", "status": "closed", "pnl_usd": 50.0}, "T2"),
        f"{PREFIX}/quote_series/dt=2026-08-24/sym=X/3-cc.json":
            env("2026-08-24", [{"streamer_symbol": "C1", "ts_epoch": 1.0,
                                "bid_price": 1.0, "ask_price": 1.1}], "T1",
                datatype="quote_series"),
        f"{PREFIX}/derived_fire_snapshot/dt=2026-08-24/sym=X/4-dd.json":
            env("2026-08-24", [{"_rid": 1, "trade_id": "t1", "payload": "{}"}], "T1",
                datatype="derived_fire_snapshot"),
        f"{PREFIX}/derived_fire_snapshot/dt=2026-08-24/sym=X/5-ee.json":
            env("2026-08-24", [{"_rid": 1, "trade_id": "t1", "payload": "{\"a\":1}"}], "T2",
                datatype="derived_fire_snapshot"),
    }
    s3 = _FakeS3(objs)
    ok = True
    rows, m = load_trades(["2026-08-24"], s3=s3)
    ok &= len(rows) == 1 and rows[0]["status"] == "closed" and m.read == 2
    q, _ = load_series("quote_series", ["2026-08-24"], s3=s3)
    ok &= len(q) == 1 and q[0]["streamer_symbol"] == "C1"
    d, _ = load_derived("fire_snapshot", ["2026-08-24"], s3=s3)
    ok &= len(d) == 1 and d[0]["payload"] == "{\"a\":1}"
    # deliberate-failure control: an unreadable bucket must report an ERROR
    class _Boom:
        def get_paginator(self, _):
            raise RuntimeError("AccessDenied")
    _r, m2 = load_trades(["2026-08-24"], s3=_Boom())
    ok &= "AccessDenied" in m2.error and "COULD NOT READ" in m2.banner()
    # and an empty day must NOT look like an error
    _r3, m3 = load_trades(["2026-08-25"], s3=s3)
    ok &= not m3.error and "empty result" in m3.banner()
    print("warehouse_source selftest:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(selftest() if "--selftest" in sys.argv else
             print("this module is imported by the R tools; --selftest to prove it") or 0)
