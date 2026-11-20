#!/usr/bin/env python3
"""
tests/check_entry_tick_grid.py — v5.0
v5.0  2026-11-20  OTV5 r132 (TICK.3) — new. THE LIVE ENTRY LADDER WALKS THE UNDERLYING'S VENUE GRID, NOT THE OCC
      SYMBOL'S. The forward-edge study 2026-11-20 (D1; ~/reviews/studies/forward_edge_20261120/REPORT.md): at r131
      EntryEngine._place_single_leg handed signal.contract.symbol (the OCC string) to _walk_price ->
      ladder_registry.price_for -> entry_ladder._increment -> tick_size.resolve. The venue rule is cached under the
      UNDERLYING (data/options_chain._get_chain_structure) and config.PENNY_CLASSES lists underlyings, so the OCC
      lookup always missed and fell back to the non-penny grid ($0.05 under $3, $0.10 at $3 or more). The operator,
      2026-11-20: "Yes to both".
  G1  QQQ, a cached QQQ venue rule (0.01), bid 3.40 / ask 3.50: the live entry path (_place_single_leg, the broker
      stubbed in entry_engine's namespace, every rung refused) posts 3.42, 3.43, 3.44, 3.45 in that order - the 25%
      start snapped down in our favour, one penny a tick, ending at the mark - and never above the mark 3.45 after
      (r131 posted 3.40 on EVERY tick and never reached the mark: on the dime grid the 25% start 3.425 floors to
      3.40, the mark 3.45 floors to 3.40, and the ratchet's 3.50 is clamped back to that same 3.40)
  G2  the same walk never logs "NO VENUE RULE": the grid came from the cached rule, not the PENNY_CLASSES guess
  G3  the walk KEY is unchanged: ladder_registry holds intent_key(<the OCC symbol>, "open", "single") mid-walk, and
      only that key (the registry key may name the contract; only the grid lookup changed)
  G4  QQQ where the grid was already right (a quote that proves penny, bid 1.23 / ask 1.31): the entry posts
      1.25, 1.26, 1.27 - the same table rungs() gives on either symbol
  G5  SPX (a child interpreter at OT_INSTRUMENT=SPX, the Cboe rule cached: 0.05 under $3, 0.10 at or above): bid
      3.40 / ask 3.80 posts 3.50, 3.60 and bid 1.10 / ask 1.30 posts 1.15, 1.20 - the tables r131 already posted (the
      OCC miss fell back to SPX's non-penny list, which equals its venue rule)
  G6  exits are unchanged: ExitEngine._exit_limit on a QQQ single-leg close (record symbol QQQ, the walk policy),
      bid 3.40 / ask 3.50, sells 3.48, 3.47, 3.46, 3.45 - the penny grid, as at r131
THE BROKER IS NEVER REACHED: get_session / get_account / place_order / confirm_order_fill / order_guard /
buying_power are stubbed in entry_engine's namespace, as tests/check_park_entry_mark.py stubs them.
Born red on r131 (0819f1e) at G1 and G2 (posted [3.40] x 8; "NO VENUE RULE for QQQ   261120C00600000");
G3-G6 pass on r131. Mutant: _place_single_leg's grid symbol back to `symbol` -> G1, G2 red.
Run:  python3 tests/check_entry_tick_grid.py
"""
import json
import logging
import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
CHILD = len(sys.argv) > 1 and sys.argv[1] == "--spx-child"
_TD = tempfile.mkdtemp(prefix="check_entry_tick_grid.")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"),
               ("OT_FEED_DB", "f.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_PLAN_STATES_FILE", "ps.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ.setdefault(_k, os.path.join(_TD, _v))
os.environ["OT_INSTRUMENT"] = "SPX" if CHILD else "QQQ"
FAILED = []

try:
    import config                                               # noqa: E402,F401
    from execution import entry_engine as EE                    # noqa: E402
    from execution import ladder_registry as LR                 # noqa: E402
    from execution import tick_size as TS                       # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

POSTED = []


class _Acct:
    def place_order(self, session, order, dry_run=False):
        POSTED.append(round(-float(order.price), 4))
        return SimpleNamespace(errors=[], order=SimpleNamespace(id="T"))


def _stub_broker():
    EE.get_session = lambda: object()
    EE.get_account = lambda: _Acct()
    EE.sdk_result = lambda r: r
    EE.Leg = lambda **kw: SimpleNamespace(**kw)
    EE.NewOrder = lambda **kw: SimpleNamespace(**kw)
    EE.confirm_order_fill = lambda *a, **k: SimpleNamespace(filled=False, net_price=None, working_order_id=None,
                                                            detail="stub: refused", order_id="", quantity=0)
    EE._guard.clear_to_post = lambda *a, **k: (True, "")
    EE._guard.after_failure = lambda *a, **k: None
    EE._guard.after_lost_post = lambda *a, **k: None
    EE._bp.affordable = lambda *a, **k: (True, "")
    EE.EntryEngine._page_if_working = staticmethod(lambda *a, **k: None)


def _signal(occ, bid, ask):
    return SimpleNamespace(contract=SimpleNamespace(symbol=occ, bid=bid, ask=ask),
                           entry_premium=round((bid + ask) / 2.0, 4), strategy_name="T", setup_type="t")


def _walk(occ, bid, ask, n):
    """Post n rungs through the REAL live entry path; every rung refused. Returns the prices posted."""
    LR.reset_all()
    POSTED.clear()
    live = EE.EntryEngine(paper_trading=False)
    sig = _signal(occ, bid, ask)
    for _ in range(n):
        live._place_single_leg(sig, 1)
    return list(POSTED)


def _rule(*pairs):
    return [SimpleNamespace(threshold=t, value=v) for t, v in pairs]


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def spx_child():
    """G5's half: OT_INSTRUMENT=SPX in this interpreter. Prints one JSON line."""
    _stub_broker()
    TS.cache_venue_rule("SPX", _rule((3.0, 0.05), (None, 0.10)))
    occ = "SPXW  261120C06000000"
    print(json.dumps({"hi": _walk(occ, 3.40, 3.80, 4), "lo": _walk(occ, 1.10, 1.30, 4)}))
    return 0


def main():
    print("check_entry_tick_grid")
    _stub_broker()
    warn = []

    class _Grab(logging.Handler):
        def emit(self, r):
            warn.append(r.getMessage())
    _tl = logging.getLogger("execution.tick_size")
    _tl.addHandler(_Grab())
    _tl.setLevel(logging.INFO)
    _tl.propagate = False

    TS.cache_venue_rule("QQQ", _rule((None, 0.01)))
    occ = "QQQ   261120C00600000"

    warn.clear()
    p = _walk(occ, 3.40, 3.50, 8)
    check("G1 QQQ 3.40/3.50 on the cached QQQ rule: the live entry posts 3.42, 3.43, 3.44, 3.45 and never above the "
          "mark 3.45",
          p[:4] == [3.42, 3.43, 3.44, 3.45] and all(x <= 3.45 + 1e-9 for x in p) and len(p) == 8,
          f"posted {p}")
    nv = [m for m in warn if "NO VENUE RULE" in m]
    check("G2 the entry walk never falls back to the PENNY_CLASSES guess (no 'NO VENUE RULE' line)", not nv,
          f"{nv[:1]}")

    LR.reset_all()
    POSTED.clear()
    EE.EntryEngine(paper_trading=False)._place_single_leg(_signal(occ, 3.40, 3.50), 1)
    keys = list(LR._WALKS.keys())
    check("G3 the walk key is still the contract's: intent_key(OCC, 'open', 'single') and nothing else",
          keys == [LR.intent_key(occ, "open", "single")], f"keys {keys}")

    p4 = _walk(occ, 1.23, 1.31, 3)
    check("G4 QQQ where the grid was already right (1.23/1.31 proves penny): 1.25, 1.26, 1.27, as rungs() gives on "
          "either symbol",
          p4 == [1.25, 1.26, 1.27] == EE_rungs(1.23, 1.31, "QQQ") == EE_rungs(1.23, 1.31, occ), f"posted {p4}")

    env = dict(os.environ)
    env["OT_INSTRUMENT"] = "SPX"
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--spx-child"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=240, stdin=subprocess.DEVNULL)
    try:
        got = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1])
    except Exception:                                           # noqa: BLE001
        got = {"err": (r.stdout[-300:] + r.stderr[-300:])}
    check("G5 SPX unchanged: 3.40/3.80 posts 3.50, 3.60 and 1.10/1.30 posts 1.15, 1.20 (the venue rule = the "
          "non-penny list)",
          got.get("hi", [])[:2] == [3.50, 3.60] and all(x <= 3.60 + 1e-9 for x in got.get("hi", []))
          and got.get("lo", [])[:2] == [1.15, 1.20] and all(x <= 1.20 + 1e-9 for x in got.get("lo", [])),
          f"{got}")

    try:
        from execution.exit_engine import ExitEngine
        LR.reset_all()
        xe = ExitEngine.__new__(ExitEngine)
        rec = {"trade_id": "tickgrid-0001", "symbol": "QQQ", "option_symbol": occ}
        sells = []
        for _ in range(5):
            px, _why = xe._exit_limit(rec, "target", 3.45, "sell", "single", quote=(3.40, 3.50))
            sells.append(round(px, 4))
            xe._exit_walk_refused(rec, px)
        ok6 = sells[:4] == [3.48, 3.47, 3.46, 3.45] and all(x >= 3.45 - 1e-9 for x in sells)
        d6 = f"sold {sells}"
    except Exception as exc:                                    # noqa: BLE001
        ok6, d6 = False, f"{type(exc).__name__}: {exc}"
    check("G6 exits unchanged: a QQQ single-leg close walks 3.48, 3.47, 3.46, 3.45 and never below the mark", ok6, d6)

    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — 6 of 6")
    return 0


def EE_rungs(b, a, sym):
    from execution.entry_ladder import rungs
    return rungs(b, a, "buy", sym)


if __name__ == "__main__":
    sys.exit(spx_child() if CHILD else main())
