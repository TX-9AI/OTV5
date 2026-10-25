#!/usr/bin/env python3
"""
tests/check_level_engine_book.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.5  2026-10-18  OTV4TEST r296 (LVL.19) — E12: a bar still being built is never judged (audit 10-18 H1: 10 of the 40
      newest REJECTED rows were judged 12-19 s into their bar on a provisional close). E7 RE-POINTED: the hour it judges
      on is judged once it has CLOSED (its old clock stood 60 s into the hour - the same defect on the hourly candle);
      the test widens BOOK_FRESH_S locally to keep the hourly-pierce publish path under test.
v1.4  2026-10-01  OTV4TEST FLIP.1 — E5 RE-POINTED BY THE RULING, NOT DELETED: the breach
      bar now also publishes the lone level's FLIPPED row, so E5 pins "a second derive
      publishes nothing new" (n0 == n1) and exactly one NON-flip event.
v1.3  2026-09-23  OTV4TEST r126 — THE LEGACY PATH IS DELETED, SO THREE THINGS MOVE HERE.
      E6 is RETARGETED: there is no LEVEL_SOURCE switch left to be "book" — the
      assertion is now that derive() has only the book path (no switch, no
      legacy methods), red on r125 where both still exist. And two properties
      MOVED from deleted legacy checkers (§38.4), both still live: E10 (was
      check_level_rejection L7) — DerivedStore.latest_rejection filters by
      KIND and by TIME, which the sweep's trigger and the exit engine's handoff
      both call; E11 (was check_level_map M8) — a feed with NO tape leaves the
      ledger exactly as it was: nothing is retired for want of bars.
v1.2  2026-09-23  OTV4TEST r124 — E9: the board's zone width comes from the BOOK the
      engine builds (book.width), with NO ctx["level_tape"] — main.py no longer
      sends one. Red on r123, where board() measured the width from that tape.
THE LIVE LEVEL ENGINE PUBLISHES THE LEVEL BOOK — driven through `derive()`.

v1.1  2026-09-23  OTV4TEST r111 — E8: the ledger reads TRAVERSED for a level retired
      inside the opening range.
v1.0  2026-09-23  OTV4TEST LVL.15 step 2 (r110; carries the r106 venv bootstrap). Born RED at 7df8438, where the engine
      has no book path: `derive()` on the same tape publishes nothing.

Every plan that trades levels reads `level_ledger` (the board) and
`level_event` (REJECTED for the sweep, ACCEPTED for the TCS). Step 2 changes
WHERE those rows come from — the book, on the operator's definitions — and
nothing about who reads them. So the contract is the two tables:

  E1 a BREACHED (1m close beyond, next 1m open beyond) is published as
     ACCEPTED on the level, stamped with the bar that opened beyond
  E2 a HELD is published as REJECTED, and its pierce is the deepest point
     beyond the near edge over the whole TESTED->HELD episode (r44)
  E3 §37: after a restart the book replays, and an event older than
     BOOK_FRESH_S is NOT published — an old trigger never reaches a plan
  E4 the ledger holds exactly the book's live levels: an old-format row is
     retired, the book's level is live, and a breached one retires BREACHED
  E5 a second derive on the same closed bar publishes nothing new
  E6 hop 0: `derive()` routes to the book when LEVEL_SOURCE is "book"
  E8 a level the book retired inside the opening range is retired TRAVERSED
     in the ledger, never BREACHED (operator's ruling 2026-09-23)
  E9 the board's zone width is the book's own (level_book.zone_width of the
     same hourly bars), set by the sync, with no level_tape in ctx (r124)
  E10 latest_rejection() filters by kind and by time (moved from check_level_rejection L7)
  E11 no tape in the feed -> the ledger is left exactly as it was (moved from
      check_level_map M8)
  E7 a HELD judged on the HOUR (no 1m candle in its episode — a feed hole)
     is published with the hourly pierce and does NOT fail the sync. Red on
     the first cut of this engine: max() of an empty span raised and froze the
     ledger; found by mutating the freshness window, which surfaced it.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# r106 IDIOM — THE LANDER RUNS CHECKS UNDER SYSTEM `python3`, NOT THE VENV, and
# this file reaches pandas/numpy, which live only in the venv (3.14, the same
# ABI as system python3 on this box — measured 2026-09-23). Index 1: the venv
# beats /usr/lib/python3/dist-packages while the repo root still wins. Without
# it this checker could not be DECLARED as a CHECK — it failed under the lander
# on `No module named 'pandas'` while passing by hand.
import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
FAILED, RAN = [], []
H, M = 3_600_000, 60_000
D = int(datetime(2026, 9, 21, tzinfo=timezone.utc).timestamp() * 1000)   # Monday, EDT
RTH = D + 24 * H + 13 * H + 30 * M                                      # Tue 09:30 ET
WORK = tempfile.mkdtemp(prefix="chk_lvl_engine-")


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:                                    # noqa: BLE001
        ok, detail = False, f"raised {type(exc).__name__}: {exc}"
    check(name, ok, detail)


def tape(cut_ms):
    """A feed store: flat 100.00 +-0.30 hours for two days, a PRE-MARKET high
    of 101.00 on Tuesday at 06:00 ET, then Tuesday's RTH on 1m:
      09:39  reaches 101.30, closes 101.20       -> TESTED, close beyond
      09:40  OPENS BACK INSIDE 100.95, closes 100.90 -> HELD at the close back
             (ruling 2026-09-22); the episode's pierce is 0.30, the HELD
             candle's own wick only 0.05 — E2 tells the two apart
      09:50  closes 101.20                        -> close beyond
      09:51  opens 101.25                         -> BREACHED
    Everything at/after `cut_ms` is removed, so the tape ends where a live
    engine would be standing."""
    p = tempfile.mktemp(dir=WORK, prefix=f"feed-{cut_ms}-", suffix=".db")   # one tape per call
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER, open REAL,"
              " high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY(symbol, interval, ts_epoch_ms))")
    rows = []
    for i in range(24 + 13):
        t = D + i * H
        hi = 101.0 if t == D + 24 * H + 10 * H else 100.3
        rows.append(("QQQ", "1h", t, 100.0, hi, 99.7, 100.0, 1.0))
    for k in range(0, 60):
        t = RTH + k * M
        o, h, l, cl = 100.5, 100.6, 100.4, 100.5
        if k == 9:
            o, h, l, cl = 100.8, 101.3, 100.8, 101.2
        elif k == 10:
            o, h, l, cl = 100.95, 101.05, 100.85, 100.9
        elif k == 20:
            o, h, l, cl = 100.9, 101.25, 100.85, 101.2
        elif k >= 21:
            o, h, l, cl = 101.25, 101.4, 101.22, 101.3
        rows.append(("QQQ", "1m", t, o, h, l, cl, 1.0))
    c.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", [r for r in rows if r[2] < cut_ms])
    c.commit()
    c.close()
    return p


def engine_at(cut_ms, clock_s, seed_old=False, store=None):
    """A fresh engine and derived store, the feed cut at `cut_ms`, the clock at
    `clock_s`, and ONE derive() call with a df_1m whose [-2] is the last closed bar."""
    import pandas as pd
    os.environ["OT_FEED_DB"] = tape(cut_ms)
    from data.derived_store import DerivedStore
    import derived.levels as L
    L.time.time = lambda: float(clock_s)
    store = store or DerivedStore(tempfile.mktemp(dir=WORK, prefix="derived-", suffix=".db"))
    if seed_old:
        store.upsert_level(("QQQ:london:99.10", "QQQ", 99.1, "support", "london",
                            "session:2026-09-18", 1.0, 0, None, 0, None, None, 0))
    eng = L.LevelEngine(store, "QQQ")
    idx = pd.to_datetime([cut_ms - 2 * M, cut_ms - M], unit="ms", utc=True).tz_convert("America/New_York")
    df1 = pd.DataFrame({"open": [100.5, 100.5], "high": [100.6, 100.6], "low": [100.4, 100.4],
                        "close": [100.5, 100.5]}, index=idx)
    ctx = {"symbol": "QQQ", "price": 100.5, "df_1m": df1}
    eng.derive(ctx)
    return eng, store, ctx


def hour_tape():
    """Hours only on Tuesday: the 15Z (11:00 ET) HOUR reaches 101.30 and closes
    100.90 — TESTED + HELD judged on '1h'. The only 1m candles are Monday's, so
    the book has a minute tape but none inside this episode."""
    p = tempfile.mktemp(dir=WORK, prefix="feedh-", suffix=".db")
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER, open REAL,"
              " high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY(symbol, interval, ts_epoch_ms))")
    rows = []
    for i in range(24 + 16):
        t = D + i * H
        hi, cl = 100.3, 100.0
        if t == D + 24 * H + 10 * H:
            hi = 101.0                                   # the pre-market high
        if t == D + 24 * H + 15 * H:
            hi, cl = 101.3, 100.9                        # the hour that holds it
        rows.append(("QQQ", "1h", t, 100.0, hi, 99.7, cl, 1.0))
    rows += [("QQQ", "1m", D + 14 * H + k * M, 100.0, 100.1, 99.9, 100.0, 1.0) for k in range(30)]
    c.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()
    return p


def events(store):
    return store.conn.execute("SELECT level_id, bar_ts, event, round(pierce_pct, 6) FROM level_event"
                              " ORDER BY bar_ts").fetchall()


def _e1():
    cut = RTH + 23 * M                                       # standing at 09:53
    _eng, store, _ = engine_at(cut, cut / 1000 + 5)
    ev = [e for e in events(store) if e[2] == "ACCEPTED"]
    ok = len(ev) == 1 and ev[0][0] == "QQQ:resistance:101.00" and ev[0][1].startswith("2026-09-22 09:51")
    return ok, f"ACCEPTED rows {ev}"


def _e2():
    cut = RTH + 12 * M                                       # standing at 09:42
    _eng, store, _ = engine_at(cut, cut / 1000 + 5)
    ev = [e for e in events(store) if e[2] == "REJECTED"]
    want = round(0.30 / 101.0, 6)          # the EPISODE, not the HELD candle's 0.05
    ok = (len(ev) == 1 and ev[0][0] == "QQQ:resistance:101.00" and ev[0][1].startswith("2026-09-22 09:40")
          and abs(ev[0][3] - want) < 1e-6)
    return ok, f"REJECTED rows {ev} (want pierce {want})"


def _e3():
    cut = RTH + 23 * M
    _eng, store, _ = engine_at(cut, cut / 1000 + 30 * 60)    # restarted 30 minutes later
    ev = events(store)
    live = [r[0] for r in store.conn.execute("SELECT level_id FROM level_ledger WHERE retired_ts IS NULL")]
    return (not ev and "QQQ:resistance:101.00" not in live), f"events {ev}; 101.00 live: {'QQQ:resistance:101.00' in live}"


def _e4():
    cut_held, cut_dead = RTH + 12 * M, RTH + 23 * M
    _e, s1, _ = engine_at(cut_held, cut_held / 1000 + 5, seed_old=True)
    rows1 = dict(s1.conn.execute("SELECT level_id, retired_reason FROM level_ledger").fetchall())
    # the SAME store, a new engine (a restart) standing after the breach
    _e, s2, _ = engine_at(cut_dead, cut_dead / 1000 + 5, store=s1)
    rows2 = dict(s2.conn.execute("SELECT level_id, retired_reason FROM level_ledger").fetchall())
    ok = (rows1.get("QQQ:london:99.10") == "NOT_A_LEVEL" and "QQQ:resistance:101.00" in rows1
          and rows1["QQQ:resistance:101.00"] is None
          and rows2.get("QQQ:resistance:101.00") == "BREACHED"
          and "QQQ:resistance:101.00" not in [r[0] for r in s2.conn.execute(
              "SELECT level_id FROM level_ledger WHERE retired_ts IS NULL")])
    return ok, f"held-time ledger {rows1}; after breach 101.00 -> {rows2.get('QQQ:resistance:101.00')}"


def _e5():
    cut = RTH + 23 * M
    eng, store, ctx = engine_at(cut, cut / 1000 + 5)
    n0 = len(events(store))
    eng._book_bar = ""                                       # even a forced re-sync
    eng.derive(ctx)
    n1 = len(events(store))
    # v1.4 (FLIP.1): the breach bar now also publishes the lone level's FLIPPED
    # row — so the pin is "nothing NEW" (n0 == n1) and exactly ONE non-flip event.
    nf = len([e for e in events(store) if ":flip:" not in e[0]])
    return (n0 == n1 and nf == 1), f"events after first {n0}, after second {n1}, non-flip {nf}"


def _e6():
    import derived.levels as L
    legacy = [m for m in ("_derive_events", "_sources", "_tape_sources", "_reconcile")
              if hasattr(L.LevelEngine, m)]
    return (not hasattr(L, "LEVEL_SOURCE") and not legacy and hasattr(L.LevelEngine, "_derive_book")), \
        f"LEVEL_SOURCE present: {hasattr(L, 'LEVEL_SOURCE')}; legacy methods: {legacy}"


def _e7():
    import pandas as pd
    import logging
    os.environ["OT_FEED_DB"] = hour_tape()
    from data.derived_store import DerivedStore
    import derived.levels as L
    t_ev = D + 24 * H + 15 * H
    # r296 (LVL.19): the hour is judged once it has CLOSED (t_ev + H), not 60 s into it; an hourly event is
    # then older than BOOK_FRESH_S, so the window is widened HERE to keep the hourly-pierce publish path under test.
    L.time.time = lambda: (t_ev + H) / 1000.0 + 60
    _fresh = L.BOOK_FRESH_S
    L.BOOK_FRESH_S = 4000.0
    fails = []

    class _Catch(logging.Handler):
        def emit(self, rec):
            if "book sync FAILED" in rec.getMessage():
                fails.append(rec.getMessage())
    h = _Catch()
    logging.getLogger("derived.levels").addHandler(h)
    try:
        store = DerivedStore(tempfile.mktemp(dir=WORK, prefix="derived-", suffix=".db"))
        eng = L.LevelEngine(store, "QQQ")
        idx = pd.to_datetime([t_ev, t_ev + M], unit="ms", utc=True).tz_convert("America/New_York")
        df1 = pd.DataFrame({"open": [100.5] * 2, "high": [100.6] * 2, "low": [100.4] * 2,
                            "close": [100.5] * 2}, index=idx)
        eng.derive({"symbol": "QQQ", "price": 100.5, "df_1m": df1})
    finally:
        logging.getLogger("derived.levels").removeHandler(h)
        L.BOOK_FRESH_S = _fresh
    ev = [e for e in events(store) if e[2] == "REJECTED" and e[0] == "QQQ:resistance:101.00"]
    want = round(0.30 / 101.0, 6)
    ok = not fails and len(ev) == 1 and abs(ev[0][3] - want) < 1e-6
    return ok, f"sync failures {fails}; REJECTED {ev} (want pierce {want})"


def _e8():
    """The ledger names WHY: a level retired inside the opening range reads
    TRAVERSED, never BREACHED (operator's ruling 2026-09-23)."""
    import derived.levels as L
    import derived.level_book as B

    class _Book:
        live, dead, traversed, events = {}, {"QQQ:support:99.00": RTH + 5 * M}, {"QQQ:support:99.00"}, []
    _orig = B.build
    B.build = lambda *a, **k: _Book()
    try:
        cut = RTH + 6 * M
        os.environ["OT_FEED_DB"] = tape(cut)
        from data.derived_store import DerivedStore
        L.time.time = lambda: cut / 1000.0 + 5
        store = DerivedStore(tempfile.mktemp(dir=WORK, prefix="derived-", suffix=".db"))
        store.upsert_level(("QQQ:support:99.00", "QQQ", 99.0, "support", "premarket",
                            "session:2026-09-22", 1.0, 0, None, 0, None, None, 0))
        L.LevelEngine(store, "QQQ")._book_sync("QQQ")
        why = store.conn.execute("SELECT retired_reason FROM level_ledger WHERE level_id='QQQ:support:99.00'").fetchone()
    finally:
        B.build = _orig
    return (why and why[0] == "TRAVERSED"), f"retired_reason {why}"


guard("E1 a BREACHED is published as ACCEPTED at the bar that opened beyond", _e1)
guard("E2 a HELD is published as REJECTED with the episode's deepest pierce", _e2)
guard("E3 §37: a restart does not publish an event older than BOOK_FRESH_S", _e3)
guard("E4 the ledger holds exactly the book's live levels; old rows retire", _e4)
guard("E5 a second derive on the same bar publishes nothing new", _e5)
guard("E6 hop 0: derive() has only the book path — no LEVEL_SOURCE switch, no legacy methods", _e6)
guard("E7 a HELD judged on the hour publishes its hourly pierce; the sync survives", _e7)
guard("E8 a level retired inside the opening range reads TRAVERSED in the ledger", _e8)


def _e9():
    from derived import level_book as B
    cut = RTH + 15 * M
    eng, store, ctx = engine_at(cut, cut / 1000 + 5)
    want = B.zone_width(B.load_bars(os.environ["OT_FEED_DB"], "QQQ", "1h"))
    got = getattr(eng, "_zone_width", None)
    bw = eng.board(100.5).get("zone_width")
    return (want is not None and got == want and bw == want and "level_tape" not in ctx), \
        f"book width {want}; engine {got}; board {bw}"


guard("E9 the board's zone width is the book's, with no level_tape in ctx (r124)", _e9)


def _e10():
    cut = RTH + 12 * M
    clock = cut / 1000 + 5
    _eng, store, _ = engine_at(cut, clock)
    r = store.latest_rejection("QQQ", 0.0, kind="resistance")
    none_kind = store.latest_rejection("QQQ", 0.0, kind="support")
    none_time = store.latest_rejection("QQQ", clock + 60.0)
    ok = (r is not None and r["level_id"] == "QQQ:resistance:101.00"
          and none_kind is None and none_time is None)
    return ok, f"resistance {r and r['level_id']}; support {none_kind}; after {none_time}"


def _e11():
    cut = D                                                   # the feed ends before its first bar
    _eng, store, _ = engine_at(cut, cut / 1000 + 5, seed_old=True)
    rows = store.conn.execute("SELECT level_id, retired_ts FROM level_ledger").fetchall()
    return (rows == [("QQQ:london:99.10", None)]), f"ledger {rows}"


guard("E10 latest_rejection() filters by kind and by time", _e10)
guard("E11 no tape in the feed -> the ledger is left exactly as it was", _e11)


def _e12():
    """r296 (LVL.19): the 09:40 HELD bar is in the store (the feed flushes the forming minute within 2 s)
    but the clock stands 20 s INTO it - nothing may be judged on it yet; 65 s later it is closed and the
    REJECTED publishes with the same bar_ts and pierce E2 pins."""
    import derived.levels as L
    cut = RTH + 11 * M                                       # the store holds bars up to and including 09:40
    forming = (RTH + 10 * M) / 1000.0 + 20                   # 09:40:20 - the 09:40 bar is still being built
    eng, store, _ = engine_at(cut, forming)
    early = [e for e in events(store) if e[2] == "REJECTED"]
    L.time.time = lambda: (RTH + 11 * M) / 1000.0 + 5        # 09:41:05 - the 09:40 bar is closed
    eng._book_sync("QQQ")
    late = [e for e in events(store) if e[2] == "REJECTED"]
    want = round(0.30 / 101.0, 6)
    ok = (early == [] and len(late) == 1 and late[0][0] == "QQQ:resistance:101.00"
          and late[0][1].startswith("2026-09-22 09:40") and abs(late[0][3] - want) < 1e-6)
    return ok, f"while forming: {early}; after the close: {late}"


guard("E12 a bar still being built is never judged: no REJECTED at 09:40:20, the REJECTED at 09:41:05 (r296)", _e12)

shutil.rmtree(WORK, ignore_errors=True)
print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
