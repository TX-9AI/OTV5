#!/usr/bin/env python3
"""check_pairing_table.py — v1.1
v1.1  2026-08-27  r160: LEG TWO IS UNIVERSALLY A SWEEP (operator ruling of
      2026-08-27, supersedes the 08-25 rows). R4.4/R4.6 now pin that a fork
      tine is NOT admitted as leg two from any predecessor; R4.7/R4.12 keep the
      sweep completion; R4.17 is retired — "a fork needs no rejection" was
      about a fork as leg ONE.

RULE 4: which trigger opened leg 1 constrains what may complete it.

🔴 OPERATOR'S RULING, 2026-08-25:
    TREND CS first  → ONLY a sweep, and only on a REJECTION.
    SWEEP first     → a fork tine, geometrically placed on the right side.
    FORK TINE first → another (opposite) fork tine, or a sweep.
    TREND CS may NEVER be leg 2 — *"that move invalidates the whole premise of
    a 'trend' credit spread."*

⚠️ REJECTION IS A SWEEP-CLASS REQUIREMENT, NOT A FORK ONE. Operator: *"a
qualifying PDH/PDL or other named level, but as a SWEEP — fork does not need a
rejection, it is assumed to be stable if it's present."*
"""
import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def _load():
    """Load ONLY the pairing helpers from main.py — importing main runs a bot."""
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    want = {"_trigger_class", "_pairing_allowed", "_sweep_has_rejection"}
    keep = [n for n in tree.body
            if (isinstance(n, ast.FunctionDef) and n.name in want)
            or (isinstance(n, ast.Assign)
                and any(getattr(t, "id", "").startswith(("_TREND_", "_SWEEP_",
                                                         "_FORK_", "_PAIRING_"))
                        for t in n.targets))]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "<pairing>", "exec"), ns)
    return ns


def main():
    ns = _load()
    allowed = ns["_pairing_allowed"]
    klass = ns["_trigger_class"]

    check("R4.0 the three trigger classes map from the real source strings",
          klass("trend_orb") == "trend" and klass("sweep_reversal") == "sweep"
          and klass("1h_fork") == "fork" and klass("1d_fork") == "fork",
          "trend_orb / sweep_reversal / 1h_fork / 1d_fork")

    # ⚠️ A SWEEP LEG 2 NOW NEEDS A LIVE REJECTION AS WELL AS A PERMITTED
    # CLASS, so these class-level checks must supply one — otherwise they
    # measure the rejection gate rather than the pairing table.
    class _Sweep:
        def __init__(self, reclaimed=True, invalidated=False, bars=1):
            self.reclaimed, self.invalidated = reclaimed, invalidated
            self.bars_ago = bars

    _LIVE = {"sweep": _Sweep()}

    # ── TREND first: sweep only ──────────────────────────────────────────
    check("R4.1 TREND leg 1 is completed by a SWEEP",
          allowed("trend_orb", "sweep_reversal", _LIVE)[0])
    check("R4.2 TREND leg 1 is NOT completed by a fork tine",
          not allowed("trend_orb", "1h_fork")[0])
    check("R4.3 TREND leg 1 is NOT completed by another trend spread",
          not allowed("trend_orb", "trend_orb")[0])

    # ── SWEEP first: a sweep again (r160) ────────────────────────────────
    check("R4.4 SWEEP leg 1 is completed by a SWEEP, never a fork tine (r160)",
          allowed("sweep_reversal", "sweep_reversal", _LIVE)[0]
          and not allowed("sweep_reversal", "1h_fork")[0]
          and not allowed("sweep_reversal", "1d_fork")[0])

    # 🔴 THE PREMISE CONFLICT. A sweep asserts a level REJECTED; a trend CS
    # asserts a trend RUNNING. Both cannot be true about one tape.
    _ok, _why = allowed("sweep_reversal", "trend_orb")
    check("R4.5 a TREND CS may NEVER follow a sweep — premise conflict",
          not _ok and "premise" in _why.lower(), _why[:70])

    # ── FORK first: sweep only (r160) ────────────────────────────────────
    check("R4.6 FORK leg 1 is NOT completed by another fork tine (r160)",
          not allowed("1h_fork", "1d_fork")[0] and not allowed("1d_fork", "1h_fork")[0])
    check("R4.7 FORK leg 1 is completed by a sweep",
          allowed("1h_fork", "sweep_reversal", _LIVE)[0])
    check("R4.8 FORK leg 1 is NOT completed by a trend spread",
          not allowed("1h_fork", "trend_orb")[0])

    # ── the trend CS is leg-1-only, from every predecessor ───────────────
    check("R4.9 NO trigger admits a trend CS as leg 2",
          all(not allowed(src, "trend_orb")[0]
              for src in ("trend_orb", "sweep_reversal", "1h_fork", "1d_fork")),
          "leg-1-only trigger")

    # ⚠️ FAIL CLOSED on anything unrecognised — a new trigger must be added to
    # the table deliberately, never admitted by default.
    check("R4.10 an UNKNOWN trigger is refused, not admitted",
          not allowed("brand_new_trigger", "sweep_reversal")[0]
          and not allowed("sweep_reversal", "brand_new_trigger")[0]
          and not allowed("", "")[0])

    # ⚠️ EVERY REFUSAL SPEAKS. r124: 406 consecutive silent refusals cost five
    # queries to explain one afternoon.
    check("R4.11 every refusal carries a reason",
          all(bool(allowed(a, b, _LIVE)[1])
              for a, b in (("trend_orb", "1h_fork"),
                           ("sweep_reversal", "trend_orb"),
                           ("x", "y"))))

    # ── 🔴 THE SWEEP'S REJECTION REQUIREMENT ─────────────────────────────
    # Operator: *"for a sweep there has to be a rejection or we don't sell
    # it."* The class check alone says the TRIGGER TYPE is permitted; it says
    # nothing about whether a rejection actually happened.
    def _pair(leg1, leg2, sweep):
        return allowed(leg1, leg2, {"sweep": sweep} if sweep else {})

    check("R4.12 a sweep leg 2 with a LIVE rejection is admitted",
          _pair("trend_orb", "sweep_reversal", _Sweep())[0])

    # ⚠️ A WICK IS NOT A REJECTION — it takes a CLOSE.
    check("R4.13 a pierce with no reclaiming CLOSE is refused",
          not _pair("trend_orb", "sweep_reversal", _Sweep(reclaimed=False))[0])

    # ⚠️ RECLAIMED-THEN-INVALIDATED IS A BREAKOUT, and selling a boundary that
    # already gave way is the worst version of this trade.
    check("R4.14 reclaimed-then-invalidated is refused as a breakout",
          not _pair("trend_orb", "sweep_reversal", _Sweep(invalidated=True))[0])

    # 🔴 THE CVX LOOP. `reclaimed` is a LATCHED FLAG, true for hours. Age is
    # measured from the RECLAIM BAR, and a stale one is not an event.
    _ok, _why = _pair("trend_orb", "sweep_reversal", _Sweep(bars=400))
    check("R4.15 a STALE latched reclaim is refused — the CVX loop",
          not _ok and "latched" in _why.lower(), _why[:64])

    check("R4.16 NO sweep state at all is refused, not admitted",
          not _pair("trend_orb", "sweep_reversal", None)[0])

    # r160 — R4.17 retired: a fork is never leg two, so "a fork needs no
    # rejection" has no leg-two case. Pinned the other way round.
    check("R4.17 a FORK is refused as leg 2 even with no sweep state (r160)",
          not _pair("sweep_reversal", "1h_fork", None)[0])

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_pairing_table: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
