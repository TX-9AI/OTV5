#!/usr/bin/env python3
"""
tests/check_exhaust_session.py  v5.0
v5.0  2026-10-31  OTV5 r62 (BRK.18) — THE EXHAUSTION EXIT'S ROC5 NEVER REACHES INTO THE PRIOR SESSION. A TRADING FIX; the
      operator, on hearing of it: "this is a fucking problem". exit_engine._momentum_divergence's momentum is the 5m close
      minus the close 5 rows back; until today's sixth 5m bar (09:55 ET) the row 5 back is YESTERDAY's. The 2026-10-30
      review (~/reviews/2026-10-30.md, the exhaust_* plan check rows r55 writes): every Breakout open before 09:55 read
      "ROC5 = 5m close 2026-10-30T09:35 minus 5m close 2026-10-29T15:40" - AMZN 067dbb54 (gapped down after earnings,
      rallying) ROC5 -9.95 / -8.00 on each new high, AVGO -14..-17, SPX -85.82 - and NFLX 3d320e88 was CLOSED 09:44:48 ET
      on "exhaustion: new short extreme 62.13 (ROC5 +0.23, 5m 09:40 forming) vs prior 62.16 (ROC5 +0.21)", both read
      from 10-29 15:45's close. The fix: a reading only when at least 6 of the frame's trailing rows are on the last
      row's ET date - else the "no reading" path a short frame has always taken (False, no state, no exhaust_reading).
      Driven through the REAL ExitEngine._momentum_divergence and the REAL ManagementPlan.decide; the clock is pinned
      (exit_engine.now_et per tick; THE WALL CLOCK at 10:05 ET - utils.time_utils.datetime and exit_engine.datetime,
      as tests/check_decay_stop.py pins it - because the lander runs CHECKs after the 15:45 hard close) and
      strategy.plan.write_row is captured.

  S1  AMZN 10-30-like gap DOWN (10-29 closes ~245, a rising open from 233): the r54 rule (copied verbatim) reads
      ROC5 -9.95 then -8.00 on the 09:35 forming bar (base 10-29 15:40); the engine takes NO reading and returns False
  S2  the mirror gap UP (10-29 closes far BELOW, a rising open): the r54 rule reads a large positive ROC5; the engine
      takes no reading
  S3  NFLX 3d320e88 replay (short, 09:44:18 / 09:44:48 on the 09:40 forming bar, base 10-29 15:45): the r54 rule
      DIVERGES on the second tick (+0.23 vs +0.21); the engine returns [False, False] and keeps no state
  S4  the session's 6th bar (09:55): a reading, base_ts today's 09:30, bars_in_session 6, the ROC5 = c(09:55) -
      c(09:30); at 09:50 (5 bars today) still none
  S5  a frame wholly inside today (and one with an untimed index) gives exactly the r54 verdicts and readings
  S6  400 random ticks per direction on frames with 1..14 of today's bars after 12 of yesterday's: the engine equals
      the r54 rule whenever >= 6 rows are today's and is False with no reading otherwise; no reading ever has a
      base_ts on another date than its bar_ts
  M1  management.decide on the NFLX replay: no exhaustion CLOSE and no exhaust_* rows on the cross-session ticks
      (r59 CLOSES on the second)
  M2  decide() on a same-session sequence after 09:55 still CLOSES on the diverging tick, the r55 reason intact
      (the pinned wall clock leaves bar_state unread - utils.time_utils._epoch_s's isinstance meets the pinned class -
      so the reason's bar reads "5m 10:10" without forming/closed; check_exhaust_evidence E6 owns that word)

Born red on 30d4da1 at S1, S2, S3, S4, S5 (its bars_in_session only), S6 and M1; M2 passes there (no change in-session).
Run:  python3 tests/check_exhaust_session.py
"""
import datetime as D
import logging
import os
import random
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_exhaust_session.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)
os.environ.setdefault("OT_INSTRUMENT", "NFLX")
try:
    import pandas as pd                                         # noqa: E402
    import utils.time_utils as _tu                              # noqa: E402
    _REAL_DT = _tu.datetime

    class _Pinned(_REAL_DT):
        @classmethod
        def now(cls, tz=None):
            t = _REAL_DT.now(_tu.ET).replace(hour=10, minute=5, second=0, microsecond=0)
            return t.astimezone(tz) if tz is not None else t.replace(tzinfo=None)
    _tu.datetime = _Pinned
    import config                                               # noqa: E402
    from execution import exit_engine as XE                     # noqa: E402
    import strategy.management as M                             # noqa: E402
    import strategy.plan as PL                                  # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

