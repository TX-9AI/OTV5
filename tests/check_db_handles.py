"""tests/check_db_handles.py — v1.0
EVERY STORE CONNECTION THE BOT OPENS IS CLOSED, AND A FAILED HEARTBEAT READ SAYS SO.

v1.0  2026-09-25 — OTV4TEST r143. `with conn:` on a sqlite3 connection COMMITS
      and does NOT close it; trade_logger (22 sites) and resting_orders (5) used
      exactly that, and the connections sit in a reference cycle, so each call's
      file handle stayed open until the cyclic GC ran. MEASURED on the live
      processes 2026-09-25: AAL 511 handles on trades.db, SOFI 219, this box 137,
      +~8/min against a 1024 soft limit. At the limit every open failed - AAL went
      blind three times (~23 min) and its first failing path was
      update_current_premium inside POSITION MANAGEMENT. The heartbeat check
      swallowed the error and logged HEARTBEAT_STALE while the heartbeat was 0.4s
      old, which cost a day of looking at the feed.

  THE GC IS DISABLED for H1/H2, because the leak's whole character is that only
  the cyclic collector frees these handles: a check that let it run could pass
  on the broken code by luck of timing.

  H1  trade_logger: 150 each of log_entry / update_current_premium /
      get_open_trades / count_today / realized_pnl_today / _get_field hold the
      open handles on the scratch trades.db flat (<= 1)
  H2  resting_orders: 150 each of record_placement / working (the reader) /
      note_seen_qty, and a close_out, hold the resting store's handles flat (<= 1)
  H3  behaviour is unchanged: a written premium reads back from a NEW
      connection (committed), and the open trade is returned
  H4  an exception inside `_db()` ROLLS BACK and still closes
  H5  a heartbeat read that RAISES is reported as a read failure with its
      exception text, not as an old heartbeat; an old heartbeat reports its age
  H6  no `with self._connect() as` / `with _conn() as` statement remains in either
      module (code lines only - comments that name the old form do not count)
"""
from __future__ import annotations

import gc
import os
import re
import sqlite3
import sys
import tempfile

import glob as _glob
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
sys.path.insert(0, _root)

