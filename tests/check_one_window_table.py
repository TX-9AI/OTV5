#!/usr/bin/env python3
"""tests/check_one_window_table.py — v5.3
v5.3  2026-11-09  OTV5 r103 (RETIRE.5 step 2) — the GEX fly row is removed with the fly, so its admission pin, the three config pins (BUTTERFLY_ENTRY_START_ET, GEX_BFLY_EARLIEST_ET, BUTTERFLY_ENTRY_CUTOFF_ET - the last gated nothing since r209), session_guard's _BUTTERFLY_CUTOFF, the two gex_pin_butterfly pins and its two W2 pairs go with it. Every live pin is unchanged.
v5.2  2026-11-08  OTV5 r88 (RETIRE.3) — the TCS row is removed with the TCS, so its admission pin, the two config pins, the two
      tcs_plan pins and its two W2 pairs go with it. Every live pin is unchanged.
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — RE-POINTED (WA 38.4): the ORB, VOLT, ATP and sweep windows are removed, so their 18 pins, their W2 pairs and
      W2b (the sweep's unread start) go with them; W4 overrides Breakout's row. Every live pin is unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
ONE ENTRY-WINDOW TABLE, AND NOTHING READS A WINDOW FROM ANYWHERE ELSE.

v1.4  2026-10-12 — OTV4TEST r273 (BFLY.10) — W5 pins UPDATED BY RULING: both fly rows and the three names
      derived from the GEX row (BUTTERFLY_ENTRY_START_ET, GEX_BFLY_EARLIEST_ET, gex_pin_butterfly.EARLIEST_ET)
      move 12:00 -> 13:00 (marked "# r273"). The operator, 2026-10-12: "reduce the fly window to 1300".

v1.3  2026-10-02 — OTV4TEST r187 (ROSTER.1) — W5 pins UPDATED BY RULING: "let's impose a 1029 debit
      cutoff rule, but exempts the GEX pin fly" (2026-10-02). The admission rows of Runaway, Hunt,
      Breakout and VOLT and every name derived from them move 15:40 -> 10:30. The ORB row and its
      derived names, the credit rows, both flies and DEBIT_DIRECTIONAL_CUTOFF_ET are unchanged.

v1.2  2026-09-30 — OTV4TEST r179 (BFLY.9) — ONE W5 pin UPDATED BY RULING: admission.ATPButterfly.window
      11:30 -> 12:00 (marked "# r179"). The plan already stayed dormant until 12:00; the operator: "12:00 is fine".
v1.1  2026-09-26 — OTV4TEST r149 (EOD.1) — W5's pins UPDATED BY RULING, as W5 itself provides. The
      operator: "I wanna extend the debit window to all day", "1. Stop entries at 1540 / 2. Resting limit
      orders at 1545, ladder exits at 1550". EIGHTEEN pins move (each marked "# r149"): the five
      directional admission rows, their ten derived names, 11:30 -> 15:40; FLATTEN_WINDOW_OPEN_ET
      15:40 -> 15:45 and VERTICAL_HOLD_TO_ET 15:50 -> 15:45 (the resting minute); HARD_CLOSE_ET
      15:45 -> 15:55 (the cross). The other 33 are unchanged, measured on the r149 build.
v1.0  2026-09-26 — OTV4TEST r148 (WIN.1). The operator, 2026-09-22: "Why are there
      multiple places for the trade windows? Why isn't there 1 universal table?";
      2026-09-26: "I agree to all of that." Windows lived in FOUR layers - the admission
      table, ~20 config constants, literal fallbacks inside the plans, harness copies -
      and two plans (tcs_plan, sweep_plan) fell back to (14, 0) against a live 15:40,
      r81's defect pre-armed. Three strategies read config names that never existed
      (HUNT_CUTOFF_ET, BREAKOUT_LATEST_ET, GEX_BFLY_LATEST_ET), so their windows lived in
      code while looking configurable. config.ENTRY_WINDOWS is now the one source.

  W1  every admission-table window == config.ENTRY_WINDOWS (all nine strategies)
  W2  every plan's resolved window == its ENTRY_WINDOWS row
  W2b (r76: removed with the sweep) sweep_credit_spread.EARLIEST_ET is DECLARED BUT UNREAD (the sweep plan governs);
      it is exempt from W2 and this fails the moment any runtime file starts reading it
  W3  no strategy/execution file reads a window name through getattr(config, NAME, <literal>)
      - the shape that turned a missing name into a silent 14:00 (definition-shaped, WA 20)
  W4  config.ADMISSION_RULES can no longer change a window (a second source)
  W5  THE EQUIVALENCE PIN: all 47 resolved window values as measured at r148. At r147 they
      were identical except admission.TrendCreditSpread (11:30 -> 11:31, the minute its plan
      already opened). A later window RULING updates these pins on purpose; nothing else may.

Run:  python3 tests/check_one_window_table.py
"""
from __future__ import annotations

import ast
import importlib
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
logging.disable(logging.CRITICAL)

PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if detail and not ok else ""))
    if not ok:
        PROBLEMS.append(name)


def hhmm(t) -> str:
    return f"{t[0]}:{t[1]:02d}"


