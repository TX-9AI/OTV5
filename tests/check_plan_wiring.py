#!/usr/bin/env python3
"""
tests/check_plan_wiring.py  v1.7  (2026-09-13)
v1.7  2026-09-13  OTV4TEST r25 — W9/W9b PASS A 1m FRAME. r24 requires the last closed bar to
      hold the 50, and these two calls passed none, so both went HOLD before
      reaching the chain / R they test. RED SINCE r24 AND SHIPPED THAT WAY: r24's
      gate list did not include this check. The frame's closes sit at the case's
      own price (101.6), so W9 still tests "no chain" and W9b still tests R.
v1.6  2026-09-08  OTV4TEST r3 — W9's fake ORB carries `fifty_accepted`, the runaway plan's trigger.
v1.5  2026-09-08  OTV4TEST r2 — W2 accepts `self.plan.prepare(` as the wiring:
      ORB's plan is a separate object the strategy owns (strategy/orb_plan.py).
v1.4  2026-09-03  r231 — W6 RE-DERIVED, NOT PATCHED. `classify()` requires
      `spot`; each fixture carries one chosen so the case it was written for
      is still the case being tested, rather than one that merely compiles
      (the r155 trap). New W6g pins r231's own rule where the range tests
      cannot reach it: a CEILING above the opening range but BELOW spot.
v1.3  r168: W9b re-pinned — the runaway carries no price invalidation.
v1.2  r160: W2 accepts `self.prepare(` as the plan entry (the sweep's
      generate_signal delegates to its plan and executes what it prepared).
v1.1  r147: W2 ignores returns inside nested helper functions (the
      butterfly's exact-strike lookup); it still flags every bare entry return.
v1.0  r146

THE PLAN IS THE STRATEGY'S INFORMER, NOT A SECOND STRATEGY — and it is WIRED.

Born red at cddfa06 (W1, W2, W4-W8 all fail there): the builders existed,
no strategy imported the plan, and the runaway's signal was invalid.

  W1  derived/plans.py contains NO strategy re-implementation (no builder
      defs, no strike selection, no chain walking).
  W2  every entry strategy owns a Plan and calls it (AST: `.planner.tick(`
      present; every `return None` inside generate_signal / decide /
      check_leg_triggers / _build_* is a plan terminal, not bare).
  W3  R is computed off the REAL width — never the $5 the builders assumed.
  W4  STRICT: a credit spread below the R floor REFUSES (executable() False).
  W5  RELAXED: the same spread is TAKEN, the R value is RECORDED, and the row
      carries the r_muted check — separable by query.
  W6  geometry: a ceiling below the opening range is INVALID; inside the
      range is INVALID; no opening range is UNMEASURED (None), never a pass.
  W7  an unmeasured check is written NULL/n/a, never 0.0/PASS.
  W8  refuse() feeds the edge-triggered gate reporter and take() clears it.

⚠️ EXECUTES, does not read source, wherever a claim is about runtime (WA §21).
The AST sweep in W1/W2 is about SHAPE, which is what it can prove.
"""
import ast
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def commit(self):
        self.conn.commit()


ENTRY_FNS = {"generate_signal", "decide", "check_leg_triggers",
             "_build_leg_signal", "_build_signal"}
STRATEGIES = ["orb_strategy", "runaway_continuation", "trend_credit_spread",
              "sweep_credit_spread", "gex_pin_butterfly",
              "iron_condor_strategy"]          # r163: daily fork retired


