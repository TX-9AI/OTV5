#!/usr/bin/env python3
"""tests/check_agent_watch.py — v1.1
THE AGENT HEARS EVERY PAGE, WAKES ONLY ON THE ONES THAT MATTER, AND ITS
TRADING VERDICTS ARE READ BY NOTHING.

v1.1  2026-09-30 — OTV4TEST r180 (AGT.3). C1 COMPARED THE LIVE FILES' SIZES,
      SO THE REAL WATCHER RECORDING A REAL EVENT MID-RUN TURNED IT RED. The
      08:00 boot sweep on 2026-09-30 reached this checker (fourth in order, the
      sweep started 08:00:31 ET) while the session's live watcher recorded the
      bot's STARTED page at 08:00:38: one real row, a red control, nothing
      leaked. C1 is now three checks that ask the question it was for - did
      THIS process write a live file - and do not depend on nothing else
      writing them: C1a the tools under test resolve every path they write or
      read inside the scratch directory; C1b no row appended to the live event
      or verdict log during the run, and no state written to the live state
      file, is one this process produced (every event, verdict and state it
      writes is captured as written); C1c the comparison itself flags a
      produced row and passes a foreign one. A size change alone is no longer
      a failure.
v1.0  2026-09-29 — OTV4TEST r171 (AGT.1 / AGT.2). Drives the REAL
      tools/agent_watch.py and tools/agent_verdict.py against fixture files:
      a fixture bot.log, a fixture trades.db built with the live table's own
      column names, a stub `journalctl`, and scratch state/events/verdicts —
      every path redirected BEFORE import, so nothing here reads or writes the
      box's live stores (C1 checks the live files are untouched).
  A1  the REAL alert_manager's routine pages classify ROUTINE (startup,
      shutdown, resumed + carried position, reconcile unavailable, sight
      restored, directional + butterfly entry, exit, daily summary)
  A2  the REAL urgent pages classify URGENT (blind, hard close failed,
      phantom, adopted, exercise footprint, orphan, short leg)
  A3  an alert nobody listed WAKES (URGENT/alert), never hides
  W1  bot.log: an urgent page prints; a routine one is recorded, not printed;
      a disk_watch ERROR prints; "no exit route" prints ONCE per strategy/day
  W2  a second scan prints NOTHING (the state carries the offset)
  W3  a half-written last line is not consumed until its newline lands
  W4  rotation: lines written before and after bot.log -> bot.log.1 are each
      read exactly once
  T1  trades.db: a loss prints LOSS once; a win prints nothing; an open row
      and a close with no booked P&L are not judged until booked
  T2  a debit loss beyond 1.25x its premium-stop risk is UNUSUAL
  T3  two same-direction losses inside 30 min are UNUSUAL; opposite
      directions are not
  T4  an entry inside a blind episode is UNUSUAL — the 09-29 shape, where
      the sight page was logged 12 s AFTER the entry
  J1  a watchdog PAGE in its journal is URGENT, and the cursor is carried
  L1  a second watcher refuses to run (exit 3, says so)
  E1  a source that raises prints WATCH-ERROR once and the scan continues
  V1  a verdict records forbid/until/note, the trade's direction and P&L,
      the last 1m close and the seconds since the loss
  V2  bad forbid, empty note, unknown trade: refused, nothing written
  V4  OBSERVE ONLY: no shipped module names AGENT_VERDICTS or agent_verdict
  C1a the tools under test resolve every path inside the scratch directory
  C1b nothing THIS process produced reached the live events, verdicts or state
      (a real event recorded by the live watcher mid-run is not a failure)
  C1c the leak comparison flags a produced row and passes a foreign one
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from datetime import datetime, timezone

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
# ENV.1 (ruled 09-27): a new gate adds the venv's site-packages itself, so the
# lander's bare `python3` can import the REAL alert_manager (it needs pytz).
import glob as _glob                                            # noqa: E402
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
        return False
    try:
        d = detail()
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)
    return ok


def _size(p):
    return os.path.getsize(p) if os.path.exists(p) else None


def _tail(p, start):
    """The complete lines appended to `p` after byte `start` (whole file if it
    shrank or is new)."""
    try:
        with open(p, "rb") as fh:
            if start and os.path.getsize(p) >= start:
                fh.seek(start)
            data = fh.read()
    except OSError:
        return []
    return [l for l in data.decode("utf-8", "replace").splitlines() if l.strip()]


def _leaked(appended, produced):
    """Rows in `appended` that this process produced (compared as parsed JSON,
    so key order and spacing cannot hide one)."""
    def _norm(l):
        try:
            return json.dumps(json.loads(l), sort_keys=True)
        except ValueError:
            return l.strip()
    made = {_norm(x) for x in produced}
    return [l for l in appended if _norm(l) in made]


PRODUCED_EVENTS, PRODUCED_VERDICTS, PRODUCED_STATES = [], [], []


def _slurp(path, into):
    try:
        into.extend(l for l in open(path, encoding="utf-8").read().splitlines() if l.strip())
    except OSError:
        pass


# ── C1 baseline: the live files, BEFORE anything runs ───────────────────────
LIVE = [os.path.join(_root, "data", "AGENT_EVENTS.jsonl"),
        os.path.join(_root, "data", "AGENT_VERDICTS.jsonl"),
        os.path.expanduser("~/.optbot/agent_watch.json")]
_live_before = [_size(p) for p in LIVE]

TMP = tempfile.mkdtemp(prefix="aw_")
BOTLOG = os.path.join(TMP, "bot.log")
TDB = os.path.join(TMP, "trades.db")
FDB = os.path.join(TMP, "feed_store.db")
os.environ.update({
    "OT_BOT_LOG": BOTLOG, "OT_TRADES_DB": TDB, "OT_FEED_DB": FDB,
    "OT_AGENT_EVENTS": os.path.join(TMP, "events.jsonl"),
    "OT_AGENT_VERDICTS": os.path.join(TMP, "verdicts.jsonl"),
    "OT_AGENT_WATCH_STATE": os.path.join(TMP, "state", "agent_watch.json"),
    "OT_AGENT_WATCH_JOURNAL": "",
    "OT_AGENT_STATUS": os.path.join(TMP, "AGENT_STATUS"),
})


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_root, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


aw = _load("tools/agent_watch.py", "_aw")
av = _load("tools/agent_verdict.py", "_av")

# C1b: capture what this process writes, AS it writes it.
_real_emit, _real_save = aw.Watch.emit, aw.save_state


def _emit(self, *a, **k):
    ev = _real_emit(self, *a, **k)
    PRODUCED_EVENTS.append(json.dumps(ev))
    return ev


def _save(st):
    PRODUCED_STATES.append(json.dumps(st, sort_keys=True))
    return _real_save(st)


aw.Watch.emit, aw.save_state = _emit, _save


def _reset():
    _slurp(os.environ["OT_AGENT_EVENTS"], PRODUCED_EVENTS)      # before it is deleted
    for p in (os.environ["OT_AGENT_EVENTS"], os.environ["OT_AGENT_WATCH_STATE"], BOTLOG,
              BOTLOG + ".1", TDB):
        if os.path.exists(p):
            os.unlink(p)


def _scan(now=None, sources=("log", "trades", "wdog")):
    """One REAL scan; -> the printed lines."""
    buf = io.StringIO()
    w = aw.Watch(now=(lambda: now) if now else time.time, out=buf)
    w.since = w.st["since"] = (now or time.time()) - 6 * 3600
    if "log" in sources:
        w.scan_log()
    if "trades" in sources:
        w.scan_trades()
    if "wdog" in sources:
        w.scan_watchdog()
    aw.save_state(w.st)
    return [l for l in buf.getvalue().splitlines() if l.strip()]


def _events():
    try:
        return [json.loads(l) for l in open(os.environ["OT_AGENT_EVENTS"])]
    except OSError:
        return []


def _stamp(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _line(ts, msg, level="INFO", src="notifications.alert_manager"):
    return "%s [%-5s] %s: %s\n" % (_stamp(ts), level, src, msg)


# ── A1/A2 — the REAL alert texts, captured, never sent ──────────────────────
def _pages():
    import notifications.alert_manager as am
    mgr = am.AlertManager.__new__(am.AlertManager)
    mgr._tg, mgr._enabled = None, False
    sent = []
    mgr._send = lambda msg: (sent.append(msg), True)[1]
    am.public_ip = lambda: ("1.2.3.4", "")
    out = {}

    def grab(name, fn):
        sent.clear()
        fn()
        out[name] = sent[0] if sent else ""

    grab("startup", lambda: mgr.send_startup_alert(paper=True, instrument="QQQ", risk_usd=1050.0,
                                                   restart_type="fresh boot"))
    grab("shutdown", lambda: mgr.send_shutdown_alert("QQQ", "maintenance"))
    grab("resumed", lambda: mgr.send_recovery_alert("QQQ", "PUT 737", 29, 1.7, 4930.0,
                                                    "Breakout", "service restart"))
    grab("carried", lambda: mgr.send_recovery_alert("QQQ", "PUT 737", 29, 1.7, 4930.0,
                                                    "Breakout", "fresh boot", carried=True))
    grab("reconcile", lambda: mgr.send_reconcile_unavailable_alert("QQQ", "timeout"))
    grab("sight", lambda: mgr.send_sight_restored_alert("QQQ", 299.0, "BARS_STALE"))
    grab("entry", lambda: mgr.send_entry_alert({"paper_trade": True, "option_side": "put",
                                                "strike": 737.0, "contracts": 29,
                                                "entry_premium": 1.7, "total_cost": 4930.0}))
    grab("fly", lambda: mgr.send_entry_alert({"paper_trade": True, "is_butterfly": True,
                                              "option_side": "call", "lower_strike": 735,
                                              "center_strike": 737, "upper_strike": 739,
                                              "contracts": 5, "net_debit": 0.8,
                                              "total_cost": 400.0}))
    grab("exit", lambda: mgr.send_exit_alert("t1", "breakout_short", 1.2, 1.7, -1450.0, 29,
                                             "hard_stop"))
    grab("daily", lambda: mgr.send_daily_summary({"instrument": "QQQ", "paper": True,
                                                  "n_trades": 3, "wins": 1, "losses": 2,
                                                  "gross_pnl": -500.0, "fees": 3.0}))
    grab("blind", lambda: mgr.send_blind_alert("QQQ", {"cause": "BARS_STALE", "timeframe": "1m",
                                                       "fields": {"age_s": 183}},
                                               open_positions=[], blind_for_s=46.0))
    grab("hard_close", lambda: mgr.send_hard_close_failure_alert("QQQ", ["t1"]))
    grab("phantom", lambda: mgr.send_phantom_closed_alert("QQQ", ["t1"]))
    grab("adopted", lambda: mgr.send_adopted_alert("QQQ", "PUT 737", 2, 1.1))
    grab("exercise", lambda: mgr.send_exercise_footprint_alert("QQQ", [{"symbol": "QQQ",
                                                                         "quantity": 100}], 73700.0))
    grab("orphan", lambda: mgr.send_orphan_cleared_alert("QQQ", ["PUT 737"]))
    grab("short_leg", lambda: mgr.send_short_leg_closed_alert("QQQ", "short 740C", "long 745C"))
    return out


_P = {}
try:
    _P.update(_pages())
except Exception as exc:                                        # noqa: BLE001
    _P["_err"] = "%s: %s" % (type(exc).__name__, exc)

ROUTINE_NAMES = ["startup", "shutdown", "resumed", "carried", "reconcile", "sight", "entry",
                 "fly", "exit", "daily"]
URGENT_NAMES = ["blind", "hard_close", "phantom", "adopted", "exercise", "orphan", "short_leg"]


def _cls(names):
    return {n: aw.classify(_P.get(n, ""))[0] if _P.get(n) else "EMPTY" for n in names}


guard("A1 every REAL routine page classifies ROUTINE (recorded, never wakes)",
      lambda: set(_cls(ROUTINE_NAMES).values()) == {"ROUTINE"},
      lambda: _P.get("_err") or str({k: v for k, v in _cls(ROUTINE_NAMES).items() if v != "ROUTINE"}))
guard("A2 every REAL urgent page classifies URGENT",
      lambda: set(_cls(URGENT_NAMES).values()) == {"URGENT"},
      lambda: _P.get("_err") or str({k: v for k, v in _cls(URGENT_NAMES).items() if v != "URGENT"}))
guard("A2b the blind page is named 'blind'",
      lambda: aw.classify(_P.get("blind", ""))[1] == "blind")
guard("A3 an alert nobody listed WAKES rather than hides",
      lambda: aw.classify("🛸 something nobody has written yet | QQQ") == ("URGENT", "alert"))


# ── W1-W4 — bot.log ─────────────────────────────────────────────────────────
_W = {}


def _w1():
    _reset()
    t = time.time() - 600
    with open(BOTLOG, "w") as fh:
        fh.write(_line(t, "ALERT: " + _P["blind"]))
        fh.write(_line(t + 1, "ALERT: " + _P["entry"]))
        fh.write(_line(t + 2, "disk_watch: QQQ at 91.0% — largest files: x", "ERROR", "data.disk_watch"))
        fh.write(_line(t + 3, "[exit] strategy 'Breakout' has no exit route — defaulting", "WARNING",
                       "execution.exit_engine"))
        fh.write(_line(t + 4, "[exit] strategy 'Breakout' has no exit route — defaulting", "WARNING",
                       "execution.exit_engine"))
    out = _scan(sources=("log",))
    ev = _events()
    _W["w1"] = out
    kinds = [re.search(r"AGENT-EVENT (\S+) (\S+)", l).groups() for l in out]
    return (kinds == [("URGENT", "blind"), ("URGENT", "disk"), ("UNUSUAL", "no_exit_route")]
            and any(e["kind"] == "entry" and e["severity"] == "ROUTINE" for e in ev))


guard("W1 urgent prints, routine is recorded silently, disk prints, no-route once", _w1,
      lambda: str(_W.get("w1"))[:300])
guard("W2 a second scan prints NOTHING", lambda: _scan(sources=("log",)) == [])


def _w3():
    t = time.time() - 300
    with open(BOTLOG, "a") as fh:
        fh.write(_line(t, "ALERT: " + _P["phantom"]).rstrip("\n"))   # no newline yet
    first = _scan(sources=("log",))
    with open(BOTLOG, "a") as fh:
        fh.write("\n")
    second = _scan(sources=("log",))
    return first == [] and len(second) == 1 and " phantom " in second[0]


guard("W3 a half-written line waits for its newline, then reads once", _w3)


def _w4():
    t = time.time() - 200
    with open(BOTLOG, "a") as fh:
        fh.write(_line(t, "ALERT: " + _P["adopted"]))          # before rotation, unread
    os.rename(BOTLOG, BOTLOG + ".1")
    with open(BOTLOG, "w") as fh:
        fh.write(_line(t + 1, "ALERT: " + _P["orphan"]))       # after rotation
    out = _scan(sources=("log",))
    again = _scan(sources=("log",))
    _W["w4"] = out
    return len(out) == 2 and " adopted " in out[0] and " orphan " in out[1] and again == []


guard("W4 rotation: before and after bot.log -> bot.log.1, each read exactly once", _w4,
      lambda: str(_W.get("w4"))[:200])


# ── T1-T4 — trades.db, built with the LIVE table's own column names ─────────
def _cols():
    """The columns agent_watch reads, checked against the live schema's names."""
    return ["trade_id", "symbol", "strategy", "direction", "status", "entry_time", "exit_time",
            "exit_reason", "pnl_usd", "entry_premium", "stop_premium", "contracts",
            "is_short_position", "credit_received"]


