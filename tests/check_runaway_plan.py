#!/usr/bin/env python3
"""
tests/check_runaway_plan.py  v5.1
v5.1  2026-10-26  OTV5 r38 (HYG.18) — scratch no longer names dir="/var/tmp": mkdtemp honours TMPDIR, which boot_sweep and land.sh point
      at a per-run dir they remove (HYG.14), so a sweep leaves nothing behind (237 dirs had piled up on SOFI). No check changed.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.6  CD.2 (2026-10-24) - X1's seeded REJECTED row carries bar_close_epoch (the judging bar's close): latest_rejection
      judges by market time now (derived_store v4.9) and never serves a row without one. Expectations unchanged.
v1.5  2026-10-14  OTV4TEST r285 (HUNT.8) - OT_COUNTERFACTUAL_DIR is set to a scratch directory before any project
      import: this file drives the exit engine with LiquidityHunt records, and r285's _hunt_cf would otherwise
      write fixture rows into the repo's data/counterfactual/hunt_stop.jsonl - the LIVE log when the boot sweep
      runs in the live tree. No check changed.
v1.4  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.3  2026-10-03  OTV4TEST r209 (RUN.10) — X2 INVERTED BY RULING. It pinned the engine HOLDING a Runaway at its 20% floor
      (r3). The management plan has closed Runaways at that floor since r168, so the hold was dead code; the
      10-03 replay of the 9 stopped trades said holding cost 499 more and none recovered; the operator:
      "runaway, concur". X2 now requires the stop, and X2b that the HUNT still holds.
v1.2  2026-09-26  OTV4TEST r149 (EOD.1) — R9 RE-POINTED: "past the cutoff" is read from the plan's
      own _cutoff_hm() (15:40 by the operator's all-day debit window), not a typed 11:31/11:32/13:00.
v1.1  2026-09-13  OTV4TEST r24 — R7/R8 RE-DERIVED ON THE BOOKS, R14-R18 ADDED. One-per-break
      and re-validation are read from trades.db and the closed bars since that
      exit, so R7 writes a REAL closed runaway row instead of calling the deleted
      `finish_break`, and R8 walks ONE continuous frame (lost, beyond, beyond)
      instead of three disconnected ticks carried by a counter. R14/R15 (09-09
      T5 and 09-11 T6 shapes) a latched 50 that is not held now does not enter;
      R16 a FRESH plan instance — a restart — still sees the finished break;
      R17 an unreadable book fails closed; R18 the run is signed.
v1.0  2026-09-08  OTV4TEST r3 — THE RUNAWAY PLAN AND ITS EXITS, ON HYPOTHETICALS
      (PLAN_SPEC §30). Real engine, real plan, real strategy, real exit engine.

  R1   🔴 a WICK to the 50 does not invalidate the ORB (v4.13) — ORB stands
  R2   🔴 a close beyond the 50 that holds invalidates it AND sets fifty_accepted
  R3   plan before acceptance -> HOLD "waiting on: the 50 ACCEPTED"
  R4   at acceptance -> strength measured (pace, acceptance), FROZEN, band set,
       contract picked inside the band, ready; the row carries it all
  R5   a rip (2 bars to the 50) gets a wider band than a grind (10 bars) on the
       same chain — and the frozen reading does not change on the next tick
  R6   the strategy fires with the plan's variables (tp50, band, strength on it)
  R7   break finished (any exit) -> HOLD naming re-validation; the standing
       state does NOT re-fire
  R8   re-validation on actual: the 50 lost on a close, then accepted on two
       closes -> the break trades again with a FRESH measurement
  R9   past the cutoff (15:40 since r149) -> DORMANT; before 09:35 -> DORMANT; one row each, then silence
  X1   🔴 REJECTED handoff: a pool above the entry rejected on close -> exit,
       for a RUNAWAY record and for an ORB record
  X2   🔴 runaway: premium at the old 20% floor with price still beyond the 50
       -> HELD, would-have-floored recorded
  X3   runaway: a 1m close back through the 50 -> thesis dead
  X4   runaway: fizzle — higher-low broken + range contraction -> exit
  X5   runaway: a close through the ORB boundary -> backstop
  X6   ORB record: the 25% floor still fires (nothing about ORB's own list moved)

Born red at OTV4TEST r2: R1/R2 (wick invalidation), R4-R8 (`strategy.runaway_plan`
absent), X1 (no handoff), X2 (the floor fires).
Run:  python3 tests/check_runaway_plan.py
"""
import os
import sqlite3
import sys
import tempfile
os.environ.setdefault("OT_COUNTERFACTUAL_DIR", tempfile.mkdtemp(prefix="cf_"))   # r285: never the live log

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def commit(self):
        self.conn.commit()


