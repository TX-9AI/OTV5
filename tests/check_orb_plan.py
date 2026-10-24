#!/usr/bin/env python3
"""
tests/check_orb_plan.py  v1.7
v1.7  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.6  2026-10-02  OTV4TEST r187 (ROSTER.1) — RE-POINTED BY THE RULING, NOT LOOSENED:
      the strategy is OFF by default from r187; this checker tests its LOGIC,
      so it switches it on for its own run (OT_ORB_TRADE=1). check_trade_switches pins the default.
v1.5  2026-10-02  OTV4TEST r185 (LADR.1) — P2, P3b and P8 RE-POINTED BY THE RULING,
      not deleted: the plan's target is the RAW 100% projection (709.19 /
      704.72), no longer pre-rounded on config.STRIKE_INCREMENT; the CONTRACT
      pinned is unchanged (709C / 705P). P4c's range moves to 706.40-707.70 so
      its target is exactly 709.00 and the 708/710 tie it names is still a tie
      (at 709.19 it passed on distance, not on the tie-break).
v1.4  2026-09-26  OTV4TEST r149 (EOD.1) — P7 and P16b RE-POINTED to the cutoff READ FROM CONFIG
      (ORB_NO_ENTRY_AFTER_ET, 15:40 by the operator's "extend the debit window to all day" /
      "Stop entries at 1540"), not a typed 11:30; the behaviour pinned is unchanged: AT the
      cutoff DORMANT, past it one dormant row then silence.
v1.3  2026-09-23  OTV4TEST r118 — P17: the prepared ORB row carries NO pitchfork
      anchor (operator: "nothing about the pitchfork needs to be addressed
      inside the ORB trade") while VWAP distance and the boundary's aggressor
      share are still stamped. Red on r117, which stamped tine_to_target,
      fork15 and the rail_* block. And the r106 venv bootstrap: under the
      lander's system python3 this died on pandas before printing a check.
v1.2  2026-09-13  OTV4TEST r20 — the `liq_map=None` kwarg dropped from every
      `ORBStrategy.generate_signal` call; nothing else changed. The parameter is
      REMOVED rather than ignored, so a harness still passing it raises — which
      is how mainline r365 found a live call site that three source-shape gates
      had missed, because this kind of check DRIVES the function.
v1.1  2026-09-08  OTV4TEST r3 — P10 drives the acceptance (close + hold): the runaway
      invalidation is a close, not a wick (orb_engine v4.13).
v1.0  2026-09-08  OTV4TEST r2 — THE ORB PLAN, ON HYPOTHETICALS (PLAN_SPEC §29).

Every case drives REAL code — `ORBPlan.prepare()`, `ORBStrategy.generate_signal()`,
`ORBEngine._check_for_break/_check_for_retest`, `ExitEngine._evaluate_orb` — on
hand-built ticks with a named shape. Nothing here is evidence about P&L; it
answers CAN IT FIRE, ON WHAT PLAN, AND IF NOT — WHICH BAR (the fork's
acceptance test, docs/FORK_BRIEF.md §5).

  P1   no opening range            -> NO PLAN, starved `opening_range`
  P2   range set, no candle yet    -> HOLD, BOTH sides priced, waiting on: impulsive candle
  P3   armed long                  -> HOLD PREPARED: stop = candle LOW, strike at +width,
                                      contract, floor, provisional size; waiting on: retest
  P4   confirmed long              -> ready, AND the contract == select_orb_strike's on
                                      the same chain (mechanism parity with e955020)
  P5   confirmation spent          -> DECLINE at `order_already_placed`, chain never read
  P6   no strike with a live quote -> DECLINE at `contract`: "NONE AVAILABLE"
  P7   at the cutoff (config; 15:40 since r149) -> DORMANT `entry_window`
  P8   the short mirror of P3/P4   -> stop = candle HIGH, put at -width
  P9   provisional size == RiskManager._size_geometry for the same inputs (C.23)
  P10  runaway invalidation        -> DECLINE `consequence` naming the hand-off
  P11  re-entry (close inside)     -> DECLINE `consequence` naming the fresh-candle wait
  P12  🔴 STALE RULE GONE: the real engine, armed 20 bars, CONFIRMS a 21st-bar retest
  P13  🔴 NO VELOCITY STALL ON ORB: stall forced to fire; ORB holds, the runaway exits
  P14  the strategy fires with the plan's variables, not its own
  P15  🔴 NO ATR FLOOR: a 0.01% ATR vol_state still fires
  P16  outside 09:35–15:40 (r149) the plan OBSERVES and does not write: one DORMANT
       row on the transition, silence after (operator 2026-09-08)
  P17  🔴 no pitchfork anchor on the prepared row (operator 2026-09-23, r118)

Born red at 910ad0e (OTV4TEST r1): P12 on the engine re-arming at bar 13, P13
on the stall exiting the ORB record, then P0 (`strategy.orb_plan` absent) —
the engine and exit cases run FIRST so the deletions are proven red on their
own, not hidden behind the missing module.

Run:  python3 tests/check_orb_plan.py
"""
import os as _os_r187
_os_r187.environ["OT_ORB_TRADE"] = "1"   # r187: test the strategy's logic switched on