def _live_cols():
    live = os.path.join(_root, "trades.db")
    if not os.path.exists(live):
        live = os.path.expanduser("~/options-trader/trades.db")
    if not os.path.exists(live):
        return None
    c = sqlite3.connect("file:%s?mode=ro" % live, uri=True)
    try:
        return [r[1] for r in c.execute("PRAGMA table_info(trades)")]
    finally:
        c.close()


_LC = _live_cols()
guard("T0 every column agent_watch reads exists in the live trades table",
      lambda: _LC is not None and not [c for c in _cols() if c not in _LC],
      lambda: "NOT RUN — no live trades.db" if _LC is None else
      str([c for c in _cols() if c not in _LC]))


def _db(rows):
    if os.path.exists(TDB):
        os.unlink(TDB)
    c = sqlite3.connect(TDB)
    c.execute("CREATE TABLE trades (%s)" % ", ".join(_cols()))
    for r in rows:
        c.execute("INSERT INTO trades VALUES (%s)" % ",".join("?" * len(_cols())),
                  [r.get(k) for k in _cols()])
    c.commit()
    c.close()


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _trade(tid, d, pnl, exit_ts, status="closed", ep=1.7, sp=1.5, n=29, entry_ts=None, credit=None):
    return {"trade_id": tid, "symbol": "QQQ", "strategy": "Breakout", "direction": d,
            "status": status,
            "entry_time": _iso(entry_ts or (exit_ts - 300 if exit_ts else time.time() - 300)),
            "exit_time": _iso(exit_ts) if exit_ts else None, "exit_reason": "stop",
            "pnl_usd": pnl, "entry_premium": ep, "stop_premium": sp, "contracts": n,
            "is_short_position": 0, "credit_received": credit}


