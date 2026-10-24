#!/usr/bin/env python3
"""
tests/check_orb_restart.py  v1.3
v1.3  2026-09-26  OTV4TEST r149 (EOD.1) — C11 RE-POINTED: the clock is set just past the ORB cutoff
      READ FROM CONFIG (ORB_NO_ENTRY_AFTER_ET, now 15:40 by the operator's all-day debit window)
      instead of a typed 11:30. Same behaviour pinned: past the cutoff a miss EXPIRES.
v1.2  2026-09-24  OTV4TEST r131 — comments only. Operator, 2026-09-24: "A close
      back into the range is a new opportunity full stop." The runaway is
      dormant until a 1m close back inside, no longer for the session; C8's
      RUNAWAY_TAPE never closes back inside, so C8's property (a restart
      REMEMBERS the runaway) is unchanged and no assertion moved. The re-arm
      itself is pinned by check_orb_reentry R1/R1r.
v1.1  2026-08-30  r195 — three cases asserted the literal
      WAITING_FOR_BREAK after a re-arm. r195 splits that into two honest
      states — AWAITING_RANGE_REENTRY when price is outside the range,
      WAITING_FOR_BREAK once a closed bar is back inside — so they now
      assert THE ENGINE RE-ARMED, which is what they were always for.

r95 — A RESTART MUST NOT ERASE THE SESSION, AND MUST NOT BUY A LATE ENTRY.

🔴 THE DEFECT THIS PINS. `_load_range_from_file()` restores the RANGE across a
restart; nothing restored the STATE, so a restarted engine came back to
WAITING_FOR_BREAK with the session's history erased — no break latches, no
attempt count, and no memory of a runaway invalidation.

🔴 THE CASE THAT MATTERS MOST IS C8, AND IT REMOVES A TRADE RATHER THAN ADDING
ONE. After a runaway the engine is deliberately dormant until a 1m close back
inside the range (r131). A restart forgot that and would arm while the runaway
still owned the move.

🔴 AND C2b IS THE OPERATOR'S RULING, 2026-08-24: **"DO NOT TAKE A MISSED ENTRY
as permission to enter LATE... jumping in after it has left the station is not
a remedy for missing it."** A reconstructed OPEN_* is recorded and CONSUMED.
There must be no path from the reach-back to a fired entry, and C2b is what
stops a future edit from quietly opening one.

Measured live 2026-08-24: QQQ's ORB plan was recorded CANCELLED /
WIPED_BY_RESTART @ 706.00 at 09:40 by the crash-loop.

⚠️ BORN RED. Against the pre-r95 engine C1/C8 fail. Verified by neutering
`rebuild_from_tape` — see WORKING_AGREEMENT 21 ("the proof a test is real: it
FAILS against the broken version") and 24 (a canary checks BEHAVIOUR, never a
version string).

⚠️ IT CALLS THE ENGINE, IT DOES NOT READ ITS SOURCE. WORKING_AGREEMENT 21: a
test that asserts on source text proves nothing about runtime. Every case below
drives real transitions and asserts on the resulting state.

Plain script with an exit code, deliberately not pytest (WORKING_AGREEMENT 36:
a red that means "this venv has no pytest" teaches an operator to ignore reds).

Run:  python3 tests/check_orb_restart.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd                                            # noqa: E402
import analysis.orb_engine as oe                               # noqa: E402

FAILURES: list = []
CLOCK = {"t": datetime(2026, 8, 24, 9, 45, 10)}
oe.now_et = lambda: CLOCK["t"]                 # deterministic session clock

ORB_HIGH, ORB_LOW, ORB_WIDTH = 702.0, 700.0, 2.0


def _bar(hh, mm, o, h, l, c):
    return (datetime(2026, 8, 24, hh, mm), o, h, l, c)


# 09:30-09:34 = the opening range 700.00-702.00.
# 09:37 = THE BREAK   (opens 701.6 INSIDE, closes 702.4 OUTSIDE)
# 09:39 = THE RETEST  (wick 701.7 enters the range, body 702.3 stays outside)
# Nothing reaches target_50pct (703.00), so this is a confirm, not a runaway.
CONFIRM_TAPE = [
    _bar(9, 30, 700.5, 702.0, 700.0, 701.0),
    _bar(9, 31, 701.0, 701.8, 700.2, 700.6),
    _bar(9, 32, 700.6, 701.5, 700.1, 701.2),
    _bar(9, 33, 701.2, 701.9, 700.4, 701.5),
    _bar(9, 34, 701.5, 702.0, 701.0, 701.7),
    _bar(9, 35, 701.7, 701.9, 701.1, 701.4),
    _bar(9, 36, 701.4, 701.8, 701.0, 701.6),
    _bar(9, 37, 701.6, 702.6, 701.5, 702.4),      # BREAK
    _bar(9, 38, 702.4, 702.7, 702.2, 702.5),
    _bar(9, 39, 702.3, 702.6, 701.7, 702.3),      # RETEST -> OPEN_LONG
    _bar(9, 40, 702.3, 702.8, 702.2, 702.6),
    _bar(9, 41, 702.6, 702.9, 702.4, 702.7),
    _bar(9, 42, 702.7, 702.9, 702.5, 702.8),
]

# No candle ever opens inside and closes outside — the tape simply drifts
# inside the range. A rebuild must NOT invent a break here.
QUIET_TAPE = [
    _bar(9, 30, 700.5, 702.0, 700.0, 701.0),
    _bar(9, 31, 701.0, 701.8, 700.2, 700.6),
    _bar(9, 32, 700.6, 701.5, 700.1, 701.2),
    _bar(9, 33, 701.2, 701.9, 700.4, 701.5),
    _bar(9, 34, 701.5, 702.0, 701.0, 701.7),
    _bar(9, 35, 701.7, 701.9, 701.1, 701.4),
    _bar(9, 36, 701.4, 701.8, 701.0, 701.6),
    _bar(9, 37, 701.6, 701.9, 701.2, 701.5),
    _bar(9, 38, 701.5, 701.8, 701.1, 701.3),
    _bar(9, 39, 701.3, 701.7, 700.9, 701.4),
]


# 09:37 breaks; price then runs straight to target_50pct (703.00) with no
# retest, which is the RUNAWAY invalidation. The engine goes dormant; nothing
# here closes back inside, so it stays dormant (r131: a close inside re-arms).
RUNAWAY_TAPE = [
    _bar(9, 30, 700.5, 702.0, 700.0, 701.0),
    _bar(9, 31, 701.0, 701.8, 700.2, 700.6),
    _bar(9, 32, 700.6, 701.5, 700.1, 701.2),
    _bar(9, 33, 701.2, 701.9, 700.4, 701.5),
    _bar(9, 34, 701.5, 702.0, 701.0, 701.7),
    _bar(9, 35, 701.7, 701.9, 701.1, 701.4),
    _bar(9, 36, 701.4, 701.8, 701.0, 701.6),
    _bar(9, 37, 701.6, 702.6, 701.5, 702.4),      # BREAK
    _bar(9, 38, 702.4, 703.4, 702.3, 703.2),      # RUNAWAY through 703.00
    _bar(9, 39, 703.2, 703.6, 703.0, 703.4),
    _bar(9, 40, 703.4, 703.8, 703.2, 703.6),
]


# A restart that consumed a MISSED confirmation, and then the tape produces a
# GENUINELY NEW setup: price returns INSIDE the range (09:44), then a fresh
# candle opens inside and closes outside (09:45 = BREAK #2), then a fresh
# retest (09:47). Operator, 2026-08-24: "All subsequent triggers not time
# gated should continue to look for entries."
SECOND_SETUP_TAPE = CONFIRM_TAPE + [
    _bar(9, 43, 702.8, 702.9, 701.4, 701.5),      # back INSIDE the range
    _bar(9, 44, 701.5, 701.9, 701.2, 701.7),      # settles inside
    _bar(9, 45, 701.7, 702.6, 701.6, 702.4),      # BREAK #2 (opens inside)
    _bar(9, 46, 702.4, 702.7, 702.2, 702.5),
    _bar(9, 47, 702.3, 702.6, 701.7, 702.3),      # RETEST #2 -> OPEN_LONG
    _bar(9, 48, 702.3, 702.8, 702.2, 702.6),
]


# 🔴 THE NFLX 2026-08-24 SHAPE, AND THE ONE MY FIRST FIXTURES ALL MISSED.
# Break, close back inside (re-arm #2), break, close back inside (re-arm #3),
# break, retest, CONFIRM. Three attempts, TWO re-arms before the confirmation.
# `_rearm()` REPLACES self._data, so any binding held across the replay is an
# orphan after the first one — which is precisely why C1-C11 stayed green over
# a live bug. Every earlier tape confirmed on attempt #1 and never re-armed.
REARM_TWICE_TAPE = [
    _bar(9, 30, 700.5, 702.0, 700.0, 701.0),
    _bar(9, 31, 701.0, 701.8, 700.2, 700.6),
    _bar(9, 32, 700.6, 701.5, 700.1, 701.2),
    _bar(9, 33, 701.2, 701.9, 700.4, 701.5),
    _bar(9, 34, 701.5, 702.0, 701.0, 701.7),
    _bar(9, 35, 701.7, 701.9, 701.1, 701.4),
    _bar(9, 36, 701.6, 702.5, 701.5, 702.2),      # BREAK #1
    _bar(9, 37, 702.2, 702.4, 701.5, 701.6),      # close INSIDE -> re-arm #2
    _bar(9, 38, 701.6, 702.4, 701.5, 702.1),      # BREAK #2
    _bar(9, 39, 702.1, 702.3, 701.4, 701.5),      # close INSIDE -> re-arm #3
    _bar(9, 40, 701.5, 702.5, 701.4, 702.4),      # BREAK #3
    _bar(9, 41, 702.3, 702.6, 701.7, 702.3),      # RETEST -> CONFIRMED
    _bar(9, 42, 702.3, 702.7, 702.2, 702.5),
]


def _frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c} for _, o, h, l, c in rows],
        index=pd.DatetimeIndex([t for t, *_ in rows]))


def _armed(engine):
    """Give the engine today's range, exactly as _load_range_from_file would."""
    d = engine._data
    d.orb_high, d.orb_low, d.orb_width = ORB_HIGH, ORB_LOW, ORB_WIDTH
    d.state = oe.ORBState.WAITING_FOR_BREAK
    engine._range_date = "2026-08-24"
    return engine


