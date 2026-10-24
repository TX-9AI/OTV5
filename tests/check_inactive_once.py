#!/usr/bin/env python3
"""
tests/check_inactive_once.py  v1.0

v1.0  2026-09-21  OTV4TEST r73 — INACTIVE SAYS SO ONCE, AND A CLOCK IN THE
      REASON IS WHAT STOPPED IT. Born RED at f378651 (r72).

r41 made the INACTIVE row EDGE-TRIGGERED on (trading-day, verdict, reason,
gate) — the operator, 2026-09-18: *"Because we know a plan is inactive outside
its window, I don't need 10k rows explaining why. I just need 1, so I'm aware
it at least KNOWS."* The rule was correct and NEVER FAILED; it was DEFEATED,
because `risk/session_guard.py` stamped `fmt_et_short()` into two refusal
reasons and a clock makes every tick a DIFFERENT reason.

MEASURED on the live store before the fix: 327 distinct INACTIVE reasons
all-time, 306 of them (94%) clock-variants of ONE message; strip the clock and
327 collapse to 22. On 2026-09-21 that was 65 rows per strategy before 09:35,
across 9 strategies, every session.

🔑 THIS GATE TESTS THE CLASS, NOT THE STRING (§20). I1 refuses ANY refusal
reason returned by the session guard that carries a clock, so the next author
cannot reintroduce the defect by writing a different sentence. I5 is the
CONTROL that keeps me honest in the other direction: a genuinely DIFFERENT
reason must still announce, because r41 deliberately kept that — *"a DIFFERENT
cap break still declares itself"* — and a fix that silenced it would trade one
defect for a worse one.

  I0  modules import
  I1  CLASS: no refusal reason from the session guard contains a clock
  I2  the two specific reasons are clean (the strings this revision changed)
  I3  the latch HOLDS: same state twice -> one row  (drives _status_changed)
  I4  BORN-RED PROOF: a clocked reason breaks the latch on the same code
  I5  CONTROL: a genuinely different reason STILL announces
  I6  CONTROL: a new trading day re-announces

Run:  python3 tests/check_inactive_once.py
"""
from __future__ import annotations
import os, re, sys, ast
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])

_err = ""
try:
    from strategy.plan import _status_changed, _STATUS, _SEEN, _SEEN_DAY
    _ok = True
except Exception as exc:                                   # noqa: BLE001
    _err = f"{type(exc).__name__}: {exc}"; _ok = False
check("I0 plan latch imports", _ok, _err)
if not _ok:
    print(f"\nFAIL: {len(FAIL)} problem(s) {FAIL}")
    sys.exit(1)

# ── I1 — THE CLASS. Every `return False, <str>` in the session guard is a
#    refusal REASON that reaches the plan row. None may carry a clock.
#    Read by AST so an f-string's PIECES are inspected, not its rendered text:
#    a formatted call like fmt_et_short() has no literal to grep for.
SRC = os.path.join(ROOT, "risk", "session_guard.py")
tree = ast.parse(open(SRC).read())
# ⚠️ THE PATTERN IS "READS THE CURRENT CLOCK", NOT "FORMATS A TIME".
# My first cut flagged `_BUTTERFLY_CUTOFF.strftime('%H:%M')` — but that is a
# CONSTANT (`dtime(BUTTERFLY_ENTRY_CUTOFF_ET...)`), so it renders ONE string
# every tick and cannot defeat the latch; the live store holds 0 distinct
# variants of it. A canary that refuses a correct line teaches the operator to
# ignore reds (§36), so the pattern was tightened rather than the line exempted.
CLOCKY = re.compile(r"fmt_et_short|now_et\s*\(|datetime\.now|\.utcnow|time\.time\s*\(", re.I)
offenders = []
for node in ast.walk(tree):
    if not (isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple)):
        continue
    if len(node.value.elts) != 2:
        continue
    first = node.value.elts[0]
    if not (isinstance(first, ast.Constant) and first.value is False):
        continue
    reason = node.value.elts[1]
    txt = ast.unparse(reason)
    if CLOCKY.search(txt):
        offenders.append(f"line {node.lineno}: {txt[:70]}")
check("I1 CLASS: no session-guard refusal reason carries a clock",
      not offenders,
      "; ".join(offenders) or f"{sum(1 for n in ast.walk(tree) if isinstance(n, ast.Return))} returns scanned")

# ── I2 — the two strings this revision changed, by their stable prefix
txt = open(SRC).read()
check("I2 'outside RTH' and the 09:35 floor are clock-free",
      'return False, "outside RTH"' in txt
      and 'return False, "opening range still forming (<9:35 ET) — no entries"' in txt,
      "the two reasons r73 changed")

# ── I3/I4/I5/I6 — DRIVE the real latch ─────────────────────────────────────
def fresh():
    _STATUS.clear(); _SEEN.clear(); _SEEN_DAY.clear()

DAY = "2026-09-21"
CLEAN = "opening range still forming (<9:35 ET) — no entries"

fresh()
first = _status_changed("ORBStrategy", DAY, "INACTIVE", CLEAN, "orb_window")
rest  = [_status_changed("ORBStrategy", DAY, "INACTIVE", CLEAN, "orb_window") for _ in range(64)]
check("I3 the latch HOLDS: 65 identical ticks -> exactly ONE row",
      first and not any(rest), f"first={first} further_writes={sum(1 for x in rest if x)}")

fresh()
clocked = [_status_changed("ORBStrategy", DAY, "INACTIVE",
                           f"{CLEAN} (09/21 09:{m:02d} ET)", "orb_window") for m in range(65)]
check("I4 BORN-RED PROOF: a CLOCKED reason breaks the same latch",
      sum(1 for x in clocked if x) == 65,
      f"{sum(1 for x in clocked if x)} of 65 ticks wrote a row — this is the defect r73 removes")

fresh()
_status_changed("ORBStrategy", DAY, "INACTIVE", CLEAN, "orb_window")
diff = _status_changed("ORBStrategy", DAY, "INACTIVE",
                       "catastrophic cap broken", "catastrophic_cap")
check("I5 CONTROL: a genuinely DIFFERENT reason still announces",
      diff, "r41 kept this on purpose — silencing it would be a worse defect")

fresh()
_status_changed("ORBStrategy", DAY, "INACTIVE", CLEAN, "orb_window")
nextday = _status_changed("ORBStrategy", "2026-09-22", "INACTIVE", CLEAN, "orb_window")
check("I6 CONTROL: a new trading day re-announces once", nextday,
      "keyed by trading date, so a session does not inherit yesterday's silence")

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