_T = {}


def _t1():
    _reset()
    now = time.time()
    _db([_trade("L1", "short", -300.0, now - 900),        # planned 580 -> not over plan
         _trade("W1", "long", 400.0, now - 800),
         _trade("O1", "long", None, None, status="open"),
         _trade("P1", "long", None, now - 700)])            # closed, P&L not booked yet
    out = _scan(now=now, sources=("trades",))
    c = sqlite3.connect(TDB)
    c.execute("UPDATE trades SET pnl_usd = -100 WHERE trade_id = 'P1'")
    c.commit(); c.close()
    out2 = _scan(now=now + 5, sources=("trades",))
    out3 = _scan(now=now + 10, sources=("trades",))
    _T["t1"] = (out, out2, out3)
    return (len(out) == 1 and "LOSS loss" in out[0] and "-300" in out[0]
            and len(out2) == 1 and "-100" in out2[0] and out3 == [])


guard("T1 a loss prints once; a win, an open row and an unbooked close do not", _t1,
      lambda: str(_T.get("t1"))[:300])


def _t2():
    _reset()
    now = time.time()
    # planned = (1.7 - 1.5) * 29 * 100 = 580; 1.25x = 725
    _db([_trade("B1", "short", -700.0, now - 3000), _trade("B2", "long", -800.0, now - 100)])
    out = _scan(now=now, sources=("trades",))
    over = [l for l in out if "loss_over_plan" in l]
    _T["t2"] = out
    return len(over) == 1 and "long lost 800" in over[0]