logging.disable(logging.CRITICAL)
ET = ZoneInfo("America/New_York")
FAILED = []
XE.is_hard_close_time = lambda *a, **k: False
XE.datetime = _Pinned
_orig_now = XE.now_et


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def at(h, m, s=0, day=30):
    return D.datetime(2026, 10, day, h, m, s, tzinfo=ET)


def frame(prior, today):
    """5m frame: `prior` closes on 10-29 ending with the 15:55 bar, then `today` closes from 10-30 09:30."""
    idx = [at(15, 55, day=29) - D.timedelta(minutes=5 * (len(prior) - 1 - i)) for i in range(len(prior))]
    idx += [at(9, 30) + D.timedelta(minutes=5 * i) for i in range(len(today))]
    c = list(prior) + list(today)
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": [100] * len(c)},
                        index=pd.DatetimeIndex(idx))


# ── THE r54 RULE, COPIED VERBATIM FROM 457ee31 execution/exit_engine.py _momentum_divergence (as check_exhaust_evidence) ──
def r54_rule(state, trade_id, underlying, direction, df_5m) -> bool:
    if underlying is None:
        return False
    mom = None
    if df_5m is not None and len(df_5m) >= 6:
        try:
            c = df_5m["close"]
            mom = float(c.iloc[-1] - c.iloc[-6])  # 5-bar ROC
        except Exception:
            mom = None
    if mom is None:
        return False
    st = state.setdefault(trade_id, {"ext": None, "mom": None})
    favorable_new_extreme = (
        st["ext"] is None or
        (direction == "long"  and underlying > st["ext"]) or
        (direction == "short" and underlying < st["ext"])
    )
    diverged = False
    if favorable_new_extreme:
        if st["mom"] is not None:
            if direction == "long":
                diverged = mom < st["mom"] and mom <= 0
            else:
                diverged = mom > st["mom"] and mom >= 0
        st["ext"] = underlying
        st["mom"] = mom
    return diverged


def today_rows(df):
    """Independent of the engine: trailing rows on the last row's ET date."""
    d = [ts.astimezone(ET).date() for ts in df.index]
    k = 0
    for x in reversed(d):
        if x != d[-1]:
            break
        k += 1
    return k


def run(xe, tid, seq, direction):
    out, reads = [], []
    for now, px, df in seq:
        XE.now_et = lambda now=now: now
        try:
            out.append(xe._momentum_divergence(tid, {"trade_id": tid}, px, direction, None, df))
        finally:
            XE.now_et = _orig_now
        rd = getattr(xe, "exhaust_reading", None)
        reads.append(rd(tid) if callable(rd) else None)
    return out, reads


def roc(df):
    c = df["close"]
    return float(c.iloc[-1] - c.iloc[-6])


print("check_exhaust_session (BRK.18)")

# S1 — AMZN 2026-10-30: 10-29 closed ~245-246, 10-30 opened 232.53, 09:30 bar closed 233.25, 09:35 forming rising.
AMZN_PRIOR = [245.60, 245.75, 245.90, 246.00, 245.85, 245.70, 245.80, 245.40, 245.20, 245.55, 245.65, 245.90]
#                                                                               ^ 15:40 (c[-6] on the 09:35 bar)
AMZN = [(at(9, 38, 18), 236.00, frame(AMZN_PRIOR, [233.2488, 235.2472])),
        (at(9, 38, 33), 236.1422, frame(AMZN_PRIOR, [233.2488, 235.2472])),
        (at(9, 38, 48), 237.365, frame(AMZN_PRIOR, [233.2488, 237.195])),
        (at(9, 39, 3), 237.83, frame(AMZN_PRIOR, [233.2488, 237.195]))]
old_roc = [round(roc(df), 4) for _, _, df in AMZN]
old_base = str(AMZN[0][2].index[-6])
xe1 = XE.ExitEngine(paper_trading=True)
o1, r1 = run(xe1, "amzn-067dbb54", AMZN, "long")
check("S1 AMZN gap down: r54 reads ROC5 -9.95 / -8.00 off 10-29 15:40; the engine takes no reading, False",
      old_roc == [-9.9528, -9.9528, -8.005, -8.005] and old_base.startswith("2026-10-29 15:40")
      and o1 == [False] * 4 and r1 == [None] * 4 and xe1._exhaust_state.get("amzn-067dbb54", {}).get("mom") is None,
      f"r54 roc {old_roc} base {old_base}; engine {o1} reads {r1}")

