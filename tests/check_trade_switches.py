#!/usr/bin/env python3
"""
tests/check_trade_switches.py  v5.4
v5.4  2026-11-08  OTV5 r88 (RETIRE.3) — S9 pins the GEX fly's window and that the TCS row is removed (r88).
v5.3  2026-11-08  OTV5 r84 (VENV.1) — a bare run (control's /usr/bin/python3 3.14, no pandas) stops with one
      ModuleNotFoundError line naming the venv to use, not a traceback: utils.venv_guard.require_venv before the first
      third-party import. Under the venv nothing changes.
v5.2  2026-11-08  OTV5 r76 (RETIRE.1) — RE-POINTED (section 38.4): VOLT, the ORB trade and the ATP fly are REMOVED, not
      switched off, so S1-S5, S7 and S10 (their switches) go with them and S0 pins that their modules and keys are
      gone; S6 (Breakout's selector and the ORB ENGINE), S8 (the 10:30 ends), S9 (the fly and TCS windows) and S11
      (Runaway's fixed end) are kept, minus the removed rows. The operator, 2026-11-07: "Yes, I want all of those things
      fixed."
v5.1  2026-10-31  OTV5 r68 (CFG.5) — S11 RE-POINTED, NOT DROPPED (section 38.4): config v5.10 fixes Runaway's end at 10:30 and reads
      no OT_RUNAWAY_END (the operator, 2026-10-31: "10&11–defaults are fine, take them out"), so the same six cases now read
      10:30 in all five Runaway readers and RUNAWAY_END_ENV_REFUSED is absent. Hunt / Breakout / VOLT unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.3  2026-10-12  OTV4TEST r273 (BFLY.10) — S9's fly rows RE-POINTED 12:00 -> 13:00. r273 (BFLY.10), by ruling - the operator, 2026-10-12: "reduce the fly window to 1300".
v1.2  2026-10-03  OTV4TEST r189 (RUNW.1) — S11: OT_RUNAWAY_END MOVES RUNAWAY'S END AND NOTHING ELSE.
      In a fresh interpreter per case, every reader of the window - config.ENTRY_WINDOWS, the admission
      table (position_manager._DEFAULT_RULES), config.RUNAWAY_CUTOFF_ET, runaway_continuation.CUTOFF_ET,
      runaway_plan._cutoff_hm - says 10:30 unset, 11:30 with "11:30", and 10:30 again (with the value
      named in RUNAWAY_END_ENV_REFUSED) for "1130", "16:30", "09:30" and "11:75"; Hunt, Breakout and VOLT
      stay at 10:30 throughout. The operator, 2026-10-03: "Yes" to the switch, for SPX-TEST.
v1.1  2026-10-02  OTV4TEST r187 — S10: THE ATP BUTTERFLY IS OFF BY DEFAULT. The operator,
      2026-10-02 21:39 ET: "Turn off the ATP". config.ATP_BUTTERFLY_ENABLED now
      defaults "0"; OT_ATP_BUTTERFLY=1 restores it. The pin fly is untouched.
v1.0  2026-10-02  OTV4TEST r187 (ROSTER.1) — VOLT IS OFF AND THE ORB TRADE IS RETIRED
      BY DEFAULT; OT_VOLT=1 / OT_ORB_TRADE=1 bring each back exactly as it was.
      The operator, 2026-10-02 21:05 ET, on the week's evidence: "1. CONCUR"
      (VOLT off), "2. CONCUR" (retire the ORB trade, keep Breakout; BRT.1's
      10-01 ruling), and earlier "My intent is to change Trading behavior this
      coming week". The opening-range ENGINE is untouched - Runaway, Breakout,
      Hunt, anchors, management and the exit engine all read it.

WHAT IT DRIVES:
  S0  the removed trades are gone: no strategy/volt_*, orb_strategy, atp_butterfly* module imports, and config
      reads no OT_VOLT / OT_ORB_TRADE / OT_ATP_BUTTERFLY key
  S6  UNCHANGED: orb_plan.select_contract (Breakout's selector) still selects, and the real ORBEngine still arms
  S8  config.ENTRY_WINDOWS ends Runaway, Hunt and Breakout at (10, 30), and the modules that act on it read it
  S9  UNCHANGED: the GEX fly (13:00-15:00, r273) and TCS keep their windows
  S11 OT_RUNAWAY_END (r189; r68: no longer read), FRESH interpreter per case: every Runaway window reader says
      10:30, RUNAWAY_END_ENV_REFUSED is absent; Hunt and Breakout stay at 10:30 in every case.
Run:  python3 tests/check_trade_switches.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
from utils.venv_guard import require_venv                         # noqa: E402  (stdlib only)
require_venv('pandas')
_S = tempfile.mkdtemp(prefix="check_trade_switches_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
for _k in ("OT_RUNAWAY_END",):
    os.environ.pop(_k, None)                                 # the default is what is tested first

import pandas as pd

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:"); self.conn.row_factory = sqlite3.Row
    def commit(self): self.conn.commit()


# ── ORB fixture (check_orb_plan's: a real engine broken and retested long) ──
def _frame(rows):
    return pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
                        index=pd.date_range("2026-09-08 09:35", periods=len(rows), freq="1min"))


def _confirmed_long():
    from analysis.orb_engine import ORBEngine, ORBState
    eng = ORBEngine(); d = eng._data
    d.orb_high, d.orb_low, d.orb_width = 707.70, 706.21, round(707.70 - 706.21, 2)
    d.state = ORBState.WAITING_FOR_BREAK
    eng._check_for_break(_frame([(706.90, 708.60, 707.10, 708.40), (708.40, 708.70, 708.30, 708.50)]))
    armed = d.state == ORBState.ARMED_LONG
    eng._check_for_retest(_frame([(707.90, 708.10, 707.65, 707.95), (707.95, 708.20, 707.90, 708.10)]))
    return eng, armed


def _orb_chain():
    from data.options_chain import OptionContract, OptionsChain
    ch = OptionsChain(underlying="TEST", expiry="2026-09-08", spot_price=707.0); ch.calls, ch.puts = [], []
    for k in (700, 702, 704, 705, 706, 707, 708, 709, 710, 712, 714):
        m = max(0.06, round(1.60 - 0.30 * abs(k - 707.0), 2))
        ch.calls.append(OptionContract(symbol=f"C{k}", strike=float(k), mark=m, bid=m - 0.02, ask=m + 0.02,
                                       delta=max(0.05, 0.50 - 0.08 * (k - 707.0)), gamma=0.03,
                                       expiry="2026-09-08", option_type="C"))
        ch.puts.append(OptionContract(symbol=f"P{k}", strike=float(k), mark=m, bid=m - 0.02, ask=m + 0.02,
                                      delta=-max(0.05, 0.50 - 0.08 * (707.0 - k)), gamma=0.03,
                                      expiry="2026-09-08", option_type="P"))
    return ch


def main():
    import config as C
    from strategy.orb_plan import select_contract

    # S0 — the removed trades are gone
    from retired_names import importers
    still = [m for m in ("strategy.volt_plan", "strategy.volt_strategy", "strategy.orb_strategy",
                         "strategy.atp_butterfly", "strategy.atp_butterfly_plan") if importers(m)]
    src = open(os.path.join(_root, "config.py")).read() + open(os.path.join(_root, "strategy", "plan_state.py")).read()
    keys = [k for k in ("OT_VOLT", "OT_ORB_TRADE", "OT_ATP_BUTTERFLY") if f'"{k}"' in src]
    check("S0 VOLT, the ORB trade and the ATP fly are removed: no module imports, no switch is read",
          not still and not keys, f"modules {still}, keys {keys}")

    # S6 — unchanged: Breakout's selector, the ORB engine
    c = select_contract(_orb_chain(), "long", 709.19)
    eng3, armed3 = _confirmed_long()
    check("S6 UNCHANGED: orb_plan.select_contract still selects (709C) and the ORB engine still arms",
          c is not None and float(c.strike) == 709.0 and armed3, f"contract={getattr(c, 'strike', None)} armed={armed3}")

    # S8 — the table and the modules that act on it
    import strategy.runaway_plan as RP, strategy.liquidity_hunt as LH, strategy.breakout as BR
    want = (10, 30)
    ends = {k: tuple(C.ENTRY_WINDOWS[k][1]) for k in ("RunawayContinuation", "LiquidityHunt", "Breakout")}
    acts = {"runaway": tuple(RP._cutoff_hm()), "hunt": tuple(LH.CUTOFF_ET), "breakout": str(BR.LATEST_ET)}
    check("S8 Runaway/Hunt/Breakout windows end at 10:30 and their modules read it",
          all(v == want for v in ends.values()) and acts["runaway"] == want and acts["hunt"] == want
          and acts["breakout"] == "10:30", f"{ends} {acts}")
    # S9 — unchanged rows
    keep = {k: tuple(map(tuple, C.ENTRY_WINDOWS[k])) for k in ("GEXPinButterfly",)}
    check("S9 UNCHANGED: the GEX fly keeps its window (13:00-15:00, r273); the TCS row is removed (r88)",
          keep["GEXPinButterfly"] == ((13, 0), (15, 0)) and "TrendCreditSpread" not in C.ENTRY_WINDOWS, str(keep))

    import subprocess
    sps = _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages"))   # r106 bootstrap, as above
    # S11 — OT_RUNAWAY_END, read in a fresh interpreter per case (config resolves it at import)
    code11 = ("import sys; sys.path[1:1] = %r; sys.path.insert(0, %r); import config as C; "
              "import execution.position_manager as PM, strategy.runaway_continuation as RC, "
              "strategy.runaway_plan as RP; "
              "w = lambda k: '%%d:%%02d' %% tuple(C.ENTRY_WINDOWS[k][1]); "
              "rules = PM._DEFAULT_RULES; adm = [r for k, r in rules.items() if 'Runaway' in str(k)]; "
              "a = adm[0].window[1] if adm else None; "
              "print('|'.join([w('RunawayContinuation'), '%%d:%%02d' %% tuple(a), str(C.RUNAWAY_CUTOFF_ET), "
              "str(RC.CUTOFF_ET), '%%d:%%02d' %% tuple(RP._cutoff_hm()), w('LiquidityHunt'), w('Breakout'), "
              "repr(getattr(C, 'RUNAWAY_END_ENV_REFUSED', '<absent>'))]))" % (sps, _root))
    got11 = {}
    for val in (None, "11:30", "1130", "16:30", "09:30", "11:75"):
        env = dict(os.environ); env.pop("OT_RUNAWAY_END", None)
        if val is not None:
            env["OT_RUNAWAY_END"] = val
        r = subprocess.run([sys.executable, "-c", code11], cwd=_root, env=env, capture_output=True, text=True)
        got11[val] = (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]
    # r68 (CFG.5): the operator, 2026-10-31, "10&11–defaults are fine, take them out" - the key is not read, so every
    # case reads 10:30 in every reader, and RUNAWAY_END_ENV_REFUSED no longer exists.
    want11 = {k: "10:30|10:30|10:30|10:30|10:30|10:30|10:30|'<absent>'"
              for k in (None, "11:30", "1130", "16:30", "09:30", "11:75")}
    check("S11 OT_RUNAWAY_END is not read (r68): every Runaway reader says 10:30 unset, '11:30' or junk; nothing else moves",
          all(got11[k] == want11[k] for k in want11),
          "; ".join(f"{k}: {got11[k]}" for k in want11 if got11[k] != want11[k]) or "all match")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}"); return 1
    print("\nGREEN — the removed trades are gone; Breakout's selector, the engine and the live windows unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
