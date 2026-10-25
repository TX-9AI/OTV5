#!/usr/bin/env python3
"""
tests/check_plan_status.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.4  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject TrendCreditSpread is DORMANT by default and a dormant plan now writes
      nothing by ruling, so this run switches it ACTIVE (OT_TCS_ACTIVE=1); the status rules it pins are unchanged.
EVERY PLAN IS WORKING OR INACTIVE, AND INACTIVE SAYS SO ONCE.

v1.3  2026-10-06  OTV4TEST r258 (HYG.17) — S13-S16: A NON-WINDOW REASON THAT COMES BACK DECLARES ITSELF.
      Found on SPX-TEST 10-06: Breakout/manage went "no open position" -> "position open —
      managing" -> back to "no open position" inside one inactive episode, and the return was
      never written, so plan.last(), the heartbeat and the [plans] line read "managing" on a flat
      book from 10:42 to 16:00. The per-episode SET (r42) keeps EVERY token it ever saw, so a
      non-window reason that was said once was silent forever after. r42's ruling says the
      opposite for every gate but the window: "if something other than the window made it
      inactive it should declare that". S13 drives A -> B -> A (no gate) and demands three rows
      and last() = A; S14 the same with named gates; S15 pins that the return, once written,
      is not repeated; S16 that a new trading day says it again (killed the one surviving mutant). S9-S12 (the window's once-per-episode rule) are unchanged and must stay green.
v1.2  2026-09-18  OTV4TEST r49 — `guard()` takes a CALLABLE detail. Its `detail`
      argument was evaluated BEFORE the predicate ran, so any detail computed
      from state the predicate sets printed STALE — a failing check reporting
      the opposite of its own finding. Rendered after the predicate now.
v1.1  2026-09-18  OTV4TEST r42 — S9-S12 for the operator's asymmetry: window is
      announced ONCE PER INACTIVE EPISODE, every other gate declares itself.
      S10 is `window -> cap -> window` and demands TWO rows — the sequence a
      last-value slot gets wrong by re-announcing window, which is why the
      implementation needs a per-episode SET. S12 phrases the window refusal
      three ways and demands one row, pinning that the rule keys on the GATE
      and never on the prose.
      ⚠️ AND `fresh()` NOW CLEARS EVERY MODULE DICT. It cleared `_STATUS` only,
      so `_SEEN`/`_SEEN_DAY` LEAKED BETWEEN CASES and S10 read an earlier
      case's episode — the same sequence passed standalone and failed in the
      suite, which is the more dangerous direction of that fault.
v1.0  2026-09-18  OTV4TEST r41 — born red at r40 (a3ff8b9), where `close_tick`
      wrote a NOT ASKED row for every idle plan on EVERY tick.

THE OPERATOR'S RULING, 2026-09-18, verbatim:
  *"Because we know a plan is inactive outside its window, I don't need 10k rows
  explaining why. I just need 1, so I'm aware it at least 'Knows' — each plan
  should have a current status as either 'working' or 'inactive' and if it's
  working, I want per tick logging. If inactive it should just say that, once,
  until it becomes active."*

⚠️ THE ASSERTION IS A ROW COUNT ACROSS TICKS, NOT A STRING IN ONE ROW. The
defect is repetition, so a checker that reads a single tick cannot see it: the
row it finds is correct every time. S3 runs FIVE ticks in one state and demands
exactly ONE row — which is the only shape that fails on the old code.
"""
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_TCS_ACTIVE"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
os.environ.setdefault("OT_TRADES_DB", os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(tempfile.mkdtemp(), "d.db"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn, detail=""):
    """Run a predicate; a MISSING symbol is a RED LINE, never a traceback.

    ⚠️ `detail` MAY BE A CALLABLE, AND OFTEN MUST BE. A plain string argument is
    evaluated BEFORE `fn()` runs, so any detail computed from state the predicate
    sets is stale — r49's N8 printed "no fire-then-return" on a FAILING check,
    which is the diagnostic saying the opposite of the truth. Pass a lambda to
    have it rendered AFTER the predicate.
    """
    try:
        ok = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return False
    try:
        det = detail() if callable(detail) else detail
    except Exception:                                           # noqa: BLE001
        det = ""
    check(name, ok, det)
    return ok


class _St:
    def __init__(s):
        s.conn = sqlite3.connect(":memory:")
        s.conn.row_factory = sqlite3.Row

    def commit(s):
        s.conn.commit()


def main():
    from strategy import plan as P

    st = _St()
    P.ensure_tables(st)
    P.bind_store(st)

    N = "TrendCreditSpread"

    def fresh():
        P.REGISTRY.clear()
        # ⚠️ TOLERANT ON PURPOSE: at the older HEAD there is no `_STATUS`, and
        # a setup helper that raises turns a BORN-RED proof into a traceback —
        # the fault this repo has now shipped three times (r32, r37, r39).
        # ⚠️ EVERY module-level dict, or state LEAKS BETWEEN CASES and a later
        # case silently reads an earlier one's episode. That is what made S10
        # report 1 row when the same sequence passed standalone.
        for _d in ("_STATUS", "_SEEN", "_SEEN_DAY", "_SKIPPED", "_SKIP_GATE", "_ASKED", "_LAST_SAID"):
            getattr(P, _d, {}).clear()
        st.conn.execute("DELETE FROM plan_tick")
        P.Plan("TrendCreditSpread", ("age",))

    def tick(n, reason=None, wrote=False):
        P.begin_tick(float(n))
        if wrote:
            # a WORKING plan speaks for itself
            P.write_row(st, "TST", float(n), "TrendCreditSpread", "ARMED", "working")
            P.REGISTRY["TrendCreditSpread"]._last = (P.tick_now()[0], "ARMED", "working")
        elif reason:
            P.skipped("TrendCreditSpread", reason)
        P.close_tick(st, "TST")

    def rows():
        return [(r["verdict"], r["reason"]) for r in st.conn.execute(
            "SELECT verdict, reason FROM plan_tick WHERE strategy='TrendCreditSpread'"
            " ORDER BY ts_epoch")]

    # ── S1/S2/S3 — the ruling itself ───────────────────────────────────────
    fresh()
    for n in range(1, 6):
        tick(n, reason="inactive — window: outside 11:30-15:00")
    r = rows()
    guard("S1 an INACTIVE plan writes exactly ONE row across five identical ticks",
          lambda: len(r) == 1, f"{len(r)} row(s) — the old board wrote 5")
    guard("S2 and the status it reports is INACTIVE, not 'NOT ASKED'",
          lambda: r and r[0][0] == "INACTIVE", f"verdict={r[0][0] if r else '-'}")
    guard("S2b the one row still carries the NAMED GATE",
          lambda: r and "window" in (r[0][1] or ""), f"{r[0][1][:50] if r else '-'}")

    # ── S4 — a WORKING plan keeps per-tick logging ─────────────────────────
    fresh()
    for n in range(10, 15):
        tick(n, wrote=True)
    rw = rows()
    guard("S4 a WORKING plan still writes EVERY tick — five ticks, five rows",
          lambda: len(rw) == 5, f"{len(rw)} row(s)")
    guard("S4b and the board reports it as working",
          lambda: P.plan_status("TrendCreditSpread") == "working")

    # ── S5 — the transition back re-announces ──────────────────────────────
    fresh()
    tick(20, reason="inactive — window: outside 11:30-15:00")
    tick(21, reason="inactive — window: outside 11:30-15:00")
    tick(22, wrote=True)                       # becomes active
    tick(23, reason="inactive — window: outside 11:30-15:00")
    r5 = rows()
    guard("S5 inactive -> working -> inactive announces the second inactive AGAIN",
          lambda: [x[0] for x in r5] == ["INACTIVE", "ARMED", "INACTIVE"],
          f"{[x[0] for x in r5]}")

    # ── S6 — a DIFFERENT reason is a state change, not a repeat ────────────
    fresh()
    tick(30, reason="inactive — window: outside 11:30-15:00")
    tick(31, reason="inactive — window: outside 11:30-15:00")
    tick(32, reason="inactive — cap: catastrophic cap broken")
    r6 = rows()
    guard("S6 inactive for a DIFFERENT reason writes again — a cap break is not noise",
          lambda: len(r6) == 2 and "cap" in r6[1][1],
          f"{len(r6)} row(s)")

    # ══ S9-S12 — THE OPERATOR'S ASYMMETRY (r42) ═══════════════════════════
    # 2026-09-18: *"if something other than the window made it inactive it
    # should declare that, but if it's the window, I just need to see that once
    # not repeatedly."*
    # ⚠️ TICKS ARE 1-BASED HERE. `begin_tick` does `float(ts or time.time())`,
    # so tick 0 is falsy and silently takes the wall clock — the row then sorts
    # out of order and every index assertion below it is meaningless. Harmless
    # in production (no real tick is epoch 0); it cost a false smoke failure.
    def gtick(n, gate=None, why=None, working=False):
        P.begin_tick(float(n))
        if working:
            P.write_row(st, "TST", float(n), N, "ARMED", "working")
            P.REGISTRY[N]._last = (P.tick_now()[0], "ARMED", "working")
        elif gate:
            P.skipped(N, f"inactive — {gate}: {why or gate}", gate=gate)
        P.close_tick(st, "TST")

    fresh()
    for i in range(1, 201):
        gtick(i, "window", "outside 11:30-15:00")
    guard("S9 TWO HUNDRED ticks outside the window -> exactly ONE row",
          lambda: len(rows()) == 1, f"{len(rows())} row(s)")

    # 🔑 THE CASE A LAST-VALUE SLOT GETS WRONG. With one remembered state,
    # window -> cap -> window RE-ANNOUNCES window, because the slot now holds
    # `cap` and window looks like a change. It needs a per-episode SET.
    fresh()
    for i in range(1, 6):
        gtick(i, "window", "outside 11:30-15:00")
    for i in range(6, 11):
        gtick(i, "catastrophic_cap", "catastrophic cap reached")
    for i in range(11, 21):
        gtick(i, "window", "outside 11:30-15:00")
    r9 = rows()
    guard("S10 window -> cap -> window is TWO rows: window once, then the cap",
          lambda: len(r9) == 2 and "catastrophic_cap" in r9[1][1],
          f"{len(r9)} row(s) — a last-value slot would write 3")

    fresh()
    for i in range(1, 4):
        gtick(i, "window", "outside 11:30-15:00")
    for i in range(4, 7):
        gtick(i, "max_open_of_type", "2 already open")
    for i in range(7, 10):
        gtick(i, "tries_per_session", "1 try used")
    guard("S11 each DIFFERENT non-window gate declares itself — 3 rows",
          lambda: len(rows()) == 3, f"{len(rows())} row(s)")

    # the gate is keyed, not the prose — rewording must not re-announce
    fresh()
    gtick(1, "window", "outside 11:30-15:00")
    gtick(2, "window", "outside 11:30 - 15:00 ET")
    gtick(3, "window", "not in window")
    guard("S12 window REWORDED three ways is still ONE row — keyed on the GATE",
          lambda: len(rows()) == 1,
          "parsing prose for the gate is how this rule would silently stop working")

    # ══ S13-S15 — r258 (HYG.17): A NON-WINDOW REASON THAT RETURNS DECLARES ITSELF ════
    _A = "no open position — nothing to manage"
    _B = "position open — managing; only the second-leg window is open"
    fresh()
    for i in range(1, 4):
        tick(i, reason=_A)
    for i in range(4, 7):
        tick(i, reason=_B)
    for i in range(7, 12):
        tick(i, reason=_A)
    r13 = rows()
    guard("S13 A -> B -> A (no gate) writes THREE rows, and last() ends at A",
          lambda: len(r13) == 3 and r13[-1][1] == _A
          and P.REGISTRY[N].last()[2] == _A,
          lambda: f"{len(r13)} row(s), last()={P.REGISTRY[N].last()!r}")
    fresh()
    for i in range(1, 4):
        gtick(i, "max_open_of_type", "2 already open")
    for i in range(4, 7):
        gtick(i, "tries_per_session", "1 try used")
    for i in range(7, 10):
        gtick(i, "max_open_of_type", "2 already open")
    r14 = rows()
    guard("S14 gate X -> gate Y -> gate X writes THREE rows — the return is news",
          lambda: len(r14) == 3 and "max_open_of_type" in r14[-1][1],
          lambda: f"{len(r14)} row(s)")
    fresh()
    tick(1, reason=_A)
    tick(2, reason=_B)
    for i in range(3, 50):
        tick(i, reason=_A)
    guard("S15 and the returned state, once written, stays SILENT (47 ticks -> one row)",
          lambda: len(rows()) == 3, lambda: f"{len(rows())} row(s)")

    # S16 — a NEW TRADING DAY says it again (the day keys the episode, r41)
    fresh()
    _d1 = [P._status_changed(N, "2026-10-05", "INACTIVE", _A),
           P._status_changed(N, "2026-10-05", "INACTIVE", _A),
           P._status_changed(N, "2026-10-06", "INACTIVE", _A)]
    guard("S16 the same reason: said, silent the same day, said again the NEXT day",
          lambda: _d1 == [True, False, True], lambda: f"{_d1}")

    # ── S7 — the status is exposed, not merely internal ────────────────────
    guard("S7 plan_status() answers working/inactive/unknown",
          lambda: P.plan_status("TrendCreditSpread") == "inactive"
          and P.plan_status("NeverHeardOfIt") == "unknown")

    # ── S8 — main.py names the gate so no table strategy hits the default ──
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    guard("S8 admission names the refusing gate for every strategy it refuses",
          lambda: "logging_state(" in src
          and 'f"inactive — {_gate}: {_why}"' in src
          and "gate=_gate" in src,
          "otherwise an out-of-window plan reads as a dispatch-gap DEFECT")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
