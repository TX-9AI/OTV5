#!/usr/bin/env python3
"""
tests/check_cap_page_once.py  v1.0

The DAILY CATASTROPHIC LOSS CAP pages ONCE PER EPISODE, and a restart inside an
episode does not page it again.

v1.0  2026-09-30  OTV4TEST r181 (ALRT.2). 2026-09-29 16:01 ET the r175 restart
      re-sent the day's 11:08 cap page: a fresh process starts un-halted, reads
      the day's realized loss and sees a transition INTO the halt. The operator's
      rule (WDOG.1): no duplicate notifications for a single event.

WHAT IT DRIVES (WA 21): the REAL RiskManager.is_halted over the REAL
TradeLogger.realized_pnl_today, fed through the logger's own closed-row hook
(check_loss_cap_rearm's seam). "A restart" is a NEW RiskManager over the same
store. The pager is a recorder; the trades store and its stamp are scratch.

  P1  breach: one page, and the stamp says today's episode is open
  P2  a restart inside the episode: still halted, NO second page, and it says so
  P3  back under the limit in the restarted process: the stamp closes the episode
  P4  a later breach the same day is a NEW episode: it pages
  P5  a restart that comes up already back under the limit closes the episode,
      so the next breach pages (the episode ended while nobody watched)
  P6  yesterday's open stamp does not silence today's first page
  P7  an unreadable stamp does not silence a page
  P8  the stamp sits beside the trades store the P&L is read from (scratch here),
      never the live box's
  P9  CONTROL, the r162 shape inside one process is unchanged: a breach pages
      once, staying breached pages nothing more

BORN RED on 59ba004 (r178) under both interpreters at P1 and P8 (no stamp is
written) and P2 (the restart pages again - the 09-29 defect).

Run:  python3 tests/check_cap_page_once.py
"""
from __future__ import annotations

import glob as _glob
import logging
import os
import shutil
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _base in (ROOT, os.path.expanduser("~/options-trader")):
    _found = _glob.glob(os.path.join(_base, "venv", "lib", "python*", "site-packages"))
    for _sp in _found:
        if _sp not in sys.path:
            sys.path.insert(1, _sp)
    if _found:
        break
sys.path.insert(0, ROOT)

# Always its OWN scratch store: the stamp lands beside it.
_SCR = tempfile.mkdtemp(prefix="check_cap_page_once_",
                        dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
os.environ["OT_TRADES_DB"] = os.path.join(_SCR, "trades.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_SCR, "derived_store.db")
os.environ["OT_RESTING_DB"] = os.path.join(_SCR, "resting.db")
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_PAPER_TRADING"] = "1"
os.environ["OT_RISK_USD"] = "1050"
os.environ["OT_DAILY_LOSS_LIMIT"] = "5000"

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


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
TL._closed_today_rows = lambda: REALIZED["rows"]
STAMP = os.path.join(_SCR, "data", "CAP_PAGED")


def day(net):
    REALIZED["rows"] = [{"pnl_usd": float(net)}]


def stamp():
    try:
        return open(STAMP, encoding="utf-8").read().strip()
    except OSError:
        return None


def fresh():
    return RiskManager(risk_per_trade=1050.0, paper_trading=True)


TODAY = RiskManager._et_date() if hasattr(RiskManager, "_et_date") else "?"

A = fresh()
day(-5200)
h = A.is_halted()
check("P1 breach: one page, and the stamp says today's episode is open",
      h is True and len(PAGES) == 1 and stamp() == f"{TODAY}|1", f"pages={len(PAGES)} stamp={stamp()}")

B = fresh()                                    # the restart
_n = len(LOGS.lines)
h = B.is_halted()
check("P2 a restart inside the episode: still halted, NO second page, and it says so",
      h is True and len(PAGES) == 1 and any("not paged again" in l for l in LOGS.lines[_n:]),
      f"pages={len(PAGES)} logged={[l[:50] for l in LOGS.lines[_n:]]}")

day(-4000)
h = B.is_halted()
check("P3 back under the limit in the restarted process: the stamp closes the episode",
      h is False and stamp() == f"{TODAY}|0", f"halted={h} stamp={stamp()}")

day(-5100)
h = B.is_halted()
check("P4 a later breach the same day is a NEW episode: it pages",
      h is True and len(PAGES) == 2 and stamp() == f"{TODAY}|1", f"pages={len(PAGES)} stamp={stamp()}")

day(-3000)
C = fresh()                                    # restarts already back under
C.is_halted()
_closed = stamp() == f"{TODAY}|0"
day(-5300)
h = C.is_halted()
check("P5 a restart that comes up back under the limit closes the episode; the next breach pages",
      _closed and h is True and len(PAGES) == 3, f"closed={_closed} pages={len(PAGES)}")

os.makedirs(os.path.dirname(STAMP), exist_ok=True)
open(STAMP, "w").write("2026-01-02|1\n")
day(-5300)
h = fresh().is_halted()
check("P6 yesterday's open stamp does not silence today's first page",
      h is True and len(PAGES) == 4, f"pages={len(PAGES)}")

open(STAMP, "w").write("garbage")
h = fresh().is_halted()
check("P7 an unreadable stamp does not silence a page", h is True and len(PAGES) == 5,
      f"pages={len(PAGES)}")

_live = os.path.expanduser("~/options-trader/data/CAP_PAGED")
_p = fresh()._cap_stamp_path() if hasattr(RiskManager, "_cap_stamp_path") else None
check("P8 the stamp sits beside the trades store (scratch here), never the live box's",
      _p == STAMP and _p != _live and os.path.exists(STAMP), f"path={_p}")

D = fresh()
day(-4000)
D.is_halted()
_before = len(PAGES)
day(-5050)
D.is_halted()
D.is_halted()
D.is_halted()
check("P9 CONTROL: inside one process a breach pages once, staying breached pages nothing more",
      len(PAGES) == _before + 1, f"pages {_before}->{len(PAGES)}")

shutil.rmtree(_SCR, ignore_errors=True)
print()
if FAIL:
    print(f"RED — {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN — one cap page per episode, a restart inside it pages nothing")
sys.exit(0)