import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


# ── fixtures built from the repo's own classes ──────────────────────────────
class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def commit(self):
        self.conn.commit()


def _frame(rows):
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
        index=pd.date_range("2026-09-08 09:35", periods=len(rows), freq="1min"))


def _engine_with_range(hi=707.70, lo=706.21):
    from analysis.orb_engine import ORBEngine, ORBState
    eng = ORBEngine()
    d = eng._data
    d.orb_high, d.orb_low, d.orb_width = hi, lo, round(hi - lo, 2)
    d.state = ORBState.WAITING_FOR_BREAK
    return eng


def _break(eng, direction):
    """Drive the REAL _check_for_break. Long: opens inside, closes above, wick
    low 707.10 (0.60 below the high). Short: wick high 706.81."""
    if direction == "long":
        eng._check_for_break(_frame([(706.90, 708.60, 707.10, 708.40),
                                     (708.40, 708.70, 708.30, 708.50)]))
    else:
        eng._check_for_break(_frame([(707.00, 706.81, 705.40, 705.60),
                                     (705.60, 705.70, 705.30, 705.50)]))
    return eng


def _retest(eng, direction):
    """Drive the REAL _check_for_retest with a qualifying bar (wick touches
    the boundary, body outside)."""
    if direction == "long":
        eng._check_for_retest(_frame([(707.90, 708.10, 707.65, 707.95),
                                      (707.95, 708.20, 707.90, 708.10)]))
    else:
        eng._check_for_retest(_frame([(705.90, 706.21, 705.80, 706.00),
                                      (706.00, 706.10, 705.90, 706.05)]))
    return eng


def _chain(strikes=(700, 702, 704, 705, 706, 707, 708, 709, 710, 712, 714),
           drop=()):
    from data.options_chain import OptionContract, OptionsChain
    ch = OptionsChain(underlying="TEST", expiry="2026-09-08", spot_price=707.0)
    ch.calls, ch.puts = [], []
    for k in strikes:
        if k in drop:
            continue
        # a plausible 0DTE ladder: premium and |delta| fall with distance
        cd = max(0.06, round(1.60 - 0.30 * abs(k - 707.0), 2))
        pdl = max(0.06, round(1.60 - 0.30 * abs(k - 707.0), 2))
        ch.calls.append(OptionContract(symbol=f"C{k}", strike=float(k), mark=cd,
                                       bid=cd - 0.02, ask=cd + 0.02,
                                       delta=max(0.05, 0.50 - 0.08 * (k - 707.0)),
                                       gamma=0.03, expiry="2026-09-08", option_type="C"))
        ch.puts.append(OptionContract(symbol=f"P{k}", strike=float(k), mark=pdl,
                                      bid=pdl - 0.02, ask=pdl + 0.02,
                                      delta=-max(0.05, 0.50 - 0.08 * (707.0 - k)),
                                      gamma=0.03, expiry="2026-09-08", option_type="P"))
    return ch


