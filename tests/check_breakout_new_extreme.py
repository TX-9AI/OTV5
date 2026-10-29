#!/usr/bin/env python3
"""
tests/check_breakout_new_extreme.py  v5.2
v5.2  2026-10-29  OTV5 r54 (BRK.16) — TWO FIXTURE/RULE UPDATES FOR THE OPERATOR'S 2026-10-29 SPEC, NO RE-FIRE PROPERTY CHANGED.
      (1) _tick's opening range is WIDER on the far side only (TST 101.00/95.00, TSS 106.00/99.00; the edge each test
      breaks is unchanged): N3, N4c, N9b and N10b re-fire on closes 0.6-1.7 points past the edge, which on the old 1.00
      wide range is past 1/2 W - now refused outright ("It should honestly refuse if it's already crossed 1/2W"), so
      the re-fire rule would never be reached. Every N assertion is as before. (2) N12a-c: Breakout no longer reads the
      level board ("purely directional without regard for levels in its path"), so an unreadable board can no longer
      refuse it: N12a board_for is never asked and range_clean / room_to_run are not conditions (no warning); N12b the
      break still fires; N12c with numbered dials neither is unmet (was: both refused).
v5.1  2026-10-26  OTV5 r38 (HYG.18) — scratch no longer names dir="/var/tmp": mkdtemp honours TMPDIR, which boot_sweep and land.sh point
      at a per-run dir they remove (HYG.14), so a sweep leaves nothing behind (237 dirs had piled up on SOFI). No check changed.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.7  2026-10-24  OTV4TEST r316 (BRK.15) — RE-POINTED, NOT DROPPED (section 38.4): r131 is no longer the default. The
      operator, 2026-10-24 13:45 ET: "The new session high/low rule needs to be dropped"; OT_BRK_REFIRE=extreme is the
      rollback that restores it, so this checker sets that for its own process and still pins every N property of
      the rule the rollback must restore. The default re-arm rule is tests/check_breakout_rearm.py. No check changed.
v1.6  2026-10-18  OTV4TEST r299 (BRK.14) — N12a-c: an unreadable level board reads None on range_clean / room_to_run
      (not "0 inside" / "open air"), is said once, still fires inside the research window, and REFUSES both once the
      dials carry numbers (audit 10-18 D3). N12a and N12c RED on 42906b9.
v1.5  2026-10-15  BRK.12 (RECORD-ONLY) — N11a-g: a return to the range re-arms the side ONCE, and is RECORDED, never
      traded (the operator, 2026-10-14 11:38 ET: "I want a return of the range to enable another breakout in either
      direction"; 2026-10-15 10:16 ET: "Concur on all", to "record-only"). N11a/b/d: no order, one row per side per
      signal bar; N11c: one re-arm per side; N11e: off records nothing; N11f: log and off decide identically on
      every bar (no order is placed by the re-arm); N11g: there is no trade value. Rows go to a SCRATCH
      OT_COUNTERFACTUAL_DIR, never the live one.
v1.4  2026-10-13  OTV4TEST r282 (BRK.10) — N10a-c: the FIRST entry is the tape's first break, not the book's first
      fill. N10d pins that a close inside the 09:30-09:34 window never counts as the break. N10a (a stale break with no fill is refused under the session high) and N10c (an unreadable tape
      fails closed on a first entry) are RED on d1fc9ab; N10b pins that a real new high still fires. N4a RE-POINTED,
      NOT DROPPED (section 38.4): the mirrored short's first break is 09:35, so the per-side property is asked there.
v1.3  2026-10-02  OTV4TEST r187 (ROSTER.1) — RE-POINTED BY THE RULING: Breakout's
      window now ends 10:30 (the operator, 2026-10-02: "let's impose a 1029
      debit cutoff rule"), and this fixture's re-fires sit at 10:49-11:01. This
      checker tests the RE-FIRE gate, not the window, so it sets the plan's
      B.LATEST_ET back to "15:40" for its own process (the plan reads it at call
      time); check_trade_switches S8 pins the real 10:30. No check changed.
v1.2  2026-10-02  OTV4TEST r186 (ZBID.1) — the _C
      fixture contract now carries a TWO-SIDED quote (bid/ask around its
      mark), as every live OptionContract does: r186 (ZBID.1) refuses a
      contract with no bid, and this fixture had none. No check changed.
v1.1  2026-09-25  OTV4TEST r142 — N9: A RE-FIRE ON THE SAME SIGNAL BAR IS REFUSED. Live,
      2026-09-25: a long fired at 09:36:16 on the 09:35 close; at 09:36:51 the
      09:35 bar was still the last closed bar and the re-fire PASSED this gate on
      the same close (-$1,250). N1-N8 never caught it: every re-fire they asked
      was on a LATER bar. ⚠️ THE FIXTURE'S CLOCK IS FIXED WITH IT: `_log` stamped
      entries at the REAL time, which the new "signal bar closed after the last
      entry" rule reads, so a run in the afternoon would refuse every re-fire and
      one at 08:00 would pass them - entries now carry the synthetic minute they
      fired at. N4b moves from minute 30 to 31: at 30 it re-asked the SAME bar the
      short had just fired on, which is now N9c's property; at 31 it still tests
      "not below the session low", and asserts the same 97.50.
A BREAKOUT RE-FIRE ON A SIDE NEEDS A NEW SESSION EXTREME (r131).

v1.0  2026-09-24  OTV4TEST r131 — born red at r130 (b1b6594): the plan has no
      re-fire gate there, so the second long fires on a close that is still
      beyond the edge and nowhere near a new high.

THE OPERATOR'S RULING, 2026-09-24, verbatim: *"A new reclaimed level has to
happen before it can fire again? A new high for a long, a new low for a
short."* The first entry per side per session keeps the break trigger (the
last closed 1m bar's CLOSE beyond the range edge). Every LATER entry on that
side needs that close strictly above the highest HIGH (long) / below the
lowest LOW (short) of every prior RTH bar since 09:30. Closes are acceptance;
no tolerance.

EVERYTHING HERE DRIVES THE REAL PLAN. `BreakoutPlan.prepare` on synthetic
bars written to a scratch feed store, with "already fired" coming from a
scratch trades.db whose rows go in through the repo's own `TradeLogger`.
Only the order-flow READER is stubbed to a passing value (it reads live
prints "as of now"); the research acceptance is pinned open so the informers
cannot decide a tick this file is not about.

  N1  the first break on a side fires exactly as before
  N2  a second long, close beyond the edge but not above the session high,
      is refused under the gate "new_extreme" (and a close EQUAL to the
      session high is refused too — strictly beyond)
  N3  a close above the session high is allowed
  N4  the short side mirrors it, and a long already fired does not block the
      first short
  N5  a restart (a fresh interpreter) still knows the side fired — trades.db
  N6  a 60-bar df_1m that no longer reaches the session high does not shrink it
  N7  breakout.GATES declares NEW_EXTREME FOUNDATIONAL, and it is the name refused
  N8  an unreadable book or tape, or a tape that does not reach 09:30, FAILS
      CLOSED under the same named gate
"""
import os
import sys
import shutil
import sqlite3
import subprocess
import tempfile

