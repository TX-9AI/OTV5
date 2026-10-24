#!/usr/bin/env python3
"""
tests/check_orb_reentry.py  v1.3
v1.3  2026-10-02  OTV4TEST r187 (ROSTER.1) — RE-POINTED BY THE RULING, NOT LOOSENED:
      the strategy is OFF by default from r187; this checker tests its LOGIC,
      so it switches it on for its own run (OT_ORB_TRADE=1). check_trade_switches pins the default.
v1.2  2026-09-26  OTV4TEST r149 (EOD.1) — R1c RE-POINTED: the flat tape now runs to the ORB cutoff
      READ FROM CONFIG (ORB_NO_ENTRY_AFTER_ET, 15:40 by the operator's all-day debit window) and the
      close inside lands AT it, instead of a typed 11:30. The pinned behaviour is unchanged.
v1.1  2026-09-24  OTV4TEST r131b — THE LINE IS OUTSIDE; THE BREAK BAR ONLY ARMS;
      THE STOP MUST SIT IN THE RANGE. Operator, same day: "No, never. If this
      happens, we wait for a valid retest." / "the candle that started inside
      the range and closed at the very top of the range, but did not go past.
      It is the break, if the very next candle opens on the range and moves
      away that's not a retest." / "The stop should be inside the opening
      range to be a valid set up, and the sizing is based on the depth of
      that candles, extreme." R4 RE-POINTED (v1.0 pinned at-the-line = inside;
      the property "no tolerance at the boundary" moves to the new
      convention). Added R4e/R4f, S1-S4, V1-V4, L1-L2.
v1.0  2026-09-24  OTV4TEST r131 — A RUNAWAY ENDS THIS BREAK, NOT THE SESSION;
      "OPENS INSIDE" IS THE PREVIOUS CLOSE; NO TOLERANCE AT THE BOUNDARY.

THE OPERATOR'S RULINGS, 2026-09-24:
  (1) "A close back into the range is a new opportunity full stop."
  (2) "It obviously opened inside because the previous candle closed inside."
      (09-24 09:58 printed its open at 736.06, 4c above the 736.02 range
      high, while 09:57 closed 735.97 inside.)
  (3) "keep it pegged to what the tape actually does" — no cents buffer.
PLAN_SPEC §29.1: the runaway means "ORB is finished on THIS break"; §29.6:
"No limit on qualifying setups per session". Before r131 the engine made a
runaway terminal for the session and orb_plan refused every tick after it.

Every case DRIVES the real `analysis.orb_engine.ORBEngine` through `update()`
— the live loop's entry point, latches and 50% acceptance included — one tick
per 1m bar with the forming bar in the frame (the harness of
check_orb_restart._live), on synthetic bars built TO THE SPEC above. R5 drives
the real `strategy.orb_plan.ORBPlan.prepare()` on that engine.

Range 700.00-702.00, width 2.00, long 50% = 703.00, short 50% = 699.00.
Boundary convention (r131b): at-or-beyond the line = OUTSIDE, strictly between
= INSIDE. A close exactly ON a boundary is a break and never "back inside". A
break candle's range-side extreme ON the line counts as within the range.

  R1  after a runaway, a 1m CLOSE back inside re-arms to WAITING_FOR_BREAK;
      closes that stay outside keep it dormant; past the cutoff it EXPIRES;
      a restart's tape replay re-arms the same way (R1r)
  R2  the next fresh impulsive candle arms a NEW attempt with ITS OWN stop
      (its low for a long, its high for a short), fresh 50% latches
  R3  a bar whose own open is OUTSIDE but whose previous close was INSIDE is
      an impulsive candle (both sides); it is not its own retest; a bar whose
      previous close AND own open are outside is still not a break
  R4  no tolerance: a close ON the line does not re-arm a runaway, 1c inside
      does; a close ON the line is the break; after a break it is not inside
  S   (2) the break bar is never its own retest; (c) a bar opening ON the line
      is not a retest (body strictly outside); the 09-22 09:34/09:35 shape;
      a restart replay does not read 09:30-09:33 bars
  V   (b) stop = the candle's range-side extreme; ON the line is valid; wholly
      outside the range is refused by name and the engine keeps waiting
  L   last_close_inside and AWAITING_RANGE_REENTRY: the line is outside
  R5  orb_plan no longer refuses with the RUNAWAY reason after the re-arm
  R6  unchanged: a runaway still hands off; a retest still fires; a
      close-inside still re-arms; a restart replays to the same state

BORN RED on b1b6594 (v1.1, 27 of 38): R1 R1s R1r R2 R2b R2s R3 R3b R3c R3s R3e
R4b-R4f S1 S2 S3 S3s V1 V2 V3 V4 L1 L2 R5. Green there and here (the unchanged
half of each property, or a guard on new behaviour): R1c R3d R4a S2b S4 V2b
R6a-R6e.

Plain script with an exit code (WORKING_AGREEMENT 36).
Run:  python3 tests/check_orb_reentry.py
"""