# S2 — the mirror: yesterday far BELOW, a rising open.
UP_PRIOR = [200.0 + 0.05 * i for i in range(12)]
UP = [(at(9, 36, 0), 221.0, frame(UP_PRIOR, [220.0, 221.0])), (at(9, 37, 0), 222.0, frame(UP_PRIOR, [220.0, 222.0]))]
up_roc = [round(roc(df), 2) for _, _, df in UP]
o2, r2 = run(XE.ExitEngine(paper_trading=True), "gapup", UP, "long")
check("S2 gap up: r54 reads ROC5 +20.6 / +21.6 off yesterday; the engine takes no reading",
      up_roc == [20.6, 21.6] and o2 == [False, False] and r2 == [None, None], f"r54 {up_roc}; engine {o2} {r2}")

# S3 — NFLX 3d320e88: short, 09:40 forming, base 10-29 15:45 = 61.70.
NFLX_PRIOR = [61.90, 61.85, 61.80, 61.78, 61.75, 61.72, 61.74, 61.71, 61.69, 61.70, 61.68, 61.66]   # 15:45 = 61.70
NFLX = [(at(9, 44, 18), 62.16, frame(NFLX_PRIOR, [62.315, 61.825, 61.915])),
        (at(9, 44, 48), 62.13, frame(NFLX_PRIOR, [62.315, 61.825, 61.93]))]
st = {}
ref3 = [r54_rule(st, "ref", px, "short", df) for _, px, df in NFLX]
n_roc = [round(roc(df), 3) for _, _, df in NFLX]
xe3 = XE.ExitEngine(paper_trading=True)
o3, r3 = run(xe3, "nflx-3d320e88", NFLX, "short")
check("S3 NFLX 3d320e88: r54 DIVERGES on 09:44:48 (+0.23 vs +0.215 off 10-29 15:45); the engine: False, no state",
      ref3 == [False, True] and n_roc == [0.215, 0.23] and str(NFLX[0][2].index[-6]).startswith("2026-10-29 15:45")
      and o3 == [False, False] and r3 == [None, None] and "nflx-3d320e88" not in xe3._exhaust_state,
      f"r54 {ref3} roc {n_roc}; engine {o3} {r3} state {xe3._exhaust_state.get('nflx-3d320e88')}")

# S4 — the 6th bar of today.
T6 = [62.315, 61.825, 62.12, 62.33, 62.385, 62.445]
xe4 = XE.ExitEngine(paper_trading=True)
o4a, r4a = run(xe4, "s4", [(at(9, 52), 62.40, frame(NFLX_PRIOR, T6[:5]))], "long")
o4b, r4b = run(xe4, "s4", [(at(9, 56), 62.50, frame(NFLX_PRIOR, T6))], "long")
g = r4b[0] or {}
check("S4 09:50 (5 bars today): no reading; 09:55 (6): a reading off today's 09:30, bars_in_session 6",
      o4a == [False] and r4a == [None] and o4b == [False]
      and str(g.get("base_ts", "")).startswith("2026-10-30T09:30") and str(g.get("bar_ts", "")).startswith("2026-10-30T09:55")
      and g.get("bars_in_session") == 6 and abs(g.get("new_roc", 0) - (62.445 - 62.315)) < 1e-9,
      f"{r4a} {g}")

# S5 — wholly-today and untimed frames: exactly r54.
SEQ5 = [(at(10, 12, 10), 409.00, 409.00), (at(10, 12, 25), 408.50, 408.50), (at(10, 12, 40), 408.90, 408.90),
        (at(10, 12, 55), 408.40, 409.50), (at(10, 13, 10), 408.45, 408.45), (at(10, 13, 25), 408.30, 410.20)]
B5 = [411.0, 410.6, 410.4, 410.0, 409.8, 409.6, 409.4, 409.2]
seq_today = [(t, px, frame([], B5 + [c])) for t, px, c in SEQ5]
o5, r5 = run(XE.ExitEngine(paper_trading=True), "s5", seq_today, "short")
st = {}
ref5 = [r54_rule(st, "r", px, "short", df) for _, px, df in seq_today]


def untimed(df):
    return df.reset_index(drop=True)


seq_ut = [(t, px, untimed(df)) for t, px, df in seq_today]
o5u, r5u = run(XE.ExitEngine(paper_trading=True), "s5u", seq_ut, "short")
check("S5 a frame wholly in today, and an untimed one, give exactly the r54 verdicts and a reading on each new low",
      o5 == ref5 == [False, False, False, False, False, True] and o5u == ref5
      and [r is not None for r in r5] == [True, True, False, True, False, True]
      and [r is not None for r in r5u] == [True, True, False, True, False, True]
      and (r5[5] or {}).get("bars_in_session") == 9, f"{o5} {o5u} ref {ref5} {r5[5]}")

