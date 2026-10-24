#!/usr/bin/env python3
"""
tests/check_loss_cap_rearm.py  v1.1

The DAILY CATASTROPHIC LOSS CAP stops NEW entries while the day's REALIZED net
is at or beyond -limit, never touches open positions, and RE-OPENS entries
once closes bring the loss back under the limit.

v1.1  2026-10-03  OTV4TEST r199 (AUD.7). C9: every cap transition leaves a row in
      circuit_breaker_events (log_circuit_breaker had zero callers). C10: a cap page
      that cannot be sent warns instead of passing silently.

v1.0  2026-09-27  OTV4TEST r162 (CAP.1). The operator, 2026-09-27: "Manage
      what's open but no new entries. If the open TRADES put us back under the
      limit again after they close, it can open trades again." and "Under the
      limit." Until r162 RiskManager.is_halted() LATCHED for the rest of the day
      once breached - while reset_session(), run on every restart, re-derived it
      from the DB, so a restart un-halted a recovered day and a running process
      did not.

WHAT IT DRIVES (WA 21): the REAL RiskManager.is_halted / reset_session /
day_realized_pnl over the REAL TradeLogger.realized_pnl_today, fed by that
logger's own closed-row hook (`_closed_today_rows`) - the only place a fixture
enters, and it is the shape the method sums (dicts with pnl_usd). The pager is a
RECORDER in place of notifications.alert_manager: nothing reaches Telegram.

  C1  -4000 (under a 5000 cap): entries open, no page
  C2  -5000 (AT the cap): halted, ONE page
  C3  -5300: still halted, still ONE page (WA 17: once per episode)
  C4  -4999 (a close brings it back under): entries RE-OPEN, logged, no page
  C5  -5001 later the same day: halted again, a SECOND page (a new episode)
  C6  +200: open
  C7  restart parity: a fresh manager's reset_session() agrees with is_halted()
      at -5100 (halted) and -4800 (open) - the two can no longer disagree
  C8  HOP 0: in main.py only attempt_new_entry calls is_halted(), and it returns
      before any entry - nothing on the exit / manage path reads the cap

BORN RED on 20ce062 (r161) at C4, C5 and C6, under both interpreters.

Run:  python3 tests/check_loss_cap_rearm.py
"""

from __future__ import annotations

