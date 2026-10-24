#!/usr/bin/env python3
"""
tests/check_breakout_rearm.py  v1.2
v1.2  CD.2 (2026-10-24) - the fixture marks the level book SYNCED (store.mark_level_sync) after seeding the ledger:
      LevelEngine.board() now fails closed as not_synced until a book sync against a recent closed 1m bar has been
      recorded (derived/levels v6.10). Every expectation is unchanged.
v1.1  2026-10-24  CD.1 - RE-POINTED (section 38.4): RENT.2/RENT.3 is scrapped, so C1 checks the two remaining modes and
      C1c becomes "OT_REENTRY_GATE is no longer read" (config has no REENTRY_GATE_MODE).
v1.0  2026-10-24  OTV4TEST r316 (BRK.15 + HUNT.13 + RENT.3) — BORN RED on 8c387f6 (r315).

THE OPERATOR'S RULINGS, 2026-10-24, verbatim:
  13:45 ET  "The new session high/low rule needs to be dropped. You established that the move was mostly done if
            we waited for a new extreme. The 20 second rule also was proven unnecessary after today's reentry
            study ... my proposal: on a losing breakout trade, forbid a liquidity hunt on the same side for the day."
  13:56 ET  "1. For now, rearm it on every reentry. 2. No more 20 second blocks ... 3. Yes, if a breakout on one
            side fails, don't allow a hunt to fire on that side for the rest of the day. 4. That is correct. Yes,
            effective Monday"

EVERYTHING HERE DRIVES THE REAL CODE: BreakoutPlan.prepare on synthetic 1m bars in a scratch feed store, "fired"
and "lost" from a scratch trades.db written through the repo's own TradeLogger, LiquidityHunt.generate_signal on
the fixture check_liquidity_hunt uses, and config read in a FRESH interpreter for the defaults. Counterfactual
rows go to a scratch OT_COUNTERFACTUAL_DIR, never the live one. Only the order-flow reader is stubbed.

  R1  the first break on a side fires
  R2  a close beyond the edge that CONTINUES the break (no close back inside since) is refused under the gate
      "fresh_break" - even a NEW session high (r131 would have fired it), and that disagreement is recorded
  R3  a close back inside, then a re-break UNDER the session high, fires (r131 refused it) - recorded
  R4  EVERY return re-arms: after the R3 entry, a second return and re-break fires again
  R5  r142 kept: the bar that already fired is refused
  R6  the short side mirrors R3
  R7  an unreadable tape FAILS CLOSED under "fresh_break"
  R8  OT_BRK_REFIRE=extreme restores r131 exactly: R3's bar is refused under "new_extreme" (fresh interpreter)
  R9  breakout.GATES declares FRESH_BREAK FOUNDATIONAL and NEW_EXTREME stays declared (the rollback)
  C1  config defaults (fresh interpreter, env cleared): BRK_REFIRE_MODE rearm, HUNT_AFTER_BRK_MODE trade; a bogus
      value of each reads the default and is NAMED; OT_REENTRY_GATE is not read (RENT.2/RENT.3 scrapped, CD.1)
  U1  breakout_failed_today: a losing same-side closed Breakout -> it; a winner, the other side, an open
      loser -> None; an unreadable book -> "unreadable"
  U2  the Hunt's A1 long fires with no losing long Breakout today
  U3  ... and HOLDS, named HUNT.13, once a long Breakout today closed at a loss; one row recorded
  U4  a losing SHORT Breakout does not hold the long Hunt
  U5  OT_HUNT_AFTER_BRK=log fires and records the would-be hold; off records nothing
"""
import os
import sys
import json
import sqlite3
import subprocess
import tempfile
import types
import time

import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path: sys.path.insert(1, _sp)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SCRATCH = os.environ.get("RA_SCRATCH") or tempfile.mkdtemp(prefix="chk_brk_ra_", dir="/var/tmp")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(SCRATCH, _v)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_BRK_RESEARCH_UNTIL"] = "2099-12-31"      # informers: accept any
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


