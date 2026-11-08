#!/usr/bin/env python3
"""
tests/check_replay_stream.py  v5.0
v5.0  2026-11-07  OTV5 r75 (REPLAY.1) — new. THE COUNTERFACTUAL TOOLS RUN ON CONTROL. exit_replay v5.1 streams
      raw/quote_series one object at a time and holds one ET day of the traded contracts' quotes; stop_sweep v5.1 sorts a
      surface whose take-profit cell is None. The Saturday brief 11-07 §6: exit_replay rc 137 (OOM) on 11-02 alone, 1,218
      objects / 6.2 GB of JSON a day; stop_sweep TypeError at line 143 on Runaway call (n 21).
  M1  A SYNTHETIC LARGE DAY STAYS SMALL: 240 objects x 6,000 rows (1.44M rows, ~1 GB if materialised) on three boxes; the
      streamed fetch keeps only the traded contract inside its window, and tracemalloc's peak stays under 40 MB
  M2  ONLY THE OBJECTS THAT OVERLAP A TRADE WINDOW ARE READ: the exact read set is the batches whose (previous key epoch,
      own key epoch] meets the padded window, including the one straddling each edge; every other object is skipped and
      counted; a box with no trade that day is never listed
  M3  THE PATH IS THE SAME PATH: path_for over the streamed fetch equals path_for over the v1.1 in-memory index on the same
      objects
  M4  ONE DAY AT A TIME: a trade on the next ET day drops the previous day's index before loading
  M5  A SYMBOL WITH NO PARTITION FALLS BACK TO EVERY PARTITION, still window-filtered, and the fallback is counted
  M6  AN UNPARSEABLE KEY IS READ, NOT SKIPPED
  M7  run_s3 never calls load_series (the materialising reader) — the call that OOM-killed control
  C1  THE RECORDED-EXIT CONTROL: a trade whose path ends where pnl_usd says reconciles and the run prints VERIFIED; the same
      trade booked at twice the path's value prints NOT VERIFIED and names the miss
  S1  stop_sweep: a surface with >= MIN_N rows renders without TypeError, and "none" (tp None) prints before tp 0.25
      within a stop
Mutation-tested: run_s3 back on load_series -> red at M7; _select returning every key -> red at M2; the `prev <= hi`
bound dropped -> red at M2; the day index not dropped on a day change -> red at M4; the row filter keeping every symbol
-> red at M1; the fallback not counted -> red at M5; untimed keys skipped -> red at M6; the control's >= 90% bar
inverted -> red at C1; _cell_order removed from the render sort -> red at S1.
Run:  python3 tests/check_replay_stream.py
"""
import contextlib
import inspect
import io
import os
import sys
import tracemalloc
from datetime import datetime, timezone

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "tests"))

import exit_replay as er          # noqa: E402
import stop_sweep as ss           # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        FAILED.append(label.split()[0])


# 2026-11-02 15:00 UTC = 10:00 ET; the trade runs 10:00-10:10 ET
DAY = "2026-11-02"
T0 = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc).timestamp()
T1 = T0 + 600          # ten minutes: every box runs this at its boot sweep, so it stays a few seconds
OCC = "QQQ   261102C00650000"
ST = ".QQQ261102C650"
OPEN = datetime(2026, 11, 2, 14, 30, tzinfo=timezone.utc).timestamp()   # 09:30 ET
SPAN = 60.0                                                            # one batch a minute


def _trade(t0=T0, t1=T1, sym="QQQ", occ=OCC, pnl=50.0):
    iso = lambda e: datetime.fromtimestamp(e, timezone.utc).isoformat()   # noqa: E731
    return {"trade_id": "t1", "status": "closed", "symbol": sym, "strategy": "LiquidityHunt",
            "option_side": "call", "option_symbol": occ, "entry_time": iso(t0),
            "exit_time": iso(t1), "entry_premium": 1.0, "contracts": 1, "pnl_usd": pnl,
            "exit_reason": "decay"}