PIN = {   # measured on the r148 build; identical to r147 except the TrendCreditSpread admission row
    "admission.Breakout.window": ((9, 35), (10, 30)),   # r187
    "admission.LiquidityHunt.window": ((9, 35), (10, 30)),   # r187
    "admission.RunawayContinuation.window": ((9, 35), (10, 30)),   # r187
    "config.CONDOR_ENTRY_CUTOFF_ET": (15, 40),
    "config.CONDOR_ENTRY_START_ET": (11, 31),
    "config.CREDIT_ENTRY_END_ET": (15, 40),
    "config.CREDIT_ENTRY_START_ET": (11, 31),
    "config.DEBIT_DIRECTIONAL_CUTOFF_ET": (15, 40),   # r149
    "config.ENTRY_OPEN_ET": (9, 35),
    "config.FLATTEN_WINDOW_OPEN_ET": (15, 45),   # r149
    "config.HARD_CLOSE_ET": (15, 55),   # r149
    "config.ORB_NO_ENTRY_AFTER_ET": (15, 40),   # r149
    "config.RUNAWAY_CUTOFF_ET": "10:30",   # r187
    "config.VERTICAL_HOLD_TO_ET": (15, 45),   # r149
    "strategy.breakout.EARLIEST_ET": "09:35",
    "strategy.breakout.LATEST_ET": "10:30",   # r187
    "strategy.liquidity_hunt.WINDOW_OPEN_ET": (9, 35),
    "strategy.runaway_plan.WINDOW_OPEN_ET": (9, 35),
    "strategy.liquidity_hunt.CUTOFF_ET": (10, 30),   # r187
    "strategy.runaway_continuation.CUTOFF_ET": "10:30",   # r187
    "strategy.runaway_plan._cutoff_hm()": (10, 30),   # r187
}


def resolved() -> dict:
    import config
    out = {}
    for k in PIN:
        if k.startswith("config."):
            v = getattr(config, k[7:], "<absent>")
            out[k] = tuple(v) if isinstance(v, (tuple, list)) else v
    mods = {}
    for k in PIN:
        if (k.startswith("strategy.") or k.startswith("risk.")) and not k.endswith("()"):
            mod, attr = k.rsplit(".", 1)
            mods.setdefault(mod, importlib.import_module(mod))
            v = getattr(mods[mod], attr)
            out[k] = tuple(v) if isinstance(v, (tuple, list)) else (v.strftime("%H:%M") if hasattr(v, "strftime") else v)
    from strategy import runaway_plan
    out["strategy.runaway_plan._cutoff_hm()"] = tuple(runaway_plan._cutoff_hm())
    from execution.position_manager import rules
    for name, r in rules().items():
        out[f"admission.{name}.window"] = tuple(tuple(x) for x in r.window)
    return out


def main() -> int:
    print("one entry-window table (WIN.1)")
    hits = []
    WIN = ("_ET",)   # time names only (GEX_BFLY_SMOOTH_WINDOW is a length, not a time)
    for d in ("strategy", "execution"):
        for f in sorted(os.listdir(os.path.join(ROOT, d))):
            if not f.endswith(".py"): continue
            tree = ast.parse(open(os.path.join(ROOT, d, f)).read())
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr"
                        and len(node.args) == 3 and isinstance(node.args[0], ast.Name) and node.args[0].id == "config"
                        and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)
                        and (node.args[1].value.endswith("_ET") or node.args[1].value.endswith("_ET_FORK"))
                        and isinstance(node.args[2], (ast.Tuple, ast.Constant)) and not (isinstance(node.args[2], ast.Constant) and node.args[2].value is None)):
                    hits.append(f"{d}/{f}:{node.lineno} {node.args[1].value}")
    check("W3 no window read through getattr(config, NAME, <literal>)", not hits, "; ".join(hits))

    try:
        import config
        EW = config.ENTRY_WINDOWS
    except Exception as exc:                                      # noqa: BLE001
        for t in ("W1", "W2", "W4", "W5"):
            check(t, False, f"config.ENTRY_WINDOWS absent ({type(exc).__name__})")
        print(f"RED — {len(PROBLEMS)} failed"); return 1
    from execution.position_manager import rules
    R = rules()
    bad = [n for n in EW if tuple(tuple(x) for x in R[n].window) != tuple(tuple(x) for x in EW[n])]
    check("W1 admission windows == config.ENTRY_WINDOWS", not bad and set(R) == set(EW), f"differ: {bad}, keys {sorted(set(R) ^ set(EW))}")

    from strategy import runaway_continuation, liquidity_hunt, breakout   # r103: gex_pin_butterfly removed
    pairs = [
        ("RunawayContinuation end", runaway_continuation.CUTOFF_ET, hhmm(EW["RunawayContinuation"][1])),
        ("LiquidityHunt end", liquidity_hunt.CUTOFF_ET, EW["LiquidityHunt"][1]),
        ("Breakout end", breakout.LATEST_ET, hhmm(EW["Breakout"][1])),
    ]
    norm = lambda v: tuple(v) if isinstance(v, (tuple, list)) else v
    mism = [f"{n}: plan {norm(a)!r} vs table {norm(b)!r}" for n, a, b in pairs if norm(a) != norm(b)]
    check("W2 every plan's window == its ENTRY_WINDOWS row", not mism, "; ".join(mism))

    saved = getattr(config, "ADMISSION_RULES", None)
    try:
        config.ADMISSION_RULES = {"Breakout": {"window": ((1, 0), (2, 0))}}
        w = tuple(tuple(x) for x in rules()["Breakout"].window)
        check("W4 ADMISSION_RULES cannot override a window", w == tuple(tuple(x) for x in EW["Breakout"]), f"got {w}")
    finally:
        if saved is None:
            try: delattr(config, "ADMISSION_RULES")
            except AttributeError: pass
        else: config.ADMISSION_RULES = saved

    got = resolved()
    diff = [f"{k}: {got.get(k)!r} != pinned {v!r}" for k, v in PIN.items() if got.get(k) != v]
    check(f"W5 all {len(PIN)} resolved window values match the r149 pins", not diff, "; ".join(diff[:6]))
    print("GREEN" if not PROBLEMS else f"RED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
