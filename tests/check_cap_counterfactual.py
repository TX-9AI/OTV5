#!/usr/bin/env python3
"""
tests/check_cap_counterfactual.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-18  OTV4TEST r288 (PARK.1) — the fake realized_pnl_today takes the cap's new exclude_strategies argument
      (RiskManager.day_realized_pnl passes config.CAP_EXCLUDED_STRATEGIES); no check changed.
v1.0  2026-10-03  OTV4TEST r208 (CAP.4) — THE CAP COUNTERFACTUAL IS RECORDED FOR EVERY ENTRY AND REFUSES NOTHING.

  The operator, 2026-10-03, on refusing an entry whose planned risk would breach
  the daily cap: "No, allow it. But do a counter factual study with a set review
  date in 2 weeks." (review 2026-10-17)

  Drives the REAL RiskManager.note_entry_risk with the REAL TradeLogger on a
  scratch trades.db; the day's realized figure is set at the logger.
  K1  a long option with a premium stop, headroom 100: risk at the stop 200,
      at max loss 1,000 - would refuse on both, and the line says so
  K2  the same entry with the day flat: would refuse on neither; STILL recorded
  K3  a credit vertical has no stop risk; max loss 672 against headroom 500
      would refuse; a cap-exempt butterfly is marked exempt
  K4  it never raises and never refuses: an unwritable path warns, returns None
  K5  the file is BESIDE the logger's trades.db (a checker's scratch takes it)
  K6  both entry paths call it right after log_entry (a source check, stated
      as one - the live proof is Monday's line count against the day's entries)

Run:  python3 tests/check_cap_counterfactual.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import json
import logging
import os
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_cap_counterfactual_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_PAPER_TRADING"] = "1"
os.environ["OT_RISK_USD"] = "1050"
os.environ["OT_DAILY_LOSS_LIMIT"] = "5000"

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    try:
        import database.trade_logger as TLM
        from database.trade_logger import TradeLogger
        import risk.risk_manager as RMM
        if not hasattr(RMM.RiskManager, "note_entry_risk"):
            raise AttributeError("RiskManager.note_entry_risk is absent")
    except Exception as exc:                                  # noqa: BLE001
        for n in ("K1", "K2", "K3", "K4", "K5"):
            check(f"{n} (did not run)", False, f"{type(exc).__name__}: {exc}")
        return _k6()

    db = os.path.join(_S, "cf", "trades.db")
    os.makedirs(os.path.dirname(db), exist_ok=True)
    TLM._trade_logger = TradeLogger(db)
    rm = RMM.RiskManager()
    path = RMM.cap_cf_path()

    def lines():
        return [json.loads(x) for x in open(path)] if os.path.exists(path) else []

    def day(v):
        TLM._trade_logger.realized_pnl_today = lambda *a, **k: v   # r288: the cap passes exclude_strategies

    long_opt = {"trade_id": "aaaaaaaa-1", "strategy": "RunawayContinuation", "entry_premium": 1.00,
                "stop_premium": 0.80, "contracts": 10, "total_cost": 1000.0, "max_loss": 0.0}
    try:
        day(-4900.0)
        out = rm.note_entry_risk(dict(long_opt))
        r = lines()[-1] if lines() else {}
        check("K1 headroom 100: stop risk 200 and max loss 1,000 would BOTH be refused - recorded, nothing refused",
              out is None and r.get("risk_stop") == 200.0 and r.get("risk_max") == 1000.0 and r.get("headroom") == 100.0
              and r.get("realized") == -4900.0 and r.get("limit") == 5000.0 and r.get("refuse_stop") == 1
              and r.get("refuse_max") == 1 and r.get("strategy") == "RunawayContinuation"
              and r.get("trade_id") == "aaaaaaaa-1" and r.get("exempt") == 0, str(r))
        day(0.0)
        rm.note_entry_risk(dict(long_opt, trade_id="aaaaaaaa-2"))
        r = lines()[-1]
        check("K2 the day flat: refused on neither, and the entry is STILL recorded (the study's denominator)",
              len(lines()) == 2 and r.get("refuse_stop") == 0 and r.get("refuse_max") == 0 and r.get("headroom") == 5000.0,
              f"{len(lines())} lines, {r}")
        day(-4500.0)
        rm.note_entry_risk({"trade_id": "bbbbbbbb-1", "strategy": "OpeningRangeCreditSpread", "entry_premium": 0.28,
                            "stop_premium": 0.0, "contracts": 1, "credit_received": 0.28, "max_loss": 672.0,
                            "total_cost": 672.0, "is_condor_leg": 1})
        c = lines()[-1]
        rm.note_entry_risk({"trade_id": "cccccccc-1", "strategy": "GEXPinButterfly", "entry_premium": 0.50,
                            "stop_premium": 0.0, "contracts": 4, "total_cost": 200.0, "max_loss": 200.0})
        b = lines()[-1]
        check("K3 a credit vertical has NO stop risk and its max loss 672 > headroom 500 would refuse; the fly is exempt",
              c.get("risk_stop") is None and c.get("risk_max") == 672.0 and c.get("refuse_stop") == 1
              and c.get("refuse_max") == 1 and c.get("exempt") == 0 and b.get("exempt") == 1 and b.get("refuse_max") == 0,
              f"credit {c}; fly {b}")
    except Exception as exc:                                  # noqa: BLE001
        check("K1 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        class _Logs(logging.Handler):
            def __init__(self):
                super().__init__(); self.lines = []

            def emit(self, record):
                self.lines.append(record.getMessage())
        h = _Logs(); logging.getLogger("risk.risk_manager").addHandler(h)
        sv = RMM.cap_cf_path
        RMM.cap_cf_path = lambda: os.path.join(_S, "no", "such", "dir", "x.jsonl")
        try:
            n0 = len(lines())
            out = rm.note_entry_risk(dict(long_opt, trade_id="dddddddd-1"))
        finally:
            RMM.cap_cf_path = sv
        check("K4 an unwritable file WARNS, returns None and raises nothing",
              out is None and len(lines()) == n0 and any("cap counterfactual NOT recorded" in x for x in h.lines),
              f"warnings {h.lines[-2:]}")
        check("K5 the file sits beside the logger's own trades.db",
              os.path.dirname(path) == os.path.dirname(db) and os.path.basename(path) == "cap_counterfactual.jsonl", path)
    except Exception as exc:                                  # noqa: BLE001
        check("K4 (did not run)", False, f"{type(exc).__name__}: {exc}")
    return _k6()


def _k6():
    try:
        def after_log_entry(path, func=None):
            src = open(os.path.join(_root, path)).read()
            tree = ast.parse(src)
            scope = tree
            if func:
                scope = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func)
            le = [n.lineno for n in ast.walk(scope) if isinstance(n, ast.Call)
                  and getattr(n.func, "attr", "") == "log_entry"]
            ne = [n.lineno for n in ast.walk(scope) if isinstance(n, ast.Call)
                  and getattr(n.func, "attr", "") == "note_entry_risk"]
            return bool(le and ne and any(0 < b - a <= 6 for a in le for b in ne)), (le, ne)
        e_ok, e = after_log_entry("execution/entry_engine.py")
        m_ok, m = after_log_entry("main.py", "_execute_condor_leg")
        check("K6 entry_engine and _execute_condor_leg each call note_entry_risk right after log_entry (source check)",
              e_ok and m_ok, f"entry_engine {e}, main {m}")
    except Exception as exc:                                  # noqa: BLE001
        check("K6 (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — every entry leaves its cap-counterfactual line; nothing is refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