class FakeStore:
    """Lazily generated quote batches: objects are BUILT on read, so the store itself costs nothing and every byte the
    fetch keeps is the fetch's own."""

    def __init__(self, parts, n_obj, rows_per, day=DAY, start=OPEN, extra_keys=()):
        self.parts, self.n_obj, self.rows_per, self.day, self.start = parts, n_obj, rows_per, day, start
        self.extra = list(extra_keys)
        self.listed_prefixes, self.read_keys = [], []

    def key(self, part, i):
        to = self.start + (i + 1) * SPAN
        return f"raw/quote_series/dt={self.day}/sym={part}/{int(to * 1000)}-h{i:04d}.json"

    def lister(self, prefix):
        self.listed_prefixes.append(prefix)
        out = []
        for part in self.parts:
            for i in range(self.n_obj):
                k = self.key(part, i)
                if k.startswith(prefix):
                    out.append(k)
        out += [k for k in self.extra if k.startswith(prefix)]
        return out

    def reader(self, key):
        self.read_keys.append(key)
        if key in self.extra:
            return {"record": [{"streamer_symbol": ST, "ts_epoch": T0 + 5, "bid_price": 1.0, "ask_price": 1.1}]}
        part = key.split("sym=")[1].split("/")[0]
        i = int(key.rsplit("-h", 1)[1].split(".")[0])
        lo = self.start + i * SPAN
        rec = []
        for j in range(self.rows_per):
            ts = lo + SPAN * (j + 1) / self.rows_per
            sym = ST if (part == "QQQ" and j % 50 == 0) else f".{part}261102C{100 + j % 400}"
            mid = 1.0 + (ts - T0) / 3600.0
            rec.append({"streamer_symbol": sym, "ts_epoch": ts, "bid_price": mid - 0.01,
                        "ask_price": mid + 0.01, "bid_size": 1.0, "ask_size": 1.0, "sequence": j})
        return {"record": rec}


def expected_reads(store, part, lo, hi):
    out, prev = [], float("-inf")
    for i in range(store.n_obj):
        e = store.start + (i + 1) * SPAN
        if lo <= e and prev <= hi:
            out.append(store.key(part, i))
        prev = e
    return out