# S6 — random.
rng = random.Random(59)
mism, cross, notes = 0, 0, []
for direction in ("long", "short"):
    xe6 = XE.ExitEngine(paper_trading=True)
    st = {}
    px = 100.0
    prior = [100.0 + rng.uniform(-3, 3) for _ in range(12)]
    for i in range(400):
        px += rng.uniform(-0.3, 0.3)
        n_today = 1 + (i // 25) % 14
        today = [px + rng.uniform(-0.6, 0.6) for _ in range(n_today)]
        df = frame(prior, today)
        p = None if i % 97 == 41 else round(px, 2)
        a = xe6._momentum_divergence("rand", {}, p, direction, None, df)
        rd = xe6.exhaust_reading("rand")
        if today_rows(df) >= 6:
            b = r54_rule(st, "rand", p, direction, df)
        else:
            b = False
            if rd is not None:
                cross += 1
        mism += (a != b)
        if rd is not None and str(rd.get("base_ts", ""))[:10] != str(rd.get("bar_ts", ""))[:10]:
            cross += 1
            notes.append(rd)
check("S6 800 random ticks: r54's verdict whenever >= 6 rows are today's, else False and no reading; no reading spans days",
      mism == 0 and cross == 0, f"{mism} mismatches, {cross} cross-session readings {notes[:1]}")

# ── the management path ──────────────────────────────────────────────────────────────────────────────
ROWS = []
_orig_write = PL.write_row


def _capture(store, symbol, ts, strategy, verdict, reason, direction="", trigger=None, invalidation=None,
             underlying=None, r=None, checks=None, check_notes=None):
    ROWS.append({"strategy": strategy, "verdict": verdict, "reason": reason, "checks": dict(checks or {}),
                 "notes": dict(check_notes or {})})
    return True


def rec(tid, direction, und):
    long_ = direction == "long"
    return {"trade_id": tid, "strategy": "Breakout", "symbol": "NFLX", "direction": direction,
            "option_side": "call" if long_ else "put", "entry_premium": 2.0, "stop_premium": 1.0,
            "target_premium": 0.0, "underlying_entry": und,
            "underlying_stop": 0.0, "entry_time": "2026-10-30T13:44:03+00:00", "contracts": 4,
            "option_symbol": "NFLX  261030P00062000", "current_delta": 0.45, "is_butterfly": 0}


def decide_run(xe, r, seq):
    plan = M.get_management_plan()
    out = []
    for now, px, df in seq:
        ROWS.clear()
        XE.now_et = lambda now=now: now
        try:
            it = plan.decide(dict(r), 2.2, df_1m=None, open_records=[r], current_price=px,
                             ctx={"df_5m": df}, exit_engine=xe)
        finally:
            XE.now_et = _orig_now
        mine = [x for x in ROWS if x["strategy"] == "Breakout/manage"]
        out.append((it, mine[-1] if mine else None))
    return out


names = ("exhaust_ext", "exhaust_roc", "exhaust_prior_ext", "exhaust_prior_roc", "exhaust_diverged", "exhaust_bar")
_saved = (config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE)
config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE = "off", "off"
PL.write_row = _capture
try:
    m1 = decide_run(XE.ExitEngine(paper_trading=True), rec("m1-nflx", "short", 62.20), NFLX)
    m2 = decide_run(XE.ExitEngine(paper_trading=True), rec("m2-short", "short", 409.2), seq_today)
finally:
    PL.write_row = _orig_write
    config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE = _saved

ex1 = [bool(it is not None and getattr(it, "condition", None) == "exhaustion") for it, _ in m1]
rows1 = [row is not None and any(n in row["checks"] for n in names) for _, row in m1]
check("M1 decide() on the NFLX replay: no exhaustion CLOSE and no exhaust_* rows on the cross-session ticks",
      ex1 == [False, False] and rows1 == [False, False],
      f"exh {ex1} rows {rows1} {[getattr(it, 'reason', None) for it, _ in m1]}")
ex2 = [bool(it is not None and getattr(it, "condition", None) == "exhaustion") for it, _ in m2]
rs = getattr(m2[5][0], "reason", "") or ""
check("M2 decide() on a same-session sequence still CLOSES on the diverging tick, the r55 reason intact",
      ex2 == [False, False, False, False, False, True]
      and rs.startswith("exhaustion: new short extreme 408.30 (ROC5 +0.20, 5m 10:10") and " vs prior 408.40 (ROC5 -0.50) on " in rs
      and rs.endswith("on weaker momentum — continuing on fumes pnl=10.0%"), f"{ex2} {rs!r}")

print("RESULT:", "FAIL " + ",".join(FAILED) if FAILED else "PASS")
sys.exit(1 if FAILED else 0)
