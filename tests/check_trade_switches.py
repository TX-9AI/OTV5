#!/usr/bin/env python3
"""
tests/check_trade_switches.py  v5.0
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

WHAT IT DRIVES (the REAL plans, on setups that FIRE when the switch is on):
  S1  VOLT, switch UNSET: VoltPlan.prepare on a firing setup prepares NOTHING,
      and VoltStrategy.generate_signal returns None.
  S2  VOLT, OT_VOLT=1: the same setup prepares a trade (the unchanged path).
  S3  ORB, switch UNSET: ORBPlan.prepare on a CONFIRMED long prepares NOTHING.
  S4  ORB, OT_ORB_TRADE=1: the same confirmed long is ready (unchanged path).
  S5  the switches are read at CALL time (a checker or a box can set them
      after import), and only the literal "1" turns a strategy on.
  S6  UNCHANGED: orb_plan.select_contract (Breakout's selector) still selects
      with the ORB trade off, and the real ORBEngine still arms on a break.
  S7  THE 10:29 DEBIT CUTOFF, real VOLT plan (switched on): ready at 10:29,
      DORMANT at 10:30.
  S8  config.ENTRY_WINDOWS ends Runaway, Hunt, Breakout and VOLT at (10, 30),
      and the modules that act on it read it (runaway _cutoff_hm, hunt and
      breakout constants).
  S9  UNCHANGED: the ORBStrategy row, both butterflies and both credit spreads
      keep their windows (the GEX pin fly is exempt by ruling).
  S11 OT_RUNAWAY_END (r189), FRESH interpreter per case: unset -> every Runaway
      window reader says 10:30; "11:30" -> all say 11:30; "1130", "16:30",
      "09:30", "11:75" -> REFUSED (named) and all say 10:30; Hunt, Breakout and
      VOLT stay at 10:30 in every case.
  S10 THE ATP FLY, in a FRESH interpreter (its plan reads the flag at import):
      switch UNSET -> config.ATP_BUTTERFLY_ENABLED and atp_butterfly_plan.ENABLED
      are both False, and so with "true"; OT_ATP_BUTTERFLY=1 -> both True.
Run:  python3 tests/check_trade_switches.py   (exit 0 green, 1 red)
"""
import datetime as dt
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
_S = tempfile.mkdtemp(prefix="check_trade_switches_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
for _k in ("OT_VOLT", "OT_ORB_TRADE", "OT_RUNAWAY_END"):
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


# ── VOLT fixture (check_volt_plan's shape: a bar series that fires) ──────────
class _C:
    def __init__(self, strike, mark=1.00, delta=0.5, gamma=0.01):
        self.strike, self.mark, self.delta, self.gamma = strike, mark, delta, gamma
        self.bid, self.ask = max(0.01, mark - 0.02), mark + 0.02
        self.expiry = "2026-09-21"


class _Chain:
    def __init__(self, spot):
        self.calls = [_C(float(int(spot) + i)) for i in (-2, -1, 0, 1, 2)]
        self.puts = [_C(float(int(spot) + i)) for i in (-2, -1, 0, 1, 2)]


def _volt_frame(last_close, last_vol, n_base, session_open=100.0):
    rows, idx = [], []
    seq = [(100.0, 1000.0)] * n_base + [(last_close, last_vol), (last_close, last_vol)]
    t0 = dt.datetime(2026, 9, 21, 9, 30)
    for bi, (close, vol) in enumerate(seq):
        o = session_open if bi == 0 else close
        rows.append({"open": o, "high": max(o, close) + 0.05, "low": min(o, close) - 0.05,
                     "close": close, "volume": vol})
        idx.append(t0 + dt.timedelta(minutes=bi))
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))


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
    from strategy import plan as P
    st = _Store(); P.ensure_tables(st); P.bind_store(st)
    from strategy.volt_plan import VoltPlan, VOL_LOOKBACK_BARS, VOL_MULT
    from strategy.volt_strategy import VoltStrategy
    from strategy.orb_plan import ORBPlan, select_contract
    from analysis.orb_engine import ORBState

    n_base = VOL_LOOKBACK_BARS + 2
    df_fire = _volt_frame(101.0, 1000.0 * (VOL_MULT + 0.5), n_base)

    def volt_prep():
        P.begin_tick()
        p = VoltPlan().prepare(chain=_Chain(101.0), price_now=101.0, df_1m=df_fire, now_hhmm="10:00")
        P.close_tick(st, "TEST"); return p

    def orb_prep(eng):
        P.begin_tick()
        p = ORBPlan().prepare(orb=eng._data, chain=_orb_chain(), price_now=707.95, now_hhmm="09:40")
        P.close_tick(st, "TEST"); return p

    # S1 / S2 — VOLT
    off = volt_prep()
    sig = VoltStrategy().generate_signal(chain=_Chain(101.0), price_now=101.0, df_1m=df_fire, now_et="10:00")
    check("S1 VOLT with OT_VOLT UNSET prepares nothing and signals nothing",
          not off.ready and off.contract is None and sig is None, f"ready={off.ready} signal={sig is not None}")
    os.environ["OT_VOLT"] = "1"
    on = volt_prep()
    check("S2 OT_VOLT=1 - the same setup prepares a trade (unchanged path)",
          on.ready and on.contract is not None, f"ready={on.ready}")
    os.environ.pop("OT_VOLT", None)

    # S3 / S4 — ORB trade
    eng, armed = _confirmed_long()
    check("S3pre the real engine armed and confirmed the long",
          armed and eng._data.state == ORBState.OPEN_LONG, str(eng._data.state))
    o_off = orb_prep(eng)
    check("S3 ORB with OT_ORB_TRADE UNSET prepares nothing on a confirmed long",
          not o_off.ready and o_off.contract is None, f"ready={o_off.ready}")
    os.environ["OT_ORB_TRADE"] = "1"
    eng2, _ = _confirmed_long()
    o_on = orb_prep(eng2)
    check("S4 OT_ORB_TRADE=1 - the confirmed long is ready (unchanged path)",
          o_on.ready and o_on.contract is not None, f"ready={o_on.ready}")
    os.environ.pop("OT_ORB_TRADE", None)

    # S5 — call-time read; only the literal "1"
    os.environ["OT_VOLT"] = "true"
    odd = volt_prep()
    os.environ["OT_VOLT"] = "1"; late = volt_prep(); os.environ.pop("OT_VOLT", None)
    check("S5 read at CALL time, and only the literal '1' turns VOLT on ('true' stays off)",
          (not odd.ready) and late.ready, f"'true'->{odd.ready} '1'->{late.ready}")

    # S6 — unchanged: Breakout's selector, the ORB engine
    c = select_contract(_orb_chain(), "long", 709.19)
    eng3, armed3 = _confirmed_long()
    check("S6 UNCHANGED: orb_plan.select_contract still selects (709C) and the ORB engine still arms",
          c is not None and float(c.strike) == 709.0 and armed3, f"contract={getattr(c, 'strike', None)} armed={armed3}")

    # S7 — the cutoff on the real VOLT plan
    os.environ["OT_VOLT"] = "1"
    def volt_at(hhmm):
        P.begin_tick()
        p = VoltPlan().prepare(chain=_Chain(101.0), price_now=101.0, df_1m=df_fire, now_hhmm=hhmm)
        P.close_tick(st, "TEST"); return p
    a, b = volt_at("10:29"), volt_at("10:30"); os.environ.pop("OT_VOLT", None)
    check("S7 the 10:29 cutoff: VOLT (switched on) is ready at 10:29 and DORMANT at 10:30",
          a.ready and not b.ready, f"10:29 ready={a.ready} 10:30 ready={b.ready}")
    # S8 — the table and the modules that act on it
    import config as C
    import strategy.runaway_plan as RP, strategy.liquidity_hunt as LH, strategy.breakout as BR
    want = (10, 30)
    ends = {k: tuple(C.ENTRY_WINDOWS[k][1]) for k in ("RunawayContinuation", "LiquidityHunt", "Breakout", "VOLT")}
    acts = {"runaway": tuple(RP._cutoff_hm()), "hunt": tuple(LH.CUTOFF_ET), "breakout": str(BR.LATEST_ET)}
    check("S8 Runaway/Hunt/Breakout/VOLT windows end at 10:30 and their modules read it",
          all(v == want for v in ends.values()) and acts["runaway"] == want and acts["hunt"] == want
          and acts["breakout"] == "10:30", f"{ends} {acts}")
    # S9 — unchanged rows
    keep = {k: tuple(map(tuple, C.ENTRY_WINDOWS[k])) for k in ("ORBStrategy", "GEXPinButterfly", "ATPButterfly",
                                                              "SweepCreditSpread", "TrendCreditSpread")}
    eod = tuple(C.EOD_SCHEDULE["entries_stop"])
    check("S9 UNCHANGED: ORB row, both flies (13:00-15:00, r273), Sweep and TCS keep their windows",
          keep["ORBStrategy"] == ((9, 35), eod) and keep["GEXPinButterfly"] == ((13, 0), (15, 0))
          and keep["ATPButterfly"] == ((13, 0), (15, 0)) and keep["SweepCreditSpread"] == ((9, 35), eod)
          and keep["TrendCreditSpread"] == ((11, 31), eod), str(keep))

    # S10 — the ATP fly off by default, read in a fresh interpreter each way
    import subprocess
    sps = _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages"))   # r106 bootstrap, as above
    code = ("import sys; sys.path[1:1] = %r; sys.path.insert(0, %r); import config, strategy.atp_butterfly_plan as A; "
            "print(config.ATP_BUTTERFLY_ENABLED, A.ENABLED)" % (sps, _root))
    got = {}
    for label, val in (("unset", None), ("true", "true"), ("1", "1")):
        env = dict(os.environ); env.pop("OT_ATP_BUTTERFLY", None)
        if val is not None:
            env["OT_ATP_BUTTERFLY"] = val
        r = subprocess.run([sys.executable, "-c", code], cwd=_root, env=env, capture_output=True, text=True)
        got[label] = (r.stdout.strip().splitlines() or [r.stderr.strip()[-160:]])[-1]
    check("S10 the ATP fly is OFF unset or 'true' (config and its plan), ON only with OT_ATP_BUTTERFLY=1",
          got["unset"] == "False False" and got["true"] == "False False" and got["1"] == "True True", str(got))

    # S11 — OT_RUNAWAY_END, read in a fresh interpreter per case (config resolves it at import)
    code11 = ("import sys; sys.path[1:1] = %r; sys.path.insert(0, %r); import config as C; "
              "import execution.position_manager as PM, strategy.runaway_continuation as RC, "
              "strategy.runaway_plan as RP; "
              "w = lambda k: '%%d:%%02d' %% tuple(C.ENTRY_WINDOWS[k][1]); "
              "rules = PM._DEFAULT_RULES; adm = [r for k, r in rules.items() if 'Runaway' in str(k)]; "
              "a = adm[0].window[1] if adm else None; "
              "print('|'.join([w('RunawayContinuation'), '%%d:%%02d' %% tuple(a), str(C.RUNAWAY_CUTOFF_ET), "
              "str(RC.CUTOFF_ET), '%%d:%%02d' %% tuple(RP._cutoff_hm()), w('LiquidityHunt'), w('Breakout'), "
              "w('VOLT'), repr(getattr(C, 'RUNAWAY_END_ENV_REFUSED', '<absent>'))]))" % (sps, _root))
    got11 = {}
    for val in (None, "11:30", "1130", "16:30", "09:30", "11:75"):
        env = dict(os.environ); env.pop("OT_RUNAWAY_END", None)
        if val is not None:
            env["OT_RUNAWAY_END"] = val
        r = subprocess.run([sys.executable, "-c", code11], cwd=_root, env=env, capture_output=True, text=True)
        got11[val] = (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]
    want11 = {None: "10:30|10:30|10:30|10:30|10:30|10:30|10:30|10:30|''",
              "11:30": "11:30|11:30|11:30|11:30|11:30|10:30|10:30|10:30|''"}
    for bad in ("1130", "16:30", "09:30", "11:75"):
        want11[bad] = "10:30|10:30|10:30|10:30|10:30|10:30|10:30|10:30|%r" % bad
    check("S11 OT_RUNAWAY_END moves Runaway's end in every reader (and nothing else); a bad value is REFUSED and named",
          all(got11[k] == want11[k] for k in want11),
          "; ".join(f"{k}: {got11[k]}" for k in want11 if got11[k] != want11[k]) or "all match")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}"); return 1
    print("\nGREEN — VOLT, the ORB trade and the ATP fly off by default; each restorable by switch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