def main():
    # ── M1 / M2: a large synthetic day ─────────────────────────────────────
    store = FakeStore(["QQQ", "SPX", "AMD"], n_obj=240, rows_per=6000)
    rows = [_trade()]
    fetch = er._S3StreamFetch(rows, lister=store.lister, reader=store.reader)
    tracemalloc.start()
    got = fetch(ST, T0 - 60, T1 + 60)
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    wanted = expected_reads(store, "QQQ", T0 - 60, T1 + 60)
    only_st = all(lo_ok for lo_ok in (T0 - 60 <= p[0] <= T1 + 60 for p in got))
    check("M1 a 1.44M-row synthetic day is held as only the traded contract's window",
          bool(got) and only_st and fetch.kept == len(got) and peak < 40 * 2**20,
          f"kept {fetch.kept} rows, tracemalloc peak {peak / 2**20:.1f} MB")
    check("M2 exactly the window's batches are read; the rest are skipped and counted; untraded boxes never listed",
          store.read_keys == wanted and fetch.skipped == 240 - len(wanted)
          and all("sym=QQQ/" in p for p in store.listed_prefixes),
          f"read {len(store.read_keys)} (want {len(wanted)}), skipped {fetch.skipped}, listed {store.listed_prefixes}")

    # ── M3: same path as the in-memory index ───────────────────────────────
    small = FakeStore(["QQQ"], n_obj=60, rows_per=200)
    f_stream = er._S3StreamFetch(rows, lister=small.lister, reader=small.reader)
    allrows = []
    for k in small.lister(""):
        allrows.extend(small.reader(k)["record"])
    legs = [(ST, +1)]
    p_stream, _w1 = er.path_for(f_stream, legs, T0, T1)
    p_mem, _w2 = er.path_for(er._s3_fetch(allrows), legs, T0, T1)
    check("M3 path_for over the streamed fetch equals the in-memory index's path",
          bool(p_stream) and p_stream == p_mem, f"{len(p_stream or [])} vs {len(p_mem or [])} points")

    # ── M4: one day at a time ──────────────────────────────────────────────
    nxt0 = T0 + 86400
    two = [_trade(), _trade(t0=nxt0, t1=nxt0 + 600)]
    d1 = FakeStore(["QQQ"], n_obj=60, rows_per=100)
    d2 = FakeStore(["QQQ"], n_obj=60, rows_per=100, day="2026-11-03", start=OPEN + 86400)

    def lister2(prefix):
        return d1.lister(prefix) + d2.lister(prefix)

    def reader2(key):
        return (d2 if "dt=2026-11-03" in key else d1).reader(key)
    f2 = er._S3StreamFetch(two, lister=lister2, reader=reader2)
    a = f2(ST, T0 - 60, T1 + 60)
    b = f2(ST, nxt0 - 60, nxt0 + 660)
    day1_left = [p for p in f2.idx.get(ST, ()) if p[0] < nxt0 - 3600]
    check("M4 the next ET day drops the previous day's index before loading",
          bool(a) and bool(b) and f2.day == "2026-11-03" and not day1_left,
          f"day {f2.day}, {len(day1_left)} day-1 rows still held")

    # ── M5: partition fallback ─────────────────────────────────────────────
    fb = FakeStore(["QQQ"], n_obj=60, rows_per=200)
    f5 = er._S3StreamFetch([_trade(sym="NOSUCH")], lister=fb.lister, reader=fb.reader)
    g5 = f5(ST, T0 - 60, T1 + 60)
    check("M5 a symbol with no partition falls back to every partition, window-filtered, and is counted",
          bool(g5) and f5.fallback == 1 and f5.skipped > 0, f"fallback {f5.fallback}, skipped {f5.skipped}")

    # ── M6: unparseable key ────────────────────────────────────────────────
    odd = f"raw/quote_series/dt={DAY}/sym=QQQ/batch-final.json"
    s6 = FakeStore(["QQQ"], n_obj=10, rows_per=10, extra_keys=[odd])
    f6 = er._S3StreamFetch(rows, lister=s6.lister, reader=s6.reader)
    f6(ST, T0 - 60, T1 + 60)
    check("M6 an object whose key carries no epoch is read, not skipped", odd in s6.read_keys,
          f"{len(s6.read_keys)} read")

    # ── M7: run_s3 does not materialise ────────────────────────────────────
    src = inspect.getsource(er.run_s3)
    check("M7 run_s3 never calls load_series", "load_series(" not in src and "_S3StreamFetch(" in src)

    # ── C1: the recorded-exit control ──────────────────────────────────────
    cs = FakeStore(["QQQ"], n_obj=60, rows_per=200)
    path, _ = er.path_for(er._S3StreamFetch(rows, lister=cs.lister, reader=cs.reader), legs, T0, T1)
    move = (path[-1][1] - path[0][1]) * 100.0
    out_ok, out_bad = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out_ok):
        er.run([_trade(pnl=move)], er._S3StreamFetch(rows, lister=cs.lister, reader=cs.reader))
    with contextlib.redirect_stdout(out_bad):
        er.run([_trade(pnl=2 * move)], er._S3StreamFetch(rows, lister=cs.lister, reader=cs.reader))
    ok_line = [ln for ln in out_ok.getvalue().splitlines() if "RECORDED-EXIT CONTROL" in ln]
    bad_txt = out_bad.getvalue()
    check("C1 the recorded-exit control passes a true path and fails a doubled booking by name",
          ok_line and ok_line[0].rstrip().endswith("VERIFIED") and "NOT VERIFIED" not in ok_line[0]
          and "NOT VERIFIED" in bad_txt and "miss QQQ" in bad_txt,
          f"ok: {ok_line[0].strip() if ok_line else 'no control line'}")

    # ── S1: stop_sweep surface with a None take-profit ─────────────────────
    srows = []
    for i in range(ss.MIN_N + 2):
        win = i % 2 == 0
        srows.append(dict(pnl_usd=(120.0 + i) if win else -(40.0 + i), entry_premium=1.0,
                          mfe_premium=2.0 if win else 1.05, mae_premium=0.9 if win else 0.5,
                          mfe_bars=10, mae_bars=3 if win else 12, contracts=1, is_short_position=0,
                          strategy="RunawayContinuation", option_side="call"))
    buf = io.StringIO()
    err = ""
    try:
        with contextlib.redirect_stdout(buf):
            ss.render(srows, "fixture")
    except TypeError as exc:
        err = str(exc)
    lines = [ln.split() for ln in buf.getvalue().splitlines()]
    cells = [(ln[0], ln[1]) for ln in lines if len(ln) > 2 and ln[0].replace(".", "").isdigit()]
    first_stop = [tp for st, tp in cells if st == cells[0][0]] if cells else []
    check("S1 stop_sweep renders a surface with tp None; 'none' prints first within a stop",
          not err and first_stop[:2] == ["none", "0.25"],
          err or f"{len(cells)} cells, first stop row order {first_stop[:3]}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — check_replay_stream: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
