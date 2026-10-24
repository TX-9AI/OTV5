#!/usr/bin/env python3
"""
tests/check_breakout_exit_line.py  v1.0

A Breakout no longer logs the false "has no exit route ... Add a branch."; its
routing is unchanged; any OTHER unrouted strategy still warns.

v1.0  2026-09-30  OTV4TEST r182 (EXIT.3). The line was false for Breakout by the
      operator's 2026-09-21 ruling and, since r171, woke the agent as UNUSUAL
      every day a Breakout traded (118 lines in bot.log, all Breakout).

WHAT IT DRIVES (WA 21): the REAL ExitEngine.evaluate dispatch with a recorder in
place of _evaluate_sweep, and the REAL tools/agent_watch classifier on each line
the dispatch logged. Nothing is priced and no store is touched.

  E1  a Breakout record still falls through to the sweep evaluator (unchanged)
  E2  ...and logs no "has no exit route", once, at INFO, naming EXIT.3
  E3  an unknown strategy still WARNS "has no exit route" (a real one still wakes)
  E4  the agent watcher does not flag the Breakout line, and still flags the other

BORN RED on 59ba004 (r178) under both interpreters at E2 and E4.

Run:  python3 tests/check_breakout_exit_line.py
"""
from __future__ import annotations

import glob as _glob
import importlib.util
import logging
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _base in (ROOT, os.path.expanduser("~/options-trader")):
    _found = _glob.glob(os.path.join(_base, "venv", "lib", "python*", "site-packages"))
    for _sp in _found:
        if _sp not in sys.path:
            sys.path.insert(1, _sp)
    if _found:
        break
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ.setdefault("OT_PAPER_TRADING", "1")
_TMP = tempfile.mkdtemp(prefix="check_breakout_exit_line_")
for _k in ("OT_AGENT_EVENTS", "OT_AGENT_WATCH_STATE", "OT_BOT_LOG", "OT_TRADES_DB", "OT_FEED_DB"):
    os.environ[_k] = os.path.join(_TMP, _k.lower())
os.environ["OT_AGENT_WATCH_JOURNAL"] = ""

FAIL = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(label.split()[0])


class _Logs(logging.Handler):
    def __init__(self):
        super().__init__()
        self.rows = []

    def emit(self, record):
        self.rows.append((record.levelname, record.getMessage()))


LOGS = _Logs()
logging.getLogger("execution.exit_engine").addHandler(LOGS)
logging.getLogger("execution.exit_engine").setLevel(logging.DEBUG)

from execution import exit_engine as XE                         # noqa: E402

eng = XE.ExitEngine(paper_trading=True)
CALLED = []
eng._evaluate_sweep = lambda record, *a, **k: (CALLED.append(record.get("strategy")), "SWEEP")[1]
eng._seed_trail_from_record = lambda record: None


def run(strategy):
    LOGS.rows.clear()
    rec = {"strategy": strategy, "trade_id": f"{strategy}-1", "direction": "long",
           "entry_premium": 1.5, "contracts": 1}
    out = [eng.evaluate(rec, 1.4) for _ in range(3)]            # three ticks, one line
    return out, list(LOGS.rows)


out_b, logs_b = run("Breakout")
check("E1 a Breakout still falls through to the sweep evaluator (routing unchanged)",
      out_b == ["SWEEP"] * 3 and CALLED.count("Breakout") == 3, f"out={out_b} called={CALLED}")
_bl = [m for lv, m in logs_b if "[exit]" in m]
check("E2 ...and logs no 'has no exit route': one INFO line naming EXIT.3",
      not any("has no exit route" in m for _lv, m in logs_b) and len(_bl) == 1
      and "EXIT.3" in _bl[0] and [lv for lv, m in logs_b if "[exit]" in m] == ["INFO"],
      str(logs_b))
out_x, logs_x = run("FooStrategy")
_xl = [(lv, m) for lv, m in logs_x if "has no exit route" in m]
check("E3 an unknown strategy still WARNS 'has no exit route' (a real one still wakes)",
      out_x == ["SWEEP"] * 3 and len(_xl) == 1 and _xl[0][0] == "WARNING", str(logs_x))

spec = importlib.util.spec_from_file_location("_aw", os.path.join(ROOT, "tools", "agent_watch.py"))
aw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aw)


def flags(msg, level):
    line = "2026-09-30 14:00:25 [%-5s] execution.exit_engine: %s\n" % (level, msg)
    with open(os.environ["OT_BOT_LOG"], "w") as fh:
        fh.write(line)
    for p in (os.environ["OT_AGENT_WATCH_STATE"], os.environ["OT_AGENT_EVENTS"]):
        if os.path.exists(p):
            os.unlink(p)
    import io
    buf = io.StringIO()
    w = aw.Watch(now=lambda: 1790776900.0, out=buf)
    w.since = w.st["since"] = 1790776900.0 - 6 * 3600
    w.scan_log()
    return [l for l in buf.getvalue().splitlines() if "AGENT-EVENT" in l]


_fb = flags(_bl[0] if _bl else "", "INFO")
_fx = flags(_xl[0][1] if _xl else "", "WARNING")
check("E4 the agent watcher does not flag the Breakout line, and still flags the other",
      _fb == [] and len(_fx) == 1 and "no_exit_route" in _fx[0], f"breakout={_fb} other={_fx}")

import shutil                                                    # noqa: E402
shutil.rmtree(_TMP, ignore_errors=True)
print()
if FAIL:
    print(f"RED — {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN — Breakout's exit line tells the truth; a real unrouted strategy still wakes")
sys.exit(0)
