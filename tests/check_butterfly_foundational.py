#!/usr/bin/env python3
"""
tests/check_butterfly_foundational.py  v1.1
v1.1  2026-09-09  OTV4TEST r6 — BEST-R pick, OI on the fixture, persistence bar set to 1 here.
v1.0  2026-09-01  r208 — THE THREE CONDITIONS RELAXED MAY NEVER WAIVE.

Operator, 2026-09-01, after five flies fired on the first tick of the noon
window and three were stopped out inside the same minute: *"there's a couple of
things minimum that need to be met even on relaxed entries. They are: Is price
pinning right now? can the Pin even be reached? Can the floor clear the spread?
If any of those are 'no' then I don't even want a relaxed one taking it."*

🔴 WHAT HAPPENED, MEASURED FROM THE ALERTS RATHER THAN REASONED. Five flies at
12:00:00 ET; META 577.5±2 ×30 at debit 0.17, CRM 260±2 ×25 at 0.21, MU 980±5
×19 at 0.28. `BUTTERFLY_STOP_LOSS_PCT` is 0.25 OF THE DEBIT, so the floors were
4.3c, 5.3c and 7.0c. A fly's value is `lower + upper - 2*center` — a small
difference of three larger numbers — so three legs of quote noise compound into
a figure that is itself 17 cents. All three closed the same minute at -26% to
-35%: stopped out by their own marks, not by price.

⚠️ THE GATE FOR THIS ALREADY EXISTED AND HAD ONE CALLER. r154 built
`criteria.stop_survivable` after CVX entered the same spread seven times in
seven minutes, and scoped it to the sweep. The butterfly was not on that list
because on 2026-08-27 it had never fired. It has had no survivability check for
its entire life.

Born red at f74818b, where F1, F2, F4, F5 and F7 all fail.
"""
from __future__ import annotations

import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


class bf_C:
    """A quoted contract, in the shape the strategy actually reads."""
    def __init__(self, strike, bid, ask):
        self.strike, self.bid, self.ask = strike, bid, ask
        self.mark = round((bid + ask) / 2.0, 4)
        self.open_interest = 100          # OTV4TEST r6: zero OI is a STARVED input