import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path: sys.path.insert(1, _sp)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# the N5 child re-enters this file in a fresh interpreter and must use the
# PARENT's scratch stores — that is the whole point of the restart check
SCRATCH = (os.environ["N5_SCRATCH"] if os.environ.get("N5_RESTART") == "1"
           else tempfile.mkdtemp(prefix="chk_brk_ne_"))
os.environ["OT_TRADES_DB"] = os.path.join(SCRATCH, "trades.db")
os.environ["OT_DERIVED_DB"] = os.path.join(SCRATCH, "derived.db")
os.environ["OT_RESTING_DB"] = os.path.join(SCRATCH, "resting.db")
os.environ["OT_FEED_DB"] = os.path.join(SCRATCH, "feed.db")
os.environ["OT_BRK_RESEARCH_UNTIL"] = "2099-12-31"      # informers: accept any
os.environ["OT_COUNTERFACTUAL_DIR"] = os.path.join(SCRATCH, "cf")   # BRK.12: never the LIVE data/counterfactual
os.environ["OT_BRK_REFIRE"] = "extreme"                 # r316: the rollback is what this file pins (and its N5 child)
FAILED, RAN = [], []
ET = "America/New_York"


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn):
    try:
        ok, det = fn()
    except Exception as exc:                                    # noqa: BLE001
        ok, det = False, f"{type(exc).__name__}: {exc}"
    check(name, bool(ok), det)


# ── the synthetic session. Range 100.00-101.00 (long) on TST; TSS mirrors it
#    about 200 (range 99.00-100.00, short). One bar per minute from 09:30.
def _long_session():
    bars = {}
    for m in range(0, 5):                                  # 09:30-09:34 the range
        bars[m] = (100.5, 101.00, 100.00, 100.5)
    for m in range(5, 101):                                # 09:35-11:10 filler
        bars[m] = (101.5, 101.80, 101.30, 101.6)
    bars[5] = (100.6, 101.40, 100.55, 101.30)              # 09:35 FIRST BREAK close
    bars[10] = (101.6, 102.50, 101.50, 101.9)              # 09:40 SESSION HIGH 102.50
    bars[15] = (102.0, 102.50, 101.90, 102.50)             # 09:45 close EQUAL to it
    bars[29] = (101.5, 101.85, 101.40, 101.60)             # 09:59 beyond edge, no new high
    bars[79] = (101.7, 102.05, 101.60, 102.00)             # 10:49 above the 60-bar frame, not the session
    bars[90] = (102.0, 102.80, 101.95, 102.70)             # 11:00 NEW HIGH close
    return bars


