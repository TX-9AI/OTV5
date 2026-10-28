#!/usr/bin/env python3
"""
tests/check_bfly_wing_log.py  v5.0
v5.0  2026-10-28  OTV5 r49 (BFLY.16) — THE WING-SEARCH LINE SAYS WHICH PIN IT SEARCHED AND WHAT THE PLAN DID WITH IT.
      META 2026-10-27 logged "[gex_bfly] wing search: 5 qualified, taking the BEST-R wing 7.50 (R 10.36, stop 2.64x its
      spread); widest was 17.50" at 13:00:16 ET (114 such lines 13:00-14:59) while the plan HELD and the gate said "no wing
      qualifies at pin 632.5 on the 2.5 grid (within 8.91 of spot): 0 too wide ..., 3 too narrow ... (best 1.65x of 2.0x)"
      at 13:05:00. Both were true, on different ticks: the search line was the smoothed pin 642.5 (wings out to 17.50 fit
      inside ~18.6 of spot ~623.9), the gate line the smoothed pin 632.5 (3 wings inside 8.91, none clearing 2.0x). Nothing
      was "taken": on every tick pinning (TRENDING) and pin_concentration (0.15 < 0.25) were unmet, and at 642.5 pin_em_fraction.
      Driven through the REAL GEXPinButterflyStrategy.prepare / generate_signal on a chain rebuilt from the 13:00:16 line
      (debits 0.66 at the 7.50 wing -> R 10.36; 0.025 per-leg spread -> stop 0.264 / quote 0.10 = 2.64x).

  L1  CONTROL: META 13:00:16 (pin 642.5, TRENDING, conc 0.15, EM 11.63) - no signal, verdict HOLD, best-R wing 7.50 prepared
  L2  the wing-search line names the pin it searched (642.5) and the spot reach (wings within 18.60)
  L3  the line says the wing was PREPARED, NOT TAKEN, and names pinning, pin_concentration and pin_em_fraction; no "taking"
  L4  the line counts the rejects: 5 qualified, 0 too wide, 2 too narrow; BEST-R 7.50 at R 10.36, 2.64x; widest 17.50
  L5  CONTROL: META 13:05:00 (pin 632.5, spot 623.59) - DECLINE at wing_search, "no wing qualifies at pin 632.5", no search line
  L6  a tick with every condition true fires the same 7.50 fly and its line says so (not "NOT TAKEN")

Born red on b78fc8f at L2, L3, L4 and L6.
Run:  python3 tests/check_bfly_wing_log.py
"""
import logging
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "META")
os.environ.setdefault("OT_PAPER_TRADING", "1")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(); self.msgs = []

    def emit(self, r):
        if r.name == "strategy.gex_pin_butterfly":
            self.msgs.append(r.getMessage())


class _St:
    def __init__(s):
        s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row

    def commit(s):
        s.conn.commit()


SPREAD = 0.025                                  # per leg: quote width 4 x 0.025 = 0.10


class _Q:
    def __init__(s, k, m):
        s.strike, s.mark = float(k), float(m)
        s.bid, s.ask = round(m - SPREAD / 2, 4), round(m + SPREAD / 2, 4)
        s.delta, s.gamma, s.theta = 0.2, 0.01, -0.03
        s.expiry, s.symbol, s.open_interest = "2026-10-28", f"META{k}C", 500


class _Ch:
    def __init__(s, calls, puts=()):
        s.calls, s.puts = list(calls), list(puts)


def chain_642():
    """The 13:00:16 call ladder about the 642.5 apex. Fly debit by wing: 2.5 -> 0.20, 5 -> 0.40 (R high but
    0.4 x debit under 2 x 0.10: too narrow), 7.5 -> 0.66 (R 10.36, 2.64x), 10 -> 1.00, 12.5 -> 1.50, 15 -> 2.00,
    17.5 -> 2.60; 20 and wider sit beyond spot and are never candidates."""
    c = 1.00
    upper = {2.5: 0.75, 5: 0.55, 7.5: 0.40, 10: 0.29, 12.5: 0.21, 15: 0.15, 17.5: 0.11, 20: 0.08, 22.5: 0.06}
    debit = {2.5: 0.20, 5: 0.40, 7.5: 0.66, 10: 1.00, 12.5: 1.50, 15: 2.00, 17.5: 2.60, 20: 3.30, 22.5: 4.00}
    q = [_Q(642.5, c)]
    for w, u in upper.items():
        q.append(_Q(642.5 + w, u))
        q.append(_Q(642.5 - w, round(debit[w] + 2 * c - u, 4)))
    return _Ch(sorted(q, key=lambda x: x.strike))


