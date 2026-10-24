#!/usr/bin/env python3
"""check_structure_viable.py
v1.3  2026-09-24  OTV4TEST r128: V6 AND V7 RE-POINTED AT strategy/sweep_plan.py AND
      strategy/credit_vertical.py. Fork r5 (8a36b6f) moved the sweep's selection
      out of sweep_credit_spread.py, so both read a file that no longer holds
      the gate (V6: viab@-1 ready@-1). Each property is MOVED, NOT DROPPED
      (section 38.4):
      · V6 "survivability is judged BEFORE the trade is marked ready, and never
        through the muteable R hurdle" is now three parts. V6a EXECUTES the real
        path: SweepPlan()._structure on a stub chain whose only difference from
        a sellable control is the short leg's ask - the wide quote is refused
        with why_key "stop_vs_spread" (credit_vertical.search_wing,
        credit_vertical.py:456-461, called at sweep_plan.py:352). V6b is an AST
        order check in SweepPlan.prepare: `self._structure(...)` runs, then the
        `if prep.structural:` block refuses and returns, and only after it
        `prep.ready = True`; no `.executable()` call in sweep_plan.py or
        sweep_credit_spread.py. V6c is an AST check that search_wing calls
        stop_survivable.
      · V7 "the sweep declares stop_vs_spread as a plan check" reads
        SweepPlan.PLAN_CHECKS (declared there at r128; TCSPlan has it at
        tcs_plan.py:218) instead of grepping sweep_credit_spread.py.
      Plus the r106 venv bootstrap (the lander runs CHECKs under
      /usr/bin/python3).
v1.2  2026-09-13  OTV4TEST r24: V8-V12 drive `is_spent` on REAL closed rows in a temp
      trades.db — the `_SPENT` dict and `mark_spent` are deleted. V9 re-derived to
      the fork's r5 ruling (spent on ACCEPTANCE only: a breach exit spends, V9b a
      stop-out does not); this file's pre-fork V9 pinned r154's stop-out rule.
v1.1  2026-08-27  r160: V6 re-pinned — no R hurdle in the sweep; survivability before READY. — v1.0

🔴 A STRUCTURE THAT CANNOT SURVIVE ITS OWN BID-ASK IS NOT A BAD TRADE.

Operator, 2026-08-27, after CVX entered the SAME 198/192 spread seven times in
seven minutes — each stopped inside a minute, about -$170 total:
*"It's allowed to enter bad trades, but if structurally it can't even survive
for a minute we need to address the structure."*

THE MEASUREMENT, straight off the alerts: credit $0.58, stop $0.67 (15%).
**The stop was NINE CENTS away** on a contract quoted in nickels. One quote
update moves the mark further than the entire stop distance — the trade was
stopped out by its own SPREAD, not by price.

⚠️ THIS IS NOT THE R HURDLE AND MUST NEVER BE MUTED BY RELAXED. R asks whether
a trade PAYS ENOUGH; relaxed exists to collect the population R would refuse.
This asks whether the trade can EXIST — construction, like requiring a
protective wing before selling undefined risk. A trade closed before it opened
teaches the sample nothing except how fast the loop spins.

⚠️ UNIVERSAL BY CONSTRUCTION. It compares two numbers from the same chain, so a
$9 stock and a $7,000 index are judged identically. That matters because
`WING_WIDTH = 5.0` is a FIXED DOLLAR amount — one strike increment on SPX, SIX
on CVX — which is how a 6-wide spread collecting $0.58 looked normal to the
code.
"""
import ast
import os
import sys
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
    from strategy.criteria import stop_survivable, STOP_VS_SPREAD_MIN

    # ── 🔴 V1 — THE EXACT CVX STRUCTURE IS REFUSED ───────────────────────
    ok, why = stop_survivable(0.09, 0.55, 0.61)
    check("V1 the CVX 2026-08-27 structure is refused (9c stop, 6c spread)",
          not ok, why[:72])

    # ── V2 — a healthy structure passes ──────────────────────────────────
    ok2, why2 = stop_survivable(0.45, 2.90, 2.95)
    check("V2 a wide stop over a tight quote passes", ok2, why2[:60])

    # ── V3 — UNMEASURABLE IS NOT PASSING ─────────────────────────────────
    # ⚠️ The whole failure class this week was a gate that silently never
    # applied. A viability check that cannot see the spread must REFUSE.
    check("V3 a missing quote refuses rather than assuming",
          not stop_survivable(0.45, 0.0, 0.0)[0])
    check("V4 a zero stop refuses", not stop_survivable(0.0, 1.0, 1.05)[0])

    # ── 🔴 V5 — IT IS NOT MODE-DEPENDENT ─────────────────────────────────
    # The same inputs must give the same answer in strict and relaxed. If this
    # ever reads `relaxed_active()`, the gate has become an economics gate.
    src = open(os.path.join(_root, "strategy", "criteria.py"),
               encoding="utf-8").read()
    fn = next((n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "stop_survivable"),
              None)
    body = ast.unparse(fn) if fn else ""
    check("V5 stop_survivable never consults the relaxed flag",
          "relaxed" not in body.lower() and "mode()" not in body)

    # ── V6 — the sweep applies it BEFORE the R hurdle ────────────────────
    # ⚠️ ORDER MATTERS: R is muted under relaxed, so a viability gate placed
    # after it would be reached only when R already passed.
    # r160: the sweep's R is a construction target inside search_wing (r157),
    # so there is no `t.executable()` hurdle to order against any more. The
    # property that survives: survivability is checked BEFORE the plan marks
    # the trade READY, and the muteable hurdle never returned.
    # r128 — RE-POINTED (38.4: moved, not dropped). Since fork r5 (8a36b6f)
    # the check lives in credit_vertical.search_wing, which SweepPlan._structure
    # calls; a refused wing becomes `prep.structural`, and prepare() refuses
    # and returns before `prep.ready = True`.
    from types import SimpleNamespace as _NS
    from strategy.sweep_plan import SweepPlan, Candidate

    def _structure_with_short_ask(ask):
        puts = [_NS(strike=198.0, bid=2.40, ask=ask, mark=round((2.40 + ask) / 2, 3)),
                _NS(strike=197.0, bid=0.40, ask=0.42, mark=0.41),
                _NS(strike=196.0, bid=0.10, ask=0.12, mark=0.11),
                _NS(strike=195.0, bid=0.03, ask=0.05, mark=0.04),
                _NS(strike=193.0, bid=0.01, ask=0.02, mark=0.015)]
        return SweepPlan()._structure(
            Candidate({"level_id": "v6", "price": 198.0, "kind": "support",
                       "provenance": "PDL"}), _NS(calls=[], puts=puts))
    _ctl = _structure_with_short_ask(2.44)      # a 4c quote: sellable
    _wide = _structure_with_short_ask(6.00)     # the SAME chain, a $3.60 quote
    check("V6a the sweep's own structure step refuses a wing its quote would stop out "
          "(stop_vs_spread), and sells the same chain on a tight quote",
          _ctl.sellable and not _wide.sellable and _wide.why_key == "stop_vs_spread",
          f"control sellable={_ctl.sellable} ({_ctl.why_key or 'ok'}); "
          f"wide sellable={_wide.sellable} key={_wide.why_key!r} {_wide.why[:60]}")

    def _fn(tree, name, cls=None):
        for n in ast.walk(tree):
            if cls and isinstance(n, ast.ClassDef) and n.name == cls:
                return next((f for f in n.body if isinstance(f, ast.FunctionDef)
                             and f.name == name), None)
            if not cls and isinstance(n, ast.FunctionDef) and n.name == name:
                return n
        return None

    _sp_tree = ast.parse(open(os.path.join(_root, "strategy", "sweep_plan.py"),
                              encoding="utf-8").read())
    _prep_fn = _fn(_sp_tree, "prepare", cls="SweepPlan")
    i_struct = i_refuse = i_ready = None
    if _prep_fn is not None:
        for n in ast.walk(_prep_fn):
            if (i_struct is None and isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == "_structure"):
                i_struct = n.lineno
            if (isinstance(n, ast.If) and "prep.structural" == ast.unparse(n.test).strip()
                    and any(isinstance(b, ast.Return) for b in n.body)
                    and "refuse(" in ast.unparse(n)):
                i_refuse = n.lineno if i_refuse is None else min(i_refuse, n.lineno)
            if (isinstance(n, ast.Assign) and ast.unparse(n).strip() == "prep.ready = True"):
                i_ready = n.lineno if i_ready is None else min(i_ready, n.lineno)
    _exe = []
    for _f in ("sweep_plan.py", "sweep_credit_spread.py"):
        _t = ast.parse(open(os.path.join(_root, "strategy", _f), encoding="utf-8").read())
        _exe += [f"{_f}:{n.lineno}" for n in ast.walk(_t)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "executable"]
    check("V6b SweepPlan.prepare builds the structure, refuses a structural fault, and "
          "only then marks ready; no muteable executable() hurdle in the sweep",
          None not in (i_struct, i_refuse, i_ready) and i_struct < i_refuse < i_ready
          and not _exe,
          f"_structure@L{i_struct} refuse(structural)@L{i_refuse} ready@L{i_ready} "
          f"executable()={_exe or 'none'}")

    _cv_tree = ast.parse(open(os.path.join(_root, "strategy", "credit_vertical.py"),
                              encoding="utf-8").read())
    _sw_fn = _fn(_cv_tree, "search_wing")
    _sv_calls = [n.lineno for n in ast.walk(_sw_fn or ast.Module(body=[], type_ignores=[]))
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "stop_survivable"]
    check("V6c credit_vertical.search_wing calls stop_survivable",
          bool(_sv_calls), f"calls @L{_sv_calls or 'none'}")

    check("V7 the sweep declares stop_vs_spread as a plan check",
          "stop_vs_spread" in SweepPlan.PLAN_CHECKS,
          f"SweepPlan.PLAN_CHECKS has {len(SweepPlan.PLAN_CHECKS)} names")

    # ── 🔴 V8 — A SPENT LEVEL DOES NOT RE-ARM ────────────────────────────
    # The second half of the CVX loop: nothing remembered the previous attempt,
    # so the level re-qualified every time price wandered back to its side.
    # `LiquiditySweep.invalidated` (LIQ.3) answers "has the TAPE accepted
    # through" — it cannot answer "did WE already try this and lose".
    import strategy.sweep_credit_spread as scs
    import tempfile as _tfv
    import database.trade_logger as _TLV
    from datetime import datetime, timedelta, timezone
    _TLV._trade_logger = _TLV.TradeLogger(os.path.join(_tfv.mkdtemp(), "v.db"))

    def _row(**kv):
        c = _TLV.get_trade_logger()._connect()
        try:
            c.execute(f"INSERT INTO trades ({','.join(kv)}) VALUES ({','.join('?' * len(kv))})",
                      tuple(kv.values()))
            c.commit()
        finally:
            c.close()
    _t = lambda m: (datetime.now(timezone.utc) - timedelta(minutes=m)).isoformat()
    check("V8 a fresh level is not spent",
          not scs.is_spent("CVX", "put", 198.0)[0])
    _row(trade_id="v9b", symbol="CVX", strategy="SweepCreditSpread", option_side="put", pool_price=201.0,
         status="closed", pnl_usd=-60.0, entry_time=_t(40), exit_time=_t(35),
         exit_reason="premium_stop_15% pnl=-16.0%")
    check("V9b (r5) a STOPPED-OUT level is NOT spent — acceptance only",
          not scs.is_spent("CVX", "put", 201.0)[0])
    _row(trade_id="v9", symbol="CVX", strategy="SweepCreditSpread", option_side="put", pool_price=198.0,
         status="closed", pnl_usd=0.0, entry_time=_t(30), exit_time=_t(25),
         exit_reason="sweep_breach_accepted: 2 closes beyond the pool 198.00 — the level is SPENT")
    check("V9 a level whose sweep exited on its BREACH is spent (read from trades.db)",
          scs.is_spent("CVX", "put", 198.0)[0])
    # ⚠️ ROUNDED TO THE CENT — the pool is recomputed per tick and drifts in the
    # last decimal; an exact-float key would never match itself and the lock
    # would silently never fire.
    check("V10 float drift still matches the spent key",
          scs.is_spent("CVX", "put", 198.004)[0])
    check("V11 the other side of the same price is a different level",
          not scs.is_spent("CVX", "call", 198.0)[0])
    check("V12 a different level is untouched",
          not scs.is_spent("CVX", "put", 202.0)[0])

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_structure_viable: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