def _live(engine, rows, lo, hi):
    """Drive the engine the way main_loop does: one tick per bar, each tick
    handing it the frame up to and including the forming bar."""
    df = _frame(rows)
    for i in range(lo, hi + 1):
        CLOCK["t"] = datetime(2026, 8, 24, rows[i][0].hour, rows[i][0].minute, 10)
        engine.update(None, df.iloc[:i + 1], float(rows[i][4]), None)
    return engine.data.state


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


# r195 — a re-arm now lands in one of TWO honest states, so these checks assert
# "the engine re-armed", not a single label.
# 🔑 AWAITING_RANGE_REENTRY IS STILL RE-ARMED. It says the attempt is over and
# price is outside the range; a break can only register from a candle that
# OPENS INSIDE, so nothing can arm from there anyway. Loosening to "either" is
# not weakening the check — the thing these cases exist to prove is that the
# engine did NOT stay OPEN and did NOT chase, and both states prove that.
_REARMED = None


def _rearmed(st) -> bool:
    import analysis.orb_engine as _oe
    return st in (_oe.ORBState.WAITING_FOR_BREAK,
                  _oe.ORBState.AWAITING_RANGE_REENTRY)


def main() -> int:
    print("check_orb_restart — a restart must not cost the ORB day")

    # ── C1: THE DEFECT ITSELF ────────────────────────────────────────────────
    # A process that ran the whole session and a process restarted between the
    # break and the retest must reach the SAME state from the SAME tape.
    CLOCK["t"] = datetime(2026, 8, 24, 9, 45, 10)
    cont = _armed(oe.ORBEngine())
    continuous = _live(cont, CONFIRM_TAPE, 1, len(CONFIRM_TAPE) - 1)

    pre = _armed(oe.ORBEngine())
    _live(pre, CONFIRM_TAPE, 1, 9)                  # dies mid-setup
    post = _armed(oe.ORBEngine())                   # fresh process: range only
    post.rebuild_from_tape(_frame(CONFIRM_TAPE))    # ← the reach-back
    restarted = _live(post, CONFIRM_TAPE, 10, len(CONFIRM_TAPE) - 1)

    check("C1 a continuous run confirms and is tradeable",
          continuous == oe.ORBState.OPEN_LONG, f"continuous={continuous}")

    # THE RULING. The restarted engine must KNOW the attempt happened — the
    # latch and the attempt count are session facts — and must NOT be sitting in
    # a state anything can fire.
    check("C1b a restart LEARNS the session (latch + attempt survive)",
          post.broke_high is True and post.data.attempt_number == 1,
          f"broke_high={post.broke_high} attempt={post.data.attempt_number}")

    check("C2b a MISSED trigger is NOT re-entered (operator ruling)",
          restarted not in (oe.ORBState.OPEN_LONG, oe.ORBState.OPEN_SHORT),
          f"restarted={restarted}")

    check("C2c the consumed attempt re-arms for a FRESH break, not a chase",
          _rearmed(restarted)
          and post.data.orb_high == ORB_HIGH and post.data.orb_low == ORB_LOW,
          f"state={restarted} range={post.data.orb_low}-{post.data.orb_high}")

    # ── C2: IT MUST NOT INVENT A SETUP ───────────────────────────────────────
    # The failure direction that matters. A reach-back that hallucinates a
    # break is worse than the bug it fixes: it trades a setup the tape never
    # produced, and it would look exactly like a recovery.
    quiet = _armed(oe.ORBEngine())
    quiet.rebuild_from_tape(_frame(QUIET_TAPE))
    check("C2 a quiet tape reconstructs NO break",
          quiet.data.state == oe.ORBState.WAITING_FOR_BREAK
          and quiet.data.attempt_number == 0,
          f"state={quiet.data.state} attempt={quiet.data.attempt_number}")

    # ── C3: ONE-SHOT AND IDEMPOTENT ──────────────────────────────────────────
    # A rebuild that ran on every tick would re-replay the break each pass and
    # inflate attempt_number without limit.
    once = _armed(oe.ORBEngine())
    first = once.rebuild_from_tape(_frame(CONFIRM_TAPE))
    attempt_after_first = once.data.attempt_number
    second = once.rebuild_from_tape(_frame(CONFIRM_TAPE))
    check("C3 the reach-back is one-shot per session",
          first is True and second is False
          and once.data.attempt_number == attempt_after_first,
          f"first={first} second={second} attempt={once.data.attempt_number}")

    # ── C4: NO RANGE, NO REPLAY — AND NOT MARKED DONE ────────────────────────
    # Before the range establishes there is nothing to break out of. The guard
    # must stay unset so the rebuild still runs on the tick the range lands;
    # marking it done here would disarm the fix on every early-starting box.
    norange = oe.ORBEngine()
    ran = norange.rebuild_from_tape(_frame(CONFIRM_TAPE))
    check("C4 no range -> no replay, and the guard stays unset",
          ran is False and norange._rebuilt_date is None,
          f"ran={ran} guard={norange._rebuilt_date!r}")

    # ── C5: A CONTINUOUS PROCESS IS UNHARMED ─────────────────────────────────
    # The rebuild runs on every box, including ones that never went down. On
    # those it must be a no-op against the state the live loop already reached.
    healthy = _armed(oe.ORBEngine())
    _live(healthy, CONFIRM_TAPE, 1, len(CONFIRM_TAPE) - 1)
    before = (healthy.data.state, healthy.data.attempt_number,
              healthy.data.stop_level)
    healthy.rebuild_from_tape(_frame(CONFIRM_TAPE))
    after = (healthy.data.state, healthy.data.attempt_number,
             healthy.data.stop_level)
    check("C5 a live process is unchanged by the reach-back",
          before == after, f"{before} -> {after}")

    # ── C6: SESSION RESET RE-ARMS THE REACH-BACK ─────────────────────────────
    # The guard is dated; reset_for_session must clear it or the fix works on
    # day one and silently never again on a box that stays up overnight.
    once.reset_for_session()
    check("C6 reset_for_session clears the rebuild guard",
          once._rebuilt_date is None, f"guard={once._rebuilt_date!r}")

    # ── C7: A RAISING TAPE MUST NOT TAKE THE TICK WITH IT ────────────────────
    bad = _armed(oe.ORBEngine())
    ok = True
    try:
        bad.rebuild_from_tape("not a dataframe")
    except Exception as exc:                                   # noqa: BLE001
        ok = False
        detail = repr(exc)
    check("C7 a malformed frame is swallowed, never raised", ok,
          "" if ok else detail)

    # ── C8: THE CASE THAT REMOVES A TRADE ────────────────────────────────────
    # A runaway invalidation is DORMANT BY DESIGN until a 1m close back inside
    # the range (r131); this tape never closes back inside. A restart that
    # forgets it sits in WAITING_FOR_BREAK and would arm while the runaway
    # still owns the move. This is the reach-back preventing a WRONG trade, not recovering a
    # missed one, and it is the strongest reason the whole mechanism earns its
    # place.
    CLOCK["t"] = datetime(2026, 8, 24, 9, 45, 10)
    rcont = _armed(oe.ORBEngine())
    _live(rcont, RUNAWAY_TAPE, 1, len(RUNAWAY_TAPE) - 1)

    rpost = _armed(oe.ORBEngine())            # fresh process after the runaway
    rpost.rebuild_from_tape(_frame(RUNAWAY_TAPE))

    check("C8 a restart REMEMBERS the runaway and stays dormant",
          rcont.data.state == oe.ORBState.INVALIDATED
          and rpost.data.state == oe.ORBState.INVALIDATED
          and rpost.data.invalidation_reason == "runaway",
          f"continuous={rcont.data.state}/{rcont.data.invalidation_reason} "
          f"restarted={rpost.data.state}/{rpost.data.invalidation_reason}")

    # ── C9: THE BOUNDARY — NORMAL ENTRIES KEEP TRYING ────────────────────────
    # Operator, 2026-08-24: the no-late-entry ruling is "for a recovered orb
    # state only. It does not apply to normal entries. Those should keep
    # trying."
    #
    # ⚠️ THIS IS THE CASE THAT STOPS THE RULING LEAKING. A LIVE confirmation
    # that has not yet been filled — chain fetch failed, liquidity thin, the
    # dispatch slot taken — must stay OPEN and keep being offered on every tick
    # until the 11:00 cutoff. Nothing in the reach-back may touch it. Without
    # this pin, a future edit that "tidies up" by consuming stale confirmations
    # generally would silently delete the ORB's own retry behaviour, and it
    # would look like a cleanup.
    CLOCK["t"] = datetime(2026, 8, 24, 9, 45, 10)
    liveeng = _armed(oe.ORBEngine())
    _live(liveeng, CONFIRM_TAPE, 1, 10)              # reads the 09:39 retest
    confirmed = liveeng.data.state
    # ... and is NOT fired (no mark_triggered) — the tick loop simply keeps
    # running for another three minutes.
    _live(liveeng, CONFIRM_TAPE, 11, len(CONFIRM_TAPE) - 1)
    check("C9 a LIVE unfilled confirmation keeps trying across ticks",
          confirmed == oe.ORBState.OPEN_LONG
          and liveeng.data.state == oe.ORBState.OPEN_LONG,
          f"at_confirm={confirmed} three_bars_later={liveeng.data.state}")

    # And the reach-back running afterwards must not consume it either: on a
    # live box the rebuild fires at boot, but the guard is what makes that
    # true, and a guard is exactly the thing that gets edited.
    liveeng.rebuild_from_tape(_frame(CONFIRM_TAPE))
    check("C9b the reach-back does not consume a LIVE confirmation",
          liveeng.data.state == oe.ORBState.OPEN_LONG,
          f"state={liveeng.data.state}")

    # ── C10: A MISS DOES NOT END THE SESSION ─────────────────────────────────
    # 🔴 Operator, 2026-08-24: "A miss of one firing sequence does not take
    # another valid entry off the table... All subsequent triggers not time
    # gated should continue to look for entries."
    #
    # This is the half that a cautious implementation gets wrong. Consuming the
    # missed attempt must return the engine to WATCHING — not park it. Price
    # comes back inside the range and breaks out again on its own merits; that
    # second setup is a normal entry and must be taken normally.
    CLOCK["t"] = datetime(2026, 8, 24, 9, 41, 10)
    eng2 = _armed(oe.ORBEngine())
    eng2.rebuild_from_tape(_frame(CONFIRM_TAPE))         # consumes the miss
    consumed = eng2.data.state
    # ... and the session carries on, live, from the next bar.
    second = _live(eng2, SECOND_SETUP_TAPE, 13, len(SECOND_SETUP_TAPE) - 1)
    check("C10 after a miss, a FRESH break+retest still fires",
          _rearmed(consumed)
          and second == oe.ORBState.OPEN_LONG
          and eng2.data.attempt_number == 2,
          f"after_miss={consumed} later={second} attempt={eng2.data.attempt_number}")

    check("C10b the re-armed engine is not tainted by the miss",
          eng2.data.break_direction == "long"
          and "missed" not in (eng2.data.invalidation_reason or ""),
          f"reason={eng2.data.invalidation_reason!r}")

    # ── C11: THE TIME GATE IS STILL THE TIME GATE ────────────────────────────
    # "not time gated" is the operator's qualifier and it must keep meaning
    # something. Past ORB's own 11:00 cutoff the missed setup EXPIRES rather
    # than re-arming — the same state a healthy engine reaches at 11:00.
    import config as _cC
    _co = tuple(_cC.ORB_NO_ENTRY_AFTER_ET)             # r149: read, not typed
    CLOCK["t"] = datetime(2026, 8, 24, _co[0], _co[1], 0)
    late = _armed(oe.ORBEngine())
    late.rebuild_from_tape(_frame(CONFIRM_TAPE))
    check(f"C11 at/past the {_co[0]}:{_co[1]:02d} cutoff a miss EXPIRES, it does not re-arm",
          late.data.state == oe.ORBState.EXPIRED,
          f"state={late.data.state}")
    CLOCK["t"] = datetime(2026, 8, 24, 9, 45, 10)

    # ── C12: THE REPLAY MUST NOT READ A CORPSE ───────────────────────────────
    # 🔴 FOUND IN A LIVE LOG, NOT BY A TEST (NFLX 2026-08-24). The reach-back
    # summary printed `state=INVALIDATED attempt=1` one line after logging
    # `CONFIRMED LONG (attempt #3)`. `_rearm()` swaps self._data for a new
    # object, so the local binding was an orphan from the first re-arm onward.
    # The consume check read that orphan, never saw OPEN, wrote no MISSED row,
    # and left the live engine CONFIRMED and tradeable.
    CLOCK["t"] = datetime(2026, 8, 24, 9, 45, 10)
    ra = _armed(oe.ORBEngine())
    ra.rebuild_from_tape(_frame(REARM_TWICE_TAPE))

    check("C12 a replay that re-arms twice still sees the confirmation",
          ra.data.attempt_number == 3,
          f"attempt={ra.data.attempt_number} (expected 3)")

    check("C12b and CONSUMES it — the ruling survives a re-arm",
          _rearmed(ra.data.state),
          f"state={ra.data.state}")

    check("C12c the miss is recorded, not swallowed",
          ra._last_missed is not None
          and ra._last_missed.get("state") == oe.ORBState.OPEN_LONG,
          f"missed={ra._last_missed}")

    # The failure this actually prevents, stated as its own case: a live engine
    # left CONFIRMED by a broken consume would hand the dispatch a reconstructed
    # setup to trade.
    check("C12d the engine is NOT left tradeable after the replay",
          ra.data.state not in (oe.ORBState.OPEN_LONG, oe.ORBState.OPEN_SHORT),
          f"state={ra.data.state}")

    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {', '.join(FAILURES)}")
        return 1
    print("check_orb_restart: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
