#!/usr/bin/env python3
"""
tests/check_floor_watch.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
THE 2 s FLOOR WATCH WAKES THE TICK (EXIT.5 on TEST, execution/fill_observers.sleep_observing).
v1.0  2026-10-13  OTV4TEST r280. The operator, 2026-10-13 13:19 ET: "Yes to all" (the relayed "Exit5, yes");
      13:22 ET, its scope: "Breakout + Runaway". Mechanics of otv4 r482 (0353b4e): the wait ends early on a FRESH
      (<= 4 s) quote at or below the enforced premium stop, the tick then decides; nothing here exits.
      Driven through the REAL sleep_observing -> observe_watch -> chain_marks read, on a scratch feed store
      (OT_FEED_DB), with a fake slice clock; the quote ages are real (updated_epoch = now - age).

  F1  trade (unset): a crossed Breakout ends the sleep after ONE 2 s slice and returns a "woke" row with early_s
  F2  log: the same cross is recorded (would_wake) but the sleep runs its full length and returns None
  F3  off: nothing recorded, full sleep
  F4  Runaway wakes; a watched strategy outside WAKE_STRATEGIES is recorded but does NOT wake; Hunt is not watched
  F5  a stale quote (6 s) and a quote above the stop do not wake
  F6  OT_FILL_OBSERVE=off does not disable the acting watch (its own switch)
  F7  an unknown OT_FLOOR_WATCH value reads as log (never act on a typo); a raising records_fn sleeps fully
  F8  the Service mode line names floor_watch=trade / log
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_floor_watch_")
for k, v in {"OT_TRADES_DB": "t.db", "OT_DERIVED_DB": "d.db", "OT_FEED_DB": "f.db", "OT_LOG_FILE": "bot.log",
             "OT_RESTING_DB": "r.db", "OT_SIGNAL_JOURNAL_DIR": "sj", "OT_COUNTERFACTUAL_DIR": "cf",
             "OT_RESTING_STOP_STATE": "rest_state.json"}.items():
    os.environ[k] = os.path.join(_TD, v)
for k in ("OT_FILL_OBSERVE", "OT_FLOOR_WATCH", "OT_RESTING_STOP"):
    os.environ.pop(k, None)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _rec(tid, **kw):
    r = {"trade_id": tid, "strategy": "Breakout", "symbol": "QQQ", "direction": "long", "option_side": "call",
         "entry_premium": 2.00, "stop_premium": 1.00, "target_premium": 0.0, "trail_stop": 0.0,
         "contracts": 10, "is_butterfly": 0, "option_symbol": "QQQ   261012C00750000", "expiry": "2026-10-12",
         "status": "open"}
    r.update(kw)
    return r


class _C:
    def __init__(self, strike, sym): self.strike, self.streamer_symbol = strike, sym


class _Chain:
    spot_price = 748.0
    calls = [_C(750.0, ".QQQ261012C750")]
    puts = []


def _feed(bid, ask, age):
    """Write the scratch feed store's one chain_marks row, `age` seconds old NOW."""
    p = os.environ["OT_FEED_DB"]
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE IF NOT EXISTS chain_marks (streamer_symbol TEXT PRIMARY KEY, bid REAL, ask REAL,"
              " delta REAL, gamma REAL, theta REAL, vega REAL, iv REAL, updated_epoch REAL NOT NULL)")
    c.execute("INSERT OR REPLACE INTO chain_marks (streamer_symbol, bid, ask, updated_epoch) VALUES (?,?,?,?)",
              (".QQQ261012C750", bid, ask, time.time() - age))
    c.commit(); c.close()


def _run(F, recs_fn, seconds=15.0):
    """Drive the REAL sleep_observing with a fake slice clock. -> (result, total slept)."""
    clock = [0.0]; slept = []
    def _sl(s): slept.append(s); clock[0] += s
    F._last_wake.clear()
    res = F.sleep_observing(seconds, recs_fn, lambda: _Chain(), _sleep=_sl, _clock=lambda: clock[0])
    return res, sum(slept)


def _rows():
    f = os.path.join(_TD, "cf", "quote_watch.jsonl")
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


