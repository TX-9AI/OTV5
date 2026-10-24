#!/usr/bin/env python3
"""tools/agent_watch.py — v1.0
THE AGENT HEARS WHAT THE OPERATOR HEARS, AND WHAT HE NEVER GETS PAGED FOR.

v1.0 (2026-09-29) — OTV4TEST r171 (AGT.1). The operator, 2026-09-29: *"What if
      we made it so that you got the notification too?"*; on the list of
      alerts, *"I agree with the unusual behavior Alerts, and I don't think we
      need any routine Alerts"*; then *"start building and deploy the ALERT
      Notification to have you intervene when you get alerted"*. The day it
      was asked for, the bot went blind at 09:30-09:37 ET and the agent learned
      of it from a screenshot; a Breakout then entered 12 s after sight
      returned on a trigger that had fired during the blind window, and
      nothing paged anyone about THAT.

🔑 IT READS; IT NEVER TOUCHES THE BOT. Every page the operator receives is
already in `bot.log` as `ALERT: <text>` (alert_manager._send logs before it
sends); the disk guard logs `disk_watch: <sym> at N%`; the emergency watchdog
logs `PAGE: <text>` to its own unit's journal; and every loss is a row in
trades.db. So this is an OBSERVER outside the process, like the watchdog:
no bot change, no restart, nothing trading waits on (§29).

WHAT IT EMITS — one stdout line per event, which is what the agent's Monitor
wakes on (`AGENT-EVENT <SEVERITY> <kind> <HH:MM ET> | <text> | id=<id>`):
  URGENT   every page that is not on the ROUTINE list below, by default — an
           unknown alert WAKES rather than hides (a new page type must not be
           silent to the agent because nobody listed it)
  UNUSUAL  behaviour nobody is paged for: an entry inside a blind episode or
           within SIGHT_WINDOW_S after it ended; a debit loss beyond LOSS_OVER_PLAN x its
           planned premium risk; a second same-direction loss inside
           CLUSTER_S; a strategy with no exit route (once per strategy a day)
  LOSS     every closed losing trade — the agent's cue to read the tape and
           record an observe-only verdict (tools/agent_verdict.py)
  ROUTINE  entries, exits, credit fills, the daily summary, started/stopped,
           sight restored, reconcile unavailable, a resumed position: RECORDED
           in the events file and NEVER printed (the operator's ruling)

Every event, routine included, is appended to AGENT_EVENTS (JSONL) — the
record a later scoring reads. State (log inode/offset, trades already judged,
the journal cursor) lives in STATE, so a Monitor that expires after 30 min
and is re-armed resumes exactly where it stopped, and a session that starts
after a quiet night is told what fired while nobody watched.

⚠️ ONE WATCHER AT A TIME: an flock on STATE's lock; a second instance says so
and exits, rather than doubling every wake.
⚠️ NEVER SILENT ON ITS OWN FAILURE (§0.5): an exception in a scan is printed
once per kind as `AGENT-EVENT WATCH-ERROR`, and the loop keeps going.

Usage:
    python3 tools/agent_watch.py --follow      # the agent's Monitor command
    python3 tools/agent_watch.py --once        # one scan, print, exit
    python3 tools/agent_watch.py --tail 20     # the last 20 recorded events
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HOME = os.path.expanduser("~")

BOT_LOG = os.environ.get("OT_BOT_LOG") or os.path.join(_HOME, "options-trader", "bot.log")
TRADES_DB = os.environ.get("OT_TRADES_DB") or os.path.join(_HOME, "options-trader", "trades.db")
EVENTS = os.environ.get("OT_AGENT_EVENTS") or os.path.join(_root, "data", "AGENT_EVENTS.jsonl")
STATE = os.environ.get("OT_AGENT_WATCH_STATE") or os.path.join(_HOME, ".optbot", "agent_watch.json")
# The watchdog pages from its own unit; "" disables the journal source (the gate).
WDOG_UNIT = os.environ.get("OT_AGENT_WATCH_JOURNAL", "optbot-emergency-watchdog.service")

POLL_S = float(os.environ.get("OT_AGENT_WATCH_POLL_S", "5"))
CATCHUP_S = 12 * 3600          # a first run with no state looks back this far
LATE_S = 180                   # an event older than this when found is "while unwatched"
SIGHT_WINDOW_S = 600           # an entry this soon after sight restored is UNUSUAL
LOSS_OVER_PLAN = 1.25          # a debit loss beyond this x planned premium risk
CLUSTER_S = 1800               # two same-direction losses inside this window

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:                                               # noqa: BLE001
    _ET = timezone(timedelta(hours=-4))

# ── classification of a page ────────────────────────────────────────────────
# ROUTINE is an ALLOW-LIST of the operator's "no routine alerts". Pinned by
# check_agent_watch A1, which drives the REAL alert_manager methods and asserts
# each one's text lands here — so a reworded alert fails the gate instead of
# quietly starting to wake the agent (or, worse, quietly stopping).
ROUTINE = [
    ("startup", re.compile(r"OptionsBot \[\w+\] STARTED \|")),
    ("shutdown", re.compile(r"OptionsBot STOPPED \|")),
    ("resumed_position", re.compile(r"OptionsBot (CARRIED|RESUMED) POSITION")),
    ("reconcile_unavailable", re.compile(r"Broker reconcile unavailable")),
    ("sight_restored", re.compile(r"Sight restored")),
    ("entry", re.compile(r"^\S+ \[(PAPER|LIVE)\] \S+ (BUTTERFLY )?(CALL|PUT)\b")),
    ("credit_fill", re.compile(r"^\S+ \[(PAPER|LIVE)\] \S+ \| .* credit=\$")),
    ("exit", re.compile(r" CLOSED .* \| pnl=[+-]?\$")),
    ("daily_summary", re.compile(r"DAILY P&L \[")),
]
# Names only — anything not ROUTINE wakes, named or not.
URGENT_KIND = [
    ("blind", "BOT IS BLIND"), ("dispatch_failed", "DISPATCH FAILED"),
    ("cap_hit", "CATASTROPHIC LOSS CAP"), ("uncancellable_order", "could not be cancelled"),
    ("condor_roll", "ROLL"), ("phantom", "hantom"), ("adopted", "DOPT"),
    ("exercise", "xercise"), ("orphan", "rphan"), ("short_leg", "hort leg"),
    ("hard_close_failed", "ard close"),
]


def classify(msg: str) -> tuple[str, str]:
    """-> (severity, kind) for the text of one page."""
    for kind, rx in ROUTINE:
        if rx.search(msg):
            return "ROUTINE", kind
    for kind, needle in URGENT_KIND:
        if needle in msg:
            return "URGENT", kind
    return "URGENT", "alert"


# ── plumbing ────────────────────────────────────────────────────────────────
def _et(ts: float) -> str:
    return datetime.fromtimestamp(ts, _ET).strftime("%H:%M ET")


def _iso_ts(s) -> float | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.timestamp()
    except Exception:                                           # noqa: BLE001
        return None


_LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \[(\w+)\s*\] ([\w.]+): (.*)$")


def _log_ts(s: str) -> float:
    # bot.log stamps are the box's clock, which is UTC (measured: the 09:34 ET
    # BLIND alert is stamped 13:34:xx)
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def load_state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:                                           # noqa: BLE001
        return {}


def save_state(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh)
    os.replace(tmp, STATE)


class Watch:
    def __init__(self, now=time.time, out=None):
        self.now = now
        self.out = out or sys.stdout
        self.st = load_state()
        self.first = not self.st
        self.since = self.st.get("since") or (now() - CATCHUP_S)
        self.st.setdefault("since", self.since)
        self._errs = set()

    # every event goes through here
    def emit(self, ts: float, severity: str, kind: str, text: str, **extra) -> dict:
        self.st["seq"] = self.st.get("seq", 0) + 1
        ev = {"id": "E%s-%d" % (datetime.fromtimestamp(ts, timezone.utc).strftime("%Y%m%d%H%M%S"),
                                self.st["seq"]),
              "ts_utc": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
              "ts_et": datetime.fromtimestamp(ts, _ET).isoformat(),
              "severity": severity, "kind": kind, "text": text.strip()[:500]}
        ev.update({k: v for k, v in extra.items() if v is not None})
        late = self.now() - ts > LATE_S
        if late:
            ev["found_late"] = True
        try:
            os.makedirs(os.path.dirname(EVENTS), exist_ok=True)
            with open(EVENTS, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev) + "\n")
        except OSError as exc:
            self.error("events_write", exc)
        if severity != "ROUTINE":
            print("AGENT-EVENT %s %s %s%s | %s | id=%s"
                  % (severity, kind, _et(ts), " (while unwatched)" if late else "",
                     ev["text"].splitlines()[0][:220], ev["id"]), file=self.out, flush=True)
        return ev

    def error(self, where: str, exc: Exception) -> None:
        key = "%s:%s" % (where, type(exc).__name__)
        if key in self._errs:
            return
        self._errs.add(key)
        print("AGENT-EVENT WATCH-ERROR %s %s | %s: %s"
              % (where, _et(self.now()), type(exc).__name__, str(exc)[:160]),
              file=self.out, flush=True)

    # ── source 1: bot.log ───────────────────────────────────────────────────
    def _open_log(self):
        """-> list of (path, start_offset) to read, oldest first, following a
        rotation (RotatingFileHandler renames bot.log to bot.log.1)."""
        try:
            cur = os.stat(BOT_LOG)
        except OSError:
            return []
        ino, off = self.st.get("log_inode"), self.st.get("log_offset", 0)
        if ino == cur.st_ino and off <= cur.st_size:
            return [(BOT_LOG, off)]
        plan = []
        rot = BOT_LOG + ".1"
        try:
            r = os.stat(rot)
            if ino is not None and r.st_ino == ino and off <= r.st_size:
                plan.append((rot, off))
        except OSError:
            pass
        plan.append((BOT_LOG, 0))
        return plan

    def scan_log(self) -> None:
        for path, off in self._open_log():
            with open(path, "rb") as fh:
                fh.seek(off)
                data = fh.read()
                end = fh.tell()
            # only whole lines; a half-written tail is read next time
            cut = data.rfind(b"\n") + 1
            for raw in data[:cut].splitlines():
                self._log_line(raw.decode("utf-8", "replace"))
            if path == BOT_LOG:
                self.st["log_inode"] = os.stat(BOT_LOG).st_ino
                self.st["log_offset"] = end - (len(data) - cut)

    def _log_line(self, line: str) -> None:
        m = _LINE.match(line)
        if not m:
            return
        try:
            ts = _log_ts(m.group(1))
        except ValueError:
            return
        if ts < self.since:
            return
        level, src, msg = m.group(2), m.group(3), m.group(4)
        if msg.startswith("ALERT: "):
            text = msg[len("ALERT: "):]
            sev, kind = classify(text)
            # r171 — BLIND EPISODES, not a sight timestamp: measured on 09-29
            # the "Sight restored" page was logged at 09:38:16 ET, TWELVE
            # SECONDS AFTER the Breakout that entered at 09:38:04 on a trigger
            # from the blind window. A rule keyed on sight alone missed it.
            eps = self.st.setdefault("blind_eps", [])
            if kind == "blind" and not (eps and eps[-1][1] is None):
                eps.append([ts, None])
            elif kind == "sight_restored" and eps and eps[-1][1] is None:
                eps[-1][1] = ts
            del eps[:-20]
            self.emit(ts, sev, kind, text, source="bot.log")
        elif msg.startswith("disk_watch: ") and level == "ERROR":
            self.emit(ts, "URGENT", "disk", msg, source="bot.log")
        elif "has no exit route" in msg:
            ms = re.search(r"strategy '([^']+)'", msg)
            strat = ms.group(1) if ms else "?"
            key = "%s|%s" % (datetime.fromtimestamp(ts, _ET).date(), strat)
            seen = self.st.setdefault("noroute_seen", [])
            if key not in seen:
                seen.append(key)
                del seen[:-50]
                self.emit(ts, "UNUSUAL", "no_exit_route", msg, source="bot.log", strategy=strat)

    # ── source 2: trades.db ─────────────────────────────────────────────────
    def scan_trades(self) -> None:
        if not os.path.exists(TRADES_DB):
            return
        con = sqlite3.connect("file:%s?mode=ro" % TRADES_DB, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT trade_id, strategy, direction, status, entry_time, exit_time,"
                " exit_reason, pnl_usd, entry_premium, stop_premium, contracts,"
                " is_short_position, credit_received FROM trades"
                " WHERE entry_time >= ? OR exit_time >= ?",
                (datetime.fromtimestamp(self.since - 86400, timezone.utc).isoformat(),) * 2
            ).fetchall()
        finally:
            con.close()
        entries = self.st.setdefault("entries_seen", [])
        closes = self.st.setdefault("closes_seen", [])
        losses = self.st.setdefault("recent_losses", [])
        for r in sorted(rows, key=lambda x: x["entry_time"] or ""):
            tid = r["trade_id"]
            ets = _iso_ts(r["entry_time"])
            if ets and ets >= self.since and tid not in entries:
                entries.append(tid)
                ep = next((e for e in self.st.get("blind_eps", [])
                           if e[0] <= ets <= (e[1] if e[1] else self.now()) + SIGHT_WINDOW_S),
                          None)
                if ep:
                    where = ("while the bot was still flagged BLIND" if not ep[1] or ets < ep[1]
                             else "%ds after sight was restored" % (ets - ep[1]))
                    self.emit(ets, "UNUSUAL", "entry_after_sight",
                              "%s %s entered %s — was its trigger seen, or did it fire "
                              "while blind? (§37)" % (r["strategy"], r["direction"], where),
                              source="trades.db", trade_id=tid, direction=r["direction"])
        for r in sorted(rows, key=lambda x: x["exit_time"] or ""):
            tid = r["trade_id"]
            xts = _iso_ts(r["exit_time"])
            if r["status"] == "open" or not xts or xts < self.since or tid in closes:
                continue
            if r["pnl_usd"] is None:
                continue          # a close whose P&L is not booked yet: judge it next pass
            closes.append(tid)
            pnl = float(r["pnl_usd"])
            if pnl >= 0:
                continue
            d = r["direction"]
            self.emit(xts, "LOSS", "loss",
                      "%s %s %+.0f — %s" % (r["strategy"], d, pnl, (r["exit_reason"] or "")[:90]),
                      source="trades.db", trade_id=tid, direction=d, pnl=round(pnl, 2),
                      strategy=r["strategy"])
            credit = bool(r["is_short_position"]) or bool(r["credit_received"])
            ep, sp, n = r["entry_premium"], r["stop_premium"], r["contracts"]
            if not credit and ep and sp and n and ep > sp:
                planned = (ep - sp) * n * 100
                if -pnl > LOSS_OVER_PLAN * planned:
                    self.emit(xts, "UNUSUAL", "loss_over_plan",
                              "%s %s lost %.0f against %.0f planned at its premium stop (%.1fx)"
                              % (r["strategy"], d, -pnl, planned, -pnl / planned),
                              source="trades.db", trade_id=tid, direction=d)
            prior = [l for l in losses if l["dir"] == d and 0 <= xts - l["ts"] <= CLUSTER_S]
            if prior and d in ("long", "short"):
                self.emit(xts, "UNUSUAL", "loss_cluster",
                          "%d %s losses inside %d min (this one %s %+.0f)"
                          % (len(prior) + 1, d, CLUSTER_S // 60, r["strategy"], pnl),
                          source="trades.db", trade_id=tid, direction=d)
            losses.append({"ts": xts, "dir": d})
        del entries[:-500]
        del closes[:-500]
        losses[:] = [l for l in losses if self.now() - l["ts"] <= 2 * 86400]

    # ── source 3: the emergency watchdog's journal ──────────────────────────
    def scan_watchdog(self) -> None:
        if not WDOG_UNIT:
            return
        cmd = ["journalctl", "-u", WDOG_UNIT, "-o", "json", "--no-pager"]
        cur = self.st.get("wdog_cursor")
        cmd += ["--after-cursor", cur] if cur else [
            "--since", "@%d" % int(self.since)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        for ln in r.stdout.splitlines():
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            self.st["wdog_cursor"] = e.get("__CURSOR", self.st.get("wdog_cursor"))
            msg = e.get("MESSAGE") or ""
            if not isinstance(msg, str):
                continue
            i = msg.find("PAGE: ")
            if i < 0:
                continue
            ts = int(e.get("__REALTIME_TIMESTAMP", "0")) / 1e6 or self.now()
            self.emit(ts, "URGENT", "watchdog", msg[i + 6:], source="watchdog")

    def scan(self) -> None:
        for name, fn in (("bot.log", self.scan_log), ("trades.db", self.scan_trades),
                         ("watchdog", self.scan_watchdog)):
            try:
                fn()
            except Exception as exc:                            # noqa: BLE001
                self.error(name, exc)
        save_state(self.st)


def _lock():
    import fcntl
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    fh = open(STATE + ".lock", "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    return fh


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the agent's alert watcher (r171)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--follow", action="store_true")
    g.add_argument("--once", action="store_true")
    g.add_argument("--tail", type=int)
    a = ap.parse_args(argv)
    if a.tail is not None:
        try:
            with open(EVENTS, encoding="utf-8") as fh:
                lines = fh.readlines()[-a.tail:]
        except OSError:
            lines = []
        for ln in lines:
            e = json.loads(ln)
            print("%s %-8s %-20s %s" % (e["ts_et"][11:16], e["severity"], e["kind"], e["text"][:120]))
        return 0
    lock = _lock()
    if lock is None:
        print("AGENT-EVENT WATCH-ERROR another agent_watch is already running — this one exits",
              flush=True)
        return 3
    w = Watch()
    if w.first:
        print("AGENT-EVENT INFO watch started with no state — looking back %dh" % (CATCHUP_S // 3600),
              flush=True)
    w.scan()
    while a.follow:
        time.sleep(POLL_S)
        w.scan()
    return 0


if __name__ == "__main__":
    sys.exit(main())