guard("T2 a debit loss beyond 1.25x its premium-stop risk is UNUSUAL (and 1.2x is not)", _t2,
      lambda: str(_T.get("t2"))[:300])


def _t3():
    _reset()
    now = time.time()
    _db([_trade("C1", "short", -100.0, now - 1500), _trade("C2", "short", -100.0, now - 600),
         _trade("C3", "long", -100.0, now - 300)])
    out = _scan(now=now, sources=("trades",))
    cl = [l for l in out if "loss_cluster" in l]
    _T["t3"] = out
    return len(cl) == 1 and "2 short losses" in cl[0]


guard("T3 two same-direction losses inside 30 min are UNUSUAL; opposite is not", _t3,
      lambda: str(_T.get("t3"))[:300])


def _t4():
    _reset()
    now = time.time()
    blind, entry, sight = now - 600, now - 350, now - 338       # sight logged AFTER entry
    with open(BOTLOG, "w") as fh:
        fh.write(_line(blind, "ALERT: " + _P["blind"]))
        fh.write(_line(sight, "ALERT: " + _P["sight"]))
    _db([_trade("S1", "short", None, None, status="open", entry_ts=entry),
         _trade("S0", "long", None, None, status="open", entry_ts=now - 5000)])
    out = _scan(now=now, sources=("log", "trades"))
    ea = [l for l in out if "entry_after_sight" in l]
    _T["t4"] = out
    return len(ea) == 1 and "short entered while the bot was still flagged BLIND" in ea[0]


