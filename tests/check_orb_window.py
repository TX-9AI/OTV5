#!/usr/bin/env python3
"""tests/check_orb_window.py  v1.2
v1.2  2026-09-26  OTV4TEST r149 (EOD.1) — W1 RE-POINTED: the ORB window closes at 15:40, the operator's
      "extend the debit window to all day" and "Stop entries at 1540" (was 11:30). W2's single boundary holds.
v1.1  2026-09-13  OTV4TEST r20 — W5 RE-DERIVED and W6 WIDENED to "no level
      surface reaches this file at all"; W7/W7b ADDED (the contract comes from
      the plan, no strike re-derived, and the conviction bump is gone).
      🔑 THE ASSERTIONS RUN ON TOKENISED CODE, comments and strings removed.
      §20 says scope a canary to a definition rather than a mention, but this
      file's changelog and its struck doctrine block are REQUIRED to name
      `select_orb_strike` and `conviction += 0.15` in order to describe removing
      them — so even a shaped pattern matched the documentation, and W7/W7b went
      red on their own prose on the first run. Mainline r365 hit this identically.
      Tokenising ends the class: the changelog can now say anything.
      Born red at 98eea8d on W6, W7 and W7b.
THE ORB ENTRY WINDOW IS 11:30, IT AGREES WITH THE DEBIT BLOCK, AND EVERY COPY
OF IT AGREES WITH config.

v1.0  2026-08-30  r193 — the window moved 11:00 -> 11:30 and the pool stopped
      moving the target. Born red at r192 (81a6233): the constant reads (11,0)
      there, two test files hardcode their own (11,0), and orb_strategy pulls
      the target to a named pool.

🔴 W3 EXISTS BECAUSE THE CONSTANT HAD THREE COPIES AND ONLY ONE OF THEM IS THE
ONE THAT TRADES. `tests/cascade_harness.py` and `tests/cascade_real.py` each
declared their own `ORB_NO_ENTRY_AFTER_ET = (11, 0)`. A harness rehearsing an
11:00 window against a fleet running 11:30 stays GREEN while measuring a
different system — the same fourth-copy shape as the PANEL mirror. This check
makes a fourth copy impossible to add quietly.

🔑 W2 IS THE ONE THAT WOULD COST A SESSION IF IT DRIFTED. Both cutoffs are
`>=` tests: the ORB window at orb_engine ~441 and the long-debit block in
`_afternoon_debit_blocked`. Equal values mean entries run to 11:29:59 and the
block takes over at 11:30:00 — no gap, no overlap. If they ever diverge, either
ORB stops arming while trades that depend on its state keep firing (the exact
contradiction the 08-20 extension was written to fix), or an ORB entry is
permitted into a window where the debit block refuses it and the refusal
arrives from somewhere confusing.

Run:  python3 tests/check_orb_window.py
"""
import os
import re
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    import config

    orb = tuple(config.ORB_NO_ENTRY_AFTER_ET)
    debit = tuple(config.DEBIT_DIRECTIONAL_CUTOFF_ET)

    check("W1 the ORB entry window closes at 15:40 (r149: all day, entries stop 15:40)", orb == (15, 40), str(orb))

    check("W2 the ORB window and the long-debit block are the SAME boundary",
          orb == debit, f"orb={orb} debit={debit}")

    # ── W3: every copy of the constant, anywhere in the tree ──────────────
    pat = re.compile(r"^\s*ORB_NO_ENTRY_AFTER_ET\s*=\s*\((\d+),\s*(\d+)\)", re.M)
    copies = {}
    for base, _dirs, files in os.walk(_root):
        if os.sep + ".git" in base:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(base, fn)
            try:
                body = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for m in pat.finditer(body):
                copies[os.path.relpath(path, _root)] = (int(m.group(1)), int(m.group(2)))
    wrong = {k: v for k, v in copies.items() if v != orb}
    check(f"W3 all {len(copies)} declared copies of the window agree with config",
          not wrong and len(copies) >= 1, f"disagreeing: {wrong or 'none'}")

    # ── W4: the ORB engine reads the constant, it does not restate it ─────
    eng = open(os.path.join(_root, "analysis", "orb_engine.py"),
               encoding="utf-8").read()
    check("W4 orb_engine compares against the imported constant",
          "(now.hour, now.minute) >= ORB_NO_ENTRY_AFTER_ET" in eng)

    # ── W5/W6/W7: the ORB knows NOTHING about levels (r20) ────────────────
    # ⚠️ ANCHORED ON CODE SHAPE, NEVER ON A MENTION. v4.7's changelog and the
    # struck doctrine block both have to NAME pools and levels in order to
    # describe removing them, so a bare string match would go red on this
    # file's own documentation — WORKING_AGREEMENT §20, and mainline's r365
    # watched its first version of W7 do exactly that.
    # 🔑 MATCH THE CODE, NOT THE PROSE. §20 says scope a canary to the shape of
    # a DEFINITION rather than a mention — but this file's changelog and its
    # struck doctrine block are REQUIRED to name `select_orb_strike` and
    # `conviction += 0.15` in order to describe removing them, so even a shaped
    # pattern matches the documentation. W7 and W7b both went red on exactly
    # that on their first run, which is mainline r365's experience repeated.
    # So the comments and strings are TOKENIZED OUT and the assertions run
    # against executable text alone. The changelog can then say anything.
    def _code_only(src: str) -> str:
        import io, tokenize
        out = []
        try:
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                out.append(tok.string)
        except Exception:                                       # noqa: BLE001
            return src                                # never hide a parse error
        return " ".join(out)

    _raw = open(os.path.join(_root, "strategy", "orb_strategy.py"),
                encoding="utf-8").read()
    st = _code_only(_raw)
    check("W5 the target is the plan's measured move — an ASSIGNMENT, not a pool",
          "target_100 , target_50 = prep . target_100 , prep . target_50" in st
          and "adjusted_target\"]" not in st)
    check("W6 no level surface reaches this file at all: no import, no parameter, no method",
          "LiquidityMap" not in st
          and "liq_map:" not in st
          and "def _analyze_liquidity" not in st
          and "liq_result" not in st,
          "one of: LiquidityMap import / liq_map param / _analyze_liquidity / liq_result")
    check("W7 the contract comes from the PLAN on every path — no strike is re-derived here",
          "contract = prep . direction , prep . side , prep . contract" in st
          and "round_to_strike" not in st
          and "select_orb_strike" not in st)
    check("W7b ...and the conviction bump that rode on a named level is gone",
          "conviction+=0.15" not in st.replace(" ", ""))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_orb_window: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
