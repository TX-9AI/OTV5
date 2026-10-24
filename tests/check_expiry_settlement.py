#!/usr/bin/env python3
"""
tests/check_expiry_settlement.py  v1.0

AN EXPIRED POSITION IS BOOKED AT ITS SETTLEMENT VALUE - NOT A FLAGGED $0.00 - AND
SHARES LEFT BY AN EXERCISE OR ASSIGNMENT PAGE THE OPERATOR.

v1.0  2026-09-27  OTV4TEST r165 (EXP.1). The operator approved EXP.1's booking fix
      (2026-09-27, "Yes" / "That's fine"). QQQ is physically settled and American-style:
      a long ITM 0DTE held to 16:00 is EXERCISED into shares, a short ITM one ASSIGNED.
      The path such a position actually takes is boot Step 1,
      TradeLogger.close_expired_open_trades, which forced pnl_usd to 0.0 - so an
      exercised winner booked as nothing and an expired-worthless loser as nothing.

DRIVES THE REAL CODE (WA 21), with scratch stores and recorders:
  X1-X5  broker_reconcile.settle_expired: long ITM (exercised), long OTM (worthless),
         short ITM (assigned), a credit vertical, a butterfly - net on
         match_closing_fills' basis
  X6     not yet expired (15:59 on the expiry day) -> None; at 16:00 -> settles
  X7     no settlement price -> None (the caller keeps the flagged $0.00)
  X8     the REAL TradeLogger.close_expired_open_trades(settle=...) on a scratch DB:
         the ITM row books intrinsic and a positive P&L, the OTM row its real loss
         (not 0.0), an unpriceable row the flagged 0.0 exactly as before
  X9     main._close_phantom_with_recovery settles an EXPIRED phantom (recorder
         trade_logger) and still flags a PRE-expiry phantom $0.00 unknown
  X10    main._check_exercise_footprint pages shares in the box's instrument, ignores
         other symbols, and pages NOTHING when the read fails or is empty
  X12    the REAL close_phantom books a recovered fill - it wrote a non-existent `exit_price`
         column since the v4 port (08-19) and raised on the first live recovery
  X11    HOP 0: boot Step 1 passes settle=_settle_expired_row, and the live broker
         reconcile calls _check_exercise_footprint

BORN RED on 26132e0 (r164) - see the ledger row.
Run:  python3 tests/check_expiry_settlement.py
"""
from __future__ import annotations