# ── the session. Range 100.00-101.00 on RA (long); RAS mirrors it about 200 (short).
#    One bar per minute from 09:30 (minute 0).
def _session():
    b = {m: (100.5, 101.0, 100.0, 100.5) for m in range(0, 5)}          # 09:30-09:34 the range
    for m in range(5, 61):
        b[m] = (101.5, 101.8, 101.3, 101.6)                             # beyond the edge (filler)
    b[5] = (100.6, 101.4, 100.55, 101.30)                               # 09:35 FIRST BREAK
    b[10] = (101.6, 102.5, 101.5, 101.9)                                # 09:40 session high 102.50
    b[12] = (101.9, 102.9, 101.8, 102.80)                               # 09:42 NEW HIGH close, break never returned
    b[13] = (102.8, 102.85, 100.5, 100.60)                              # 09:43 BACK INSIDE (100.60 <= 101.00)
    b[14] = (100.6, 100.9, 100.5, 100.70)                               # 09:44 inside
    b[15] = (100.7, 101.5, 100.65, 101.40)                              # 09:45 RE-BREAK 101.40, under the 102.90 high
    b[16] = (101.4, 101.45, 100.4, 100.50)                              # 09:46 back inside again
    b[17] = (100.5, 101.35, 100.45, 101.30)                             # 09:47 a SECOND re-break
    return b


def _mirror(b):
    return {m: (200 - o, 200 - l, 200 - h, 200 - c) for m, (o, h, l, c) in b.items()}


def _write_feed(day):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    c = sqlite3.connect(os.environ["OT_FEED_DB"])
    c.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, "
              "ts_epoch_ms INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL, "
              "volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    o = int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET)).timestamp() * 1000)
    for sym, bars in (("RA", _session()), ("RAS", _mirror(_session()))):
        for m, (op, h, l, cl) in bars.items():
            c.execute("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)",
                      (sym, "1m", o + m * 60_000, op, h, l, cl, 1000.0))
    c.commit()
    c.close()


def _frame(sym, day, minute, feed=None):
    import pandas as pd
    from datetime import datetime
    from zoneinfo import ZoneInfo
    o = int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET)).timestamp() * 1000)
    c = sqlite3.connect(f"file:{feed or os.environ['OT_FEED_DB']}?mode=ro", uri=True)
    rows = c.execute("SELECT ts_epoch_ms, open, high, low, close, volume FROM candles "
                     "WHERE symbol=? AND interval='1m' AND ts_epoch_ms <= ? ORDER BY ts_epoch_ms",
                     (sym, o + minute * 60_000)).fetchall()
    c.close()
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.pop("ts"), unit="ms", utc=True).dt.tz_convert(ET)
    return df.iloc[-60:]


class _ORB:
    def __init__(self, hi, lo):
        self.orb_high, self.orb_low = hi, lo


class _C:
    def __init__(self, k):
        self.strike, self.mark, self.delta, self.gamma, self.expiry = k, 1.0, 0.5, 0.05, ""
        self.ask, self.bid = 1.05, 0.95


class _Chain:
    def __init__(self, px):
        ks = [round(px) + i for i in range(-6, 7)]
        self.calls, self.puts = [_C(k) for k in ks], [_C(k) for k in ks]


def _hm(minute):
    return f"{9 + (30 + minute) // 60:02d}:{(30 + minute) % 60:02d}"


def _tick(plan, spec, sym, day, minute, feed=None):
    """Ask the plan at the START of `minute`: the last closed bar is minute-1."""
    df = _frame(sym, day, minute, feed)
    px = float(df.iloc[-1]["open"])
    hi, lo = (100.00, 99.00) if sym == "RAS" else (101.00, 100.00)
    return plan.prepare(spec=spec, orb=_ORB(hi, lo), price_now=px, now_et=_hm(minute),
                        chain=_Chain(px), df_1m=df, flow_conn=None, symbol=sym)


def _why(p):
    t = p.tick
    return f"ready={p.ready} why={(t.plan.last()[2] if t.closed else '-')[:110]!r}"


def _refused(p, gate):
    t = p.tick
    return (not p.ready and t.closed and str(t.plan.last()[2]).startswith(f"{gate}:"))