guard("T4 an entry inside a blind episode is UNUSUAL (the 09-29 shape)", _t4,
      lambda: str(_T.get("t4"))[:300])


# ── J1 — the watchdog's journal, through a stub journalctl ──────────────────
def _j1():
    _reset()
    d = tempfile.mkdtemp(prefix="jstub_", dir=TMP)
    log = os.path.join(d, "calls")
    now = time.time()
    with open(os.path.join(d, "journalctl"), "w") as fh:
        fh.write("#!/bin/sh\necho \"$@\" >> %s\n" % log
                 + "echo '%s'\n" % json.dumps({"__CURSOR": "c1", "__REALTIME_TIMESTAMP":
                                               str(int((now - 60) * 1e6)),
                                               "MESSAGE": "2026-09-29 15:51:00 ET  PAGE: 🚨 closed 2"})
                 + "echo '%s'\n" % json.dumps({"__CURSOR": "c2", "MESSAGE": "healthy"}))
    os.chmod(os.path.join(d, "journalctl"), 0o755)
    old_path, old_unit = os.environ["PATH"], aw.WDOG_UNIT
    os.environ["PATH"] = d + os.pathsep + old_path
    aw.WDOG_UNIT = "stub.service"
    try:
        out = _scan(now=now, sources=("wdog",))
        _scan(now=now + 5, sources=("wdog",))
    finally:
        os.environ["PATH"], aw.WDOG_UNIT = old_path, old_unit
    calls = open(log).read().splitlines()
    _T["j1"] = (out, calls)
    return (len(out) == 1 and "URGENT watchdog" in out[0] and "closed 2" in out[0]
            and "--after-cursor c2" in calls[-1])