def _mirror(bars):
    return {m: (200 - o, 200 - l, 200 - h, 200 - c) for m, (o, h, l, c) in bars.items()}


def _write_feed(day):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    c = sqlite3.connect(os.environ["OT_FEED_DB"])
    c.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, "
              "ts_epoch_ms INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL, "
              "volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    o = int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET)).timestamp() * 1000)
    gap = {m: b for m, b in _long_session().items() if m != 0}     # no 09:30 bar
    tsw = dict(_long_session())                                     # r282: an in-window close beyond the edge
    tsw[2] = (100.6, 101.30, 100.50, 101.20)                       # 09:32 closes 101.20 > 101.00 INSIDE the range
    tsw[5] = (100.6, 100.95, 100.40, 100.80)                       # 09:35 no break
    tsw[6] = (100.8, 101.40, 100.70, 101.30)                       # 09:36 the FIRST break after the range
    tsr = dict(_long_session())                                     # BRK.12: a return to the range
    tsr[11] = (101.8, 101.85, 100.50, 100.60)                      # 09:41 closes BACK INSIDE (100.60 <= 101.00)
    tsr[12] = (100.6, 100.90, 100.50, 100.70)                      # 09:42 inside
    tsr[13] = (100.7, 101.50, 100.65, 101.40)                      # 09:43 RE-BREAK 101.40 < session high 102.50
    tsr[14] = (101.4, 101.45, 100.40, 100.50)                      # 09:44 back inside again
    tsr[15] = (100.5, 101.35, 100.45, 101.30)                      # 09:45 a SECOND re-break, under the high
    for sym, bars in (("TST", _long_session()), ("TSS", _mirror(_long_session())),
                      ("TSG", gap), ("TSW", tsw), ("TSR", tsr), ("TSRS", _mirror(tsr))):
        for m, (op, h, l, cl) in bars.items():
            c.execute("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)",
                      (sym, "1m", o + m * 60_000, op, h, l, cl, 1000.0))
    c.commit()
    c.close()


def _frame(sym, day, minute, keep=60):
    """The frame main.py hands over: bars up to and INCLUDING the forming one
    (at `minute`), the last `keep` of them, tz-aware ET like fetch_candles."""
    import pandas as pd
    from datetime import datetime
    from zoneinfo import ZoneInfo
    o = int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET)).timestamp() * 1000)
    c = sqlite3.connect(f"file:{os.environ['OT_FEED_DB']}?mode=ro", uri=True)
    rows = c.execute("SELECT ts_epoch_ms, open, high, low, close, volume FROM candles "
                     "WHERE symbol=? AND interval='1m' AND ts_epoch_ms <= ? ORDER BY ts_epoch_ms",
                     (sym, o + minute * 60_000)).fetchall()
    c.close()
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.pop("ts"), unit="ms", utc=True).dt.tz_convert(ET)
    return df.iloc[-keep:]


class _ORB:
    def __init__(self, hi, lo):
        self.orb_high, self.orb_low = hi, lo


class _C:
    def __init__(self, k):
        self.strike, self.mark, self.delta, self.gamma, self.expiry, self.ask = k, 1.0, 0.5, 0.05, "", 1.05
        self.bid = 0.95                                      # r186: two-sided


class _Chain:
    def __init__(self, px):
        ks = [round(px) + i for i in range(-6, 7)]
        self.calls, self.puts = [_C(k) for k in ks], [_C(k) for k in ks]


def _hm(minute):
    return f"{9 + (30 + minute) // 60:02d}:{(30 + minute) % 60:02d}"


def _tick(plan, spec, sym, day, minute, keep=60):
    """Ask the plan at the START of `minute`: the last closed bar is minute-1."""
    df = _frame(sym, day, minute, keep)
    px = float(df.iloc[-1]["open"])
    # r54 (BRK.16): the FAR side is wide so the re-fire closes stay inside 1/2 W of the edge each test breaks
    hi, lo = (106.00, 99.00) if sym in ("TSS", "TSRS") else (101.00, 95.00)
    prep = plan.prepare(spec=spec, orb=_ORB(hi, lo), price_now=px, now_et=_hm(minute),
                        chain=_Chain(px), df_1m=df, flow_conn=None, symbol=sym)
    return prep, df