def _log_brk(side, minute, day, pnl=None, closed=False, sym="RA"):
    """A Breakout entry filled 16 s into `minute` of `day`, optionally closed at `pnl`."""
    import uuid
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from database.trade_logger import get_trade_logger, make_record
    tid = str(uuid.uuid4())
    tl = get_trade_logger()
    tl.log_entry(make_record(
        trade_id=tid, symbol=sym, strategy="Breakout",
        setup_type=f"breakout_{'long' if side == 'call' else 'short'}",
        direction=("long" if side == "call" else "short"), option_side=side,
        orb_range_high=101.0, orb_range_low=100.0, paper_trade=1))
    at = (datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET))
          + timedelta(minutes=minute, seconds=16)).astimezone(ZoneInfo("UTC")).isoformat()
    conn = tl._connect()
    try:
        conn.execute("UPDATE trades SET entry_time=? WHERE trade_id=?", (at, tid))
        if closed:
            conn.execute("UPDATE trades SET status='closed', pnl_usd=?, exit_time=? WHERE trade_id=?",
                         (pnl, at, tid))
        elif pnl is not None:                                # an OPEN trade carrying a running loss
            conn.execute("UPDATE trades SET pnl_usd=? WHERE trade_id=?", (pnl, tid))
        conn.commit()
    finally:
        conn.close()
    return tid


def _cf_rows(name):
    p = os.path.join(os.environ["OT_COUNTERFACTUAL_DIR"], name)
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


_SHIM = ("import sys,os,glob;[sys.path.insert(1,p) for p in glob.glob(os.path.join(os.getcwd(),'venv','lib',"
         "'python*','site-packages'))];sys.path.insert(0,os.getcwd());")


