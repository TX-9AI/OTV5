#!/usr/bin/env python3
"""
tests/check_excursion_plan_exit.py  v5.1
v5.1  2026-11-14  OTV5 r113 (AM.7) — new. THE EXCURSION SEES THE TICK THE MANAGEMENT PLAN EXITS ON. NFLX 2026-11-13
      booked target_hit at 0.245 with mfe_premium 0.205: the management plan's CLOSE skipped exit_engine.evaluate(),
      the only caller of _track_excursion, so the exit tick's mark was never recorded. Driven through the REAL
      PositionManager._manage_one (paper, a stub trade logger) on a RunawayContinuation record (the plan covers it).

  X1  a Runaway marked 1.50 then 2.45 (over its 2.00 target): the plan closes it on the second tick at 2.45, and the
      excursion handed to log_exit says mfe_premium >= the exit price (2.45)
  X2  one tick per pricing pass: two ticks -> excursion_ticks == 2 (the pass that reaches both position_manager's call
      and evaluate() is counted once)
  X3  a record with no _px_seq still counts every call (a hand-built record, as before)
Born red on r108 (6b380b2): X1 (mfe 1.50 < exit 2.45).
Run:  OT_INSTRUMENT=QQQ python3 tests/check_excursion_plan_exit.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_excursion_plan_exit_")
for k, v in {"OT_TRADES_DB": "t.db", "OT_DERIVED_DB": "d.db", "OT_FEED_DB": "f.db", "OT_LOG_FILE": "bot.log",
             "OT_RESTING_DB": "r.db", "OT_SIGNAL_JOURNAL_DIR": "sj", "OT_COUNTERFACTUAL_DIR": "cf",
             "OT_ALERT_SPOOL": "spool.jsonl"}.items():
    os.environ[k] = os.path.join(_TD, v)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _C:
    def __init__(self, strike, sym):
        self.strike, self.streamer_symbol = strike, sym


class _Chain:
    def __init__(self, spot=748.0):
        self.spot_price = spot
        self.calls = [_C(750.0, ".QQQ261113C750")]
        self.puts = []


def main():
    try:
        import execution.position_manager as PM
        import execution.exit_engine as XE
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN — the bot's imports cannot load ({type(exc).__name__}: {exc}); run under the venv")
        return 2
    XE.is_hard_close_time = lambda *a, **k: False

    class _TL:
        def __init__(self):
            self.exits = []

        def update_current_premium(self, *a, **k): pass
        def update_trail_stop(self, *a, **k): pass
        def set_exit_contract(self, *a, **k): return True
        def get_open_trades(self): return []
        def update_fields(self, *a, **k): pass
        def log_exit(self, **k): self.exits.append(k)

    class _Alert:
        def __getattr__(self, n):
            return lambda *a, **k: None
    PM.get_alert_manager = lambda: _Alert()

    rec = {"trade_id": "x1-runaway", "strategy": "RunawayContinuation", "setup_type": "runaway", "symbol": "QQQ",
           "direction": "long", "option_side": "call", "entry_premium": 1.00, "stop_premium": 0.80,
           "target_premium": 2.00, "trail_stop": 0.0, "underlying_entry": 0.0, "underlying_stop": 0.0,
           "contracts": 10, "is_butterfly": 0, "option_symbol": "QQQ   261113C00750000", "expiry": "2026-11-13",
           "entry_time": "2026-11-13T14:40:00+00:00", "status": "open"}
    pm = PM.PositionManager(paper_trading=True)
    tl = _TL()
    pm._trade_logger = tl
    marks = [1.50, 2.45]
    real_fetch = pm._fetch_current_premium

    def _fetch(record, chain=None):
        record["_px_seq"] = int(record.get("_px_seq") or 0) + 1     # one pricing pass, as the real fetch stamps it
        return marks.pop(0)
    pm._fetch_current_premium = _fetch
    kept = [pm._manage_one(rec, None, _Chain()) for _ in range(2)]
    ex = tl.exits[0] if tl.exits else {}
    exc = ex.get("excursion") or {}
    mfe = exc.get("mfe_premium", rec.get("mfe_premium"))
    px = ex.get("exit_price")
    check("X1 the plan closes at 2.45 and the excursion's mfe_premium >= the exit price",
          kept == [True, False] and px is not None and abs(float(px) - 2.45) < 1e-9
          and mfe is not None and float(mfe) >= 2.45 - 1e-9,
          f"kept={kept} exit={px} reason={ex.get('exit_reason')} mfe={mfe} excursion={exc}")
    check("X2 one tick per pricing pass: excursion_ticks == 2 after two ticks",
          int(rec.get("excursion_ticks") or 0) == 2, f"ticks={rec.get('excursion_ticks')}")

    r3 = {"trade_id": "x3"}
    for p in (1.0, 1.2, 0.9):
        XE._track_excursion(r3, p)
    check("X3 a record with no _px_seq counts every call (3 calls -> 3 ticks; mfe 1.2, mae 0.9)",
          r3.get("excursion_ticks") == 3 and r3.get("mfe_premium") == 1.2 and r3.get("mae_premium") == 0.9, f"{r3}")
    pm._fetch_current_premium = real_fetch

    print("=" * 60)
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {FAILED}")
        return 1
    print("GREEN — the excursion sees the tick the plan exits on")
    return 0


if __name__ == "__main__":
    sys.exit(main())
