#!/usr/bin/env python3
"""
tests/check_lock_mark.py  v5.0
v5.0  2026-11-21  OTV5 r137 (LOCK.1) — EVERY PROFIT LOCK, TRAIL AND PEAK DECIDES ON THE MARK. The operator, 2026-11-21:
      "any profit locks need to be on mark" (2026-11-19: "Mark is the worst buy or sell we accept."). At r136 PARK's
      +60% / +20% lock (exit_engine._evaluate_park) armed and exited on the r105 bid stash (_exit_bid); OGAP's walk was
      converted at r136; every other exit read the tick's mark (current_premium). This gate drives the REAL
      ExitEngine.evaluate (and the REAL ManagementPlan.decide for the strategies it covers) on scratch stores:

  L1  PARK, mark vs bid disagree on the way up: mark 1.60 (bid 1.40) ARMS the lock (entry 1.00); armed, mark 1.21 (bid
      1.05, under the 1.20 floor) HOLDS; mark 1.20 (bid 1.20) exits "park_lock: mark 1.20 ..."
  L2  PARK, the bid alone never arms: mark 1.59 with no ask/bid stash, then mark 1.59 with bid 1.59: no arm; mark 1.10 holds
  L3  BID INDEPENDENCE, every live-lineup route (PARK, OGAP, RunawayContinuation, LiquidityHunt) and Breakout (paper):
      the same mark path (1.00 up to 2.10, back to 0.70) gives tick-for-tick the same (should_exit, exit_reason) through
      evaluate() with no stash and with a bid 0.25 under / an ask 0.25 over every mark; PARK's path closes on park_lock
      (not vacuous)
  L4  the same through ManagementPlan.decide (RunawayContinuation, LiquidityHunt, Breakout): action and reason identical
      with and without the stash
  L5  the park_exit counterfactual row says basis "mark", carries the deciding mark and the tick bid beside it
  L6  SOURCE: in exit_engine's decision functions and management's decide, _exit_bid / _exit_ask / _exit_quote /
      _fresh_quote appear only where the bid is RECORDED (_evaluate_park / _evaluate_ogap pass `bid` to their *_cf
      row and nowhere else; management's _record_delta_floor row)
Born red on 4b6f22f (r136) at L1, L3, L5, L6 (L2 and L4 are guards: green on both).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_lock_mark.py
"""
import ast
import inspect
import json
import os
import shutil
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_lock_mark_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
os.environ["OT_FEED_DB"] = os.path.join(_TD, "f.db")
os.environ["OT_LOG_FILE"] = os.path.join(_TD, "bot.log")
os.environ["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(_TD, "sj")
CF = os.path.join(_TD, "cf")
os.environ["OT_COUNTERFACTUAL_DIR"] = CF
ET = ZoneInfo("America/New_York")
FAILED = []
PATH = [1.00, 1.30, 1.62, 1.90, 2.10, 1.80, 1.50, 1.25, 1.21, 1.19, 1.10, 0.95, 0.70]


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {str(detail)[:600]}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    print("check_lock_mark")
    try:
        import pandas  # noqa: F401
        import execution.exit_engine as XE
        from strategy import management as MG
        import utils.time_utils as TU
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2

    # ── the clock: 12:00 ET + one minute per tick, in every module that holds the real now_et / now_utc ──
    _clock = {"t": datetime(2026, 11, 5, 12, 0, 0, tzinfo=ET)}
    _real_dt = XE.datetime

    class _D(_real_dt):
        @classmethod
        def now(cls, tz=None):
            t = _clock["t"]
            return t if tz is None else t.astimezone(tz)
    real = {"now_et": TU.now_et, "now_utc": TU.now_utc}
    fake = {"now_et": lambda: _clock["t"], "now_utc": lambda: _clock["t"].astimezone(timezone.utc)}
    sw = [(m, n) for m in list(sys.modules.values()) for n in real if m is not None and getattr(m, n, None) is real[n]]
    for m, n in sw:
        setattr(m, n, fake[n])
    XE.datetime = _D

    def at(i):
        _clock["t"] = datetime(2026, 11, 5, 12, i % 60, 0, tzinfo=ET)

    def rec(tid, strategy, **kw):
        r = {"trade_id": tid, "strategy": strategy, "symbol": "QQQ", "direction": "long", "option_side": "call",
             "entry_premium": 1.0, "contracts": 2, "stop_premium": 0.0, "current_delta": 0.5,
             "target_premium": 2.0, "trail_activation": 1.5, "underlying_stop": 0.0,
             "entry_time": "2026-11-05T15:30:00+00:00", "option_symbol": f"X-{tid}", "is_butterfly": 0}
        if strategy in ("RunawayContinuation", "LiquidityHunt", "Breakout"):
            r["stop_premium"] = 0.75
        r.update(kw)
        return r

    def stash(r, bid, ask):
        if bid is None:
            r.pop("_exit_bid", None)
            r.pop("_exit_ask", None)
        else:
            r["_exit_bid"], r["_exit_ask"] = bid, ask

    try:
        # ── L1 ──
        eng = XE.ExitEngine(paper_trading=True)
        r1 = rec("l1", "PARK")
        out = []
        for i, (m, b) in enumerate([(1.30, 1.10), (1.60, 1.40), (1.21, 1.05), (1.20, 1.20)]):
            at(i)
            stash(r1, b, m + (m - b))
            d = eng.evaluate(r1, m)
            out.append((d.should_exit, d.exit_reason, bool(r1.get("_park_armed"))))
        check("L1 PARK: mark 1.60 (bid 1.40) arms; armed, mark 1.21 (bid 1.05) holds; mark 1.20 exits park_lock: mark",
              [o[0] for o in out] == [False, False, False, True] and out[1][2] is True
              and str(out[3][1]).startswith("park_lock: mark 1.20"), out)

        # ── L2 ──
        r2 = rec("l2", "PARK")
        o2 = []
        for i, (m, b) in enumerate([(1.59, None), (1.59, 1.59), (1.10, 1.05)]):
            at(i)
            stash(r2, b, None if b is None else m + 0.01)
            d = eng.evaluate(r2, m)
            o2.append((d.should_exit, d.exit_reason, bool(r2.get("_park_armed"))))
        check("L2 PARK: mark 1.59 never arms (stash or not); mark 1.10 holds", all(o == (False, "", False) for o in o2), o2)

        # ── L3 bid independence, through evaluate() ──
        os.environ["OT_DECAY_STOP"] = os.environ.get("OT_DECAY_STOP", "1")
        seqs, park_reason = {}, ""
        for strat in ("PARK", "OGAP", "RunawayContinuation", "LiquidityHunt", "Breakout"):
            both = []
            for with_bid in (False, True):
                e = XE.ExitEngine(paper_trading=True)
                r = rec(f"l3-{strat}-{int(with_bid)}", strat)
                s = []
                for i, m in enumerate(PATH):
                    at(i)
                    stash(r, max(0.01, round(m - 0.25, 2)) if with_bid else None, round(m + 0.25, 2) if with_bid else None)
                    d = e.evaluate(r, m)
                    s.append((bool(d.should_exit), str(d.exit_reason or "")))
                    if d.should_exit:
                        break
                both.append(s)
            seqs[strat] = both
            if strat == "PARK":
                park_reason = both[1][-1][1] if both[1] else ""
        diff = {k: v for k, v in seqs.items() if v[0] != v[1]}
        check("L3 bid independence through evaluate(): PARK, OGAP, Runaway, Hunt, Breakout decide the same with and "
              "without a bid/ask stash; PARK closes on park_lock",
              not diff and park_reason.startswith("park_lock"), diff or seqs.get("PARK"))

        # ── L4 through ManagementPlan.decide ──
        l4 = {}
        for strat in ("RunawayContinuation", "LiquidityHunt", "Breakout"):
            both = []
            for with_bid in (False, True):
                e = XE.ExitEngine(paper_trading=True)
                mp = MG.ManagementPlan()
                r = rec(f"l4-{strat}-{int(with_bid)}", strat)
                s = []
                for i, m in enumerate(PATH):
                    at(i)
                    stash(r, max(0.01, round(m - 0.25, 2)) if with_bid else None, round(m + 0.25, 2) if with_bid else None)
                    r["current_premium"] = m
                    it = mp.decide(r, m, exit_engine=e, open_records=[r])
                    s.append(None if it is None else (it.action, it.reason))
                    if it is not None and it.action == "CLOSE":
                        break
                both.append(s)
            l4[strat] = both
        d4 = {k: v for k, v in l4.items() if v[0] != v[1]}
        covered = all(any(x is not None for x in v[0]) for k, v in l4.items() if MG.covers({"strategy": k}))
        check("L4 bid independence through ManagementPlan.decide (Runaway, Hunt, Breakout)", not d4 and covered, d4 or l4)

        # ── L5 the counterfactual row ──
        fx = os.path.join(CF, "park_exit.jsonl")
        rows = [json.loads(x) for x in open(fx)] if os.path.exists(fx) else []
        rl = [x for x in rows if x.get("trade_id") == "l1"]
        check("L5 park_exit row: basis mark, the deciding mark 1.20, the tick bid 1.20 beside it",
              len(rl) == 1 and rl[0].get("basis") == "mark" and rl[0].get("mark") == 1.20 and rl[0].get("bid") == 1.20, rl)
    finally:
        XE.datetime = _real_dt
        for m, n in sw:
            setattr(m, n, real[n])

    # ── L6 source ──
    QUOTE = ("_exit_bid", "_exit_ask", "_exit_quote", "_fresh_quote")
    decision_fns = ["evaluate", "_evaluate_route", "_evaluate_orb", "_evaluate_sweep", "_evaluate_adopted",
                    "_update_trail", "_update_post_target_trail", "_update_fvg_trail", "_theta_bleed",
                    "_runaway_thesis_exits", "_final_form_floor", "_breakout_trail_gate", "trail_armed",
                    "_decay_read", "_park_late_read", "_hunt_at_target", "_rejected_handoff", "_seed_trail_from_record"]
    bad = []
    for n in decision_fns:
        fn = getattr(XE.ExitEngine, n, None)
        if fn is None:
            continue
        src = inspect.getsource(fn)
        bad += [f"ExitEngine.{n}: {q}" for q in QUOTE if q in src]
    for fn in (XE.ogap_exit_step, XE._gain_floor, XE.breakout_trail_arm, XE._track_excursion, MG.ManagementPlan.decide):
        src = inspect.getsource(fn)
        bad += [f"{fn.__qualname__}: {q}" for q in QUOTE if q in src]

    def bid_only_to_cf(fn, cf_name):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        ok_ids = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == cf_name:
                ok_ids |= {id(a) for a in node.args}
        loads = [nd for nd in ast.walk(tree) if isinstance(nd, ast.Name) and nd.id == "bid"
                 and isinstance(nd.ctx, ast.Load)]
        stores = [nd for nd in ast.walk(tree) if isinstance(nd, ast.Name) and nd.id == "bid"
                  and isinstance(nd.ctx, ast.Store)]
        return bool(loads) and all(id(nd) in ok_ids for nd in loads) and len(stores) == 1
    for fn, cf in ((XE.ExitEngine._evaluate_park, "_park_cf"), (XE.ExitEngine._evaluate_ogap, "_ogap_cf")):
        if not bid_only_to_cf(fn, cf):
            bad.append(f"{fn.__name__}: the bid is read for more than its {cf} row")
    check("L6 source: no decision function reads the bid/ask stash; PARK / OGAP read it only into their *_cf row",
          not bad, bad)

    if FAILED:
        print(f"\nRED — {len(FAILED)} of 6 failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — every profit lock, trail and peak decides on the mark (L1-L6)")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        if _TD.startswith(tempfile.gettempdir()) and os.path.basename(_TD).startswith("check_lock_mark_"):
            shutil.rmtree(_TD, ignore_errors=True)
    sys.exit(rc)
