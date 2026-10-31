#!/usr/bin/env python3
"""tests/check_series_catchup.py — v5.0
v5.0  2026-10-31  OTV5 r64 (SER.1) — A PUSH RUN CATCHES A SERIES BACKLOG UP, AND THE DRAIN GRADES ONE IT COULD NOT SHIP.
      s3_push v5.3 shipped ONE 50,000-row object per series table per 5-minute run (~167 rows/s); SPX writes ~310
      quote rows/s. On 2026-10-30 the fleet was taken down at the close with S3's SPX quote_series ending at 13:53 ET
      and QQQ's at 14:38, and `--verify` printed `OK short=0` for both: prefix counters count objects, not rows.
      Operator: "yes to all of the prepared solutions" (2026-10-31).

🔑 IT DRIVES THE REAL warehouse.s3_push (push_series and main --verify) against a synthetic feed_store.db holding
300,000 quote_series rows and an in-memory S3. HOME is a temp dir, so no real ledger or store is touched.

  C1  a run with budget left ships the whole 300k-row backlog and the mark reaches the last row
  C2  ... in objects of at most SERIES_BATCH_ROWS rows (the r20 memory bound), six of them
  C3  CONTROL: deadline=None is exactly one batch (the v5.3 behaviour; green on both trees)
  C4  a budget already spent still gives every table its first batch (no table starved worse than v5.3)
  C5  two tables behind are BOTH caught up (round-robin, not one table eating the budget)
  C6  a timer run stops taking extra batches when a --verify is waiting (drain_wanted newer than the run)
  C7  main --verify drains 300k rows: `  SERIES_LAG series|quote_series series_lag_s=0` and `DRAIN ... OK`
  C8  main --verify with no drain budget: series_lag_s > 0 BEHIND and `DRAIN ... SHORT`; the DRAIN line keeps the
      shape its three parsers read (conductor DRAIN_RE nine fields, self_close endswith, eod_backfill tail -8)
  C9  self_close.series_lag_max reads the SERIES_LAG lines (0 when there are none)

Born red on 6543fdc. Run:  python3 tests/check_series_catchup.py
"""
import datetime
import io
import os
import re
import sqlite3
import sys
import tempfile
import time
import types
from contextlib import redirect_stdout
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
ET = ZoneInfo("America/New_York")
_fails = []
N = 300_000

# A private HOME before s3_push is imported: its state, store and lock paths derive from it at import time.
_HOME = tempfile.mkdtemp(prefix="series_catchup_")
os.environ["HOME"] = _HOME
os.environ["OT_INSTRUMENT"] = "SPX"
os.environ["OT_S3_PUSH"] = "1"
for _k in ("OT_WAREHOUSE_STATE", "OT_CHAIN_ROOT", "OT_PUSH_PAUSE_FLAG", "OT_S3_SERIES_BATCH",
           "OT_S3_SERIES_BUDGET_S", "OT_S3_SERIES_DRAIN_BUDGET_S"):
    os.environ.pop(_k, None)


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


class FakeS3:
    """put/get/list backed by a dict, so put_and_verify's byte-compare and verify()'s LIST both work."""

    def __init__(self):
        self.store = {}

    def put_object(self, Bucket=None, Key=None, Body=None):
        self.store[Key] = Body

    def get_object(self, Bucket=None, Key=None):
        body = self.store[Key]
        return {"Body": types.SimpleNamespace(read=lambda: body)}

    def get_paginator(self, _name):
        store = self.store

        class _P:
            def paginate(self, Bucket=None, Prefix=""):
                yield {"Contents": [{"Key": k, "Size": len(v)} for k, v in store.items()
                                    if k.startswith(Prefix)]}
        return _P()


def _t0():
    """Yesterday 10:00 ET: one ET day for every row (300k rows * 0.05 s = 4.2 h)."""
    y = datetime.datetime.now(ET).date() - datetime.timedelta(days=1)
    return datetime.datetime.combine(y, datetime.time(10, 0), tzinfo=ET).timestamp()