def _child(env_extra, code):
    """A FRESH interpreter (config reads env at import) with this file's scratch stores."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("OT_BRK_REFIRE", "OT_HUNT_AFTER_BRK", "OT_REENTRY_GATE")}
    env.update(env_extra)
    env["RA_SCRATCH"] = SCRATCH
    r = subprocess.run([sys.executable, "-c", _SHIM + code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        day = datetime.now(ZoneInfo(ET)).date()
        _write_feed(day)
        from database.trade_logger import get_trade_logger
        get_trade_logger()
        import strategy.breakout as B
        B.LATEST_ET = "15:40"                                # the re-fire rule, not the window
        from strategy.breakout import Breakout
        from strategy.breakout_plan import BreakoutPlan
        BreakoutPlan._flow = staticmethod(lambda conn, symbol: (0.2, 1.0))
        spec = Breakout()
        plan = spec._plan_()
    except Exception as exc:                                    # noqa: BLE001
        check("R0 setup", False, f"{type(exc).__name__}: {exc}")
        return _tail()

    gate = getattr(B, "FRESH_BREAK", "fresh_break")

    # R1 the first long break (signal 09:35)
    p1 = _tick(plan, spec, "RA", day, 6)
    guard("R1 the first break on a side fires", lambda: (p1.ready and p1.direction == "long", _why(p1)))
    _log_brk("call", 6, day)                                 # it filled at 09:36:16

    # R2 09:42 closes a NEW session high but the 09:35 break never returned inside
    p2 = _tick(plan, spec, "RA", day, 13)
    guard(f"R2 a continuation of the break - even a new session high - is refused under '{gate}'",
          lambda: (_refused(p2, gate), _why(p2)))
    guard("R2b ...and the disagreement with r131 (which would have fired) is recorded",
          lambda: (any(r.get("direction") == "long" and r.get("rearm_ok") is False
                       and r.get("new_extreme_ok") is True and r.get("fired") is False
                       for r in _cf_rows("breakout_refire.jsonl")), str(_cf_rows("breakout_refire.jsonl"))[:160]))

    # R3 09:43 back inside, 09:45 re-break under the session high
    p3 = _tick(plan, spec, "RA", day, 16)
    guard("R3 a close back inside, then a re-break UNDER the session high, fires",
          lambda: (p3.ready and p3.direction == "long", _why(p3)))
    guard("R3b ...and r131's refusal of it is recorded beside the fire",
          lambda: (any(r.get("rearm_ok") is True and r.get("new_extreme_ok") is False and r.get("fired") is True
                       for r in _cf_rows("breakout_refire.jsonl")), str(_cf_rows("breakout_refire.jsonl"))[-160:]))
    _log_brk("call", 16, day)                                # filled 09:46:16 on the 09:45 bar

    # R5 the same bar again (ask at 09:46:30: the last closed bar is still 09:45)
    p5 = _tick(plan, spec, "RA", day, 16)
    guard(f"R5 r142 kept: the bar that already fired is refused under '{gate}'",
          lambda: (_refused(p5, gate) and "already fired" in str(p5.tick.plan.last()[2]), _why(p5)))

    # R4 09:46 back inside again, 09:47 a second re-break
    p4 = _tick(plan, spec, "RA", day, 18)
    guard("R4 EVERY return re-arms: a second return and re-break fires again",
          lambda: (p4.ready and p4.direction == "long", _why(p4)))

    # R6 the short mirror of R3 (its first break is spent by the earlier bars, never filled)
    _log_brk("put", 6, day, sym="RAS")
    p6 = _tick(plan, spec, "RAS", day, 16)
    guard("R6 the short side mirrors it: a return and re-break fires short",
          lambda: (p6.ready and p6.direction == "short", _why(p6)))

    # R7 unreadable tape
    feed = os.environ["OT_FEED_DB"]
    df7 = _frame("RA", day, 18)                              # signal 09:47: past r142, so the TAPE is what is read
    os.environ["OT_FEED_DB"] = os.path.join(SCRATCH, "absent", "feed.db")
    try:
        p7 = plan.prepare(spec=spec, orb=_ORB(101.0, 100.0), price_now=101.3, now_et="09:48",
                          chain=_Chain(101.3), df_1m=df7, flow_conn=None, symbol="RA")
    except Exception as exc:                                    # noqa: BLE001  a crash is a FAIL line, not an exit
        p7 = exc
    finally:
        os.environ["OT_FEED_DB"] = feed
    guard(f"R7 an unreadable tape FAILS CLOSED under '{gate}'",
          lambda: ((not isinstance(p7, Exception)) and _refused(p7, gate)
                   and "unreadable" in str(p7.tick.plan.last()[2]),
                   repr(p7)[:160] if isinstance(p7, Exception) else _why(p7)))

    # R8 the rollback, in a fresh interpreter on the same stores (R3's bar again, as a fresh side)
    code8 = (
        "import os,sys;sys.argv=['x'];sys.path.insert(0,'tests');import check_breakout_rearm as K;"
        "from zoneinfo import ZoneInfo;from datetime import datetime;"
        "day=datetime.now(ZoneInfo('America/New_York')).date();"
        "import strategy.breakout as B;B.LATEST_ET='15:40';"
        "from strategy.breakout import Breakout;from strategy.breakout_plan import BreakoutPlan;"
        "BreakoutPlan._flow=staticmethod(lambda c,s:(0.2,1.0));sp=Breakout();pl=sp._plan_();"
        "p=K._tick(pl,sp,'RAS',day,16);"
        "print('VERDICT', p.ready, str(p.tick.plan.last()[2])[:80] if p.tick.closed else '-')")
    rc8, out8 = _child({"OT_BRK_REFIRE": "extreme"}, code8)
    guard("R8 OT_BRK_REFIRE=extreme restores r131: the RAS re-break under the session low is refused at new_extreme",
          lambda: ("VERDICT False new_extreme:" in out8, f"rc={rc8} {out8[-200:]}"))

    guard("R9 breakout.GATES declares FRESH_BREAK FOUNDATIONAL and keeps NEW_EXTREME (the rollback)",
          lambda: (B.GATES.get("FRESH_BREAK") == "FOUNDATIONAL" and B.GATES.get("NEW_EXTREME") == "FOUNDATIONAL",
                   str({k: B.GATES.get(k) for k in ("FRESH_BREAK", "NEW_EXTREME")})))

    # C1 config defaults and refusals, fresh interpreters
    cc = ("import config as c;print('MODES',c.BRK_REFIRE_MODE,c.HUNT_AFTER_BRK_MODE,"
          "repr(c.BRK_REFIRE_ENV_REFUSED),repr(c.HUNT_AFTER_BRK_ENV_REFUSED),hasattr(c,'REENTRY_GATE_MODE'))")
    rc_a, out_a = _child({}, cc)
    guard("C1a unset: brk_refire=rearm, hunt_after_brk=trade",
          lambda: ("MODES rearm trade '' '' False" in out_a, f"rc={rc_a} {out_a[-160:]}"))
    rc_b, out_b = _child({"OT_BRK_REFIRE": "bogus", "OT_HUNT_AFTER_BRK": "nope"}, cc)
    guard("C1b a bogus value of each reads the default and is NAMED",
          lambda: ("MODES rearm trade 'bogus' 'nope' False" in out_b, f"rc={rc_b} {out_b[-160:]}"))
    rc_c, out_c = _child({"OT_REENTRY_GATE": "trade"}, cc)
    guard("C1c OT_REENTRY_GATE is no longer read (RENT.2/RENT.3 scrapped)",
          lambda: ("MODES rearm trade '' '' False" in out_c, f"rc={rc_c} {out_c[-160:]}"))

    _hunt(day)
    return _tail()


def _hunt(day):
    """U1-U5 on check_liquidity_hunt's own fixture (bias LONG, A1 from 101.00)."""
    try:
        import config
        from strategy import plan as P
        import strategy.liquidity_hunt as LH
        from execution import handoff as H
        from data.derived_store import DerivedStore
    except Exception as exc:                                    # noqa: BLE001
        check("U0 setup", False, f"{type(exc).__name__}: {exc}")
        return
    bft = getattr(LH, "breakout_failed_today", None)

    class St:
        def __init__(s): s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()
    st = St(); P.ensure_tables(st); P.bind_store(st)
    ds = DerivedStore(path=os.path.join(SCRATCH, "hunt_derived.db"))
    ds.mark_level_sync("TST", time.time())        # CD.2: the book is synced "now"
    LH._symbol_of = lambda: "TST"
    now = time.time()
    ds.upsert_level(("TST:prev_day:102.50", "TST", 102.5, "resistance", "prev_day", "day", now - 3600, 0, None, 0, None, None, 1))
    ds.upsert_level(("TST:london:97.00", "TST", 97.0, "support", "london", "session", now - 3600, 0, None, 0, None, None, 1))
    orb = types.SimpleNamespace(orb_high=101.0, orb_low=100.0)

    class _G:
        def __init__(s, k, prem, delta, gamma):
            s.strike, s.mark, s.ask, s.bid = float(k), prem, prem + 0.02, prem - 0.02
            s.delta, s.gamma, s.theta, s.expiry, s.open_interest, s.symbol = delta, gamma, -0.04, "x", 100, f"O{k}"
    chain = types.SimpleNamespace(calls=[_G(101, 0.95, 0.46, 0.05), _G(102, 0.48, 0.30, 0.058),
                                         _G(103, 0.20, 0.17, 0.04), _G(104, 0.10, 0.08, 0.02)], puts=[])
    import pandas as pd
    frame = pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in
                          [(100.9, 101.4, 100.8, 101.3), (101.3, 101.5, 101.2, 101.4)]],
                         index=pd.date_range("2026-09-10 09:42", periods=2, freq="1min"))

    def row():
        r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='LiquidityHunt' "
                            "ORDER BY rowid DESC LIMIT 1").fetchone()
        return (r["verdict"], r["reason"] or "") if r else ("", "")

    def fire(n):
        h = LH.LiquidityHunt(); h._store = ds; h.planner.symbol = "TST"; LH.FINISHED.clear(); H.reset()
        try:
            LH._HAB_SAID.clear()
        except AttributeError:
            pass
        P.begin_tick(n)
        sg = h.generate_signal(orb=orb, price_now=101.3, now_et="09:42", atr_pct=0.14, chain=chain,
                               df_1m=frame, atm_iv=0.25)
        P.close_tick(st, "TST")
        return sg, row()

    def wipe():
        with sqlite3.connect(os.environ["OT_TRADES_DB"]) as c:
            c.execute("DELETE FROM trades")

    def log_now(side, pnl, closed=True):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        nowm = datetime.now(ZoneInfo(ET))
        return _log_brk(side, max(0, (nowm.hour - 9) * 60 + nowm.minute - 30 - 1), day, pnl=pnl, closed=closed)

    # U1 the book read
    wipe()
    log_now("call", 250.0)                                   # a WINNING long
    log_now("put", -400.0)                                   # a losing SHORT
    log_now("call", -300.0, closed=False)                    # an OPEN long (not failed yet)
    r_none = bft("long") if bft else "absent"
    lose = log_now("call", -310.0)                           # the losing long
    r_hit = bft("long") if bft else "absent"
    import database.trade_logger as TLm
    _gtl = TLm.get_trade_logger

    def _boom(*a, **k):
        raise sqlite3.OperationalError("unable to open database file")
    TLm.get_trade_logger = _boom
    try:
        r_bad = bft("long") if bft else "absent"
    finally:
        TLm.get_trade_logger = _gtl
    guard("U1 breakout_failed_today: winner / other side / open loser -> None; a closed losing long -> it; "
          "an unreadable book -> 'unreadable'",
          lambda: (r_none is None and isinstance(r_hit, tuple) and r_hit[0] == lose and r_hit[1] == -310.0
                   and r_bad == "unreadable", f"none={r_none!r} hit={r_hit!r} unreadable={r_bad!r}"))

    # U2 no losing long today -> A1 fires
    wipe()
    log_now("put", -400.0)                                   # U4's losing SHORT is present from the start
    sig, r = fire(1.0)
    guard("U2/U4 with no losing LONG Breakout today (a losing short is) the A1 long fires",
          lambda: (sig is not None and sig.direction == "long", f"{r[0]} {r[1][-100:]}"))

    # U3 a losing long -> HOLD, named, recorded
    log_now("call", -310.0)
    n0 = len(_cf_rows("hunt_after_breakout.jsonl"))
    sig, r = fire(2.0)
    rows = _cf_rows("hunt_after_breakout.jsonl")[n0:]
    guard("U3 a long Breakout that LOST today holds the long Hunt, named HUNT.13",
          lambda: (sig is None and r[0] == "HOLD" and "HUNT.13" in r[1], f"{r[0]} {r[1][-120:]}"))
    guard("U3b ...and one row is recorded with the losing trade and held=True",
          lambda: (len(rows) == 1 and rows[0].get("held") is True and rows[0].get("breakout_pnl") == -310.0
                   and rows[0].get("direction") == "long", str(rows)[:200]))

    # U5 log and off
    _mode = getattr(config, "HUNT_AFTER_BRK_MODE", None)
    try:
        config.HUNT_AFTER_BRK_MODE = "log"
        n1 = len(_cf_rows("hunt_after_breakout.jsonl"))
        sig_l, r_l = fire(3.0)
        rows_l = _cf_rows("hunt_after_breakout.jsonl")[n1:]
        config.HUNT_AFTER_BRK_MODE = "off"
        n2 = len(_cf_rows("hunt_after_breakout.jsonl"))
        sig_o, r_o = fire(4.0)
        rows_o = _cf_rows("hunt_after_breakout.jsonl")[n2:]
    finally:
        config.HUNT_AFTER_BRK_MODE = _mode
    guard("U5 log fires the Hunt and records the would-be hold (held=False); off fires and records nothing",
          lambda: (sig_l is not None and len(rows_l) == 1 and rows_l[0].get("held") is False
                   and sig_o is not None and rows_o == [],
                   f"log={sig_l is not None}/{rows_l} off={sig_o is not None}/{rows_o}"))


def _tail():
    print()
    if FAILED:
        print(f"check_breakout_rearm: {len(FAILED)} FAILED of {len(RAN)}: {' '.join(FAILED)}")
        return 1
    print(f"check_breakout_rearm: all {len(RAN)} checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
