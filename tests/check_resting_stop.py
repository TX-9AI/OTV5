#!/usr/bin/env python3
"""
tests/check_resting_stop.py  v1.0
A FIRED PREMIUM STOP RESTS AT ITS OWN LEVEL BEFORE IT CHASES (STOP.1, execution/resting_stop.py).
v1.0  2026-10-10  OTV4TEST r266. The operator, 2026-10-10 13:08 ET: "post a resting order when our stop is hit, wait
      for price to come back to it"; 13:10 ET: "I can live with a 5% emergency stop on failed fills"; 18:28 ET: "120
      seconds is fine"; 13:37 ET: "Yes, to all. Study, fit & apply."
  S1  the rule: a mark back at the level books the LEVEL; a mark 5% of entry under it books the mark (emergency);
      120 s books the mark (timeout); inside the window and above the emergency, it keeps resting
  S2  the rest lives on DISK: a fresh interpreter reads the same rest and resolves it the same way
  S3  mode: unset -> off; trade on PAPER -> trade; trade on a LIVE box -> off (refused); junk -> off, named
  S4  eligible: hard_stop and trail_stop_hit on a single long; NOT structure_stop, no_progress, hard_close, a
      butterfly, a condor leg
  S5  END TO END through the REAL PositionManager._manage_one (paper): tick 1 at 0.95 under a 1.00 stop BEGINS a rest
      (nothing booked, the row stays open); tick 2 at 1.01 books 1.00 as "hard_stop... | rested: filled at the level";
      the counterfactual rows say 0.95 was the old rule's price and +$ against it
  S6  END TO END emergency: tick 2 at 0.88 (under 1.00 - 0.05 x 2.00) books 0.88 as "rested: emergency"
  S7  END TO END mode off: tick 1 books 0.95 at once (today's behaviour, unchanged)
  S8  END TO END live box with trade: books at once (refused) - never rests
  S9  any OTHER close of a resting trade abandons the rest (state cleared, an 'abandoned' row)
  S10 the Service mode line names resting_stop (the REAL main._banner_dials)
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_resting_stop_")
for k, v in {"OT_TRADES_DB": "t.db", "OT_DERIVED_DB": "d.db", "OT_FEED_DB": "f.db", "OT_LOG_FILE": "bot.log",
             "OT_RESTING_DB": "r.db", "OT_SIGNAL_JOURNAL_DIR": "sj", "OT_COUNTERFACTUAL_DIR": "cf",
             "OT_RESTING_STOP_STATE": "rest_state.json"}.items():
    os.environ[k] = os.path.join(_TD, v)
os.environ.pop("OT_RESTING_STOP", None)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _rows():
    f = os.path.join(_TD, "cf", "resting_stop.jsonl")
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


def _probe(env):
    e = {k: v for k, v in os.environ.items() if k != "OT_RESTING_STOP"}
    e.update(env)
    p = subprocess.run([sys.executable, "-c", "import config,json;print(json.dumps([config.RESTING_STOP_MODE,"
                        " config.RESTING_STOP_ENV_REFUSED]))"], cwd=ROOT, env=e, capture_output=True, text=True,
                       timeout=120)
    return json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 else p.stderr[-200:]


def _rec(tid, **kw):
    r = {"trade_id": tid, "strategy": "Breakout", "symbol": "QQQ", "direction": "long", "option_side": "call",
         "entry_premium": 2.00, "stop_premium": 1.00, "target_premium": 0.0, "trail_stop": 0.0,
         "underlying_entry": 0.0, "underlying_stop": 0.0, "contracts": 10, "is_butterfly": 0,
         "option_symbol": "QQQ   261012C00750000", "entry_time": "2026-10-12T13:40:00+00:00", "status": "open"}
    r.update(kw)
    return r


def main():
    print("check_resting_stop")
    try:
        import pandas  # noqa: F401
        import config
        import execution.exit_engine as XE
        import execution.position_manager as PM
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    try:
        import execution.resting_stop as RS
    except Exception as exc:                                    # noqa: BLE001
        check("S0 execution/resting_stop.py exists", False, f"{type(exc).__name__}: {exc} - this tree predates r266")
        print("\nRED — 1 of 1 failed: S0")
        return 1

    XE.is_hard_close_time = lambda *a, **k: False             # the clock seam every checker pins (exit_engine:800)
    config.RESTING_STOP_MODE = "trade"

    # ── S1 the rule ─────────────────────────────────────────────────────────
    RS.begin(_rec("s1a"), "hard_stop_50% pnl=-52.5%", 0.95, 1.00, now=1000.0)
    a1 = RS.step("s1a", 0.97, now=1030.0)
    a2 = RS.step("s1a", 1.01, now=1040.0)
    RS.begin(_rec("s1b"), "hard_stop_50% pnl=-52.5%", 0.95, 1.00, now=1000.0)
    b = RS.step("s1b", 0.90, now=1010.0)                       # 1.00 - 0.05 x 2.00 = 0.90 exactly -> emergency
    RS.begin(_rec("s1c"), "trail_stop_hit pnl=20.0%", 2.30, 2.40, now=1000.0)
    c1 = RS.step("s1c", 2.35, now=1119.0)
    c2 = RS.step("s1c", 2.35, now=1120.0)
    check("S1 level back -> books the LEVEL; 5%-of-entry under -> the mark (emergency); 120 s -> the mark; else rest",
          a1 is None and a2 is not None and a2[0] == 1.00 and a2[1] == "filled at the level"
          and b is not None and b[0] == 0.90 and b[1] == "emergency"
          and c1 is None and c2 is not None and c2[0] == 2.35 and c2[1] == "timeout",
          f"a1={a1} a2={a2 and a2[:2]} b={b and b[:2]} c1={c1} c2={c2 and c2[:2]}")

    # ── S2 on disk ──────────────────────────────────────────────────────────
    RS.begin(_rec("s2"), "hard_stop_50% pnl=-52.5%", 0.95, 1.00, now=2000.0)
    p = subprocess.run([sys.executable, "-c", "import execution.resting_stop as R;"
                        "a=R.step('s2', 1.02, now=2010.0); print(a[0], a[1])"],
                       cwd=ROOT, env=dict(os.environ), capture_output=True, text=True, timeout=120)
    check("S2 the rest lives on DISK: a fresh interpreter resolves it (1.00, filled at the level)",
          p.returncode == 0 and p.stdout.strip().endswith("1.0 filled at the level"), p.stdout + p.stderr[-200:])
    RS.finish("s2", 1.0, "filled at the level", now=2010.0)

    # ── S3 mode ─────────────────────────────────────────────────────────────
    m0, mt, mj = _probe({}), _probe({"OT_RESTING_STOP": "trade"}), _probe({"OT_RESTING_STOP": "always"})
    check("S3 unset -> off; trade -> trade; junk -> off and named; a LIVE box refuses trade",
          m0 == ["off", ""] and mt == ["trade", ""] and mj == ["off", "always"]
          and RS.active_mode(True) == "trade" and RS.active_mode(False) == "off", f"{m0} {mt} {mj}")

    # ── S4 eligible ─────────────────────────────────────────────────────────
    ok4 = (RS.eligible(_rec("e"), "hard_stop_12% pnl=-12.0%") and RS.eligible(_rec("e"), "trail_stop_hit pnl=30.0%")
           and not RS.eligible(_rec("e"), "structure_stop: touch 750.00 through 750.10 pnl=-5.0%")
           and not RS.eligible(_rec("e"), "no_progress: 2 closed bars") and not RS.eligible(_rec("e"), "hard_close_ladder_15:50_ET")
           and not RS.eligible(_rec("e", is_butterfly=1), "hard_stop_40%")
           and not RS.eligible(_rec("e", is_condor_leg=1), "hard_stop_40%"))
    check("S4 eligible: hard_stop, trail_stop_hit on a single long only", ok4)

    # ── the REAL PositionManager, paper, stub stores ────────────────────────
    class _TL:
        def __init__(self): self.exits = []
        def update_current_premium(self, *a, **k): pass
        def update_trail_stop(self, *a, **k): pass
        def set_exit_contract(self, *a, **k): return True
        def get_open_trades(self): return []
        def log_exit(self, **k): self.exits.append(k)
    class _Alert:
        def __getattr__(self, n): return lambda *a, **k: None
    PM.get_alert_manager = lambda: _Alert()

    def run(paper, mode, tid, marks):
        config.RESTING_STOP_MODE = mode
        pm = PM.PositionManager(paper_trading=paper)
        tl = _TL(); pm._trade_logger = tl
        rec = _rec(tid)
        seq = list(marks)
        pm._fetch_current_premium = lambda record, chain=None: seq.pop(0)
        if not paper:                                          # never reach a broker: book the mark we pass
            XE.ExitEngine.place_exit_order = (lambda self, record, reason, mark_price=None, **k:
                                              XE.FillResult(confirmed=True, fill_price=mark_price))
        kept = []
        for _ in marks:
            kept.append(pm._manage_one(rec, None, None))
        return tl.exits, kept

    n0 = len(_rows())
    ex5, kept5 = run(True, "trade", "s5", [0.95, 1.01])
    r5 = [r for r in _rows()[n0:] if r["trade_id"] == "s5"]
    check("S5 tick 1 (0.95 under the 1.00 stop) RESTS - nothing booked, row kept; tick 2 (1.01) books 1.00 'rested: filled'",
          kept5 == [True, False] and len(ex5) == 1 and abs(ex5[0]["exit_price"] - 1.00) < 1e-9
          and "rested: filled at the level" in ex5[0]["exit_reason"] and ex5[0]["exit_reason"].startswith("hard_stop")
          and [r["event"] for r in r5] == ["start", "end"] and r5[0]["mark_at_trigger"] == 0.95
          and abs(r5[1]["usd_vs_old_rule"] - 50.0) < 1e-6 and not RS.is_resting("s5"),
          f"kept={kept5} exits={ex5} rows={r5}")

    ex6, kept6 = run(True, "trade", "s6", [0.95, 0.88])
    check("S6 emergency: tick 2 at 0.88 (under 0.90) books 0.88 'rested: emergency'",
          kept6 == [True, False] and len(ex6) == 1 and abs(ex6[0]["exit_price"] - 0.88) < 1e-9
          and "rested: emergency" in ex6[0]["exit_reason"], f"kept={kept6} exits={ex6}")

    ex7, kept7 = run(True, "off", "s7", [0.95])
    check("S7 mode off: tick 1 books 0.95 at once, unchanged", kept7 == [False] and len(ex7) == 1
          and abs(ex7[0]["exit_price"] - 0.95) < 1e-9 and "rested" not in ex7[0]["exit_reason"], f"{kept7} {ex7}")

    ex8, kept8 = run(False, "trade", "s8", [0.95])
    check("S8 a LIVE box with trade books at once (refused) and never rests", kept8 == [False] and len(ex8) == 1
          and not RS.is_resting("s8"), f"{kept8} {ex8}")

    config.RESTING_STOP_MODE = "trade"
    RS.begin(_rec("s9"), "hard_stop_50% pnl=-52.5%", 0.95, 1.00)
    pm = PM.PositionManager(paper_trading=True); tl = _TL(); pm._trade_logger = tl
    pm._execute_exit(_rec("s9"), XE.ExitDecision(should_exit=True, exit_reason="hard_close_ladder_15:50_ET"), 0.92)
    ab = [r for r in _rows() if r["trade_id"] == "s9" and r["event"] == "abandoned"]
    check("S9 any OTHER close of a resting trade abandons the rest", not RS.is_resting("s9") and len(ab) == 1, f"{ab}")

    e = dict(os.environ, OT_RESTING_STOP="trade", OT_INSTRUMENT=os.environ.get("OT_INSTRUMENT", "QQQ"))
    p = subprocess.run([sys.executable, "-c", "import main;print(main._banner_dials())"], cwd=ROOT, env=e,
                       capture_output=True, text=True, timeout=240)
    out = (p.stdout.strip().splitlines() or [""])[-1]
    check("S10 the Service mode line names 'resting_stop=trade'", p.returncode == 0 and "resting_stop=trade" in out,
          out or p.stderr[-300:])

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
