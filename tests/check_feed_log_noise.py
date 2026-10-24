"""tests/check_feed_log_noise.py — v1.1
v1.1  2026-09-26  OTV4TEST r146 — L7 re-pointed to adjacency: main() now opens with the UNSET guard, so basicConfig is no longer the first call; the property - the filter installed on the very next statement, before anything logs - is pinned unchanged.
THE FEED'S JOURNAL CARRIES THE FEED, NOT THE SDK'S WEBSOCKET FRAMES — AND
DROPPED DATA STAYS VISIBLE.

v1.0  2026-09-24 — OTV4TEST r134. tastytrade 13.2.3 hard-sets its logger to
      DEBUG (tastytrade/__init__.py:13), so every frame passed data/candle_feed.py's
      INFO basicConfig: MEASURED 2,895 of 2,988 journal lines in five minutes. One
      kind of SDK DEBUG line is not chatter: "Failed to parse event" is a print
      the SDK THREW AWAY (173 in 30 minutes, all fractional-share TimeAndSale
      sizes). The filter must drop the first and keep the second.

  L0  the premise still holds: the SDK's logger is at DEBUG (else this is moot)
  L1  SDK DEBUG chatter from a CHILD logger (tastytrade.streamer) is dropped
  L2  SDK DEBUG "Failed to parse event" is KEPT
  L3  SDK WARNING and above are kept
  L4  our own loggers are not touched by the filter
  L5  END TO END: root handler + the real installer + the real SDK loggers —
      chatter absent from the output, the parse failure present
  L6  installing twice adds ONE filter per handler
  L7  main() installs it immediately after basicConfig (AST)
"""
from __future__ import annotations

import ast
import glob as _glob
import io
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


try:
    import tastytrade                                            # noqa: F401
    import data.candle_feed as cf
except Exception as exc:                                         # noqa: BLE001
    check("L0 import data.candle_feed and tastytrade", False, "%s: %s" % (type(exc).__name__, exc))
    print(f"\nRED — {len(FAILED)} of {len(RAN)}")
    sys.exit(1)

F = getattr(cf, "_TTNoiseFilter", None)
INSTALL = getattr(cf, "_install_tt_noise_filter", None)


def _rec(name, level, msg):
    return logging.LogRecord(name, level, __file__, 1, msg, None, None)


check("L0 the SDK's own logger is at DEBUG (the reason this filter exists)",
      logging.getLogger("tastytrade").level == logging.DEBUG,
      "level=%s" % logging.getLogger("tastytrade").level)
check("L0 the filter and its installer exist", F is not None and INSTALL is not None)
if F is None or INSTALL is None:
    print(f"\nRED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)

f = F()
check("L1 SDK DEBUG chatter from a child logger is dropped",
      not f.filter(_rec("tastytrade.streamer", logging.DEBUG, "received message: {'type': 'FEED_DATA'}"))
      and not f.filter(_rec("tastytrade", logging.DEBUG, "sending keepalive message")))
check("L2 SDK DEBUG 'Failed to parse event' is KEPT (dropped data stays visible)",
      f.filter(_rec("tastytrade.streamer", logging.DEBUG,
                    "Failed to parse event: 1 validation error for TimeAndSale, skipping")))
check("L3 SDK WARNING and above are kept",
      f.filter(_rec("tastytrade.streamer", logging.WARNING, "reconnecting"))
      and f.filter(_rec("tastytrade", logging.ERROR, "boom")))
check("L4 our own loggers pass untouched, even at DEBUG",
      f.filter(_rec("data.candle_feed", logging.DEBUG, "feed stream traceback"))
      and f.filter(_rec("root", logging.DEBUG, "received message: looks like the SDK's")))


def _l5():
    root = logging.getLogger()
    saved = root.handlers[:], root.level
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    try:
        root.handlers[:] = [h]
        root.setLevel(logging.INFO)
        INSTALL()
        sl = logging.getLogger("tastytrade.streamer")
        sl.debug("received message: {'type': 'FEED_DATA'}")
        sl.debug("sending keepalive message")
        sl.debug("Failed to parse event: 1 validation error for TimeAndSale, skipping")
        sl.warning("websocket closed")
        out = buf.getvalue()
        n_filters = sum(isinstance(x, F) for x in h.filters)
        INSTALL()
        n_after = sum(isinstance(x, F) for x in h.filters)
        return out, n_filters, n_after
    finally:
        root.handlers[:], _lvl = saved[0], None
        root.setLevel(saved[1])


out, n1, n2 = _l5()
check("L5 end to end: chatter absent, parse failure and warning present",
      "received message" not in out and "keepalive" not in out
      and "Failed to parse event" in out and "websocket closed" in out, repr(out[:200]))
check("L6 installing twice adds one filter per handler", n1 == 1 and n2 == 1, "%d then %d" % (n1, n2))


def _l7():
    tree = ast.parse(open(os.path.join(ROOT, "data", "candle_feed.py"), encoding="utf-8").read())
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    if fn is None:
        return False
    # r146 — RE-POINTED, NOT DROPPED (§38.4): main() now opens with the UNSET-instrument
    # guard, so the pin is on ADJACENCY, not position - basicConfig, and the very
    # next statement installs the filter, before anything can log.
    def _name(n):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
            return getattr(n.value.func, "attr", getattr(n.value.func, "id", ""))
        return ""
    names = [_name(n) for n in fn.body[:8]]
    return ("basicConfig" in names and names.index("basicConfig") + 1 < len(names)
            and names[names.index("basicConfig") + 1] == "_install_tt_noise_filter")


check("L7 main() installs the filter immediately after basicConfig", _l7())

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
