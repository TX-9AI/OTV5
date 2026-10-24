#!/usr/bin/env python3
"""
tests/check_exit_pricing.py  v1.2
v1.2  2026-10-18  OTV4TEST r293 (DELTA.2) — P6b drives PositionManager._fetch_current_premium with a quoted contract whose
      delta is None, then 0.0: current_delta must be None and the r209 warning must fire once; 0.45 restores it. The
      production stash stored 0.0 and flagged it readable, so P6's warning never fired in production (audit 10-18 D2).
v1.1  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.0  2026-10-03  OTV4TEST r209 (EXIT.4) — THE EXIT'S PRICING IS DECLARED; THE RUNAWAY STOPS; A DARK DELTA IS SAID.

  From the 10-03 audit (A4, A5, A6, A10, A13) and the operator's rulings that
  day: "why do you say mark? Clearly ladder is more advantageous" (credit and
  butterfly stops keep the ladder); "runaway, concur" (keep the 20% stop);
  "yes, fix the trading path defects".

  P1  management.EXIT_PRICING names nine conditions; a CLOSE intent carries
      its pricing, a HOLD carries none
  P2  NO PRICE CHANGED: for each condition's real reason text the old
      substring rule and the declaration agree
  P3  the REAL _exit_policy reads a declaration only for ITS OWN reason, and
      the end-of-day close still outranks it
  P4  the REAL ManagementPlan.decide closes a credit leg on its premium stop
      with pricing `walk`, and a long option on its hard stop with `floor`
  P5  RUN.10: the REAL exit engine STOPS a Runaway below its premium floor and
      still HOLDS a Hunt there (recorded would-have-floored)
  P6  a Breakout delta that cannot be read WARNS once, sets current_delta None,
      and says once when it is back; a Runaway does not warn
  P7  the session guard has no butterfly cutoff branch; the parameter remains
  P8  the structure stop's reason says `touch`, not `1m close`

Run:  python3 tests/check_exit_pricing.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import logging
import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_exit_pricing_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_PAPER_TRADING"] = "1"

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(_S, "plan.db"))
        self.conn.row_factory = sqlite3.Row

    def commit(self):
        self.conn.commit()


class _Logs(logging.Handler):
    def __init__(self):
        super().__init__(); self.lines = []

    def emit(self, record):
        self.lines.append((record.levelname, record.getMessage()))


def _frame(rows, hhmm):
    import pandas as pd
    idx = pd.date_range(f"2026-09-10 {hhmm}", periods=len(rows), freq="1min", tz="America/New_York")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx).assign(volume=1000)


REASONS = {
    "hard_stop": "hard_stop_20% pnl=-20.0%", "structure_stop": "structure_stop: touch 99.80 through 100.00 pnl=-8.0%",
    "premium_stop": "premium_stop_15% pnl=-15.0%", "stop": "stop_20% pnl=-20.0%",
    "breach": "breach: touch 99.80 through 100.00 pnl=-8.0%", "acceptance": "acceptance: touch 99.8 through 100.0 pnl=-8.0%",
    "delta_par": "delta_par: delta 0.910 >= par 0.90 pnl=80.0%", "target": "target_hit pnl=100.0%",
    "nickel": "nickel_close pnl=80.0%",
}


def main():
    import execution.exit_engine as XE
    M = None
    try:
        from strategy import management as M
        EP = dict(M.EXIT_PRICING)
        check("P1 nine conditions are declared; a CLOSE carries its pricing and a HOLD carries none",
              set(EP) == set(REASONS) and M.Intent("CLOSE", "x", "premium_stop").pricing == "walk"
              and M.Intent("CLOSE", "x", "hard_stop").pricing == "floor" and M.Intent("HOLD", "", "hard_stop").pricing is None
              and M.Intent("CLOSE", "x", "trail").pricing is None, str(EP))
        rec = {"strategy": "X"}
        diff = {c: (XE.ExitEngine._exit_policy(rec, REASONS[c]), EP[c]) for c in REASONS
                if XE.ExitEngine._exit_policy(rec, REASONS[c]) != EP[c]}
        check("P2 NO PRICE CHANGED: the substring rule and the declaration agree on all nine reasons", not diff, str(diff))
    except Exception as exc:                                  # noqa: BLE001
        check("P1 (did not run)", False, f"{type(exc).__name__}: {exc}")
        check("P2 (did not run)", False, "management.EXIT_PRICING absent")

    try:
        r1 = "premium_stop_15% pnl=-15.0%"
        own = XE.ExitEngine._exit_policy({"_exit_pricing": (r1, "floor")}, r1)
        other = XE.ExitEngine._exit_policy({"_exit_pricing": ("some other reason", "floor")}, r1)
        sv = XE.hard_close_order_mode
        XE.hard_close_order_mode = lambda *_a, **_k: "limit"
        try:
            eod = XE.ExitEngine._exit_policy({"_exit_pricing": ("hard_close_ladder_15:50_ET", "floor"), "strategy": "Breakout",
                                              "option_symbol": "X"}, "hard_close_ladder_15:50_ET")
        finally:
            XE.hard_close_order_mode = sv
        check("P3 a declaration is read for ITS OWN reason only, and the end-of-day close outranks it",
              own == "floor" and other == "walk" and eod in ("debit_hard_close", "eod_resting", "eod_cross"),
              f"own {own}, another reason {other}, eod {eod}")
    except Exception as exc:                                  # noqa: BLE001
        check("P3 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        from strategy import plan as P
        st = _Store(); P.bind_store(st)
        try:
            MP = M.ManagementPlan()
            ctx = {"price": 101.0, "derived_engines": [], "orb_high": 101.0, "orb_low": 100.0}
            P.begin_tick(1.0)
            credit = {"trade_id": "cr1", "strategy": "SweepCreditSpread", "option_side": "call", "direction": "neutral",
                      "entry_premium": 0.40, "current_premium": 0.60, "stop_premium": 0.49, "spread_width": 1.0,
                      "credit_received": 0.40, "is_condor_leg": 1, "is_credit_vertical": 1, "short_strike": 102.0,
                      "long_strike": 103.0, "underlying_stop": 0.0, "contracts": 1}
            ic = MP.decide(credit, 0.60, df_1m=None, current_price=101.0, ctx=ctx, exit_engine=None)
            P.begin_tick(2.0)
            debit = {"trade_id": "rw1", "strategy": "RunawayContinuation", "option_side": "call", "direction": "long",
                     "entry_premium": 1.00, "current_premium": 0.70, "stop_premium": 0.80, "target_premium": 2.00,
                     "underlying_stop": 0.0, "contracts": 1}
            idb = MP.decide(debit, 0.70, df_1m=None, current_price=101.0, ctx=ctx, exit_engine=None)
        finally:
            P.bind_store(None)
        check("P4 decide(): the credit leg's premium stop is priced `walk`, the long option's hard stop `floor`",
              ic is not None and ic.action == "CLOSE" and ic.reason.startswith("premium_stop") and ic.pricing == "walk"
              and idb is not None and idb.action == "CLOSE" and idb.reason.startswith("hard_stop") and idb.pricing == "floor",
              f"credit {ic and (ic.action, ic.reason, getattr(ic, 'pricing', '?'))}; "
              f"debit {idb and (idb.action, idb.reason, getattr(idb, 'pricing', '?'))}")
    except Exception as exc:                                  # noqa: BLE001
        check("P4 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        import datetime as _dt
        from zoneinfo import ZoneInfo
        _rdt, _rhc = XE.datetime, XE.is_hard_close_time

        class _F(_dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return _dt.datetime(2026, 9, 10, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        XE.datetime = _F; XE.is_hard_close_time = lambda: False
        try:
            xe = XE.ExitEngine(paper_trading=True)
            xe._theta_bleed = lambda *a, **k: False
            xe._rejected_handoff = lambda *a, **k: ""
            xe._runaway_thesis_exits = lambda *a, **k: ""
            xe._hunt_at_target = lambda *a, **k: ""
            base = {"trade_id": "p5", "setup_type": "x", "direction": "long", "option_side": "call",
                    "entry_premium": 1.00, "contracts": 1, "status": "open", "stop_premium": 0.80, "target_premium": 0.0,
                    "trail_activation": 0.0, "underlying_entry": 100.6, "underlying_stop": 0.0, "underlying_target": 0.0,
                    "orb_range_high": 101.0, "orb_range_low": 100.0, "entry_time": "2026-09-10T09:47:00"}
            fr = _frame([(100.5, 100.7, 100.4, 100.6), (100.6, 100.8, 100.5, 100.7)], "09:58")
            run = dict(base, trade_id="p5-run", strategy="RunawayContinuation")
            hunt = dict(base, trade_id="p5-hunt", strategy="LiquidityHunt")
            dr = xe._evaluate_orb(run, 0.70, fr)
            dh = xe._evaluate_orb(hunt, 0.70, fr)
        finally:
            XE.datetime, XE.is_hard_close_time = _rdt, _rhc
        check("P5 at 0.70 against a 0.80 floor the Runaway is STOPPED and the Hunt HOLDS (would-have-floored recorded)",
              dr.should_exit is True and not run.get("_would_have_floored")
              and dh.should_exit is False and bool(hunt.get("_would_have_floored")),
              f"runaway exit {dr.should_exit} ({dr.exit_reason}) flag {run.get('_would_have_floored')}; "
              f"hunt exit {dh.should_exit} ({dh.exit_reason}) flag {hunt.get('_would_have_floored')}")
    except Exception as exc:                                  # noqa: BLE001
        check("P5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        import execution.position_manager as PM
        h = _Logs(); lg = logging.getLogger("execution.position_manager"); lg.addHandler(h); lg.setLevel(logging.INFO)
        brk = {"trade_id": "bk1", "strategy": "Breakout", "current_delta": 0.55}
        PM._delta_readable(brk, False, "no quoted contract at the strike")
        PM._delta_readable(brk, False, "again")
        w = [m for lv, m in h.lines if lv == "WARNING" and "UNREADABLE" in m]
        dark = brk.get("current_delta", "unset")
        PM._delta_readable(brk, True)
        back = [m for lv, m in h.lines if "readable again" in m]
        run = {"trade_id": "rw9", "strategy": "RunawayContinuation", "current_delta": 0.5}
        PM._delta_readable(run, False, "x")
        w2 = [m for lv, m in h.lines if lv == "WARNING" and "UNREADABLE" in m]
        lg.removeHandler(h)
        check("P6 a Breakout's unreadable delta WARNS ONCE, becomes None, and its return is said once; a Runaway is silent",
              len(w) == 1 and dark is None and len(back) == 1 and "_delta_unreadable" not in brk and len(w2) == 1
              and run.get("current_delta") is None, f"warnings {len(w)}/{len(w2)}, delta {dark}, back {len(back)}")
    except Exception as exc:                                  # noqa: BLE001
        check("P6 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # r293 (DELTA.2) — THROUGH THE REAL FETCH. P6 drove _delta_readable by hand; the production stash stored
    # float(delta or 0.0) and then called _delta_readable(record, True), so the warning P6 proves could never fire.
    try:
        import execution.position_manager as PM
        h = _Logs(); lg = logging.getLogger("execution.position_manager"); lg.addHandler(h); lg.setLevel(logging.INFO)
        pm = PM.PositionManager(paper_trading=True)

        class _C:
            def __init__(self, strike, mark, delta):
                self.strike, self.mark, self.bid, self.ask = strike, mark, mark - 0.01, mark + 0.01
                self.delta, self.theta, self.iv, self.gamma = delta, -0.02, 0.30, 0.01

        class _Chain:
            def __init__(self, c):
                self.calls, self.puts = [c], []
        rec = {"trade_id": "d2", "strategy": "Breakout", "option_side": "call", "strike": 100.0,
               "entry_premium": 1.0, "current_delta": 0.55, "is_butterfly": 0}
        m1 = pm._fetch_current_premium(rec, _Chain(_C(100.0, 1.20, None)))
        d_none = rec.get("current_delta", "unset")
        m2 = pm._fetch_current_premium(rec, _Chain(_C(100.0, 1.25, 0.0)))     # the chain's missing-greek sentinel
        d_zero = rec.get("current_delta", "unset")
        w = [m for lv, m in h.lines if lv == "WARNING" and "UNREADABLE" in m]
        m3 = pm._fetch_current_premium(rec, _Chain(_C(100.0, 1.30, 0.45)))
        back = [m for lv, m in h.lines if "readable again" in m]
        lg.removeHandler(h)
        check("P6b THE REAL FETCH: delta None then 0.0 on the quoted contract -> current_delta None, ONE warning; 0.45 restores it, said once",
              m1 == 1.20 and m2 == 1.25 and m3 == 1.30 and d_none is None and d_zero is None and len(w) == 1
              and rec.get("current_delta") == 0.45 and len(back) == 1,
              f"marks {m1},{m2},{m3} delta {d_none!r}/{d_zero!r}/{rec.get('current_delta')!r} warnings {len(w)} back {len(back)}")
    except Exception as exc:                                  # noqa: BLE001
        check("P6b (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        src = open(os.path.join(_root, "risk", "session_guard.py")).read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "can_enter")
        params = [a.arg for a in fn.args.args]
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        used = any(isinstance(n, ast.Name) and n.id == "is_butterfly" for n in ast.walk(fn))
        check("P7 the session guard keeps the is_butterfly parameter and no longer branches on it",
              "is_butterfly" in params and not used
              and not any(isinstance(n, ast.Name) and n.id == "_BUTTERFLY_CUTOFF" for n in ast.walk(fn)),
              f"params {params}, used {used}")
    except Exception as exc:                                  # noqa: BLE001
        check("P7 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        msrc = open(os.path.join(_root, "strategy", "management.py")).read()
        code = "\n".join(l for l in msrc.split('"""', 2)[2].splitlines() if not l.strip().startswith("#"))
        check("P8 the structure stop's reason and narration say `touch`; no `1m close` remains in the code",
              'touch {last_close:.2f} through' in code and "1m close" not in code,
              f"touch {'touch {last_close' in code}, '1m close' left {code.count('1m close')}")
    except Exception as exc:                                  # noqa: BLE001
        check("P8 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — pricing is declared and unchanged; the Runaway stops; a dark delta is said; the dead cutoff is gone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
