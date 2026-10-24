#!/usr/bin/env python3
"""check_plan_signal.py — v1.6
v1.6  2026-09-22  OTV4TEST r92 — PS8 pins the r84 gate-word mapping instead of the old
      panel's "hushed" line. One row per plan makes one line per plan
      structural rather than suppressed, and WINDOW CLOSED stays distinct
      from STALE — the operator's later, stricter ruling.
v1.5  2026-09-17  OTV4TEST r35 — reads query.py at the REPO ROOT (r34 moved it
      and missed this file; see check_query_sections v1.4).
v1.4  2026-09-11  OTV4TEST r14 — reads query.py under tools/ (root cleanup).
v1.3  2026-09-09  OTV4TEST r8 — PS8 reads the hushed line's new label (NOT ASKED joins it).
v1.2  2026-09-09  OTV4TEST r7 — PS8: readers hush DORMANT, the writer keeps it.
v1.1  2026-09-08  OTV4TEST r2 — PS3 reads `strategy/orb_plan.py`, where the ORB
      narration now lives ("Waiting on: impulsive candle" / "Waiting on: retest").

🔴 THE PER-TICK LOG MUST CARRY SIGNAL, NOT A TRANSCRIPT OF THE CLOCK.

Operator, 2026-08-27, reading UNH's morning: *"How much value is there in
having the afternoon strategies dominating the per-tick log during the entire
window that they're not gonna be traded? ... What's notably missing is the ORB
sequence — it doesn't appear anywhere in here. We had several qualifying
break/retests."*

TWO FAILURES IN ONE TABLE:

1. **~900 of ~1,300 rows were three credit strategies saying "it isn't 11:31
   yet", once a minute, for two hours.** A per-minute record of a clock. It
   buried the one sequence he was looking for.

2. **The ORB plan wrote a STATE LABEL and no geometry.** UNH logged 70 ticks
   `ARMED_SHORT` and one `TAKE` — with no record of where the break was, how
   deep the retest went, which attempt it was, or what the engine was waiting
   for. When a qualifying break+retest is on the chart and the bot does not
   take it, the table could not say why. Every field needed was already on
   `ORBData` and was simply never read.
"""
import ast
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def commit(self):
        self.conn.commit()