def _bare_returns(path):
    """`return None` / bare `return` inside an entry function that is NOT a
    plan terminal (t.refuse/starved/take/hold)."""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    bad = []
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        for fn in cls.body:
            if not isinstance(fn, ast.FunctionDef) or fn.name not in ENTRY_FNS:
                continue
            body_src = ast.get_source_segment(src, fn) or ""
            # r160: a strategy whose generate_signal delegates to its own
            # prepare() (the plan) is wired through that call
            # OTV4TEST r2: or to a plan object it owns (`self.plan.prepare(`)
            if ("planner.tick(" not in body_src and "t=None" not in body_src
                    and "self.prepare(" not in body_src
                    and ".plan.prepare(" not in body_src) \
                    and fn.name not in ("_build_leg_signal", "_build_signal"):
                # an ABC stub (`return None` only) is exempt
                if len(fn.body) == 1 and isinstance(fn.body[0], ast.Return):
                    continue
                bad.append(f"{fn.name}: no planner.tick()")
                continue
            # v1.1 — returns inside a NESTED helper (a local lookup function)
            # are not entry returns; only walk the entry function's own body
            nested = {id(x) for inner in ast.walk(fn)
                      if isinstance(inner, ast.FunctionDef) and inner is not fn
                      for x in ast.walk(inner)}
            for n in ast.walk(fn):
                if id(n) in nested:
                    continue
                if isinstance(n, ast.Return):
                    v = n.value
                    if v is None or (isinstance(v, ast.Constant) and v.value is None):
                        # the exception-handler `return None` AFTER a NO PLAN
                        # write is allowed: it is preceded by t.refuse(...)
                        line = src.split("\n")[n.lineno - 2].strip()
                        if "verdict=\"NO PLAN\")" in line or "t.refuse(" in line:
                            continue
                        if len(fn.body) == 1:
                            continue
                        bad.append(f"{fn.name}@{n.lineno}")
    return bad


