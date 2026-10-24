#!/usr/bin/env python3
"""
tests/check_plan_heartbeat.py  v1.3
v1.3  2026-10-06  OTV4TEST r257 — H4's FROZEN HEARTBEATS ARE WRITTEN UNDER THE PANEL'S OWN INSTRUMENT.
      r252 (BOX.18) made query.show_decisions read plan_heartbeat WHERE symbol=query.INSTRUMENT; this
      fixture wrote the literal "QQQ", so under OT_INSTRUMENT=SPX the panel read nothing and H4 went red
      for that reason alone (SPX-TEST's 08:05 sweep, 10-06). Green on QQQ by construction. Found, measured
      and proposed by SPX-TEST. No assertion changed.
v1.2  2026-09-22  OTV4TEST r91 — H4/H5 FREEZE THE CLOCK. They drive the real
      panel, and `show_decisions` returns early before 09:30 ET, so from r86
      (sweep moved to the 08:00 BOOT) they failed EVERY morning for a reason
      unrelated to the panel. §40.1: the wall clock was supplying the answer.
v1.1  2026-09-21  OTV4TEST r84 — H6/H7/H8. Born red 3 of 9 at
      674c8d5, H6 naming all 13 ungated call sites.
v1.0  2026-09-21  OTV4TEST r83 — born RED at 0e4c8f1.

🔴 THE PLANS PANEL WAS MEASURING PUNCTUATION. It asked "is this plan stale?"
by comparing the newest `plan_tick` row against a 300-second cut. r41 made
those rows EDGE-TRIGGERED by the operator's own ruling, so a plan behaving
perfectly writes nothing and turns "stale" five minutes later. MEASURED
2026-09-21 14:44: **16 of 18 rows flagged ⚠️ STALE and all 16 were correct**;
the only two that read "fresh" were the two whose reason text embeds live
prices, so every tick produced a new string.

Operator: *"I wanna see on that page if my strategies are actively evaluating
the feed. If they're not then say that, and if they are tell me what they're
looking at."* And: *"I don't think stale needs to be the same thing as window
closed. Report stale if it really is stale and report window closed if that's
the reason."*

  H1  UPSERT, NOT APPEND — the table cannot grow (r41's ruling is untouched)
  H2  a plan that RAN reads EVALUATING
  H3  CLASS: the gate is CARRIED from BOTH mechanisms, never parsed from prose
  H4  a window-closed plan reads WINDOW CLOSED and NOT stale
  H5  a plan in the admission table that never heartbeat is surfaced

Run:  python3 tests/check_plan_heartbeat.py
"""
from __future__ import annotations
import io as _io, os, sys, tempfile, time, contextlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = tempfile.mkdtemp(prefix="check_plan_heartbeat.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))

FAIL: list = []
def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])

import strategy.plan as P

# ⚠️ H0 IS A GUARD, NOT A CHECK (the r72/V0 pattern). At a base without r83
# this file would otherwise die on an AttributeError traceback — "born red" in
# the sense that it exits non-zero, but naming nothing. A gate that cannot say
# WHAT is missing teaches the reader to skim the red (§36).
_missing = [n for n in ("_write_heartbeats", "ensure_tables", "_SKIP_GATE", "REGISTRY")
            if not hasattr(P, n)]
check("H0 strategy.plan exposes the heartbeat machinery",
      not _missing, f"missing={_missing} — r83 has not landed in this tree")
if _missing:
    print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
    sys.exit(1)


class _FakePlan:
    def __init__(self, verdict, why, wrote, gate=""):
        self._v, self._w, self._wrote = verdict, why, wrote
        if gate:
            self._last_gate = gate
    def last(self):
        return (1, self._v, self._w)
    def wrote_this_tick(self):
        return self._wrote

from data.derived_store import get_derived_store
store = get_derived_store()
# the same helper the bot uses — never a hand-rolled CREATE, or the fixture
# could pass against a schema production does not have (§0.4)
P.ensure_tables(store)

P.REGISTRY.clear()
P.REGISTRY["Alpha"] = _FakePlan("HOLD", "reading the tape", True)
P.REGISTRY["Beta"]  = _FakePlan("INACTIVE", "inactive — window: Beta is outside 09:35-11:30 ET", False)
P._SKIP_GATE.clear(); P._SKIP_GATE["Beta"] = "window"
P._ASKED.clear()

P._write_heartbeats(store, "QQQ", 7, time.time())
P._write_heartbeats(store, "QQQ", 8, time.time())      # twice: UPSERT, not append

rows = list(store.conn.execute(
    "SELECT plan, state, gate, verdict FROM plan_heartbeat WHERE symbol='QQQ' ORDER BY plan"))
n_alpha = list(store.conn.execute(
    "SELECT COUNT(*) FROM plan_heartbeat WHERE symbol='QQQ' AND plan='Alpha'"))[0][0]

check("H1 UPSERT, not append — two ticks leave ONE row per plan",
      n_alpha == 1, f"Alpha rows={n_alpha} — r41's ruling governs the LEDGER; "
                    f"this is current state and must not grow")

_by = {r[0]: r for r in rows}
check("H2 a plan that RAN reads EVALUATING",
      _by.get("Alpha", (None, None))[1] == "EVALUATING",
      f"Alpha={_by.get('Alpha')}")

# 🔑 H3 IS THE CLASS CHECK AND IT FAILED TWICE IN DEVELOPMENT. The gate reaches
# the board by TWO different mechanisms — `_report_block` for a plan that ran
# and refused itself, `_SKIP_GATE` for one that was never asked — and the first
# two cuts read only one, so every window-closed plan came out a bare HELD.
check("H3 CLASS: the gate is CARRIED from the not-asked path, not parsed",
      _by.get("Beta", (None, None, None))[2] == "window",
      f"Beta gate={_by.get('Beta', (None,None,''))[2]!r} — parsing it back out "
      f"of 'inactive — window: ...' is what broke twice")

