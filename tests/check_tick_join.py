#!/usr/bin/env python3
"""
tests/check_tick_join.py  v1.0  (2026-08-29, r177)

TWO WEEKEND FIXES, BOTH PINNED AT THE SEAM.

Born red at 7f60245 (r176): OptionsChain had no atm_iv and no table carried
a tick_id.

  A1  OptionsChain.atm_iv assembles a DECIMAL ATM iv from the streamed
      per-contract ivs (median of the 3 nearest per side)
  A2  a chain whose feed has not populated ivs reads 0.0 — the butterfly's
      no-fallback starvation stays LOUD; we fixed the supply, not the rule
  A3  main's butterfly dispatch expression resolves a REAL value now — the
      exact getattr that read the absent field for three weeks
  J1  plan_tick, plan_check and strategy_note rows written in the same tick
      carry the SAME tick_id — the fit joins BY KEY, not by timestamp
  J2  a store created BEFORE r177 gains the column in place; its old rows
      read 0, which no join matches
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


def main():
    from data.options_chain import OptionsChain, OptionContract

    def _c(k, iv):
        c = OptionContract()
        c.strike, c.iv, c.bid, c.ask = float(k), iv, 0.5, 0.6
        return c

    ch = OptionsChain(underlying="TST", spot_price=100.0,
                      calls=[_c(100, 0.41), _c(101, 0.43), _c(102, 0.45), _c(110, 2.0)],
                      puts=[_c(100, 0.44), _c(99, 0.42), _c(98, 0.40), _c(90, 0.02)])
    check("A1 atm_iv is the median of the nearest streamed ivs, decimal",
          0.40 <= ch.atm_iv <= 0.45, f"{ch.atm_iv:.3f}")
    ch0 = OptionsChain(underlying="TST", spot_price=100.0,
                       calls=[_c(100, 0.0)], puts=[_c(100, 0.0)])
    check("A2 no ivs from the feed -> 0.0: the starvation stays loud", ch0.atm_iv == 0.0)
    _atm = float(getattr(ch, "atm_iv", 0.0) or 0.0) or None
    check("A3 the dispatch expression that starved the butterfly resolves a real value",
          _atm is not None and abs(_atm - ch.atm_iv) < 1e-12, str(_atm))
    msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    check("A3b main still reads chain.atm_iv (the supply feeds the existing seam)",
          'getattr(chain, "atm_iv"' in msrc)

    # ── the join key ─────────────────────────────────────────────────────
    from strategy import plan as P
    from derived.notes import NoteWriter
    st = _Store()
    P.bind_store(st)
    n = P.begin_tick(77.0)
    t = P.Plan("JoinProbe", ("x",)).tick(100.0)
    t.check("x", 1.0, True)
    t.hold("join probe")
    NoteWriter(st, "TST").write("JoinProbe", {"price": 100.0}, fired=False)
    ids = {r[0] for r in st.conn.execute(
        "SELECT tick_id FROM plan_tick WHERE strategy='JoinProbe'").fetchall()}
    ids |= {r[0] for r in st.conn.execute(
        "SELECT tick_id FROM plan_check WHERE strategy='JoinProbe'").fetchall()}
    ids |= {r[0] for r in st.conn.execute(
        "SELECT tick_id FROM strategy_note WHERE strategy='JoinProbe'").fetchall()}
    check("J1 plan_tick + plan_check + strategy_note in one tick share ONE tick_id",
          ids == {n}, f"ids={ids} expected={{{n}}}")

    # J2 — a pre-r177 store migrates in place
    old = _Store()
    old.conn.execute("CREATE TABLE plan_tick (ts_epoch REAL NOT NULL, symbol TEXT NOT NULL,"
                     " strategy TEXT NOT NULL, verdict TEXT NOT NULL, reason TEXT,"
                     " trigger_price REAL, invalidation REAL, underlying REAL,"
                     " dist_to_trigger REAL, r_now REAL,"
                     " direction TEXT NOT NULL DEFAULT '',"
                     " PRIMARY KEY (ts_epoch, symbol, strategy, direction))")
    old.conn.execute("INSERT INTO plan_tick (ts_epoch, symbol, strategy, verdict)"
                     " VALUES (1.0,'TST','Old','HOLD')")
    old.conn.execute("CREATE TABLE plan_check (ts_epoch REAL NOT NULL, symbol TEXT NOT NULL,"
                     " strategy TEXT NOT NULL, check_name TEXT NOT NULL, value REAL,"
                     " verdict TEXT, direction TEXT NOT NULL DEFAULT '',"
                     " PRIMARY KEY (ts_epoch, symbol, strategy, check_name, direction))")
    old.commit()
    P.bind_store(old)
    m = P.begin_tick(78.0)
    t2 = P.Plan("MigProbe", ("x",)).tick(100.0)
    t2.check("x", 1.0, True)
    t2.hold("migrated")
    rows = old.conn.execute("SELECT strategy, tick_id FROM plan_tick ORDER BY ts_epoch").fetchall()
    check("J2 a pre-r177 store gains tick_id in place: old rows read 0, new rows the key",
          ("Old", 0) in rows and ("MigProbe", m) in rows, str(rows))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_tick_join: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