import ast
import atexit
import glob as _glob
import logging
import os
import shutil
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The lander runs CHECKs under the SYSTEM python3 (no pytz): borrow the repo
# venv's packages, check_volt_sizing's idiom (r161's refused first land).
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
sys.path.insert(0, ROOT)
if not os.environ.get("OT_TRADES_DB"):
    _scr = tempfile.mkdtemp(prefix="check_loss_cap_rearm_",
                            dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
    atexit.register(shutil.rmtree, _scr, True)
    os.environ["OT_TRADES_DB"] = os.path.join(_scr, "trades.db")
    os.environ["OT_DERIVED_DB"] = os.path.join(_scr, "derived_store.db")
    os.environ["OT_RESTING_DB"] = os.path.join(_scr, "resting.db")
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_PAPER_TRADING"] = "1"
os.environ["OT_RISK_USD"] = "1050"
os.environ["OT_DAILY_LOSS_LIMIT"] = "5000"

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


print("=" * 68)
print("DAILY CATASTROPHIC LOSS CAP: halt at the limit, re-open under it")
print("=" * 68)

# ── the pager is a recorder: nothing may reach the real alert channel ──────
PAGES: list = []
_fake = types.ModuleType("notifications.alert_manager")
_fake.get_alert_manager = lambda: types.SimpleNamespace(_send=lambda msg: PAGES.append(msg))
sys.modules["notifications.alert_manager"] = _fake


class _Logs(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


LOGS = _Logs()
logging.getLogger("risk.risk_manager").addHandler(LOGS)

from database import trade_logger as _tl                       # noqa: E402
from risk.risk_manager import RiskManager                      # noqa: E402

TL = _tl.get_trade_logger()
REALIZED = {"rows": []}
TL._closed_today_rows = lambda: REALIZED["rows"]               # the one fixture seam


def day(net):
    """Today's CLOSED trades, as the logger's own row shape, summing to `net`."""
    REALIZED["rows"] = [{"pnl_usd": float(net)}]


RM = RiskManager(risk_per_trade=1050.0, paper_trading=True)
LIMIT = RM._daily_loss_limit
check("C0 the cap under test is the configured 5000", LIMIT == 5000.0, f"limit={LIMIT}")

day(-4000)
check("C1 -4000: entries open, no page", RM.is_halted() is False and len(PAGES) == 0,
      f"halted={RM._session_halted} pages={len(PAGES)}")
day(-5000)
check("C2 -5000 (AT the cap): halted, one page", RM.is_halted() is True and len(PAGES) == 1,
      f"halted={RM._session_halted} pages={len(PAGES)}")
day(-5300)
check("C3 -5300: still halted, still one page", RM.is_halted() is True and len(PAGES) == 1,
      f"halted={RM._session_halted} pages={len(PAGES)}")
day(-4999)
_n = len(LOGS.lines)
h = RM.is_halted()
check("C4 -4999 (back under): entries RE-OPEN, logged, no page",
      h is False and len(PAGES) == 1 and any("RE-ARMED" in l for l in LOGS.lines[_n:]),
      f"halted={h} pages={len(PAGES)} logged={[l[:60] for l in LOGS.lines[_n:]]}")
day(-5001)
check("C5 -5001 later: halted again, a SECOND page (new episode)",
      RM.is_halted() is True and len(PAGES) == 2,
      f"halted={RM._session_halted} pages={len(PAGES)}")
day(200)
check("C6 +200: open", RM.is_halted() is False, f"halted={RM._session_halted}")

for net, want in ((-5100, True), (-4800, False)):
    day(net)
    fresh = RiskManager(risk_per_trade=1050.0, paper_trading=True)
    fresh.reset_session()
    after_reset = fresh._session_halted
    check(f"C7 restart at {net}: reset_session and is_halted agree ({want})",
          after_reset is want and fresh.is_halted() is want,
          f"reset={after_reset} is_halted={fresh.is_halted()}")

# ── C9 (r199) — every transition above left a row in circuit_breaker_events ──
# C2 hit, C4 re-armed, C5 hit again, C6 re-armed: four rows, in that order, each
# carrying the day's realized figure. Read from the scratch trades.db the REAL
# TradeLogger wrote.
try:
    import sqlite3 as _sq
    _con = _sq.connect(os.environ["OT_TRADES_DB"])
    _ev = [(r[0], r[1]) for r in _con.execute(
        "SELECT reason, notes FROM circuit_breaker_events ORDER BY id")]
    _con.close()
except Exception as _exc:                                      # noqa: BLE001
    _ev = [("<unreadable>", f"{type(_exc).__name__}: {_exc}")]
check("C9 the cap's transitions are RECORDED: hit, re-armed, hit, re-armed - with the day's figure",
      [e[0] for e in _ev] == ["daily_cap_hit", "daily_cap_rearmed", "daily_cap_hit", "daily_cap_rearmed"]
      and "-5000.00" in _ev[0][1] and "-4999.00" in _ev[1][1],
      f"events={_ev}")

# C10 — a page that fails to send is SAID (it was `except: pass`)
_fake.get_alert_manager = lambda: (_ for _ in ()).throw(RuntimeError("telegram down"))
LOGS.lines.clear()
day(-6000)
_h10 = RM.is_halted()
check("C10 a cap page that cannot be sent WARNS, and the halt still holds",
      _h10 is True and any("cap page NOT sent" in ln for ln in LOGS.lines),
      f"halted={_h10} lines={[ln[:60] for ln in LOGS.lines][-3:]}")
_fake.get_alert_manager = lambda: types.SimpleNamespace(_send=lambda msg: PAGES.append(msg))

# ── C8 — HOP 0: only the entry path reads the cap ───────────────────────────
_t = ast.parse(open(os.path.join(ROOT, "main.py")).read())
callers = set()
for f in ast.walk(_t):
    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for n in ast.walk(f):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "is_halted"):
                callers.add(f.name)
check("C8 in main.py only attempt_new_entry reads is_halted() - exits never do",
      callers == {"attempt_new_entry"}, f"callers={sorted(callers)}")

print()
if FAIL:
    print(f"RED — {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN — halts at the cap, re-opens under it, pages once per episode")
sys.exit(0)
