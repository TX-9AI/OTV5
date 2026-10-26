#!/usr/bin/env python3
"""
tests/check_manage_board_clears.py  v5.0
v5.0  2026-10-26  OTV5 r35 (PLN.3) — A CLOSED POSITION'S MANAGE VERDICT LEAVES THE [plans] LINE.
      SPX 2026-10-26: "RunawayContinuation/manage=CLOSE(... -34%)" stayed on the line from the 09:40 close to 16:02;
      12 of 14 boxes the same. Driven through the real PlanEngine.derive (close_tick, the board, begin_tick) on an
      in-memory store, the line captured from the "derived.plans" logger.

  M1  a tick where Breakout/manage runs and writes CLOSE: the next [plans] line shows Breakout/manage=CLOSE
  M2  the next tick, where it is not run (the position is closed): the line no longer shows Breakout/manage
  M3  a non-condition plan that did not run this tick (Breakout) stays on the line (close_tick writes its default)
  M4  running Breakout/manage again (a new position) puts it back on the line

Born red on 4465ec8 at M2 (board_line ran after begin_tick and had no /manage rule).
Run:  python3 tests/check_manage_board_clears.py
"""
import logging
import os
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_PLAN_BOARD_LOG_S"] = "0.0001"
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(); self.lines = []

    def emit(self, r):
        m = r.getMessage()
        if m.startswith("[plans] "):
            self.lines.append(m)


def main():
    from strategy import plan as P
    from derived import plans as DP

    class St:
        def __init__(s): s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()
    st = St()
    eng = DP.PlanEngine(st, "TST")
    cap = _Cap(); lg = logging.getLogger("derived.plans"); lg.addHandler(cap); lg.setLevel(logging.INFO)
    brk = P.REGISTRY.get("Breakout") or P.Plan("Breakout", ("x",))
    man = P.REGISTRY.get("Breakout/manage") or P.Plan("Breakout/manage", ("pnl",))

    def board():
        time.sleep(0.002)
        eng._last_board_log = 0.0
        eng.derive({})
        return cap.lines[-1] if cap.lines else ""

    P.begin_tick(time.time())
    t = brk.tick(100.0); t.check("x", 1, False); t.hold("waiting on: x")
    t = man.tick(100.0); t.check("pnl", -0.34, False); t.hold("floor crossed -34%", verdict="CLOSE")
    line1 = board()
    check("M1 the tick it ran: Breakout/manage=CLOSE is on the line", "Breakout/manage=CLOSE" in line1, line1[:160])

    t = brk.tick(100.0); t.check("x", 1, False); t.hold("waiting on: x")      # manage not run: closed
    line2 = board()
    check("M2 the next tick (position closed, manage not run): Breakout/manage is off the line",
          "Breakout/manage=" not in line2, line2[:160])
    line3 = board()                                                       # Breakout itself not run this tick either
    check("M3 a non-condition plan not run this tick stays on the line", "Breakout=" in line3, line3[:160])

    t = man.tick(100.0); t.check("pnl", 0.10, True); t.hold("holding +10%")
    line4 = board()
    check("M4 a new position: Breakout/manage is back on the line", "Breakout/manage=HOLD" in line4, line4[:160])

    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
