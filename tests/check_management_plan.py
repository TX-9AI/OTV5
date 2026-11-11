#!/usr/bin/env python3
"""
tests/check_management_plan.py  v5.5  (2026-11-11)
v5.5  2026-11-11  OTV5 r107 (RETIRE.5 follow-up) — D12c re-pointed (WA 38.4): the engine's butterfly exit is removed, so D12c pins it gone.
v5.4  2026-11-09  OTV5 r103 (RETIRE.5 step 2) — the GEX pin fly leaves the management plan: M5, D12 and D12a pin that a GEXPinButterfly record is no longer the plan's (decide -> None, no row); M7's ids drop bf1; M11 pins its EXIT_CONDITIONS row absent and Breakout's present. D12c (the engine's generic butterfly path) unchanged.
v5.3  2026-11-08  OTV5 r88 (RETIRE.3) — M4, M8, D8 and D9 (the TCS's narration, vector, hold and breach) go with the TCS; M7 drops its id and M11 pins it absent; D10's formed condor is two IronCondorStrategy legs (were TCS). Every other check unchanged.
v5.2  2026-11-08  OTV5 r76 (RETIRE.1) — RE-POINTED (WA 38.4): the sweep and the ATP fly are removed from the management plan, so M3, D5-D7 (the
      sweep vertical) and D12e (the ATP fly) go with them; M7's ids and M11's roster drop them (and M11 pins them absent);
      D10's formed condor is two TCS legs; D12b/D12d (sweep_credit_spread.is_spent, read only by the removed sweep plan)
      go with it. Every other check unchanged.
v5.1  2026-11-03  OTV5 r73 (BFLY.17) — M5 and D12a: the GEX pin fly names the flatten as its only exit and HOLDS below its old floor (the operator, 2026-11-03: "For the GEX
      fly, I want no stop except hold to close"); the ATP butterfly, which keeps its stop, still CLOSEs at it (D12e).
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ... Previous title: tests/check_management_plan.py  v1.5  (2026-10-03)
v1.5  OTV4TEST r209 (EXIT.4): M1, M2b, M3, M4 read `touch < 101.00 -> out (breach)` - the narration names the
      structure stop a TOUCH (it reads the forming bar and always has; the operator kept it, 2026-10-03).
      Only the four expected strings moved.
v1.4  OTV4TEST r25: D12b RE-DERIVED FROM A SOURCE PIN TO THE RULE, AND IT FOUND A HOLE.
      It pinned trade_logger's spent-marking hook (`_is_cv`, the underlying_stop
      read) — deleted by r24, so D12b was RED SINCE r24 AND SHIPPED THAT WAY (not in
      r24's gate list) — and the pre-fork rule that ANY losing exit spends a level,
      which the fork's r5 ruling replaced with acceptance only. It now DRIVES this
      file's own plan: a TCS whose 1m close goes through its bound is closed by
      `MP.decide` under the plan's `breach:` label, that exit is written as a real
      row in a temp trades.db, and `is_spent` must read the level SPENT, keyed on
      the bound (D12b); the same TCS stopped out on premium must NOT spend it
      (D12d). D12b was red against r24's lock, which read only exit_engine's labels.
v1.3  r169: the butterfly rides to the 15:45 flatten or the 25% floor — D12
      re-pinned (above the old target -> HOLD), D12a the floor, D12c the
      engine acts on neither target nor max hold; M5 re-pinned.
v1.2  r168: the runaway's record carries no underlying stop and a 20% floor;
      D1 is the 20% floor; D2 is the pullback THROUGH the ORB boundary that
      must HOLD; D2b/D16 pin the split between ORB's structure stop and the
      runaway's premium floor.
v1.1  r167: D1-D15 — the plan DECIDES: spec conditions first (hard stop,
      structure/breach/acceptance, target, nickel, the 15% floor), the
      engine's calculators second (trail, theta bleed) adopted as the plan's
      own; a formed condor, ORB, ADOPTED and tents are not the plan's; BOS is
      gone; position_manager asks the plan first; ORB's path untouched.
v1.0  (2026-08-27, r166)

THE MANAGEMENT PLAN WATCHES; THE EXIT ENGINE EXECUTES.

Born red at 1b83ee0 (r165): strategy/management.py does not exist.

  M1  a runaway long, premium up 30%, trail not yet armed -> the row names
      the hard stop, the structure stop and the target with the record's
      OWN numbers, says the trail is not armed, carries MFE.
  M2  the same trade after the trail arms -> "premium <= trail -> out".
  M3  (r76: removed with the sweep) a sweep credit spread -> credit semantics: pnl positive when the
      spread's value FALLS; the premium stop reads ">=".
  M4  (r88: removed with the TCS) TCS -> breach of the ORB bound, no premium stop, nickel.
  M5  a butterfly -> stop and target, from the record.
  M6  an ADOPTED record -> no row (no declared conditions, no spec).
  M7  the r66 vector is written for the open position with outcome "manage"
      and the trade_id attached, once per record per tick.
  M8  (r88: removed with the TCS) the TCS vector (vote, ADX, ORB width over EM).
  M9  every reading the plan writes comes from the record — the plan holds
      no threshold of its own (AST: no numeric literal compared to a premium).
  M10 main_loop calls the management plan AFTER manage_open_position and
      inside a try — narration can never reach an exit.
"""
import ast
import json
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
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