def chain_632():
    """13:05:00 about the 632.5 apex: the 3 wings inside 8.91 of spot are all priced but none clears 2.0x."""
    c = 3.00
    q = [_Q(632.5, c)]
    for w, (u, d) in {2.5: (2.30, 0.20), 5: (1.75, 0.35), 7.5: (1.30, 0.45),
                      10: (0.95, 0.80), 12.5: (0.70, 1.20)}.items():
        q.append(_Q(632.5 + w, u))
        q.append(_Q(632.5 - w, round(d + 2 * c - u, 4)))
    return _Ch(sorted(q, key=lambda x: x.strike))


class _G:
    def __init__(s, pin, env="TRENDING", conc=0.15):
        s.gex_environment, s.pin_strike, s.pin_concentration = env, pin, conc


def run(b, P, cap, gex, spot, chain, em, n=12):
    """n ticks on one pin (the smoothing window is 12, persistence 8), as the box asks it every 15 s; returns the
    LAST tick's (preparation, signal, log lines)."""
    b.expected_move = lambda u, iv, now=None: em
    strat = b.GEXPinButterflyStrategy(); strat.planner.symbol = "META"
    seen, real = [], strat.prepare
    strat.prepare = lambda **kw: seen.append(real(**kw)) or seen[-1]     # the real prepare, its result kept
    sig = None
    for i in range(n):
        P.begin_tick(1793120400.0 + 15 * i)
        cap.msgs.clear()
        sig = strat.generate_signal(gex=gex, price_now=spot, now_et="13:00", atm_iv=0.35, chain=chain)
    return strat, seen[-1], sig, list(cap.msgs)


def main():
    import strategy.gex_pin_butterfly as b
    from strategy import plan as P
    st = _St(); P.ensure_tables(st); P.bind_store(st)
    b.ENABLED = True
    _em0 = b.expected_move
    cap = _Cap(); lg = logging.getLogger("strategy.gex_pin_butterfly"); lg.addHandler(cap); lg.setLevel(logging.DEBUG)
    try:
        # ── META 13:00:16 ─────────────────────────────────────────────────
        strat, prep, sig, msgs = run(b, P, cap, _G(642.5), 623.90, chain_642(), 11.63)
        last = strat.planner.last()
        unmet = set(prep.unmet)
        check("L1 CONTROL META 13:00:16: no signal, the plan HOLDs, the 7.50 fly is prepared at R 10.36",
              sig is None and last[1] == "HOLD" and prep.ready and abs((prep.wing or 0) - 7.5) < 1e-9
              and abs((prep.r or 0) - 10.3636) < 1e-3
              and {"pinning", "pin_concentration", "pin_em_fraction"} <= unmet,
              f"sig={sig} verdict={last[1]} wing={prep.wing} r={prep.r} unmet={sorted(unmet)}")
        line = next((m for m in msgs if "wing search" in m), "")
        check("L2 the wing-search line names the pin it searched and the spot reach",
              "pin 642.5" in line and "within 18.60" in line, line or "no wing-search line")
        check("L3 it says PREPARED, NOT TAKEN and names the three conditions the plan holds on",
              "NOT TAKEN" in line and "taking" not in line
              and all(c in line for c in ("pinning", "pin_concentration", "pin_em_fraction")), line)
        check("L4 it counts the rejects (5 qualified, 0 too wide, 2 too narrow) beside the best-R and widest wings",
              all(s in line for s in ("5 qualified", "0 too wide", "2 too narrow", "BEST-R wing 7.50", "R 10.36",
                                      "2.64x", "widest qualified 17.50")), line)

        # ── META 13:05:00 — the gate's tick ───────────────────────────────
        strat5, _p5, sig5, msgs5 = run(b, P, cap, _G(632.5), 623.59, chain_632(), 11.63)
        last5 = strat5.planner.last()
        check("L5 CONTROL META 13:05:00: DECLINE at wing_search, 'no wing qualifies at pin 632.5', no search line",
              sig5 is None and last5[1] == "DECLINE" and last5[2].startswith("wing_search:")
              and "no wing qualifies at pin 632.5" in last5[2] and "within 8.91 of spot" in last5[2]
              and "3 too narrow" in last5[2] and not any("wing search" in m for m in msgs5),
              f"verdict={last5[1]} reason={last5[2][:200]}")

        # ── a tick with every condition true ──────────────────────────────
        strat6, _p6, sig6, msgs6 = run(b, P, cap, _G(642.5, env="PINNING", conc=0.60), 623.90, chain_642(), 25.0)
        line6 = next((m for m in msgs6 if "wing search" in m), "")
        check("L6 every condition true: the same 7.50 fly fires and its line says so",
              sig6 is not None and abs(sig6.wing_actual - 7.5) < 1e-9 and "every condition true" in line6
              and "NOT TAKEN" not in line6, f"sig={'fired' if sig6 else None} line={line6}")
    finally:
        b.expected_move = _em0
        lg.removeHandler(cap)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