from __future__ import annotations
import os as _os_r187
_os_r187.environ["OT_ORB_TRADE"] = "1"   # r187: test the strategy's logic switched on

import os
import sqlite3
import sys
from datetime import datetime

import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path: sys.path.insert(1, _sp)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging                                                   # noqa: E402
logging.disable(logging.CRITICAL)

import pandas as pd                                              # noqa: E402
import analysis.orb_engine as oe                                 # noqa: E402

S = oe.ORBState
FAILED: list = []
DAY = (2026, 9, 24)
CLOCK = {"t": datetime(*DAY, 9, 35, 10)}
oe.now_et = lambda: CLOCK["t"]                   # deterministic session clock

HI, LO, W = 702.00, 700.00, 2.00


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def B(hh, mm, o, h, l, c):
    return (datetime(*DAY, hh, mm), o, h, l, c)


RANGE = [                                         # the 09:30 five-minute bar
    B(9, 30, 700.5, 702.0, 700.0, 701.0),
    B(9, 31, 701.0, 701.8, 700.2, 700.6),
    B(9, 32, 700.6, 701.5, 700.1, 701.2),
    B(9, 33, 701.2, 701.9, 700.4, 701.5),
    B(9, 34, 701.5, 702.0, 701.0, 701.7),
]


def _frame(rows):
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c} for _, o, h, l, c in rows],
        index=pd.DatetimeIndex([t for t, *_ in rows]))


