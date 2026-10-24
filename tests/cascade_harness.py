#!/usr/bin/env python3
"""
tests/cascade_harness.py  v1.5
v1.5  2026-10-12  OTV4TEST r273 (BFLY.10) — BUTTERFLY_ENTRY_START_ET (12, 0) -> (13, 0), the config's new fly start
      (the operator, 2026-10-12: "reduce the fly window to 1300"). Caught by the full sweep's check_cascade_constants C1.
v1.4  2026-09-26  OTV4TEST r149 — EOD.1 moves the copies with config: ORB_NO_ENTRY_AFTER_ET and
      DEBIT_DIRECTIONAL_CUTOFF_ET (11,30)->(15,40), the operator's all-day debit window;
      HARD_CLOSE_ET (15,45)->(15,55), the cross (unused by the model; compared only).
v1.3  2026-09-22  OTV4TEST r92 — TWO DRIFTED LITERALS. TCS_ENTRY_END_ET (14,0)->(15,40)
      after r81 made CREDIT_ENTRY_END_ET the one END; CONDOR_ENTRY_START_ET
      (11,11)->(11,31). The second had drifted INVISIBLY because
      check_cascade_constants compared 4 of the 8 mirrored constants.
v1.2  2026-09-04  r246 — TCS.9: the local constant copy is now
      COMPARED against config by `check_cascade_constants.py`. The copy
      is deliberate — this harness models the cascade without importing
      config — but a copy nobody compares is drift waiting to happen:
      r238 parked TCS at (0,0) and this still read (14,0), modelling a
      TCS that traded, and r241 made it correct BY ACCIDENT.  (2026-08-30)

v1.1  2026-08-30  r193 — ORB_NO_ENTRY_AFTER_ET follows config (11:30).
      This file declared its OWN (11, 0); a design harness rehearsing an 11:00
      window against a fleet running 11:30 stays green while measuring a
      different system. tests/check_orb_window.py W3 now pins every
      declared copy against config.

A DESIGN HARNESS FOR THE PLAN CASCADE. Not a backtest, not a study.

⚠️ THE TAPES ARE SYNTHETIC. Every price below is hand-constructed to have a
named SHAPE (a trend, a chop, a fakeout). Nothing here touches a real tape, a
real chain, or a real fill, so NOTHING IT PRINTS IS EVIDENCE ABOUT P&L,
win rate, or whether any of these plans is any good. What it CAN answer, and
the only reason it exists:

    ON A TAPE OF A GIVEN SHAPE, WHICH PLANS SELF-ELIMINATE, IN WHAT ORDER,
    AND WHAT IS LEFT STANDING AT THE END?

Operator, 2026-08-25: *"try to cascade them in different orders as price moves
or chops & see which ones self-eliminate in what order."*

⚠️ ORB IS DELIBERATELY ABSENT. Operator: *"leave orb alone. That one can't get
encumbered with extra hurdles & it already pretty much plans."* It is modelled
here ONLY as the thing that fixes the range and then vacates at 11:00 — it is
never a cascade candidate.

THE INVARIANT THIS HARNESS EXISTS TO PROVE-OR-BREAK:
    every `executable_from_here()` is a comparison against a price FIXED AT
    DECLARATION or a stamped structural fact. If any of them needs to
    recompute a score from the live tape, the design has failed and the old
    confluence loop is back wearing new vocabulary.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable

# Real constants, read from config rather than invented, so the windows in the
# harness are the windows on the box.
ORB_NO_ENTRY_AFTER_ET       = (15, 40)   # r149 EOD.1; r193 — keep in step with config;
                                         # tests/check_orb_window.py pins every copy
DEBIT_DIRECTIONAL_CUTOFF_ET = (15, 40)   # r149 — EOD_SCHEDULE entries_stop
CONDOR_ENTRY_START_ET       = (11, 31)   # r92 — = CREDIT_ENTRY_START_ET
# 🔴 r246 (TCS.9) — THESE ARE A DELIBERATE LOCAL COPY, AND THE COPY IS THE
# POINT: this harness models the cascade WITHOUT importing config, so it can be
# reasoned about standing still while the fleet's constants move. But a copy
# nobody compares is drift waiting to happen — r238 set TCS_ENTRY_END_ET to
# (0,0) to park TCS and these still read (14,0), so for a day they modelled a
# TCS that traded. r241 restored (14,0) and made them correct BY ACCIDENT.
# ⚠️ `tests/check_cascade_constants.py` now compares every one of these against
# config and fails on a difference, so the copy stays intentional instead of
# becoming stale. Same treatment ORB_NO_ENTRY_AFTER_ET already has.
TCS_START_ET                = (11, 31)
TCS_ENTRY_END_ET            = (15, 40)   # r92 — r81 unified every credit END
BUTTERFLY_ENTRY_START_ET    = (13, 0)   # r273 (BFLY.10): was (12, 0); mirrors config (check_cascade_constants C1)
CONDOR_TRIGGER_APPROACH     = 0.65
HARD_CLOSE_ET               = (15, 55)   # r149 — EOD_SCHEDULE cross_at

ALIVE, GONE = "ALIVE", "GONE"


# ══════════════════════════════════════════════════════════════════════════
#  THE TAPE
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class Tick:
    hhmm: tuple              # (hour, minute) ET
    price: float
    bar_close: Optional[float] = None   # set on the minute; None mid-bar

    @property
    def t(self) -> int:
        return self.hhmm[0] * 60 + self.hhmm[1]


@dataclass
class Structure:
    """Everything FIXED for the session. A plan may read these; it may never
    read a score. This is the whole discipline in one dataclass."""
    orb_high: float
    orb_low: float
    session_high: float
    session_low: float
    named_levels: List[float]
    gex_pin: Optional[float]
    bb_middle: float
    atr: float
    # structural facts, stamped — not scores
    trend_direction: str = ""       # "bull"/"bear"/"" — the VOTE at declaration
    fork_built: bool = False


# ══════════════════════════════════════════════════════════════════════════
#  THE PLAN
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class Plan:
    name: str
    trigger: float                      # FIXED at declaration
    invalidation: float                 # FIXED at declaration
    direction: str                      # "up" = fires on a close ABOVE trigger
    window: tuple                       # ((h,m) open, (h,m) close)
    instrument: str                     # pre-selected, described
    arm_reason: str
    mode: str = "tight"
    declared_at: tuple = (0, 0)
    state: str = ALIVE
    gone_why: str = ""
    gone_at: Optional[tuple] = None
    # a plan may carry ONE extra fixed price (e.g. the condor's other side)
    trigger_b: Optional[float] = None
    fired_at: Optional[tuple] = None

    def executable_from_here(self, tk: Tick, st: Structure) -> tuple:
        """THE BINARY. Returns (bool, reason).

        ⚠️ EVERY BRANCH BELOW COMPARES THE TAPE TO A NUMBER SET AT
        DECLARATION. No branch may consult a live score. That is the test."""
        if tk.t < self.window[0][0] * 60 + self.window[0][1]:
            return True, "not yet open"          # alive, simply early
        if tk.t >= self.window[1][0] * 60 + self.window[1][1]:
            return False, f"window closed {self.window[1][0]:02d}:{self.window[1][1]:02d}"
        # 🔴 INVALIDATION IS ONLY LIVE ONCE THE PLAN HAS TRIGGERED.
        # v1.0 of this harness had it active from declaration, which killed
        # every plan on the first tick: a plan WAITING for price to rise to
        # 352.11 was being eliminated for price being below 352.11. That is
        # not invalidation, it is "not yet triggered", and conflating the two
        # makes a forward plan impossible to hold. Found by running the
        # harness, which is the only reason it exists.
        if self.fired_at is None:
            return True, "armed, awaiting trigger"
        if tk.bar_close is not None:
            if self.direction == "up" and tk.bar_close < self.invalidation:
                return False, f"close {tk.bar_close:.2f} < invalidation {self.invalidation:.2f}"
            if self.direction == "down" and tk.bar_close > self.invalidation:
                return False, f"close {tk.bar_close:.2f} > invalidation {self.invalidation:.2f}"
        return True, "live"

    def triggered(self, tk: Tick) -> bool:
        if tk.bar_close is None:
            return False
        if tk.t < self.window[0][0] * 60 + self.window[0][1]:
            return False
        return (tk.bar_close > self.trigger if self.direction == "up"
                else tk.bar_close < self.trigger)


# ══════════════════════════════════════════════════════════════════════════
#  DECLARATION — the inversion, one per setup
#  "What price, FROM HERE, would constitute this setup — and what would I
#   trade when it comes?"
# ══════════════════════════════════════════════════════════════════════════
def declare_all(st: Structure, at: tuple) -> List[Plan]:
    """Every plan the structure supports, declared at `at`.

    ⚠️ ORB IS NOT HERE BY OPERATOR RULING. It fixes the range and vacates."""
    P: List[Plan] = []
    strike = lambda x: round(x)          # whole-dollar strikes for the harness

    # ── RUNAWAY CONTINUATION (debit) ──────────────────────────────────────
    # Fires on the CONTINUATION confirming, not on the break itself.
    if st.trend_direction == "bull":
        P.append(Plan(
            name="RunawayContinuation",
            trigger=st.orb_high + 0.25 * st.atr,     # ⟨PRIOR⟩
            invalidation=st.orb_high,
            direction="up",
            window=((9, 35), DEBIT_DIRECTIONAL_CUTOFF_ET),
            instrument=f"long C {strike(st.orb_high + st.atr)}",
            arm_reason="ORB broke without retest; debit owns the slot to 11:30",
            declared_at=at))

    # ── TREND PARTICIPATION (credit) ──────────────────────────────────────
    # The floor UNDER the move. Strike re-anchors per PLAN, never per session.
    if st.trend_direction == "bull":
        floor = max(st.orb_high, st.session_low)
        P.append(Plan(
            name="TrendParticipation",
            trigger=st.orb_high,
            invalidation=st.orb_high,
            direction="up",
            window=(TCS_START_ET, TCS_ENTRY_END_ET),
            instrument=f"PCS {strike(floor)}/{strike(floor-5)}",
            arm_reason=f"credit floor under a bull move, anchored {floor:.2f}",
            declared_at=at))

    # ── SWEEP CREDIT SPREAD ───────────────────────────────────────────────
    # Identity is (pool, reclaim bar). Declared only ON a reclaim close.
    for lv in st.named_levels:
        if abs(lv - st.session_low) < 0.35 * st.atr:
            P.append(Plan(
                name=f"SweepCredit@{lv:.2f}",
                trigger=lv,
                invalidation=lv - 0.25 * st.atr,      # ⟨PRIOR⟩ acceptance
                direction="up",
                window=(CONDOR_ENTRY_START_ET, TCS_ENTRY_END_ET),
                instrument=f"PCS {strike(lv)}/{strike(lv-5)}",
                arm_reason=f"named level {lv:.2f} swept and reclaimed",
                declared_at=at))

    # ── IRON CONDOR — ONE PLAN, TWO TRIGGERS ──────────────────────────────
    up_short = st.session_high + 0.5 * st.atr
    dn_short = st.session_low - 0.5 * st.atr
    P.append(Plan(
        name="IronCondor",
        trigger=st.bb_middle + CONDOR_TRIGGER_APPROACH * (up_short - st.bb_middle),
        trigger_b=st.bb_middle - CONDOR_TRIGGER_APPROACH * (st.bb_middle - dn_short),
        invalidation=up_short,
        direction="up",
        window=(CONDOR_ENTRY_START_ET, TCS_ENTRY_END_ET),
        instrument=f"CCS {strike(up_short)} / PCS {strike(dn_short)}",
        arm_reason="ranging; both boundaries identified",
        declared_at=at))

    # ── GEX PIN BUTTERFLY ─────────────────────────────────────────────────
    if st.gex_pin:
        P.append(Plan(
            name="GEXPinButterfly",
            trigger=st.gex_pin + 0.5 * st.atr,        # ⟨PRIOR⟩ approach band
            invalidation=st.gex_pin + 2.0 * st.atr,   # ⟨PRIOR⟩ pin abandoned
            direction="down",
            window=(BUTTERFLY_ENTRY_START_ET, TCS_ENTRY_END_ET),
            instrument=f"fly {strike(st.gex_pin)}",
            arm_reason=f"firm pin {st.gex_pin:.2f}, price away from it",
            declared_at=at))

    # ── DAILY FORK ────────────────────────────────────────────────────────
    if st.fork_built:
        tine = st.session_high + 1.0 * st.atr
        P.append(Plan(
            name="DailyFork",
            trigger=tine,
            invalidation=tine + 0.25 * st.atr,        # ⟨PRIOR⟩
            direction="up",
            window=(CONDOR_ENTRY_START_ET, TCS_ENTRY_END_ET),
            instrument=f"CCS {strike(tine)}/{strike(tine+5)}",
            arm_reason="1d fork built, containment holding",
            declared_at=at))

    return P


# ══════════════════════════════════════════════════════════════════════════
#  THE CASCADE
# ══════════════════════════════════════════════════════════════════════════
def run(tape: List[Tick], st: Structure, declare_at: tuple,
        label: str) -> Dict:
    plans = declare_all(st, declare_at)
    timeline, fired = [], []

    for tk in tape:
        for p in plans:
            if p.state == GONE:
                continue
            ok, why = p.executable_from_here(tk, st)
            if not ok:
                p.state, p.gone_why, p.gone_at = GONE, why, tk.hhmm
                timeline.append((tk.hhmm, p.name, "ELIMINATED", why))
                continue
            if p.triggered(tk) and p.fired_at is None:
                p.fired_at = tk.hhmm
                fired.append(p)
                timeline.append((tk.hhmm, p.name, "TRIGGERED", p.instrument))

    survivors = [p for p in plans if p.state == ALIVE]
    return {"label": label, "plans": plans, "timeline": timeline,
            "fired": fired, "survivors": survivors}


def report(r: Dict) -> None:
    print(f"\n{'═'*74}\n  {r['label']}\n{'═'*74}")
    print(f"  declared {len(r['plans'])} plans\n")
    for hhmm, name, what, why in r["timeline"]:
        mark = "🔥" if what == "TRIGGERED" else "✗ "
        print(f"   {hhmm[0]:02d}:{hhmm[1]:02d}  {mark} {name:<22} {what:<12} {why}")
    print(f"\n   ELIMINATION ORDER: "
          f"{' → '.join(p.name for p in r['plans'] if p.state == GONE) or '(none)'}")
    print(f"   STILL STANDING AT THE END: "
          f"{', '.join(p.name for p in r['survivors']) or '(nothing)'}")
    print(f"   TRIGGERED: "
          f"{', '.join(f'{p.name} @{p.fired_at[0]:02d}:{p.fired_at[1]:02d}' for p in r['fired']) or '(nothing)'}")


# ══════════════════════════════════════════════════════════════════════════
#  SYNTHETIC TAPES — each has a NAMED SHAPE and is hand-built
# ══════════════════════════════════════════════════════════════════════════
def _bars(start: tuple, prices: List[float]) -> List[Tick]:
    """One bar per minute from `start`. Tapes are built long enough to cross
    12:00 so the butterfly's window is genuinely exercised rather than being
    a trivial survivor."""
    out, h, m = [], start[0], start[1]
    for px in prices:
        out.append(Tick((h, m), px, bar_close=px))
        m += 1
        if m == 60:
            h, m = h + 1, 0
    return out


def tape_trend_from_inside() -> tuple:
    """TODAY'S TSLA SHAPE. The rip STARTS INSIDE the range and runs 90 min.
    Operator: 'THAT rip started INSIDE THE FUCKING RANGE.'"""
    st = Structure(orb_high=352.11, orb_low=349.23, session_high=352.40,
                   session_low=348.90, named_levels=[350.42, 352.40],
                   gex_pin=360.0, bb_middle=351.0, atr=1.20,
                   trend_direction="bull", fork_built=True)
    px = ([351.4, 351.6, 351.9, 352.0] +                    # inside, coiling
          [352.3, 352.9, 353.4, 353.6, 353.5, 353.8] +      # break + push
          [354.1, 354.4, 354.2, 354.6, 355.1, 355.4] +      # trend leg
          [355.0, 355.6, 356.2, 356.8, 356.4, 356.0] +       # extension + fade
          [356.3, 356.1, 355.8, 356.0, 356.4, 356.7] +       # holds the gain
          [356.5, 356.2, 356.6, 357.0, 356.8, 356.5] +
          [356.9, 357.2, 356.9, 356.6, 356.8, 357.1])
    return _bars((11, 31), px), st, "TREND FROM INSIDE THE RANGE (TSLA 08-25 shape)"


def tape_chop() -> tuple:
    """Price oscillates around the middle, never accepting either boundary."""
    st = Structure(orb_high=352.11, orb_low=349.23, session_high=352.60,
                   session_low=348.80, named_levels=[350.42, 352.40],
                   gex_pin=351.0, bb_middle=350.7, atr=1.20,
                   trend_direction="", fork_built=False)
    px = ([350.6, 351.2, 350.4, 349.9, 350.8, 351.4] +
          [350.9, 350.2, 349.7, 350.5, 351.1, 350.6] +
          [350.3, 351.0, 350.8, 350.1, 349.9, 350.7] +
          [350.9, 350.4, 351.2, 350.6, 350.0, 350.8] +
          [351.3, 350.7, 350.2, 350.9, 351.1, 350.5] +
          [350.4, 351.0, 350.6, 350.3, 350.8, 351.2])
    return _bars((11, 31), px), st, "CHOP AROUND THE MIDDLE (no acceptance either side)"


def tape_fakeout() -> tuple:
    """Breaks up, fails, closes back inside and keeps going the other way."""
    st = Structure(orb_high=352.11, orb_low=349.23, session_high=352.90,
                   session_low=348.60, named_levels=[350.42, 349.00],
                   gex_pin=349.0, bb_middle=350.9, atr=1.20,
                   trend_direction="bull", fork_built=False)
    px = ([351.8, 352.4, 352.9, 352.6] +          # break up
          [352.0, 351.5, 350.9, 350.2] +          # fail back inside
          [349.6, 349.1, 348.7, 348.4, 348.9] +    # roll over
          [348.5, 348.2, 348.6, 348.3, 347.9, 348.1] +
          [347.8, 348.0, 347.6, 347.9, 348.2, 347.7] +
          [348.0, 347.5, 347.8, 348.1, 347.9, 348.3] +
          [348.0, 347.7, 348.2, 348.4, 348.1, 347.8])
    return _bars((11, 31), px), st, "FAKEOUT — breaks up, fails, rolls over"


def tape_grind_to_pin() -> tuple:
    """Slow drift toward a firm GEX pin. The butterfly's tape."""
    st = Structure(orb_high=352.11, orb_low=349.23, session_high=352.30,
                   session_low=350.10, named_levels=[352.40],
                   gex_pin=350.0, bb_middle=351.2, atr=0.90,
                   trend_direction="", fork_built=False)
    px = ([351.9, 351.7, 351.8, 351.4, 351.2, 351.0] +
          [350.9, 351.1, 350.8, 350.6, 350.5, 350.3] +
          [350.4, 350.2, 350.1, 350.0, 350.1, 349.9] +
          [350.0, 349.8, 350.1, 350.0, 349.9, 350.2] +
          [350.0, 350.1, 349.9, 350.0, 350.2, 350.0] +
          [349.9, 350.1, 350.0, 349.8, 350.0, 350.1])
    return _bars((11, 31), px), st, "SLOW GRIND INTO A FIRM PIN"


if __name__ == "__main__":
    print(__doc__)
    print("\n" + "!"*74)
    print("  SYNTHETIC TAPES. Shape only. NOT evidence about P&L or edge.")
    print("!"*74)
    # ⚠️ The tapes run 11:31 onward, so a plan whose window opens at 12:00
    # (the butterfly) is "not yet open" throughout and survives TRIVIALLY.
    # That is an artefact of the tape length, NOT a finding about the
    # butterfly. Tapes are extended below so the window is actually reached.
    for maker in (tape_trend_from_inside, tape_chop,
                  tape_fakeout, tape_grind_to_pin):
        tape, st, label = maker()
        report(run(tape, st, (11, 31), label))
    print()
    sys.exit(0)
