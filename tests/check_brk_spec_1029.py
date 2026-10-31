#!/usr/bin/env python3
"""
tests/check_brk_spec_1029.py  v5.1
v5.1  2026-10-30  OTV5 r58 (DECAY.1) — OT_DECAY_STOP=0 HERE: this checker pins a pre-decay exit in isolation. T1 / T3 (a +30% Breakout given back to 1.90 below 0.5W, and the 2.60 -> 2.00 tick before the 0.5W arm) now close on the peak-decay stop, which is the r57 rule working, not the trail;
      the decay stop itself is gated by tests/check_decay_stop.py. No assertion changed.
v5.0  2026-10-29  OTV5 r54 (BRK.16) — THE OPERATOR'S 2026-10-29 BREAKOUT SPEC, DRIVEN THROUGH THE REAL CODE.
      "the target will be from the boundary of the opening range a distance of 1W"; "I want the trailing stop
      activation to occur at 1/2 W"; "for STRIKE selection, it should be the strike nearest that 1W distance we identify
      as the target"; "The breakout trade should be purely directional without regard for levels in its path"; "if the
      Pin is in the direction of the break, allow it. But if the pin is on the opposite direction from our trade,
      forbid it"; "if we haven't entered before it reaches 1W, absolutely refuse it — that is runaway's domain. It
      should honestly refuse if it's already crossed 1/2W."; "I concur on both. Yes build it."

  Fixture: opening range 100.00-101.00 (W = 1.00), so the 1W target is 102.00 long / 99.00 short, the trail arms at
  101.50 / 99.50 and the 1/2 W entry limit is 101.50 / 99.50.

  S1  the REAL BreakoutPlan.prepare, long: target = orb_high + 1W (102.00), source "edge+1W", the plan is READY
  S2  the same, short: target = orb_low - 1W (99.00)
  S3  R is SIGNED: (target - break close) / risk (0.70 / 0.75), not abs() of the old measured move
  S4  no level read: a pool sitting in the path (derived.levels.board_for patched) changes nothing - board_for is never
      called, the target stays 102.00, range_clean / room_to_run are not conditions and read "n/a - Breakout has no
      level reads"
  S5  no DEFER: past the research window with gamma_regime unmet and the old harvest shape (a pool 0.3R ahead), the
      plan WAITs - verdict WAIT, no DEFER->LiquidityHunt / DEFER->SweepCreditSpread
  S6  the strike NEAREST the 1W target on SPX (102.40, 0.40 past it), not the at-or-inside one (101.50)
  S7  a break close past 1/2 W (101.60 >= 101.50) refuses: "the break close is already past 1/2 W (runaway's domain)"
  S8  a break close exactly AT 1/2 W (101.50) refuses too
  S9  the fire tick: Breakout.generate_signal on a READY plan with the live price past 1/2 W (101.60) does not fire;
      S9b at 101.35 it fires (control)
  T1  the trail is UNARMED below 0.5W: +30% (2.60, underlying 101.40) writes no trail; the give-back to 1.90 that
      today's trail (seeded 1.40, ratcheted to 1.95) closes HOLDS
  T2  the structure stop still exits an unarmed trade - and r98's nearer-stop deferral cannot defer to the trail
      (today a 1.95 trail would hold a touch through 100.55 at a 2.00 mark)
  T3  at 0.5W (underlying 101.55) the trail ARMS, seeded at max(stop 1.40, peak 2.60 x 0.75) = 1.95; it is latched,
      and a later 1.94 mark with the underlying back at 101.30 is a trail_stop_hit
  T4  a short arms at orb_low - 0.5W (99.50), not before (its trail is at least the 1.95 seed; the FVG lock may sit
      above it - today's mechanics once armed)
  T5  a record with NO opening range keeps today's trail (armed from entry: 2.60 trails at 1.95) - the safer side
  T6  a restart: a persisted trail_stop re-arms (trail_armed True, a 1.90 mark exits on it); a Breakout row written
      to a real trades.db and read back by get_open_trades() carries orb_range_high/low and direction
  T7  another strategy through the same evaluator (an unrouted name) trails from entry as before
  P1  pin_ahead_allows: a Breakout long with the pin ABOVE price inside the band is ALLOWED
  P2  a pin BEHIND (below a long / above a short) stays refused
  P3  a pin exactly AT price stays refused
  P4  every other strategy keeps today's gate (ORBStrategy / RunawayContinuation / LiquidityHunt with a pin ahead)
  P5  outside the band (no refusal) nothing changes; the gate's branch logs "[pin] ALLOWED" (source)
  H1  the LiquidityHunt still reads the level board (board_for called)

Born red on ecfe729 at S1-S9b, T1-T4, P1 and P5 (16 of 23; S9b because the base plan never readies on this fixture -
its pool caps the reach and SPX's at-or-inside pick finds no strike).
Run:  python3 tests/check_brk_spec_1029.py
"""
import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_brk_spec_1029.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
# r58 (DECAY.1): this checker pins a pre-decay exit in isolation; the peak-decay stop is gated in tests/check_decay_stop.py
os.environ["OT_DECAY_STOP"] = "0"
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _ORB:
    orb_high, orb_low = 101.00, 100.00


