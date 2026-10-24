#!/usr/bin/env python3
"""
tests/check_orb_rearm_zone.py  v1.6
v1.6  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.5  2026-09-04  r235 — Z1d RE-DERIVED. It asserted `order_placed` is
      CLEARED on the armed path — r227's fix against a GLOBAL latch, and the
      very behaviour that let ONE retest fire three times once the flag turned
      out never to be set on the single-leg path. Z1d now pins that the SPENT
      confirmation survives the close, and Z1d2 that a fresh retest re-opens
      the gate.
v1.4  2026-09-03  r228 — Z1g-Z1j: a 1m CLOSE back INSIDE the range ends the
      thesis. r221 armed UNCONDITIONALLY — it never consulted where price was
      — so a trade resolving after a re-entry would have stayed armed on a
      dead impulsive candle, and would have overwritten a `close_inside`
      invalidation the tick machinery had already applied. Mirrored on both
      sides.
v1.3  2026-09-03  r227 — Z1d/Z1e/Z1f: the per-confirmation latches are cleared
      and the impulsive candle is not. Without the clear, `order_placed`
      survives and orb_strategy refuses every subsequent retest — verified by
      deleting the line and watching Z1d go red.
v1.2  2026-09-03  r226 — 🔴 THIS FILE WAS WALL-CLOCK DEPENDENT AND WOULD HAVE
      GONE RED EVERY AFTERNOON. `notify_position_closed` compares `now_et()`
      against ORB's own entry cutoff and returns EXPIRED past it, so Z1, Z1c
      and Z3c passed before 11:00 ET and failed after — caught at 11:51 on
      the day it was written. A check whose verdict depends on WHEN it runs
      teaches the suite to be ignored in the afternoon. The clock is frozen
      inside orb_engine's own namespace, since that is where `now_et` is
      resolved.
v1.1  2026-09-03  r222 — S1-S5 MIRROR EVERY CHECK ON THE SHORT SIDE. The
      operator's example was a long and so was every original check; the
      engine's geometry is symmetric but r221's `long_side` flag decides the
      DIRECTION of the `beyond` comparison, and a flipped comparison would
      accept a short's 50% the instant price ROSE — handing every short to
      the runaway immediately. S2 is that check.
v1.0  2026-09-03  r221 — THE BAND BETWEEN THE BOUNDARY AND THE 50% HAD NO OWNER.

🔴 `notify_position_closed` ALWAYS CALLED `_rearm()`, WHICH WIPES ORBData. The
impulsive candle went with it and the engine sat in AWAITING_RANGE_REENTRY, so
a second retest of the boundary FROM OUTSIDE could arm nothing. Meanwhile the
runaway will not take the move until a 1m close beyond `target_50pct` HOLDS.
Measured on NVDA, 2026-09-03: broke 227.43, retested, entered, exited in
profit — and 227.43 -> 228.77 was owned by NO strategy.

🔑 A RETEST AND A RE-ENTRY ARE DIFFERENT EVENTS. The operator's correction, and
the distinction the whole change rests on:
  · RETEST   = wick into the range, close back OUTSIDE. A TEST. Fires a trade,
               leaves the impulsive candle intact.
  · RE-ENTRY = a CLOSE back INSIDE the range. ACCEPTANCE. Terminates the
               thesis; a fresh break must set a new impulsive candle.
"Wicks are tests & closes are acceptance."

⚠️ AND THE 50% HANDOFF USES THE RUNAWAY'S OWN TWO-PART TEST. Standing down on a
TOUCH of the 50% would end the ORB thesis while the runaway never armed —
re-opening the same gap one level higher.

Born red at 9b29ec5 (r220), where Z1 and Z4 fail.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def _bars(closed_bar_close, forming=None, closed_high=None):
    """Bars where the CLOSED candle is `iloc[-2]`, as the engine reads it.

    🔴 MY FIRST FIXTURE PUT THE TEST BAR AT `iloc[-1]` AND PROVED NOTHING.
    Every latch in orb_engine reads `df_1m.iloc[-2]` — the last CLOSED candle;
    `iloc[-1]` is still forming. Z2 "passed" against a wick it never examined.
    I read that convention in the source and then did not apply it, so the
    helper now makes the closed bar explicit and impossible to misplace.
    """
    import pandas as pd
    c0 = float(closed_bar_close)
    c1 = float(c0 if forming is None else forming)
    h0 = float(c0 + .05 if closed_high is None else closed_high)
    return pd.DataFrame({"open":  [c0, c1],
                         "high":  [h0, c1 + .05],
                         "low":   [c0 - .05, c1 - .05],
                         "close": [c0, c1]})


def main():
    from analysis import orb_engine as OE

    # 🔴 THIS SUITE WAS WALL-CLOCK DEPENDENT AND WOULD HAVE GONE RED EVERY
    # AFTERNOON. `notify_position_closed` compares `now_et()` against ORB's own
    # cutoff and returns EXPIRED past it, so Z1/Z1c/Z3c passed before 11:00 ET
    # and failed after — caught at 11:51 on 2026-09-03, hours after the file
    # was written and "green". A check whose verdict depends on when it runs is
    # worse than no check: it teaches the suite to be ignored in the afternoon.
    # ⚠️ FROZEN INSIDE THE ENGINE'S MODULE, not globally — the engine resolves
    # `now_et` from its own namespace, and patching anywhere else would leave
    # the real clock in play.
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI
    _FROZEN = _dt(2026, 9, 3, 10, 15, tzinfo=_ZI("America/New_York"))
    OE.now_et = lambda: _FROZEN

    def armed_long_engine():
        """An engine mid-setup: broke 227.43 long, impulse candle recorded."""
        e = OE.ORBEngine() if hasattr(OE, "ORBEngine") else OE.get_orb_engine()
        d = OE.ORBData()
        d.state = OE.ORBState.OPEN_LONG
        d.orb_high, d.orb_low = 227.43, 226.23
        d.orb_width = d.orb_high - d.orb_low
        d.break_candle_low, d.break_candle_high = 226.90, 227.60
        d.break_direction = "LONG"
        d.stop_distance_px = 0.53
        d.target_50pct = d.orb_high + d.orb_width * 0.5      # 228.03
        d.attempt_number = 1
        e._data = d
        return e, d

    # ── Z1 — A RESOLVED TRADE IN THE ZONE STAYS ARMED ───────────────────
    # ⚠️ READ `e._data`, NEVER A HELD REFERENCE. r96's lesson: `_rearm()`
    # REPLACES ORBData wholesale, so a `d` captured before the call is stale
    # and still reports OPEN_LONG. My first draft asserted against that stale
    # object and so would have passed on the OLD code for the wrong reason —
    # the engine is the source of truth, not a snapshot of it.
    e, _d0 = armed_long_engine()
    e.notify_position_closed()
    d = e._data
    check("Z1 a resolved trade with the 50% unaccepted stays ARMED_LONG",
          d.state == OE.ORBState.ARMED_LONG, d.state)

    # 🔑 THE IMPULSIVE CANDLE IS THE POINT. `_rearm()` wipes ORBData, so if it
    # ran, the stop geometry is gone and the next retest would size off 0.0 —
    # the sizer's "degenerate branch takes it to a 1-lot loudly".
    check("Z1b the ORIGINAL impulsive candle and stop distance survive",
          abs(d.break_candle_low - 226.90) < 1e-9
          and abs(d.stop_distance_px - 0.53) < 1e-9,
          f"candle {d.break_candle_low} dist {d.stop_distance_px}")
    check("Z1c the attempt number advances",
          d.attempt_number == 2, str(d.attempt_number))

    # ── Z1d — THE PER-CONFIRMATION LATCHES ARE CLEARED ──────────────────
    # 🔴 THE FAILURE r221 WOULD HAVE SHIPPED, AND IT IS A QUIET ONE.
    # `order_placed` is r207's one-confirmation-one-order latch, and its own
    # comment reads "`_rearm()` builds a fresh ORBData, so the next attempt
    # starts clean WITHOUT ANYONE CLEARING IT" — true until r221 stopped
    # calling `_rearm()` on this path to keep the impulsive candle. The flag
    # then survives, `orb_strategy` refuses on it with "this confirmation is
    # SPENT", and the engine sits ARMED and declines EVERY retest for the rest
    # of the session. An armed engine that never fires looks exactly like a
    # market with no setups.
    # 🔑 THE GENERAL RULE THIS PINS: not rebuilding ORBData means every field
    # scoped to ONE CONFIRMATION must be cleared BY NAME. The impulsive candle
    # and the 50% latches are kept deliberately; these are not.
    # 🔴 Z1d RE-DERIVED AT r235. It asserted `order_placed` is CLEARED here —
    # r227's fix against a GLOBAL latch, and the very behaviour that let ONE
    # retest fire three times once the flag turned out never to be set on the
    # single-leg path. The latch is now per-confirmation: the seq is what
    # re-opens the gate, so clearing the flag here would restore the defect.
    e2, _ = armed_long_engine()
    e2._data.confirmation_seq = 1
    e2._data.order_placed = True
    e2._data.order_placed_seq = 1
    e2._data.confirmed_at = "2026-09-03T10:05:00"
    e2._data.retest_depth_px = 0.42
    e2.notify_position_closed()
    d2 = e2._data
    check("Z1d the SPENT confirmation survives the close (r235)",
          # spent stays spent across the close, AND a fresh retest re-opens it
          d2.order_placed_seq == d2.confirmation_seq == 1
          and __import__("strategy.orb_strategy", fromlist=["x"]
                         ).confirmation_spent(d2),
          f"cseq={d2.confirmation_seq} oseq={d2.order_placed_seq}")
    d2.confirmation_seq += 1                      # a genuinely new retest
    check("Z1d2 and a FRESH qualifying retest re-opens the gate",
          not __import__("strategy.orb_strategy", fromlist=["x"]
                         ).confirmation_spent(d2),
          f"cseq={d2.confirmation_seq} oseq={d2.order_placed_seq}")
    d2.confirmation_seq -= 1
    check("Z1e and the other per-confirmation fields reset",
          d2.confirmed_at == "" and d2.retest_depth_px == 0.0,
          f"confirmed_at={d2.confirmed_at!r} depth={d2.retest_depth_px}")
    check("Z1f while the impulsive candle and 50% latches SURVIVE",
          abs(d2.break_candle_low - 226.90) < 1e-9
          and abs(d2.stop_distance_px - 0.53) < 1e-9
          and abs(d2.target_50pct - 228.03) < 1e-9,
          f"candle {d2.break_candle_low} dist {d2.stop_distance_px} "
          f"tp50 {d2.target_50pct}")

    # ── Z1g — A CLOSE BACK INSIDE THE RANGE ENDS THE THESIS ─────────────
    # 🔴 r221 SHIPPED WITHOUT THIS TEST AND ARMED UNCONDITIONALLY. The
    # operator's rule is explicit: the setup survives a resolved trade ONLY IF
    # PRICE IS STILL OUTSIDE. A 1m CLOSE back inside is a RE-ENTRY —
    # ACCEPTANCE, not a test — so the impulsive candle is dead and a fresh
    # break must set a new one.
    # ⚠️ AND UNCONDITIONAL ARMING WOULD HAVE OVERWRITTEN a `close_inside`
    # invalidation the tick machinery had already applied, resurrecting a
    # thesis the tape had just killed.
    e3, _ = armed_long_engine()
    e3._update_break_latches(_bars(226.80))     # closed INSIDE 226.23-227.43
    check("Z1g the engine records that the close was inside the range",
          e3._data.last_close_inside is True, str(e3._data.last_close_inside))
    e3.notify_position_closed()
    check("Z1h a trade resolving after a close INSIDE does not stay armed",
          e3._data.state != OE.ORBState.ARMED_LONG, e3._data.state)
    check("Z1i and the impulsive candle is GONE — a fresh break must set one",
          e3._data.break_candle_low == 0.0 and e3._data.stop_distance_px == 0.0,
          f"candle {e3._data.break_candle_low} dist {e3._data.stop_distance_px}")

    # ⚠️ MIRRORED: for a SHORT the range is above, and the same close is inside.
    e4 = OE.ORBEngine() if hasattr(OE, "ORBEngine") else OE.get_orb_engine()
    d4 = OE.ORBData()
    d4.state = OE.ORBState.OPEN_SHORT
    d4.orb_high, d4.orb_low = 227.43, 226.23
    d4.orb_width = 1.20
    d4.break_candle_high, d4.break_candle_low = 226.76, 226.10
    d4.break_direction = "short"
    d4.stop_distance_px = 0.53
    d4.target_50pct = 225.63
    e4._data = d4
    e4._update_break_latches(_bars(226.80))
    e4.notify_position_closed()
    check("Z1j the same rule holds on the SHORT side",
          e4._data.state != OE.ORBState.ARMED_SHORT, e4._data.state)

    # ── Z2 — A WICK THROUGH THE 50% ARMS NOTHING ────────────────────────
    # ⚠️ Wicks are tests. The tracker reads the CLOSED candle, so a bar whose
    # HIGH pierces 228.03 while its CLOSE sits below must not hand the move to
    # the runaway.
    e, d = armed_long_engine()
    import pandas as pd
    # the CLOSED bar wicks to 228.60 and closes at 227.80 — below the 50%
    e._update_break_latches(_bars(227.80, forming=227.85, closed_high=228.60))
    d = e._data
    check("Z2 a WICK through the 50% does not accept it",
          not d.fifty_accepted and not d.fifty_pending,
          f"accepted={d.fifty_accepted} pending={d.fifty_pending}")

    # ── Z3 — A CLOSE BEYOND THAT DOES NOT HOLD IS DISCARDED ─────────────
    # ⚠️ The runaway requires the hold at the next tick. A close that reverses
    # immediately is a wick with extra steps, and the ORB setup must stand.
    e, d = armed_long_engine()
    e._update_break_latches(_bars(228.40))              # closed beyond -> pending
    check("Z3 one close beyond the 50% is PENDING, not accepted",
          d.fifty_pending and not d.fifty_accepted,
          f"pending={d.fifty_pending}")
    e._update_break_latches(_bars(227.90))              # fell back
    check("Z3b a pending close that does not hold is cleared",
          not d.fifty_pending and not d.fifty_accepted)
    e.notify_position_closed()
    check("Z3c and the ORB is still armed after that failed acceptance",
          e._data.state == OE.ORBState.ARMED_LONG, e._data.state)

    # ── Z4 — ACCEPTED 50% HANDS THE MOVE TO THE RUNAWAY ─────────────────
    # 🔴 "If it reaches the 50, then the runaway owns it unequivocally — that
    # move in itself invalidates an ORB trade."
    e, d = armed_long_engine()
    e._update_break_latches(_bars(228.40))              # close beyond
    e._update_break_latches(_bars(228.50))              # held
    check("Z4 a close beyond the 50% that HOLDS is accepted",
          d.fifty_accepted, f"accepted={d.fifty_accepted}")
    e.notify_position_closed()
    check("Z4b an accepted 50% stands the ORB down as 'runaway'",
          e._data.state == OE.ORBState.INVALIDATED
          and e._data.invalidation_reason == "runaway",
          f"{e._data.state}/{e._data.invalidation_reason}")

    # ── Z4c — AN ALREADY-ARMED ENGINE STANDS DOWN ON ACCEPTANCE ─────────
    # 🔴 `fifty_accepted` WAS ONLY CONSULTED IN `notify_position_closed`, so an
    # engine ARMED at the moment acceptance landed stayed armed — and would
    # still fire on a retest of a boundary the move had long since left behind.
    # Operator: "if it reaches the 50, then the runaway owns it unequivocally —
    # that move in itself invalidates an ORB trade."
    e5, _ = armed_long_engine()
    e5._data.state = OE.ORBState.ARMED_LONG
    e5._update_break_latches(_bars(228.40))
    e5._update_break_latches(_bars(228.50))
    check("Z4c an ARMED engine stands down when the 50% is accepted",
          e5._data.state == OE.ORBState.INVALIDATED
          and e5._data.invalidation_reason == "runaway",
          f"{e5._data.state}/{e5._data.invalidation_reason}")

    # ⚠️ BUT A LIVE POSITION IS NEVER TOUCHED. The exit engine manages an open
    # trade; standing the ENGINE down must not reach into one that is running.
    e6, _ = armed_long_engine()          # state is OPEN_LONG
    e6._update_break_latches(_bars(228.40))
    e6._update_break_latches(_bars(228.50))
    check("Z4d a LIVE position is left alone by the stand-down",
          e6._data.state == OE.ORBState.OPEN_LONG, e6._data.state)

    # ── Z5 — ACCEPTANCE IS A LATCH ──────────────────────────────────────
    # ⚠️ Once the runaway owns the move it keeps it for the session, even if
    # price falls back. Same discipline as broke_high/broke_low.
    e, d = armed_long_engine()
    e._update_break_latches(_bars(228.40))
    e._update_break_latches(_bars(228.50))
    e._update_break_latches(_bars(227.50))              # well back below
    check("Z5 acceptance does not clear when price falls back",
          d.fifty_accepted)

    # ══ THE SHORT SIDE, MIRRORED ════════════════════════════════════════
    # ⚠️ EVERY CHECK ABOVE USED A LONG BECAUSE THE OPERATOR'S EXAMPLE WAS ONE.
    # Symmetry in the engine's geometry (target_50pct = orb_low - width/2,
    # stop = break_candle_high) does NOT prove symmetry in r221's additions:
    # `long_side` decides the direction of the `beyond` comparison, and getting
    # it wrong makes a SHORT accept the 50% the instant price rises — handing
    # every short to the runaway immediately.
    def armed_short_engine():
        e2 = OE.ORBEngine() if hasattr(OE, "ORBEngine") else OE.get_orb_engine()
        d2 = OE.ORBData()
        d2.state = OE.ORBState.OPEN_SHORT
        d2.orb_high, d2.orb_low = 227.43, 226.23
        d2.orb_width = d2.orb_high - d2.orb_low
        d2.break_candle_low, d2.break_candle_high = 226.10, 226.76
        d2.break_direction = "short"
        d2.stop_distance_px = 0.53
        d2.target_50pct = d2.orb_low - d2.orb_width * 0.5      # 225.63
        d2.attempt_number = 1
        e2._data = d2
        return e2, d2

    # ── S1 — a resolved SHORT in the zone stays ARMED_SHORT ─────────────
    e, _ = armed_short_engine()
    e.notify_position_closed()
    d = e._data
    check("S1 a resolved SHORT stays ARMED_SHORT",
          d.state == OE.ORBState.ARMED_SHORT, d.state)
    check("S1b the short's impulsive candle (the HIGH) survives",
          abs(d.break_candle_high - 226.76) < 1e-9
          and abs(d.stop_distance_px - 0.53) < 1e-9,
          f"candle {d.break_candle_high} dist {d.stop_distance_px}")

    # ── S2 — price RISING must not accept a short's 50% ─────────────────
    # 🔴 THE CHECK THAT CATCHES A FLIPPED COMPARISON. A short's 50% is BELOW
    # the range at 225.63. If `beyond` used `>` for a short, a close at 228
    # would "accept" it and hand every short to the runaway at once.
    e, _ = armed_short_engine()
    e._update_break_latches(_bars(228.00))
    check("S2 a close far ABOVE does not accept a SHORT's 50%",
          not e._data.fifty_pending and not e._data.fifty_accepted,
          f"pending={e._data.fifty_pending} accepted={e._data.fifty_accepted}")

    # ── S3 — a wick BELOW the short's 50% tests, does not accept ────────
    e, _ = armed_short_engine()
    e._update_break_latches(_bars(225.80, forming=225.85, closed_high=226.0))
    # the closed bar's LOW is 225.75 — through 225.63 — but it CLOSED at 225.80
    check("S3 a wick through a SHORT's 50% does not accept it",
          not e._data.fifty_accepted, str(e._data.fifty_accepted))

    # ── S4 — close BELOW that holds accepts, and stands the ORB down ────
    e, _ = armed_short_engine()
    e._update_break_latches(_bars(225.40))      # closed beyond -> pending
    check("S4 a SHORT close below the 50% is pending",
          e._data.fifty_pending and not e._data.fifty_accepted)
    e._update_break_latches(_bars(225.30))      # held
    check("S4b and holding accepts it",
          e._data.fifty_accepted, str(e._data.fifty_accepted))
    e.notify_position_closed()
    check("S4c an accepted SHORT 50% stands the ORB down as 'runaway'",
          e._data.state == OE.ORBState.INVALIDATED
          and e._data.invalidation_reason == "runaway",
          f"{e._data.state}/{e._data.invalidation_reason}")

    # ── S5 — a pending SHORT close that reverses is cleared ─────────────
    e, _ = armed_short_engine()
    e._update_break_latches(_bars(225.40))
    e._update_break_latches(_bars(225.90))      # back above the 50%
    check("S5 a SHORT pending close that does not hold is cleared",
          not e._data.fifty_pending and not e._data.fifty_accepted)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_orb_rearm_zone: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
