#!/usr/bin/env python3
"""
tests/check_foreign_symbol_board.py  v1.1
v1.1  2026-10-20  OTV4TEST r307 (GATE.4) - F7 PINS ITS OWN PLAN STATES FILE. Since r303 the plans panel skips every plan
      data/plan_states.json names dormant, and F7 read the LIVE file (the bot writes it at start; VOLT is dormant in it),
      so its stale-VOLT control row vanished: RED at the 10-20 08:00 sweep on QQQ-TEST and SPX-TEST (STALE rows: []),
      green in every worktree, which has no such file. F7 now points OT_PLAN_STATES_FILE at an absent file in its own
      temp dir - the panel's no-states path, which judges every heartbeat - and restores the env after.
A SYMBOL THIS BOX NO LONGER FEEDS NEVER JUDGES IT, AND A CASH INDEX HAS NO TAPE WHOEVER ASKS (BOX.18).

v1.0  2026-10-05  OTV4TEST r252 - found on SPX-TEST, 10-05 09:37 ET, on the operator's own board
      (devtools item 6): AAL/15m..1d amber, prints (T&S) amber at age 231688s, ROLLUP amber in RTH;
      and the 09:35 open scan RED on feed:rollup. SPX-TEST was AAL until 10-03; its feed store
      still holds 11,675 AAL candles and 87,206 AAL prints (every print in the store is AAL), and
      its level book counted 68 live levels of which 48 were AAL's.

  F1  in RTH, a fresh box (SPX + VIX current, critical streams current) with STALE AAL candles
      rolls up GREEN - the AAL rows do not paint it
  F2  the AAL candles are still REPORTED (shown, not hidden), flagged foreign, bulb n/a
  F3  CONTROL: a stale SPX/1m on the same store still rolls the board up non-GREEN
  F4  collect() called with no is_index (open_scan's call; devtools sets no OT_INSTRUMENT)
      on an SPX box renders prints n/a
  F5  UNSET instrument judges every candle as before - AAL is NOT foreign, never a guess
  F6  the open scan counts THIS box's live levels only (20 SPX, not 68)
  F7  query.py's plans panel lists no AAL heartbeat as STALE on an SPX box, and still lists
      a genuinely stale SPX heartbeat (the control)

Fixtures are written through the REAL FeedStore / DerivedStore schemas; the board is the REAL
tools/manifold_health.collect/rollup and the REAL tools/open_scan.scan_ready.
"""
import os
import sys
import tempfile
import time
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def _feed(path, now, spx_age=5):
    from data.candle_feed import FeedStore
    fs = FeedStore(path)
    c = fs.conn
    ms = lambda age: int((now - age) * 1000)                      # noqa: E731
    rows = [("SPX", "1m", ms(spx_age)), ("VIX", "1m", ms(5)),
            ("SPX", "5m", ms(60)), ("VIX", "5m", ms(60)),
            ("AAL", "1m", ms(236275)), ("AAL", "5m", ms(236515)), ("AAL", "15m", ms(237115)),
            ("AAL_EXT", "1m", ms(219935))]
    for sym, iv, ts in rows:
        c.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,0)", (sym, iv, ts, 10, 11, 9, 10))
    c.execute("INSERT INTO greeks_series (streamer_symbol, ts_epoch) VALUES (?,?)", (".SPXW1", now - 5))
    c.execute("INSERT INTO quote_series (streamer_symbol, ts_epoch) VALUES (?,?)", (".SPXW1", now - 1))
    c.execute("INSERT INTO quote_series (streamer_symbol, ts_epoch) VALUES (?,?)", ("SPX", now - 1))
    c.execute("INSERT INTO chain_marks (streamer_symbol, updated_epoch) VALUES (?,?)", (".SPXW1", now - 1))
    c.commit()
    c.close()


def _derived(path, now):
    from data.derived_store import DerivedStore
    ds = DerivedStore(path)
    conn = getattr(ds, "conn", None) or getattr(ds, "_conn", None)
    import sqlite3
    conn = conn if conn is not None else sqlite3.connect(path)
    for i in range(48):
        conn.execute("INSERT INTO level_ledger (level_id, symbol, price, created_ts) VALUES (?,?,?,?)",
                     (f"aal{i}", "AAL", 12.0 + i, now - 300000))
    for i in range(20):
        conn.execute("INSERT INTO level_ledger (level_id, symbol, price, created_ts) VALUES (?,?,?,?)",
                     (f"spx{i}", "SPX", 7700.0 + i, now - 3600))
    conn.commit()