def main():
    # ── W1 ────────────────────────────────────────────────────────────────
    ptree = ast.parse(open(os.path.join(_root, "derived/plans.py")).read())
    defs = {n.name for n in ast.walk(ptree) if isinstance(n, ast.FunctionDef)}
    builders = defs & {"_butterfly", "_participation", "_sweep", "_runaway",
                       "_condor", "_roll", "_fork", "_gamma_by_strike", "_pin"}
    psrc = open(os.path.join(_root, "derived/plans.py")).read()
    check("W1 derived/plans.py re-implements NO strategy",
          not builders and ".calls" not in psrc and ".puts" not in psrc
          and "strike" not in psrc.lower().replace("plan_tick", ""),
          ", ".join(sorted(builders)) or "clean")

    # ── W2 ────────────────────────────────────────────────────────────────
    for m in STRATEGIES:
        bad = _bare_returns(os.path.join(_root, "strategy", m + ".py"))
        check(f"W2 {m}: every entry return is a plan terminal",
              not bad, ", ".join(bad) or "wired")

    # ── the plan, executed ────────────────────────────────────────────────
    from strategy import plan as P
    st = _Store()
    P.bind_store(st)
    P.begin_tick(1000.0)
    os.environ["OT_RELAXED_ENTRY"] = "0"
    from strategy import criteria as C

    pl = P.Plan("TestStrat", ("credit", "width", "risk", "r", "geometry"))

    # W3 — real width
    t = pl.tick(100.0, "put")
    t.credit_spread(95.0, 92.5, 0.60)              # width 2.5, NOT 5.0
    check("W3 R uses the real width (2.5), not an assumed $5",
          abs(t.r - 0.60 / 1.90) < 1e-3 and abs(t.risk - 1.9) < 1e-9,
          f"r={t.r} risk={t.risk}")

    # W4 — strict refuses
    ok, why = t.executable()
    check("W4 STRICT: R 0.32 below the floor is refused", ok is False and "below" in why, why)
    t.refuse("r", why)
    row = st.conn.execute("SELECT verdict, reason, r_now FROM plan_tick "
                          "WHERE strategy='TestStrat'").fetchone()
    check("W4b the refusal is a DECLINE row carrying R", row and row[0] == "DECLINE"
          and row[2] is not None and "r:" in (row[1] or ""), str(row))

    # W5 — relaxed records, does not veto
    os.environ["OT_RELAXED_ENTRY"] = "1"
    os.environ["OT_PAPER_TRADING"] = "1"     # relaxed is refused on a live box
    if not C.relaxed_active():
        print("  SKIP  W5 relaxed cannot activate in this environment (is_live fails closed)")
    else:
        P.begin_tick(1001.0)
        t2 = pl.tick(100.0, "put")
        t2.credit_spread(95.0, 92.5, 0.60)
        ok2, why2 = t2.executable()
        check("W5 RELAXED: the same spread is executable", ok2 is True and "MUTED" in why2, why2)
        t2.take(object())
        row2 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                               "strategy='TestStrat' AND ts_epoch=1001.0").fetchone()
        chk = {r[0]: (r[1], r[2]) for r in st.conn.execute(
            "SELECT check_name, value, verdict FROM plan_check WHERE "
            "strategy='TestStrat' AND ts_epoch=1001.0")}
        check("W5b TAKE row says the hurdle was muted",
              row2 and row2[0] == "TAKE" and "MUTED" in (row2[1] or ""), str(row2))
        check("W5c the R VALUE is recorded and r_muted is queryable",
              chk.get("r", (None,))[0] is not None and chk.get("r_muted", (None, ""))[1] == "PASS",
              str({k: chk[k] for k in ("r", "r_muted") if k in chk}))
    os.environ["OT_RELAXED_ENTRY"] = "0"

    # W6 — geometry
    from analysis.session_map import classify, CEILING, FLOOR
    # ⚠️ RE-DERIVED AT r231, NOT PATCHED. `classify` now requires `spot`
    # because role must agree with PRICE as well as with the opening range
    # (operator, 2026-09-03). Every fixture below carries a spot chosen so the
    # case it was written for is still the case being tested — a fixture
    # updated to merely compile would silently start measuring something else,
    # which is the r155 trap.
    ok_a, _ = classify(349.0, CEILING, 351.88, 349.20, "upper tine", spot=350.0)
    ok_b, _ = classify(350.5, FLOOR, 351.88, 349.20, "session low", spot=352.0)
    ok_c, _ = classify(355.0, CEILING, 351.88, 349.20, "session high", spot=352.0)
    ok_d, _ = classify(355.0, CEILING, None, None, "session high", spot=352.0)
    ok_e, _ = classify(340.0, CEILING, 351.88, 349.20, "upper tine", spot=350.0)
    check("W6a a CEILING below the opening range is INVALID", ok_a is False)
    check("W6b a level INSIDE the opening range is INVALID", ok_b is False)
    check("W6c a CEILING above the range is valid", ok_c is True)
    check("W6d no opening range -> UNMEASURED (None), never a pass", ok_d is None)
    check("W6e a displaced upper tine is NOT re-cast as a floor", ok_e is False)
    # W6g — r231's own rule, pinned HERE too so the range tests above cannot
    # be read as covering it: this level clears every range test and is still
    # invalid because price has traversed it.
    ok_g, _ = classify(352.5, CEILING, 351.88, 349.20, "upper tine", spot=355.0)
    check("W6g a CEILING above the range but BELOW spot is INVALID",
          ok_g is False)
    P.begin_tick(1002.0)
    t3 = pl.tick(350.0, "call")
    g = t3.level(349.0, CEILING, "upper tine", 351.88, 349.20, 350.0)
    t3.refuse("geometry", t3.last_why)
    r3 = st.conn.execute("SELECT verdict FROM plan_check WHERE strategy='TestStrat' "
                         "AND ts_epoch=1002.0 AND check_name='geometry'").fetchone()
    check("W6f the geometry elimination is a queryable FAIL row",
          g is False and r3 and r3[0] == "FAIL", str(r3))

    # W7 — NULL not zero
    P.begin_tick(1003.0)
    t4 = pl.tick(None)
    t4.check("width", None, None)
    t4.starved("chain")
    r4 = st.conn.execute("SELECT value, verdict FROM plan_check WHERE "
                         "strategy='TestStrat' AND ts_epoch=1003.0 AND check_name='width'").fetchone()
    r4b = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                          "strategy='TestStrat' AND ts_epoch=1003.0").fetchone()
    check("W7 an unmeasured check is NULL / n/a", r4 == (None, "n/a"), str(r4))
    check("W7b a starved tick is a NO PLAN row NAMING the input",
          r4b and r4b[0] == "NO PLAN" and "chain" in (r4b[1] or ""), str(r4b))

    # W8 — the gate reporter bridge
    from analysis import gate_report as GR
    GR._reporter = GR.GateReporter(store=None, symbol="T")
    P.begin_tick(1004.0)
    pl.symbol = "T"
    t5 = pl.tick(100.0)
    t5.refuse("entry_window", "closed")
    snap = GR._reporter.snapshot()
    check("W8 refuse() reports the block edge-triggered",
          "TestStrat" in snap and snap["TestStrat"]["gate"] == "entry_window", str(snap))
    P.begin_tick(1005.0)
    pl.tick(100.0).take(object())
    check("W8b take() clears the block", "TestStrat" not in GR._reporter.snapshot())

    # ── the runaway end to end: starved without a chain, valid with one ──
    from strategy.runaway_continuation import RunawayContinuationStrategy

    class _ORB:
        state = "OPEN_LONG"
        # ⚠️ `target_50pct` — the field the REAL ORBData declares. This double
        # carried `tp50`, a name that exists on nothing, and the strategy
        # read the same ghost — so these checks were GREEN while the gate
        # they exercise refused every runaway on the fleet. A fixture must
        # match the real class, not the caller's assumption.
        orb_high, orb_low, target_50pct = 101.0, 100.0, 101.5
        invalidation_reason = "runaway"
        fifty_accepted, bars_since_break = True, 2      # OTV4TEST r3: the trigger

    class _C:
        def __init__(s, k, mark, delta, gamma=0.01):
            s.strike, s.mark, s.ask, s.bid = k, mark, mark + 0.02, mark - 0.02
            s.delta, s.gamma, s.theta = delta, gamma, -0.05
            s.expiry, s.option_type, s.symbol = "x", "call", f"C{k}"
            s.open_interest = 100

    class _Chain:
        calls = [_C(102.0, 0.90, 0.40, 0.03), _C(103.0, 0.45, 0.25), _C(104.0, 0.20, 0.12)]
        puts = []

    # OTV4TEST r25 — r24 made entry require the CLOSED 1m bar to hold the 50 NOW
    # (runaway_plan's `fifty_held_now`); live, main.py always passes ctx["df_1m"].
    # A call with no frame therefore HOLDs before it reaches the case under test,
    # so the fixture carries bars whose closes sit at this case's own price.
    import pandas as _pd

    def _bars_at(px):
        return _pd.DataFrame([{"open": px, "high": px, "low": px, "close": px}] * 5,
                             index=_pd.date_range("2026-09-08 10:10", periods=5, freq="1min",
                                                  tz="America/New_York"))

    rs = RunawayContinuationStrategy()
    P.begin_tick(1006.0)
    r0 = rs.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.6, now_et="10:15",
                            df_1m=_bars_at(101.6))
    row6 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                           "strategy='RunawayContinuation' AND ts_epoch=1006.0").fetchone()
    check("W9 runaway without a chain: NO PLAN row naming the chain",
          r0 is None and row6 and row6[0] == "NO PLAN" and "chain" in (row6[1] or ""), str(row6))
    P.begin_tick(1007.0)
    r1 = rs.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.6, now_et="10:15", chain=_Chain(),
                            df_1m=_bars_at(101.6))
    row7 = st.conn.execute("SELECT verdict, r_now, invalidation FROM plan_tick WHERE "
                           "strategy='RunawayContinuation' AND ts_epoch=1007.0").fetchone()
    # r168: the runaway has NO price invalidation — its floor is a 20% premium
    # loss — so the row carries R and a NULL invalidation.
    check("W9b runaway with a chain writes a row with R and NO price invalidation (r168)",
          row7 is not None and row7[1] is not None and row7[2] is None, str(row7))
    check("W9c the signal (if fired) is VALID — strike, premium, contract resolved",
          r1 is None or r1.is_valid,
          "strict refused on R" if r1 is None else f"strike={r1.strike} prem={r1.entry_premium}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_plan_wiring: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
