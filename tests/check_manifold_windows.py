#!/usr/bin/env python3
"""
tests/check_manifold_windows.py  v1.1

v1.1  2026-10-05  OTV4TEST r252 (BOX.18) - the fixture is SPX's board, so the box instrument is PINNED to SPX
      (manifold_health v4.4 judges only the box's own instrument + VIX; under the sweep's OT_INSTRUMENT=QQQ the SPX
      rows would be foreign). No assertion changed.

r95 — THE BOARD MUST BE ABLE TO REACH ITS OWN GOOD STATE.

🔴 WHY. Operator, 2026-08-24: "those sections will never be green during RTH &
if used in the dashboard, it would never show green."

`<SYM>_EXT` is the NON-RTH route — candle_feed segregates every out-of-session
bar to it. During RTH it therefore receives nothing and ages, exactly as
designed. Judged against an RTH freshness budget it painted AMBER on every box,
every session, forever, and dragged the rollup to DEGRADED with it. **A rollup
that cannot reach GREEN is not a rollup**, and a permanently-amber row is how a
reader is trained to stop looking (WORKING_AGREEMENT 17 / the CV.1 failure).

The fixture below is built from the SPX board the operator screenshotted at
10:36 ET on 2026-08-24: SPX_EXT fresh (a real extended subscription), VIX_EXT
aged 4868-9308s (pre-market bars, segregated), session_summary aged 3003s, and
prints/underlying/theo at zero rows.

⚠️ IT DRIVES REAL SQLITE AND THE REAL collect()/rollup(). No source reading
(WORKING_AGREEMENT 21).

Run:  python3 tests/check_manifold_windows.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.manifold_health import (                             # noqa: E402
    collect, rollup, GREEN, AMBER, RED, GREY, NA)

FAILURES: list = []
NOW = time.time()


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def _build_feed(path, prints_rows=0):
    """A feed store shaped like SPX's at 10:36 ET on 2026-08-24."""
    c = sqlite3.connect(path)
    for t, col in (("greeks_series", "ts_epoch"), ("quote_series", "ts_epoch"),
                   ("prints", "ts_epoch"), ("last_trade", "ts_epoch"),
                   ("session_summary", "ts_epoch"),
                   ("underlying_series", "ts_epoch"), ("theo_series", "ts_epoch")):
        c.execute(f"CREATE TABLE {t} (id INTEGER PRIMARY KEY, {col} REAL)")
    c.execute("CREATE TABLE chain_marks (id INTEGER PRIMARY KEY, updated_epoch REAL)")
    c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT,"
              " ts_epoch_ms INTEGER, open REAL, high REAL, low REAL,"
              " close REAL, volume REAL)")

    def ins(tbl, col, age):
        c.execute(f"INSERT INTO {tbl} ({col}) VALUES (?)", (NOW - age,))

    ins("greeks_series", "ts_epoch", 25)
    ins("quote_series", "ts_epoch", 1)
    ins("chain_marks", "updated_epoch", 1)
    ins("last_trade", "ts_epoch", 1)
    ins("session_summary", "ts_epoch", 3003)      # 09:46 — session boundary
    for _ in range(prints_rows):
        ins("prints", "ts_epoch", 1)
    # underlying_series / theo_series deliberately left EMPTY (rows=0)

    def bar(sym, iv, age_s):
        c.execute("INSERT INTO candles VALUES (?,?,?,1,1,1,1,0)",
                  (sym, iv, int((NOW - age_s) * 1000)))

    for iv, age in (("1m", 8), ("5m", 8), ("15m", 308), ("1h", 2108), ("1d", 52508)):
        bar("SPX", iv, age)
        bar("SPX_EXT", iv, age)                   # a live extended subscription
        bar("VIX", iv, age)
    for iv, age in (("1m", 4868), ("5m", 5108), ("15m", 5708), ("1h", 9308)):
        bar("VIX_EXT", iv, age)                   # pre-market, segregated
    c.commit()
    c.close()