def _row(st, strat, ts):
    return st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy=? "
                           "AND ts_epoch=?", (strat, ts)).fetchone()


def main():
    from strategy import plan as P
    from strategy.management import ManagementPlan, EXIT_CONDITIONS
    from derived.notes import NoteWriter
    st = _Store()
    P.bind_store(st)

    class _Notes:                       # what ctx["derived_engines"] holds
        name = "notes"
        writer = NoteWriter(st, "TST")

    class _Trend:
        overall_direction, primary_adx = "BULLISH", 27.0

    ctx = {"price": 101.9, "derived_engines": [_Notes()], "trend": _Trend(),
           "orb_high": 101.0, "orb_low": 100.0, "expected_move": 2.0}
    MP = ManagementPlan()

    run = {"trade_id": "rw1", "strategy": "RunawayContinuation", "option_side": "call",
           "direction": "long", "entry_premium": 1.00, "current_premium": 1.30,
           "stop_premium": 0.75, "target_premium": 2.00, "underlying_stop": 101.0,
           "trail_stop": None, "mfe_premium": 1.34, "mae_premium": 0.96, "excursion_ticks": 12}
    # r167: covered records are written by decide(); tick() narrates the rest.
    P.begin_tick(1.0)
    it = MP.decide(run, 1.30, df_1m=None, current_price=101.9, ctx=ctx, exit_engine=None)
    r1 = _row(st, "RunawayContinuation/manage", 1.0)
    check("M1 runaway +30%, no condition fired -> HOLD naming the floor, the breach and the target from the record",
          it and it.action == "HOLD" and r1 and r1[0] == "HOLD"
          and "premium <= 0.75 -> out (floor)" in r1[1] and "touch < 101.00 -> out (breach)" in r1[1]
          and "premium >= 2.00 -> out (target)" in r1[1] and "(+30%)" in r1[1], str(r1))
    run["trail_stop"] = 1.12
    P.begin_tick(2.0)
    MP.decide(run, 1.30, df_1m=None, current_price=102.4, ctx=ctx, exit_engine=None)
    r2 = _row(st, "RunawayContinuation/manage", 2.0)
    check("M2 trail on the record -> 'premium <= 1.12 -> out (trail)'",
          r2 and "premium <= 1.12 -> out (trail)" in r2[1], str(r2))

    short_run = dict(run, trade_id="rw2", option_side="put", direction="short",
                     underlying_stop=100.0, trail_stop=None)
    P.begin_tick(2.5)
    MP.decide(short_run, 1.30, df_1m=None, current_price=99.1, ctx=ctx, exit_engine=None)
    r2b = _row(st, "RunawayContinuation/manage", 2.5)
    check("M2b a SHORT runaway is hurt by a close ABOVE its stop — the row reads '>'",
          r2b and "touch > 100.00 -> out (breach)" in r2b[1], str(r2b))
    # r88 (RETIRE.3): M4 (the TCS's breach-and-nickel narration) goes with the TCS.

    fly = {"trade_id": "bf1", "strategy": "GEXPinButterfly", "option_side": "call",
           "is_butterfly": True, "entry_premium": 0.18, "current_premium": 0.22,
           "stop_premium": 0.135, "target_premium": 0.60, "excursion_ticks": 20}
    P.begin_tick(5.0)
    MP.decide(fly, 0.22, df_1m=None, current_price=100.6, ctx=ctx, exit_engine=None)
    r5 = _row(st, "GEXPinButterfly/manage", 5.0)
    check("M5 (r103) a GEXPinButterfly record is no longer the plan's: no management row is written",
          not r5, str(r5))

    P.begin_tick(6.0)
    n6 = MP.tick(ctx, [{"trade_id": "ad1", "strategy": "ADOPTED", "entry_premium": 1.0}], 100.0)
    check("M6 an ADOPTED record gets no row", n6 == 0)

    notes = st.conn.execute("SELECT strategy, outcome, trade_id, payload FROM strategy_note "
                            "WHERE outcome='manage' ORDER BY rowid").fetchall()
    check("M7 the r66 vector is written per open position with outcome 'manage' and the trade_id",
          len(notes) >= 3 and all(n[1] == "manage" for n in notes)
          and {n[2] for n in notes} >= {"rw1", "rw2"} and "bf1" not in {n[2] for n in notes},   # r88: tc1 removed; r103: bf1 (the fly) removed
          f"{len(notes)} notes, ids {sorted({n[2] for n in notes})}")
    # r88 (RETIRE.3): M8 (the TCS vector) goes with the TCS.

    # M9 — the plan holds no threshold of its own
    src = open(os.path.join(_root, "strategy", "management.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            # a structural COUNT (len(legs) >= 2) is not a premium threshold
            if isinstance(n.left, ast.Call) and getattr(n.left.func, "id", "") == "len":
                continue
            for c in n.comparators:
                if isinstance(c, ast.Constant) and isinstance(c.value, (int, float)) and c.value not in (0, 1):
                    bad.append(f"line {n.lineno}: compares to {c.value}")
    check("M9 the management plan compares premiums to the RECORD's fields, never to a literal of its own",
          not bad, "; ".join(bad) or "clean")

    # M10 — wired after manage_open_position, inside a try
    msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    ml = next(n for n in ast.walk(ast.parse(msrc)) if isinstance(n, ast.FunctionDef) and n.name == "main_loop")
    body = ast.unparse(ml)
    i_m = body.find("pos_mgr.manage_open_position(chain=ctx.get('chain')")
    i_p = body.find("get_management_plan().tick(")
    in_try = any(isinstance(n, ast.Try) and "get_management_plan" in ast.unparse(n) for n in ast.walk(ml))
    check("M10 main_loop runs the management plan AFTER manage_open_position, inside a try",
          i_m != -1 and i_p != -1 and i_m < i_p and in_try, f"manage@{i_m} plan@{i_p} try={in_try}")

    check("M11 every strategy that opens a position declares its exit conditions",
          {"RunawayContinuation", "IronCondorStrategy", "Breakout"}
          <= set(EXIT_CONDITIONS)
          and not ({"ORBStrategy", "SweepCreditSpread", "ATPButterfly", "TrendCreditSpread",   # r88: + the TCS
                    "GEXPinButterfly"}                                                         # r103: + the GEX fly
                   & set(EXIT_CONDITIONS)))

    # ══ r167 — THE PLAN DECIDES ═══════════════════════════════════════════
    import pandas as pd
    from execution.exit_engine import ExitDecision
    from strategy.management import covers

    class _Engine:
        """A stand-in for the calculator: returns what it is told to."""
        def __init__(self, decision=None): self.d, self.calls = decision, 0
        def evaluate(self, record, prem, **kw):
            self.calls += 1
            return self.d if self.d is not None else ExitDecision()

    def _df(closes, t0=3_000_000):
        idx = pd.to_datetime([t0 + 60 * i for i in range(len(closes))], unit="s", utc=True)
        return pd.DataFrame({"open": closes, "high": [c + 0.2 for c in closes],
                             "low": [c - 0.2 for c in closes], "close": closes}, index=idx)

    # r168 — the runaway's record: a 20% floor (0.80 on a 1.00 entry) and NO
    # underlying_stop. The ORB boundary is not its stop.
    rw = {"trade_id": "d1", "strategy": "RunawayContinuation", "option_side": "call",
          "direction": "long", "entry_premium": 1.00, "current_premium": 1.30,
          "stop_premium": 0.80, "target_premium": 2.00, "underlying_stop": 0.0,
          "trail_stop": None, "excursion_ticks": 5}
    eng = _Engine()
    P.begin_tick(10.0)
    it = MP.decide(dict(rw, current_premium=0.79), 0.79, df_1m=_df([101.5, 101.6]), exit_engine=eng)
    rd1 = _row(st, "RunawayContinuation/manage", 10.0)
    check("D1 runaway premium 0.79 <= the 20% floor 0.80 -> CLOSE hard_stop_20%, the calculator NOT consulted",
          it and it.action == "CLOSE" and it.condition == "hard_stop" and "20%" in it.reason
          and eng.calls == 0 and rd1 and rd1[0] == "CLOSE" and "CUT" in rd1[1], f"{it and it.reason} {rd1}")
    P.begin_tick(11.0)
    it = MP.decide(rw, 1.05, df_1m=_df([101.5, 100.8]), exit_engine=eng)
    rd2 = _row(st, "RunawayContinuation/manage", 11.0)
    check("D2 (r168) a pullback: 1m close 100.80 BACK THROUGH the ORB boundary 101.00 with the premium "
          "still above the floor -> HOLD. Room to breathe; the boundary is not a stop.",
          it and it.action == "HOLD" and rd2 and rd2[0] == "HOLD" and "breach" not in rd2[1],
          f"{it and it.action} {rd2}")
    orb_rec = {"trade_id": "d2o", "strategy": "ORBStrategy", "option_side": "call",
               "direction": "long", "entry_premium": 1.00, "current_premium": 1.10,
               "stop_premium": 0.75, "underlying_stop": 100.62}
    check("D2b ORB keeps its impulsive-origin structure stop — but through ITS OWN path, "
          "never this plan's",
          not covers(orb_rec))
    tr = ExitDecision(); tr.new_trail_stop = 1.12
    eng = _Engine(tr)
    P.begin_tick(12.0)
    it = MP.decide(rw, 1.55, df_1m=_df([101.5, 102.4]), exit_engine=eng)
    rd3 = _row(st, "RunawayContinuation/manage", 12.0)
    check("D3 no spec condition fired -> the engine's trail (armed at 50%) is adopted: TRAIL 1.12, row says so",
          it and it.action == "TRAIL" and it.trail == 1.12 and eng.calls == 1
          and rd3 and rd3[0] == "TRAIL" and "premium <= 1.12 -> out (trail)" in rd3[1], str(rd3))
    th = ExitDecision(); th.should_exit, th.exit_reason = True, "theta_bleed pnl=12.0%"
    eng = _Engine(th)
    P.begin_tick(13.0)
    it = MP.decide(rw, 1.12, df_1m=_df([101.5, 102.0]), exit_engine=eng)
    check("D4 the calculator says theta_bleed -> CLOSE theta_bleed (the 'other variables' stay)",
          it and it.action == "CLOSE" and it.condition == "theta_bleed", str(it and it.reason))
    d = it.to_exit_decision()
    check("D4b the intent converts to the engine's ExitDecision the executor already understands",
          d.should_exit and d.exit_reason.startswith("theta_bleed"))

    eng = _Engine()                                  # a fresh calculator (r76: the sweep block that reset it is removed)
    # r88 (RETIRE.3): D8 / D9 (the TCS holds through +38% and closes on its breach) go with the TCS; D10's formed
    # condor is two IronCondorStrategy credit legs (were TCS legs).
    tc = {"trade_id": "d8", "strategy": "IronCondorStrategy", "option_side": "put",
          "is_credit_vertical": True, "is_condor_leg": True,
          "entry_premium": 1.30, "current_premium": 1.80, "underlying_stop": 351.88}
    leg2 = dict(tc, trade_id="d10b", option_side="call")
    P.begin_tick(19.0)
    it = MP.decide(tc, 1.20, df_1m=_df([352.6, 352.7]), open_records=[tc, leg2], exit_engine=eng)
    check("D10 a FORMED condor (two legs) is not the plan's to decide -> None (the ladder decides)",
          it is None and not covers(tc, [tc, leg2]))
    check("D11 ORB, ADOPTED and a tent are never the plan's",
          not covers({"strategy": "ORBStrategy"}) and not covers({"strategy": "ADOPTED"})
          and not covers({"strategy": "SweepCreditSpread", "is_tent": True}))
    bf = {"trade_id": "d12", "strategy": "GEXPinButterfly", "option_side": "call",
          "is_butterfly": True, "entry_premium": 0.18, "current_premium": 0.62,
          "stop_premium": 0.135, "target_premium": 0.60}
    P.begin_tick(20.0)
    it = MP.decide(bf, 0.62, df_1m=_df([100.9, 101.0]), exit_engine=eng)
    rd12 = _row(st, "GEXPinButterfly/manage", 20.0)
    check("D12 (r103) a GEXPinButterfly record above its old target is not the plan's: decide -> None, no row",
          it is None and not rd12, f"{it and it.action} {rd12}")
    P.begin_tick(20.5)
    it = MP.decide(dict(bf, current_premium=0.13), 0.13, df_1m=_df([100.9, 101.0]), exit_engine=eng)
    check("D12a (r103) ...and below its old floor: still None (the fly's hold-to-close row is removed)",
          it is None, str(it and (it.action, it.reason)))
    _xsrc = open(os.path.join(_root, "execution", "exit_engine.py"), encoding="utf-8").read()
    check("D12c (r107) the engine has no butterfly path at all (the generic fly exit is removed)",
          "def _evaluate_butterfly(" not in _xsrc and "def _close_butterfly(" not in _xsrc)
    # D12b/D12d (OTV4TEST r25) — the plan's OWN breach close must spend the level it
    # sold against, read back from trades.db the way the TCS/sweep plans read it.
    # r76: D12b/D12d read the sweep module's is_spent, whose only consumer (the sweep plan) is removed with the sweep.
    esrc = open(os.path.join(_root, "execution", "exit_engine.py"), encoding="utf-8").read()
    ecode = "\n".join(l for l in esrc.split("\n") if not l.strip().startswith("#"))
    check("D13 BOS is retired from the exit engine's decision path",
          'exit_reason = f"bos_exit' not in ecode and "tracker.update(df_1m)" not in ecode)
    pmsrc = open(os.path.join(_root, "execution", "position_manager.py"), encoding="utf-8").read()
    pm = next(n for n in ast.walk(ast.parse(pmsrc)) if isinstance(n, ast.FunctionDef)
              and n.name == "_manage_one")          # the per-record body
    pmb = ast.unparse(pm)
    i_dec = pmb.find("get_management_plan().decide(")
    i_ev = pmb.find("exit_eng.evaluate(record, current_premium")
    check("D14 position_manager asks the plan FIRST and falls back to evaluate() only when it returns None",
          i_dec != -1 and i_ev != -1 and i_dec < i_ev and "if decision is None:" in pmb,
          f"decide@{i_dec} evaluate@{i_ev}")
    ob = next(n for n in ast.walk(ast.parse(esrc)) if isinstance(n, ast.FunctionDef) and n.name == "_evaluate_orb")
    obs = ast.unparse(ob)
    check("D15 ORB's own exit path is untouched — the 50% trail, the post-target tightening, the "
          "impulsive-origin structure stop",
          "post_target_trail" in obs and "orb_structure_stop" in obs
          and ("TRAIL_ACTIVATION" in obs or "trail_activation" in obs))
    rsrc = open(os.path.join(_root, "strategy", "runaway_continuation.py"), encoding="utf-8").read()
    rcode = "\n".join(l for l in rsrc.split("\n") if not l.strip().startswith("#"))
    check("D16 (r168) the runaway's signal sets NO underlying_stop and stop_loss_pct=RUNAWAY_MAX_LOSS_PCT",
          "underlying_stop=prep.boundary" not in rcode and "stop_loss_pct=self.MAX_LOSS_PCT" in rcode
          and "RUNAWAY_MAX_LOSS_PCT" in rsrc)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_management_plan: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
