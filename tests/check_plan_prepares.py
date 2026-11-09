#!/usr/bin/env python3
"""
tests/check_plan_prepares.py  v5.6
v5.6  2026-11-09  OTV5 r103 (RETIRE.5 step 2) — the GEX pin butterfly is removed: its r97 flag flip, the butterfly block (B1-B5, the fly's plan on the store) and the r178 block (B10-B14b, pin_played and persistence) go with it; B6 pins that attempt_new_entry asks no butterfly. B7 (add_open_position appends), the condor and runaway blocks are unchanged.
v5.5  2026-11-08  OTV5 r97 (RETIRE.5) —  GEX fly is cut in production (OFF in code); this checker flips it on to exercise its code until step 2 removes it.
v5.4  2026-11-08  OTV5 r88 (RETIRE.3) — the TCS block and its OT_TCS_ACTIVE=1 switch go with the TCS; the condor, butterfly and runaway blocks are unchanged.
v5.3  2026-11-08  OTV5 r76 (RETIRE.1) — RE-POINTED (WA 38.4): the sweep is removed, so the S block (S1-S9b, the sweep's plan on the store) and T4-T7 (a
      tine as a sweep level) go with it; the condor, butterfly, TCS and runaway blocks are unchanged.
v5.2  2026-11-03  OTV5 r73 (BFLY.17) — the fly now also asks VIX < 20 and an open inside yesterday's range (the
      operator, 2026-11-03: "I want the VIX rule enforced & I want more discriminatory entries"); neither is this
      check's subject, so vix_now and prior_range_read are pinned to a VIX of 17 and an open inside the range.
v5.1  2026-10-25  OTV5 r9 (GATE.7) — T4-T7 (the tine block) are pinned to the same session open as the S block; they passed no pin, so before 09:30 ET T5 and T7 were red and T4 and T6 passed for the wrong reason. The S-block pins now reach the plan (sweep_credit_spread v5.6). Every expectation is unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.25  CD.2 (2026-10-24) - seeded REJECTED rows carry their market time; the sweep's session open is pinned
      (session_open_epoch) so the checker does not depend on the clock; the fixture marks the level book SYNCED (store.mark_level_sync) after seeding the ledger:
      LevelEngine.board() now fails closed as not_synced until a book sync against a recent closed 1m bar has been
      recorded (derived/levels v6.10). Every expectation is unchanged.
v1.24 2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject SweepCreditSpread / TrendCreditSpread is DORMANT by default and a dormant plan now writes
      nothing by ruling, so this run switches it ACTIVE (OT_TCS_ACTIVE=1; r76: OT_SWEEP_CS no longer read); what it pins is unchanged.
v1.23 2026-10-05  OTV4TEST r255 — PINNED TO QQQ, the instrument its fixtures are written for (found and named by
      SPX-TEST): M2/M3 build a 1-wide QQQ grid, and under OT_INSTRUMENT=SPX config.STRIKE_INCREMENT is 5, so
      condor_roll's proximity read the call as TESTED (M2) and priced the roll on SPX's grid (M3). Red on
      b08d747 too; the sweep forces QQQ, so only SPX-TEST saw it. No assertion changed.
v1.22 2026-09-26  OTV4TEST r149 (EOD.1) — R8 and R14 RE-POINTED: "past the cutoff" is now five
      minutes past the cutoff READ FROM CONFIG (RUNAWAY_CUTOFF_ET, 15:40), not a typed 11:45. The
      operator's 2026-08-29 "Debit entries are finished at 1130, period" is superseded by his
      2026-09-26 "I wanna extend the debit window to all day" / "Stop entries at 1540"; what r176
      pinned — the debit cutoff does not relax — still holds and is still pinned.
v1.21 2026-09-23  OTV4TEST r126 — T1-T3 RETIRED with analysis/liquidity_mapper (deleted):
      T1/T2's property MOVED to check_rails_book R8/R9; T1b went with the map
      object; T3 was reversed by r116 (a fork lives while its builder builds it).
v1.20  2026-09-23  OTV4TEST r113 - S9 INVERTS and S9b is added: the sweep no longer
      grades pierce depth (operator's HELD has no depth; step 3 approved). A
      0.60% pierce and a 0.005% pierce BOTH fire. S9 pinned the old ceiling,
      so it had to move with the rule - the r106 lesson.
v1.19  2026-09-22  OTV4TEST r106 - S8 INVERTS: a REJECTED 10 bars old IS
      a trigger now. And T4's fixture had to change with the rule it depends
      on - it made events inert by AGEING them, which no longer works; they
      are DELETED, because "no rejection yet" is now expressed by there being
      no rejection.
v1.18  2026-09-22  OTV4TEST r92 — S5's probe time is DERIVED from the plan's own LATEST_ET.
      It passed a literal 14:30, which r81 moved INSIDE the sweep's window —
      and the docstring's "10:15" was stale too, from before the 13:00 floor
      was removed. Two stale numbers disagreeing about which was wrong.
v1.17 2026-09-18  OTV4TEST r43 — B6 follows the call one level down
      (main_loop -> attempt_new_entry -> _attempt_butterfly), asserting the
      reachable path rather than one call's address.
      🔴 B13 MATCHED A MENTION, NOT A CALL, AND A COMMENT BROKE IT. It did
      `msrc.index("mark_pin_played")` on the raw file, so the FIRST occurrence
      won — and r43 added a docstring line naming it above the fire site. The
      rule (mark AFTER execution, so a refused or zero-sized fire does not burn
      the pin) was never violated; the canary was reading prose. Re-anchored on
      the two CALLS via the AST, and mutation-tested: moving the execute below
      the mark still fails it.
v1.16 2026-09-13  OTV4TEST r24 — SPENT AND FINISHED ARE REAL ROWS. S7/T7 write a closed sweep
      row that exited on its breach (the r5 rule: spent on acceptance only)
      instead of calling the deleted `mark_spent`; R11 writes a closed runaway
      row instead of `finish_break`; R13 is re-derived from a pin on the hook's
      source to the rule itself — a WINNING runaway exit finishes its break.
      And every runaway call passes a frame: entry now needs the CLOSED BAR to
      prove the 50 is held (a live tick always has one; none means no entry),
      so the frame's closes sit at each case's own price and no case changes
      meaning. B1b narrowed to the 2026-09-01 trade's own 1-wide (still refused
      at 40%), and B1c added: the wider floor admits that ladder's 2-wide.
v1.15  2026-09-09  OTV4TEST r11 — M5 re-derived: a rolled structure is FINAL FORM with one
      floor; the tent rung is retired (PLAN_SPEC §35 v2).
v1.14  2026-09-09  OTV4TEST r9 — the TCS constant patching is gone with the TCS rewrite
      (the C cases were retired at r238; the TCS is pinned in check_tcs_plan).
v1.13  2026-09-09  OTV4TEST r6 — B12 re-derived on the smoothed pin (one tick is chatter;
      the window's mode is a migration); B14 pins persistence as a bar; B2 titled BEST-R.
v1.12  2026-09-09  OTV4TEST r5 — S1–S9 RE-DERIVED against the sweep PLAN: levels come
      from a DerivedStore fixture, the trigger is a REJECTED event, the short anchors
      on the level; S8/S9 pin freshness and the depth band. The liq_map fixtures are gone.
v1.11  2026-09-08  OTV4TEST r3 — R1–R14 re-pointed at the runaway PLAN: the trigger is
      the engine's `fifty_accepted` latch (no `prev_close`), an unmet bar is a DECLINE
      naming the bar, a finished break HOLDS pending re-validation, any exit finishes
      the break, and the cutoff pin reads strategy/runaway_plan.py.
v1.10  2026-09-04  r238 — C1–C5, T7 and T8 RETIRED, not patched. They
      pinned `adx`, `trend_vote`, `outside_range` and `drift_bar` — conditions
      the r238 rewrite DELETED. A check for a rule that no longer exists cannot
      be re-derived, only retired. New-spec coverage is `check_tcs_fifty.py`;
      TCS.10 records what the old block covered that the new one does not.
v1.9  2026-09-04  r237 — C1–C5 RESTORE `TCS_ENTRY_END_ET` FOR THEIR
      DURATION. TCS is parked at (0,0) in production, but these exercise the
      strategy's INTERNALS — the ADX floor, the range test, the POP fault, the
      wing search — which tomorrow's rewrite starts from. Patches the MODULE
      not config, restores after, and the production value is pinned by
      `check_tcs_parked` P5 so this file can never be what claims TCS is
      parked (§20: the canary cannot live in the file doing the patching).
v1.8  2026-09-04  r237 — C1–C5 patch `TCS_ENTRY_END_ET` back to (14,0)
      for their duration so the strategy's INTERNALS stay covered while it is
      parked — the rewrite starts from them tomorrow. Patches the MODULE not
      config, restores after, and the production value is pinned by
      `check_tcs_parked` P5 so this file can never be what says TCS is parked.
v1.7  2026-09-03  r234 — S2 RE-DERIVED. It asserted
      `stop_premium == credit * 1.15` — 15% OF CREDIT, the inverted rule r155
      deleted — so the suite was CERTIFYING a stop 4x tighter than the one the
      engine fires. Third time a fixture in this file has certified the defect
      it was meant to pin; r219 did it for the fill basis.  (2026-09-02, r219)
v1.6  r219 — 🔴 S2 ASSERTED THE BASIS MISMATCH AND SO CERTIFIED IT. It
      required `net_credit == 1.30`, the BID/ASK credit, while
      position_manager marks a credit vertical at MID — so this file passed on
      every run while every credit vertical was booked on one side of the
      quote and marked on the other, losing both half-spreads at fill. The
      fixture's 95P is 1.40/1.44 and the 92.5P is 0.08/0.10: judged 1.30, mark
      1.33. Re-derived to the MARK per the operator's ruling that paper fills
      at mark, with S2b requiring the plan line to NAME BOTH — it read
      "credit N (bid/ask)" and N is now the mark, so an unlabelled number
      would carry the same lie forward.
v1.5  r208 — THE BUTTERFLY HYPOTHETICALS ARE RE-DERIVED. `calls_good` WAS the
      2026-09-01 trade: penny legs on a 1-wide ladder, debit 0.18, R 4.6, and
      the old code took it. It is kept as `calls_unsurvivable` and B1b, the
      refusal case (r155 — a fixture encoding the replaced rule is re-derived,
      not deleted). B2 now pins the NARROWEST of two qualifying wings; B3
      pins the wing_search refusal with the best available R stated. B3b is
      inverted: it asserted relaxed does not waive feasibility and still
      PASSED for a reason that no longer exists, so it now drives BOTH
      postures over one chain and asserts the verdicts are identical.
      ⚠️ B12 needed a 104 strike, and its absence was informative: a migrated
      pin near the edge of the listed chain has fewer wings to choose from,
      so "the magnet moved" and "the magnet moved somewhere we can trade"
      are different facts.
v1.5  r168: R2b — the runaway carries no underlying stop; a 20% premium floor.
v1.4  r165: R1-R8 — the runaway: contract prepared before the TP confirms;
      the buy on confirmation; the gamma-leverage pick is the best strike
      REACHABLE within the run (102 on a 0.90 run, 103 on a 1.90 run); the
      invalidated-on-runaway handoff; unbroken ORB holds; unreachable ATR
      holds naming it; past the cutoff is dormant.
v1.3  r164: C1-C6 — TCS: a weak ADX holds with the put spread prepared; a
      strong vote fires the plan's 350/347.5; price back inside the range
      holds; a NEUTRAL vote has no side to prepare; no wing clears R declines;
      09:50 is dormant.
v1.2  r163: T1-T7 — the tine as a MOVING level: a touch is found against the
      rail where it WAS (slope x time), not where it is now; a falling rail
      the high never reached is no touch; acceptance invalidates; the sweep's
      plan fires leg one on the touch with the short beyond the move; as leg
      two the touch is never selected; the spent lock is keyed by name.
v1.1  r161: B1-B7 — the butterfly's plan (weak pin holds with the fly
      prepared; R<1 declined, relaxed included; no exact apex strike declined)
      and its exemption from the single-position rule (asked with a position
      open, record appended).
v1.0  r160

HYPOTHETICALS. Operator: *"see if each one makes logical sense afterwards by
testing them on hypothetical conditions. if it doesn't it's probably not
written correctly."* Each scenario below is a market condition stated in
words, then what the PLAN must say and what the STRATEGY must do.

Born red at 379fdf1 (r158): `prepare()`, `authorize()` and `manage()` do not
exist.

THE SWEEP — the plan is anticipatory, the strategy is confirmatory
  S1  13:30, NY Low 96 swept 3 bars ago, NOT yet reclaimed, chain prices a
      wing to R>=1. -> PLAN: HOLD "PREPARED — sell 95P/buy .. Waiting on:
      reclaimed". STRATEGY: fires nothing. (The trade is fully selected
      before the trigger.)
  S2  same tick, the bar CLOSES back inside. -> STRATEGY fires, and the
      signal's strikes/credit/stop are the plan's numbers, not re-derived.
  S3  reclaimed, but every wing prices below R 1.00. -> PLAN: DECLINE
      wing_r_best (structural). STRATEGY: nothing, even though the trigger
      is true. Relaxed does NOT waive it.
  S4  reclaimed, but no chain this tick. -> PLAN: NO PLAN naming "chain".
  S5  past the plan's own LATEST_ET — outside the slot. -> DORMANT, one row.
  S6  a call vertical is open; the freshest sweep is a HIGH (call side).
      Authorized side is PUT. -> the plan prepares the freshest LOW sweep
      instead; a call sweep cannot fire under the authorization.
  S7  reclaimed at a pool that stopped us out earlier today. -> DECLINE
      spent_level (structural), trigger true or not.

THE CONDOR — authorizes, then manages
  A1  no vertical open -> no authorization, no restriction.
  A2  a call vertical open -> "put" authorized, and the reason says SWEEP.
  A3  both open -> "" and "nothing more may fire".
  M1  one leg open -> LONE row (15% stop, not a condor).
  M2  formed, price mid-range, neither short tested -> HOLD, no rung.
  M3  formed, put short tested, a roll of the call side makes it risk-free
      -> row verdict ROLL, rung 1, with roll credit / close cost /
      cumulative vs width, risk_free PASS.
  M4  formed, put short tested, NO roll reaches risk-free -> the row says
      NO RUNG in so many words (the ladder gap, named on the tick).
  M5  rolled structure, 1m close through the call short -> rung 2b TENT,
      the hedge named as the OPPOSITE type, the floor stated.
"""
import os
import time
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
# ⚠️ r106 — THE LANDER RUNS CHECKS UNDER SYSTEM `python3`, NOT THE VENV, and
# the repo imports below reach `tastytrade`, which lives only in the venv — so
# this file could never be DECLARED as a CHECK. It passed by hand and failed
# under the lander, which reads as flaky rather than structural. Inserted at
# index 1 so the venv beats /usr/lib/python3/dist-packages (whose older
# `typing_extensions` otherwise shadows it) while the repo root still wins.
import glob as _glob
_RT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sp in _glob.glob(os.path.join(_RT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ["OT_INSTRUMENT"] = "QQQ"   # v1.23: the fixtures are a 1-wide QQQ grid; SPX STRIKE_INCREMENT=5
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def commit(self):
        self.conn.commit()


class _C:
    def __init__(self, k, bid, ask, delta=0.2, symbol=""):
        self.strike, self.bid, self.ask = float(k), float(bid), float(ask)
        self.mark = (bid + ask) / 2
        self.delta, self.gamma, self.theta = delta, 0.01, -0.03
        self.expiry, self.open_interest = "x", 100
        self.symbol = symbol or f"P{k}"


class _Chain:
    def __init__(self, puts, calls=()):
        self.puts, self.calls = list(puts), list(calls)


class _Sweep:
    def __init__(self, kind, pool, name, reclaimed, bars=3, rej=0.0018,
                 sweep_price=None, invalidated=False):
        self.kind, self.pool_price, self.swept_named_level = kind, pool, name
        self.reclaimed, self.invalidated, self.bars_ago = reclaimed, invalidated, bars
        self.rejection_pct = rej
        self.sweep_price = sweep_price if sweep_price is not None else (
            pool - 0.18 if kind == "low_sweep" else pool + 0.18)


class _LM:
    def __init__(self, *sweeps):
        self.sweeps = list(sweeps)
        self.recent_sweep = min(self.sweeps, key=lambda s: s.bars_ago) if self.sweeps else None


def _row(st, strat, ts):
    return st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy=? "
                           "AND ts_epoch=?", (strat, ts)).fetchone()


def main():

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
    from strategy import plan as P
    st = _Store()
    P.bind_store(st)
    os.environ["OT_RELAXED_ENTRY"] = "0"
    # r76: the sweep (S block) is removed; its puts chain stays for the condor's management cases below
    good_puts = [_C(97.5, 2.40, 2.50), _C(95, 1.40, 1.44), _C(92.5, 0.08, 0.10),
                 _C(90, 0.03, 0.05), _C(87.5, 0.02, 0.03)]
    # ── the condor ────────────────────────────────────────────────────────
    from strategy.iron_condor_strategy import IronCondorStrategy
    IC = IronCondorStrategy()
    check("A1 nothing open -> no authorization, no restriction", IC.authorize([]) == ("", ""))
    a2 = IC.authorize(["call"])
    check("A2 call vertical open -> PUT authorized, and only as a SWEEP",
          a2[0] == "put" and "SWEEP" in a2[1], a2[1])
    a3 = IC.authorize(["call", "put"])
    check("A3 both open -> nothing more may fire", a3[0] == "" and "nothing more" in a3[1])

    class _PM:
        def __init__(self, recs): self.recs = recs
        def get_open_records(self): return self.recs

    def leg(side, short, long_, credit, bw=False):
        return {"is_condor_leg": True, "option_side": side, "short_strike": short,
                "long_strike": long_, "spread_width": abs(short - long_),
                "credit_received": credit, "contracts": 1, "is_broken_wing": bw}

    # M1
    P.begin_tick(10.0)
    IC.manage(_PM([leg("put", 95, 90, 1.10)]), _Chain(good_puts), 98.0)
    m1 = _row(st, "CondorManagement", 10.0)
    check("M1 one leg -> LONE row, 15% stop, not a condor",
          m1 and m1[0] == "HOLD" and "lone" in m1[1] and "15%" in m1[1], str(m1))

    # a chain for management, 1-point strikes (the roll walks STRIKE_INCREMENT).
    # Calls lose value further OTM; rolling the call side down from 105 toward
    # price 95.4 collects credit. 98/103 collects 3.8-0.8 = 3.0 -> cumulative
    # 5.15 >= tested width 5 -> risk-free.
    def _cv(k, base, slope, k0): return max(0.02, base - (k - k0) * slope)
    m_puts = [_C(k, _cv(100 - k, 5, 0.6, 0) - 0.02, _cv(100 - k, 5, 0.6, 0) + 0.02)
              for k in range(85, 101)]
    m_calls = [_C(k, _cv(k, 5, 0.6, 96) - 0.02, _cv(k, 5, 0.6, 96) + 0.02, symbol=f"C{k}")
               for k in range(96, 116)]
    formed = _PM([leg("put", 95, 90, 1.10), leg("call", 105, 110, 1.05)])

    # M2
    P.begin_tick(11.0)
    rung = IC.manage(formed, _Chain(m_puts, m_calls), 100.0)
    m2 = _row(st, "CondorManagement", 11.0)
    check("M2 formed, mid-range -> HOLD, neither short tested, no rung",
          rung == "HOLD" and m2 and "neither short tested" in m2[1], str(m2))

    # M3 — put short 95 tested (price 95.4); roll the call side down toward
    # price collects fat credit here -> risk-free reachable
    P.begin_tick(12.0)
    rung = IC.manage(formed, _Chain(m_puts, m_calls), 95.4)
    m3 = _row(st, "CondorManagement", 12.0)
    chk = {r[0]: (r[1], r[2]) for r in st.conn.execute(
        "SELECT check_name, value, verdict FROM plan_check WHERE strategy='CondorManagement' AND ts_epoch=12.0")}
    check("M3 put short tested, roll reaches risk-free -> ROLL verdict, rung 1, numbers stated",
          rung == "ROLL" and m3 and m3[0] == "ROLL" and "RUNG 1" in m3[1]
          and "cumulative" in m3[1] and chk.get("risk_free", (None, ""))[1] == "PASS",
          f"{m3} risk_free={chk.get('risk_free')}")

    # M4 — same tested short, but the call side is cheap: the best roll (98/103)
    # collects 0.8-0.3 = 0.5 -> cumulative 2.65, short of the 5-wide width
    cheap_calls = [_C(k, _cv(k, 1.0, 0.1, 96) - 0.01, _cv(k, 1.0, 0.1, 96) + 0.01, symbol=f"C{k}")
                   for k in range(96, 116)]
    P.begin_tick(13.0)
    rung = IC.manage(formed, _Chain(m_puts, cheap_calls), 95.4)
    m4 = _row(st, "CondorManagement", 13.0)
    check("M4 tested, NO roll reaches risk-free -> the row says NO RUNG (the ladder gap, named)",
          rung == "NO_RUNG" and m4 and m4[0] == "DECLINE" and "NO RUNG" in m4[1]
          and "never do nothing" in m4[1], str(m4))

    # M5 — already rolled, 1m close through the call short 105
    import pandas as pd
    idx = pd.to_datetime([1_000_000 + 60 * i for i in range(3)], unit="s", utc=True)
    df = pd.DataFrame({"open": [104, 104.8, 105.3], "high": [104.9, 105.6, 105.8],
                       "low": [103.9, 104.7, 105.1], "close": [104.6, 105.4, 105.5]}, index=idx)
    rolled = _PM([leg("put", 100, 95, 1.10 + 0.9, bw=True), leg("call", 105, 110, 1.05)])
    P.begin_tick(14.0)
    rung = IC.manage(rolled, _Chain(m_puts, m_calls), 105.5, df_1m=df)
    m5 = _row(st, "CondorManagement", 14.0)
    check("M5 (r11) rolled structure -> FINAL FORM: the floor is the only exit, the tent rung is retired",
          rung == "FINAL" and m5 and m5[0] == "HOLD" and "FINAL FORM" in m5[1] and "floor" in m5[1]
          and "TENT" not in m5[1], str(m5)[:160])

    # r103 (RETIRE.5): the butterfly block (B1-B5) is removed with the GEX pin butterfly.
    # B6 — wiring: main_loop asks the butterfly in the position-open branch and
    # appends its record; the authorization no longer skips it.
    import ast as _ast
    msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    ml = next(n for n in _ast.walk(_ast.parse(msrc))
              if isinstance(n, _ast.FunctionDef) and n.name == "main_loop")
    mls = _ast.unparse(ml)
    # ⚠️ r43 — THE CALL MOVED ONE LEVEL DOWN, THE RULE DID NOT. `main_loop` used
    # to call `_attempt_butterfly(..., additive=True)` directly in the
    # position-open branch. ADM.1 removed the entry gate, so main_loop calls
    # `attempt_new_entry` in BOTH branches and that is what asks the butterfly —
    # still with a position open, still additively. B6 asserts the reachable
    # path, not the address of one call.
    _anb = next(n for n in _ast.walk(_ast.parse(msrc))
                if isinstance(n, _ast.FunctionDef) and n.name == "attempt_new_entry")
    check("B6 (r103) main_loop asks attempt_new_entry in both branches, and no butterfly is asked any more",
          "attempt_new_entry(ctx, ms, state)" in mls
          and "_attempt_butterfly" not in _ast.unparse(_anb) and "def _attempt_butterfly" not in msrc
          and '_plan_skip("GEXPinButterfly", _auth_why)' not in mls)
    from execution.position_manager import PositionManager
    pm = PositionManager.__new__(PositionManager)
    pm._open_records = [{"trade_id": "v1", "is_condor_leg": True}]
    pm.add_open_position({"trade_id": "bf1", "is_butterfly": True})
    check("B7 add_open_position APPENDS — the vertical under management is not dropped",
          [r["trade_id"] for r in pm._open_records] == ["v1", "bf1"])

    import pandas as pd
    # ── r76: T4-T7 (a tine as a sweep LEVEL) are removed with the sweep plan they drove ──
    _bind_book()
    # RETIRE.3 (r88): the TCS block (r164 / r237 / r238) goes with the TCS.

    # ── THE RUNAWAY (r165) — gamma does the heavy lifting ────────────────
    import strategy.runaway_continuation as rw
    RW = rw.RunawayContinuationStrategy(); RW.planner.symbol = "TST"
    # r24 — entry needs the CLOSED BAR to prove the 50 is held NOW. Every call below
    # that passes no frame gets one whose closes sit at that call's own price, dated
    # today (the book's rows are today's), so no case changes meaning.
    _rw_gen = RW.generate_signal

    def _bars_at(px):
        import pandas as pd
        from datetime import datetime
        from zoneinfo import ZoneInfo
        d = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        return pd.DataFrame([{"open": px, "high": px, "low": px, "close": px}] * 5,
                            index=pd.date_range(f"{d} 10:00", periods=5, freq="1min"))

    def _gen_with_bars(**kw):
        if kw.get("df_1m") is None and kw.get("price_now") is not None:
            kw["df_1m"] = _bars_at(float(kw["price_now"]))
        return _rw_gen(**kw)
    RW.generate_signal = _gen_with_bars

    class _ORB:
        def __init__(self, state="OPEN_LONG", hi=101.0, lo=100.0, tp=101.5, inval="", bd="",
                     accepted=False):
            self.state, self.orb_high, self.orb_low, self.target_50pct = state, hi, lo, tp
            self.invalidation_reason, self.break_direction = inval, bd
            self.fifty_accepted, self.bars_since_break = accepted, 2   # OTV4TEST r3

    class _G:
        def __init__(self, k, prem, delta, gamma):
            self.strike, self.mark, self.ask, self.bid = float(k), prem, prem + 0.02, prem - 0.02
            self.delta, self.gamma, self.theta = delta, gamma, -0.04
            self.expiry, self.open_interest, self.symbol = "x", 100, f"C{k}"

    # spot 101.9 after a 0.90 run from the ORB high 101.0. A realistic OTM
    # ladder: premium and delta fall with distance, gamma peaks near the money.
    calls_rw = [_G(102, 0.95, 0.46, 0.050), _G(103, 0.48, 0.30, 0.058), _G(104, 0.20, 0.17, 0.040),
                _G(105, 0.08, 0.09, 0.022), _G(106, 0.03, 0.04, 0.010)]

    def _lev(c, run=0.9):
        return (abs(c.delta) * run + 0.5 * c.gamma * run * run) / c.ask
    _by_lev = sorted(calls_rw, key=lambda c: -_lev(c))
    os.environ["OT_RELAXED_ENTRY"] = "1"      # R muteable here; the pick is the point
    P.begin_tick(50.0)
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.9,
                             now_et="10:15", chain=_Chain([], calls_rw))
    r50 = _row(st, "RunawayContinuation", 50.0)
    check("R1 (OTV4TEST r3) broke and ran, the 50 not yet ACCEPTED -> HOLD waiting on it",
          sig is None and r50 and r50[0] == "HOLD" and "50 ACCEPTED" in r50[1], str(r50))
    P.begin_tick(51.0)
    sig = RW.generate_signal(orb=_ORB(accepted=True), atr_pct=0.14, price_now=101.9,
                             now_et="10:15", chain=_Chain([], calls_rw))
    r51 = _row(st, "RunawayContinuation", 51.0)
    check("R2 the 50 ACCEPTED (close beyond, held) -> BUYS the plan's contract, valid",
          sig is not None and sig.is_valid and sig.option_side == "call"
          and getattr(sig, "disarms_retest", False) and r51 and r51[0] == "TAKE", str(r51))
    check("R2b (r168) the runaway carries NO underlying stop and a 20% premium floor — "
          "the ORB boundary is not its stop",
          sig is not None and not getattr(sig, "underlying_stop", 0)
          and abs(sig.stop_loss_pct - 0.20) < 1e-9
          and abs(sig.stop_premium() - sig.entry_premium * 0.80) < 1e-9
          and "50" in (r51[1] or ""),
          f"underlying_stop={getattr(sig, 'underlying_stop', None)} floor={sig and sig.stop_premium():.2f}")
    # Raw leverage-per-dollar always crowns the cheapest far-OTM ticket (here
    # the 105/106). "Just enough OTM" is the reachability band — strikes
    # within the run — and inside it the 102 wins. The band is the discipline.
    check("R3 the pick is the highest gamma-leverage strike REACHABLE within the 0.90 run "
          "(the 102); the raw ranking's winner sits beyond the run and is not taken",
          sig is not None and sig.strike == 102.0 and abs(sig.run_at_entry - 0.9) < 1e-9
          and _by_lev[0].strike > 101.9 + 0.9,
          f"picked {sig and sig.strike}; raw ranking {[c.strike for c in _by_lev][:3]}")
    P.begin_tick(52.0)
    sig = RW.generate_signal(orb=_ORB(hi=100.0, tp=100.8, accepted=True), atr_pct=0.14, price_now=101.9, now_et="10:15", chain=_Chain([], calls_rw))
    check("R4 a bigger run (1.90) reaches further and gamma picks the 103 — 'just enough OTM' "
          "scales with the intensity of the move",
          sig is not None and sig.strike == 103.0, str(sig and sig.strike))
    P.begin_tick(53.0)
    sig = RW.generate_signal(orb=_ORB(state="INVALIDATED", inval="runaway", bd="long", accepted=True),
                             atr_pct=0.14, price_now=101.9, now_et="10:15",
                             chain=_Chain([], calls_rw))
    check("R5 the engine has invalidated on 'runaway' — direction taken from break_direction, "
          "the handoff fires", sig is not None and sig.direction == "long")
    P.begin_tick(54.0)
    sig = RW.generate_signal(orb=_ORB(state="WATCHING"), atr_pct=0.14, price_now=100.5, now_et="10:15", chain=_Chain([], calls_rw))
    r54 = _row(st, "RunawayContinuation", 54.0)
    check("R6 ORB not broken -> HOLD, nothing to prepare until it breaks",
          sig is None and r54 and r54[0] == "HOLD" and "nothing to prepare" in r54[1], str(r54))
    P.begin_tick(55.0)
    sig = RW.generate_signal(orb=_ORB(accepted=True), atr_pct=0.03, price_now=101.9,
                             now_et="10:15", chain=_Chain([], calls_rw))
    r55 = _row(st, "RunawayContinuation", 55.0)
    check("R7 ATR 0.03% (unreachable tape) -> DECLINE naming atr_pct and the gap — recorded, not silent",
          sig is None and r55 and r55[0] == "DECLINE" and r55[1].startswith("atr_pct"), str(r55))
    # ── r174 — the two structural gates from 2026-08-28's tape ───────────
    import strategy.runaway_continuation as rwmod
    # the teenie: floor 20% of 0.17 = 3.4c, spread ask-bid = 4c -> refused
    teenie = _G(107, 0.15, 0.09, 0.022); teenie.ask, teenie.bid = 0.17, 0.13
    P.begin_tick(57.0)
    sig = RW.generate_signal(orb=_ORB(hi=100.0, tp=100.8, accepted=True), atr_pct=0.14, price_now=105.9, now_et="10:15",
                             chain=_Chain([], [teenie]))
    r57 = _row(st, "RunawayContinuation", 57.0)
    check("R9 (r174) the only candidate is a teenie whose 20% floor sits INSIDE its own "
          "bid/ask -> structural DECLINE naming the spread, even on relaxed",
          sig is None and r57 and r57[0] == "DECLINE" and "clears its own bid/ask" in r57[1]
          and "1 rejected" in r57[1], str(r57))
    # same chain plus a real-premium strike: the pick lands there, not the teenie
    real = _G(102, 0.95, 0.46, 0.050)          # floor 19c >> ~4c spread
    P.begin_tick(58.0)
    sig = RW.generate_signal(orb=_ORB(accepted=True), atr_pct=0.14, price_now=101.9,
                             now_et="10:15", chain=_Chain([], [real, teenie]))
    check("R10 (r174) with a real-premium strike on the chain the pick lands there — the "
          "spread gate is what keeps the leverage score off the teenies",
          sig is not None and sig.strike == 102.0, str(sig and sig.strike))
    # one runaway per break: a floor stop-out finishes (long, 101.0)
    _book_row(trade_id="rw-r11", symbol="TST", strategy="RunawayContinuation", option_side="call",
              orb_range_high=101.0, orb_range_low=100.0, status="closed", pnl_usd=-30.0,
              entry_time=_now_iso(12), exit_time=_now_iso(6), exit_reason="runaway_thesis_dead")
    P.begin_tick(59.0)
    sig = RW.generate_signal(orb=_ORB(accepted=True), atr_pct=0.14, price_now=101.9,
                             now_et="10:15", chain=_Chain([], [real]))
    r59 = _row(st, "RunawayContinuation", 59.0)
    check("R11 (OTV4TEST r3) this break is finished -> HOLD naming re-validation: one runaway per break, any exit",
          sig is None and r59 and r59[0] == "HOLD" and "finished" in r59[1], str(r59))
    P.begin_tick(59.5)
    sig = RW.generate_signal(orb=_ORB(hi=103.0, tp=103.8, accepted=True), atr_pct=0.14, price_now=104.9, now_et="10:15",
                             chain=_Chain([], [_G(106, 0.95, 0.46, 0.050)]))
    check("R12 (r174) a NEW break at a new boundary is a new trade",
          sig is not None, str(sig and sig.strike))
    _bind_book()
    _book_row(trade_id="rw-r13", symbol="TST", strategy="RunawayContinuation", option_side="call",
              orb_range_high=102.25, orb_range_low=100.0, status="closed", pnl_usd=+180.0,
              entry_time=_now_iso(12), exit_time=_now_iso(6), exit_reason="orb_trail_stop pnl=33.0%")
    check("R13 (OTV4TEST r3, read from the book since r24) a WINNING runaway exit finishes its break too",
          isinstance(rwmod.break_last_exit("long", 102.25), float))
    _bind_book()

    import config as _cP
    _rc = tuple(int(x) for x in str(_cP.RUNAWAY_CUTOFF_ET).split(":"))   # r149: read, not typed
    _past = f"{_rc[0]:02d}:{_rc[1] + 5:02d}" if _rc[1] + 5 < 60 else f"{_rc[0] + 1:02d}:{_rc[1] - 55:02d}"
    os.environ["OT_RELAXED_ENTRY"] = "0"
    P.begin_tick(56.0)
    sig = RW.generate_signal(orb=_ORB(accepted=True), atr_pct=0.14, price_now=101.9,
                             now_et=_past, chain=_Chain([], calls_rw))
    r56 = _row(st, "RunawayContinuation", 56.0)
    check(f"R8 {_past}, past the {_cP.RUNAWAY_CUTOFF_ET} cutoff (strict) -> DORMANT", sig is None and r56 and r56[0] == "DORMANT", str(r56))
    # ── r176 — THE DEBIT CUTOFF DOES NOT RELAX (operator, 2026-08-29:
    # "Debit entries are finished at 1130, period … We are burning theta").
    # Dormant rows DEDUPE, so the pin is behavioural: relaxed at 11:45
    # produces no signal and no new TAKE/HOLD row.
    os.environ["OT_RELAXED_ENTRY"] = "1"
    P.begin_tick(56.5)
    sig = RW.generate_signal(orb=_ORB(accepted=True), atr_pct=0.14, price_now=101.9,
                             now_et=_past, chain=_Chain([], [_G(102, 0.95, 0.46, 0.050)]))
    r565 = _row(st, "RunawayContinuation", 56.5)
    check(f"R14 (r176) {_past} UNDER RELAXED -> still dormant: no signal, no TAKE/HOLD row",
          sig is None and (r565 is None or r565[0] == "DORMANT"), str(r565))
    src_rw = open(os.path.join(_root, "strategy", "runaway_plan.py"), encoding="utf-8").read()
    check("R14b (r176) the relaxed 14:00 extension is gone from the source (now the plan's)",
          'relaxed.window(' not in src_rw and "_cutoff_hm()" in src_rw)
    os.environ["OT_RELAXED_ENTRY"] = "0"

    # 🔴 r238 — REMOVED with the C-block: this drove `drift_bar` and the
    # `puts_tcs` fixture, both deleted by the rewrite. See TCS.10.


    # r103 (RETIRE.5): the r178 block (B10-B14b: pin_played, smoothing, persistence, the mark after execution) is removed
    # with the GEX pin butterfly.

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_plan_prepares: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
