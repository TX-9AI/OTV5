#!/usr/bin/env python3
"""
tests/check_butterfly_legs.py  v2.4
v2.4  2026-09-13  OTV4TEST r24 — B2b: the signal generate_signal emits carries the
      operator's 40% floor (was 25%), asserted against the RULED 0.40, not
      against config — reading config back would only prove config agrees
      with itself. Born red at 21257bf.
v2.3  2026-09-09  OTV4TEST r6 — BEST-R pick, OI on the fixture, persistence bar set to 1 here.
v2.2  r208: THE BUTTERFLY PINS ARE RE-DERIVED, NOT PATCHED. B1-B3 encoded a
      world that no longer exists — a wing COMPUTED from WING_EM_FRAC and
      snapped to a grid, with R checked afterwards. The wing is now SEARCHED
      over listed strikes and bracketed by R_FLOOR (wide side) and
      stop survivability (narrow side).
      🔴 THE OLD B1 FIXTURE IS THE 2026-09-01 TRADE. A 1-wide ladder on 4c
      legs prices a 0.18 debit at R 4.56, and the old code TOOK it: that is
      META/CRM/MU, three flies stopped out inside the minute they opened on
      floors of 4.3c to 7.0c. It is kept, inverted, as the refusal case —
      r155's rule that a fixture encoding the replaced rule is re-derived
      rather than deleted.
      B2's premise is gone outright: there is no computed wing to floor at one
      increment. What survives is the CAP (the near wing may not cross spot)
      and the new invariant that candidates come from listed strikes only.
v2.1  r170: clock pinned at 12:30 and atm_iv 0.43 (see check_plan_prepares
      v1.6) — the B pins were time-of-day dependent.
v2.0  (2026-08-27, r160)
v2.0  r160: RENAMED from check_leg2_levels.py. The L1-L13 leg-two pins are
      gone with the code they pinned — the condor no longer selects a level;
      tests/check_plan_prepares.py holds the leg-two hypotheticals now. Only
      the butterfly pins (B1-B4, r147) remain.

THE BUTTERFLY HAS LEGS.

  L1-L4  level_state: UNTESTED / BREACHED / REJECTED / ACCEPTED on a 1m tape,
         using the sweep detector's acceptance count.
  L5     leg two arms on the NEAREST valid level of the COMPLEMENTARY role.
  L6     BREACHED -> HOLD, no signal ("never sell on a level being breached").
  L7     REJECTED -> a VALID credit vertical beyond the level, R recorded.
  L8     STRICT vetoes a sub-1:1 leg two; RELAXED takes and records r_muted.
  L9     ACCEPTED -> the level is finished and the plan moves to the NEXT one.
  L10    a finished level survives a restart (reloaded from plan_ledger).
  L11    no candidate -> HOLD row saying leg two is off the table.
  L12    the pairing table filters level CLASS (trend-first -> named pools only).
  B1     the 2026-09-01 fly (1-wide ladder, 4c legs, R 4.56) is REFUSED, and
         the row names WHICH bound refused it.
  B2     a qualifying ladder fires the NARROWEST wing that clears both bounds.
  B3     no wing clears R 1.00 -> refused, best-available R stated.
  B4     no exact strike at the pin -> refused, never a nearest substitute.
"""
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
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


def _df(rows, t0):
    """1m bars from (high, low, close) tuples, starting at epoch t0."""
    import pandas as pd
    idx = pd.to_datetime([t0 + 60 * i for i in range(len(rows))], unit="s", utc=True)
    return pd.DataFrame({"open": [r[2] for r in rows], "high": [r[0] for r in rows],
                         "low": [r[1] for r in rows], "close": [r[2] for r in rows]},
                        index=idx)


class _C:
    def __init__(self, k, mark, delta=0.2, spread=0.02):
        self.strike, self.mark = float(k), float(mark)
        # ⚠️ THE LEG SPREAD IS A PARAMETER NOW, because it is half the
        # arithmetic: a fly's own quote is FOUR of these wide.
        self.bid, self.ask = mark - spread, mark + spread
        self.delta, self.gamma, self.theta = delta, 0.01, -0.03
        self.expiry, self.symbol, self.open_interest = "x", f"O{k}", 100


class _Chain:
    def __init__(self, calls, puts):
        self.calls, self.puts = calls, puts