RANGE = [(100.2, 100.9, 100.0, 100.5, 900)] * 5


def _rows(close, direction="long"):
    """Five range bars, the break bar CLOSING at `close`, then the forming bar at the same price."""
    if direction == "long":
        brk = (100.6, max(close, 101.0) + 0.10, 100.55, close, 2400)
    else:
        brk = (100.4, 100.45, min(close, 100.0) - 0.10, close, 2400)
    live = (close, close + 0.05, close - 0.05, close, 800)
    return RANGE + [brk, live]


def _df(rows):
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": v} for o, h, l, c, v in rows],
        index=pd.date_range("2026-10-05 09:30", periods=len(rows), freq="1min"))


def _c(strike, delta, side="C"):
    return types.SimpleNamespace(strike=float(strike), mark=2.0, bid=1.9, ask=2.1, delta=delta,
                                 gamma=0.05, symbol=f"X{side}{strike}", streamer_symbol=f".X{side}{strike}",
                                 expiry="2026-10-05", option_type=side)


def _chain_long(*strikes):
    return types.SimpleNamespace(calls=[_c(k, 0.45) for k in strikes], puts=[])


def _chain_short(*strikes):
    return types.SimpleNamespace(calls=[], puts=[_c(k, -0.45, "P") for k in strikes])


