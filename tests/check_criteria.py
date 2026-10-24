#!/usr/bin/env python3
"""
tests/check_criteria.py  v1.0  (2026-08-25)

`strategy/criteria.py` is the SINGLE SOURCE for anything the relaxed flag
changes — and structural prices are never among them.

⚠️ C5 IS THE ONE THAT MATTERS. Relaxed must never move a TRIGGER or an
INVALIDATION. Loosening evidence produces MORE PLANS of the same trade;
loosening a trigger produces A DIFFERENT TRADE WEARING THE SAME NAME, and the
two populations stop being comparable — which destroys the only thing the
relaxed/strict split exists for.
"""
import os
import sys

FAIL = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    for k in ("OT_RELAXED_ENTRY", "OT_PAPER_TRADING"):
        os.environ.pop(k, None)
    from strategy import criteria as C

    # ── C1: STRICT is the default, and R gates ──────────────────────────
    check("C1 with no flag the mode is STRICT and R gates",
          C.mode() == "STRICT" and C.r_hurdle() == C.R_FLOOR,
          f"{C.mode()} hurdle={C.r_hurdle()}")

    # ── C2: MUTED is None, never 0.0 ────────────────────────────────────
    # ⚠️ A floor of 0.0 would still reject a negative-R plan and would look
    # like a decision nobody made. The fit must tell "did not gate" from
    # "gated at zero" — the same discipline second_order.py uses for an
    # unmeasurable greek.
    os.environ["OT_RELAXED_ENTRY"] = "1"
    os.environ["OT_PAPER_TRADING"] = "1"
    for m in [m for m in sys.modules if m.startswith("strategy")]:
        del sys.modules[m]
    from strategy import criteria as C2
    check("C2 relaxed + paper MUTES the hurdle — None, never 0.0",
          C2.mode() == "RELAXED" and C2.r_hurdle() is None,
          f"{C2.mode()} hurdle={C2.r_hurdle()!r}")

    check("C3 a MUTED hurdle returns verdict MUTED, not PASS",
          C2.r_verdict(0.19)[0] == "MUTED", str(C2.r_verdict(0.19)[0]))

    # ── C4: THE LIVE GUARD SURVIVES THE REROUTE ─────────────────────────
    # ⚠️ criteria.py owns NO flag of its own — it delegates to
    # relaxed.is_allowed(), which refuses relaxed on a live box and FAILS
    # CLOSED when the mode cannot be read. A second source of truth here
    # would silently bypass that guard.
    os.environ.pop("OT_PAPER_TRADING", None)          # live box
    for m in [m for m in sys.modules if m.startswith("strategy")]:
        del sys.modules[m]
    from strategy import criteria as C3
    check("C4 relaxed on a LIVE box falls back to STRICT — hurdle stays up",
          C3.mode() == "STRICT" and C3.r_hurdle() == C3.R_FLOOR,
          f"{C3.mode()} hurdle={C3.r_hurdle()}")

    # ── C5: STRUCTURAL PRICES ARE NEVER MODE-DEPENDENT ──────────────────
    overlap = [k for k in C3.CRITERIA if k in C3.STRUCTURAL]
    check("C5 no STRUCTURAL price appears in the CRITERIA table",
          not overlap, str(overlap))

    raised = False
    try:
        C3.get("trigger_price")
    except ValueError:
        raised = True
    check("C5b asking criteria for a structural price RAISES", raised)

    # ── C6: criteria.py does not read its own env flag ──────────────────
    src = open(os.path.join(root, "strategy", "criteria.py"), encoding="utf-8").read()
    body = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))
    own_flag = "os.environ.get(\"OT_RELAXED" in body
    check("C6 criteria.py owns NO relaxed flag — it delegates", not own_flag)

    # ── C7: the tagging did NOT move ────────────────────────────────────
    # ⚠️ relaxed.tag() stamps relaxed_entry=1 on the trade record and is the
    # POPULATION LABEL, not a criterion. Purging it with the thresholds would
    # make relaxed and strict trades indistinguishable forever — the one
    # property this whole design depends on.
    rel = open(os.path.join(root, "strategy", "relaxed.py"), encoding="utf-8").read()
    check("C7 relaxed.tag() still exists — the population label is intact",
          "def tag(" in rel)

    print()
    if FAIL:
        print(f"FAILED {len(FAIL)}: {', '.join(FAIL)}")
        return 1
    print("check_criteria: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