def main():
    import config
    from strategy import gex_pin_butterfly as B
    from strategy.criteria import stop_survivable, STOP_VS_SPREAD_MIN

    pct = float(getattr(config, "BUTTERFLY_STOP_LOSS_PCT", 0.25))

    # ── F1 — the fly's own two-sided quote, built per leg ────────────────
    # 🔑 THE FLY'S SPREAD IS NOT ONE LEG'S SPREAD. Buying costs
    # lower.ask + upper.ask - 2*center.bid; selling receives the mirror.
    if not hasattr(B, "_structure_quote"):
        check("F1 the fly's own bid/ask is built from all three legs",
              False, "_structure_quote does not exist")
        check("F2 the 2026-09-01 META fly is REFUSED by its own spread",
              False, "_structure_quote does not exist")
        check("F3 a fly whose floor clears the spread is allowed",
              False, "_structure_quote does not exist")
    else:
        lo, ce, up = bf_C(575.5, 2.07, 2.13), bf_C(577.5, 1.17, 1.23), bf_C(579.5, 0.44, 0.50)
        b, a = B._structure_quote(lo, ce, up)
        want_b = 2.07 + 0.44 - 2 * 1.23
        want_a = 2.13 + 0.50 - 2 * 1.17
        check("F1 the fly's own bid/ask is built from all three legs",
              abs(b - want_b) < 1e-9 and abs(a - want_a) < 1e-9,
              f"got {b:.3f}/{a:.3f} want {want_b:.3f}/{want_a:.3f}")

        # ── F2 — THE ACTUAL TRADE, REFUSED ──────────────────────────────
        # The legs above price a 0.17 debit, which is META's fly to the cent.
        debit = lo.mark + up.mark - 2 * ce.mark
        ok, why = stop_survivable(debit * pct, b, a)
        check("F2 the 2026-09-01 META fly is REFUSED by its own spread",
              (not ok) and abs(debit - 0.17) < 0.02,
              f"debit={debit:.2f} floor={debit*pct:.4f} ok={ok} — {why[:60]}")

        # ── F3 — AND A REAL ONE IS NOT ─────────────────────────────────
        # ⚠️ A GATE THAT ONLY EVER REFUSES IS INDISTINGUISHABLE FROM BROKEN
        # (§17). The positive case is what proves it discriminates.
        lo2, ce2, up2 = bf_C(95, 6.07, 6.13), bf_C(100, 2.29, 2.35), bf_C(105, 0.90, 0.96)
        b2, a2 = B._structure_quote(lo2, ce2, up2)
        debit2 = lo2.mark + up2.mark - 2 * ce2.mark
        ok2, why2 = stop_survivable(debit2 * pct, b2, a2)
        check("F3 a fly whose floor clears the spread is allowed",
              ok2, f"debit={debit2:.2f} floor={debit2*pct:.3f} "
                   f"spread={a2-b2:.3f} — {why2[:60]}")

    # ── F4 — the categories, as DATA (WA §36) ───────────────────────────
    g = getattr(B, "GATES", {})
    check("F4 reach is FOUNDATIONAL and survivability is declared",
          g.get("EM_MAX_FRAC") == "FOUNDATIONAL"
          and g.get("STOP_VS_SPREAD_MIN") == "FEASIBILITY",
          f"EM_MAX_FRAC={g.get('EM_MAX_FRAC')} "
          f"STOP_VS_SPREAD_MIN={g.get('STOP_VS_SPREAD_MIN')}")

    # ── F5 — RELAXED IS GONE FROM THIS STRATEGY ENTIRELY ────────────────
    # Operator, 2026-09-01: "the 'relaxed' is adding unnecessary complexity —
    # get rid of relaxed entirely." Scoped to the butterfly at his follow-up,
    # since the sweep is still deliberately loose to collect parameters.
    # ⚠️ NOT A GREP FOR THE WORD. The file's history blocks discuss relaxation
    # at length and always will; §20 — an absence canary tests for a CALL, not
    # a mention, or good changelog prose trips it.
    bsrc = open(os.path.join(_root, "strategy", "gex_pin_butterfly.py"),
                encoding="utf-8").read()
    btree = ast.parse(bsrc, "gex_pin_butterfly.py")
    live = [n.lineno for n in ast.walk(btree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "relaxed"]
    check("F5 the butterfly makes no relaxed.* call at all",
          not live, f"live relax calls at lines {live}")
    check("F5b WING_EM_FRAC is deleted, not re-categorised",
          not hasattr(B, "WING_EM_FRAC") and "WING_EM_FRAC" not in g,
          f"attr={hasattr(B, 'WING_EM_FRAC')} gate={g.get('WING_EM_FRAC')}")

    # ── F6 — "is it pinning" was never relaxable, and must stay that way ──
    src = open(os.path.join(_root, "strategy", "gex_pin_butterfly.py"),
               encoding="utf-8").read()
    tree = ast.parse(src, "gex_pin_butterfly.py")
    relaxed_names = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "relaxed"):
            for arg in list(node.args) + [k.value for k in node.keywords]:
                if isinstance(arg, ast.Name):
                    relaxed_names.add(arg.id)
    check("F6 the PINNING test passes through no relax call",
          "PIN_STRIKE" not in relaxed_names and "PINNING" not in relaxed_names,
          f"relaxed constants: {sorted(relaxed_names)}")

    # ── F8 — THE WING SEARCH, DRIVEN END TO END ─────────────────────────
    # 🔑 THE TWO BOUNDS PULL OPPOSITE WAYS. R rises as the wing narrows;
    # survivability falls, because a fly's quote is FOUR leg-spreads wide while
    # its debit shrinks. With only R wired the selector steered to the least
    # survivable structure and called it best — 2026-09-01, five flies at R 8.5
    # to 16.9, three dead inside the minute.
    import sqlite3
    from strategy import plan as P
    import strategy.gex_pin_butterfly as bf
    from utils.time_utils import ET as _ET

    class _St:
        def __init__(s):
            s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()

    class _Ch:
        def __init__(s, calls): s.puts, s.calls = [], calls

    class _G:
        def __init__(s, pin, conc=0.60, env="PINNING"):
            s.gex_environment, s.pin_strike, s.pin_concentration = env, pin, conc

    st = _St(); P.ensure_tables(st); P.bind_store(st)
    bf.ENABLED = True
    _e, _l = bf.EARLIEST_ET, bf.LATEST_ET
    bf.EARLIEST_ET, bf.LATEST_ET = "09:30", "16:00"
    _em_real = bf.expected_move
    bf.expected_move = lambda u, iv, now=None: _em_real(
        u, iv, now=bf.datetime(2026, 8, 27, 12, 30, tzinfo=_ET))
    strat = bf.GEXPinButterflyStrategy(); strat.planner.symbol = "TST"

    # OTV4TEST r6: persistence is a bar (8 ticks); these fixtures assert SELECTION on
    # a single tick, so the bar is set to 1 here and pinned on its own in check_plan_prepares B13.
    import strategy.gex_pin_butterfly as _bfm; _bfm.PERSIST_TICKS = 1

    def _row(ts):
        r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                            "ts_epoch=?", (ts,)).fetchone()
        return (r["verdict"], r["reason"]) if r else None

    # ⚠️ THE 2026-09-01 SHAPE: a 1-wide ladder on penny legs. R 4.56 and the
    # old code took it. Both bounds cannot be met here at any debit —
    # width >= 64 x leg-spread means 2c legs need $1.28 of wing.
    bad = [bf_C(k, m - 0.01, m + 0.01) for k, m in
           ((99, 1.60), (100, 1.00), (101, 0.55), (102, 0.28), (103, 0.14))]
    P.begin_tick(90.0)
    sig = strat.generate_signal(gex=_G(101.0), chain=_Ch(bad), price_now=100.0,
                                now_et="12:30", atm_iv=0.43)
    r90 = _row(90.0)
    check("F8 the 2026-09-01 fly is refused, and the refusal names the bound",
          sig is None and r90 and r90[0] == "DECLINE"
          and "wing_search" in r90[1] and "clear their own spread" in r90[1],
          str(r90)[:130])

    # ── F8b — TWO WINGS QUALIFY AND THE NARROWEST WINS ──────────────────
    # Operator: "the wings should be a 1-R or better (that's the widest
    # allowed) but prefer narrower if available."
    good = [bf_C(k, m - 0.005, m + 0.005) for k, m in
            ((99, 2.55), (100, 1.70), (101, 1.00), (102, 0.70), (103, 0.45))]
    P.begin_tick(91.0)
    sig2 = strat.generate_signal(gex=_G(101.0), chain=_Ch(good), price_now=99.0,
                                 now_et="12:30", atm_iv=0.90)
    got = (sig2 and (sig2.lower_contract.strike, sig2.center_contract.strike,
                     sig2.upper_contract.strike))
    check("F8b two wings qualify and the BEST-R wing is taken (r6; here the narrower)",
          got == (100.0, 101.0, 102.0),
          f"{got} (wing 2 at 99/101/103 also clears R>=1)")
    check("F8c the apex is the pin, never a substitute",
          sig2 is not None and sig2.center_contract.strike == 101.0,
          f"apex={sig2 and sig2.center_contract.strike}")
    bf.EARLIEST_ET, bf.LATEST_ET = _e, _l
    bf.expected_move = _em_real

    # ── F7 — readiness is reachable ONLY through a qualified candidate ──
    # ⚠️ SOURCE-LEVEL BY NECESSITY AND LABELLED AS SUCH (§21). F8 proves the
    # search refuses and F8b proves it selects; this proves there is no OTHER
    # path to `prep.ready`, which is the shape that would let a future edit
    # compute the search and then set up a fly anyway — the `pin_concentration`
    # failure mode, where a value was measured, used for a boolean and thrown
    # away.
    parent = {}
    for node in ast.walk(btree):
        for kid in ast.iter_child_nodes(node):
            parent[kid] = node
    ready_sites, guarded = 0, 0
    for node in ast.walk(btree):
        # ⚠️ ONLY THE SITES THAT SET IT TRUE. `self.ready = False` in the
        # dataclass initialiser is not a path to a trade, and counting it made
        # this read 1/2 and fail for a reason unrelated to what it checks —
        # exactly the noisy-gate failure r150 and C.36 record.
        if not (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Attribute) and t.attr == "ready"
                        for t in node.targets)
                and isinstance(node.value, ast.Constant)
                and node.value.value is True):
            continue
        ready_sites += 1
        cur = node
        while cur in parent:
            cur = parent[cur]
            if isinstance(cur, ast.If):
                names = {n.id for n in ast.walk(cur.test) if isinstance(n, ast.Name)}
                if "_cands" in names:
                    guarded += 1
                    break
    check("F7 prep.ready is reachable only through the wing search",
          ready_sites > 0 and guarded == ready_sites,
          f"{guarded}/{ready_sites} assignments guarded by the candidate list")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_butterfly_foundational: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