def _db(path, tables_rows):
    """A slim feed_store-shaped db (ts_epoch + one value; no index): 300k rows is ~4 MB, because a gate that
    fills a small /tmp quota fails for the wrong reason (the 2026-10-31 control box had ~34 MB of quota left)."""
    con = sqlite3.connect(path)
    for table, n in tables_rows:
        con.execute(f"CREATE TABLE {table} (ts_epoch REAL, v INTEGER)")
        t0 = _t0()
        con.executemany(f"INSERT INTO {table} VALUES (?,?)", ((t0 + i * 0.05, i) for i in range(n)))
    con.commit()
    con.close()
    return path


def _objs(store, table):
    return [k for k in store if f"/{table}/" in k]


def _rows_per_obj(store, table):
    import json
    return [json.loads(store[k]).get("n_rows") for k in _objs(store, table)]


def _push(SP, s3, path, led, tables, **kw):
    return SP.push_series(s3, "B", path, led, "SPX", None, tables=tables, **kw)


def main():
    try:
        from warehouse import s3_push as SP
    except Exception as exc:                                  # pragma: no cover
        ck("C0", False, f"cannot import warehouse.s3_push ({exc})")
        print("\nRED — C0")
        return 1
    tmp = os.path.join(_HOME, "dbs")
    os.makedirs(tmp)
    one = _db(os.path.join(tmp, "one.db"), [("quote_series", N)])
    two = _db(os.path.join(tmp, "two.db"), [("greeks_series", N // 2), ("quote_series", N // 2)])
    last = _t0() + (N - 1) * 0.05
    cap = getattr(SP, "SERIES_BATCH_ROWS", 50000)

    # C1 / C2 — budget left: the whole backlog ships in capped objects
    s3, led = FakeS3(), {}
    try:
        t = time.time()
        _push(SP, s3, one, led, ("quote_series",), deadline=time.time() + 600)
        el = time.time() - t
        mark = float(led.get("series|quote_series", 0) or 0)
        ck("C1", abs(mark - last) < 1e-3, f"mark {mark:.2f} want {last:.2f} ({el:.1f} s for {N:,} rows)")
        per = _rows_per_obj(s3.store, "quote_series")
        ck("C2", len(per) == N // cap and max(per or [0]) <= cap and sum(per) == N,
           f"{len(per)} object(s), rows per object {sorted(set(per))}")
    except Exception as exc:
        ck("C1", False, f"raised {exc!r}")
        ck("C2", False, "C1 did not run")

    # C3 — CONTROL: no deadline = exactly one batch
    s3, led = FakeS3(), {}
    try:
        _push(SP, s3, one, led, ("quote_series",))
        ck("C3", len(_objs(s3.store, "quote_series")) == 1, f"{len(_objs(s3.store, 'quote_series'))} object(s), want 1")
    except Exception as exc:
        ck("C3", False, f"raised {exc!r}")

    # C4 — spent budget: still one batch per table
    s3, led = FakeS3(), {}
    try:
        _push(SP, s3, two, led, ("greeks_series", "quote_series"), deadline=time.time() - 1)
        n_g, n_q = len(_objs(s3.store, "greeks_series")), len(_objs(s3.store, "quote_series"))
        ck("C4", (n_g, n_q) == (1, 1), f"greeks {n_g} quote {n_q} object(s), want 1 and 1")
    except Exception as exc:
        ck("C4", False, f"raised {exc!r}")

    # C5 — two tables behind: both caught up
    s3, led = FakeS3(), {}
    try:
        _push(SP, s3, two, led, ("greeks_series", "quote_series"), deadline=time.time() + 600)
        lh = _t0() + (N // 2 - 1) * 0.05
        mg = float(led.get("series|greeks_series", 0) or 0)
        mq = float(led.get("series|quote_series", 0) or 0)
        ck("C5", abs(mg - lh) < 1e-3 and abs(mq - lh) < 1e-3, f"marks greeks {mg:.2f} quote {mq:.2f} want {lh:.2f}")
    except Exception as exc:
        ck("C5", False, f"raised {exc!r}")

    # C6 — a waiting --verify stops a timer run's extras
    s3, led = FakeS3(), {}
    flag = getattr(SP, "DRAIN_WANTED_PATH", None)
    try:
        if flag is None:
            raise AttributeError("no DRAIN_WANTED_PATH")
        os.makedirs(os.path.dirname(flag), exist_ok=True)
        open(flag, "w").write("x")
        os.utime(flag, (time.time() + 5, time.time() + 5))
        _push(SP, s3, one, led, ("quote_series",), deadline=time.time() + 600)
        n = len(_objs(s3.store, "quote_series"))
        ck("C6", n == 1, f"{n} object(s) with a drain waiting, want 1")
    except Exception as exc:
        ck("C6", False, f"raised {exc!r}")
    finally:
        if flag and os.path.exists(flag):
            os.remove(flag)

    # C7 / C8 — main --verify end to end (a fake boto3; the store at the module's own FEED_DB path)
    os.makedirs(os.path.dirname(SP.FEED_DB), exist_ok=True)
    fake = FakeS3()
    sys.modules["boto3"] = types.SimpleNamespace(client=lambda *a, **k: fake)

    def run_verify(budget):
        for p in (SP.FEED_DB, SP.CANDLE_LEDGER, SP.COUNTERS_PATH):
            if os.path.exists(p):
                os.remove(p)
        fake.store.clear()
        _db(SP.FEED_DB, [("quote_series", N)])
        old = getattr(SP, "SERIES_DRAIN_BUDGET_S", None)
        if old is not None:
            SP.SERIES_DRAIN_BUDGET_S = budget
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                SP.main(["--verify"])
        finally:
            if old is not None:
                SP.SERIES_DRAIN_BUDGET_S = old
        return buf.getvalue()

    drain_re = re.compile(r"DRAIN host=\S+ sym=\S+ drained=\S+ pushed=\d+ failed=\d+ prefixes=\d+ "
                          r"local=\d+ s3=\d+ short=\d+ (?P<verdict>\S+)$", re.M)
    try:
        out = run_verify(600)
        lag = re.search(r"^  SERIES_LAG series\|quote_series series_lag_s=(\d+)", out, re.M)
        m = drain_re.search(out)
        ck("C7", bool(lag) and lag.group(1) == "0" and m is not None and m.group("verdict") == "OK",
           f"lag line {lag.group(0) if lag else None!r}; drain verdict {m.group('verdict') if m else None}")
    except Exception as exc:
        ck("C7", False, f"raised {exc!r}")
    try:
        out = run_verify(0)
        lag = re.search(r"^  SERIES_LAG series\|quote_series series_lag_s=(\d+) BEHIND", out, re.M)
        m = drain_re.search(out)
        lines = out.splitlines()
        di = next((i for i, l in enumerate(lines) if l.startswith("DRAIN ")), -1)
        ck("C8", bool(lag) and int(lag.group(1)) > 0 and m is not None and m.group("verdict") == "SHORT"
           and di >= 0 and lines[di].rstrip().endswith("SHORT") and len(lines) - di <= 8,
           f"lag {lag.group(1) if lag else None}; drain verdict {m.group('verdict') if m else None}; "
           f"{len(lines) - di - 1 if di >= 0 else '?'} line(s) after DRAIN")
    except Exception as exc:
        ck("C8", False, f"raised {exc!r}")

    # C9 — self_close reads the lag lines
    try:
        from warehouse import self_close as SC
        f = getattr(SC, "series_lag_max")
        a = f("  SERIES_LAG series|quote_series series_lag_s=7620 BEHIND (x)\n"
              "  SERIES_LAG series|greeks_series series_lag_s=0\nDRAIN host=x ... short=0 SHORT\n")
        b = f("DRAIN host=x sym=y drained=yes pushed=1 failed=0 prefixes=1 local=1 s3=1 short=0 OK\n")
        ck("C9", a == 7620 and b == 0, f"max {a} (want 7620), none {b} (want 0)")
    except Exception as exc:
        ck("C9", False, f"raised {exc!r}")

    if _fails:
        print(f"\nRED — {len(_fails)} check(s) failed: {' '.join(_fails)}")
        return 1
    print("\nGREEN — a backlog is caught up in capped objects, and a drain that cannot finish says SHORT")
    return 0


if __name__ == "__main__":
    import shutil
    try:
        rc = main()
    finally:
        shutil.rmtree(_HOME, ignore_errors=True)
    sys.exit(rc)