_s = tempfile.mkdtemp(prefix="check_db_handles_",
                      dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
TR = os.path.join(_s, "trades.db")
RE = os.path.join(_s, "resting.db")
os.environ["OT_TRADES_DB"] = TR
os.environ["OT_RESTING_DB"] = RE
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
os.environ.setdefault("OT_PAPER_TRADING", "1")

FAIL: list = []
N = 150


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


def premium_on_disk(tid):
    """current_premium as a FRESH connection sees it, or None if the row is not
    there at all (i.e. nothing was committed) - never a crash."""
    c = sqlite3.connect(TR)
    try:
        r = c.execute("SELECT current_premium FROM trades WHERE trade_id=?", (tid,)).fetchone()
    finally:
        c.close()
    return None if r is None else r[0]


def fds(path):
    rp = os.path.realpath(path)
    n = 0
    for f in os.listdir("/proc/self/fd"):
        try:
            if os.path.realpath(f"/proc/self/fd/{f}") == rp:
                n += 1
        except OSError:
            pass
    return n


from database.trade_logger import TradeLogger, make_record      # noqa: E402

gc.collect()
gc.disable()
try:
    # ── H1 ────────────────────────────────────────────────────────────────
    tl = TradeLogger(db_path=TR, paper_trading=True)
    tl.log_entry(make_record(trade_id="h1", symbol="QQQ", strategy="Breakout",
                             direction="long", paper_trade=1))
    before = fds(TR)
    for i in range(N):
        tl.update_current_premium("h1", 1.0 + i / 1000)
        tl.get_open_trades()
        tl.count_today("Breakout")
        tl.realized_pnl_today()
        tl._get_field("h1", "symbol")
    for i in range(N):
        tl.log_entry(make_record(trade_id=f"h1-{i}", symbol="QQQ", strategy="VOLT",
                                 direction="short", paper_trade=1))
    after = fds(TR)
    check(f"H1 trade_logger: {N * 6} calls leave the trades.db handles flat",
          after <= max(before, 1), f"open handles {before} -> {after}")

    # ── H2 ────────────────────────────────────────────────────────────────
    from execution import resting_orders as ro
    ro.record_placement(order_id="o0", session_date="2026-09-25", strategy="ORBStrategy",
                        symbol="QQQ", underlying="QQQ", side="call", strike=745.0,
                        offered_qty=1, offer_price=1.0)
    before = fds(RE)
    for i in range(N):
        ro.record_placement(order_id=f"o{i + 1}", session_date="2026-09-25",
                            strategy="ORBStrategy", symbol="QQQ", underlying="QQQ",
                            side="call", strike=745.0, offered_qty=1, offer_price=1.0)
        ro.working("2026-09-25")                      # the reader
        ro.note_seen_qty(f"o{i + 1}", 1)              # an update
    ro.close_out("o1", "cancelled", "check")          # the close path
    after = fds(RE)
    check(f"H2 resting_orders: {N} each of record_placement / working / note_seen_qty leave the handles flat",
          after <= max(before, 1), f"open handles {before} -> {after}")

    # ── H3 ────────────────────────────────────────────────────────────────
    tl.update_current_premium("h1", 2.345)
    v = premium_on_disk("h1")
    check("H3 a write is COMMITTED - a fresh connection reads it back",
          v is not None and abs(float(v) - 2.345) < 1e-9,
          f"read {v}" if v is not None else "row absent on disk - nothing was committed")
    check("H3b get_open_trades still returns the open trade",
          any(r["trade_id"] == "h1" for r in tl.get_open_trades()))

    # ── H4 ────────────────────────────────────────────────────────────────
    _db = getattr(tl, "_db", None)
    if _db is None:
        check("H4 an exception inside _db() rolls back and closes", False,
              "TradeLogger._db does not exist (pre-r143)")
    else:
        before = fds(TR)
        try:
            with _db() as conn:
                conn.execute("UPDATE trades SET current_premium=9.99 WHERE trade_id='h1'")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        v = premium_on_disk("h1")
        check("H4 an exception inside _db() ROLLS BACK and still closes",
              v is not None and abs(float(v) - 2.345) < 1e-9 and fds(TR) <= before,
              f"premium {v}, handles {before} -> {fds(TR)}")
finally:
    gc.enable()

# ── H5 ────────────────────────────────────────────────────────────────────
from data import market_data as md                              # noqa: E402
bad = sqlite3.connect(":memory:")                               # no feed_meta table
ok = md._feed_alive(bad)
why = (getattr(md, "_ALIVE_WHY", None) or {}).get("why", "<no _ALIVE_WHY>")
check("H5 a heartbeat read that RAISES is reported as a read failure, with the error",
      ok is False and "READ FAILED" in why and "no such table" in why, repr(why))
old = sqlite3.connect(":memory:")
old.execute("CREATE TABLE feed_meta (symbol TEXT, interval TEXT, last_write_epoch REAL)")
import time as _t
old.execute("INSERT INTO feed_meta VALUES ('__feed__','heartbeat',?)", (_t.time() - 600,))
ok = md._feed_alive(old)
why = (getattr(md, "_ALIVE_WHY", None) or {}).get("why", "<no _ALIVE_WHY>")
check("H5b an OLD heartbeat reports its age, not a read failure",
      ok is False and re.search(r"heartbeat \d+s old", why or "") is not None, repr(why))

# ── H6 ────────────────────────────────────────────────────────────────────
left = []
for rel, pat in (("database/trade_logger.py", r"^\s+with self\._connect\(\) as "),
                 ("execution/resting_orders.py", r"^\s+with _conn\(\) as ")):
    for i, line in enumerate(open(os.path.join(_root, rel)), 1):
        if re.match(pat, line):
            left.append(f"{rel}:{i}")
check("H6 no block-form connect that commits without closing remains", not left,
      ", ".join(left[:6]))

print(f"\n{'GREEN' if not FAIL else 'RED'} — {len(FAIL)} failed" + (f": {FAIL}" if FAIL else ""))
sys.exit(1 if FAIL else 0)