# H4/H5 drive the REAL panel and read what the operator would read.
# 🔴 r91 — THE CLOCK IS FROZEN, AND THAT IS THE WHOLE FIX. `show_decisions`
# returns early before 09:30 ET — "nothing yet — the session opens at 09:30 ET"
# — so both of these asserted against an EMPTY panel and went red for a reason
# that had nothing to do with the panel. They passed at r83/r84 only because
# every run until then happened during or after the session. r86 moved the full
# sweep to the 08:00 BOOT, which is before the open BY CONSTRUCTION, so from
# that revision on these two would have failed every single morning, forever.
# ⚠️ §40.1 EXACTLY — "a probe run in a shell that exported the thing under
# test destroyed the RUNTIME." Here the WALL CLOCK supplied the answer, and a
# check whose verdict depends on when it ran is a check about nothing.
# ⚠️ THE HEARTBEATS MOVE WITH THE CLOCK, AND THEY MUST. The panel's staleness
# test is `now - ts_epoch > STALE_S`, so freezing the clock WITHOUT restamping
# the rows would read every plan ⚠️ STALE and fail H4 from the other side —
# swapping one clock artefact for its mirror image. ONE instant, used by the
# writer and the reader alike.
import query
_frozen = query.now_et().replace(hour=12, minute=0, second=0, microsecond=0)
P._write_heartbeats(store, query.INSTRUMENT or "QQQ", 9, _frozen.timestamp())   # r257: the panel's own symbol
_real_now_et = query.now_et
query.now_et = lambda: _frozen
buf = _io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        try:
            query.show_decisions(store.conn)
        except Exception as e:                                  # noqa: BLE001
            print(f"panel raised: {e}")
finally:
    query.now_et = _real_now_et           # never leave the module patched
out = buf.getvalue()
check("H4 a window-closed plan reads WINDOW CLOSED and never STALE",
      ("WINDOW CLOSED" in out) and ("STALE" not in out),
      f"window_closed={'WINDOW CLOSED' in out} stale_present={'STALE' in out}")

check("H5 a plan in the admission table that never heartbeat is SURFACED",
      "NOT RUNNING" in out,
      "a plan that is never constructed cannot heartbeat; asking the heartbeat "
      "who exists would hide exactly the failure this panel is for")

# ── H6 — THE CLASS: EVERY SKIP SITE PASSES A GATE (r84) ───────────────────
# 🔴 MEASURED 2026-09-21: 15 of 16 `_plan_skip`/`_plan_skip_all` calls in
# main.py passed NO gate, so every refusal that was not the clock reached the
# board unlabelled and rendered as a bare "HELD" — including the butterflies'
# one-per-session quota, which the operator asked to see named: *"shouldn't
# the plan say something about that? Something like quota hit."*
# ⚠️ `_plan_skip`'s OWN DOCSTRING ALREADY WARNED ABOUT THIS — "recovering a
# gate by parsing the reason sentence is how that rule would quietly stop
# working the first time someone reworded a message" — and 15 call sites
# ignored it anyway. A rule stated in prose and unenforced decays; this is the
# enforcement.
import ast as _ast
_src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "main.py"), encoding="utf-8").read()
_ungated = []
for node in _ast.walk(_ast.parse(_src)):
    if (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name)
            and node.func.id in ("_plan_skip", "_plan_skip_all")):
        if not any(k.arg == "gate" for k in node.keywords):
            _ungated.append(node.lineno)
check("H6 CLASS: every _plan_skip call site passes a gate",
      not _ungated,
      f"ungated at main.py lines {_ungated} — an unlabelled refusal renders "
      f"as a bare HELD and the board cannot name why")

# ── H7 — THE PLAN IS BUILT ON CONSTRUCTION, NOT ON FIRST USE (r84) ────────
# 🔴 Breakout built its plan lazily in `_plan_()`, so outside 09:35-11:30
# nothing called `prepare()`, `BreakoutPlan()` was never constructed, and it
# entered NO registry at all: no heartbeat, absent from the board, and nothing
# could tell "not yet constructed" from "crashed". THIS IS r77 IN A DIFFERENT
# COSTUME — there a lazy IMPORT let check_imports pass green on a strategy
# raising every tick; here a lazy CONSTRUCTION hides the plan from every
# registry-based check.
_cases = [("Breakout", "strategy.breakout", "Breakout"),
          ("VOLT", "strategy.volt_strategy", "VoltStrategy")]
_lazy = []
for want, mod, cls in _cases:
    P.REGISTRY.clear()
    try:
        m = __import__(mod, fromlist=[cls])
        getattr(m, cls)()
        if want not in P.REGISTRY:
            _lazy.append(f"{cls} -> {sorted(P.REGISTRY)}")
    except Exception as e:                                      # noqa: BLE001
        _lazy.append(f"{cls} raised {type(e).__name__}: {e}")
check("H7 CLASS: constructing a strategy registers its plan immediately",
      not _lazy,
      f"lazy={_lazy} — a plan that registers only on first use is invisible "
      f"to every board and every checker until its window opens")

# ── H8 — the gate vocabulary reaches the reader ──────────────────────────
import inspect as _insp
_qsrc = _insp.getsource(query.show_decisions)
check("H8 the board names the session quota rather than a bare HELD",
      '"tries_per_session": "QUOTA HIT"' in _qsrc,
      "expected a tries_per_session -> QUOTA HIT mapping in the panel")

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