class Drive:
    """The engine, fed the way main_loop feeds it: one update() per bar,
    each tick handing it the frame up to and including the FORMING bar, so
    the bar just appended becomes iloc[-2] on the next step."""

    def __init__(self, rows=None, base=None):
        self.e = oe.ORBEngine()
        d = self.e._data
        d.orb_high, d.orb_low, d.orb_width = HI, LO, W
        d.state = S.WAITING_FOR_BREAK
        self.e._range_date = "%04d-%02d-%02d" % DAY
        self.rows = list(RANGE if base is None else base)
        for r in rows or []:
            self.bar(*r)

    def bar(self, hh, mm, o, h, l, c):
        """Close bar hh:mm; the tick is read at hh:(mm+1):10."""
        self.rows.append(B(hh, mm, o, h, l, c))
        t = self.rows[-1][0]
        m = t.hour * 60 + t.minute + 1
        forming = (datetime(*DAY, m // 60, m % 60), c, c, c, c)
        CLOCK["t"] = datetime(*DAY, m // 60, m % 60, 10)
        self.e.update(None, _frame(self.rows + [forming]), c, None)
        return self

    @property
    def d(self):
        return self.e.data                        # re-read: _rearm replaces it

    def st(self):
        return f"{self.d.state}/{self.d.invalidation_reason or '-'}"


# ── the runaway tapes, long and short ───────────────────────────────────────
def runaway_long():
    return Drive([
        (9, 35, 701.7, 701.9, 701.1, 701.4),      # inside
        (9, 36, 701.6, 702.6, 701.5, 702.4),      # BREAK #1 long, stop 701.5
        (9, 37, 702.4, 703.4, 702.3, 703.2),      # close beyond the 50% 703.00
        (9, 38, 703.2, 703.6, 703.0, 703.4),      # ... and it holds -> RUNAWAY
    ])


def runaway_short():
    return Drive([
        (9, 35, 700.3, 700.9, 700.1, 700.6),
        (9, 36, 700.4, 700.5, 699.4, 699.6),      # BREAK #1 short, stop 700.5
        (9, 37, 699.6, 699.7, 698.6, 698.8),      # close beyond the 50% 699.00
        (9, 38, 698.8, 699.0, 698.4, 698.6),      # ... held -> RUNAWAY
    ])


def main() -> int:
    # ── R6a a runaway still hands off, and stays dormant while outside ──────
    rl = runaway_long()
    r6a0 = rl.st()
    rl.bar(9, 39, 703.4, 703.5, 702.5, 702.6)     # back under the 50%, still OUTSIDE
    rl.bar(9, 40, 702.6, 702.9, 702.1, 702.2)     # still outside the range
    check("R6a a runaway still hands off (INVALIDATED/runaway) and stays dormant "
          "while every close is still outside the range",
          r6a0 == "INVALIDATED/runaway" and rl.st() == "INVALIDATED/runaway",
          f"at runaway={r6a0} two outside closes later={rl.st()}")

    # ── R1 a close back inside re-arms the engine ───────────────────────────
    rl.bar(9, 41, 702.2, 702.3, 701.6, 701.8)     # CLOSE INSIDE
    check("R1 after a runaway, a 1m CLOSE back inside re-arms to WAITING_FOR_BREAK "
          "(not INVALIDATED/terminal)",
          rl.d.state == S.WAITING_FOR_BREAK, rl.st())
    rs = runaway_short()
    r1s0 = rs.st()
    rs.bar(9, 39, 698.6, 700.4, 698.5, 700.2)     # CLOSE INSIDE (short side)
    check("R1s the short mirror: runaway, then a close inside re-arms",
          r1s0 == "INVALIDATED/runaway" and rs.d.state == S.WAITING_FOR_BREAK,
          f"{r1s0} -> {rs.st()}")
    late = runaway_long()
    import config as _cR
    _co = tuple(_cR.ORB_NO_ENTRY_AFTER_ET)             # r149: read, not typed
    for t in range(9 * 60 + 39, _co[0] * 60 + _co[1]):
        late.bar(t // 60, t % 60, 703.4, 703.6, 703.2, 703.4)
    late.bar(_co[0], _co[1], 703.4, 703.5, 701.5, 701.6)  # inside, read a minute after the cutoff
    check("R1c the same window as the close-inside path: a close inside after the "
          "cutoff re-arms nothing (EXPIRED)", late.d.state == S.EXPIRED, late.st())

    # ── R2 the next fresh impulsive candle arms a NEW attempt ───────────────
    old_stop = 701.5
    rl.bar(9, 42, 701.8, 701.9, 701.3, 701.5)     # settles inside
    rl.bar(9, 43, 701.5, 702.5, 701.2, 702.3)     # BREAK #2: opens inside, low 701.2
    d = rl.d
    check("R2 the fresh candle arms ARMED_LONG with ITS OWN stop (its low 701.20, "
          "not the dead candle's 701.50), attempt #2, fresh 50% latches",
          d.state == S.ARMED_LONG and abs(d.stop_level - 701.2) < 1e-9
          and abs(d.break_candle_low - 701.2) < 1e-9 and d.stop_level != old_stop
          and d.attempt_number == 2 and not d.fifty_accepted and not d.fifty_pending
          and abs(d.stop_distance_px - 0.8) < 1e-9,
          f"{rl.st()} stop={d.stop_level} low={d.break_candle_low} attempt="
          f"{d.attempt_number} fifty={d.fifty_pending}/{d.fifty_accepted}")
    rl.bar(9, 44, 702.3, 702.6, 701.9, 702.2)     # RETEST: wick in, body outside
    check("R2b ... and its retest FIRES (OPEN_LONG) on the new candle's stop",
          rl.d.state == S.OPEN_LONG and abs(rl.d.stop_level - 701.2) < 1e-9, rl.st())
    rs.bar(9, 40, 700.2, 700.4, 699.9, 700.1)     # inside
    rs.bar(9, 41, 700.1, 700.8, 699.5, 699.7)     # BREAK #2 short: high 700.8
    check("R2s the short mirror: its own stop is its HIGH (700.80, not 700.50)",
          rs.d.state == S.ARMED_SHORT and abs(rs.d.stop_level - 700.8) < 1e-9
          and rs.d.attempt_number == 2,
          f"{rs.st()} stop={rs.d.stop_level} attempt={rs.d.attempt_number}")

    # ── R3 the previous close is the candle's origin ────────────────────────
    p = Drive([(9, 35, 701.7, 701.95, 701.5, 701.97)])        # closes 701.97 INSIDE
    p.bar(9, 36, 702.04, 702.5, 701.95, 702.3)   # opens 702.04 OUTSIDE, closes 702.30
    check("R3 own open 702.04 OUTSIDE, previous close 701.97 INSIDE -> an impulsive "
          "candle: ARMED_LONG, stop = its low 701.95",
          p.d.state == S.ARMED_LONG and abs(p.d.stop_level - 701.95) < 1e-9
          and p.d.attempt_number == 1, f"{p.st()} stop={p.d.stop_level}")
    check("R3b that candle is NOT its own retest (its wick 701.95 touched the range "
          "with its body 702.04-702.30 outside, and it stayed ARMED, not OPEN)",
          p.d.state == S.ARMED_LONG, p.st())
    p.bar(9, 37, 702.3, 702.4, 701.98, 702.1)    # a LATER bar: wick in, body out
    check("R3c the next bar's retest fires", p.d.state == S.OPEN_LONG, p.st())
    q = Drive([(9, 35, 700.3, 700.6, 700.02, 700.03)])        # closes 700.03 INSIDE
    q.bar(9, 36, 699.96, 700.05, 699.5, 699.6)   # opens 699.96 OUTSIDE (below)
    check("R3s the short mirror: own open below, previous close inside -> ARMED_SHORT, "
          "stop = its high 700.05", q.d.state == S.ARMED_SHORT
          and abs(q.d.stop_level - 700.05) < 1e-9, f"{q.st()} stop={q.d.stop_level}")
    n = oe.ORBEngine()
    n._data.orb_high, n._data.orb_low, n._data.orb_width = HI, LO, W
    n._data.state = S.WAITING_FOR_BREAK
    n._check_for_break(_frame([B(9, 40, 702.1, 702.3, 702.05, 702.2),   # prev close OUTSIDE
                               B(9, 41, 702.2, 702.7, 702.1, 702.6),    # own open OUTSIDE
                               B(9, 42, 702.6, 702.6, 702.6, 702.6)]))
    check("R3d a bar whose previous close AND own open are outside is still not a break",
          n.data.state == S.WAITING_FOR_BREAK, n.data.state)
    n2 = oe.ORBEngine()
    n2._data.orb_high, n2._data.orb_low, n2._data.orb_width = HI, LO, W
    n2._data.state = S.WAITING_FOR_BREAK
    n2._check_for_break(_frame([B(9, 40, 702.1, 702.3, 702.05, 702.2),  # prev close OUTSIDE
                                B(9, 41, 702.00, 702.7, 701.9, 702.6),  # own open ON the line
                                B(9, 42, 702.6, 702.6, 702.6, 702.6)]))
    check("R3e (r131b) an own open exactly ON the line is not 'started inside': with "
          "the previous close outside too, it is not a break",
          n2.data.state == S.WAITING_FOR_BREAK, n2.data.state)

    # ── R4 no tolerance: the line is OUTSIDE (r131b) ────────────────────────
    a = runaway_long()
    a.bar(9, 39, 703.4, 703.5, 701.9, 702.00)    # closes EXACTLY on the high
    check("R4a a close exactly ON the high is not back inside: the runaway stays "
          "dormant (r131b: at-or-beyond = outside)", a.st() == "INVALIDATED/runaway", a.st())
    b = runaway_long()
    b.bar(9, 39, 703.4, 703.5, 701.9, 701.99)    # 1c inside
    check("R4b ... a close 1c inside (701.99) re-arms — no tolerance either way",
          b.d.state == S.WAITING_FOR_BREAK, b.st())
    c = runaway_short()
    c.bar(9, 39, 698.6, 700.1, 698.5, 700.00)    # exactly on the low
    c2 = runaway_short()
    c2.bar(9, 39, 698.6, 700.1, 698.5, 700.01)   # 1c inside
    check("R4c short mirror: ON the low stays dormant, 1c inside re-arms",
          c.st() == "INVALIDATED/runaway" and c2.d.state == S.WAITING_FOR_BREAK,
          f"700.00: {c.st()}; 700.01: {c2.st()}")
    k = Drive([(9, 35, 701.7, 701.9, 701.5, 701.8)])
    k.bar(9, 36, 701.8, 702.2, 701.7, 702.00)    # opens inside, closes ON the high
    check("R4d BREAK: a bar that starts inside and closes exactly ON the high is the "
          "break (ARMED_LONG, stop = its low 701.70); broke_high latches",
          k.d.state == S.ARMED_LONG and abs(k.d.stop_level - 701.7) < 1e-9
          and k.e.broke_high, f"{k.st()} stop={k.d.stop_level} broke_high={k.e.broke_high}")
    ks = Drive([(9, 35, 700.3, 700.6, 700.2, 700.4)])
    ks.bar(9, 36, 700.4, 700.5, 699.8, 700.00)   # closes ON the low
    check("R4e short mirror: a close ON the low is the break (stop = its high 700.50)",
          ks.d.state == S.ARMED_SHORT and abs(ks.d.stop_level - 700.5) < 1e-9
          and ks.e.broke_low, f"{ks.st()} stop={ks.d.stop_level}")
    k.bar(9, 37, 702.3, 702.4, 701.9, 702.00)    # after the break: closes ON the line
    check("R4f after a break, a close ON the line is NOT a close back inside (still "
          "ARMED), and with its body not strictly outside it is not a retest",
          k.d.state == S.ARMED_LONG, k.st())

    # ── S (2)/(c) the retest is a LATER bar with a body STRICTLY outside ────
    s1 = Drive([(9, 35, 701.7, 701.95, 701.5, 701.9)])        # closes inside
    s1.bar(9, 36, 702.00, 702.5, 701.95, 702.3)  # opens ON the line, wick in, closes out
    check("S1 (2) the break bar is NEVER its own retest — even one that opens exactly "
          "ON the line with its wick in and its body at/above the line: it only ARMS",
          s1.d.state == S.ARMED_LONG, s1.st())
    s1.bar(9, 37, 702.00, 702.6, 702.00, 702.4)  # opens ON the line and moves away
    check("S2 (c) a later bar that OPENS ON the line (702.00) and moves away is NOT a "
          "retest — keep waiting", s1.d.state == S.ARMED_LONG, s1.st())
    s1.bar(9, 38, 702.4, 702.5, 701.98, 702.2)   # wick in, body strictly outside
    check("S2b ... and a later bar with its body STRICTLY outside confirms",
          s1.d.state == S.OPEN_LONG, s1.st())
    s3 = Drive([(9, 34, 701.2, 702.0, 701.1, 702.00)],        # 09-22 shape: the range's
               base=RANGE[:4])
    s3.bar(9, 35, 702.00, 702.5, 701.99, 702.4)  # last bar closes ON the high; next
    check("S3 the 09-22 09:34/09:35 shape: the 09:34 bar closing ON the high is the "
          "break; 09:35 opening ON the line is not a retest (HEAD fired it)",
          s3.d.state == S.ARMED_LONG and abs(s3.d.stop_level - 701.1) < 1e-9,
          f"{s3.st()} stop={s3.d.stop_level}")
    ss = Drive([(9, 35, 700.3, 700.6, 700.05, 700.1)])
    ss.bar(9, 36, 700.00, 700.02, 699.5, 699.6)  # short: opens ON the low, wick in
    ss.bar(9, 37, 700.00, 700.00, 699.4, 699.5)  # opens ON the line, moves away
    check("S3s short mirror: the break bar only arms; a bar opening ON the low is "
          "not a retest", ss.d.state == S.ARMED_SHORT, ss.st())
    pr = oe.ORBEngine()
    pr._data.orb_high, pr._data.orb_low, pr._data.orb_width = HI, LO, W
    pr._data.state = S.WAITING_FOR_BREAK
    pr._range_date = "%04d-%02d-%02d" % DAY
    CLOCK["t"] = datetime(*DAY, 9, 36, 10)
    tape = [B(9, 30, 700.5, 701.0, 700.0, 700.8),
            B(9, 31, 700.8, 702.0, 700.7, 702.00),   # closes ON the eventual high
            B(9, 32, 701.9, 701.95, 701.0, 701.2),
            B(9, 33, 701.2, 701.5, 701.0, 701.3),
            B(9, 34, 701.3, 701.6, 701.1, 701.4),
            B(9, 35, 701.4, 701.6, 701.2, 701.5),
            B(9, 36, 701.5, 701.5, 701.5, 701.5)]
    pr.rebuild_from_tape(_frame(tape))
    check("S4 a restart's replay does not read a 09:30-09:33 bar (never read live) "
          "closing ON the eventual high as a break",
          pr.data.state == S.WAITING_FOR_BREAK and pr.data.attempt_number == 0,
          f"{pr.data.state} attempt={pr.data.attempt_number}")

    # ── V (b) the stop must sit inside the range for a valid setup ──────────
    v1 = Drive([(9, 35, 701.7, 701.95, 701.5, 701.97)])       # closes inside
    v1.bar(9, 36, 702.03, 702.5, 702.00, 702.3)  # opens outside; low ON the line
    check("V1 a break candle whose low is exactly ON the high (702.00) is VALID: "
          "armed, stop 702.00", v1.d.state == S.ARMED_LONG
          and abs(v1.d.stop_level - 702.0) < 1e-9, f"{v1.st()} stop={v1.d.stop_level}")
    v2 = Drive([(9, 35, 701.7, 701.95, 701.5, 701.97)])
    v2.bar(9, 36, 702.04, 702.5, 702.02, 702.3)  # whole bar ABOVE the range
    rf = str(getattr(v2.d, "break_refusal", "") or "")
    check("V2 a break candle whose low (702.02) is OUTSIDE the range is NOT a valid "
          "setup: not armed, the reason is recorded by name",
          v2.d.state == S.WAITING_FOR_BREAK and v2.d.attempt_number == 0
          and "outside the range" in rf and "702.02" in rf, f"{v2.st()} refusal={rf!r}")
    v2.bar(9, 37, 702.3, 702.4, 702.1, 702.2)    # still out there: nothing
    v2.bar(9, 38, 702.2, 702.3, 701.8, 701.9)    # back inside
    v2.bar(9, 39, 701.9, 702.4, 701.6, 702.3)    # starts inside, closes beyond
    check("V2b ... the engine keeps waiting, and a later bar that starts inside and "
          "closes beyond arms normally (stop = its low 701.60)",
          v2.d.state == S.ARMED_LONG and v2.d.attempt_number == 1
          and abs(v2.d.stop_level - 701.6) < 1e-9, f"{v2.st()} stop={v2.d.stop_level}")
    v3 = Drive([(9, 35, 700.3, 700.6, 700.02, 700.03)])
    v3.bar(9, 36, 699.96, 699.98, 699.5, 699.6)  # short: whole bar BELOW the range
    rs3 = str(getattr(v3.d, "break_refusal", "") or "")
    check("V3 short mirror: a break candle whose high (699.98) is below the range is "
          "refused by name", v3.d.state == S.WAITING_FOR_BREAK
          and "outside the range" in rs3, f"{v3.st()} refusal={rs3!r}")

    # ── L the line is OUTSIDE everywhere else too ──────────────────────────
    l1 = Drive([(9, 35, 701.7, 701.9, 701.1, 701.4),
                (9, 36, 701.6, 702.6, 701.5, 702.4),      # BREAK
                (9, 37, 702.3, 702.6, 701.7, 702.3)])     # RETEST -> OPEN_LONG
    l1.bar(9, 38, 702.3, 702.4, 701.9, 702.00)   # closes ON the line while OPEN
    l1.e.notify_position_closed()
    check("L1 a trade resolving with the last close ON the line keeps the setup ARMED "
          "(last_close_inside is strict)", l1.d.state == S.ARMED_LONG, l1.st())
    l2 = Drive([(9, 35, 701.7, 701.9, 701.1, 701.4),
                (9, 36, 701.6, 702.6, 701.5, 702.4)])
    l2.e._rearm()                                 # AWAITING_RANGE_REENTRY
    l2.bar(9, 37, 702.4, 702.5, 701.9, 702.00)   # ON the line
    at_line = l2.d.state
    l2.bar(9, 38, 702.0, 702.1, 701.8, 701.99)   # 1c inside
    check("L2 AWAITING_RANGE_REENTRY: a close ON the line is not back inside; 1c "
          "inside is", at_line == S.AWAITING_RANGE_REENTRY
          and l2.d.state == S.WAITING_FOR_BREAK, f"{at_line} -> {l2.d.state}")

    # ── R5 the plan reads the re-armed engine ───────────────────────────────
    try:
        from strategy import plan as P
        from strategy.orb_plan import ORBPlan
        from data.options_chain import OptionContract, OptionsChain
    except Exception as exc:                                  # noqa: BLE001
        check("R5 strategy.orb_plan imports", False, repr(exc))
        return _done()

    class _Store:
        def __init__(self):
            self.conn = sqlite3.connect(":memory:")
            self.conn.row_factory = sqlite3.Row

        def commit(self):
            self.conn.commit()
    st = _Store()
    P.ensure_tables(st)
    P.bind_store(st)
    ch = OptionsChain(underlying="TEST", expiry="2026-09-24", spot_price=701.0)
    for k_ in range(694, 710):
        m = max(0.10, round(1.5 - 0.2 * abs(k_ - 701), 2))
        ch.calls.append(OptionContract(symbol=f"C{k_}", strike=float(k_), mark=m,
                                       bid=m - 0.02, ask=m + 0.02, delta=0.3,
                                       option_type="C"))
        ch.puts.append(OptionContract(symbol=f"P{k_}", strike=float(k_), mark=m,
                                      bid=m - 0.02, ask=m + 0.02, delta=-0.3,
                                      option_type="P"))

    def prep(eng, now):
        P.begin_tick()
        ORBPlan().prepare(orb=eng.data, chain=ch, price_now=701.0, now_hhmm=now)
        P.close_tick(st, "TEST")
        r = st.conn.execute("SELECT verdict, reason FROM plan_tick ORDER BY ts_epoch "
                            "DESC, rowid DESC LIMIT 1").fetchone()
        return (r["verdict"], r["reason"] or "") if r else ("", "")

    e5 = runaway_long()
    v0, w0 = prep(e5.e, "09:39")
    e5.bar(9, 39, 703.4, 703.5, 701.6, 701.8)    # CLOSE INSIDE
    v1, w1 = prep(e5.e, "09:40")
    check("R6b while the runaway stands the plan DECLINEs `consequence` RUNAWAY "
          "(the hand-off is still reported)",
          v0 == "DECLINE" and "RUNAWAY" in w0, f"{v0}: {w0[:90]}")
    check("R5 after the close inside the plan no longer refuses with the runaway "
          "reason: it HOLDs, waiting on a fresh impulsive candle",
          v1 == "HOLD" and "RUNAWAY" not in w1 and "impulsive candle" in w1
          and "outside the range" not in w1, f"{v1}: {w1[:110]}")

    vp = Drive([(9, 35, 701.7, 701.95, 701.5, 701.97)])
    vp.bar(9, 36, 702.04, 702.5, 702.02, 702.3)  # refused: low outside
    vv, vw = prep(vp.e, "09:37")
    check("V4 the plan's HOLD row names the refused candidate",
          vv == "HOLD" and "REFUSED" in vw and "outside the range" in vw, f"{vv}: {vw[-120:]}")

    # ── R6 the pre-existing paths ───────────────────────────────────────────
    f = Drive([(9, 35, 701.7, 701.9, 701.1, 701.4),
               (9, 36, 701.6, 702.6, 701.5, 702.4),      # BREAK, own open inside
               (9, 37, 702.4, 702.7, 702.2, 702.5),
               (9, 38, 702.3, 702.6, 701.7, 702.3)])     # RETEST
    check("R6c a first break's retest still fires (OPEN_LONG, stop = impulsive low)",
          f.d.state == S.OPEN_LONG and abs(f.d.stop_level - 701.5) < 1e-9
          and f.d.attempt_number == 1, f"{f.st()} stop={f.d.stop_level}")
    g = Drive([(9, 35, 701.7, 701.9, 701.1, 701.4),
               (9, 36, 701.6, 702.6, 701.5, 702.4),      # BREAK
               (9, 37, 702.4, 702.5, 701.6, 701.7)])     # closes back INSIDE
    check("R6d a close-inside invalidation still re-arms to WAITING_FOR_BREAK",
          g.d.state == S.WAITING_FOR_BREAK, g.st())
    live = runaway_long()
    for r in [(9, 39, 703.4, 703.5, 701.6, 701.8),
              (9, 40, 701.8, 701.9, 701.3, 701.5),
              (9, 41, 701.5, 702.5, 701.2, 702.3)]:
        live.bar(*r)
    re_ = oe.ORBEngine()
    re_._data.orb_high, re_._data.orb_low, re_._data.orb_width = HI, LO, W
    re_._data.state = S.WAITING_FOR_BREAK
    re_._range_date = live.e._range_date
    re_.rebuild_from_tape(_frame(live.rows + [B(9, 42, 702.3, 702.3, 702.3, 702.3)]))
    same = ((re_.data.state, re_.data.attempt_number, re_.data.stop_level)
            == (live.d.state, live.d.attempt_number, live.d.stop_level))
    check("R6e a restart's tape replay reaches the continuous engine's state "
          "(r95: one _advance_state for both paths)", same,
          f"live={live.st()}#{live.d.attempt_number}@{live.d.stop_level} "
          f"replay={re_.data.state}#{re_.data.attempt_number}@{re_.data.stop_level}")
    check("R1r ... and on this tape that state is the NEW attempt: the replay "
          "re-arms after the runaway and arms the fresh candle (#2 @ 701.20)",
          same and live.d.state == S.ARMED_LONG and live.d.attempt_number == 2,
          f"live={live.st()}#{live.d.attempt_number}@{live.d.stop_level} "
          f"replay={re_.data.state}#{re_.data.attempt_number}@{re_.data.stop_level}")
    return _done()


def _done() -> int:
    if FAILED:
        print(f"\nFAIL — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
