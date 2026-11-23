#!/usr/bin/env python3
"""
tests/check_hunt_no_dormant_guard.py  v5.1
v5.1  2026-11-23  OTV5 r153 (TRIM.2) — the Hunt is RETIRED (DORMANT, no switch), so its plan writes no row by rule; its
      code is kept until the purge, and this gate drives that code directly. G4a/G4b read the Hunt's own plan_tick
      verdict, so the run lifts the Hunt's plan state to ACTIVE inside this process only (the check_audit_20260823 a3
      pattern for the dormant condor). What G1-G4 pin is unchanged.
v5.0  2026-11-21  OTV5 r142 (HUNT.16) — NEW. BORN RED on r141 (G1, G2a-G2e, G3); green on r142.

THE DEFECT. strategy/liquidity_hunt.py (HUNT.13, OTV4TEST r316) asked trades.db, on every armed Hunt, for a CLOSED
losing Breakout on that side today, and HELD the Hunt when that read failed. Breakout is DORMANT with no switch since
r110 (strategy/plan_state.py), so no such row can be written: the only effect left was a Hunt held, for a reason that
cannot apply, whenever trades.db could not be read at that moment (locked, I/O error). The operator, 2026-11-21: "if
it's an obvious fix or improvement, let's consider it". r142 removes the guard, its read, its counterfactual writer,
its plan check and its config key (OT_HUNT_AFTER_BRK) with its Service-line field.

EVERYTHING HERE DRIVES THE REAL CODE: LiquidityHunt.generate_signal on check_liquidity_hunt's fixture (bias LONG, A1
from 101.00, target 102.50), a scratch trades.db written through the repo's own TradeLogger, and config read in a FRESH
interpreter. trades.db's failures are injected at TradeLogger._connect (a proxy that records every SQL statement).

  G1   an armed Hunt FIRES when trades.db turns unreadable after the Hunt's own one-per-break read (a lock that
       catches the next read of the tick); r141 held it "trades.db is UNREADABLE ... (HUNT.13)"
  G1b  ... and fires with a CLOSED losing long Breakout row in today's book (the dormant setup's book is not asked)
  G2a  the module defines no breakout_failed_today, _record_hunt_after_breakout or _HAB_SAID
  G2b  the module source has no SQL on strategy='Breakout' and no HUNT_AFTER_BRK
  G2c  PLAN_CHECKS has no breakout_failed (and keeps break_finished and runway)
  G2d  config (fresh interpreter, OT_HUNT_AFTER_BRK set) defines no HUNT_AFTER_BRK_MODE / _ENV_REFUSED
  G2e  main.py's Service line no longer names hunt_after_brk
  G3   on an armed tick the Hunt sends trades.db exactly ONE statement, the LiquidityHunt one-per-break read
  G4a  UNCHANGED: trades.db unreadable from the first read -> HOLD, "failing closed (one per break)"
  G4b  UNCHANGED: a Hunt row today on this break -> HOLD, "one per break"
  G4c  UNCHANGED: a price through its target -> no signal (runway structural)
  G4d  UNCHANGED: ATR under the reachability floor -> no signal
  G4e  UNCHANGED: before the entry window -> no signal
  G4f  UNCHANGED: a clean book -> the A1 long fires on the 102 call, stop at the 101.00 boundary, target 102.50
"""
import os
import sys
import sqlite3
import subprocess
import tempfile
import time
import types

import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path: sys.path.insert(1, _sp)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SCRATCH = tempfile.mkdtemp(prefix="chk_hunt_ndg_")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(SCRATCH, _v)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ.pop("OT_HUNT_AFTER_BRK", None)
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


class _Conn:
    """A trades.db connection proxy: records every statement; raises once the tick's read budget is spent."""
    def __init__(self, real, box):
        self._real, self._box = real, box

    def execute(self, sql, *a, **k):
        self._box["sql"].append(" ".join(str(sql).split()))
        return self._real.execute(sql, *a, **k)

    def __getattr__(self, n):
        return getattr(self._real, n)