def main():
    print("check_brk_spec_1029")
    try:
        import pandas  # noqa: F401
        import config as C
        import strategy.breakout as B
        from strategy.breakout import Breakout
        from strategy.breakout_plan import BreakoutPlan
        from data.candle_feed import FeedStore
        import derived.levels as LV
        import execution.exit_engine as XE
        import strategy.management as MG
        import main as M
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2

    fs = FeedStore(os.environ["OT_FEED_DB"])
    research_open, research_closed = "2099-12-31", "2026-10-04"
    calls = {"n": 0}
    _real_board = LV.board_for

    def _pool_board(store, symbol, price, orb_high=None, orb_low=None, limit=3):
        calls["n"] += 1
        return {"state": "ok", "above": [{"price": 101.525, "near_edge": 101.525, "provenance": "pdh"},
                                         {"price": 100.50, "provenance": "inside"}],
                "below": [{"price": 100.50, "provenance": "inside"}]}

    LV.board_for = _pool_board                                  # a pool in the path and a level inside the range

    def prep(close, chain=None, direction="long", symbol="SPX", until=research_open, price=None):
        B.RESEARCH_UNTIL = until
        plan = BreakoutPlan()
        rows = _rows(close, direction)
        p = plan.prepare(spec=Breakout, orb=_ORB(), price_now=price if price is not None else rows[-1][3],
                         now_et="10:05", chain=chain, df_1m=_df(rows), flow_conn=fs.conn, symbol=symbol)
        return plan, p

    def last(plan):
        return str((plan.planner._last or (None, "", ""))[2])

    # ── S1-S3: the 1W target, signed R ─────────────────────────────────────
    _, p1 = prep(101.30, _chain_long(102.0, 103.0))
    check("S1 long: target = orb_high + 1W = 102.00 via edge+1W, plan READY",
          abs((p1.target or 0) - 102.0) < 1e-9 and p1.target_src == "edge+1W" and p1.ready,
          f"target={p1.target} src={p1.target_src} ready={p1.ready} unmet={p1.unmet}")
    _, p2 = prep(99.70, _chain_short(99.0, 98.0), direction="short")
    check("S2 short: target = orb_low - 1W = 99.00 via edge-1W, plan READY",
          abs((p2.target or 0) - 99.0) < 1e-9 and p2.target_src == "edge-1W" and p2.ready,
          f"target={p2.target} src={p2.target_src} ready={p2.ready} unmet={p2.unmet}")
    _r = (102.0 - 101.30) / 0.75
    check("S3 R is signed (target - break close) / risk = 0.70 / 0.75",
          p1.r is not None and abs(p1.r - _r) < 1e-6 and abs((p1.risk or 0) - 0.75) < 1e-9,
          f"r={p1.r} risk={p1.risk} want {_r:.4f}")

    # ── S4-S5: no levels, no DEFER ─────────────────────────────────────────
    notes = getattr(p1.tick, "check_notes", {}) or {}
    check("S4 no level read: board_for never called, range_clean/room_to_run not conditions, read n/a",
          calls["n"] == 0 and "range_clean" not in p1.conditions and "room_to_run" not in p1.conditions
          and "range_clean" not in Breakout.CONDITIONS and "room_to_run" not in Breakout.CONDITIONS
          and "no level reads" in notes.get("range_clean", "") and "no level reads" in notes.get("room_to_run", "")
          and abs((p1.target or 0) - 102.0) < 1e-9,
          f"board_for calls={calls['n']} conds={sorted(p1.conditions)} notes={notes.get('range_clean')!r}")
    plan5, p5 = prep(101.30, _chain_long(102.0), until=research_closed)
    v5 = str(getattr(p5, "verdict", ""))
    check("S5 past research, gamma_regime unmet, a pool 0.3R ahead: the plan WAITs, no DEFER",
          not p5.ready and v5 == "WAIT" and "DEFER" not in last(plan5) and calls["n"] == 0,
          f"verdict={v5} unmet={p5.unmet} last={last(plan5)!r} board_for calls={calls['n']}")

    # ── S6: the strike nearest the 1W target, SPX included ─────────────────
    _, p6 = prep(101.30, _chain_long(102.40, 101.50))
    k6 = getattr(getattr(p6, "contract", None), "strike", None)
    check("S6 SPX: the strike NEAREST the 1W target (102.40), not the at-or-inside one (101.50)",
          k6 == 102.40, f"chose={k6} target={p6.target}")

    # ── S7-S9: a break already past 1/2 W is the runaway's ─────────────────
    plan7, p7 = prep(101.60, _chain_long(102.0))
    check("S7 a break close past 1/2 W (101.60 >= 101.50) refuses: 'past 1/2 W (runaway's domain)'",
          not p7.ready and "past 1/2 W" in last(plan7) and "runaway" in last(plan7),
          f"ready={p7.ready} last={last(plan7)!r}")
    plan8, p8 = prep(101.50, _chain_long(102.0))
    check("S8 a break close exactly AT 1/2 W (101.50) refuses too",
          not p8.ready and "past 1/2 W" in last(plan8), f"ready={p8.ready} last={last(plan8)!r}")

    def fire(px):
        plan, p = prep(101.30, _chain_long(102.0))
        if not p.ready:
            return None, f"not ready: {p.unmet} {last(plan)}"
        p.price_now = px                                       # the live price on the fire tick
        strat = Breakout.__new__(Breakout)
        strat._plan = plan
        strat.prepare = lambda **kw: p
        out = strat.generate_signal()
        return out, last(plan)

    o9, w9 = fire(101.60)
    check("S9 the fire tick: a live price past 1/2 W (101.60) does not fire",
          not (o9 is not None and getattr(o9, "strategy_name", "") == "Breakout") and "1/2 W" in w9,
          f"out={type(o9).__name__} last={w9!r}")
    o9b, w9b = fire(101.35)
    check("S9b control: at 101.35 (inside 1/2 W) the same plan fires",
          o9b is not None and getattr(o9b, "strategy_name", "") == "Breakout", f"out={o9b!r} last={w9b!r}")
    LV.board_for = _real_board

    # ── T1-T7: the trail, through the REAL ManagementPlan.decide + ExitEngine ──
    XE.is_hard_close_time = lambda *a, **k: False
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    def rec(tid, direction="long", hi=101.0, lo=100.0, strategy="Breakout"):
        long_ = direction == "long"
        return {"trade_id": tid, "strategy": strategy, "setup_type": "breakout_" + direction, "symbol": "QQQ",
                "direction": direction, "option_side": "call" if long_ else "put", "is_butterfly": 0,
                "is_condor_leg": 0, "is_credit_vertical": 0, "is_broken_wing": 0,
                "strike": 102.0 if long_ else 99.0, "expiry": "2099-12-31", "contracts": 2,
                "entry_premium": 2.00, "stop_premium": 1.40, "trail_activation": 2.00, "target_premium": 4.00,
                "trail_stop": 0.0, "underlying_entry": 101.30 if long_ else 99.70,
                "underlying_stop": 100.55 if long_ else 100.45,
                "underlying_target": 102.0 if long_ else 99.0, "orb_range_high": hi, "orb_range_low": lo,
                "option_symbol": "QQQ   991231C00102000", "entry_time": now_iso, "entry_delta": 0.8,
                "current_delta": 0.45, "paper_trade": 1, "status": "open"}

    def frame(px):
        return _df(RANGE + [(px, px + 0.02, px - 0.02, px, 500)])

    def tick(plan, eng, r, prem, px):
        r["current_price"] = px
        it = plan.decide(r, prem, df_1m=frame(px), open_records=None, current_price=px,
                         ctx={"df_5m": None, "vol": None, "trend": None}, exit_engine=eng)
        if it is not None and it.action == "TRAIL" and it.trail is not None:
            r["trail_stop"] = it.trail                          # position_manager persists it
        return it

    def act(it):
        return "None" if it is None else f"{it.action}:{it.reason[:40]}"

    def new():
        return MG.ManagementPlan(), XE.ExitEngine(paper_trading=True)

    mp, en = new()
    r1 = rec("t1-unarmed")
    a = tick(mp, en, r1, 2.60, 101.40)
    b = tick(mp, en, r1, 1.90, 101.35)
    check("T1 below 0.5W the trail is inert: +30% writes no trail, the 1.90 give-back HOLDS",
          a is not None and a.action == "HOLD" and b is not None and b.action == "HOLD"
          and float(r1.get("trail_stop") or 0) == 0.0,
          f"tick1={act(a)} tick2={act(b)} trail_stop={r1.get('trail_stop')}")

    mp, en = new()
    r2 = rec("t2-structure")
    a = tick(mp, en, r2, 2.60, 101.40)
    b = tick(mp, en, r2, 2.00, 100.50)                         # a touch through 100.55, mark above any trail
    check("T2 unarmed: the structure stop exits (no deferral to a trail that has not armed)",
          b is not None and b.action == "CLOSE" and b.condition == "structure_stop",
          f"tick1={act(a)} tick2={act(b)}")

    mp, en = new()
    r3 = rec("t3-arm")
    a = tick(mp, en, r3, 2.60, 101.40)
    b = tick(mp, en, r3, 2.40, 101.55)
    armed = bool(getattr(en, "trail_armed", lambda r: False)(r3))
    c = tick(mp, en, r3, 1.94, 101.30)
    check("T3 at 0.5W the trail arms, seeded max(1.40, 2.60 x 0.75) = 1.95, latched; 1.94 later exits on it",
          a.action == "HOLD" and b is not None and b.action == "TRAIL" and abs((b.trail or 0) - 1.95) < 1e-9
          and armed and c is not None and c.action == "CLOSE" and "trail_stop_hit" in c.reason,
          f"tick1={act(a)} tick2={act(b)} trail={getattr(b, 'trail', None)} armed={armed} tick3={act(c)}")

    mp, en = new()
    r4 = rec("t4-short", direction="short")
    a = tick(mp, en, r4, 2.60, 99.60)
    b = tick(mp, en, r4, 2.50, 99.50)
    check("T4 a short arms at orb_low - 0.5W (99.50), not at 99.60",
          a is not None and a.action == "HOLD" and b is not None and b.action == "TRAIL"
          and (b.trail or 0) >= 1.95 - 1e-9, f"tick1={act(a)} tick2={act(b)}")

    mp, en = new()
    r5 = rec("t5-no-range", hi=0.0, lo=0.0)
    a = tick(mp, en, r5, 2.60, 101.40)
    check("T5 no opening range on the record: today's trail (armed from entry, 2.60 trails at 1.95)",
          a is not None and a.action == "TRAIL" and abs((a.trail or 0) - 1.95) < 1e-9
          and bool(getattr(en, "trail_armed", lambda r: True)(r5)), f"tick1={act(a)}")

    mp, en = new()
    r6 = rec("t6-restart")
    r6.update(trail_stop=1.95, mfe_premium=2.60, max_premium_seen=2.60)
    armed6 = bool(getattr(en, "trail_armed", lambda r: True)(r6))
    a = tick(mp, en, r6, 1.90, 101.30)
    ok_db, why_db = False, ""
    try:
        from database.trade_logger import get_trade_logger, make_record
        tl = get_trade_logger()
        row = rec("t6-db-row")
        row.pop("status", None)
        tl.log_entry(make_record(**row))
        got = [x for x in tl.get_open_trades() if x.get("trade_id") == "t6-db-row"]
        g = got[0] if got else {}
        ok_db = bool(got) and float(g.get("orb_range_high") or 0) == 101.0 \
            and float(g.get("orb_range_low") or 0) == 100.0 and g.get("direction") == "long"
        why_db = f"rows={len(got)} hi={g.get('orb_range_high')} lo={g.get('orb_range_low')} dir={g.get('direction')}"
    except Exception as exc:                                    # noqa: BLE001
        why_db = f"{type(exc).__name__}: {exc}"
    check("T6 restart: a persisted trail re-arms and exits at 1.90; trades.db rehydrates orb_range_high/low + direction",
          armed6 and a is not None and a.action == "CLOSE" and "trail_stop_hit" in a.reason and ok_db,
          f"armed={armed6} tick={act(a)} db: {why_db}")

    mp, en = new()
    r7 = rec("t7-other", strategy="ZzUnrouted")
    a = en.evaluate(r7, 2.60, df_1m=frame(101.40))
    check("T7 another strategy through the same evaluator trails from entry as before (a trail at +30%)",
          a.new_trail_stop is not None and not a.should_exit,
          f"trail={a.new_trail_stop} exit={a.should_exit}")

    # ── P1-P5: the pin gate ────────────────────────────────────────────────
    from strategy.gex_pin_butterfly import expected_move
    px, iv = 500.0, 0.20
    em = expected_move(px, iv)
    near = em * C.PIN_PROXIMITY_MIN_FRAC * 0.5
    gx = lambda pin: types.SimpleNamespace(pin_strike=pin, gex_environment="PINNING")   # noqa: E731
    ctx = lambda pin: {"gex": gx(pin), "price": px, "atm_iv": iv}                          # noqa: E731
    sig = lambda name, d: types.SimpleNamespace(strategy_name=name, direction=d,          # noqa: E731
                                                option_side="call" if d == "long" else "put")
    allows = getattr(M, "pin_ahead_allows", None)

    def verdict(name, d, pin):
        v = M.pin_proximity_verdict(ctx(pin))
        if allows is None:
            return v[0], False
        return v[0], bool(allows(sig(name, d), ctx(pin), v))

    rl, al = verdict("Breakout", "long", px + near)
    rs, as_ = verdict("Breakout", "short", px - near)
    check("P1 Breakout, PINNING inside the band, pin AHEAD (long above / short below): ALLOWED",
          rl and al and rs and as_, f"long refuse={rl} allow={al}; short refuse={rs} allow={as_}")
    rb, ab = verdict("Breakout", "long", px - near)
    rbs, abs_ = verdict("Breakout", "short", px + near)
    check("P2 a pin BEHIND the trade stays refused", rb and not ab and rbs and not abs_,
          f"long allow={ab} short allow={abs_}")
    ra, aa = verdict("Breakout", "long", px)
    check("P3 a pin exactly AT price stays refused", ra and not aa, f"refuse={ra} allow={aa}")
    others = [(n, verdict(n, "long", px + near)) for n in ("ORBStrategy", "RunawayContinuation", "LiquidityHunt")]
    check("P4 every other strategy keeps today's gate (a pin ahead is still refused)",
          all(v[0] and not v[1] for _, v in others), f"{others}")
    far = em * (C.PIN_PROXIMITY_MIN_FRAC + 0.2)
    rf, af = verdict("Breakout", "long", px + far)
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    check("P5 outside the band nothing changes (not refused, nothing to allow); the gate logs '[pin] ALLOWED'",
          not rf and not af and allows is not None and "[pin] ALLOWED %s %s" in src
          and "elif _refuse and pin_ahead_allows(signal, ctx" in src, f"refuse={rf} allow={af} fn={allows}")

    # ── H1: the Hunt keeps its levels ──────────────────────────────────────
    try:
        from strategy.liquidity_hunt import LiquidityHunt
        hc = {"n": 0}

        def _cnt(*a, **k):
            hc["n"] += 1
            return {"state": "ok", "above": [], "below": []}
        LV.board_for = _cnt
        LiquidityHunt()._board(100.5, 101.0, 100.0)
        LV.board_for = _real_board
        check("H1 the LiquidityHunt still reads the level board", hc["n"] == 1, f"calls={hc['n']}")
    except Exception as exc:                                    # noqa: BLE001
        LV.board_for = _real_board
        check("H1 the LiquidityHunt still reads the level board", False, f"{type(exc).__name__}: {exc}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
