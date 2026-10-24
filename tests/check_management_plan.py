#!/usr/bin/env python3
"""
tests/check_management_plan.py  v1.5  (2026-10-03)
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
  M3  a sweep credit spread -> credit semantics: pnl positive when the
      spread's value FALLS; the premium stop reads ">=".
  M4  TCS -> breach of the ORB bound, no premium stop, nickel.
  M5  a butterfly -> stop and target, from the record.
  M6  an ADOPTED record -> no row (no declared conditions, no spec).
  M7  the r66 vector is written for the open position with outcome "manage"
      and the trade_id attached, once per record per tick.
  M8  the TCS vector exists now (vote, ADX, ORB width over EM).
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
    sweep = {"trade_id": "sw1", "strategy": "SweepCreditSpread", "option_side": "put",
             "is_credit_vertical": True, "entry_premium": 1.30, "current_premium": 0.90,
             "stop_premium": 1.495, "underlying_stop": 96.0, "excursion_ticks": 8}
    P.begin_tick(3.0)
    MP.decide(sweep, 0.90, df_1m=None, open_records=[sweep], current_price=97.4, ctx=ctx, exit_engine=None)
    r3 = _row(st, "SweepCreditSpread/manage", 3.0)
    check("M3 a credit spread: value fell 1.30 -> 0.90 reads as +31%, the floor reads '>='",
          r3 and "credit" in r3[1] and "(+31%)" in r3[1] and "premium >= 1.50 -> out (floor)" in r3[1]
          and "touch < 96.00 -> out (breach)" in r3[1], str(r3))

    tcs = {"trade_id": "tc1", "strategy": "TrendCreditSpread", "option_side": "put",
           "is_credit_vertical": True, "is_trend_credit": True, "entry_premium": 1.30,
           "current_premium": 1.10, "underlying_stop": 351.88, "excursion_ticks": 3}
    P.begin_tick(4.0)
    MP.decide(tcs, 1.10, df_1m=None, open_records=[tcs], current_price=353.2, ctx=ctx, exit_engine=None)
    r4 = _row(st, "TrendCreditSpread/manage", 4.0)
    check("M4 TCS -> breach of the bound and the nickel; no premium floor named",
          r4 and "touch < 351.88 -> out (breach)" in r4[1] and "nickel" in r4[1]
          and "(floor)" not in r4[1], str(r4))

    fly = {"trade_id": "bf1", "strategy": "GEXPinButterfly", "option_side": "call",
           "is_butterfly": True, "entry_premium": 0.18, "current_premium": 0.22,
           "stop_premium": 0.135, "target_premium": 0.60, "excursion_ticks": 20}
    P.begin_tick(5.0)
    MP.decide(fly, 0.22, df_1m=None, current_price=100.6, ctx=ctx, exit_engine=None)
    r5 = _row(st, "GEXPinButterfly/manage", 5.0)
    check("M5 butterfly -> the floor and the 15:45 flatten, no target (r169)",
          r5 and "premium <= 0.14 -> out (floor)" in r5[1] and "15:45 -> flatten" in r5[1]
          and "target" not in r5[1], str(r5))

    P.begin_tick(6.0)
    n6 = MP.tick(ctx, [{"trade_id": "ad1", "strategy": "ADOPTED", "entry_premium": 1.0}], 100.0)
    check("M6 an ADOPTED record gets no row", n6 == 0)

    notes = st.conn.execute("SELECT strategy, outcome, trade_id, payload FROM strategy_note "
                            "WHERE outcome='manage' ORDER BY rowid").fetchall()
    check("M7 the r66 vector is written per open position with outcome 'manage' and the trade_id",
          len(notes) >= 5 and all(n[1] == "manage" for n in notes)
          and {n[2] for n in notes} >= {"rw1", "sw1", "tc1", "bf1"},
          f"{len(notes)} notes, ids {sorted({n[2] for n in notes})}")
    tcs_note = next((json.loads(n[3]) for n in notes if n[0] == "TrendCreditSpread"), None)
    spec = (tcs_note or {}).get("specific", {})
    check("M8 the TCS vector exists now — vote, ADX, ORB width over EM",
          spec.get("trend_dir") == "BULLISH" and spec.get("adx") == 27.0
          and abs((spec.get("orb_width_over_em") or 0) - 0.5) < 1e-9, str(spec))

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
          {"RunawayContinuation", "ORBStrategy", "SweepCreditSpread", "TrendCreditSpread",
           "IronCondorStrategy", "GEXPinButterfly"} <= set(EXIT_CONDITIONS))

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

    sw = {"trade_id": "d5", "strategy": "SweepCreditSpread", "option_side": "put",
          "is_credit_vertical": True, "is_condor_leg": True, "entry_premium": 1.30,
          "current_premium": 1.52, "stop_premium": 1.495, "underlying_stop": 96.0}
    eng = _Engine()
    P.begin_tick(14.0)
    it = MP.decide(sw, 1.52, df_1m=_df([96.6, 96.4]), open_records=[sw], exit_engine=eng)
    check("D5 a lone sweep vertical at 1.52 >= the 15% floor 1.495 -> CLOSE premium_stop_15%",
          it and it.action == "CLOSE" and it.condition == "premium_stop" and "15%" in it.reason,
          str(it and it.reason))
    P.begin_tick(15.0)
    it = MP.decide(dict(sw, current_premium=1.20), 1.20, df_1m=_df([96.4, 95.7]),
                   open_records=[sw], exit_engine=eng)
    check("D6 a 1m close 95.70 through the pool 96.00 -> CLOSE acceptance",
          it and it.action == "CLOSE" and it.condition == "acceptance", str(it and it.reason))
    P.begin_tick(16.0)
    it = MP.decide(dict(sw, current_premium=0.04), 0.04, df_1m=_df([96.6, 96.7]),
                   open_records=[sw], exit_engine=eng)
    check("D7 value at the nickel -> CLOSE nickel", it and it.condition == "nickel")
    tc = {"trade_id": "d8", "strategy": "TrendCreditSpread", "option_side": "put",
          "is_credit_vertical": True, "is_condor_leg": True, "is_trend_credit": True,
          "entry_premium": 1.30, "current_premium": 1.80, "underlying_stop": 351.88}
    P.begin_tick(17.0)
    it = MP.decide(tc, 1.80, df_1m=_df([353.0, 352.6]), open_records=[tc], exit_engine=eng)
    check("D8 TCS at 1.80 (+38% against) but NO premium stop -> HOLD; only the breach or the nickel closes it",
          it and it.action == "HOLD", str(it and it.action))
    P.begin_tick(18.0)
    it = MP.decide(tc, 1.80, df_1m=_df([352.6, 351.5]), open_records=[tc], exit_engine=eng)
    check("D9 TCS: a 1m close 351.50 through the bound 351.88 -> CLOSE breach",
          it and it.condition == "breach")

    leg2 = dict(sw, trade_id="d10b", option_side="call")
    P.begin_tick(19.0)
    it = MP.decide(sw, 1.20, df_1m=_df([96.6, 96.7]), open_records=[sw, leg2], exit_engine=eng)
    check("D10 a FORMED condor (two legs) is not the plan's to decide -> None (the ladder decides)",
          it is None and not covers(sw, [sw, leg2]))
    check("D11 ORB, ADOPTED and a tent are never the plan's",
          not covers({"strategy": "ORBStrategy"}) and not covers({"strategy": "ADOPTED"})
          and not covers({"strategy": "SweepCreditSpread", "is_tent": True}))
    bf = {"trade_id": "d12", "strategy": "GEXPinButterfly", "option_side": "call",
          "is_butterfly": True, "entry_premium": 0.18, "current_premium": 0.62,
          "stop_premium": 0.135, "target_premium": 0.60}
    P.begin_tick(20.0)
    it = MP.decide(bf, 0.62, df_1m=_df([100.9, 101.0]), exit_engine=eng)
    rd12 = _row(st, "GEXPinButterfly/manage", 20.0)
    check("D12 (r169) the butterfly at 0.62 above its old target 0.60 -> HOLD: it rides to the 15:45 "
          "flatten or the 25% floor, whichever first",
          it and it.action == "HOLD" and rd12 and "15:45 -> flatten" in rd12[1] and "target" not in rd12[1],
          f"{it and it.action} {rd12}")
    P.begin_tick(20.5)
    it = MP.decide(dict(bf, current_premium=0.13), 0.13, df_1m=_df([100.9, 101.0]), exit_engine=eng)
    check("D12a the butterfly at 0.13 <= the 25% floor 0.135 -> CLOSE stop_25%",
          it and it.action == "CLOSE" and it.condition == "stop" and "25%" in it.reason, str(it and it.reason))
    bfb = next(n for n in ast.walk(ast.parse(esrc if 'esrc' in dir() else open(os.path.join(_root, "execution", "exit_engine.py"), encoding="utf-8").read()))
               if isinstance(n, ast.FunctionDef) and n.name == "_evaluate_butterfly")
    bfs = "\n".join(l for l in ast.unparse(bfb).split("\n") if not l.strip().startswith("#"))
    check("D12c the engine's butterfly path acts on neither a target nor a max hold any more",
          "target_hit" not in bfs and "butterfly_max_hold" not in bfs and "stop_hit" in bfs)
    # D12b/D12d (OTV4TEST r25) — the plan's OWN breach close must spend the level it
    # sold against, read back from trades.db the way the TCS/sweep plans read it.
    import tempfile as _tfd
    from datetime import datetime as _dtd, timedelta as _tdd, timezone as _tzd
    import database.trade_logger as _TLD
    import strategy.sweep_credit_spread as _scd
    _TLD._trade_logger = _TLD.TradeLogger(os.path.join(_tfd.mkdtemp(), "d12.db"))
    tcs = {"trade_id": "d12b", "strategy": "TrendCreditSpread", "option_side": "put",
           "is_credit": True, "entry_premium": 0.40, "current_premium": 0.55,
           "stop_premium": 0.0, "underlying_stop": 100.50}
    P.begin_tick(21.0)
    it_b = MP.decide(tcs, 0.55, df_1m=_df([100.7, 100.3]), exit_engine=eng)

    def _closed_row(tid, bound, reason):
        _now = _dtd.now(_tzd.utc)
        c = _TLD.get_trade_logger()._connect()
        try:
            c.execute("INSERT INTO trades (trade_id, symbol, strategy, option_side, underlying_stop,"
                      " status, pnl_usd, entry_time, exit_time, exit_reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (tid, "TST", "TrendCreditSpread", "put", bound, "closed", -15.0,
                       (_now - _tdd(minutes=20)).isoformat(), (_now - _tdd(minutes=5)).isoformat(), reason))
            c.commit()
        finally:
            c.close()
    if it_b is not None and it_b.action == "CLOSE":
        _closed_row("d12b", 100.50, it_b.reason)
    check("D12b a TCS closed by the plan's OWN breach (1m close through its bound) spends that level (TCS keys on the bound)",
          it_b is not None and it_b.action == "CLOSE" and _scd.is_spent("TST", "put", 100.50)[0],
          f"{it_b and it_b.reason} -> spent={_scd.is_spent('TST', 'put', 100.50)}")
    _closed_row("d12d", 99.00, "premium_stop_15% pnl=-16.0%")
    check("D12d (r5) the same spread stopped out on premium does NOT spend its level — acceptance only",
          not _scd.is_spent("TST", "put", 99.00)[0], str(_scd.is_spent("TST", "put", 99.00)))

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
