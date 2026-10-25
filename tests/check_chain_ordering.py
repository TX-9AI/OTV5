#!/usr/bin/env python3
"""check_chain_ordering.py — v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.4  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject SweepCreditSpread (C9/C10) is DORMANT by default and a dormant plan now writes
      nothing by ruling, so this run switches it ACTIVE (OT_SWEEP_CS=1); what it pins is unchanged.
v1.3  2026-10-03  OTV4TEST r196 (AUD.5) — C13/C14: THE VOLATILITY MEASURES REACH THE ENGINES. They were
      computed after run_all, so character_axis_sample's realised vols, vol_ratio and close_capture were
      NULL on 3,580 of 3,580 rows. C13 pins the order in run_analysis; C14 drives the real port into the
      real CharacterEngine on a scratch store and reads the row it writes.
v1.2  2026-09-18  OTV4TEST r41 — C7 re-pointed: the board's verdict for an
      unasked strategy is now INACTIVE (operator's status ruling), and C7 asserted
      the literal string. The RULE it guards — no strategy vanishes from plan_tick
      — is unchanged, so the assertion moved to the row's existence and a closed
      set of not-working verdicts rather than one spelling.
v1.1  2026-08-26  r146: C7-C11 re-pinned against the plan BOARD (derived/plans
      v2.0) after the seven builders were deleted. The property survives —
      no strategy may vanish from plan_tick — the mechanism is now NOT ASKED
      rows with the dispatcher's reason, plus the asked-and-silent canary.

🔴 THE 2026-08-26 SILENT FAILURE. The chain and GEX were fetched ~20 lines
BELOW `run_analysis()`, but the derived engines run INSIDE it. So every plan
builder hit its `chain is None` guard, `plans` came back empty on every tick,
`_write_tick` was never reached — and `plan_tick`/`plan_check` were never
CREATED. A full session produced nothing and looked, from outside, exactly like
an engine that was never registered.

⚠️ TWO INDEPENDENT DEFECTS, TWO INDEPENDENT PINS:
  C1-C4  the ORDERING — chain is fetched before run_analysis, published on ctx
         before the engines run, and NOT fetched twice.
  C5-C6  the VISIBILITY — tables are created at engine init, so an empty table
         says "ran, found nothing" instead of leaving a missing-table mystery.
"""
import ast
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ["OT_SWEEP_CS"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()

    # ── C1: the fetch happens BEFORE the run_analysis call ────────────────
    # ⚠️ MATCH CODE, NOT PROSE. The comments here TALK about the old ordering,
    # so a raw substring search would find "fetch_chain" in an explanation and
    # pass while the code was still wrong. Strip comments via AST first — the
    # rule that has now fired four times on this codebase.
    tree = ast.parse(src)
    # ⚠️ SEARCH THE WHOLE MODULE. My first version sliced from `def main(` —
    # but this bot's tick loop is not inside a function of that name, so both
    # positions came back -1 and the check "passed by absence". A pin that
    # cannot find the code it is pinning is not a pin.
    # ⚠️ AND SCOPE TO THE TICK LOOP. Module-wide, `run_analysis(state` also
    # matches its own DEFINITION (which sits earlier in the file than the call
    # site), and `fetch_chain()` has other legitimate callers. Both made the
    # check measure the wrong thing. The claim is about ORDER WITHIN ONE TICK,
    # so the scope must be the function that runs the tick.
    _loop = next((n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                  # ⚠️ LOCATE BY A MARKER THE MUTATION CANNOT MOVE. Keying on
                  # "run_analysis(state, chain=" meant that reverting the fix
                  # made the tick loop UNFINDABLE, so the pin failed with
                  # "could not locate" instead of naming the real regression.
                  # A check should fail for the reason it exists.
                  and "run_analysis(state" in ast.unparse(n)
                  and "POLL_INTERVAL_SECONDS" in ast.unparse(n)), None)
    if _loop is None:
        print("  FAIL  could not locate the tick loop in main.py")
        return 1
    stripped = "\n".join(
        l for l in ast.unparse(_loop).split("\n")
        if not l.strip().startswith("#"))
    i_fetch = stripped.find("fetch_chain()")
    i_run = stripped.find("run_analysis(state, chain=")
    check("C1 the chain is fetched BEFORE run_analysis is called",
          i_fetch != -1 and i_run != -1 and i_fetch < i_run,
          f"fetch@{i_fetch} run@{i_run}")

    # ── C2: run_analysis ACCEPTS it ───────────────────────────────────────
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "run_analysis"),
              None)
    check("C2 run_analysis takes the chain as a parameter",
          fn is not None and any(a.arg == "chain" for a in fn.args.args),
          ", ".join(a.arg for a in fn.args.args) if fn else "not found")

    # ── C3: ctx["chain"] is set BEFORE run_all inside run_analysis ────────
    body = ast.unparse(fn) if fn else ""
    body_nc = "\n".join(l for l in body.split("\n")
                        if not l.strip().startswith("#"))
    i_set = body_nc.find("ctx['chain'] = chain")
    i_all = body_nc.find("run_all(")
    check("C3 ctx['chain'] is published BEFORE run_all inside run_analysis",
          i_set != -1 and i_all != -1 and i_set < i_all,
          f"set@{i_set} run_all@{i_all}")

    # ── C4: exactly ONE fetch per tick ────────────────────────────────────
    # ⚠️ A second fetch would double the market-data calls AND could disagree
    # with the chain the derived engines just recorded from.
    check("C4 fetch_chain() is called exactly once per tick (no re-fetch)",
          stripped.count("fetch_chain()") == 1,
          f"{stripped.count('fetch_chain()')} call site(s)")

    # ── C5/C6: the tables exist even when NOTHING is produced ─────────────
    from derived.plans import PlanEngine

    class _Store:
        def __init__(self):
            self.conn = sqlite3.connect(":memory:")
        def commit(self):
            self.conn.commit()

    st = _Store()
    PlanEngine(store=st, symbol="TEST", ledger=None)      # construct only
    names = {r[0] for r in st.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    check("C5 plan_tick exists after INIT, with no plan ever produced",
          "plan_tick" in names, ", ".join(sorted(names)) or "none")
    check("C6 plan_check exists after INIT too",
          "plan_check" in names)

    # ── C7-C11 (r146) — THE BOARD, not the builders ───────────────────────
    # v1.0's C7-C11 exercised the seven plan builders deleted in r146. What
    # survives is the property they were protecting: NO STRATEGY MAY VANISH
    # FROM plan_tick. The board now writes a NOT ASKED row for every
    # registered strategy the dispatch never called, carrying the
    # dispatcher's reason.
    from strategy import plan as _plan
    from strategy.runaway_continuation import RunawayContinuationStrategy
    from strategy.sweep_credit_spread import SweepCreditSpreadStrategy
    RunawayContinuationStrategy(); SweepCreditSpreadStrategy()   # register
    st3 = _Store()
    e3 = PlanEngine(store=st3, symbol="T3", ledger=None)
    e3.derive({"price": 201.4})                    # tick 1 opens
    _plan.skipped("RunawayContinuation", "ORB has not run away")
    e3.derive({"price": 201.5})                    # tick 2 closes tick 1
    rows = {r[0]: (r[1], r[2]) for r in st3.conn.execute(
        "SELECT strategy, verdict, reason FROM plan_tick")}
    # ⚠️ r41 — THE VERDICT IS `INACTIVE` NOW, AND C7 IS RE-POINTED AT ITS
    # INTENT RATHER THAN LOOSENED. What this check exists to prove is that NO
    # STRATEGY VANISHES FROM plan_tick — r146's rule. The verdict STRING was
    # incidental to that and changed on the operator's ruling of 2026-09-18
    # ("each plan should have a current status as either working or inactive"),
    # so C7 now asserts the row EXISTS and carries a NOT-WORKING status. It is
    # still a closed set: an empty or unexpected verdict fails.
    check("C7 a strategy the dispatch never asked still gets a row",
          "RunawayContinuation" in rows
          and rows["RunawayContinuation"][0] in ("INACTIVE", "NO PLAN"),
          str(rows.get("RunawayContinuation")))
    check("C8 the INACTIVE row carries the dispatcher's reason",
          "ORB has not run away" in (rows.get("RunawayContinuation", ("", ""))[1] or ""))
    check("C9 a strategy with no stated reason still gets a row saying so",
          "SweepCreditSpread" in rows and "no reason" in (rows["SweepCreditSpread"][1] or ""),
          str(rows.get("SweepCreditSpread")))
    # ⚠️ AND A STRATEGY THAT WAS ASKED BUT WROTE NOTHING IS FLAGGED — that
    # is the canary for an unwired `return None`.
    _plan.asked("SweepCreditSpread", None)
    e3.derive({"price": 201.6})
    r3 = st3.conn.execute(
        "SELECT verdict, reason FROM plan_tick WHERE strategy='SweepCreditSpread' "
        "ORDER BY ts_epoch DESC LIMIT 1").fetchone()
    check("C10 asked-and-silent writes a NO PLAN row naming the unwired return",
          r3 is not None and r3[0] == "NO PLAN" and "wrote no plan row" in (r3[1] or ""),
          str(r3))
    # ⚠️ NULL, never 0.0 — an unmeasured check stays n/a (VW.1, pinned).
    t = RunawayContinuationStrategy.__new__(RunawayContinuationStrategy)
    _pt = _plan.REGISTRY["RunawayContinuation"].tick(100.0)
    _pt.check("atr_pct", None, None)
    _pt.refuse("atr_pct", "unmeasured")
    rc = st3.conn.execute(
        "SELECT value, verdict FROM plan_check WHERE strategy='RunawayContinuation' "
        "AND check_name='atr_pct' ORDER BY ts_epoch DESC LIMIT 1").fetchone()
    check("C11 an unmeasured check is NULL / FAIL-by-refusal, never 0.0/PASS",
          rc is not None and rc[0] is None, str(rc))

    # ⚠️ AND condor_triggers MUST REACH THE ENGINES — the second input with
    # exactly the chain's defect: published mid-dispatch, after run_analysis.
    _msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    _ra = next((n for n in ast.walk(ast.parse(_msrc))
                if isinstance(n, ast.FunctionDef) and n.name == "run_analysis"),
               None)
    _rb = "\n".join(l for l in ast.unparse(_ra).split("\n")
                    if not l.strip().startswith("#")) if _ra else ""
    i_ctm = _rb.find("ctx['condor_triggers']")
    i_ra = _rb.find("run_all(")
    check("C12 condor_triggers is published BEFORE run_all",
          i_ctm != -1 and i_ra != -1 and i_ctm < i_ra,
          f"set@{i_ctm} run_all@{i_ra}")

    # 🔴 r196 (AUD.5) — AND THE VOLATILITY MEASURES: THE THIRD INPUT WITH THE CHAIN'S
    # DEFECT. They were computed in _apply_derived_ports, AFTER run_all, so the
    # character engine sampled realised_vol_cc / parkinson as None on every row.
    i_vol = _rb.find("_apply_vol_ports(ctx)")
    check("C13 the volatility measures are put on ctx BEFORE run_all",
          i_vol != -1 and i_ra != -1 and i_vol < i_ra, f"vol@{i_vol} run_all@{i_ra}")

    # C14 — DRIVEN: the REAL vol port feeds the REAL character engine a sample it
    # can store. Synthetic 5m bars with real movement; a scratch store.
    try:
        import glob as _g
        for _sp in _g.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
            if _sp not in sys.path:
                sys.path.insert(1, _sp)                       # r106 venv bootstrap
        import tempfile as _tf
        _d = _tf.mkdtemp(prefix="check_chain_ordering_")
        for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
            os.environ.setdefault(_k, os.path.join(_d, _f))
        os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_d, "sj"))
        os.environ.setdefault("OT_LOG_FILE", os.path.join(_d, "bot.log"))
        os.environ.setdefault("OT_INSTRUMENT", "QQQ")
        import pandas as pd
        import main as _main
        from derived.character_engine import CharacterEngine

        class _St:
            def __init__(self, path):
                self.conn = sqlite3.connect(path)

            def commit(self):
                self.conn.commit()
        px = [100.0 + 0.4 * ((i * 7) % 5) + 0.05 * i for i in range(60)]
        df = pd.DataFrame({"open": px, "high": [p + 0.3 for p in px], "low": [p - 0.3 for p in px],
                           "close": [p + 0.1 for p in px], "volume": [1000] * 60})
        port = getattr(_main, "_apply_vol_ports", None)

        def sample(with_port):
            st = _St(os.path.join(_d, "axis_%d.db" % int(with_port)))
            ctx = {"df_5m": df, "price": px[-1], "atm_iv": None,
                   "realised_vol_cc": None, "realised_vol_parkinson": None}
            if with_port and port is not None:
                port(ctx)
            CharacterEngine(store=st, symbol="QQQ").derive(ctx)
            return st.conn.execute("SELECT efficiency, realised_vol_cc, realised_vol_parkinson, close_capture"
                                   " FROM character_axis_sample").fetchone()
        got, old = sample(True), sample(False)
        check("C14 DRIVEN: after the vol port the character engine stores realised vol and close_capture",
              port is not None and got is not None and got[1] is not None and got[2] is not None
              and got[3] is not None and old is not None and old[1] is None,
              f"port={'present' if port else 'ABSENT'} with={got} without={old}")
    except Exception as exc:                                    # noqa: BLE001
        check("C14 (did not run)", False, f"{type(exc).__name__}: {exc}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_chain_ordering: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
