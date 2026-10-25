#!/usr/bin/env python3
"""check_entry_windows.py — v5.1
v5.1  2026-10-25  OTV5 r9 (GATE.7) — its sweep prepare call is pinned to a session open (now - 2h), as every fixture that drives the trend or sweep wrapper now is (check_session_pin P6); the path it pins stops before any level read, so every expectation is unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.7  2026-10-12  OTV4TEST r273 (BFLY.10) — W4c: THE BUTTERFLIES OPEN AT 13:00, DRIVEN. The operator,
      2026-10-12 12:26 ET: "For TEST repo, I want to reduce the fly window to 1300 or later starting
      tomorrow". GEXPinButterfly prepare() is dormant on entry_window at 12:59 and records it at 13:00;
      ENTRY_WINDOWS starts both flies (GEX, ATP) at (13, 0). Mirrors otv4 r484 W4c's method.
v1.6  2026-10-02  OTV4TEST r187 (ROSTER.1) — W6 RE-POINTED BY THE RULING. The operator,
      2026-10-02: "let's impose a 1029 debit cutoff rule, but exempts the GEX pin fly".
      The directional debit cutoff is 10:30 (exclusive; last entry 10:29) and is the
      Runaway row of ENTRY_WINDOWS; the credit END and EOD_SCHEDULE["entries_stop"]
      stay ONE minute, 15:40. MOVED, NOT DROPPED: both halves are still pinned.
v1.5  2026-09-26  OTV4TEST r149 (EOD.1) — W6 RE-POINTED. The 08-24 one-minute daylight between the
      debit cutoff and the credit start is SUPERSEDED by the operator's ruling, 2026-09-26: "I wanna
      extend the debit window to all day" and "Stop entries at 1540". W6 now pins that the debit
      cutoff, the credit END and EOD_SCHEDULE["entries_stop"] are ONE minute: 15:40.
v1.4  2026-09-24  OTV4TEST r128: FOUR STALE ASSERTIONS AND TWO HOLLOW GREENS
      RE-POINTED AT WHERE THE CODE LIVES NOW. Every property is MOVED, NOT
      DROPPED (section 38.4). Fork r5 (8a36b6f) moved the sweep's logic into
      strategy/sweep_plan.py, and r3/r9 moved PLAN_CHECKS onto the plan
      classes; this file kept reading the old homes.
      · W9pre: the recorder wrapped `relaxed.window`, which the sweep no longer
        calls at all - its window is the fixed EARLIEST_ET/LATEST_ET pair
        (sweep_plan.py:132-133) compared in `prepare()`. The property ("the
        sweep window is never relaxable") is now an AST check: sweep_plan.py
        calls no relaxed.window / relaxed.widen and imports neither by name.
      · W9: EXECUTES the real window gate - SweepCreditSpreadStrategy().prepare
        (which delegates to SweepPlan.prepare) at every minute 09:30-16:00
        under OT_RELAXED_ENTRY=0 and =1 (paper, so relaxed is genuinely
        allowed) and asserts the entry_window outcome is identical minute for
        minute. Plan rows go to an in-memory store, never a live one.
      · W9b: SUPERSEDED BY PLAN_SPEC 31.2 (docs/PLAN_SPEC.md:1271), which set
        the sweep window to open 09:35 on purpose. It pinned the applied start
        to CREDIT_ENTRY_START_ET (11:31); it now pins the APPLIED window,
        measured from the W9 run, to config.SWEEP_CS_EARLIEST_ET_FORK (09:35)
        -> CREDIT_ENTRY_END_ET, in both modes.
      · W7: read PLAN_CHECKS off the STRATEGY classes; three of them now set it
        per instance from their plan. It reads the declaring classes: RunawayPlan
        (runaway_plan.py:154), TCSPlan (tcs_plan.py:212), SweepPlan
        (sweep_plan.py:285), GEXPinButterflyStrategy, IronCondorStrategy.
      · W1 / W5 (HOLLOW GREENS): compared sweep_credit_spread.EARLIEST_ET and
        C.SWEEP_CS_EARLIEST_ET, constants nothing live reads. W1 now holds the
        universal start on condor + TCS and pins the sweep's own ruled start
        (C.SWEEP_CS_EARLIEST_ET_FORK == 09:35, PLAN_SPEC 31.2); W5 asserts
        sweep_plan.EARLIEST_ET is that config value.
      Plus the r106 venv bootstrap (the lander runs CHECKs under
      /usr/bin/python3).
v1.3  2026-09-08  r321: W9 — THE WINDOW A STRATEGY COMPUTES, NOT THE CONSTANT
      IT DECLARES. W5 asserts `sweep.EARLIEST_ET == CREDIT_ENTRY_START_ET` and
      was green while the sweep OPENED AT 09:45 under relaxed, because
      `prepare()` passes its constants through `relaxed.window()` and the
      `relaxed_earliest` default is "09:45" — a value nobody chose for this
      strategy. W9 drives the same call the strategy makes, in BOTH modes, and
      asserts the applied window is identical. Born red at 82d369e.
v1.2  2026-09-08  r317: W8 — THE END SIDE, WHICH THIS FILE NEVER ASSERTED.
      W1 has pinned ONE credit START across four paths since r146, written
      after the sweep kept 11:11 on a `getattr` default whose key did not
      exist. `SWEEP_CS_LATEST_ET` was the SAME DEFECT on the END and survived
      both sweeps because nothing here looked at ends at all. Born red at
      0498534, where `C.SWEEP_CS_LATEST_ET` raises AttributeError.
      ⚠️ W8 GOES RED ON A DELIBERATE DIVERGENCE TOO, and that is the point:
      if a future ruling gives one credit path its own cutoff, this check is
      how that decision gets recorded rather than absorbed. Update it WITH the
      ruling; do not loosen it to keep a run green.
v1.1  2026-08-26  r146: W7 re-pinned to each strategy's PLAN_CHECKS after the
      builder engine was deleted.

🔴 ONE START TIME FOR EVERY CREDIT SPREAD, AND ONE MINUTE OF DAYLIGHT.

Operator, 2026-08-26: a universal credit start "to keep things tidy". The
number is 11:31 rather than 11:30 because of his own 2026-08-24 ruling —
*"Handoff (credit) needs to start at 1131 - it's colliding with runaway (same
trigger)"* — and because the debit cutoff test is `>= (11, 30)`, so the debit
is blocked AT 11:30. A credit start of 11:30 would hand both the same minute
and reproduce the collision that ruling fixed.

⚠️ SECONDS CANNOT EXPRESS A FINER BOUNDARY. Every gate compares
`(now.hour, now.minute)`; 11:30:01 and 11:30:59 are the same tuple. The tick is
30s besides, so a sub-minute boundary would land wherever each box's restart
drift happened to put it.
"""
import sys
import os
import ast
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    import config as C

    start = C.CREDIT_ENTRY_START_ET

    # ⚠️ FOUR PATHS, NOT THREE. The sweep read its start from a getattr
    # DEFAULT that was never in config, so it kept 11:11 while the other three
    # moved — caught by check_sweep_spread's S8a, not by me. Any credit path
    # that carries its own literal is the failure this check exists to prevent.
    # r128 — RE-POINTED (38.4: moved, not dropped). `SWEEP_CS_EARLIEST_ET` is
    # read by nothing live since fork r5; the sweep reads
    # `SWEEP_CS_EARLIEST_ET_FORK` (sweep_plan.py:132), and PLAN_SPEC 31.2 opened
    # it at 09:35 ON PURPOSE. So the one-start rule holds on condor + TCS, and
    # the sweep's divergence is pinned to the RULED value — a move of it is a
    # ruling to record here, not a drift to absorb (W8's warning).
    _sw = tuple(C.SWEEP_CS_EARLIEST_ET_FORK)
    check("W1 condor and TCS use the ONE credit start; the sweep uses its ruled "
          "09:35 (PLAN_SPEC 31.2)",
          C.CONDOR_ENTRY_START_ET == start and C.TCS_START_ET == start
          and _sw == (9, 35),
          f"credit={start} condor={C.CONDOR_ENTRY_START_ET} "
          f"tcs={C.TCS_START_ET} sweep_fork={_sw}")

    # 🔴 THE DAYLIGHT RULE. The debit cutoff is `>= (11, 30)` — debit is blocked
    # AT 11:30 — so the credit must start STRICTLY LATER than 11:30, or both
    # own the same minute and the handover is ambiguous in the log and the
    # record. This is the operator's 08-24 collision, and it is the single
    # thing most likely to be "tidied" back into existence later.
    check("W2 credit starts strictly AFTER the debit cutoff minute",
          start > (11, 30), f"credit start {start} vs debit cutoff (11, 30)")

    check("W3 the credit window is non-empty",
          start < C.CONDOR_ENTRY_CUTOFF_ET,
          f"{start} -> {C.CONDOR_ENTRY_CUTOFF_ET}")

    # ⚠️ THE BUTTERFLY OPENS LATER THAN THE CREDIT SPREADS, AND THAT IS THE
    # RULING, not an oversight. Operator, 2026-08-26: *"Butterfly is debit &
    # any sooner than noon to reach a pin is unlikely to hold all the way to
    # the closing bell."* It is a DEBIT that needs the pin to hold into the
    # close, so a later start is protective rather than restrictive.
    bf = C.BUTTERFLY_ENTRY_START_ET
    print(f"  NOTE  butterfly (debit) starts {bf}, "
          f"{(bf[0]*60+bf[1]) - (start[0]*60+start[1])} min after the credit "
          f"spreads — RULED 2026-08-26, a debit needs the pin to hold to the bell")

    # ⚠️ AND THE WINDOW LENGTH IS A REAL COST, so state it rather than bury it.
    mins = ((C.CONDOR_ENTRY_CUTOFF_ET[0]*60 + C.CONDOR_ENTRY_CUTOFF_ET[1])
            - (start[0]*60 + start[1]))
    print(f"  NOTE  credit entry window is {mins} min "
          f"(was 169 at the old 11:11 condor start)")

    # ── 🔴 W4-W6 — THE STRATEGIES AND THE PLANS MUST AGREE ───────────────
    # ⚠️ TWO MORE getattr DEFAULTS WITH NO CONFIG KEY, found the same way as
    # the sweep: `GEX_BFLY_EARLIEST_ET` defaulted to "11:00" — so the LIVE
    # butterfly gate opened a full hour before BUTTERFLY_ENTRY_START_ET, a
    # constant production read NOWHERE — and `RUNAWAY_CUTOFF_ET` defaulted to
    # "11:30". A config value nobody reads is decorative; a default nobody can
    # see is the real setting.
    import strategy.gex_pin_butterfly as _bf
    import strategy.runaway_continuation as _rc
    import strategy.sweep_credit_spread as _sc
    import strategy.sweep_plan as _sp_mod

    def _hm(t):
        return tuple(int(x) for x in t.split(":")) if isinstance(t, str) else tuple(t)

    check("W4 the butterfly STRATEGY honours the config noon rule",
          _hm(_bf.EARLIEST_ET) == tuple(C.BUTTERFLY_ENTRY_START_ET),
          f"strategy {_bf.EARLIEST_ET} vs config {C.BUTTERFLY_ENTRY_START_ET}")

    # ── W4c — r273 (BFLY.10): 13:00, DRIVEN through prepare(), not read off a constant ─
    def _window_open(hhmm):
        # Out of window prepare() returns dormant BEFORE recording the entry_window
        # condition; in window it records it. The condition list is the signal.
        p = _bf.GEXPinButterflyStrategy().prepare(gex=None, price_now=100.0, now_et=hhmm)
        return "entry_window" in repr(getattr(p, "conditions", p))

    _ew = C.ENTRY_WINDOWS
    check("W4c both flies start at (13, 0) and GEX prepare() is dormant at 12:59, open at 13:00",
          tuple(_ew["GEXPinButterfly"][0]) == (13, 0) and tuple(_ew["ATPButterfly"][0]) == (13, 0)
          and not _window_open("12:59") and _window_open("13:00"),
          f"GEX={_ew['GEXPinButterfly']} ATP={_ew['ATPButterfly']} "
          f"12:59 open={_window_open('12:59')} 13:00 open={_window_open('13:00')}")

    # r128 — the constant the LIVE gate compares against (sweep_plan.py:132,
    # applied in prepare()), not sweep_credit_spread.EARLIEST_ET, which nothing
    # live reads since fork r5.
    check("W5 the sweep PLAN honours its config start (SWEEP_CS_EARLIEST_ET_FORK)",
          _hm(_sp_mod.EARLIEST_ET) == tuple(C.SWEEP_CS_EARLIEST_ET_FORK),
          f"sweep_plan {_sp_mod.EARLIEST_ET} vs config {C.SWEEP_CS_EARLIEST_ET_FORK}")

    # 🔴 r149 — ONE STOP FOR EVERY ENTRY. The 08-24 daylight (debit cutoff one
    # minute before the credit start) is superseded: debits run all day, and
    # every entry — debit and credit — stops at EOD_SCHEDULE["entries_stop"].
    _dc = _hm(_rc.CUTOFF_ET)
    _es = tuple(C.EOD_SCHEDULE["entries_stop"])
    check("W6 debit cutoff 10:30 (r187, the Runaway row); credit end = EOD entries_stop (15:40)",
          _dc == tuple(C.ENTRY_WINDOWS["RunawayContinuation"][1]) == (10, 30)
          and _es == tuple(C.CREDIT_ENTRY_END_ET) == (15, 40),
          f"debit cutoff {_dc}, credit end {tuple(C.CREDIT_ENTRY_END_ET)}, entries_stop {_es}")

    # ── 🔴 W8 — ONE CREDIT END, THE MIRROR OF W1 ─────────────────────────
    # The sweep's END was `getattr(config, "SWEEP_CS_LATEST_ET", "14:00")` with
    # NO SUCH KEY — the third instance of the default-is-the-only-source shape
    # in this codebase, and the first on the END side. All four read 14:00
    # today, so this is latent: it costs nothing until the cutoff moves, and
    # then three paths move and the sweep does not.
    # ⚠️ NAMED FAILURE, NEVER A TRACEBACK. At 0498534 neither CREDIT_ENTRY_END_ET
    # nor SWEEP_CS_LATEST_ET exists, and a bare read raised AttributeError —
    # "the checker crashed" and "the constant is absent" must not look alike
    # (WORKING_AGREEMENT §0.5), least of all in the check whose whole subject is
    # a constant that was missing.
    _missing = [n for n in ("CREDIT_ENTRY_END_ET", "SWEEP_CS_LATEST_ET",
                            "CONDOR_ENTRY_CUTOFF_ET", "TCS_ENTRY_END_ET")
                if not hasattr(C, n)]
    if _missing:
        check("W8 there is ONE credit end and every credit path uses it",
              False, f"config defines no {', '.join(_missing)}")
        check("W8b the credit window is bounded the right way round", False,
              "cannot evaluate — the end constant is absent")
        _end = None
    else:
        _end = tuple(C.CREDIT_ENTRY_END_ET)
        check("W8 there is ONE credit end and every credit path uses it",
              tuple(C.CONDOR_ENTRY_CUTOFF_ET) == _end
              and tuple(C.TCS_ENTRY_END_ET) == _end
              and _hm(C.SWEEP_CS_LATEST_ET) == _end
              and _hm(_sc.LATEST_ET) == _end,
              f"end={_end} condor={C.CONDOR_ENTRY_CUTOFF_ET} tcs={C.TCS_ENTRY_END_ET} "
              f"sweep_cfg={C.SWEEP_CS_LATEST_ET} sweep_strategy={_sc.LATEST_ET}")
        check("W8b the credit window is bounded the right way round",
              tuple(start) < _end, f"{start} -> {_end}")

    # ── 🔴 W9 — THE APPLIED WINDOW, IN BOTH MODES ────────────────────────
    # Operator, 2026-09-08: *"The sweep window cannot be relaxed. It needs to
    # remain strict at all times"* — the start has since been ruled 09:35
    # (PLAN_SPEC 31.2); "never relaxable" stands.
    # r128 — RE-POINTED (38.4: moved, not dropped). Fork r5 (8a36b6f) moved the
    # gate into SweepPlan.prepare, which compares `now_et` to the fixed
    # EARLIEST_ET / LATEST_ET (sweep_plan.py:132-133) and never calls
    # `relaxed.window` — so the old recorder saw nothing and read None/None.
    # 🔴 §0.4 STILL APPLIES: this RUNS the real gate and reads the outcome the
    # plan itself records (`checks["entry_window"]`), rather than re-deriving it.

    # W9pre — the static half: nothing in the sweep plan can widen its window.
    _spsrc = open(os.path.join(_root, "strategy", "sweep_plan.py"),
                  encoding="utf-8").read()
    _bad = []
    for _n in ast.walk(ast.parse(_spsrc)):
        if (isinstance(_n, ast.Call) and isinstance(_n.func, ast.Attribute)
                and _n.func.attr in ("window", "widen")
                and isinstance(_n.func.value, ast.Name)
                and _n.func.value.id in ("relaxed", "_rx", "rx")):
            _bad.append(f"{_n.func.value.id}.{_n.func.attr}() @L{_n.lineno}")
        if (isinstance(_n, ast.ImportFrom) and (_n.module or "").endswith("relaxed")
                and any(a.name in ("window", "widen") for a in _n.names)):
            _bad.append(f"from {_n.module} import window/widen @L{_n.lineno}")
    check("W9pre the sweep plan never passes its window through relaxed.window/widen",
          not _bad, ", ".join(_bad) or "no relaxed.window / relaxed.widen call")

    import sqlite3 as _sq
    import strategy.plan as _P
    from strategy import relaxed as _rx

    class _MemStore:                     # plan rows land here, never in a live store
        def __init__(self):
            self.conn = _sq.connect(":memory:")

        def commit(self):
            self.conn.commit()

    # ⚠️ RELAXED IS PAPER-ONLY AND `is_live()` FAILS CLOSED, so without this
    # the "relaxed" arm runs STRICT and the check passes on a broken tree.
    # A checker whose two arms are secretly the same arm cannot fail.
    _prev = os.environ.get("OT_RELAXED_ENTRY")
    _prev_paper = os.environ.get("OT_PAPER_TRADING")
    os.environ["OT_PAPER_TRADING"] = "1"
    _minutes = [(h, m) for h in range(9, 16) for m in range(60) if (h, m) >= (9, 30)] + [(16, 0)]
    _open, _armed = {}, {}
    try:
        for _m in ("0", "1"):
            os.environ["OT_RELAXED_ENTRY"] = _m
            _armed[_m] = _rx.is_allowed()
            import time as _time
            _strat = _sc.SweepCreditSpreadStrategy()
            _strat.plan.planner._store = _MemStore()
            _row = {}
            for _hmv in _minutes:
                _P.clear_dormant(_strat.plan.planner.strategy)   # a dormant repeat records nothing
                # price_now=None: an OPEN window records entry_window=True and
                # then starves on price, so nothing past the gate runs.
                _prep = _strat.prepare(price_now=None, now_et=f"{_hmv[0]:02d}:{_hmv[1]:02d}",
                                       atr_pct=0.1, chain=None,
                                       session_open_epoch=_time.time() - 7200.0)   # GATE.7: pinned
                _row[_hmv] = _prep.tick.checks.get("entry_window", (None, None))[1]
            _open[_m] = _row
    finally:
        if _prev is None:
            os.environ.pop("OT_RELAXED_ENTRY", None)
        else:
            os.environ["OT_RELAXED_ENTRY"] = _prev
        if _prev_paper is None:
            os.environ.pop("OT_PAPER_TRADING", None)
        else:
            os.environ["OT_PAPER_TRADING"] = _prev_paper

    def _span(row):
        on = [k for k, v in row.items() if v is True]
        if not on:
            return None
        last = on[-1]
        end = (last[0] + (last[1] + 1) // 60, (last[1] + 1) % 60)
        return on[0], end                # [start, end) — the gate is `hm >= LATEST`

    _diff = [f"{h:02d}:{m:02d}" for (h, m) in _minutes if _open["0"][(h, m)] != _open["1"][(h, m)]]
    _unrec = [f"{h:02d}:{m:02d}" for (h, m) in _minutes if _open["0"][(h, m)] is None]
    check("W9 the sweep's APPLIED window is identical in both modes (09:30-16:00, "
          "every minute, relaxed arm genuinely relaxed)",
          _armed["0"] is False and _armed["1"] is True and not _diff and not _unrec
          and _span(_open["0"]) is not None,
          f"relaxed allowed strict={_armed['0']} relaxed={_armed['1']}; "
          f"differ at {_diff[:6] or 'none'}; unrecorded {_unrec[:6] or 'none'}; "
          f"strict={_span(_open['0'])} relaxed={_span(_open['1'])}")
    # W9b — SUPERSEDED BY PLAN_SPEC 31.2: the start is 09:35 by ruling, not the
    # universal 11:31; the end is the universal credit end (W8's property).
    _want = (tuple(C.SWEEP_CS_EARLIEST_ET_FORK), tuple(C.CREDIT_ENTRY_END_ET))
    check("W9b and the applied window is SWEEP_CS_EARLIEST_ET_FORK -> CREDIT_ENTRY_END_ET "
          "in both modes (PLAN_SPEC 31.2)",
          _span(_open["0"]) == _want and _span(_open["1"]) == _want,
          f"strict={_span(_open['0'])} relaxed={_span(_open['1'])} want={_want}")

    # ── W7 — the PLAN side declares and applies the same window ──────────
    # ⚠️ NO PLAN BUILDER CHECKED THE CLOCK AT ALL until r142. A fork plan read
    # TAKE at 11:05 while the strategy could not act until 11:31 — the row
    # looked tradeable and was not, and nothing in the table said why.
    # r146 — the plan is now the strategy's own (strategy/plan.py); each
    # strategy declares the checks it owns as PLAN_CHECKS. ORB is exempt by
    # ruling (record-only, zero hurdles) and the roll is management.
    # r128 — RE-POINTED (38.4: moved, not dropped). Since r3/r9 the runaway,
    # TCS and sweep STRATEGIES set PLAN_CHECKS per instance from their plan, so
    # reading the strategy CLASS found nothing. Read the classes that DECLARE
    # it; the butterfly and the condor still declare on the strategy class.
    from strategy.runaway_plan import RunawayPlan
    from strategy.tcs_plan import TCSPlan
    from strategy.sweep_plan import SweepPlan
    from strategy.gex_pin_butterfly import GEXPinButterflyStrategy
    from strategy.iron_condor_strategy import IronCondorStrategy
    _missing = [c.__name__ for c in (
        RunawayPlan, TCSPlan, SweepPlan,
        GEXPinButterflyStrategy, IronCondorStrategy)
        if "entry_window" not in getattr(c, "PLAN_CHECKS", ())]
    check("W7 every entry strategy's plan declares an entry_window check",
          not _missing, ", ".join(_missing) or "none")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_entry_windows: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