guard("J1 a watchdog PAGE is URGENT and the journal cursor is carried", _j1,
      lambda: str(_T.get("j1"))[:300])


# ── L1 / E1 ─────────────────────────────────────────────────────────────────
def _l1():
    lock = aw._lock()
    try:
        r = subprocess.run([sys.executable, os.path.join(_root, "tools", "agent_watch.py"), "--once"],
                           capture_output=True, text=True, timeout=60, env=dict(os.environ))
    finally:
        lock.close()
    _T["l1"] = (r.returncode, r.stdout.strip()[:120])
    return r.returncode == 3 and "already running" in r.stdout


guard("L1 a second watcher refuses to run and says so", _l1, lambda: str(_T.get("l1")))


def _e1():
    _reset()
    open(BOTLOG, "w").write(_line(time.time() - 60, "ALERT: " + _P["blind"]))
    buf = io.StringIO()
    w = aw.Watch(out=buf)
    w.scan_trades = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    w.scan()
    w.scan()
    out = buf.getvalue().splitlines()
    errs = [l for l in out if "WATCH-ERROR trades.db" in l]
    _T["e1"] = out
    return len(errs) == 1 and any("URGENT blind" in l for l in out)


guard("E1 a failing source prints WATCH-ERROR once; the others still scan", _e1,
      lambda: str(_T.get("e1"))[:300])


# ── V1-V4 — the verdict ─────────────────────────────────────────────────────
def _v1():
    now = time.time()
    _db([_trade("c7bbd5af-0421", "short", -1241.0, now - 120)])
    if os.path.exists(FDB):
        os.unlink(FDB)
    c = sqlite3.connect(FDB)
    c.execute("CREATE TABLE candles (symbol, interval, ts_epoch_ms, open, high, low, close, volume)")
    c.execute("INSERT INTO candles VALUES ('QQQ','1m',?,1,1,1,737.5,1)", (int((now - 30) * 1000),))
    c.commit(); c.close()
    v = av.record("short", "stacked FVG retrace, sellers absorbed at 737", "a 5m close above 739.62",
                  trade_id="c7bbd5af", now=now)
    rows = [json.loads(l) for l in open(os.environ["OT_AGENT_VERDICTS"])]
    _T["v1"] = v
    return (rows[-1] == v and v["forbid"] == "short" and v["loss_direction"] == "short"
            and v["loss_pnl"] == -1241.0 and v["px_last_1m"] == 737.5
            and 115 <= v["s_since_loss"] <= 125 and v["until"].startswith("a 5m close"))


