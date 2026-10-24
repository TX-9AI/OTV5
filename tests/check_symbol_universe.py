#!/usr/bin/env python3
"""tests/check_symbol_universe.py — v1.0
THE TRADEABLE UNIVERSE IS THE MEASURED TOP 75, AND A SYMBOL OFF IT IS REFUSED
AT EVERY DOOR: THE INSTALLER, THE BOT, AND THE FEED.

v1.0  2026-09-29 — OTV4TEST r175 (SYM.1). The operator, 2026-09-29: "probably
      the 50 most liquid names ... bump it up to 75. Any list that would include
      AAL and Sofi would be the right number", then "Yes to all" (ATM spread
      <= 10%, keep every existing symbol). Until r175 an unlisted OT_INSTRUMENT
      installed, streamed and traded on a silent $1 strike step
      (STRIKE_INCREMENTS.get(INSTRUMENT, 1)).
  U1  >= 75 listed, SOFI and AAL among them, and every pre-r175 symbol kept
  U2  every step is one of the ladders listed chains use (0.5 1 2.5 5), and
      every penny class is a listed symbol
  U3  config.INSTRUMENT_LISTED: True for SOFI, False for an unlisted symbol
  U4  the REAL main.py refuses an unlisted symbol: exit 78, named, and nothing
      logged in (HOME is a temp dir, so the live bot.log is never opened)
  U5  the REAL candle feed (`python -m data.candle_feed`, the unit's own
      command) refuses it: exit 78, named
  U6  the REAL setup_ec2.sh --plan stops at step 1 on an unlisted symbol and
      passes a listed one (sudo stubbed to refuse; nothing is installed)
  U7  retention keeps 5m and 15m >= 30 days (the first-boot backfill), and
      config's declared copy agrees with the purge's
  U8  configure.sh item 1's list, run through its REAL line, fits 76 columns
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
import glob as _glob                                            # noqa: E402
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []
PY = os.path.join(_root, "venv", "bin", "python")
PY = PY if os.path.exists(PY) else sys.executable


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


SRC = open(os.path.join(_root, "config.py")).read()


def _lit(name):
    m = re.search(r"^%s = (\{.*?\n\})" % name, SRC, re.S | re.M)
    return ast.literal_eval(m.group(1)) if m else {}


SI, PC = _lit("STRIKE_INCREMENTS"), _lit("PENNY_CLASSES")
PRE_R175 = {"SPY", "QQQ", "SPX", "IWM", "DIA", "SMH", "TLT", "GLD", "AAPL", "MSFT", "META",
            "MU", "TSLA", "NVDA", "NFLX", "ORCL", "SMCI", "PLTR", "AMD", "AMZN", "GOOGL",
            "XOM", "CVX", "JPM", "GS", "LLY", "UNH", "AVGO", "CRM", "COST", "SOFI", "AAL"}
UNLISTED = "ZZZQ"
_D = {}

guard("U1 >= 75 listed, SOFI and AAL in, every pre-r175 symbol kept",
      lambda: len(SI) >= 75 and {"SOFI", "AAL"} <= set(SI) and PRE_R175 <= set(SI),
      lambda: "%d listed; missing pre-r175: %s" % (len(SI), sorted(PRE_R175 - set(SI))))
guard("U2 every step is a real ladder (0.5/1/2.5/5); every penny class is listed",
      lambda: set(SI.values()) <= {0.5, 1, 2.5, 5} and set(PC) <= set(SI),
      lambda: "steps %s; penny not listed: %s" % (sorted(set(SI.values())), sorted(set(PC) - set(SI))))


def _cfg(sym):
    r = subprocess.run([PY, "-c", "import config; print(config.INSTRUMENT_LISTED)"],
                       cwd=_root, capture_output=True, text=True, timeout=120,
                       env={**os.environ, "OT_INSTRUMENT": sym})
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-120:]


guard("U3 INSTRUMENT_LISTED: True for SOFI, False for an unlisted symbol",
      lambda: (_D.setdefault("u3", (_cfg("SOFI"), _cfg(UNLISTED)))) == ("True", "False"),
      lambda: str(_D.get("u3")))


def _home():
    return tempfile.mkdtemp(prefix="symu_")


def _u4():
    h = _home()
    r = subprocess.run([PY, "main.py", "--service"], cwd=_root, capture_output=True, text=True,
                       timeout=180, env={**os.environ, "OT_INSTRUMENT": UNLISTED, "HOME": h,
                                         "OT_TRADES_DB": os.path.join(h, "t.db")})
    _D["u4"] = (r.returncode, r.stderr.strip()[-160:])
    return (r.returncode == 78 and "not in config.STRIKE_INCREMENTS" in r.stderr
            and "TastyTrade session established" not in r.stdout + r.stderr)


guard("U4 the REAL main.py refuses an unlisted symbol (exit 78, named, no login)", _u4,
      lambda: str(_D.get("u4")))


def _u5():
    h = _home()
    r = subprocess.run([PY, "-m", "data.candle_feed"], cwd=_root, capture_output=True, text=True,
                       timeout=180, env={**os.environ, "OT_INSTRUMENT": UNLISTED, "HOME": h})
    _D["u5"] = (r.returncode, r.stderr.strip()[-160:])
    return r.returncode == 78 and "not in config.STRIKE_INCREMENTS" in r.stderr


guard("U5 the REAL candle feed refuses an unlisted symbol (exit 78, named)", _u5,
      lambda: str(_D.get("u5")))


def _setup(sym):
    h = _home()
    stubs = os.path.join(h, "stubs")
    os.makedirs(stubs)
    with open(os.path.join(stubs, "sudo"), "w") as fh:
        fh.write('#!/bin/sh\necho "REFUSED sudo $*" >&2\nexit 90\n')
    os.chmod(os.path.join(stubs, "sudo"), 0o755)
    env = {"PATH": stubs + ":/usr/bin:/bin", "HOME": h, "OT_INSTRUMENT": sym,
           "TT_CLIENT_SECRET": "fx", "TT_REFRESH_TOKEN": "fx", "TT_ACCOUNT_NUMBER": "fx",
           "TELEGRAM_TOKEN": "fx", "TELEGRAM_CHAT_ID": "fx"}
    return subprocess.run(["setsid", "-w", "bash", os.path.join(_root, "setup_ec2.sh"), "--plan"],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env,
                          timeout=120)


def _u6():
    bad, good = _setup(UNLISTED), _setup("SOFI")
    _D["u6"] = (bad.returncode, bad.stdout[-160:], good.returncode)
    return (bad.returncode != 0 and "is not a listed symbol" in bad.stdout
            and "Defaults: " + UNLISTED not in bad.stdout
            and "is not a listed symbol" not in good.stdout and "Defaults: SOFI" in good.stdout)


guard("U6 the REAL setup_ec2.sh --plan stops on an unlisted symbol, passes a listed one", _u6,
      lambda: str(_D.get("u6")))


def _u7():
    from warehouse import retention_purge as rp
    m = re.search(r"^# RETENTION_DAYS = \{(.*?)\n# \}", SRC, re.S | re.M)
    decl = dict(re.findall(r'"(\w+)":\s*(\w+)', m.group(1))) if m else {}
    _D["u7"] = (rp.RETENTION_DAYS, decl)
    return (rp.RETENTION_DAYS["5m"] >= 30 and rp.RETENTION_DAYS["15m"] >= 30
            and decl.get("5m") == str(rp.RETENTION_DAYS["5m"])
            and decl.get("15m") == str(rp.RETENTION_DAYS["15m"]))


guard("U7 retention keeps 5m/15m >= 30 days and config's declared copy agrees", _u7,
      lambda: str(_D.get("u7")))


def _u8():
    line = next(l for l in open(os.path.join(_root, "configure.sh")) if "${allowed}" in l
                and "echo" in l and "Could not" not in l)
    allowed = " ".join(sorted(SI))
    r = subprocess.run(["bash", "-c", line], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "allowed": allowed})
    lines = r.stdout.splitlines()
    got = set(" ".join(lines).split())
    _D["u8"] = (max((len(x) for x in lines), default=0), len(lines))
    return lines and max(len(x) for x in lines) <= 76 and got == set(SI)


guard("U8 configure.sh item 1's REAL list line fits 76 columns, every symbol shown", _u8,
      lambda: "widest %s over %s lines" % _D.get("u8", ("?", "?")))

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