def _refused_at_gate(prep):
    t = prep.tick
    return (not prep.ready and t.verdict == "DECLINE"
            and t.plan.last()[2].startswith("new_extreme:")
            and (t.checks.get("new_extreme") or (None, None))[1] is False)


def _why(prep):
    t = prep.tick
    return (f"ready={prep.ready} verdict={t.verdict or prep.verdict} "
            f"why={(t.plan.last()[2] if t.closed else '-')[:90]!r} "
            f"sess={(t.checks.get('session_extreme') or (None,))[0]}")


def _log(side, minute, day):
    """An entry filled 16s into `minute` (09:30 + minute) of `day` — on the
    fixture's clock, because the r142 rule reads the entry TIME."""
    import uuid
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from database.trade_logger import get_trade_logger, make_record
    tid = str(uuid.uuid4())
    tl = get_trade_logger()
    tl.log_entry(make_record(
        trade_id=tid, symbol="TST", strategy="Breakout",
        setup_type=f"breakout_{'long' if side == 'call' else 'short'}",
        direction=("long" if side == "call" else "short"), option_side=side,
        orb_range_high=101.0, orb_range_low=100.0, paper_trade=1))
    at = (datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET))
          + timedelta(minutes=minute, seconds=16)).astimezone(ZoneInfo("UTC")).isoformat()
    conn = tl._connect()
    try:
        conn.execute("UPDATE trades SET entry_time=? WHERE trade_id=?", (at, tid))
        conn.commit()
    finally:
        conn.close()