def main():
    from strategy import plan as P
    st = _Store()
    P.bind_store(st)
    # HERMETIC LEDGER: the condor's leg-2 plan persists finished levels through
    # derived.registry.plan_ledger(); point it at the same in-memory store so
    # the test never touches (or is polluted by) a real derived_store.db.
    import derived.registry as _reg
    from derived.plan_ledger import PlanLedger
    _led = PlanLedger(st, "TST")
    _reg.plan_ledger = lambda symbol="": _led
    P.begin_tick(1.0)
    os.environ["OT_RELAXED_ENTRY"] = "0"

    # ── the butterfly ─────────────────────────────────────────────────────
    from strategy.gex_pin_butterfly import GEXPinButterflyStrategy
    import strategy.gex_pin_butterfly as bf
    bf.ENABLED = True
    bf.EARLIEST_ET, bf.LATEST_ET = "09:30", "16:00"

    class _GEX:
        gex_environment, pin_strike, pin_concentration = "PINNING", 101.0, 0.60

    # ⚠️ THE 2026-09-01 SHAPE, KEPT AS THE REFUSAL CASE. 1-wide ladder, 4c
    # legs. A fly's quote is FOUR leg-spreads wide, so no debit on this ladder
    # can both clear R 1.00 and hold a 25% floor: width >= 64 x leg-spread
    # means 4c legs need $2.56 of wing.
    calls = [_C(k, m) for k, m in ((99, 1.60), (100, 1.00), (101, 0.55), (102, 0.28), (103, 0.14))]
    chain_b = _Chain(calls, [])
    # PIN THE CLOCK (see check_plan_prepares): expected_move reads wall time.
    _em_real = bf.expected_move
    from utils.time_utils import ET as _ET
    _fixed_now = bf.datetime(2026, 8, 27, 12, 30, tzinfo=_ET)
    bf.expected_move = lambda u, iv, now=None: _em_real(u, iv, now=_fixed_now)
    b = GEXPinButterflyStrategy()

    # OTV4TEST r6: persistence is a bar (8 ticks); these fixtures assert SELECTION on
    # a single tick, so the bar is set to 1 here and pinned on its own in check_plan_prepares B13.
    import strategy.gex_pin_butterfly as _bfm; _bfm.PERSIST_TICKS = 1
    b.planner.symbol = "TST"
    P.begin_tick(20.0)
    sig = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=0.43,
                            chain=chain_b)
    rowb = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                           "strategy='GEXPinButterfly' AND ts_epoch=20.0").fetchone()
    check("B1 the 2026-09-01 fly is REFUSED, and the row names the bound",
          sig is None and rowb and rowb[0] == "DECLINE"
          and "wing_search" in (rowb[1] or "")
          and "clear their own spread" in (rowb[1] or ""), str(rowb))

    # ── B2 — a ladder where a fly IS constructible: narrowest wins ────────
    # Two wings clear both bounds (1-wide at R 1.50, 2-wide at R 1.00) and the
    # operator's rule is "1-R or better is the widest allowed, prefer narrower
    # if available", so the 1-wide is the answer.
    tight = [_C(k, m, spread=0.005) for k, m in
             ((99, 2.55), (100, 1.70), (101, 1.00), (102, 0.70), (103, 0.45))]
    P.begin_tick(20.5)
    sig_ok = b.generate_signal(gex=_GEX(), price_now=99.0, now_et="12:30", atm_iv=0.90,
                               chain=_Chain(tight, []))
    check("B2 a qualifying ladder fires the BEST-R wing of those that clear (r6)",
          sig_ok is not None and sig_ok.is_valid and sig_ok.is_butterfly
          and sig_ok.center_contract.strike == 101.0
          and sig_ok.lower_contract.strike == 100.0
          and sig_ok.upper_contract.strike == 102.0
          and sig_ok.butterfly_direction == "call" and sig_ok.net_debit > 0,
          f"legs={sig_ok and (sig_ok.lower_contract.strike, sig_ok.center_contract.strike, sig_ok.upper_contract.strike)}")

    check("B2b (r24) the fired fly carries the operator's 40% floor: stop = debit x 0.60",
          sig_ok is not None and abs(float(sig_ok.stop_loss_pct) - 0.40) < 1e-9
          and abs(float(sig_ok.stop_premium()) - float(sig_ok.net_debit) * 0.60) < 1e-9,
          f"stop_loss_pct={sig_ok and sig_ok.stop_loss_pct} stop={sig_ok and sig_ok.stop_premium()} "
          f"debit={sig_ok and sig_ok.net_debit}")

    # ── B3 — nothing clears R: refused, with the best R on the record ─────
    calls_fat = [_C(k, m, spread=0.005) for k, m in
                 ((99, 2.00), (100, 1.50), (101, 0.55), (102, 0.28), (103, 0.14))]
    P.begin_tick(21.0)
    sig2 = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=0.43,
                             chain=_Chain(calls_fat, []))
    row2 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                           "strategy='GEXPinButterfly' AND ts_epoch=21.0").fetchone()
    check("B3 no wing clears R 1.00 -> refused, best-available R stated",
          sig2 is None and row2 and row2[0] == "DECLINE"
          and "too wide for R>=" in (row2[1] or ""), str(row2))
    P.begin_tick(22.0)
    sig3 = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=0.43,
                             chain=_Chain([c for c in calls if c.strike != 101.0], []))
    row3 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                           "strategy='GEXPinButterfly' AND ts_epoch=22.0").fetchone()
    check("B4 no exact strike at the pin -> refused, never a nearest substitute",
          sig3 is None and row3 and "legs:" in (row3[1] or ""), str(row3))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_butterfly_legs: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
