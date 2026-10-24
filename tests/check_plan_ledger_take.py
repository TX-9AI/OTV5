#!/usr/bin/env python3
"""
tests/check_plan_ledger_take.py  v1.1
v1.1  2026-10-19  OTV4TEST r303 (PSTATE.1) — L4's ORCS is DORMANT by default and a dormant plan opens no ledger row by ruling,
      so this run switches ORCS ACTIVE (OT_ORCS=1) to test the per-leg rows. check_plan_states D3 pins dormant.
v1.0  2026-10-03  OTV4TEST r211 (PLN.2) — EVERY TAKE OPENS ITS PLAN_LEDGER ROW, IN THE STORE THAT IS BOUND.

  The 10-03 audit: plan_ledger held ORB plans and nothing else. `_ledger_open`
  returned whenever a store was bound (r6, to keep test rows out of the box) -
  and the plan board binds the box's own store at start, so no take ever opened
  a row in production; and nine plans carried self_ledgers=True where two
  strategies really open their own. The operator, 2026-10-03: "Gather as much
  as is available to serve our studies and backtests."

  Drives the REAL Plan / PlanTick.take / PlanLedger on a scratch store.
  L1  take() with a store bound writes ONE TRIGGERED row, with the spread's strikes
  L2  a plan flagged self_ledgers that does NOT open its own rows (the Runaway)
      gets its row; a strategy that DOES (the ORB, the condor) gets none here
  L3  a second take closes the first as never filled (unchanged behaviour)
  L4  ORCS opens one row per leg and keeps the sibling's; a fill links to the
      row opened last (the leg about to execute)
  L5  nothing is written anywhere when no store is bound

Run:  python3 tests/check_plan_ledger_take.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sqlite3
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ["OT_ORCS"] = "1"   # r303: L4's subject is active (check_plan_states pins dormant)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_plan_ledger_take_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def commit(self):
        self.conn.commit()


def _rows(st, strategy=None):
    try:
        q = "SELECT strategy, state, short_strike, long_strike, closed_ts, trade_ids, direction FROM plan_ledger"
        rows = [tuple(r) for r in st.conn.execute(q + " ORDER BY created_ts, rowid")]
    except sqlite3.OperationalError:
        return []
    return [r for r in rows if strategy is None or r[0] == strategy]


def _sig(side="put"):
    s = types.SimpleNamespace(option_side=side, underlying_entry=750.2, short_put_contract=None, long_put_contract=None,
                              short_call_contract=None, long_call_contract=None)
    k = (747.0, 744.0) if side == "put" else (753.0, 756.0)
    setattr(s, f"short_{side}_contract", types.SimpleNamespace(strike=k[0]))
    setattr(s, f"long_{side}_contract", types.SimpleNamespace(strike=k[1]))
    return s


def main():
    from strategy import plan as P
    st = _Store(os.path.join(_S, "led.db"))
    P.bind_store(st)
    try:
        P.REGISTRY.pop("GateTake", None)
        pl = P.Plan("GateTake", ("credit", "width", "risk", "r"))
        P.begin_tick(1000.0)
        t = pl.tick(750.2, "put")
        t.credit_spread(747.0, 744.0, 0.25)
        t.take(_sig("put"))
        r = _rows(st, "GateTake")
        check("L1 take() with a store bound writes ONE TRIGGERED row carrying 747/744",
              len(r) == 1 and r[0][1] == "TRIGGERED" and r[0][2:4] == (747.0, 744.0) and r[0][4] is None, str(r))

        run = P.Plan("RunawayContinuation", ("r",), record_only=True, self_ledgers=True)
        orb = P.Plan("ORBStrategy", ("r",), record_only=True, self_ledgers=True)
        P.begin_tick(1001.0)
        run.tick(750.2, "long").take(_sig("put"))
        orb.tick(750.2, "long").take(_sig("put"))
        check("L2 the Runaway (flagged self_ledgers, opens none itself) gets its row; the ORB gets none here",
              len(_rows(st, "RunawayContinuation")) == 1 and _rows(st, "ORBStrategy") == []
              and "ORBStrategy" in getattr(P, "OWN_LEDGER", ()),
              f"runaway {_rows(st, 'RunawayContinuation')}, orb {_rows(st, 'ORBStrategy')}")

        P.begin_tick(1002.0)
        t2 = pl.tick(750.4, "put"); t2.credit_spread(747.0, 744.0, 0.26); t2.take(_sig("put"))
        r = _rows(st, "GateTake")
        check("L3 a second take closes the first as never filled and opens a new row",
              len(r) == 2 and r[0][4] is not None and r[1][4] is None, str(r))
    except Exception as exc:                                  # noqa: BLE001
        check("L1 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        from strategy import orcs as S
        from derived.plan_ledger import PlanLedger
        P._DORMANT.pop("OpeningRangeCreditSpread", None)
        sg = S.OpeningRangeCreditSpread()
        P.begin_tick(1003.0)
        sp, sc = _sig("put"), _sig("call")
        sg.ledger_open(sp)
        led = PlanLedger(st, sg.planner.symbol)
        a = led.link_trade("OpeningRangeCreditSpread", "trade-put")
        sg.ledger_open(sc)
        b = led.link_trade("OpeningRangeCreditSpread", "trade-call")
        r = _rows(st, "OpeningRangeCreditSpread")
        check("L4 ORCS: a row per leg, the sibling kept; each fill links to the row opened for it",
              len(r) == 2 and all(x[4] is None for x in r) and r[0][2:4] == (747.0, 744.0) and r[1][2:4] == (753.0, 756.0)
              and "trade-put" in (r[0][5] or "") and "trade-call" in (r[1][5] or "") and a != b, f"{r} links {a},{b}")
    except Exception as exc:                                  # noqa: BLE001
        check("L4 (did not run)", False, f"{type(exc).__name__}: {exc}")
    finally:
        P.bind_store(None)

    try:
        n0 = len(_rows(st))
        P.REGISTRY.pop("GateUnbound", None)
        ub = P.Plan("GateUnbound", ("r",))
        ub._store = None
        sv = P._store
        P._store = lambda: None
        try:
            P.begin_tick(1004.0)
            ub.tick(750.2, "put").take(_sig("put"))
        finally:
            P._store = sv
        check("L5 with no store bound nothing is written and nothing raises", len(_rows(st)) == n0, f"{n0} -> {len(_rows(st))}")
    except Exception as exc:                                  # noqa: BLE001
        check("L5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — every take opens its ledger row in the bound store; ORCS opens one per leg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
