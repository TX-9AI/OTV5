#!/usr/bin/env python3
"""tests/check_standing_offer.py  v1.3
v1.3  2026-09-26  OTV4TEST r149 — S7 RE-POINTED, NOT LOOSENED: it searched the WHOLE of main.py
      for the first 'if pos_mgr.has_open_position():', and r149's handle_hard_close (which
      runs before main_loop in the file) now carries one, so S7 compared the supervisor against
      the wrong function. It now reads main_loop only; still red if the loop's split moves
      above the supervisor (mutant-checked on r149).
v1.2  2026-09-10  OTV4TEST r13 — S5 adopts its fixture fill into a TEMP trade logger, never
      the box's. Predecessor defect #12.
THE ORB STANDING OFFER: one order, supervised from both branches, and the
BROKER declares the position.

v1.1  2026-09-01  r207 — S3 IS RE-DERIVED AND THE FIXTURE STOPS ROTTING.
      S3 asserted that a paper offer at a price "not back to the level" was
      LEFT STANDING. That premise is retired by operator ruling — "in paper
      mode, they ALL fill" — and the arithmetic behind it was wrong anyway:
      it compared the UNDERLYING price to the OPTION STRIKE. Re-derived rather
      than deleted, per r155: a fixture whose numbers encode the rule being
      replaced is the trap, not the test.
      ⚠️ AND `SNAP["expiry"]` WAS HARDCODED "2026-08-31". `get_open_trades_live()`
      drops rows whose expiry has passed, so S5/S5b went red on 2026-09-01 and
      would have stayed red forever — verified by running this file unmodified
      at f74818b. Now relative to today. r170's lesson: a hypothetical pinned
      to a wall-clock value is a check that eventually fails for a reason that
      has nothing to do with the code.
      ⚠️ THIS FILE STILL DOES NOT DRIVE `_place_single_leg`, which is the gap
      that let r195 go green over a path that never executed in paper. That
      coverage lives in tests/check_orb_sequence.py S9.
v1.0  2026-08-30  r195 — backlog ORB.2. Born red at r194 (0b0d15a):
      `execution/resting_orders.py` does not exist there, ORB walks the ladder,
      and nothing supervises an unfilled order.

🔑 S5 AND S6 ARE THE TWO THAT MATTER, and neither is about a flag.
  S5 — adoption is IDEMPOTENT. The supervisor calls adopt on every fill DELTA,
       so a 4-then-10 partial calls it twice. Booking two positions for one
       contract the broker holds once is worse than booking none.
  S6 — the order saying "filled" is NOT permission to book. Operator's ruling
       is that broker POSITIONS declare the position; if the order reports fills
       and the book does not list the contract, we page and book nothing.

⚠️ S1 IS A SOURCE CHECK AND IT IS THE ONLY ONE HERE, DELIBERATELY. Whether ORB
alone bypasses the ladder is a fact about a predicate, not about a run — there
is no execution that proves a NEGATIVE for every other strategy. Everything
else in this file EXECUTES.

Run:  python3 tests/check_standing_offer.py
"""
import json
import datetime as _dt
import os
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ["OT_RESTING_DB"] = os.path.join(tempfile.mkdtemp(), "resting.db")

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


_TODAY = _dt.datetime.now().strftime("%Y-%m-%d")

SNAP = dict(symbol="NVDA", strategy="ORBStrategy", setup_type="ORB Long",
            direction="long", underlying_entry=197.15, underlying_stop=195.89,
            underlying_target=202.85, vix_at_entry=15.0, is_fed_day=False,
            option_side="call", is_butterfly=False, strike=196.0,
            # ⚠️ r207 — RELATIVE, NOT HARDCODED. This read "2026-08-31" and
            # `get_open_trades_live()` drops any row whose expiry is in the
            # past, so S5/S5b went red on 2026-09-01 and would have stayed red
            # forever — a date-rotting fixture, the same class as the r170
            # butterfly hypotheticals that drifted with the hour they ran at.
            # A permanent red teaches the reader to skip red runs.
            expiry=_TODAY, setup_grade="UNGRADED", setup_score=None,
            stop_premium=0.9, trail_activation=1.8, target_premium=2.4,
            adx_at_entry=28.0, flat_angle_deg=0.0, swept_level_name="",
            level_strength=0.0, relaxed_entry=0, notes="")