def _frame(rows, start="09:36"):
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
        index=pd.date_range(f"2026-09-08 {start}", periods=len(rows), freq="1min"))


def _engine():
    from analysis.orb_engine import ORBEngine, ORBState
    e = ORBEngine()
    d = e._data
    d.orb_high, d.orb_low, d.orb_width = 101.0, 100.0, 1.0      # 50% long = 101.5
    d.state = ORBState.WAITING_FOR_BREAK
    return e


def _break_long(e):
    e._check_for_break(_frame([(100.6, 101.3, 100.5, 101.2), (101.2, 101.4, 101.1, 101.3)]))
    return e


def _drive(e, rows):
    """One engine tick on a frame whose closed bar is rows[-2]: the real update
    order (acceptance BEFORE the retest read)."""
    df = _frame(rows)
    e._track_fifty_acceptance(df)
    e._check_for_retest(df)
    return df


def _rip_frame():
    # two bars from the candle to the 50: closes at the highs, big displacement
    return _frame([(100.6, 101.3, 100.5, 101.2), (101.2, 101.7, 101.15, 101.65),
                   (101.65, 101.9, 101.6, 101.85), (101.85, 101.95, 101.8, 101.9)])


def _grind_frame():
    rows = [(100.6, 101.3, 100.5, 101.2)]
    px = 101.2
    for i in range(9):                    # ten bars creeping, closes mid-bar
        px += 0.05
        rows.append((px - 0.05, px + 0.12, px - 0.15, px))
    rows.append((px, px + 0.1, px - 0.1, px + 0.02))
    return _frame(rows)


class _G:
    def __init__(self, k, prem, delta, gamma):
        self.strike, self.mark, self.ask, self.bid = float(k), prem, prem + 0.02, prem - 0.02
        self.delta, self.gamma, self.theta = delta, gamma, -0.04
        self.expiry, self.open_interest, self.symbol, self.option_type = "x", 100, f"C{k}", "C"


class _Chain:
    def __init__(self, calls):
        self.calls, self.puts = calls, []


def _calls():
    return [_G(102, 0.95, 0.46, 0.050), _G(103, 0.48, 0.30, 0.058), _G(104, 0.20, 0.17, 0.040),
            _G(105, 0.12, 0.09, 0.022)]


def _last_row(st):
    r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='RunawayContinuation' "
                        "ORDER BY ts_epoch DESC, rowid DESC LIMIT 1").fetchone()
    return (r["verdict"], r["reason"] or "") if r else ("", "")