def main():
    os.environ["OT_BOT_UNIT"] = "no-such-unit-check-foreign"   # box_instrument never reads the real unit
    os.environ["OT_INSTRUMENT"] = "SPX"
    import tools.manifold_health as mh
    now = time.time()
    with tempfile.TemporaryDirectory() as d:
        feed, der = os.path.join(d, "feed_store.db"), os.path.join(d, "derived_store.db")
        _feed(feed, now)
        _derived(der, now)

        rep = mh.collect(feed, der, True, False)
        r = mh.rollup(rep)
        check("F1 stale AAL candles do not paint an SPX box's RTH rollup", r == mh.GREEN, f"rollup {r}")
        aal = [c for c in rep["candles"] if c["label"].startswith("AAL")]
        check("F2 the AAL candles are still reported, foreign, n/a",
              len(aal) == 4 and all(c.get("foreign") and c["bulb"] == mh.NA for c in aal),
              ", ".join(f"{c['label']}:{c['bulb']}:{c.get('foreign')}" for c in aal))

        feed2 = os.path.join(d, "feed2.db")
        _feed(feed2, now, spx_age=900)
        r2 = mh.rollup(mh.collect(feed2, der, True, False))
        check("F3 CONTROL: a stale SPX/1m still rolls the board up non-GREEN", r2 != mh.GREEN, f"rollup {r2}")

        rep4 = mh.collect(feed, der, True)
        pr = [s for s in rep4["streams"] if s["table"] == "prints"]
        check("F4 collect() with no is_index renders an SPX box's prints n/a",
              bool(pr) and pr[0]["bulb"] == mh.NA, f"prints {pr[0]['bulb'] if pr else 'missing'}")

        os.environ.pop("OT_INSTRUMENT", None)
        rep5 = mh.collect(feed, der, True, False)
        aal5 = [c for c in rep5["candles"] if c["label"].startswith("AAL")]
        check("F5 UNSET instrument: every candle judged as before (AAL not foreign)",
              bool(aal5) and not any(c.get("foreign") for c in aal5) and all(c["bulb"] != mh.NA for c in aal5),
              ", ".join(f"{c['label']}:{c['bulb']}" for c in aal5))
        os.environ["OT_INSTRUMENT"] = "SPX"

        import open_scan as OS
        s = OS.Scan()
        OS.scan_ready(s, feed, der, dt.datetime.now(OS.ET) if hasattr(OS, "ET") else dt.datetime.now())
        lv = [f["text"] for f in s.f if f["sig"].startswith("levels")]
        check("F6 the open scan counts this box's live levels only (20 SPX, not 68)",
              bool(lv) and lv[0].startswith("level book: 20 live"), lv[0] if lv else "no levels line")

    # F7 - the REAL query.show_decisions over a plan_heartbeat built by the REAL schema owner
    import io, contextlib
    with tempfile.TemporaryDirectory() as d2:
        from data.derived_store import DerivedStore
        from strategy.plan import ensure_tables
        ds = DerivedStore(os.path.join(d2, "derived_store.db"))
        ensure_tables(ds)
        import query as Q
        Q.INSTRUMENT = "SPX"
        _pin = dt.datetime.now(Q.ET).replace(hour=11, minute=5, second=0, microsecond=0)
        Q.now_et = lambda: _pin            # in session, whatever the wall clock says
        t_now = _pin.timestamp()           # ages are measured against the PINNED clock
        for sym, plan, age in (("AAL", "LiquidityHunt", 132000), ("AAL", "Breakout", 132000),
                               ("SPX", "LiquidityHunt", 5), ("SPX", "VOLT", 900)):
            ds.conn.execute("INSERT INTO plan_heartbeat (symbol, plan, ts_epoch, tick_id, state)"
                            " VALUES (?,?,?,?,?)", (sym, plan, t_now - age, 6, "IDLE"))
        ds.conn.commit()
        buf = io.StringIO()
        _prev_ps = os.environ.get("OT_PLAN_STATES_FILE")
        os.environ["OT_PLAN_STATES_FILE"] = os.path.join(d2, "no_plan_states.json")   # r307: never the live file
        try:
            with contextlib.redirect_stdout(buf):
                Q.show_decisions(ds.conn)
        finally:
            if _prev_ps is None:
                os.environ.pop("OT_PLAN_STATES_FILE", None)
            else:
                os.environ["OT_PLAN_STATES_FILE"] = _prev_ps
        out = buf.getvalue()
        stale = [ln.split()[1] for ln in out.splitlines() if "STALE" in ln and ln.strip().startswith("!!")]
        check("F7 the plans panel lists no AAL heartbeat as STALE; the stale SPX one still shows",
              "VOLT" in stale and not ({"Breakout"} & set(stale)) and stale.count("LiquidityHunt") == 0,
              f"STALE rows: {stale}")

    print(("RED - " + f"{len(FAILED)} of {len(RAN)} failed: " + " ".join(FAILED)) if FAILED
          else f"GREEN - {len(RAN)} of {len(RAN)} passed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
