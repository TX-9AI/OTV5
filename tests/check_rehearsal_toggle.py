#!/usr/bin/env python3
"""
tests/check_rehearsal_toggle.py  v1.1
v1.1  2026-10-18  OTV4TEST r301 (LOG.1) — G6a-c: outside RTH a zero-marks chain is INFO once per expiry and the
      rehearsal's chain miss INFO once per day; inside RTH both stay as loud as before (audit 10-18 E3). RED before.

r108 — THE PRE-OPEN REHEARSAL HAS A GO-RED TOGGLE, AND IT FAILS TOWARD RUNNING.

Operator, 2026-08-24, asking the right question three weeks early: "Is there a
danger of forgetting it's on 3 weeks from now & we come off paper & go live?"

  G1  the flag is read LIVE (no cache) — devtools fans it out with no restart
  G2  its PRESENCE disables; ABSENCE runs. A fresh or rebuilt box rehearses
  G3  an unreadable path FAILS TOWARD RUNNING
  G4  the disabled notice is said ONCE per process, not once a minute
  G5  ⚠️ THE SAFETY IS NOT THE TOGGLE. Every order site is behind
      entries_open(), which requires is_rth() AND is_orb_complete() — so the
      rehearsal cannot place whether it is on, off, paper or LIVE. This is the
      assertion that has to survive the next strategy someone adds.

Run:  python3 tests/check_rehearsal_toggle.py
"""
from __future__ import annotations
import ast, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

import main as _m

# ── G1/G2/G3 — the flag's behaviour, driven for real ─────────────────────────
_saved = _m._REHEARSAL_FLAG
tmp = tempfile.mkdtemp()
try:
    _m._REHEARSAL_FLAG = os.path.join(tmp, "REHEARSAL_OFF")
    check("G2a absent flag -> rehearsal RUNS", _m._rehearsal_disabled() is False)
    open(_m._REHEARSAL_FLAG, "w").close()
    check("G2b present flag -> rehearsal OFF", _m._rehearsal_disabled() is True)
    os.remove(_m._REHEARSAL_FLAG)
    check("G1 the read is LIVE — removing the flag re-enables with no restart",
          _m._rehearsal_disabled() is False)
    _m._REHEARSAL_FLAG = "\x00/not/a/path"
    check("G3 an unreadable path FAILS TOWARD RUNNING",
          _m._rehearsal_disabled() is False)
finally:
    _m._REHEARSAL_FLAG = _saved

# ── G4 — one line, not one a minute ──────────────────────────────────────────
class _S:
    pass
s = _S()
_m._rehearsal_note(s)
check("G4a the notice latches", getattr(s, "_rehearsal_noted", False) is True)
_m._rehearsal_note(s)          # must be a no-op
check("G4b and does not repeat", getattr(s, "_rehearsal_noted", False) is True)

# ── G5 — THE ORDER SITES ARE THE SAFETY, NOT THE TOGGLE ──────────────────────
# Enumerate every place an order is SUBMITTED to open a position and assert each
# is behind entries_open(). This is the assertion that fails when someone adds a
# fourth path — the AFD.1 shape, where the gate is one the NEXT strategy lacks.
msrc = open(os.path.join(ROOT, "main.py")).read()
esrc = open(os.path.join(ROOT, "execution/entry_engine.py")).read()
mfns = {n.name: ast.unparse(n) for n in ast.walk(ast.parse(msrc))
        if isinstance(n, ast.FunctionDef)}
efns = {n.name: ast.unparse(n) for n in ast.walk(ast.parse(esrc))
        if isinstance(n, ast.FunctionDef)}
for where, src in (("_execute_condor_leg (all 4 credit triggers)", mfns.get("_execute_condor_leg", "")),
                   ("entry_engine.enter (single leg + butterfly)", efns.get("enter", ""))):
    check(f"G5 {where} is behind entries_open()", "entries_open()" in src)

from utils.time_utils import entries_open, ET
from datetime import datetime
check("G5c entries_open requires RTH — 20:00 refuses even post-09:35",
      entries_open(datetime(2026, 8, 25, 20, 0, tzinfo=ET)) is False)
check("G5d and it is not paper-only: nothing in the gate reads PAPER_TRADING",
      "PAPER" not in ast.unparse(next(
          n for n in ast.walk(ast.parse(open(
              os.path.join(ROOT, "utils/time_utils.py")).read()))
          if isinstance(n, ast.FunctionDef) and n.name == "entries_open")))

# ── G6 (r301, LOG.1) — THE REHEARSAL IS QUIET ABOUT THE CHAIN IT CANNOT HAVE ──────
# Measured 2026-10-12..16: 2,417 "Chain FAIL-LOUD" ERROR lines and 2,428 "Could not fetch options chain"
# WARNINGs, every one between 16:00 and 23:59 ET - the r101 rehearsal asking for marks that are gone
# after the bell. Inside RTH both stay exactly as loud as before.
import logging as _lg
try:
    import data.options_chain as _OC
    _OC._ZERO_MARKS_SAID.clear()
    seq_out = [_OC.zero_marks_log_level("QQQ", "2026-10-19", in_rth=False) for _ in range(3)]
    seq_in = [_OC.zero_marks_log_level("QQQ", "2026-10-19", in_rth=True) for _ in range(3)]
    other = _OC.zero_marks_log_level("QQQ", "2026-10-20", in_rth=False)
    check("G6a outside RTH a zero-marks chain is INFO once per expiry, then silent; another expiry is said once",
          seq_out == ["info", "", ""] and other == "info", f"outside={seq_out} other={other!r}")
    check("G6b inside RTH it is ERROR on every build (FAIL-LOUD unchanged)", seq_in == ["error"] * 3, f"inside={seq_in}")
except AttributeError as exc:
    check("G6a outside RTH a zero-marks chain is INFO once per expiry, then silent", False, f"no helper: {exc}")
    check("G6b inside RTH it is ERROR on every build (FAIL-LOUD unchanged)", False, f"no helper: {exc}")
try:
    _lines = []

    class _Cap(_lg.Handler):
        def emit(self, r):
            _lines.append((r.levelname, r.getMessage()))
    _h = _Cap(); _lg.getLogger("main").addHandler(_h); _lg.getLogger("main").setLevel(_lg.INFO)
    try:
        _m._CHAIN_MISS_SAID.clear()
        r1 = [_m._chain_miss_say(True) for _ in range(3)]
        r2 = [_m._chain_miss_say(False) for _ in range(2)]
    finally:
        _lg.getLogger("main").removeHandler(_h)
    infos = [l for l in _lines if l[0] == "INFO" and "no options chain outside RTH" in l[1]]
    warns = [l for l in _lines if l[0] == "WARNING" and "Could not fetch options chain" in l[1]]
    check("G6c the rehearsal's chain miss is INFO once per day; inside RTH it stays a WARNING every tick",
          r1 == ["info", "", ""] and r2 == ["warning", "warning"] and len(infos) == 1 and len(warns) == 2,
          f"rehearsal={r1} rth={r2} infos={len(infos)} warnings={len(warns)}")
except AttributeError as exc:
    check("G6c the rehearsal's chain miss is INFO once per day; inside RTH it stays a WARNING every tick", False,
          f"no helper: {exc}")

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
