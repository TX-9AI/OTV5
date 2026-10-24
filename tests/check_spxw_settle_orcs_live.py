#!/usr/bin/env python3
"""
tests/check_spxw_settle_orcs_live.py  v1.1
v1.1  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject OpeningRangeCreditSpread is DORMANT by default and a dormant plan now
      writes nothing by ruling, so this run switches it ACTIVE (OT_ORCS=1); what it pins is unchanged.
v1.0  2026-10-04  OTV4TEST r247 (FORK-ONLY) — TWO LIVE-PATH FINDINGS FROM SPX-TEST'S AUDIT, FIXED BY THE
      OPERATOR'S ORDER ("Fix the SPXW settlement", "Fix the ORCS ledger rows issue").

  S1  an expired position whose underlying is "SPXW" settles at the SPX INDEX's 16:00 close (the store keeps
      the index tape under "SPX") - it found no bars and booked a flagged $0.00
  S2  "SPX" and "QQQ" read their own tape, unchanged; a symbol with no bars is still None (flagged, never a guess)
  O1  a LIVE box: _attempt_orcs writes NO plan_ledger row and makes NO entry call for a ready ORCS side
      (the refusal sat in _execute_condor_leg, AFTER ledger_open, so every ready side left an orphan row)
  O2  a PAPER box: unchanged - ledger_open, then the entry, once per ready side
Drives the REAL main._settlement_spot against a scratch feed store built by the real FeedStore, and the REAL
main._attempt_orcs with the strategy and the entry stubbed. No network, no live store.
Run: python3 tests/check_spxw_settle_orcs_live.py
"""
import os, sys, tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_ORCS"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    d = tempfile.mkdtemp(prefix="check_spxw_settle_")
    os.environ["OT_FEED_DB"] = os.path.join(d, "feed_store.db")
    os.environ.setdefault("OT_LOG_FILE", os.path.join(d, "bot.log"))
    try:
        from data.candle_feed import FeedStore
        fs = FeedStore(os.environ["OT_FEED_DB"])
        ET = ZoneInfo("America/New_York")
        t1559 = int(datetime(2026, 10, 2, 15, 59, tzinfo=ET).timestamp() * 1000)
        for sym, px in (("SPX", 7700.5), ("QQQ", 749.25)):
            fs.conn.execute("INSERT INTO candles VALUES (?,'1m',?,?,?,?,?,0)",
                            (sym, t1559, px, px + 1, px - 1, px))
        fs.conn.commit()
        fs.conn.close()
        import main as M
        spxw = M._settlement_spot("SPXW", "2026-10-02")
        check("S1 SPXW settles at the SPX index's 16:00 close (7700.50), not a flagged None",
              spxw == 7700.5, f"got {spxw!r}")
        own = (M._settlement_spot("SPX", "2026-10-02"), M._settlement_spot("QQQ", "2026-10-02"),
               M._settlement_spot("NVDA", "2026-10-02"))
        check("S2 SPX and QQQ read their own tape; a symbol with no bars stays None",
              own == (7700.5, 749.25, None), f"got {own!r}")

        calls = []

        class _Orcs:
            name = "OpeningRangeCreditSpread"

            def generate_signals(self, **kw):
                return [SimpleNamespace(strategy_name="OpeningRangeCreditSpread", side="put")]

            def ledger_open(self, sig):
                calls.append("ledger_open")

        saved = (M._orcs_strategy, M._execute_condor_leg)
        try:
            M._orcs_strategy = _Orcs()
            M._execute_condor_leg = lambda sig, state, ctx: calls.append("entry")
            ctx = {"price": 7700.0, "orb_high": 7710.0, "orb_low": 7690.0, "chain": None, "gap": None,
                   "macro": None}
            M._attempt_orcs(ctx, SimpleNamespace(paper_trading=False))
            live = list(calls)
            calls.clear()
            M._attempt_orcs(ctx, SimpleNamespace(paper_trading=True))
            paper = list(calls)
        finally:
            M._orcs_strategy, M._execute_condor_leg = saved
        check("O1 LIVE: no plan_ledger row and no entry call for a ready ORCS side", live == [], f"calls={live}")
        check("O2 PAPER: unchanged - ledger_open then the entry", paper == ["ledger_open", "entry"],
              f"calls={paper}")
    except Exception as exc:  # noqa: BLE001
        check("X0 (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {sorted(set(FAILED))}"); return 1
    print("\nGREEN — SPXW settles on the index; a live box writes no ORCS row"); return 0


if __name__ == "__main__":
    sys.exit(main())