def main():
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        globals().update(ZoneInfo=ZoneInfo, datetime=datetime)
        day = datetime.now(ZoneInfo(ET)).date()
        _write_feed(day)
        from database.trade_logger import get_trade_logger
        get_trade_logger()                                   # the repo's schema
        from strategy.breakout import Breakout
        import strategy.breakout as B
        B.LATEST_ET = "15:40"                                # r187: re-fire logic, not the window (S8 pins 10:30)
        from strategy.breakout_plan import BreakoutPlan
        import config as config_mod
        globals()["config_mod"] = config_mod
        BreakoutPlan._flow = staticmethod(lambda conn, symbol: (0.2, 1.0))
        spec = Breakout()
        plan = spec._plan_()
    except Exception as exc:                                    # noqa: BLE001
        for n in ("N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9"):
            check(f"{n} setup", False, f"{type(exc).__name__}: {exc}")
        return _tail()

    # ── N1 — the FIRST long: nothing in the book, the break close decides ──
    p1, _ = _tick(plan, spec, "TST", day, 6)                 # signal 09:35 close 101.30
    guard("N1 the first break on a side fires exactly as before (no book row, close beyond the edge)",
          lambda: (p1.ready and p1.direction == "long"
                   and "session_extreme" not in p1.tick.checks, _why(p1)))

    # ── N10 (r282, BRK.10) — NOTHING FILLED, BUT THE BREAK ALREADY HAPPENED ──
    # The 09:35 long break was refused (no fill). At 09:59 a close beyond the
    # edge but under the 09:40 session high is NOT a first break: refused.
    p10a, _ = _tick(plan, spec, "TST", day, 30)              # signal 09:59 close 101.60 < 102.50
    guard("N10a no fill, but the break first closed at 09:35: a 09:59 close under the session high is refused",
          lambda: (_refused_at_gate(p10a) and "first_break" in p10a.tick.checks
                   and abs(float(p10a.tick.checks["session_extreme"][0]) - 102.50) < 1e-9, _why(p10a)))
    p10b, _ = _tick(plan, spec, "TST", day, 91)              # signal 11:00 close 102.70 > 102.50
    guard("N10b no fill, stale break: a close ABOVE the session high still fires",
          lambda: (p10b.ready and p10b.direction == "long", _why(p10b)))
    p10d, _ = _tick(plan, spec, "TSW", day, 7)               # signal 09:36: the first break after 09:35
    guard("N10d a close beyond the edge INSIDE the 09:30-09:34 range window does not make the first break stale",
          lambda: (p10d.ready and p10d.direction == "long" and "first_break" not in p10d.tick.checks, _why(p10d)))
    _feed10 = os.environ["OT_FEED_DB"]
    os.environ["OT_FEED_DB"] = os.path.join(SCRATCH, "absent", "feed.db")
    try:
        p10c = plan.prepare(spec=spec, orb=_ORB(101.0, 100.0), price_now=101.5, now_et="09:36",
                            chain=_Chain(101.5), df_1m=_frame_from(_feed10, "TST", day, 6),
                            flow_conn=None, symbol="TST")
    finally:
        os.environ["OT_FEED_DB"] = _feed10
    guard("N10c no fill and an unreadable feed store: the first break FAILS CLOSED at 'new_extreme'",
          lambda: (not p10c.ready and p10c.tick.verdict == "DECLINE"
                   and p10c.tick.plan.last()[2].startswith("new_extreme:"), _why(p10c)))

    # ── N11 (BRK.12) — A RETURN TO THE RANGE RE-ARMS THE SIDE ONCE: RECORDED, NEVER TRADED ──
    # The operator, 2026-10-14 11:38 ET: "I want a return of the range to enable another breakout in either
    # direction" ("Breakout only", "One re-arm per side"); 2026-10-15 10:16 ET: "Concur on all" (to
    # "BRK.12 / HUNT.9: record-only"). TSR: first break 09:35 (refused, no fill), session high 102.50 at
    # 09:40, 09:41 closes back inside, 09:43 re-breaks at 101.40 under the high.
    import json as _json
    import strategy.breakout_plan as BP
    _cf = os.path.join(os.environ["OT_COUNTERFACTUAL_DIR"], "breakout_rearm.jsonl")

    def _rows(sym=None):
        try:
            with open(_cf) as fh:
                rr = [_json.loads(x) for x in fh if x.strip()]
        except FileNotFoundError:
            return []
        return [r for r in rr if sym is None or r.get("symbol") == sym]

    p11a, _ = _tick(plan, spec, "TSR", day, 14)               # signal 09:43 close 101.40 < 102.50
    r11a = _rows("TSR")
    guard("N11a a return to the range then a re-break under the high: NO ORDER (refused at 'new_extreme') "
          "and ONE breakout_rearm row (long, returned 09:41, new_extreme_ok False)",
          lambda: (_refused_at_gate(p11a) and len(r11a) == 1 and r11a[0]["direction"] == "long"
                   and r11a[0]["new_extreme_ok"] is False and r11a[0]["mode"] == "log"
                   and abs(r11a[0]["break_close"] - 101.40) < 1e-9
                   and _hm(11) == datetime.fromtimestamp(r11a[0]["return_ms"] / 1000, ZoneInfo(ET)).strftime("%H:%M"),
                   f"rows={r11a} {_why(p11a)}"))
    _tick(plan, spec, "TSR", day, 14)                         # the next 15 s tick: the SAME signal bar
    guard("N11b the same signal bar asked again writes no second row (one per side per signal bar)",
          lambda: (len(_rows("TSR")) == 1, f"rows={len(_rows('TSR'))}"))
    p11c, _ = _tick(plan, spec, "TSR", day, 16)               # signal 09:45: a SECOND return + re-break
    guard("N11c ONE re-arm per side: a second return and re-break writes no row, and is refused as before",
          lambda: (_refused_at_gate(p11c) and len(_rows("TSR")) == 1, f"rows={len(_rows('TSR'))} {_why(p11c)}"))
    p11d, _ = _tick(plan, spec, "TSRS", day, 14)              # the mirrored short, signal 09:43
    r11d = _rows("TSRS")
    guard("N11d the short side mirrors it (either direction): no order, one short row",
          lambda: (_refused_at_gate(p11d) and len(r11d) == 1 and r11d[0]["direction"] == "short",
                   f"rows={r11d} {_why(p11d)}"))
    _saved_mode = getattr(config_mod, "BRK_REARM_MODE", "log")
    config_mod.BRK_REARM_MODE = "off"
    getattr(BP, "_REARM_SAID", set()).clear()
    try:
        p11e, _ = _tick(plan, spec, "TSRS", day, 14)
    finally:
        config_mod.BRK_REARM_MODE = _saved_mode
    guard("N11e OT_BRK_REARM=off: not evaluated, no row, the same refusal",
          lambda: (_refused_at_gate(p11e) and len(_rows("TSRS")) == 1 and "range_rearm" not in p11e.tick.checks,
                   f"rows={len(_rows('TSRS'))} {_why(p11e)}"))
    # NO DECISION CHANGES: every minute of the re-arm fixture, log vs off, gives the same ready/verdict.
    _diff = []
    for _sym in ("TSR", "TSRS"):
        for _m in range(6, 21):
            getattr(BP, "_REARM_SAID", set()).clear(); config_mod.BRK_REARM_MODE = "log"
            _a, _ = _tick(plan, spec, _sym, day, _m)
            config_mod.BRK_REARM_MODE = "off"
            _b, _ = _tick(plan, spec, _sym, day, _m)
            config_mod.BRK_REARM_MODE = _saved_mode
            if (_a.ready, _a.tick.verdict) != (_b.ready, _b.tick.verdict):
                _diff.append((_sym, _hm(_m - 1), _a.ready, _b.ready))
    guard("N11f RECORD-ONLY: log and off reach the same decision on every bar 09:35-09:49 (both sides)",
          lambda: (not _diff, f"differs={_diff}"))
    _env = dict(os.environ, OT_BRK_REARM="trade")
    _o = subprocess.run([sys.executable, "-c", "import config;print(config.BRK_REARM_MODE, config.BRK_REARM_ENV_REFUSED)"],
                        cwd=ROOT, env=_env, capture_output=True, text=True, timeout=120)
    guard("N11g there is no trade value: OT_BRK_REARM=trade reads as log and is named",
          lambda: (_o.stdout.split()[-2:] == ["log", "trade"], (_o.stdout + _o.stderr)[-160:]))

    # ── N9 — the long filled at 09:36:16; the 09:35 bar is STILL the last closed
    # bar for the rest of that minute (2026-09-25, 09:36:51, -$1,250) ────────────
    _log("call", 6, day)
    p9, _ = _tick(plan, spec, "TST", day, 6)                 # signal 09:35 AGAIN
    guard("N9 a re-fire on the SAME signal bar that fired the last entry is refused",
          lambda: (_refused_at_gate(p9) and "no bar has closed since" in p9.tick.plan.last()[2],
                   _why(p9)))
    p9b, _ = _tick(plan, spec, "TST", day, 7)                # signal 09:36: close 101.60 > 09:35's 101.40
    guard("N9b the NEXT bar re-fires when it really makes a new high — the side is not locked",
          lambda: (p9b.ready and p9b.direction == "long"
                   and abs(float(p9b.tick.checks["session_extreme"][0]) - 101.40) < 1e-9, _why(p9b)))

    # ── N2 — one long in the book; a close beyond the edge, no new high ─────
    p2, _ = _tick(plan, spec, "TST", day, 30)                # signal 09:59 close 101.60 < 102.50
    guard("N2 a second long beyond the edge but NOT above the session high is refused at 'new_extreme'",
          lambda: (_refused_at_gate(p2)
                   and abs(float(p2.tick.checks["session_extreme"][0]) - 102.50) < 1e-9, _why(p2)))
    p2b, _ = _tick(plan, spec, "TST", day, 16)               # signal 09:45 close == 102.50
    guard("N2b a close EQUAL to the session high is refused — strictly above, no tolerance",
          lambda: (_refused_at_gate(p2b), _why(p2b)))

    # ── N3 — a close above the session high is allowed ───────────────────
    p3, _ = _tick(plan, spec, "TST", day, 91)                # signal 11:00 close 102.70 > 102.50
    guard("N3 a close ABOVE the session high re-fires",
          lambda: (p3.ready and p3.direction == "long"
                   and (p3.tick.checks.get("new_extreme") or (None, None))[1] is True, _why(p3)))

    # ── N4 — the short side mirrors it ────────────────────────────────────
    # the first short is taken at 09:59 — below the edge, NOT below the 09:40
    # session low — so only a per-SIDE count lets it through: a long in the
    # book must not make the first short need a new extreme.
    # r282 RE-POINTED, NOT DROPPED: the mirrored session's short break first closes at 09:35 (98.70), so 09:59
    # is a STALE short break (N10's rule); the per-side property is asked on the TRUE first short, signal 09:35.
    p4a, _ = _tick(plan, spec, "TSS", day, 6)                # 98.70 below the 99.00 edge: the first short break
    guard("N4a the first SHORT fires on the break close although a long already fired — the latch is per side",
          lambda: (p4a.ready and p4a.direction == "short"
                   and "session_extreme" not in p4a.tick.checks, _why(p4a)))
    _log("put", 30, day)
    p9c, _ = _tick(plan, spec, "TSS", day, 30)               # the SAME 09:59 bar the short fired on
    guard("N9c the short side: the same signal bar cannot re-fire either",
          lambda: (_refused_at_gate(p9c) and "no bar has closed since" in p9c.tick.plan.last()[2],
                   _why(p9c)))
    p4b, _ = _tick(plan, spec, "TSS", day, 31)               # 10:00 bar: 98.40 not below 97.50
    guard("N4b a second short below the edge but NOT below the session low is refused",
          lambda: (_refused_at_gate(p4b)
                   and abs(float(p4b.tick.checks["session_extreme"][0]) - 97.50) < 1e-9, _why(p4b)))
    p4c, _ = _tick(plan, spec, "TSS", day, 91)               # 97.30 below 97.50
    guard("N4c a close BELOW the session low re-fires the short",
          lambda: (p4c.ready and p4c.direction == "short", _why(p4c)))

    # ── N5 — a restart: a FRESH interpreter, a fresh plan, the same book ───
    def restart():
        env = dict(os.environ, N5_RESTART="1", N5_SCRATCH=SCRATCH)
        out = subprocess.run([sys.executable, os.path.abspath(__file__)], env=env, capture_output=True,
                             text=True, timeout=120)
        line = [l for l in out.stdout.splitlines() if l.startswith("N5RESULT")]
        return (bool(line) and line[-1].split()[1] == "REFUSED",
                (line[-1] if line else (out.stderr.strip().splitlines() or ["no output"])[-1])[:160])
    guard("N5 a restart still knows the long fired — read from trades.db, not memory", restart)

    # ── N6 — the 60-bar frame lost the 09:40 high; the session did not ────
    p6, df6 = _tick(plan, spec, "TST", day, 80, keep=60)     # signal 10:49 close 102.00
    frame_hi = float(df6.iloc[:-2]["high"].max())
    guard("N6 a truncated df_1m does not shrink the session high (09:40's 102.50 still binds)",
          lambda: (frame_hi < 102.00 and df6.index[0].strftime("%H:%M") > "09:40"
                   and _refused_at_gate(p6),
                   f"frame {df6.index[0].strftime('%H:%M')}-{df6.index[-1].strftime('%H:%M')} "
                   f"high {frame_hi:.2f}; " + _why(p6)))

    # ── N7 — declared FOUNDATIONAL, and it is the name refused under ──────
    guard("N7 breakout.GATES declares NEW_EXTREME FOUNDATIONAL and the plan refuses under that name",
          lambda: (B.GATES.get("NEW_EXTREME") == "FOUNDATIONAL"
                   and getattr(B, "NEW_EXTREME", None) == "new_extreme"
                   and "new_extreme" in Breakout.PLAN_CHECKS,
                   f"GATES={B.GATES.get('NEW_EXTREME')} NEW_EXTREME={getattr(B, 'NEW_EXTREME', None)}"))

    # ── N8 — fail closed: an unreadable tape, then an unreadable book ─────
    feed = os.environ["OT_FEED_DB"]
    os.environ["OT_FEED_DB"] = os.path.join(SCRATCH, "absent", "feed.db")
    try:
        p8 = plan.prepare(spec=spec, orb=_ORB(101.0, 100.0), price_now=102.0, now_et="11:01",
                          chain=_Chain(102.0), df_1m=_frame_from(feed, "TST", day, 91),
                          flow_conn=None, symbol="TST")
    finally:
        os.environ["OT_FEED_DB"] = feed
    guard("N8a an unreadable feed store refuses a re-fire at 'new_extreme', never passes it",
          lambda: (_refused_at_gate(p8) or (not p8.ready and p8.tick.verdict == "DECLINE"
                                            and p8.tick.plan.last()[2].startswith("new_extreme:")),
                   _why(p8)))
    p8c, _ = _tick(plan, spec, "TSG", day, 91)               # would pass on a whole tape
    guard("N8c a session tape that does not reach 09:30 refuses a re-fire — the high may be missing",
          lambda: (_refused_at_gate(p8c) and "09:30" in p8c.tick.plan.last()[2], _why(p8c)))
    import database.trade_logger as TL
    saved = TL._trade_logger
    class _Broken:
        _mode_flag = 1
        def _connect(self):
            raise sqlite3.OperationalError("disk I/O error")
    TL._trade_logger = _Broken()
    try:
        p8b, _ = _tick(plan, spec, "TST", day, 6)
    finally:
        TL._trade_logger = saved
    guard("N8b an unreadable trades.db refuses at 'new_extreme' — it cannot know the side is fresh",
          lambda: (not p8b.ready and p8b.tick.verdict == "DECLINE"
                   and p8b.tick.plan.last()[2].startswith("new_extreme:"), _why(p8b)))
    # (last on purpose: its second long entry would change what every later
    # minute-91 re-ask is testing)
    # N9d — freshness is judged against the LATEST entry, not the first: a second
    # long fills at 11:01:16 on the 11:00 new-high close; asked again on that same
    # bar it must refuse, although the 09:36 entry is long gone.
    _log("call", 91, day)
    p9d, _ = _tick(plan, spec, "TST", day, 91)
    guard("N9d the LATEST same-side entry sets the fresh-bar bound, not the first",
          lambda: (_refused_at_gate(p9d) and "no bar has closed since" in p9d.tick.plan.last()[2]
                   and "11:01:16" in p9d.tick.plan.last()[2], _why(p9d)))

    # ── N12 (r299, BRK.14) — AN UNREADABLE LEVEL BOARD IS NOT A CLEAN RANGE ──
    # derived.levels.board_for raises; the plan's range_clean / room_to_run must read None (not "0 inside" /
    # "open air"), say so once, still fire inside the research window ("any" admits an absent reading by the
    # operator's ruling), and REFUSE on both once the dials carry numbers.
    import logging as _lg
    import derived.levels as _LV
    _warn = []

    class _H(_lg.Handler):
        def emit(self, r):
            if r.levelno >= _lg.WARNING and "level board" in r.getMessage():
                _warn.append(r.getMessage())
    _h = _H(); _lg.getLogger("strategy.breakout_plan").addHandler(_h)
    _orig_bf = _LV.board_for
    _asked = []

    def _boom(*a, **k):
        _asked.append(1)
        raise RuntimeError("derived store locked (fixture)")
    _LV.board_for = _boom
    _saved_ru = B.RESEARCH_UNTIL
    with sqlite3.connect(os.environ["OT_TRADES_DB"]) as _c12:   # N9's logged entries would refuse any first break
        _c12.execute("DELETE FROM trades")
    try:
        plan12 = spec._plan_()
        p12, _ = _tick(plan12, spec, "TSW", day, 7)          # a first long break (TST carries N9's logged entries), board unreadable
        rc12 = p12.conditions.get("range_clean") or (0.0, None, None)
        rr12 = p12.conditions.get("room_to_run") or (0.0, None, None)
        # r54 (BRK.16): Breakout reads no board - it is never asked, and neither bar is a condition any more
        guard("N12a an unreadable board is never asked: range_clean / room_to_run are not conditions, no warning",
              lambda: ("range_clean" not in p12.conditions and "room_to_run" not in p12.conditions
                       and not _asked and len(_warn) == 0,
                       f"range_clean={rc12} room_to_run={rr12} board asked={len(_asked)} warnings={len(_warn)}"))
        guard("N12b inside the research window the break still fires (no decision change before the dials get numbers)",
              lambda: (p12.ready and p12.direction == "long", _why(p12)))
        B.RESEARCH_UNTIL = "2026-01-01"                      # the dials carry numbers now
        plan12c = spec._plan_()
        p12c, _ = _tick(plan12c, spec, "TSR", day, 6)        # another first break, on a symbol with no logged entry
        rc12c = p12c.conditions.get("range_clean") or (0.0, None, True)
        rr12c = p12c.conditions.get("room_to_run") or (0.0, None, True)
        guard("N12c with numbered dials an unreadable board refuses NOTHING: neither bar is unmet (r54, BRK.16)",
              lambda: ("range_clean" not in p12c.unmet and "room_to_run" not in p12c.unmet
                       and not _asked and len(_warn) == 0,
                       f"range_clean={rc12c} room_to_run={rr12c} unmet={p12c.unmet} warnings={len(_warn)}"))
    finally:
        _LV.board_for = _orig_bf
        B.RESEARCH_UNTIL = _saved_ru
        _lg.getLogger("strategy.breakout_plan").removeHandler(_h)
    return _tail()