def main():
    from strategy import plan as P
    st = _Store()
    P.ensure_tables(st)
    P.bind_store(st)
    os.environ["OT_RELAXED_ENTRY"] = "1"          # R muteable; selection is the point
    from analysis.orb_engine import ORBState

    # ── R1 / R2: the invalidation is a close ────────────────────────────
    e = _break_long(_engine())
    _drive(e, [(101.3, 101.8, 101.2, 101.4), (101.4, 101.5, 101.3, 101.45)])   # wick to 101.8
    check("R1 🔴 a WICK to the 50 does not invalidate the ORB",
          e._data.state == ORBState.ARMED_LONG and not e._data.fifty_accepted,
          f"state={e._data.state}")
    _drive(e, [(101.4, 101.7, 101.3, 101.6), (101.6, 101.8, 101.5, 101.7)])    # close beyond
    _drive(e, [(101.6, 101.8, 101.5, 101.7), (101.7, 101.9, 101.6, 101.8)])    # held
    check("R2 🔴 a close beyond the 50, held -> INVALIDATED runaway with fifty_accepted",
          e._data.state == ORBState.INVALIDATED and e._data.invalidation_reason == "runaway"
          and e._data.fifty_accepted, f"state={e._data.state} acc={e._data.fifty_accepted}")

    # ── the plan ─────────────────────────────────────────────────────────
    try:
        from strategy.runaway_plan import RunawayPlan, BAND_RIP, BAND_GRIND, BAND_NORMAL
    except ImportError as exc:
        check("R0 strategy.runaway_plan imports", False, str(exc))
        print(f"\nFAIL — {len(FAILED)} check(s): {FAILED}")
        return 1
    import strategy.runaway_continuation as RC

    # ── r24: a TEMP trade book for this check's life ─────────────────────
    # One-per-break and the spent lock are READ from trades.db now (DEC.1), so
    # the fixtures are real closed rows in a real TradeLogger's table — and the
    # book is scratch, so nothing here can read or write the box's (r13).
    import tempfile as _tfb
    import database.trade_logger as _TLB

    def _bind_book():
        _TLB._trade_logger = _TLB.TradeLogger(os.path.join(_tfb.mkdtemp(), "book.db"))
        return _TLB._trade_logger

    def _book_row(**kv):
        c = _TLB.get_trade_logger()._connect()
        try:
            c.execute(f"INSERT INTO trades ({','.join(kv)}) VALUES ({','.join('?' * len(kv))})",
                      tuple(kv.values()))
            c.commit()
        finally:
            c.close()

    def _now_iso(minutes_ago=0):
        from datetime import datetime, timedelta, timezone
        return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()

    _bind_book()

    def prep_for(plan, orb, df, now="10:05", price=101.85, chain=None):
        P.begin_tick()
        pr = plan.prepare(orb=orb, atr_pct=0.14, price_now=price, now_et=now,
                          chain=chain if chain is not None else _Chain(_calls()), df_1m=df)
        P.close_tick(st, "TEST")
        return pr

    plan = RunawayPlan()
    e3 = _break_long(_engine())
    p3 = prep_for(plan, e3._data, _frame([(100.6, 101.3, 100.5, 101.2), (101.2, 101.4, 101.1, 101.3)]))
    v, why = _last_row(st)
    check("R3 before acceptance -> HOLD waiting on the 50 ACCEPTED",
          v == "HOLD" and "50 ACCEPTED" in why and not p3.ready, f"{v}: {why[:90]}")

    e4 = _break_long(_engine())
    e4._data.bars_since_break = 2
    e4._data.fifty_accepted = True
    p4 = prep_for(plan, e4._data, _rip_frame())
    v, why = _last_row(st)
    check("R4 at acceptance -> strength measured and frozen, band set, contract inside it, ready",
          p4.ready and p4.strength is not None and p4.pace is not None
          and p4.acceptance is not None and p4.contract is not None and p4.band in
          (BAND_GRIND, BAND_NORMAL, BAND_RIP), f"strength={p4.strength} band={p4.band} "
          f"k={getattr(p4.contract, 'strike', None)} ready={p4.ready}")
    check("R4b the trade line carries the strength, the band and the 50",
          "strength" in p4.trade_line() and "band" in p4.trade_line() and "50%" in p4.trade_line(),
          p4.trade_line()[:120])

    # R5 rip vs grind
    plan_r, plan_g = RunawayPlan(), RunawayPlan()
    er = _break_long(_engine()); er._data.bars_since_break = 2; er._data.fifty_accepted = True
    eg = _break_long(_engine()); eg._data.bars_since_break = 10; eg._data.fifty_accepted = True
    pr = prep_for(plan_r, er._data, _rip_frame(), price=101.85)
    pg = prep_for(plan_g, eg._data, _grind_frame(), price=101.85)
    check("R5 a rip gets a wider band than a grind on the same chain",
          pr.strength is not None and pg.strength is not None and pr.strength > pg.strength
          and pr.band > pg.band,
          f"rip strength={pr.strength} band={pr.band}; grind strength={pg.strength} band={pg.band}")
    pr2 = prep_for(plan_r, er._data, _grind_frame(), price=101.85)      # a different frame now
    check("R5b the reading is FROZEN — a later tick with other bars does not change it",
          pr2.strength == pr.strength and pr2.band == pr.band)

    # R6 the strategy fires with the plan's variables
    strat = RC.RunawayContinuationStrategy()
    P.begin_tick()
    sig = strat.generate_signal(orb=er._data, atr_pct=0.14, price_now=101.85, now_et="10:05",
                                chain=_Chain(_calls()), df_1m=_rip_frame())
    P.close_tick(st, "TEST")
    check("R6 the strategy FIRES with the plan's variables on the signal",
          sig is not None and sig.underlying_tp50 == 101.5 and sig.strength_band == pr.band
          and sig.strength_at_entry == pr.strength and sig.contract is not None
          and not getattr(sig, "underlying_stop", 0) and _last_row(st)[0] == "TAKE",
          f"sig={sig is not None} row={_last_row(st)[0]}")

    # R7 break finished, any exit -> the standing state never re-fires. The fact is
    # a CLOSED RUNAWAY ROW in trades.db (09:40-09:41 ET on the fixture's day).
    _book_row(trade_id="rw-r7", symbol="TEST", strategy="RunawayContinuation", option_side="call",
              orb_range_high=101.0, orb_range_low=100.0, status="closed", pnl_usd=12.0,
              entry_time="2026-09-08T13:40:00+00:00", exit_time="2026-09-08T13:41:00+00:00",
              exit_reason="orb_trail_stop pnl=4.0%")
    p7 = prep_for(strat.plan, er._data, _rip_frame(), price=101.85)
    v, why = _last_row(st)
    check("R7 break finished -> HOLD naming re-validation, no fire",
          v == "HOLD" and "finished" in why and not p7.ready, f"{v}: {why[:100]}")

    # R8 re-validation on actual: lose the 50 on a close, then two closes beyond
    # ⚠️ r24: ONE continuous frame since the exit, read whole every tick — the old
    # version fed three disconnected 2-bar frames and relied on a counter carried
    # between them in memory, which is exactly what a restart erased.
    lost, b1, b2 = (101.7, 101.8, 101.2, 101.3), (101.3, 101.7, 101.25, 101.6), (101.6, 101.8, 101.5, 101.7)
    forming = (101.7, 101.9, 101.6, 101.85)
    frames = [_frame([lost, forming], "09:42"),
              _frame([lost, b1, forming], "09:42"),
              _frame([lost, b1, b2, forming], "09:42")]
    outs = [prep_for(strat.plan, er._data, f, price=101.85) for f in frames]
    check("R8 the 50 lost on a close then accepted on two closes -> the break trades again",
          (not outs[0].ready) and (not outs[1].ready) and outs[2].ready,
          f"ready={[o.ready for o in outs]} why={[o.revalidation for o in outs]}")

    # ── R14-R18 (r24): below the 50, restart, unreadable book, signed run ──
    _bind_book()
    e14 = _break_long(_engine()); e14._data.bars_since_break = 2; e14._data.fifty_accepted = True
    p14 = prep_for(RunawayPlan(), e14._data,
                   _frame([(100.6, 101.3, 100.5, 101.2), (101.2, 101.7, 101.15, 101.65),
                           (101.65, 101.7, 100.7, 100.8), (100.8, 100.9, 100.7, 100.8)], "09:50"),
                   price=100.8)
    v, why = _last_row(st)
    check("R14 (09-09 T5) the 50 LATCHED but price below the boundary -> HOLD, no entry",
          v == "HOLD" and "NOT held now" in why and not p14.ready, f"{v}: {why[:110]}")
    check("R18 the run is SIGNED: a price back inside a long break has a negative run",
          p14.run is not None and p14.run < 0, f"run={p14.run}")
    p15 = prep_for(RunawayPlan(), e14._data,
                   _frame([(100.6, 101.3, 100.5, 101.2), (101.2, 101.7, 101.15, 101.65),
                           (101.65, 101.66, 101.4, 101.46), (101.46, 101.5, 101.4, 101.45)], "09:50"),
                   price=101.45)
    v, why = _last_row(st)
    check("R15 (09-11 T6) between the boundary and the 50 on the latch -> HOLD, no entry",
          v == "HOLD" and "NOT held now" in why and not p15.ready, f"{v}: {why[:110]}")
    _book_row(trade_id="rw-r16", symbol="TEST", strategy="RunawayContinuation", option_side="call",
              orb_range_high=101.0, orb_range_low=100.0, status="closed", pnl_usd=-40.0,
              entry_time="2026-09-08T13:40:00+00:00", exit_time="2026-09-08T13:41:00+00:00",
              exit_reason="runaway_thesis_dead")
    p16 = prep_for(RunawayPlan(), e14._data, _rip_frame(), price=101.85)
    v, why = _last_row(st)
    check("R16 a FRESH plan instance (a restart) still sees the finished break in the book",
          v == "HOLD" and "finished" in why and not p16.ready, f"{v}: {why[:110]}")

    class _Unreadable(_TLB.TradeLogger):
        def __init__(self):
            pass
        def _connect(self):
            raise RuntimeError("the book is unreadable")
    _TLB._trade_logger = _Unreadable()
    p17 = prep_for(RunawayPlan(), e14._data, _rip_frame(), price=101.85)
    v, why = _last_row(st)
    check("R17 an unreadable trade book FAILS CLOSED -> HOLD, never a fire",
          v == "HOLD" and "unreadable" in why and "fails closed" in why and not p17.ready,
          f"{v}: {why[:110]}")
    _bind_book()

    # R9 dormant outside the window, one row then silence
    def rows():
        return st.conn.execute("SELECT COUNT(*) FROM plan_tick WHERE strategy='RunawayContinuation' "
                               "AND verdict='DORMANT'").fetchone()[0]
    P.clear_dormant("RunawayContinuation")
    from strategy import runaway_plan as _rpm
    _c9 = _rpm._cutoff_hm(); _m9 = _c9[0] * 60 + _c9[1]      # r149: read, not typed
    _f9 = lambda m: f"{m // 60:02d}:{m % 60:02d}"
    n0 = rows(); prep_for(plan, er._data, _rip_frame(), now=_f9(_m9 + 1)); n1 = rows()
    prep_for(plan, er._data, _rip_frame(), now=_f9(_m9 + 2)); prep_for(plan, er._data, _rip_frame(), now=_f9(_m9 + 10)); n2 = rows()
    prep_for(plan, er._data, _rip_frame(), now="09:31"); n3 = rows()
    prep_for(plan, er._data, _rip_frame(), now="09:32"); n4 = rows()
    check(f"R9 outside 09:35–{_f9(_m9)}: one DORMANT row per transition, then silence",
          n1 == n0 + 1 and n2 == n1 and n3 == n2 + 1 and n4 == n3, f"{n0}->{n1}->{n2}->{n3}->{n4}")

    # ── the exits ────────────────────────────────────────────────────────
    import datetime as _dt
    from zoneinfo import ZoneInfo
    import execution.exit_engine as XE
    import data.derived_store as DS
    from data.derived_store import DerivedStore
    _real_dt = XE.datetime
    _real_hc = XE.is_hard_close_time
    _real_store = DS._store
    ET = ZoneInfo("America/New_York")

    class _Frozen(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _dt.datetime(2026, 9, 8, 10, 30, tzinfo=ET)
    XE.datetime = _Frozen
    XE.is_hard_close_time = lambda: False
    store = DerivedStore(path=os.path.join(tempfile.mkdtemp(), "derived.db"))
    DS._store = store
    import config as _cfg
    try:
        xe = XE.ExitEngine(paper_trading=True)
        xe._theta_bleed = lambda *a, **k: False
        xe._velocity_stall = lambda *a, **k: None
        base = {"trade_id": "x-run", "strategy": "RunawayContinuation", "setup_type": "runaway",
                "direction": "long", "entry_premium": 1.00, "contracts": 1, "status": "open",
                "stop_premium": 0.80, "target_premium": 2.00, "trail_activation": 1.50,
                "underlying_stop": 0.0, "underlying_entry": 101.85, "orb_range_high": 101.0,
                "orb_range_low": 100.0, "entry_time": "2026-09-08T10:05:00"}
        # X1 handoff: a resistance at 102.6 rejected on close after entry
        store.insert_level_event((_cfg.INSTRUMENT, "lvl-102.6", "2026-09-08 10:20:00",
                                  _dt.datetime(2026, 9, 8, 10, 20, tzinfo=ET).timestamp(),
                                  "REJECTED", 102.6, "resistance", "prev_day", 0.001, "shallow", 1, 102.4,
                                  _dt.datetime(2026, 9, 8, 10, 21, tzinfo=ET).timestamp()))   # CD.2: the bar's close
        held = _frame([(102.3, 102.5, 102.2, 102.4), (102.4, 102.6, 102.3, 102.45)], "10:19")
        d = xe._evaluate_orb(dict(base), 1.30, held)
        check("X1 🔴 REJECTED handoff exits the runaway, naming the pool",
              d.should_exit and "handoff" in str(d.exit_reason) and "102.60" in str(d.exit_reason),
              f"{d.should_exit}: {d.exit_reason}")
        d_orb = xe._evaluate_orb(dict(base, trade_id="x-orb", strategy="ORBStrategy",
                                      underlying_stop=100.5, stop_premium=0.75), 1.30, held)
        check("X1b ...and the ORB record too", d_orb.should_exit and "handoff" in str(d_orb.exit_reason))
        # clear the event for the rest
        store.conn.execute("DELETE FROM level_event"); store.conn.commit()
        # X2 HOLD at the old floor while price is beyond the 50
        rec = dict(base)
        d = xe._evaluate_orb(rec, 0.78, held)
        check("X2 (r209, RUN.10) premium at the 20% floor -> the Runaway is STOPPED; nothing is held",
              d.should_exit and "hard_stop" in str(d.exit_reason) and not rec.get("_would_have_floored"),
              f"{d.should_exit}:{d.exit_reason} rec={rec.get('_would_have_floored')}")
        rec_h = dict(base, trade_id="x2-hunt", strategy="LiquidityHunt")
        _sv_ht = xe._hunt_at_target
        xe._hunt_at_target = lambda *a, **k: ""
        try:
            d_h = xe._evaluate_orb(rec_h, 0.78, held)
        finally:
            xe._hunt_at_target = _sv_ht
        check("X2b the HUNT at the same floor is still HELD, would-have-floored recorded",
              not (d_h.should_exit and "hard_stop" in str(d_h.exit_reason)) and bool(rec_h.get("_would_have_floored")),
              f"{d_h.should_exit}:{d_h.exit_reason} rec={rec_h.get('_would_have_floored')}")
        # X3 thesis dead: close back through 101.5
        dead = _frame([(101.8, 101.9, 101.2, 101.3), (101.3, 101.4, 101.2, 101.35)], "10:19")
        d = xe._evaluate_orb(dict(base), 0.95, dead)
        check("X3 a 1m close back through the 50 -> runaway_thesis_dead",
              d.should_exit and "thesis_dead" in str(d.exit_reason), str(d.exit_reason))
        # X4 fizzle: higher-low broken + range contraction, price still beyond 101.5
        fz = _frame([(101.6, 102.4, 101.5, 102.3), (102.3, 102.9, 102.2, 102.8),
                     (102.8, 103.2, 102.6, 103.0), (103.0, 103.15, 102.95, 103.05),
                     (103.05, 103.1, 102.98, 103.02), (103.02, 103.06, 102.97, 103.0),
                     (103.0, 103.03, 102.5, 102.55),          # closes below the rolling pullback low
                     (102.55, 102.6, 102.5, 102.56)], "10:06")
        rec4 = dict(base)
        d = xe._evaluate_orb(rec4, 1.20, fz)
        check("X4 fizzle: higher-low broken + range contraction -> runaway_fizzle",
              d.should_exit and "fizzle" in str(d.exit_reason) and "higher_low_broken" in str(d.exit_reason),
              f"{d.exit_reason} read={rec4.get('_fizzle_read')}")
        # X5 backstop: a close through the boundary (also through the 50 -> thesis first)
        bs = _frame([(101.6, 101.7, 100.7, 100.8), (100.8, 100.9, 100.7, 100.85)], "10:19")
        d = xe._evaluate_orb(dict(base), 0.60, bs)
        check("X5 a close through the boundary exits (thesis dead fires first, beneath it the backstop)",
              d.should_exit and ("thesis_dead" in str(d.exit_reason) or "backstop" in str(d.exit_reason)),
              str(d.exit_reason))
        # X6 ORB floor unchanged
        d = xe._evaluate_orb(dict(base, trade_id="x-orb2", strategy="ORBStrategy",
                                  underlying_stop=100.5, stop_premium=0.75), 0.70, held)
        check("X6 the ORB's own 25% floor still fires", d.should_exit and "hard_stop" in str(d.exit_reason),
              str(d.exit_reason))
    finally:
        XE.datetime = _real_dt
        XE.is_hard_close_time = _real_hc
        DS._store = _real_store
        os.environ["OT_RELAXED_ENTRY"] = "0"

    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("PASS — check_runaway_plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