def main():
    try:
        from execution import resting_orders as ro
    except ImportError as exc:
        # Named failure, never a traceback — "the checker crashed" and "the
        # feature is absent" must not look alike.
        check("S0 execution/resting_orders.py exists", False, str(exc))
        print("\nFAILED 1: S0 — nothing below can execute")
        return 1
    from execution import entry_engine as ee
    from utils.time_utils import now_et

    d = now_et().date().isoformat()

    # ── S1: exactly ONE strategy leaves the ladder ─────────────────────────
    class _S:
        def __init__(self, n):
            self.strategy_name = n
    exempt = [n for n in ("ORBStrategy", "RunawayContinuation",
                          "IronCondorStrategy", "TrendCreditSpread",
                          "GEXPinButterfly", "SweepCreditSpread")
              if ee._is_standing_offer(_S(n))]
    check("S1 ORB alone is exempt from the entry ladder",
          exempt == ["ORBStrategy"], f"exempt: {exempt}")

    # ── S2: an offer is not a fill ─────────────────────────────────────────
    ro.record_placement(order_id="T1", session_date=d, strategy="ORBStrategy",
                        symbol="NVDA  260831C00196000", underlying="NVDA",
                        side="call", strike=196.0, offered_qty=10,
                        offer_price=1.20, direction="long",
                        target_50pct=199.68, structure_stop=195.89,
                        signal_json=json.dumps(SNAP))
    rows = ro.working(d)
    check("S2 a placed offer is WORKING, with its own attempt's levels frozen",
          len(rows) == 1 and rows[0]["state"] == "WORKING"
          and rows[0]["target_50pct"] == 199.68
          and rows[0]["structure_stop"] == 195.89)

    # ⚠️ r207 — CAPTURED BEFORE SUPERVISION. Paper now fills the whole offer on
    # the first pass, so `working()` is empty afterwards and the later cases
    # would have nothing to read. The row is the fixture; the table is the
    # thing under test.
    row = ro.working(d)[0]

    # ── S3: r207 — A PAPER OFFER FILLS WHOLE, FIRST PASS ───────────────────
    # 🔴 THIS CHECK USED TO ASSERT THE OPPOSITE, and its premise is retired by
    # operator ruling, 2026-09-01: "in paper mode, they ALL fill." v1.0 modelled
    # no-fill risk by comparing the UNDERLYING price to the OPTION STRIKE —
    # different quantities — so it filled every OTM offer instantly and no ITM
    # one, backwards, and never executed because `_place_single_leg` reached the
    # paper filler before an offer was ever placed. A fixture that encodes the
    # rule being replaced is the r155 trap; it is re-derived, not deleted.
    n = ro.supervise(price=197.5, last_1m_close=197.2, paper=True, adopt=None)
    check("S3 a paper offer fills WHOLE on the first supervision pass",
          n == 1 and len(ro.working(d)) == 0,
          f"closed={n} still_working={len(ro.working(d))}")

    # ── S4: every cancel trigger, both directions ──────────────────────────
    cr = ro.cancel_reason
    t50 = ro.cancel_reason(row, price=199.70, last_1m_close=199.5,
                           target_50pct=199.68, structure_stop=195.89,
                           direction="long")
    st = cr(row, price=196.0, last_1m_close=195.71, target_50pct=199.68,
            structure_stop=195.89, direction="long")
    eod = cr(row, price=196.0, last_1m_close=196.0, target_50pct=199.68,
             structure_stop=195.89, direction="long", eod=True)
    keep = cr(row, price=197.5, last_1m_close=196.9, target_50pct=199.68,
              structure_stop=195.89, direction="long")
    sh50 = cr(row, price=190.0, last_1m_close=190.2, target_50pct=190.62,
              structure_stop=196.11, direction="short")
    shst = cr(row, price=195.0, last_1m_close=196.30, target_50pct=190.62,
              structure_stop=196.11, direction="short")
    check("S4 all four triggers fire, both directions, and a live setup keeps",
          t50.startswith("ran_past_50pct") and st.startswith("structure_stop")
          and eod == "eod_flatten" and keep == ""
          and sh50.startswith("ran_past_50pct")
          and shst.startswith("structure_stop"),
          f"long50={bool(t50)} struct={bool(st)} eod={bool(eod)} "
          f"keep={keep!r} short50={bool(sh50)} shortstruct={bool(shst)}")

    # ── S5: adoption is idempotent ─────────────────────────────────────────
    import tempfile as _tf
    import database.trade_logger as _TL
    # r13 — a TEMP logger for this test's life: S5's adopt_fill wrote orb-T1 into the
    # box's LIVE trades.db when the lander ran this check (2026-09-10) and the bot
    # resumed a phantom position. The temp file dies with the process.
    _TL._trade_logger = _TL.TradeLogger(db_path=os.path.join(_tf.mkdtemp(), 'trades.db'))
    tl = _TL.get_trade_logger()
    ok4 = ro.adopt_fill(row, 4, paper=True)
    got = [r for r in tl.get_open_trades_live()
           if str(r.get("trade_id")) == "orb-T1"]
    first = (len(got) == 1 and int(got[0]["contracts"]) == 4)
    ok10 = ro.adopt_fill(row, 10, paper=True)
    got = [r for r in tl.get_open_trades_live()
           if str(r.get("trade_id")) == "orb-T1"]
    grew = (len(got) == 1 and int(got[0]["contracts"]) == 10)
    check("S5 a partial then a full fill GROW one record, never two",
          ok4 and ok10 and first and grew,
          f"after 4: {first}, after 10: {grew}, rows={len(got)}")
    check("S5b the record carries the setup's own levels, not defaults",
          got and float(got[0]["underlying_stop"]) == 195.89
          and got[0]["strategy"] == "ORBStrategy")

    # ── S6: the order is not permission to book ────────────────────────────
    # LIVE path with a positions read that lists nothing for this contract.
    import data.tasty_client as tc
    ro.record_placement(order_id="T2", session_date=d, strategy="ORBStrategy",
                        symbol="NVDA  260831C00200000", underlying="NVDA",
                        side="call", strike=200.0, offered_qty=5,
                        offer_price=0.80, direction="long",
                        target_50pct=199.68, structure_stop=195.89,
                        signal_json=json.dumps(SNAP))
    row2 = [r for r in ro.working(d) if r["order_id"] == "T2"][0]
    _real = getattr(tc, "get_open_option_positions", None)
    tc.get_open_option_positions = lambda: []          # book says nothing
    try:
        booked = ro.adopt_fill(row2, 5, paper=False)
    finally:
        if _real is not None:
            tc.get_open_option_positions = _real
    got2 = [r for r in tl.get_open_trades_live()
            if str(r.get("trade_id")) == "orb-T2"]
    check("S6 fills with no matching broker POSITION book nothing",
          booked is False and not got2,
          f"returned {booked!r}, rows={len(got2)}")

    # ── S8: the trade ending ends the offer, whatever the exit reason ─────
    # 🔴 THE CASE THE TRIGGER LIST CANNOT REACH. Offer 10, four fill, the
    # position exits on theta_bleed — not "fully filled", not "past the 50%
    # TP", not "structure stop". The remaining six must not keep standing.
    ro.record_placement(order_id="T3", session_date=d, strategy="ORBStrategy",
                        symbol="NVDA  260831C00196000", underlying="NVDA",
                        side="call", strike=196.0, offered_qty=10,
                        offer_price=1.20, direction="long",
                        target_50pct=199.68, structure_stop=195.89,
                        signal_json=json.dumps(SNAP))
    live_before = len([r for r in ro.working(d) if r["order_id"] == "T3"])
    n = ro.cancel_all_working("position closed: theta_bleed pnl=12.0%",
                              paper=True)
    live_after = [r for r in ro.working(d) if r["order_id"] == "T3"]
    check("S8 an exit on ANY reason cancels the standing remainder",
          live_before == 1 and n >= 1 and not live_after,
          f"before={live_before} cancelled={n} after={len(live_after)}")

    # and position_manager must do it BEFORE re-arming, or nothing left knows
    # which offer belonged to the setup the engine has just forgotten.
    pm = open(os.path.join(_root, "execution", "position_manager.py"),
              encoding="utf-8").read()
    i_cancel = pm.find("cancel_all_working")
    i_rearm = pm.find("notify_position_closed()")
    check("S8b the remainder is cancelled BEFORE the engine re-arms",
          i_cancel != -1 and i_rearm != -1 and i_cancel < i_rearm)

    # ── S9: the sequence after a trade is not "waiting for the break" ─────
    from analysis.orb_engine import ORBState, ORBEngine
    import pandas as pd
    eng = ORBEngine()
    eng._data.orb_high, eng._data.orb_low, eng._data.orb_width = 196.5, 190.15, 6.35
    eng._data.state = ORBState.OPEN_LONG
    eng._rearm()
    st1 = eng.data.state
    outside = pd.DataFrame({"open": [197.0, 197.1], "high": [197.4, 197.3],
                            "low": [196.8, 196.9], "close": [197.2, 197.0]})
    eng._advance_state(outside)
    st2 = eng.data.state
    inside = pd.DataFrame({"open": [196.4, 196.3], "high": [196.6, 196.5],
                           "low": [196.0, 196.1], "close": [196.20, 196.30]})
    eng._advance_state(inside)
    st3 = eng.data.state
    check("S9 after a trade the engine AWAITS RANGE RE-ENTRY, and only claims "
          "WAITING_FOR_BREAK once a closed bar is back inside",
          st1 == ORBState.AWAITING_RANGE_REENTRY
          and st2 == ORBState.AWAITING_RANGE_REENTRY
          and st3 == ORBState.WAITING_FOR_BREAK,
          f"{st1} -> {st2} -> {st3}")

    e2 = ORBEngine()
    e2._data.orb_high, e2._data.orb_low, e2._data.orb_width = 196.5, 190.15, 6.35
    e2._data.state = ORBState.INVALIDATED
    e2._data.invalidation_reason = "close_inside"
    e2._advance_state(inside)
    check("S9b a close_inside invalidation re-arms straight to "
          "WAITING_FOR_BREAK — that one PROVES re-entry",
          e2.data.state == ORBState.WAITING_FOR_BREAK, str(e2.data.state))

    # ── S10: ORB no longer re-arms at SIGNAL time ─────────────────────────
    # 🔑 THE ORIGINAL DEFECT. mark_triggered() at signal time re-armed the
    # engine, and _rearm() WIPES ORBData — a live plan's direction, stop and
    # target erased while the plan was live.
    src_m = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    # ⚠️ THE WINDOW MUST END BEFORE THE RUNAWAY. `RunawayContinuation` calls
    # mark_triggered() on ITS firing, deliberately and documented — "the runaway
    # IS the evidence price never came back for it". A window that ran to the
    # next Priority heading swallowed that call and failed this check on
    # behaviour that is correct.
    _i = src_m.find("orb_sig = _safe_strategy")
    _blk = src_m[_i:src_m.find("RunawayContinuation", _i)]
    # ⚠️ COMMENTS ARE NOT CALLS (WA §20). The r195 note in main.py NAMES
    # mark_triggered() while explaining its removal, and a bare string match
    # went red on that documentation. Strip comment lines and look for a CALL.
    orb_block = "\n".join(l for l in _blk.splitlines()
                          if not l.strip().startswith("#"))
    check("S10 ORB does not mark_triggered() on the signal any more",
          "mark_triggered()" not in orb_block,
          "the engine must stay OPEN_* until the TRADE resolves")

    # ── S7: the supervisor runs before the position branch splits ──────────
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    _ml = src.find("\ndef main_loop(")
    src = src[_ml:] if _ml != -1 else ""
    i_sup = src.find("_supervise_offers(ctx, state)")
    i_branch = src.find("if pos_mgr.has_open_position():")
    check("S7 supervision runs BEFORE has_open_position() splits the loop",
          i_sup != -1 and i_branch != -1 and i_sup < i_branch,
          "an unfilled offer has no position, so the manage branch would "
          "never reach it")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_standing_offer: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