def _last_row(st):
    r = st.conn.execute("SELECT verdict, reason FROM plan_tick ORDER BY ts_epoch DESC, "
                        "rowid DESC LIMIT 1").fetchone()
    return (r["verdict"], r["reason"] or "") if r else ("", "")


def main():
    from strategy import plan as P
    st = _Store()
    P.ensure_tables(st)
    P.bind_store(st)

    # ── 🔴 P12 the stale rule is gone ─────────────────────────────────────
    from analysis.orb_engine import ORBState
    e10 = _break(_engine_with_range(), "long")
    for i in range(20):                       # twenty bars outside, no retest
        e10._check_for_retest(_frame([(708.30, 708.40, 708.20, 708.35),
                                      (708.35, 708.45, 708.25, 708.40)]).set_index(
            __import__("pandas").date_range(f"2026-09-08 09:{40 + i:02d}", periods=2, freq="1min")))
    still_armed = e10._data.state == ORBState.ARMED_LONG
    _retest(e10, "long")
    check("P12 🔴 armed 20 bars with no retest, the 21st-bar retest CONFIRMS (no stale re-arm)",
          still_armed and e10._data.state == ORBState.OPEN_LONG
          and e10._data.bars_since_break >= 20,
          f"after20={still_armed} final={e10._data.state} bars={e10._data.bars_since_break}")
    import config as _cfg
    check("P12b ORB_MAX_RETEST_BARS no longer exists in config",
          not hasattr(_cfg, "ORB_MAX_RETEST_BARS"))

    # ── 🔴 P13 no velocity stall on ORB ───────────────────────────────────
    import datetime as _dt
    from zoneinfo import ZoneInfo
    import execution.exit_engine as XE
    _real_dt = _dt.datetime
    ET = ZoneInfo("America/New_York")

    class _Frozen(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _real_dt(2026, 9, 8, 10, 30, tzinfo=ET)
    XE.datetime = _Frozen
    _real_hc = XE.is_hard_close_time
    XE.is_hard_close_time = lambda: False      # 10:30 ET, not the 15:45 flatten
    try:
        xe = XE.ExitEngine(paper_trading=True)
        xe._velocity_stall = lambda *a, **k: "velocity_stall FORCED"
        xe._theta_bleed = lambda *a, **k: False
        rec = {"trade_id": "p13-orb", "strategy": "ORBStrategy", "setup_type": "ORB Long",
               "direction": "long", "entry_premium": 1.00, "contracts": 1, "status": "open",
               "stop_premium": 0.75, "target_premium": 2.00, "trail_activation": 1.50,
               "underlying_stop": 0.0, "underlying_entry": 100.0}
        d_orb = xe._evaluate_orb(dict(rec), 0.95, None)
        d_run = xe._evaluate_orb(dict(rec, trade_id="p13-run",
                                      strategy="RunawayContinuation"), 0.95, None)
        check("P13 🔴 stall forced: the ORB record HOLDS, the runaway record still exits",
              (not d_orb.should_exit) and d_run.should_exit
              and "velocity_stall" in str(d_run.exit_reason),
              f"orb={d_orb.should_exit} run={d_run.should_exit}:{d_run.exit_reason}")
    finally:
        XE.datetime = _real_dt
        XE.is_hard_close_time = _real_hc

    # ── the plan module itself (everything below needs it) ───────────────
    try:
        from strategy.orb_plan import ORBPlan, provisional_size, MAX_LOSS_PCT
    except ImportError as exc:
        check("P0 strategy.orb_plan imports", False, str(exc))
        print(f"\nFAIL — {len(FAILED)} check(s): {FAILED}")
        return 1
    from analysis.orb_engine import ORBState

    def prep_for(eng, chain, now="09:36", offer=False, price=707.0):
        P.begin_tick()
        plan = ORBPlan()
        pr = plan.prepare(orb=eng._data, chain=chain, price_now=price,
                          now_hhmm=now, offer_working=offer)
        P.close_tick(st, "TEST")
        return pr

    # ── P1 no range ──────────────────────────────────────────────────────
    from analysis.orb_engine import ORBEngine
    e0 = ORBEngine()
    p1 = prep_for(e0, _chain())
    v, why = _last_row(st)
    check("P1 no opening range -> NO PLAN starved opening_range",
          v == "NO PLAN" and "opening_range" in why and "opening_range" in p1.starved,
          f"{v}: {why}")

    # ── P2 range, no candle -> both sides priced ─────────────────────────
    e1 = _engine_with_range()
    p2 = prep_for(e1, _chain())
    v, why = _last_row(st)
    lk, lc = p2.candidates.get("long", (None, None))
    sk, sc = p2.candidates.get("short", (None, None))
    check("P2 range set -> HOLD with BOTH candidates priced, waiting on impulsive candle",
          v == "HOLD" and "impulsive candle" in why and lc is not None and sc is not None
          and abs(lk - 709.19) < 1e-9 and abs(sk - 704.72) < 1e-9,
          f"{v}: {why[:120]} long={lk} short={sk}")
    check("P2b the long candidate is a CALL at +width and the short a PUT at -width",
          lc is not None and sc is not None and lc.option_type == "C"
          and sc.option_type == "P" and float(lc.strike) == 709.0 and float(sc.strike) == 705.0,
          f"{getattr(lc, 'strike', None)}{getattr(lc, 'option_type', '')} "
          f"{getattr(sc, 'strike', None)}{getattr(sc, 'option_type', '')}")

    # ── P3 armed long -> PREPARED ─────────────────────────────────────────
    e2 = _break(_engine_with_range(), "long")
    check("P3pre the real engine armed long off the impulsive candle",
          e2._data.state == ORBState.ARMED_LONG and e2._data.stop_level == 707.10)
    p3 = prep_for(e2, _chain())
    v, why = _last_row(st)
    check("P3 armed long -> HOLD PREPARED, waiting on: retest",
          v == "HOLD" and "PREPARED" in why and "Waiting on: retest" in why and not p3.ready,
          f"{v}: {why[:140]}")
    check("P3b stop = the impulsive candle's LOW; strike = high + width; floor = 75% premium",
          p3.stop == 707.10 and abs(p3.target_strike - 709.19) < 1e-9
          and p3.contract is not None and float(p3.contract.strike) == 709.0
          and abs(p3.floor_premium - round(p3.premium * (1 - MAX_LOSS_PCT), 4)) < 1e-9,
          f"stop={p3.stop} strike={p3.target_strike} prem={p3.premium} floor={p3.floor_premium}")
    check("P3c provisional size = floor(width / boundary-to-stop) = floor(1.49/0.60) = 2",
          p3.size_provisional == 2, f"size={p3.size_provisional}")
    # 🔴 P17 (r118) — no pitchfork anchor on the ORB's prepared row
    _anch = {r[0] for r in st.conn.execute(
        "SELECT DISTINCT check_name FROM plan_check WHERE strategy='ORBStrategy' "
        "AND check_name LIKE 'anchor_%'")}
    _fork = sorted(a for a in _anch if "tine" in a or "fork" in a or a.startswith("anchor_rail_"))
    check("P17 🔴 the prepared ORB row stamps no pitchfork anchor; VWAP and aggressor stay",
          not _fork and {"anchor_vwap_minus_price", "anchor_aggressor_at_boundary"} <= _anch,
          f"fork anchors {_fork}; all anchors {sorted(_anch)}")

    # ── P4 confirmed long -> ready, parity with select_orb_strike ─────────
    e3 = _retest(_break(_engine_with_range(), "long"), "long")
    check("P4pre the real engine confirmed the retest",
          e3._data.state == ORBState.OPEN_LONG and e3._data.confirmation_seq == 1)
    ch = _chain()
    p4 = prep_for(e3, ch)
    check("P4 confirmed long -> every bar clears, ready for the strategy",
          p4.ready and not p4.structural and not p4.starved and p4.contract is not None,
          f"ready={p4.ready} structural={p4.structural} starved={p4.starved}")
    # mechanism parity: the same chain, the same target, the e955020 selector
    import data.options_chain as OC
    fetcher = OC.OptionsChainFetcher.__new__(OC.OptionsChainFetcher)
    legacy = fetcher.select_orb_strike(ch, "long", e3._data.target_strike)
    check("P4b PARITY — the plan's contract is the one select_orb_strike picks on the same chain",
          legacy is not None and p4.contract is legacy,
          f"plan={getattr(p4.contract, 'strike', None)} legacy={getattr(legacy, 'strike', None)}")
    # and the tie-break: two equidistant strikes, lower |delta| wins (carried rule)
    ch_tie = _chain(strikes=(708, 710))         # target 709 sits between them
    e3b = _retest(_break(_engine_with_range(lo=706.40), "long"), "long")  # target 709.00
    p4b = prep_for(e3b, ch_tie)
    legacy_tie = fetcher.select_orb_strike(ch_tie, "long", e3b._data.target_strike)
    check("P4c PARITY on the equidistant tie-break too",
          p4b.contract is legacy_tie and float(p4b.contract.strike) == 710.0,
          f"plan={getattr(p4b.contract, 'strike', None)} legacy={getattr(legacy_tie, 'strike', None)}")

    # ── P5 spent confirmation, chain never needed ────────────────────────
    e4 = _retest(_break(_engine_with_range(), "long"), "long")
    e4._data.order_placed = True
    e4._data.order_placed_seq = e4._data.confirmation_seq
    p5 = prep_for(e4, None)                      # chain=None on purpose
    v, why = _last_row(st)
    check("P5 spent confirmation -> DECLINE at order_already_placed, before any chain read",
          v == "DECLINE" and why.startswith("order_already_placed") and not p5.ready,
          f"{v}: {why[:100]}")

    # ── P6 none available ────────────────────────────────────────────────
    e5 = _break(_engine_with_range(), "long")
    # "nearest listed" always finds SOMETHING if any call is quoted, so NONE
    # AVAILABLE is a chain with no quoted calls at all
    ch_none = _chain(strikes=(705, 706, 707))
    ch_none.calls = []
    prep_for(e5, ch_none)
    v, why = _last_row(st)
    check("P6 no call with a live quote -> DECLINE at contract: NONE AVAILABLE",
          v == "DECLINE" and why.startswith("contract") and "NONE AVAILABLE" in why,
          f"{v}: {why[:100]}")

    # ── P7 past the cutoff ───────────────────────────────────────────────
    import config as _c7
    _co = tuple(_c7.ORB_NO_ENTRY_AFTER_ET)
    _hm = lambda m: f"{m // 60:02d}:{m % 60:02d}"
    _com = _co[0] * 60 + _co[1]
    e6 = _break(_engine_with_range(), "long")
    p7 = prep_for(e6, _chain(), now=_hm(_com))
    v, why = _last_row(st)
    check(f"P7 {_hm(_com)} (the cutoff) -> DORMANT entry_window, nothing prepared",
          v == "DORMANT" and "entry_window" in why and p7.contract is None,
          f"{v}: {why[:80]}")

    # ── P8 short mirror ──────────────────────────────────────────────────
    e7 = _retest(_break(_engine_with_range(), "short"), "short")
    p8 = prep_for(e7, _chain())
    check("P8 short: stop = the impulsive candle's HIGH (706.81); put at low - width (705); ready",
          p8.ready and p8.stop == 706.81 and p8.side == "put"
          and abs(p8.target_strike - 704.72) < 1e-9
          and float(p8.contract.strike) == 705.0 and p8.contract.option_type == "P",
          f"ready={p8.ready} stop={p8.stop} strike={p8.target_strike}")

    # ── P9 sizing parity with the real sizer (C.23) ──────────────────────
    from risk.risk_manager import RiskManager
    rm = RiskManager()
    cases = [(1.49, 0.60, 1.00), (6.35, 0.61, 2.00), (6.35, 6.05, 2.00), (1.49, 1.49, 0.50),
             (6.35, 0.10, 0.80)]
    mism = []
    for w, d, prem in cases:
        real = rm._size_geometry(prem, w, d, budget_usd=None).contracts
        mine = provisional_size(w, d, prem)
        if real != mine:
            mism.append((w, d, prem, real, mine))
    check("P9 provisional_size == RiskManager._size_geometry on every case incl. the budget bind",
          not mism, f"mismatches={mism}")
    check("P9b degenerate geometry (stop beyond the width) sizes 1, like the sizer",
          provisional_size(1.49, 2.00, 1.00) == 1
          and rm._size_geometry(1.00, 1.49, 2.00).contracts == 1)

    # ── P10 / P11 consequences ───────────────────────────────────────────
    e8 = _break(_engine_with_range(), "long")
    # OTV4TEST r3: the runaway invalidation is a CLOSE beyond the 50 (708.445)
    # that HOLDS — two closed bars — not a wick. Drive update()'s order.
    for rows in ([(708.50, 708.60, 708.30, 708.55), (708.55, 708.70, 708.40, 708.60)],
                 [(708.55, 708.70, 708.40, 708.60), (708.60, 708.75, 708.45, 708.65)]):
        e8._track_fifty_acceptance(_frame(rows))
        e8._check_for_retest(_frame(rows))
    check("P10pre the real engine invalidated on runaway",
          e8._data.state == ORBState.INVALIDATED and e8._data.invalidation_reason == "runaway")
    p10 = prep_for(e8, _chain())
    v, why = _last_row(st)
    check("P10 runaway -> DECLINE consequence: hand-off named",
          v == "DECLINE" and why.startswith("consequence") and "RUNAWAY" in why
          and p10.consequence == "runaway", f"{v}: {why[:100]}")
    e9 = _break(_engine_with_range(), "long")
    e9._check_for_retest(_frame([(707.90, 708.00, 707.30, 707.50),      # closes back inside
                                 (707.50, 707.60, 707.40, 707.45)]))
    check("P11pre the real engine invalidated on close_inside",
          e9._data.state == ORBState.INVALIDATED and e9._data.invalidation_reason == "close_inside")
    prep_for(e9, _chain())
    v, why = _last_row(st)
    check("P11 re-entry -> DECLINE consequence: fresh impulsive candle named",
          v == "DECLINE" and "RE-ENTRY" in why and "fresh" in why, f"{v}: {why[:100]}")

    # ── P14 the strategy fires with the plan's variables ─────────────────
    from strategy.orb_strategy import ORBStrategy
    e11 = _retest(_break(_engine_with_range(), "long"), "long")
    ch14 = _chain()
    P.begin_tick()
    strat = ORBStrategy()
    sig = strat.generate_signal(orb=e11._data, ms=None, vol_state=None,
                                chain=ch14, macro=None, current_price=707.95,
                                now_hhmm="09:48")
    P.close_tick(st, "TEST")
    v, why = _last_row(st)
    check("P14 confirmed + unspent -> the strategy FIRES (TAKE row)",
          sig is not None and v == "TAKE", f"sig={sig is not None} row={v}: {why[:80]}")
    check("P14b the signal carries the plan's stop, strike, premium and 100%/50% levels",
          sig is not None and sig.underlying_stop == 707.10 and sig.strike == 709.0
          and abs(sig.entry_premium - 1.00) < 1e-9 and sig.underlying_target == e11._data.target_100pct
          and sig.underlying_tp50 == e11._data.target_50pct and sig.contract is not None,
          f"stop={getattr(sig, 'underlying_stop', None)} strike={getattr(sig, 'strike', None)} "
          f"prem={getattr(sig, 'entry_premium', None)}")
    # one confirmation, one order: mark it placed, ask again
    e11._data.order_placed = True
    e11._data.order_placed_seq = e11._data.confirmation_seq
    P.begin_tick()
    sig2 = strat.generate_signal(orb=e11._data, ms=None, vol_state=None,
                                 chain=ch14, macro=None, current_price=707.95,
                                 now_hhmm="09:48")
    P.close_tick(st, "TEST")
    check("P14c the tick after an order on the same confirmation does NOT fire again",
          sig2 is None and _last_row(st)[1].startswith("order_already_placed"))

    # ── 🔴 P15 no ATR floor ───────────────────────────────────────────────
    class _Vol:
        atr = 0.07
        atr_pct = 0.01          # would have been refused at r1 (floor 0.05%)
        atr_normalized = 0.0001
        price_vs_vwap = "ABOVE"
    e12 = _retest(_break(_engine_with_range(), "long"), "long")
    P.begin_tick()
    sig3 = ORBStrategy().generate_signal(orb=e12._data, ms=None, vol_state=_Vol(),
                                         chain=_chain(), macro=None,
                                         current_price=707.95, now_hhmm="09:48")
    P.close_tick(st, "TEST")
    check("P15 🔴 a 0.01% ATR session still fires — ORB has no ATR read",
          sig3 is not None and _last_row(st)[0] == "TAKE",
          f"sig={sig3 is not None} row={_last_row(st)}")
    import strategy.orb_strategy as OS
    check("P15b ORB_ATR_FLOOR_PCT is not defined on the strategy module",
          not hasattr(OS, "ORB_ATR_FLOOR_PCT"))

    # ── P16 outside the window: OBSERVE ONLY, DON'T WRITE ─────────────────
    # Operator, 2026-09-08. One row on the transition, then nothing.
    def rows():
        return st.conn.execute("SELECT COUNT(*) FROM plan_tick WHERE strategy='ORBStrategy'").fetchone()[0]
    P.clear_dormant("ORBStrategy")
    e13 = _break(_engine_with_range(), "long")
    n0 = rows()
    prep_for(e13, _chain(), now="09:31")            # before 09:35: forming
    n1 = rows()
    prep_for(e13, _chain(), now="09:32")
    prep_for(e13, _chain(), now="09:33")
    n2 = rows()
    check("P16 before 09:35 -> ONE dormant row, then silence on identical ticks",
          n1 == n0 + 1 and n2 == n1 and _last_row(st)[0] == "DORMANT",
          f"rows {n0}->{n1}->{n2} last={_last_row(st)}")
    prep_for(e13, _chain(), now="09:36")             # inside: it speaks
    n3 = rows()
    prep_for(e13, _chain(), now=_hm(_com + 1))       # past the cutoff (r149: read from config)
    n4 = rows()
    prep_for(e13, _chain(), now=_hm(_com + 2))
    prep_for(e13, _chain(), now=_hm(_com + 10))
    n5 = rows()
    check(f"P16b inside the window it writes; past {_hm(_com)} one dormant row, then silence",
          n3 == n2 + 1 and n4 == n3 + 1 and n5 == n4,
          f"rows {n2}->{n3}->{n4}->{n5}")

    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("PASS — check_orb_plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