def main():
    # ── 🔴 PS1 — THE ORB SEQUENCE IS RECORDED, NOT JUST THE LABEL ────────
    from strategy.orb_strategy import ORBStrategy
    want = {"orb_high", "orb_low", "orb_width", "break_direction",
            "break_close", "bars_since_break", "retest_depth_px",
            "attempt_number", "stop_level", "target_50pct", "target_100pct"}
    have = set(ORBStrategy.PLAN_CHECKS)
    check("PS1 the ORB plan declares the whole sequence",
          want <= have, f"missing: {sorted(want - have) or 'none'}")

    # ⚠️ AND THE FIELDS MUST EXIST ON THE REAL ORBData — the whole point is
    # that they were always there and never read. A typo here reintroduces the
    # week's other defect (a name assumed rather than opened).
    from analysis.orb_engine import ORBData
    real = set(getattr(ORBData, "__annotations__", {}))
    mapped = {"break_close": "break_candle_close"}
    bad = [c for c in want
           if mapped.get(c, c) not in real]
    check("PS2 every declared ORB check maps to a real ORBData field",
          not bad, f"not on ORBData: {sorted(bad) or 'none'}")

    # ── PS3 — the refusal names what it is WAITING FOR ───────────────────
    # OTV4TEST r2 — the narration lives in the PLAN (strategy/orb_plan.py):
    # both sides priced while waiting on the impulsive candle, then PREPARED
    # while waiting on the retest.
    src = open(os.path.join(_root, "strategy", "orb_plan.py"),
               encoding="utf-8").read()
    check("PS3 the ORB plan row says what it is WAITING ON, not just the state",
          "Waiting on: retest" in src and "Waiting on: impulsive candle" in src)

    # ── 🔴 PS4 — OUT-OF-WINDOW IS DORMANT, AND DEDUPLICATED ──────────────
    from strategy import plan as P
    st = _Store()
    P.ensure_tables(st)
    P.bind_store(st)
    P.clear_dormant()
    pl = P.Plan("TestStrategy", ("entry_window",))
    for _ in range(240):                      # two hours at 30s
        P.begin_tick()
        pl.tick(100.0).dormant("entry_window", "outside the window")
        P.close_tick(st, "TEST")
    n = st.conn.execute("SELECT count(*) FROM plan_tick").fetchone()[0]
    check("PS4 240 identical dormant ticks write ONE row",
          n == 1, f"{n} rows (was 240)")

    # ⚠️ A CHANGE MUST STILL WRITE — dedupe is not silence.
    P.begin_tick()
    pl.tick(100.0).dormant("entry_window", "window OPEN")
    P.close_tick(st, "TEST")
    n2 = st.conn.execute("SELECT count(*) FROM plan_tick").fetchone()[0]
    check("PS5 a CHANGED dormant reason writes again", n2 == 2, f"{n2} rows")

    # ⚠️ AND close_tick MUST NOT FILL THE GAP WITH ITS OWN ROW. A silent
    # dormant tick that leaves `_last` stale gets a NOT ASKED row — or worse,
    # "a return path in this strategy is not wired through its plan" — which is
    # LOUDER than what it replaced.
    rows = [r[0] for r in st.conn.execute(
        "SELECT verdict FROM plan_tick").fetchall()]
    check("PS6 no NOT ASKED filler rows are written for a dormant strategy",
          "NOT ASKED" not in rows, ", ".join(sorted(set(rows))))

    # ── PS7 — the reason must be TIME-INVARIANT or dedupe does nothing ───
    # "09:40 ET is before..." and "09:41 ET is before..." are different strings.
    for rel in ("strategy/trend_credit_spread.py",
                "strategy/iron_condor_strategy.py",
                "strategy/gex_pin_butterfly.py",
                "strategy/sweep_credit_spread.py"):      # r161: the sweep is dormant too
        s = open(os.path.join(_root, rel), encoding="utf-8").read()
        tree = ast.parse(s)
        bad_call = False
        for n_ in ast.walk(tree):
            if (isinstance(n_, ast.Call)
                    and isinstance(n_.func, ast.Attribute)
                    and n_.func.attr == "dormant"):
                txt = ast.unparse(n_)
                if "hm[0]" in txt or "_hm" in txt or "{now_et}" in txt:
                    bad_call = True
        check(f"PS7 {os.path.basename(rel)}: dormant reason carries no clock",
              not bad_call)

    # PS8 (OTV4TEST r7) — the READERS hush dormant plans; the record keeps them.
    qsrc = open(os.path.join(_root, "query.py"), encoding="utf-8").read()
    psrc = open(os.path.join(_root, "strategy", "plan.py"), encoding="utf-8").read()
    dsrc = open(os.path.join(_root, "devtools.sh"), encoding="utf-8").read()
    # 🔴 r92 — THE HUSH WAS THE OLD PANEL'S ANSWER; r83 GAVE A BETTER ONE.
    # This asserted the literal `if verdict in ("DORMANT", "NOT ASKED")` and a
    # "hushed (dormant / not asked)" line. Both belonged to the `plan_tick`
    # panel that r83 replaced WHOLESALE at the operator's instruction. The
    # complaint the hush answered — *"I don't need a block each"* — is answered
    # better now: `plan_heartbeat` is ONE ROW PER PLAN, so the panel renders
    # exactly one line per plan by construction rather than by suppressing
    # some, and a plan outside its window reads WINDOW CLOSED instead of
    # vanishing into a summary count.
    # ⚠️ AND THAT IS THE OPERATOR'S LATER, STRICTER RULING: *"I don't think
    # stale needs to be the same thing as window closed. Report stale if it
    # really is stale and report window closed if that's the reason."* A hush
    # collapses those two back together, which is what r83 was written to end.
    # 🔑 SO PS8 PINS THE MAPPING, NOT THE SUPPRESSION: every admission gate
    # reaches the reader as ONE WORD. An unknown gate degrades to "HELD" —
    # vaguer, never invisible — which is the property that makes a one-line
    # render safe to rely on.
    _WORDS = ("WINDOW CLOSED", "QUOTA HIT", "AT CAP", "HALTED",
              "NO CHAIN", "RETIRED", "POSITION OPEN", "AWAITING AUTH")
    _absent = [w for w in _WORDS if w not in qsrc]
    check("PS8 query.py DECISIONS renders each gate as ONE WORD, one line per plan",
          not _absent and '"entry_window":' in qsrc and "plan_heartbeat" in qsrc,
          f"missing words={_absent}")
    check("PS8b the WRITER still records the dormant transition row (the bot sees everything)",
          'self._close("DORMANT", f"{gate}: {why}")' in psrc)
    check("PS8c the PLAN ROWS / PLAN BOARD sensors exclude DORMANT by default",
          "verdict <> 'DORMANT'" in dsrc and "Show DORMANT rows too?" in dsrc)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_plan_signal: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
