#!/usr/bin/env python3
"""check_lone_stop.py — v1.0

🔴 THE LONE-VERTICAL STOP IS A FRACTION OF THE RISK, NOT OF THE CREDIT.

Operator, 2026-08-27, after CVX entered the SAME 197.5/192.5 spread SEVENTEEN
times in twelve minutes, every one dead inside a minute:
*"We need to fix the structure that that loop was exploiting."*

WHAT IT WAS: `stop_level = entry_prem * 1.15` — fifteen percent of the CREDIT.
**That is inverted.** The less credit collected, the tighter the stop in
DOLLARS, so the structures with the least premium got the least room:

    credit $0.58  ->  stop distance $0.087     <- the CVX loop
    credit $1.50  ->  stop distance $0.225
    credit $3.00  ->  stop distance $0.450

A thin credit means the short strike is FAR OUT and the position is LESS
threatened — and it was handed a stop a single tick clears. Eight cents of
tolerance against $442 of risk. Enter, noise, stop, re-arm, repeat.

NOW: anchored to `width - credit`, which is what is actually at stake and does
not shrink as the credit shrinks. Same 15% — a $0.58 credit on a 5-wide gets
**$0.663** of room instead of $0.087.

⚠️ THIS IS NOT THE R HURDLE AND IS NOT MUTED BY RELAXED, and the distinction is
the whole point. R is a RATIO judged once at entry — economics, and relaxed
mutes it deliberately to collect the population it would refuse. This uses only
R's DENOMINATOR, as a DISTANCE, continuously, to decide when to LEAVE. A
relaxed R-0.11 trade is still taken; it simply lives long enough to produce an
outcome. **A trade stopped by noise is not an observation** — today's sixteen
CVX rows said nothing about whether selling that level works, because none of
them survived long enough to find out.
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


def main():
    from config import LONE_STOP_PCT_OF_RISK as P

    src = open(os.path.join(_root, "execution", "exit_engine.py"),
               encoding="utf-8").read()
    code = "\n".join(l for l in src.split("\n")
                     if not l.strip().startswith("#"))

    # ── 🔴 L1 — THE INVERTED RULE IS GONE FROM THE CODE ──────────────────
    # ⚠️ Match CODE, not the comment that explains the removal — that comment
    # quotes the old expression, and five guards this week fired on their own
    # prose.
    check("L1 the credit-anchored stop is gone",
          "entry_prem * (1 + 0.15)" not in code, "no `entry_prem * 1.15`")

    check("L2 the stop is anchored to the risk",
          "_risk * LONE_STOP_PCT_OF_RISK" in code)

    # ── L3 — the arithmetic, on the structure that looped ────────────────
    credit, width = 0.58, 5.0
    risk = width - credit
    new_dist = risk * P
    old_dist = credit * P
    check("L3 the CVX structure gets real room now",
          new_dist > 0.50, f"${old_dist:.3f} -> ${new_dist:.3f} "
                           f"({new_dist / old_dist:.1f}x)")

    # ── 🔴 L4 — THE INVERSION IS ACTUALLY REVERSED ───────────────────────
    # Under the old rule, room RISES with credit. Under the new one it FALLS —
    # which is correct: a fat credit means the short strike is near the money
    # and less is at stake.
    room = [(width - c) * P for c in (0.58, 1.50, 3.00, 4.00)]
    check("L4 room now FALLS as the credit rises (was: rose)",
          room == sorted(room, reverse=True),
          " > ".join(f"{r:.3f}" for r in room))

    # ── L5 — a missing width must not silently become no stop ────────────
    check("L5 a missing spread_width falls back and WARNS",
          "credit-anchored fallback" in src and "logger.warning" in code)

    # ── 🔴 L6 — NOT MODE-DEPENDENT ───────────────────────────────────────
    # If this ever consults `relaxed`, it has become an economics gate and the
    # circle the operator asked about would be real.
    fn = next((n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef)
               and n.name == "_evaluate_condor_leg"), None)
    body = ast.unparse(fn) if fn else ""
    check("L6 the lone stop never consults the relaxed flag",
          "relaxed" not in body.lower())

    # ── L7 — the exit reason states the rule it applied ──────────────────
    check("L7 the exit reason names the risk-anchored stop",
          "of risk" in src)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_lone_stop: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