import ast
import datetime as dt
import glob as _glob
import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
sys.path.insert(0, ROOT)
_S = tempfile.mkdtemp(prefix="check_expiry_settlement_", dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
if not os.environ.get("OT_TRADES_DB"):
    os.environ["OT_TRADES_DB"] = os.path.join(_S, "t.db")
    os.environ["OT_DERIVED_DB"] = os.path.join(_S, "d.db")
    os.environ["OT_RESTING_DB"] = os.path.join(_S, "r.db")
    os.environ["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(_S, "sj")
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_PAPER_TRADING"] = "True"
import logging
logging.disable(logging.CRITICAL)
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        FAIL.append(name.split()[0])


print("=" * 68)
print("EXPIRY SETTLEMENT - booked at value; shares page")
print("=" * 68)

from execution import broker_reconcile as BR                           # noqa: E402
HAS = hasattr(BR, "settle_expired")
check("X0 broker_reconcile.settle_expired exists", HAS, "" if HAS else "absent")

EXP = "2026-09-25"
AFTER = dt.datetime(2026, 9, 25, 16, 0, tzinfo=ET)
spot = lambda s, e: 705.00                                             # noqa: E731


def S(rec, now=AFTER, reader=spot):
    return BR.settle_expired(rec, now, reader) if HAS else "ABSENT"


base = {"symbol": "QQQ", "expiry": EXP, "option_side": "call", "contracts": 2, "strategy": "Breakout"}
long_itm = dict(base, strike=700.0, entry_premium=1.00)
long_otm = dict(base, strike=710.0, entry_premium=1.00)
short_itm = dict(base, strike=700.0, entry_premium=1.00, is_short_position=1)
vert = dict(base, strategy="SweepCreditSpread", is_condor_leg=1, short_symbol=".QQQ260925C700",
            long_symbol=".QQQ260925C706", short_strike=700.0, long_strike=706.0, entry_premium=0.50)
fly = dict(base, strategy="GEXPinButterfly", is_butterfly=1, lower_strike=700.0, center_strike=705.0,
           upper_strike=710.0, entry_premium=1.20)
check("X1 long call ITM -> intrinsic 5.00, exercised", S(long_itm) == (5.0, "expired_itm_exercised"), str(S(long_itm)))
check("X2 long call OTM -> 0.00, worthless (a REAL value, not unknown)", S(long_otm) == (0.0, "expired_worthless"), str(S(long_otm)))
check("X3 short call ITM -> 5.00, assigned", S(short_itm) == (5.0, "expired_itm_assigned"), str(S(short_itm)))
check("X4 credit vertical 700/706 at 705 -> short 5 - long 0 = 5.00", S(vert) == (5.0, "expired_settled"), str(S(vert)))
check("X5 butterfly 700/705/710 pinned at 705 -> 5.00", S(fly) == (5.0, "expired_settled"), str(S(fly)))
check("X6 15:59 on the expiry day -> None; 16:00 -> settles",
      S(long_itm, now=dt.datetime(2026, 9, 25, 15, 59, tzinfo=ET)) is None and S(long_itm)[1] == "expired_itm_exercised",
      f"{S(long_itm, now=dt.datetime(2026, 9, 25, 15, 59, tzinfo=ET))}")
check("X7 no settlement price -> None (flagged $0.00 kept)", S(long_itm, reader=lambda s, e: None) is None, "")

# ── X8 the real boot Step 1 path, scratch DB ─────────────────────────────────
from database.trade_logger import TradeLogger, make_record              # noqa: E402
TL = TradeLogger(paper_trading=True)
for tid, rec in (("x8-itm", long_itm), ("x8-otm", long_otm), ("x8-nop", dict(long_itm, symbol="NOPE"))):
    TL.log_entry(make_record(trade_id=tid, **{k: v for k, v in rec.items()}))
# log_entry stamps entry_time now; expiry 09-25 is in the past for any run after it.
def settle(r):
    got = BR.settle_expired(r, AFTER + dt.timedelta(days=400), lambda s, e: 705.0 if s == "QQQ" else None)
    return None if got is None else (got[0], BR.phantom_pnl(r, got[0]), got[1])
try:
    TL.close_expired_open_trades(settle=settle)
    import sqlite3
    c = sqlite3.connect(os.environ["OT_TRADES_DB"]); c.row_factory = sqlite3.Row
    got = {r["trade_id"]: dict(r) for r in c.execute("select trade_id,exit_premium,pnl_usd,exit_reason,status from trades")}
    ok8 = (got["x8-itm"]["pnl_usd"] == (5.0 - 1.0) * 2 * 100 and "expired_itm_exercised" in got["x8-itm"]["exit_reason"]
           and got["x8-otm"]["pnl_usd"] == -1.0 * 2 * 100 and "expired_worthless" in got["x8-otm"]["exit_reason"]
           and got["x8-nop"]["pnl_usd"] == 0.0 and got["x8-nop"]["exit_reason"] == "expired_orphan_autoclosed"
           and all(v["status"] == "closed" for v in got.values()))
    d8 = str({k: (v["pnl_usd"], v["exit_reason"]) for k, v in got.items()})
except TypeError as exc:
    ok8, d8 = False, f"close_expired_open_trades has no settle: {exc}"
check("X8 boot Step 1 books ITM +$800, OTM -$200 (not 0.0), unpriceable flagged 0.0", ok8, d8)

# ── X12 the pre-existing close_phantom column bug (v4 port, 08-19) ───────────
try:
    TL.log_entry(make_record(trade_id="x12-rec", **long_itm))
    TL.close_phantom("x12-rec", reason="phantom_closed_at_broker_pnl_recovered", exit_price=1.55, pnl_usd=110.0)
    r12 = c.execute("select exit_premium,pnl_usd,status from trades where trade_id='x12-rec'").fetchone()
    ok12, d12 = (r12 is not None and r12["exit_premium"] == 1.55 and r12["pnl_usd"] == 110.0 and r12["status"] == "closed"), str(dict(r12) if r12 else None)
except Exception as exc:
    ok12, d12 = False, f"{type(exc).__name__}: {exc}"
check("X12 a RECOVERED phantom fill books (exit_premium + pnl), no OperationalError", ok12, d12)

# ── X9 / X10 the main.py hooks ───────────────────────────────────────────────
import main                                                             # noqa: E402
class Rec:
    def __init__(self): self.calls = []
    def close_phantom(self, rid, reason="", exit_price=None, pnl_usd=None):
        self.calls.append((rid, reason, exit_price, pnl_usd))
main._settlement_spot = lambda s, e: 705.0
r9 = Rec()
main._close_phantom_with_recovery(r9, dict(long_itm, trade_id="x9-exp"), [], "phantom_closed_at_broker")
future = (dt.datetime.now(ET) + dt.timedelta(days=5)).strftime("%Y-%m-%d")
main._close_phantom_with_recovery(r9, dict(long_itm, trade_id="x9-pre", expiry=future), [], "phantom_closed_at_broker")
c9 = {c[0]: c for c in r9.calls}
check("X9 an expired phantom settles (+$800); a pre-expiry phantom stays flagged $0.00 unknown",
      c9.get("x9-exp", (0, "", None, None))[3] == 800.0 and "expired_itm_exercised" in c9["x9-exp"][1]
      and c9.get("x9-pre", (0, "", 1, 1))[2:] == (None, None), str(r9.calls))

PAGES = []
main.get_alert_manager = lambda: types.SimpleNamespace(
    send_exercise_footprint_alert=lambda inst, eq, notional=0.0: PAGES.append((inst, eq)))
tc = types.ModuleType("data.tasty_client")
tc.get_open_equity_positions = lambda: [{"symbol": "QQQ", "quantity": 400, "direction": "Long"},
                                        {"symbol": "AAPL", "quantity": 10, "direction": "Long"}]
sys.modules["data.tasty_client"] = tc
mq = types.ModuleType("data.market_data"); mq.fetch_quote = lambda s: 705.0
sys.modules["data.market_data"] = mq
ok10 = hasattr(main, "_check_exercise_footprint")
if ok10:
    main._check_exercise_footprint("QQQ")
    one = list(PAGES)
    tc.get_open_equity_positions = lambda: []
    main._check_exercise_footprint("QQQ")
    def boom(): raise RuntimeError("broker down")
    tc.get_open_equity_positions = boom
    main._check_exercise_footprint("QQQ")
    ok10 = len(one) == 1 and one[0][1] == [{"symbol": "QQQ", "quantity": 400, "direction": "Long"}] and len(PAGES) == 1
check("X10 QQQ shares page once, other symbols ignored, empty/failed reads page nothing", ok10, str(PAGES))

# ── X11 hop 0 ─────────────────────────────────────────────────────────────────
src = open(os.path.join(ROOT, "main.py")).read(); t = ast.parse(src)
calls = {(n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", ""), tuple(k.arg for k in n.keywords),
          getattr(f, "name", "")) for f in ast.walk(t) if isinstance(f, ast.FunctionDef)
         for n in ast.walk(f) if isinstance(n, ast.Call)}
step1 = any(c[0] == "close_expired_open_trades" and "settle" in c[1] and c[2] == "_recover_open_position" for c in calls)
recon = any(c[0] == "_check_exercise_footprint" and c[2] == "_reconcile_with_broker" for c in calls)
check("X11 boot Step 1 passes settle=, and the broker reconcile checks for shares", step1 and recon,
      f"step1={step1} reconcile={recon}")

print()
if FAIL:
    print(f"RED - {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN - expired positions book their settlement; shares page")
sys.exit(0)