def main():
    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        import pandas as pd
        from strategy import plan as P
        import strategy.liquidity_hunt as LH
        from strategy import plan_state as _ps              # v5.1 (r153): the Hunt is DORMANT (retired); lift it here
        _ps_orig = _ps.state
        _ps.state = lambda n: "active" if _ps.base(n) == "LiquidityHunt" else _ps_orig(n)
        from data.derived_store import DerivedStore
        import database.trade_logger as TLm
        from database.trade_logger import get_trade_logger, make_record
    except Exception as exc:                                    # noqa: BLE001
        check("G0 setup", False, f"{type(exc).__name__}: {exc}")
        return _tail()

    class St:
        def __init__(s): s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()
    st = St(); P.ensure_tables(st); P.bind_store(st)
    ds = DerivedStore(path=os.path.join(SCRATCH, "hunt_derived.db"))
    ds.mark_level_sync("TST", time.time())
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
    frame = pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in
                          [(100.9, 101.4, 100.8, 101.3), (101.3, 101.5, 101.2, 101.4)]],
                         index=pd.date_range("2026-09-10 09:42", periods=2, freq="1min"))

    tl = get_trade_logger()
    TL_cls = type(tl)
    real_connect = TL_cls._connect
    box = {"sql": [], "ok_reads": None, "n": 0}

    def _proxy_connect(self):
        box["n"] += 1
        if box["ok_reads"] is not None and box["n"] > box["ok_reads"]:
            raise sqlite3.OperationalError("database is locked")
        return _Conn(real_connect(self), box)

    def row():
        r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='LiquidityHunt' "
                            "ORDER BY rowid DESC LIMIT 1").fetchone()
        return (r["verdict"], r["reason"] or "") if r else ("", "")

    tick = [0.0]

    def fire(ok_reads=None, price=101.3, now_et="09:42", atr=0.14):
        h = LH.LiquidityHunt(); h._store = ds; h.planner.symbol = "TST"; LH.FINISHED.clear()
        if hasattr(LH, "_HAB_SAID"):
            LH._HAB_SAID.clear()
        box.update(sql=[], ok_reads=ok_reads, n=0)
        tick[0] += 1.0
        P.begin_tick(tick[0])
        TL_cls._connect = _proxy_connect
        try:
            sg = h.generate_signal(orb=orb, price_now=price, now_et=now_et, atr_pct=atr, chain=chain,
                                   df_1m=frame, atm_iv=0.25)
        finally:
            TL_cls._connect = real_connect
        P.close_tick(st, "TST")
        return sg, row(), list(box["sql"])

    def wipe():
        c = tl._connect()
        try:
            c.execute("DELETE FROM trades"); c.commit()
        finally:
            c.close()

    day = datetime.now(ZoneInfo(ET)).date()
    at = (datetime.now(ZoneInfo(ET)) - timedelta(minutes=2)).astimezone(ZoneInfo("UTC")).isoformat()
    if datetime.now(ZoneInfo(ET)).date() != (datetime.now(ZoneInfo(ET)) - timedelta(minutes=2)).date():
        at = datetime(day.year, day.month, day.day, 0, 1, tzinfo=ZoneInfo(ET)).astimezone(ZoneInfo("UTC")).isoformat()

    def log_row(strategy, side, pnl=None, closed=False, ustop=None):
        import uuid
        tid = str(uuid.uuid4())
        tl.log_entry(make_record(trade_id=tid, symbol="TST", strategy=strategy,
                                 setup_type=f"{strategy.lower()}_x",
                                 direction=("long" if side == "call" else "short"), option_side=side,
                                 underlying_stop=ustop, orb_range_high=101.0, orb_range_low=100.0, paper_trade=1))
        c = tl._connect()
        try:
            c.execute("UPDATE trades SET entry_time=? WHERE trade_id=?", (at, tid))
            if closed:
                c.execute("UPDATE trades SET status='closed', pnl_usd=?, exit_time=? WHERE trade_id=?", (pnl, at, tid))
            c.commit()
        finally:
            c.close()
        return tid

    # G4f the baseline: a clean book fires
    wipe()
    sig, r, sql = fire()
    guard("G4f UNCHANGED: a clean book -> the A1 long fires (102 call, stop 101.00, target 102.50)",
          lambda: (sig is not None and sig.direction == "long" and float(sig.strike) == 102.0
                   and float(sig.underlying_stop) == 101.0 and float(sig.underlying_target) == 102.5
                   and sig.setup_type == "liquidity_hunt_A1", f"{r[0]} {r[1][-120:]}"))
    guard("G3  an armed tick sends trades.db ONE statement: the Hunt's own one-per-break read",
          lambda: (len(sql) == 1 and "strategy='LiquidityHunt'" in sql[0]
                   and not any("Breakout" in s for s in sql), f"{len(sql)} statements: {[s[:90] for s in sql]}"))

    # G1 trades.db turns unreadable after the one-per-break read
    sig, r, sql = fire(ok_reads=1)
    guard("G1  trades.db unreadable after the one-per-break read -> the armed A1 long FIRES (r141 held it, HUNT.13)",
          lambda: (sig is not None and sig.direction == "long" and "HUNT.13" not in r[1], f"{r[0]} {r[1][-140:]}"))

    # G1b a closed losing long Breakout in today's book does not hold it either
    log_row("Breakout", "call", pnl=-310.0, closed=True)
    sig, r, sql = fire()
    cf = os.path.join(os.environ["OT_COUNTERFACTUAL_DIR"], "hunt_after_breakout.jsonl")
    guard("G1b a closed losing long Breakout row today -> the A1 long still fires; no hunt_after_breakout row",
          lambda: (sig is not None and "HUNT.13" not in r[1] and not os.path.exists(cf), f"{r[0]} {r[1][-140:]}"))

    # G2 the code is gone
    src = open(LH.__file__, encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    body = code.split('"""', 2)[-1] if code.startswith('"""') else code     # past the module docstring (history)
    guard("G2a no breakout_failed_today / _record_hunt_after_breakout / _HAB_SAID",
          lambda: (not any(hasattr(LH, n) for n in ("breakout_failed_today", "_record_hunt_after_breakout", "_HAB_SAID")),
                   str([n for n in ("breakout_failed_today", "_record_hunt_after_breakout", "_HAB_SAID") if hasattr(LH, n)])))
    guard("G2b the module's code has no SQL on strategy='Breakout' and no HUNT_AFTER_BRK",
          lambda: ("strategy='Breakout'" not in body and "HUNT_AFTER_BRK" not in body
                   and "hunt_after_breakout" not in body, "found" if "strategy='Breakout'" in body else ""))
    pc = tuple(getattr(LH.LiquidityHunt, "PLAN_CHECKS", ()))
    guard("G2c PLAN_CHECKS has no breakout_failed, keeps break_finished and runway",
          lambda: ("breakout_failed" not in pc and "break_finished" in pc and "runway" in pc, str(pc)))
    env = {k: v for k, v in os.environ.items()}
    env["OT_HUNT_AFTER_BRK"] = "trade"
    shim = ("import sys,os,glob;[sys.path.insert(1,p) for p in glob.glob(os.path.join(os.getcwd(),'venv','lib',"
            "'python*','site-packages'))];sys.path.insert(0,os.getcwd());")
    cp = subprocess.run([sys.executable, "-c", shim + "import config as c;print('HAS',hasattr(c,'HUNT_AFTER_BRK_MODE'),"
                         "hasattr(c,'HUNT_AFTER_BRK_ENV_REFUSED'))"], cwd=ROOT, env=env,
                        capture_output=True, text=True, timeout=120)
    out = (cp.stdout + cp.stderr).strip()
    guard("G2d config (fresh, OT_HUNT_AFTER_BRK=trade) defines no HUNT_AFTER_BRK_MODE / _ENV_REFUSED",
          lambda: ("HAS False False" in out, f"rc={cp.returncode} {out[-160:]}"))
    msrc = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    mcode = "\n".join(l for l in msrc.splitlines() if not l.lstrip().startswith("#")).split('"""', 2)[-1]
    guard("G2e main.py's Service line no longer names hunt_after_brk",
          lambda: ("hunt_after_brk=" not in mcode and "HUNT_AFTER_BRK" not in mcode, ""))

    # G4 the Hunt's other gates
    wipe()
    sig, r, sql = fire(ok_reads=0)
    guard("G4a UNCHANGED: trades.db unreadable from the first read -> HOLD, failing closed (one per break)",
          lambda: (sig is None and r[0] == "HOLD" and "failing closed (one per break)" in r[1], f"{r[0]} {r[1][-140:]}"))
    log_row("LiquidityHunt", "call", ustop=101.0)
    sig, r, sql = fire()
    guard("G4b UNCHANGED: a Hunt row today on this break -> HOLD, one per break",
          lambda: (sig is None and r[0] == "HOLD" and "one per break" in r[1], f"{r[0]} {r[1][-140:]}"))
    wipe()
    sig, r, sql = fire(price=102.6)
    guard("G4c UNCHANGED: a price through its 102.50 target -> no signal",
          lambda: (sig is None, f"{r[0]} {r[1][-140:]}"))
    sig, r, sql = fire(atr=0.01)
    guard("G4d UNCHANGED: ATR under the reachability floor -> no signal",
          lambda: (sig is None, f"{r[0]} {r[1][-140:]}"))
    sig, r, sql = fire(now_et="09:20")
    guard("G4e UNCHANGED: before the entry window -> no signal",
          lambda: (sig is None, f"{r[0]} {r[1][-140:]}"))
    return _tail()


def _tail():
    print()
    if FAILED:
        print(f"check_hunt_no_dormant_guard: {len(FAILED)} FAILED of {len(RAN)}: {' '.join(FAILED)}")
        return 1
    print(f"check_hunt_no_dormant_guard: all {len(RAN)} checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
