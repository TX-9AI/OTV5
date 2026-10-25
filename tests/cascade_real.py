#!/usr/bin/env python3
"""
tests/cascade_real.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.5  2026-10-12  OTV4TEST r273 (BFLY.10) — BUTTERFLY_ENTRY_START_ET (12, 0) -> (13, 0), the config's new fly start
      (the operator, 2026-10-12: "reduce the fly window to 1300"). Caught by the full sweep's check_cascade_constants C1.
v1.4  2026-09-26  OTV4TEST r149 — EOD.1 moves the copies with config: ORB_NO_ENTRY_AFTER_ET and
      DEBIT_DIRECTIONAL_CUTOFF_ET (11,30)->(15,40), the operator's all-day debit window.
v1.3  2026-09-22  OTV4TEST r92 — the same two drifted literals as cascade_harness.
v1.2  2026-09-04  r246 — TCS.9: the local constant copy is now
      COMPARED against config by `check_cascade_constants.py`. The copy
      is deliberate — this harness models the cascade without importing
      config — but a copy nobody compares is drift waiting to happen:
      r238 parked TCS at (0,0) and this still read (14,0), modelling a
      TCS that traded, and r241 made it correct BY ACCIDENT.  (2026-08-30)

v1.1  2026-08-30  r193 — ORB_NO_ENTRY_AFTER_ET follows config (11:30).
      This file declared its OWN (11, 0); a real-tape run rehearsing an 11:00
      window against a fleet running 11:30 stays green while measuring a
      different system. tests/check_orb_window.py W3 now pins every
      declared copy against config.

THE PLAN CASCADE RUN ON REAL 1-MINUTE TAPES.

Input: TSLA_1m_30d.csv + _VIX_1m_30d.csv (yfinance, 22 sessions,
2026-07-27 → 2026-08-25, supplied by the operator).

⚠️ WHAT THIS IS AND IS NOT
  · IT IS a structural harness: it computes the SAME fixed anchors production
    computes (ORB from the 09:30-09:35 window, session extremes, ATR, ADX),
    declares one plan per setup at its real window open, and runs the
    elimination cascade tick by tick against the real tape.
  · IT IS NOT a backtest. There are NO OPTION PRICES here. Every plan's
    "instrument" is a strike, not a fill, and nothing computes credit, debit,
    P&L or win rate. A plan that triggers here means PRICE REACHED THE
    TRIGGER — not that the trade would have been available, priced sanely, or
    profitable.
  · ⚠️ CHARM, VANNA AND GEX ARE ABSENT FROM THIS DATA. Every validator that
    depends on them is reported UNAVAILABLE and is NOT silently skipped.
    The GEX pin itself does not exist here, so the butterfly is declared
    against a STUB pin (session VWAP-ish midpoint) and is flagged as such
    everywhere it appears. Nothing about the butterfly in this output is
    evidence about the butterfly.

WHAT IT CAN ANSWER, which is the whole reason it exists:
    across 22 real sessions of different shapes — which plans self-eliminate,
    IN WHAT ORDER, at what time, and what is left standing?
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean
from typing import Optional, List, Dict

UP = os.environ.get("TAPE_DIR", "/mnt/user-data/uploads")

# Real production constants
ORB_WINDOW_MIN              = 5
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

ALIVE, GONE = "ALIVE", "GONE"


# ══════════════════════════════════════════════════════════════════════
#  TAPE
# ══════════════════════════════════════════════════════════════════════
@dataclass
class Bar:
    ts: str
    o: float; h: float; l: float; c: float; v: float
    @property
    def hm(self): return (int(self.ts[11:13]), int(self.ts[14:16]))
    @property
    def t(self): return self.hm[0] * 60 + self.hm[1]
    @property
    def day(self): return self.ts[:10]


def load(fn) -> Dict[str, List[Bar]]:
    days = defaultdict(list)
    with open(os.path.join(UP, fn)) as fh:
        for r in csv.DictReader(fh):
            try:
                b = Bar(r["timestamp"], float(r["open"]), float(r["high"]),
                        float(r["low"]), float(r["close"]), float(r["volume"] or 0))
            except (ValueError, KeyError):
                continue
            if 9 * 60 + 30 <= b.t <= 16 * 60:      # RTH only
                days[b.day].append(b)
    return {d: sorted(v, key=lambda x: x.ts) for d, v in days.items()}


def atr(bars: List[Bar], n=14) -> float:
    if len(bars) < 2:
        return 0.0
    trs = []
    for i in range(1, len(bars)):
        p, b = bars[i-1], bars[i]
        trs.append(max(b.h - b.l, abs(b.h - p.c), abs(b.l - p.c)))
    return mean(trs[-n:]) if trs else 0.0


def adx(bars: List[Bar], n=14) -> float:
    """Wilder ADX on the supplied bars. Returns 0.0 when undefined."""
    if len(bars) < n * 2:
        return 0.0
    pdm, ndm, trs = [], [], []
    for i in range(1, len(bars)):
        p, b = bars[i-1], bars[i]
        up_m, dn_m = b.h - p.h, p.l - b.l
        pdm.append(up_m if (up_m > dn_m and up_m > 0) else 0.0)
        ndm.append(dn_m if (dn_m > up_m and dn_m > 0) else 0.0)
        trs.append(max(b.h - b.l, abs(b.h - p.c), abs(b.l - p.c)))
    def smooth(xs):
        s = sum(xs[:n]); out = [s]
        for x in xs[n:]:
            s = s - s / n + x; out.append(s)
        return out
    st, sp, sn = smooth(trs), smooth(pdm), smooth(ndm)
    dx = []
    for tr, p_, n_ in zip(st, sp, sn):
        if tr <= 0:
            continue
        pdi, ndi = 100 * p_ / tr, 100 * n_ / tr
        if pdi + ndi > 0:
            dx.append(100 * abs(pdi - ndi) / (pdi + ndi))
    return mean(dx[-n:]) if len(dx) >= n else (mean(dx) if dx else 0.0)


# ══════════════════════════════════════════════════════════════════════
#  STRUCTURE — everything FIXED, computed from the tape up to `upto`
# ══════════════════════════════════════════════════════════════════════
@dataclass
class Structure:
    orb_high: float; orb_low: float
    session_high: float; session_low: float
    atr: float; adx: float
    direction: str
    vix: float
    pin_stub: float
    bb_middle: float


def structure_at(bars: List[Bar], upto_t: int, vix: float) -> Optional[Structure]:
    orb = [b for b in bars if 9*60+30 <= b.t < 9*60+30+ORB_WINDOW_MIN]
    seen = [b for b in bars if b.t <= upto_t]
    if not orb or len(seen) < 30:
        return None
    a = atr(seen)
    x = adx(seen)
    closes = [b.c for b in seen]
    mid = mean(closes[-20:])
    first, last = closes[0], closes[-1]
    d = "bull" if last > first + 0.25 * a else ("bear" if last < first - 0.25 * a else "")
    return Structure(
        orb_high=max(b.h for b in orb), orb_low=min(b.l for b in orb),
        session_high=max(b.h for b in seen), session_low=min(b.l for b in seen),
        atr=a, adx=x, direction=d, vix=vix, pin_stub=round(mid), bb_middle=mid)


# ══════════════════════════════════════════════════════════════════════
#  PLAN
# ══════════════════════════════════════════════════════════════════════
@dataclass
class Plan:
    name: str
    trigger: float
    invalidation: float
    direction: str                 # "up"/"down"
    window: tuple
    instrument: str
    arm_reason: str
    # VALIDATORS — the derived indicators, read as KILL conditions only.
    # ⚠️ A validator may only SUBTRACT. It can never re-arm a dead plan.
    v_adx_min: Optional[float] = None
    v_adx_max: Optional[float] = None
    v_vix_max: Optional[float] = None
    v_needs: tuple = ()            # named inputs this plan needs but lacks
    state: str = ALIVE
    gone_why: str = ""
    gone_at: Optional[tuple] = None
    fired_at: Optional[tuple] = None

    def check(self, b: Bar, st: Structure) -> tuple:
        if b.t < self.window[0][0]*60 + self.window[0][1]:
            return True, "not yet open"
        if b.t >= self.window[1][0]*60 + self.window[1][1]:
            return False, f"window closed {self.window[1][0]:02d}:{self.window[1][1]:02d}"
        # ── VALIDATORS (subtract only) ────────────────────────────────
        if self.v_adx_min is not None and st.adx < self.v_adx_min:
            return False, f"validator ADX {st.adx:.1f} < {self.v_adx_min}"
        if self.v_adx_max is not None and st.adx > self.v_adx_max:
            return False, f"validator ADX {st.adx:.1f} > {self.v_adx_max}"
        if self.v_vix_max is not None and st.vix > self.v_vix_max:
            return False, f"validator VIX {st.vix:.1f} > {self.v_vix_max}"
        # ── INVALIDATION — only live AFTER the trigger ────────────────
        if self.fired_at is None:
            return True, "armed"
        if self.direction == "up" and b.c < self.invalidation:
            return False, f"close {b.c:.2f} < invalidation {self.invalidation:.2f}"
        if self.direction == "down" and b.c > self.invalidation:
            return False, f"close {b.c:.2f} > invalidation {self.invalidation:.2f}"
        return True, "live"

    def triggered(self, b: Bar) -> bool:
        if b.t < self.window[0][0]*60 + self.window[0][1]:
            return False
        return b.c > self.trigger if self.direction == "up" else b.c < self.trigger


def declare(st: Structure) -> List[Plan]:
    P = []
    s = lambda x: round(x)
    if st.direction == "bull":
        P.append(Plan("RunawayContinuation", st.orb_high + 0.25*st.atr, st.orb_high,
                      "up", ((9, 35), DEBIT_DIRECTIONAL_CUTOFF_ET),
                      f"long C {s(st.orb_high + st.atr)}",
                      "ORB broke without retest", v_adx_min=20.0))
        P.append(Plan("TrendParticipation", st.orb_high, st.orb_high, "up",
                      (TCS_START_ET, TCS_ENTRY_END_ET),
                      f"PCS {s(max(st.orb_high, st.session_low))}/"
                      f"{s(max(st.orb_high, st.session_low)-5)}",
                      "credit floor under a bull move", v_adx_min=18.0))
    if st.direction == "bear":
        P.append(Plan("TrendParticipation", st.orb_low, st.orb_low, "down",
                      (TCS_START_ET, TCS_ENTRY_END_ET),
                      f"CCS {s(min(st.orb_low, st.session_high))}/"
                      f"{s(min(st.orb_low, st.session_high)+5)}",
                      "credit ceiling over a bear move", v_adx_min=18.0))
    up_s = st.session_high + 0.5*st.atr
    dn_s = st.session_low - 0.5*st.atr
    P.append(Plan("IronCondor",
                  st.bb_middle + CONDOR_TRIGGER_APPROACH*(up_s - st.bb_middle),
                  up_s, "up", (CONDOR_ENTRY_START_ET, TCS_ENTRY_END_ET),
                  f"CCS {s(up_s)} / PCS {s(dn_s)}", "ranging, both boundaries known",
                  v_adx_max=25.0))
    P.append(Plan("GEXPinButterfly", st.pin_stub + 0.5*st.atr,
                  st.pin_stub + 2.0*st.atr, "down",
                  (BUTTERFLY_ENTRY_START_ET, TCS_ENTRY_END_ET),
                  f"fly {s(st.pin_stub)} [STUB PIN]",
                  "⚠️ STUB — no GEX in this data",
                  v_vix_max=30.0, v_needs=("gex", "charm", "vanna")))
    return P


def run_day(day: str, bars: List[Bar], vix: float) -> Optional[Dict]:
    st = structure_at(bars, TCS_START_ET[0]*60 + TCS_START_ET[1], vix)
    if st is None:
        return None
    plans = declare(st)
    tl = []
    for b in bars:
        cur = structure_at(bars, b.t, vix) or st
        for p in plans:
            if p.state == GONE:
                continue
            ok, why = p.check(b, cur)
            if not ok:
                p.state, p.gone_why, p.gone_at = GONE, why, b.hm
                tl.append((b.hm, p.name, "OUT", why)); continue
            if p.fired_at is None and p.triggered(b):
                p.fired_at = b.hm
                tl.append((b.hm, p.name, "TRIG", p.instrument))
    return {"day": day, "st": st, "plans": plans, "timeline": tl}


if __name__ == "__main__":
    tsla, vixd = load("TSLA_1m_30d.csv"), load("_VIX_1m_30d.csv")
    print(__doc__)
    print("!"*74)
    print("  NO OPTION PRICES IN THIS DATA. 'TRIG' MEANS PRICE REACHED THE")
    print("  TRIGGER — NOT THAT A TRADE EXISTED, PRICED SANELY, OR WON.")
    print("  GEX / CHARM / VANNA ABSENT → the butterfly runs on a STUB pin.")
    print("!"*74)

    order_counts, out_reasons, surv = defaultdict(int), defaultdict(int), defaultdict(int)
    detail_days = []
    for day in sorted(tsla):
        vb = vixd.get(day, [])
        vix = mean([b.c for b in vb]) if vb else 0.0
        r = run_day(day, tsla[day], vix)
        if not r:
            continue
        detail_days.append(r)
        gone = [p for p in r["plans"] if p.state == GONE]
        gone.sort(key=lambda p: (p.gone_at or (99, 99)))
        order_counts[" → ".join(p.name for p in gone) or "(none eliminated)"] += 1
        for p in gone:
            out_reasons[f"{p.name}: {p.gone_why.split(' close')[0][:44]}"] += 1
        for p in r["plans"]:
            if p.state == ALIVE:
                surv[p.name] += 1

    print(f"\n{'═'*74}\n  22 SESSIONS — ELIMINATION ORDERS OBSERVED\n{'═'*74}")
    for k, v in sorted(order_counts.items(), key=lambda x: -x[1]):
        print(f"  {v:>3}x  {k}")
    print(f"\n{'═'*74}\n  WHERE PLANS DIED\n{'═'*74}")
    for k, v in sorted(out_reasons.items(), key=lambda x: -x[1]):
        print(f"  {v:>3}x  {k}")
    print(f"\n{'═'*74}\n  STILL STANDING AT THE CLOSE (count of sessions)\n{'═'*74}")
    for k, v in sorted(surv.items(), key=lambda x: -x[1]):
        print(f"  {v:>3}x  {k}")

    print(f"\n{'═'*74}\n  DETAIL — 2026-08-25 (today; the TSLA rip)\n{'═'*74}")
    for r in detail_days:
        if r["day"] != "2026-08-25":
            continue
        st = r["st"]
        print(f"  ORB {st.orb_low:.2f}-{st.orb_high:.2f}  ATR {st.atr:.2f}  "
              f"ADX {st.adx:.1f}  dir={st.direction or 'flat'}  VIX {st.vix:.1f}")
        for hm, name, what, why in r["timeline"]:
            print(f"   {hm[0]:02d}:{hm[1]:02d}  {'🔥' if what=='TRIG' else '✗ '} "
                  f"{name:<22} {what:<5} {why}")
        alive = [p.name for p in r["plans"] if p.state == ALIVE]
        print(f"   STANDING AT CLOSE: {', '.join(alive) or '(nothing)'}")
    sys.exit(0)