def main():
    print("check_floor_watch")
    try:
        import pandas  # noqa: F401
        import execution.fill_observers as F
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2

    # F1 trade (unset)
    _feed(0.94, 0.98, 1.0)                                      # mid 0.96 <= 1.00, 1 s old
    n0 = len(_rows())
    r1, t1 = _run(F, lambda: [_rec("f1")])
    new = _rows()[n0:]
    check("F1 trade (unset): a crossed Breakout ends the sleep after one 2 s slice; returns a woke row with early_s",
          isinstance(r1, dict) and r1.get("event") == "woke" and r1.get("trade_id") == "f1"
          and abs(t1 - 2.0) < 1e-9 and abs(float(r1.get("early_s") or 0) - 13.0) < 1e-6
          and [x["event"] for x in new] == ["would_wake", "woke"], f"res={r1} slept={t1} rows={new}")

    # F2 log
    os.environ["OT_FLOOR_WATCH"] = "log"
    n0 = len(_rows())
    r2, t2 = _run(F, lambda: [_rec("f2")])
    new = _rows()[n0:]
    check("F2 log: the cross is recorded (would_wake) but the sleep runs 15 s and returns None",
          r2 is None and abs(t2 - 15.0) < 1e-9 and [x["event"] for x in new] == ["would_wake"],
          f"res={r2} slept={t2} rows={new}")

    # F3 off (and the record-only observer off too)
    os.environ["OT_FLOOR_WATCH"] = "off"; os.environ["OT_FILL_OBSERVE"] = "off"
    n0 = len(_rows())
    r3, t3 = _run(F, lambda: [_rec("f3")])
    check("F3 off: nothing recorded, full sleep", r3 is None and abs(t3 - 15.0) < 1e-9 and len(_rows()) == n0,
          f"res={r3} slept={t3}")
    os.environ.pop("OT_FLOOR_WATCH"); os.environ.pop("OT_FILL_OBSERVE")

    # F4 scope
    r4a, t4a = _run(F, lambda: [_rec("f4a", strategy="RunawayContinuation")])
    n0 = len(_rows())
    r4b, t4b = _run(F, lambda: [_rec("f4b", strategy="SomeOtherLong")])
    rec_b = [x["event"] for x in _rows()[n0:]]
    r4c, t4c = _run(F, lambda: [_rec("f4c", strategy="LiquidityHunt")])
    check("F4 Runaway wakes; a watched strategy outside WAKE_STRATEGIES records but does not wake; Hunt is unwatched",
          isinstance(r4a, dict) and abs(t4a - 2.0) < 1e-9 and r4b is None and abs(t4b - 15.0) < 1e-9
          and "would_wake" in rec_b and "woke" not in rec_b and r4c is None and abs(t4c - 15.0) < 1e-9,
          f"a={r4a},{t4a} b={r4b},{t4b},{rec_b} c={r4c},{t4c}")

    # F5 stale / above
    _feed(0.94, 0.98, 6.0)
    r5a, t5a = _run(F, lambda: [_rec("f5a")])
    _feed(1.02, 1.06, 1.0)
    r5b, t5b = _run(F, lambda: [_rec("f5b")])
    check("F5 a stale quote (6 s) and a quote above the stop do not wake",
          r5a is None and abs(t5a - 15.0) < 1e-9 and r5b is None and abs(t5b - 15.0) < 1e-9,
          f"stale={r5a},{t5a} above={r5b},{t5b}")

    # F6 fill_observe=off does not disable the acting watch
    _feed(0.94, 0.98, 1.0)
    os.environ["OT_FILL_OBSERVE"] = "off"
    r6, t6 = _run(F, lambda: [_rec("f6")])
    os.environ.pop("OT_FILL_OBSERVE")
    check("F6 OT_FILL_OBSERVE=off leaves the acting watch on (its own switch)",
          isinstance(r6, dict) and abs(t6 - 2.0) < 1e-9, f"res={r6} slept={t6}")

    # F7 typo + raising records_fn
    os.environ["OT_FLOOR_WATCH"] = "yes"
    mode = getattr(F, "floor_watch_mode", lambda: "<absent>")()
    r7a, t7a = _run(F, lambda: [_rec("f7a")])
    os.environ.pop("OT_FLOOR_WATCH")
    def _boom(): raise RuntimeError("records failure")
    raised = None
    try:
        r7b, t7b = _run(F, _boom)
    except Exception as exc:                                    # noqa: BLE001
        raised, r7b, t7b = exc, None, -1
    check("F7 an unknown OT_FLOOR_WATCH reads as log (no wake); a raising records_fn sleeps fully, never raises",
          mode == "log" and r7a is None and abs(t7a - 15.0) < 1e-9 and raised is None and abs(t7b - 15.0) < 1e-9,
          f"mode={mode} res={r7a},{t7a} raised={raised} slept={t7b}")

    # F8 the Service mode line
    e = dict(os.environ, OT_INSTRUMENT=os.environ.get("OT_INSTRUMENT", "QQQ"))
    p1 = subprocess.run([sys.executable, "-c", "import main;print(main._banner_dials())"], cwd=ROOT, env=e,
                        capture_output=True, text=True, timeout=240)
    p2 = subprocess.run([sys.executable, "-c", "import main;print(main._banner_dials())"], cwd=ROOT,
                        env=dict(e, OT_FLOOR_WATCH="log"), capture_output=True, text=True, timeout=240)
    o1 = (p1.stdout.strip().splitlines() or [""])[-1]; o2 = (p2.stdout.strip().splitlines() or [""])[-1]
    check("F8 the Service mode line names floor_watch=trade (unset) / log",
          "floor_watch=trade" in o1 and "floor_watch=log" in o2, f"unset={o1[-90:]} log={o2[-90:]}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks: the floor watch wakes the tick")
    return 0


if __name__ == "__main__":
    sys.exit(main())