guard("V1 a verdict records forbid/until/note, the loss, the last close, the lag", _v1,
      lambda: str(_T.get("v1"))[:300])


def _v2():
    p = os.environ["OT_AGENT_VERDICTS"]
    n = len(open(p).readlines())
    bad = 0
    for kw in ({"forbid": "sideways", "note": "x"}, {"forbid": "long", "note": "  "},
               {"forbid": "long", "note": "x", "trade_id": "nosuchtrade"}):
        try:
            av.record(**kw)
        except ValueError:
            bad += 1
    return bad == 3 and len(open(p).readlines()) == n


guard("V2 bad forbid, empty note, unknown trade: refused, nothing written", _v2)


def _v4():
    hits = []
    for top in os.listdir(_root):
        if top in ("tests", "docs", "venv", ".git", "data") or top.startswith("."):
            continue
        base = os.path.join(_root, top)
        paths = [base] if os.path.isfile(base) else [
            os.path.join(dp, f) for dp, _, fs in os.walk(base) for f in fs]
        for p in paths:
            rel = os.path.relpath(p, _root)
            if not p.endswith((".py", ".sh")) or rel in ("tools/agent_verdict.py",
                                                         "tools/agent_watch.py"):
                continue
            try:
                s = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if "AGENT_VERDICTS" in s or "agent_verdict" in s:
                hits.append(rel)
    _T["v4"] = hits
    return hits == []


guard("V4 OBSERVE ONLY: no shipped module names the verdicts or their tool", _v4,
      lambda: str(_T.get("v4")))

_slurp(os.environ["OT_AGENT_EVENTS"], PRODUCED_EVENTS)
_slurp(os.environ["OT_AGENT_VERDICTS"], PRODUCED_VERDICTS)
_C1 = {}


def _c1a():
    paths = {"aw.EVENTS": aw.EVENTS, "aw.STATE": aw.STATE, "aw.BOT_LOG": aw.BOT_LOG,
             "aw.TRADES_DB": aw.TRADES_DB, "av.VERDICTS": av.VERDICTS,
             "av.TRADES_DB": av.TRADES_DB, "av.FEED_DB": av.FEED_DB}
    _C1["a"] = sorted(k for k, v in paths.items() if not str(v).startswith(TMP + os.sep))
    return not _C1["a"]


guard("C1a CONTROL: the tools under test resolve every path inside the scratch directory",
      _c1a, lambda: "outside scratch: %s" % _C1.get("a"))


def _c1b():
    ev = _leaked(_tail(LIVE[0], _live_before[0] or 0), PRODUCED_EVENTS)
    vd = _leaked(_tail(LIVE[1], _live_before[1] or 0), PRODUCED_VERDICTS)
    try:
        live_state = json.dumps(json.load(open(LIVE[2], encoding="utf-8")), sort_keys=True)
    except (OSError, ValueError):
        live_state = None
    st = live_state is not None and live_state in set(PRODUCED_STATES)
    _C1["b"] = {"events": len(ev), "verdicts": len(vd), "state": st,
                "captured": (len(PRODUCED_EVENTS), len(PRODUCED_VERDICTS), len(PRODUCED_STATES)),
                "live grew": [(_size(p) or 0) - (b or 0) for p, b in zip(LIVE, _live_before)]}
    return (not ev and not vd and not st
            and PRODUCED_EVENTS and PRODUCED_VERDICTS and PRODUCED_STATES)


guard("C1b CONTROL: nothing this process produced reached the live events, verdicts or state",
      _c1b, lambda: str(_C1.get("b")))


def _c1c():
    mine = PRODUCED_EVENTS[0]
    shuffled = json.dumps(dict(reversed(list(json.loads(mine).items()))))
    foreign = json.dumps({"id": "E20260930120035-50", "severity": "ROUTINE", "kind": "startup",
                          "text": "a real event the live watcher recorded mid-run"})
    return (_leaked([foreign], PRODUCED_EVENTS) == []
            and _leaked([foreign, shuffled], PRODUCED_EVENTS) == [shuffled])


guard("C1c the leak comparison flags a produced row (in any key order) and passes a foreign one",
      _c1c)

shutil.rmtree(TMP, ignore_errors=True)
print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
