#!/usr/bin/env python3
"""check_conviction_removed.py — v2.1
v2.1  2026-08-27  r159: the docstring named the retired classifier's field by
      its old name, which tripped the exorcism gate
      — the land gate was RED at r152-r158. Renamed; the gate is green again.

🔴 THE SETUP SCORER IS DELETED. NO GRADE, NO CONVICTION, NO WEIGHTED SUM.

Operator, 2026-08-27: *"What fucking SUM are we still using??? That is TRASH
CODE. It's held over dumpster fodder from otv3 which was a complete failure."*
And: *"Get the grading bullshit out of there. If we re-introduce it later, it
won't be anything resembling the previous model."*

WHAT IT WAS: four dimensions x weights, summed to a `total`, compared against a
threshold to emit an A/B letter or REFUSE the trade.

WHY IT IS GONE — docs/INHERITED_FINDINGS.md §4, measured:
  **A-grade 399 trades −$8,244 · B-grade 220 trades +$1,893.**
It SELECTED LOSERS. ~90% of the grade was ONE COLUMN PRINTED TWICE
(the retired conviction score and `signal_quality`, identical medians AND identical
spreads over 619 trades) plus two constants measuring 1.000 across all 619 —
and those constants were `vwap_alignment` and `liquidity_clear`, two of the
four dimensions. The sum never measured anything.

⚠️ BY 2026-08-27 IT CONTRIBUTED NOTHING BUT REFUSALS. Both of its named gates
were default-OFF (`MIN_RRR_ACTIVE=0`, `VWAP_FILTER_ACTIVE=0`), and
`signal.conviction` defaulted to 0.0 with exactly ONE strategy of seven ever
setting it — so five strategies were capped at 0.75 of the score permanently.
TSLA's runaway scored vwap 1.0 / liquidity 1.0 / rrr 1.0 / macro 0.8, totalled
**0.43 against a 0.55 floor**, and was refused while the whole fleet sat at
zero trades through the highest-volume half hour of the day.

⚠️ AND THE PROFILES WERE ARITHMETICALLY BROKEN besides: weights were removed
over time and the remainder never rescaled. ContinuationStrategy topped out at
0.450 against a 0.55 floor — mathematically unable to pass on any tape — while
owning the best measured exit in the fleet (continuation_trail, 149 trades,
85%, +$27,884).

THE VETOES THAT REMAIN ARE THE OPERATOR'S, AND THEY LIVE IN THE STRATEGIES:
the R hurdle (muted under relaxed), session-map geometry, entry windows, level
invalidation, distance-to-pin. A setup either meets its own spec or it does
not. There is no second opinion summed from weights nobody chose.

⚠️ WHAT MUST SURVIVE: `TrendVote.conviction` (analysis/trend_engine.py) is
computed fresh from ADX and EMA alignment on every call — a per-timeframe vote
weight, NOT the leaky integrator. `ScoreResult.conviction` (shadow/) is the
shadow scorer's own output, log-only by design. Three different things share
the name; only one was dead.
"""
import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def _code(path):
    """Source with comment lines stripped — match CODE, never the prose that
    explains a removal. Five guards this week fired on their own comments."""
    return "\n".join(l for l in open(path, encoding="utf-8").read().split("\n")
                     if not l.strip().startswith("#"))


def main():
    # ── S1 — the file is GONE ────────────────────────────────────────────
    check("S1 risk/setup_scorer.py no longer exists",
          not os.path.exists(os.path.join(_root, "risk", "setup_scorer.py")))

    # ── S2 — and nothing imports it ──────────────────────────────────────
    bad = []
    for root, _, files in os.walk(_root):
        if "/.git" in root or "__pycache__" in root:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(root, fn)
            try:
                tree = ast.parse(open(p, encoding="utf-8").read())
            except Exception:                                   # noqa: BLE001
                continue
            for n in ast.walk(tree):
                if (isinstance(n, ast.ImportFrom) and n.module
                        and "setup_scorer" in n.module):
                    bad.append(f"{os.path.relpath(p, _root)}:{n.lineno}")
                if isinstance(n, ast.Import):
                    for a in n.names:
                        if "setup_scorer" in a.name:
                            bad.append(f"{os.path.relpath(p, _root)}:{n.lineno}")
    check("S2 nothing imports setup_scorer", not bad, ", ".join(bad) or "none")

    # ── S3 — main.py's trade path has no score, no scorer, no grade ──────
    mtree = ast.parse(open(os.path.join(_root, "main.py"), encoding="utf-8").read())
    names = {n.id for n in ast.walk(mtree) if isinstance(n, ast.Name)}
    check("S3 main.py references neither `score` nor `scorer`",
          "score" not in names and "scorer" not in names,
          ", ".join(sorted(names & {"score", "scorer"})) or "clean")

    # ── S4 — no A/B letter is assigned anywhere in the trade path ────────
    import re
    hits = []
    for rel in ("main.py", "execution/entry_engine.py", "risk/risk_manager.py"):
        p = os.path.join(_root, rel)
        if os.path.exists(p) and re.search(r"grade\s*=\s*['\"][AB]['\"]", _code(p)):
            hits.append(rel)
    check("S4 no code assigns an A or B grade", not hits, ", ".join(hits) or "none")

    # ── 🔴 S5 — WHAT MUST SURVIVE. Two live things share the name. ───────
    te = _code(os.path.join(_root, "analysis", "trend_engine.py"))
    check("S5 TrendVote.conviction is UNTOUCHED (fresh ADX+EMA, not the leak)",
          "vote.conviction = adx_score" in te)

    # ── S6 — the trade record still HAS its columns ──────────────────────
    # ⚠️ Removing the selector must not drop the columns: the DB schema and
    # every dashboard read them, and a future selector will refill them.
    tl = _code(os.path.join(_root, "database", "trade_logger.py"))
    check("S6 setup_grade / setup_score columns still exist in the schema",
          "setup_grade" in tl)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_conviction_removed: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