def _frame_from(feed, sym, day, minute):
    saved = os.environ["OT_FEED_DB"]
    os.environ["OT_FEED_DB"] = feed
    try:
        return _frame(sym, day, minute)
    finally:
        os.environ["OT_FEED_DB"] = saved


def _tail():
    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks: a Breakout re-fire on a side needs a new session extreme")
    return 0


def _n5_child():
    """Run inside a FRESH interpreter against the parent's scratch stores."""
    from zoneinfo import ZoneInfo
    from datetime import datetime
    day = datetime.now(ZoneInfo(ET)).date()
    from strategy.breakout import Breakout
    import strategy.breakout as B
    B.LATEST_ET = "15:40"                                    # r187, as above
    from strategy.breakout_plan import BreakoutPlan
    BreakoutPlan._flow = staticmethod(lambda conn, symbol: (0.2, 1.0))
    spec = Breakout()
    p, _ = _tick(spec._plan_(), spec, "TST", day, 30)
    print("N5RESULT", "REFUSED" if _refused_at_gate(p) else "ALLOWED", _why(p))


if __name__ == "__main__":
    if os.environ.get("N5_RESTART") == "1":
        _n5_child()
    else:
        try:
            rc = main()
        finally:
            shutil.rmtree(SCRATCH, ignore_errors=True)
        sys.exit(rc)