def main() -> int:
    os.environ["OT_INSTRUMENT"] = "SPX"           # v1.1: the fixture is SPX's board
    print("check_manifold_windows — freshness is judged in each stream's own window")

    d = tempfile.mkdtemp()
    feed = os.path.join(d, "feed_store.db")
    _build_feed(feed)
    derived = os.path.join(d, "derived_store.db")   # absent: normal degraded state

    def find(rep, key, label):
        return next(x for x in rep[key] if x["label"] == label)

    # ── W1: DURING RTH THE BOARD CAN REACH GREEN ─────────────────────────────
    # This is the deliverable. Before r95 this fixture returned AMBER on the
    # VIX_EXT rows alone.
    rth = collect(feed, derived, in_rth=True, is_index=True)
    check("W1 during RTH the rollup is GREEN", rollup(rth) == GREEN,
          f"rollup={rollup(rth)}")

    # ── W2: THE EXT ROWS ARE IDLE, NOT FAULTY ────────────────────────────────
    vix_ext = find(rth, "candles", "VIX_EXT/1m")
    check("W2 VIX_EXT is ⚪ IDLE during RTH, not AMBER",
          vix_ext["bulb"] == GREY and vix_ext["after_hours"] is True,
          f"bulb={vix_ext['bulb']} after_hours={vix_ext['after_hours']}")

    # ⚠️ AT 3003s THE SUMMARY IS STILL INSIDE ITS 3600s BUDGET, so GREEN is the
    # correct answer here — the window rule only governs what STALENESS means.
    # The real requirement is the one below: once it ages past the budget, which
    # it does every single session by ~10:45, it must go IDLE and not AMBER.
    summ = find(rth, "streams", "session summary")
    check("W2b session summary is classified after-hours",
          summ["after_hours"] is True and summ["bulb"] != AMBER,
          f"bulb={summ['bulb']}")

    aged = os.path.join(d, "aged_summary.db")
    _build_feed(aged)
    con = sqlite3.connect(aged)
    con.execute("UPDATE session_summary SET ts_epoch=?", (NOW - 20000,))
    con.commit(); con.close()
    ag = collect(aged, derived, in_rth=True, is_index=True)
    ag_s = find(ag, "streams", "session summary")
    check("W2c an aged session summary is ⚪ IDLE in RTH, never AMBER",
          ag_s["bulb"] == GREY and rollup(ag) == GREEN,
          f"bulb={ag_s['bulb']} rollup={rollup(ag)}")

    # ── W3: THE RTH ROWS ARE STILL JUDGED ────────────────────────────────────
    # The failure direction that matters: a window rule that silences EVERYTHING
    # would also show green, and would be useless.
    spx1m = find(rth, "candles", "SPX/1m")
    check("W3 the plain RTH series is still judged GREEN on fresh rows",
          spx1m["bulb"] == GREEN and spx1m["after_hours"] is False,
          f"bulb={spx1m['bulb']}")

    stale = os.path.join(d, "stale.db")
    _build_feed(stale)
    con = sqlite3.connect(stale)
    con.execute("UPDATE candles SET ts_epoch_ms=? WHERE symbol='SPX'"
                " AND interval='1m'", (int((NOW - 4000) * 1000),))
    con.commit(); con.close()
    st = collect(stale, derived, in_rth=True, is_index=True)
    check("W3b a genuinely dead RTH tape still degrades the rollup",
          rollup(st) == AMBER, f"rollup={rollup(st)}")

    # ── W4: OUTSIDE RTH THE WINDOWS SWAP ─────────────────────────────────────
    off = collect(feed, derived, in_rth=False, is_index=True)
    v = find(off, "candles", "VIX_EXT/1m")
    p = find(off, "candles", "SPX/1m")
    check("W4 outside RTH the EXT rows are judged and the RTH rows idle",
          v["bulb"] == AMBER and p["bulb"] == GREEN,
          f"VIX_EXT={v['bulb']} SPX={p['bulb']}")

    # ── W5: prints ON AN INDEX IS n/a, NOT RED ───────────────────────────────
    pr = find(rth, "streams", "prints (T&S)")
    check("W5 prints on a cash index renders ⚫ n/a", pr["bulb"] == NA,
          f"bulb={pr['bulb']} rows={pr['rows']}")

    eq = collect(feed, derived, in_rth=True, is_index=False)
    pr_eq = find(eq, "streams", "prints (T&S)")
    check("W5b on an EQUITY the same empty table is still RED",
          pr_eq["bulb"] == RED, f"bulb={pr_eq['bulb']}")

    withrows = os.path.join(d, "withprints.db")
    _build_feed(withrows, prints_rows=5)
    eq2 = collect(withrows, derived, in_rth=True, is_index=False)
    check("W5c an equity WITH prints is GREEN — the bulb still works",
          find(eq2, "streams", "prints (T&S)")["bulb"] == GREEN)

    # ── W6: underlying / theo ARE OFF THE BOARD (r125) ───────────────────────
    # ⚠️ THIS ASSERTION IS INVERTED FROM WHAT IT SAID BEFORE, and the reason is
    # evidence rather than taste. It used to hold that "did not arrive" must
    # not be laundered into "cannot exist" — right in principle, and it kept
    # two permanent reds on the board. UNDERLYING was then PROBED (2026-08-24,
    # tools/probe_aux_streams.py) with Trade/Greeks/Quote as live controls:
    # zero events on BOTH symbol spaces. THEO was proven reachable and then
    # deliberately unsubscribed in r118 after it took SPX's entire per-contract
    # subscription down with it. Operator: "I don't want underlying on the
    # manifold at all. You can also take off THEO. We tried it, it's not worth
    # the traffic burden with no readers."
    # A permanent red for a stream nobody reads teaches the operator to ignore
    # red, which is the only thing this board is for.
    labels = {s["label"] for s in rth["streams"]}
    check("W6 underlying and theo price are OFF the board",
          "underlying" not in labels and "theo price" not in labels,
          str(sorted(labels)))

    # ── W7: n/a NEVER PAINTS THE ROLLUP ──────────────────────────────────────
    check("W7 an n/a stream cannot degrade the rollup",
          rollup(rth) == GREEN and pr["bulb"] == NA)

    # ── W8 (r125): AFTER-HOURS ROWS NEVER PAINT THE ROLLUP, EITHER WAY ───────
    # Operator: "I don't want manifold health degraded for after-hours
    # sources." The prior rule excluded them during RTH only, so OUTSIDE RTH
    # they BECAME the rollup — and a VIX_EXT/1h that has not ticked since
    # yesterday is not a fault at 8pm any more than at 2pm; VIX simply does not
    # trade after hours the way QQQ does.
    for _rth in (True, False):
        rep = {"in_rth": _rth,
               "streams": [{"critical": True,  "bulb": GREEN, "after_hours": False},
                           {"critical": False, "bulb": AMBER, "after_hours": True}],
               "candles": [{"bulb": GREEN, "after_hours": False},
                           {"bulb": AMBER, "after_hours": True},
                           {"bulb": RED,   "after_hours": True}]}
        check(f"W8 a stale/dead after-hours row cannot degrade the rollup "
              f"(in_rth={_rth})", rollup(rep) == GREEN)
    # and a REAL failure still paints it
    check("W8c an RTH candle failure still turns the rollup RED",
          rollup({"in_rth": True, "streams": [],
                  "candles": [{"bulb": RED, "after_hours": False}]}) == RED)

    # ── W9 (r125): THE RTH CLOCK IS ASKED IN ET ─────────────────────────────
    # `datetime.now()` was the BOX's clock and the boxes run UTC, so this read
    # 18:12 at 14:12 ET and declared the session over mid-session. `_in_window`
    # INVERTS on that flag, so the after-hours rows counted as in-window and
    # painted the rollup AMBER — a clock error presented as a data fault.
    from datetime import datetime as _dt
    from utils.time_utils import ET as _ET
    from tools.manifold_health import _rth_now as _rn
    check("W9a 14:12 ET on a weekday is IN session",
          _rn(_dt(2026, 8, 25, 14, 12, tzinfo=_ET)) is True)
    check("W9b 20:12 ET is not", _rn(_dt(2026, 8, 25, 20, 12, tzinfo=_ET)) is False)
    check("W9c a Saturday is not", _rn(_dt(2026, 8, 29, 14, 12, tzinfo=_ET)) is False)

    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {', '.join(FAILURES)}")
        return 1
    print("check_manifold_windows: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
