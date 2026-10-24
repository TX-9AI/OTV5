#!/usr/bin/env python3
"""
tools/emergency_watchdog.py  v1.2 — THE OUT-OF-PROCESS EMERGENCY WATCHDOG.

v1.2  2026-10-11  OTV4TEST r268 (DEP.12, mirror of otv4 r478) — HALF DAYS. WINDOW's end, CLOSE_AT and CLOSE_END move to
      the day's bell through _at() (utils/market_calendar.close_shift_minutes): on a 13:00 close it flattens 12:50-13:00
      and idles from 13:05. WINDOW's 09:30 start is raw. _at() is byte-identical to otv4's.

v1.1  2026-10-04  OTV4TEST r242 (LIVE.1 B0, FORK-ONLY) — cancel_working() called account.get_live_orders /
      delete_order bare; on tastytrade 13.x those are coroutines, so on a LIVE box the 15:50 watchdog
      could cancel nothing. Both now go through tasty_client.sdk_result. Found by check_sdk_async A4
      (mirrored from otv4 r463) - mainline has no watchdog, so this half is this tree's alone.

v1.0  2026-09-27  OTV4TEST r168 (EXP.1 item 3). Operator, 2026-09-27: *"Not a
      bad idea to have one for 'emergencies'"*; asked what it should do when the
      bot is dead or stuck with a position open: **"Page, then close at 15:50"**;
      whether a dead bot with NO position is an emergency: **"No, positions
      only"**; and on the first build, which paged early and again on recovery:
      *"I already have a bot blind notification. I don't think i need a
      duplicate of that"* -> *"Keep it, as long as it's not a duplicate line of
      effort or I'll be getting multiple notifications for a single event"*.

WHAT IT COVERS THAT NOTHING ELSE DID. systemd restarts a CRASHED bot in 30s;
the bot pages its own blindness and its own shutdown. The uncovered case is
the bot ALIVE BUT STUCK (a hung call, a wedged loop) or DOWN AND NOT COMING
BACK while a position is open: it cannot page about itself, and its own
end-of-day close never runs. This runs in its own process from its own timer.

THE RULE, EVERY MINUTE ON A TRADING DAY 09:30-16:05 ET:
  healthy  = the bot's service is `active` AND its heartbeat (data/BOT_HEARTBEAT,
             touched at the top of every main-loop pass) is <= 180s old — or the
             process started < 300s ago (a boot is not a hang).
  Before 15:50 it WATCHES AND SAYS NOTHING (the ruling: no duplicate of the
  bot's own alerts). From 15:50 to 16:00, unhealthy on two consecutive
  minutes with a position open: THE EMERGENCY CLOSE, once a day —
    1. STOP the bot HARD (SIGKILL, then `systemctl stop` inside the 30s restart
       delay so systemd does not bring it back). Hard, because the bot's
       SIGTERM handler exists only to send a STOPPED page — a second message
       for this event. A bot that will not die is never closed beside: nothing
       is sent to the broker and the one page says close by hand.
    2. live only: cancel the instrument's working broker orders.
    3. run the bot's OWN end-of-day close (position_manager.flatten_all — the
       same ladder, the same $0.00 rule, the same 15:55 cross, the same booking)
       every 15s until flat or 16:00.
    4. ONE page: why, each position closed with its P&L, anything still open.
  The bot is NOT restarted (its startup page would be a second message); it
  starts at the next boot, and the page says so.

🔑 ONE EVENT, ONE MESSAGE — HOW. The bot's code running in THIS process
(flatten_all -> exit alerts) would page every close. load_env() therefore takes
TELEGRAM_TOKEN / TELEGRAM_CHAT_ID OUT of this process's environment and keeps
them for the watchdog's own sender alone; config reads them at call time, so
every AlertManager built here is disabled.

⚠️ WHY A HEARTBEAT FILE AND NOT bot.log's AGE. Measured 09-14..09-25: bot.log
went silent for 703-1208s at 15:39-15:41 ET on 09-18, 09-21 and 09-23 — the
very window this acts in. A log-age rule would have called a quiet bot stuck.
Ticks average 15.1s (900 twenty-tick windows; the slowest averaged 21.9s), so
180s is twelve ticks of margin.
⚠️ THE BOT'S ENVIRONMENT IS READ AT RUN TIME (`systemctl show <svc> -p
Environment`), never copied at install: configure.sh edits the unit, and a
stale copy would close a LIVE book as paper. Nothing here prints a value.
~~⚠️ HALF DAYS ARE NOT MODELLED, as everywhere in this tree (market_calendar).~~ Modelled since r268 (DEP.12): _at().
⚠️ THE WHOLE BOX DOWN IS NOT COVERED: nothing on the box can page then.
⚠️ A DELIBERATE STOP with a position still open at 15:50 is closed like a hang.
⚠️ ALWAYS EXITS 0: a red here is a page, not a failed unit.

Run:  venv/bin/python tools/emergency_watchdog.py            (the timer's call)
      venv/bin/python tools/emergency_watchdog.py --status   (read-only: what it sees; no values)
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import shlex
import sqlite3
import subprocess
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ET = ZoneInfo("America/New_York")
HEARTBEAT = os.path.join(ROOT, "data", "BOT_HEARTBEAT")
STATE = os.path.join(ROOT, "data", "emergency_watchdog.json")
SERVICE = os.environ.get("OT_BOT_SERVICE", "optionsbot")

STALE_S = 180          # heartbeat older than this = stuck
BOOT_GRACE_S = 300     # a process younger than this is starting, not stuck
WINDOW = (dt.time(9, 30), dt.time(16, 5))
CLOSE_AT = dt.time(15, 50)
CLOSE_END = dt.time(16, 0)
PASS_S = 15            # one flatten pass per tick, as the bot does
LIVE_STATES = {"Received", "Routed", "In Flight", "Live", "Contingent"}
_TG_KEYS = ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID")


def _log(msg: str) -> None:
    print(f"{dt.datetime.now(ET):%Y-%m-%d %H:%M:%S} ET  {msg}", flush=True)


# ── the real world ──────────────────────────────────────────────────────────
class Real:
    """Every side effect, in one place, so the gate can replace all of them."""

    def __init__(self):
        self.env = {}
        self._tg = {}

    def now(self) -> dt.datetime:
        return dt.datetime.now(ET)

    def trading_day(self, d: dt.date) -> bool:
        from utils.market_calendar import is_trading_day
        return is_trading_day(d)

    def _sysctl(self, *args) -> str:
        r = subprocess.run(["systemctl", *args], capture_output=True, text=True, timeout=20)
        return (r.stdout or "").strip()

    def load_env(self) -> dict:
        """The bot unit's Environment=, applied to this process — EXCEPT the
        Telegram pair, which only this watchdog's sender keeps. Never printed."""
        raw = self._sysctl("show", SERVICE, "-p", "Environment", "--value")
        env = {}
        for tok in shlex.split(raw):
            k, sep, v = tok.partition("=")
            if sep and k:
                env[k] = v
        self._tg = {k: env.get(k) or os.environ.get(k, "") for k in _TG_KEYS}
        os.environ.update({k: v for k, v in env.items() if k not in _TG_KEYS})
        for k in _TG_KEYS:
            os.environ.pop(k, None)             # the bot's code here cannot page
        self.env = env
        return env

    def service_state(self) -> str:
        return self._sysctl("is-active", SERVICE) or "unknown"

    def process_age_s(self):
        v = self._sysctl("show", SERVICE, "-p", "ExecMainStartTimestampMonotonic", "--value")
        try:
            started = int(v) / 1e6
        except ValueError:
            return None
        if started <= 0:
            return None
        return time.monotonic() - started

    def heartbeat_age_s(self):
        try:
            return time.time() - os.path.getmtime(HEARTBEAT)
        except OSError:
            return None

    def paper(self) -> bool:
        return os.environ.get("OT_PAPER_TRADING", "True") != "False"

    def _db(self):
        db = os.environ.get("OT_TRADES_DB") or os.path.expanduser("~/options-trader/trades.db")
        return sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)

    def open_positions(self) -> list:
        con = self._db()
        try:
            rows = con.execute(
                "SELECT trade_id, strategy FROM trades WHERE status='open' "
                "AND COALESCE(paper_trade,1)=?", (1 if self.paper() else 0,)).fetchall()
        finally:
            con.close()
        return [f"{r[1]} {str(r[0])[:8]}" for r in rows]

    def outcomes(self, opened: list) -> list:
        """'<strategy> <id8> <pnl>' for each position this close set out to shut."""
        con = self._db()
        out = []
        try:
            for o in opened:
                sid = o.split()[-1]
                r = con.execute("SELECT status, pnl_usd FROM trades WHERE trade_id LIKE ?",
                                (sid + "%",)).fetchone()
                if r and r[0] == "closed" and r[1] is not None:
                    out.append(f"{o} {r[1]:+,.0f}")
                else:
                    out.append(f"{o} STILL OPEN")
        finally:
            con.close()
        return out

    def page(self, msg: str) -> bool:
        _log("PAGE: " + msg)
        tok, chat = self._tg.get("TELEGRAM_TOKEN"), self._tg.get("TELEGRAM_CHAT_ID")
        if not (tok and chat):
            _log("page NOT SENT - Telegram is not configured on the bot unit")
            return False
        try:
            body = json.dumps({"chat_id": chat, "text": html.escape(msg, quote=False)[:4096],
                               "parse_mode": "HTML"}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as exc:                                  # noqa: BLE001
            _log(f"page FAILED ({type(exc).__name__})")
            return False

    def stop_bot(self) -> bool:
        """SIGKILL (the SIGTERM handler would page), then stop inside the 30s
        restart delay so systemd leaves it down."""
        subprocess.run(["sudo", "-n", "systemctl", "kill", "--signal=KILL", SERVICE], timeout=30)
        time.sleep(2)
        subprocess.run(["sudo", "-n", "systemctl", "stop", SERVICE], timeout=60)
        return self.service_state() in ("inactive", "failed")

    def cancel_working(self) -> int:
        from data.tasty_client import get_session, get_account, sdk_result
        inst = os.environ.get("OT_INSTRUMENT", "")
        session, account = get_session(), get_account()
        n = 0
        for o in sdk_result(account.get_live_orders(session)):            # r242 B0
            st = getattr(getattr(o, "status", None), "value", str(getattr(o, "status", "")))
            if st not in LIVE_STATES:
                continue
            legs = [str(getattr(lg, "symbol", "")) for lg in (getattr(o, "legs", None) or [])]
            if getattr(o, "underlying_symbol", None) != inst and not any(s.split()[0] == inst for s in legs if s):
                continue
            sdk_result(account.delete_order(session, o.id))                    # r242 B0
            _log(f"cancelled working order {o.id} ({st})")
            n += 1
        return n

    def flatten_pass(self) -> list:
        """One pass of the bot's own end-of-day close; the still-open ids."""
        from execution.position_manager import get_position_manager
        pm = get_position_manager(self.paper())
        chain = None
        try:
            from data.options_chain import get_chain_fetcher
            chain = get_chain_fetcher().fetch_chain()
        except Exception as exc:                                  # noqa: BLE001
            _log(f"chain fetch failed ({type(exc).__name__}); pass runs without marks")
        pm.has_open_position()                  # a fresh process loads the open rows
        pm.flatten_all(reason="emergency_watchdog", chain=chain, spot=None)
        # ⚠️ THE ANSWER IS trades.db, READ FRESH - and _open_records is NEVER
        # reassigned: a live close's working order id rides in the record
        # dict between passes, and a reload would drop it mid-walk.
        return [str(r.get("trade_id", ""))[:8] for r in pm._trade_logger.get_open_trades()]

    def sleep(self, s: float) -> None:
        time.sleep(s)

    def load_state(self) -> dict:
        try:
            with open(STATE) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def save_state(self, st: dict) -> None:
        tmp = STATE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(st, f)
        os.replace(tmp, STATE)


# ── the judgement ───────────────────────────────────────────────────────────
def health(w) -> tuple:
    """(healthy, why). Starting counts as healthy; unknown counts as not."""
    svc = w.service_state()
    if svc != "active":
        return False, f"service {svc}"
    age = w.process_age_s()
    if age is not None and age < BOOT_GRACE_S:
        return True, f"starting ({age:.0f}s)"
    hb = w.heartbeat_age_s()
    if hb is None:
        return False, "no heartbeat file"
    if hb > STALE_S:
        return False, f"heartbeat {hb:.0f}s old (stuck)"
    return True, f"heartbeat {hb:.0f}s"


def _at(t: dt.time, now: dt.datetime) -> dt.time:
    """r478 / DEP.12 — a 16:00-bell time moved to `now`'s bell (15:50 -> 12:50 on a
    13:00 close). CLOSE SIDE ONLY. Fails toward a FULL day: the pre-r478 times."""
    try:
        from utils.market_calendar import close_shift_minutes
        sh = int(close_shift_minutes(now.date()))
    except Exception:                                             # noqa: BLE001
        sh = 0
    m = max(0, t.hour * 60 + t.minute - sh)
    return dt.time(m // 60, m % 60)


def run_once(w) -> str:
    """One timer firing. Returns a one-word verdict for the log and the gate.
    ⚠️ PAGES ONLY FROM emergency_close, ONCE PER EVENT (the ruling)."""
    now = w.now()
    st = w.load_state()
    if st.get("date") != now.date().isoformat():
        st = {"date": now.date().isoformat()}
    if not w.trading_day(now.date()) or not (WINDOW[0] <= now.time() < _at(WINDOW[1], now)):
        return "idle"
    w.load_env()
    ok, why = health(w)
    try:
        opened = w.open_positions()
    except Exception as exc:                                      # noqa: BLE001
        _log(f"trades.db unreadable ({type(exc).__name__}) - nothing to act on")
        opened = []
    if ok or not opened:
        st.pop("unhealthy_since", None)
        w.save_state(st)
        return "ok" if ok else "flat"

    first = st.setdefault("unhealthy_since", now.isoformat())
    seen_twice = first != now.isoformat()
    _log(f"UNHEALTHY ({why}) with {len(opened)} open: {', '.join(opened)}")
    if (seen_twice and _at(CLOSE_AT, now) <= now.time() < _at(CLOSE_END, now)
            and not st.get("closed")):
        st["closed"] = True                     # once a day, whatever happens next
        w.save_state(st)
        return emergency_close(w, os.environ.get("OT_INSTRUMENT", "?"),
                               "PAPER" if w.paper() else "LIVE", opened, why)
    w.save_state(st)
    return "unhealthy" if seen_twice else "watching"


def emergency_close(w, inst: str, mode: str, opened: list, why: str) -> str:
    """Stop, cancel, close, then ONE page. Every branch ends in exactly one."""
    head = f"\U0001F6A8 {inst} {mode} EMERGENCY CLOSE - the bot was {why} at {w.now():%H:%M} ET"
    if not w.stop_bot():
        w.page(f"{head}. It WOULD NOT STOP ({w.service_state()}), so NOTHING WAS SENT. "
               f"CLOSE BY HAND NOW: {', '.join(opened)}")
        return "stop_failed"
    notes = []
    if mode == "LIVE":
        try:
            _log(f"{w.cancel_working()} working order(s) cancelled")
        except Exception as exc:                                  # noqa: BLE001
            notes.append(f"cancelling working orders FAILED ({type(exc).__name__}) - check the order book")
    left = list(opened)
    while True:
        try:
            left = w.flatten_pass()
        except Exception as exc:                                  # noqa: BLE001
            _log(f"flatten pass raised {type(exc).__name__}: {exc}")
        _n = w.now()
        if not left or _n.time() >= _at(CLOSE_END, _n):
            break
        w.sleep(PASS_S)
    try:
        lines = w.outcomes(opened)
    except Exception as exc:                                      # noqa: BLE001
        lines = [f"{o} (outcome unreadable: {type(exc).__name__})" for o in opened]
    verdict = "closed" if not left else "incomplete"
    tail = ("FLAT." if not left else f"{len(left)} STILL OPEN - CLOSE BY HAND.")
    w.page(f"{head}. Stopped it and closed: " + "; ".join(lines) + f". {tail} "
           + (" ".join(notes) + " " if notes else "")
           + "The bot stays stopped until the next boot.")
    return verdict


def status(w) -> int:
    """Read-only: what the watchdog would see right now. Prints no env value."""
    now = w.now()
    env = w.load_env()
    ok, why = health(w)
    print(f"now            {now:%Y-%m-%d %H:%M:%S} ET  trading day: {w.trading_day(now.date())}")
    print(f"service        {SERVICE}: {w.service_state()}")
    print(f"environment    {len(env)} keys read; instrument {os.environ.get('OT_INSTRUMENT', '?')}; "
          f"{'PAPER' if w.paper() else 'LIVE'}; telegram "
          f"{'set' if all(w._tg.get(k) for k in _TG_KEYS) else 'MISSING'}")
    print(f"health         {'healthy' if ok else 'UNHEALTHY'} ({why})")
    try:
        op = w.open_positions()
        print(f"open           {len(op)} {', '.join(op)}")
    except Exception as exc:                                      # noqa: BLE001
        print(f"open           UNREADABLE ({type(exc).__name__})")
    print(f"state          {w.load_state()}")
    return 0


def main(argv) -> int:
    w = Real()
    if "--status" in argv:
        return status(w)
    try:
        _log(f"verdict: {run_once(w)}")
    except Exception as exc:                                      # noqa: BLE001
        _log(f"watchdog raised {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
