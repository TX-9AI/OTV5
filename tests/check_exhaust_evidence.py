#!/usr/bin/env python3
"""
tests/check_exhaust_evidence.py  v5.1
v5.1  2026-10-31  OTV5 r68 (CFG.5) — OT_RESTING_STOP_STATE leaves the scratch env: the resting stop and its state file are deleted
      (the operator, 2026-10-31: "Resting stop was a study. It failed. Get this the fuck out of here"). No check changed.
v5.0  2026-10-30  OTV5 r55 (BRK.17) — THE EXHAUSTION EXIT'S EVIDENCE IS WRITTEN; NO DECISION CHANGES.
      UNH 2026-10-29 took three Breakout exhaustion exits (10534a1a 09:42 ET +$200, 4f01b80a 10:01 +$144,
      449040f2 10:05 -$4.50, the last 60 s after entry) whose reason read only "exhaustion: new short extreme on
      weaker momentum — continuing on fumes pnl=16.1%": the extremes and the 5-bar 5m ROCs behind it lived in
      exit_engine._exhaust_state and nowhere else. The operator, 2026-10-29: "The momentum values behind that exit
      aren't logged. -damn it, why?" ... "Yes, build it."
      Driven through the REAL ExitEngine._momentum_divergence and the REAL ManagementPlan.decide; only the clock
      (exit_engine.now_et) is pinned and strategy.plan.write_row is captured (the rows it would write).

  E1  short: the engine's verdicts on a 6-tick sequence equal the r54 rule's (copied verbatim below) and the
      recorded [F, F, F, F, F, T]
  E2  long: the mirror sequence, same proof
  E3  400 random ticks per direction (seeded): the engine's verdict equals the r54 rule's on every tick
  E4  a reading is stored on every NEW favourable extreme (and only then): prior/new extreme, prior/new ROC5,
      the comparison, the 5m bar the ROC's close was read from and whether it was forming
  E5  a frame shorter than 6 bars or no price: False, and no reading (as before: no reading at all)
  E6  the 5m bar is "closed" when the clock is past its end, "forming" inside it
  M1  management: decide() on the short sequence CLOSES only on the diverging tick, condition "exhaustion"
  M2  that CLOSE reason keeps "exhaustion: new short extreme" / "on weaker momentum — continuing on fumes pnl=" and
      carries both extremes and both ROC5s
  M3  a plan check row set (exhaust_ext / _roc / _prior_ext / _prior_roc / _diverged / _bar) is written on each new
      extreme tick and on no other; exhaust_roc's note carries the comparison
  M4  the long mirror through decide(): CLOSE on the diverging tick with both extremes and ROCs
  M5  an engine without exhaust_reading (r54's) gives the r54 reason exactly - the reader is optional

Born red on 457ee31 at E4, E5b, E6, M2, M3 and M4.
Run:  python3 tests/check_exhaust_evidence.py
"""
import datetime as D
import os
import random
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_exhaust_evidence.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)
os.environ.setdefault("OT_INSTRUMENT", "UNH")
try:
    import pandas as pd                                         # noqa: E402
    import config                                               # noqa: E402
    from execution import exit_engine as XE                     # noqa: E402
    import strategy.management as M                             # noqa: E402
    import strategy.plan as PL                                  # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def at(h, m, s=0):
    return D.datetime(2026, 10, 29, h, m, s, tzinfo=ET)


def frame(closes, last_start=at(9, 40)):
    """5m frame: the LAST row starts at last_start (the forming bar at a clock inside it)."""
    n = len(closes)
    idx = pd.DatetimeIndex([last_start - D.timedelta(minutes=5 * (n - 1 - i)) for i in range(n)])
    return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes,
                         "volume": [100] * n}, index=idx)


# ── THE r54 RULE, COPIED VERBATIM FROM 457ee31 execution/exit_engine.py _momentum_divergence ──────────
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


BASE5 = [410.0, 409.8, 409.6, 409.4, 409.2]       # c[-6] = 410.00 for every tick below
# (clock, price, forming 5m close) -> ROC5 = forming close - 410.00
SHORT = [(at(9, 40, 18), 409.00, 409.00),         # first extreme, ROC5 -1.00 (no prior)
         (at(9, 40, 33), 408.50, 408.50),         # new low, ROC5 -1.50: stronger - confirmed
         (at(9, 40, 48), 408.90, 408.90),         # not a new low: no comparison
         (at(9, 41, 3), 408.40, 409.50),          # new low, ROC5 -0.50: weaker but < 0 - no divergence
         (at(9, 41, 18), 408.45, 408.45),         # not a new low
         (at(9, 41, 33), 408.30, 410.20)]         # new low, ROC5 +0.20: weaker and >= 0 - DIVERGED
SHORT_WANT = [False, False, False, False, False, True]
SHORT_NEW = [True, True, False, True, False, True]
BASE5L = [100.0, 100.2, 100.4, 100.6, 100.8]
LONG = [(at(9, 40, 18), 101.00, 101.00), (at(9, 40, 33), 101.50, 101.50), (at(9, 40, 48), 101.20, 101.20),
        (at(9, 41, 3), 101.60, 100.50), (at(9, 41, 18), 101.55, 101.55), (at(9, 41, 33), 101.70, 99.80)]
LONG_WANT = [False, False, False, False, False, True]

_orig_now = XE.now_et


def engine_run(xe, tid, seq, base, direction):
    out, reads = [], []
    for now, px, c5 in seq:
        XE.now_et = lambda now=now: now
        try:
            out.append(xe._momentum_divergence(tid, {"trade_id": tid}, px, direction, None, frame(base + [c5])))
        finally:
            XE.now_et = _orig_now
        rd = getattr(xe, "exhaust_reading", None)
        reads.append(rd(tid) if callable(rd) else None)
    return out, reads


def ref_run(seq, base, direction):
    st = {}
    return [r54_rule(st, "ref", px, direction, frame(base + [c5])) for _, px, c5 in seq]


print("check_exhaust_evidence (BRK.17)")
xe = XE.ExitEngine(paper_trading=True)

s_out, s_reads = engine_run(xe, "e1-short", SHORT, BASE5, "short")
check("E1 short: the engine's verdicts equal the r54 rule's and the recorded sequence",
      s_out == ref_run(SHORT, BASE5, "short") == SHORT_WANT, f"engine {s_out} ref {ref_run(SHORT, BASE5, 'short')}")
l_out, l_reads = engine_run(xe, "e2-long", LONG, BASE5L, "long")
check("E2 long: the engine's verdicts equal the r54 rule's and the recorded sequence",
      l_out == ref_run(LONG, BASE5L, "long") == LONG_WANT, f"engine {l_out} ref {ref_run(LONG, BASE5L, 'long')}")

rng = random.Random(55)
mism = 0
for direction in ("short", "long"):
    st = {}
    px, closes = 100.0, [100.0 + rng.uniform(-1, 1) for _ in range(5)]
    for i in range(400):
        px += rng.uniform(-0.3, 0.3)
        closes = closes[1:] + [px + rng.uniform(-0.2, 0.2)] if i % 7 == 0 else closes
        c5 = px + rng.uniform(-0.4, 0.4)
        df = frame(closes + [c5]) if i % 50 != 13 else frame([c5] * 3)   # now and then a short frame
        p = None if i % 97 == 41 else round(px, 2)
        a = xe._momentum_divergence("rand-" + direction, {}, p, direction, None, df)
        b = r54_rule(st, "rand", p, direction, df)
        mism += (a != b)
check("E3 400 random ticks per direction: the engine's verdict equals the r54 rule's on every one",
      mism == 0, f"{mism} mismatches")

new_ok = [(r is not None) == want for r, want in zip(s_reads, SHORT_NEW)]
r6 = s_reads[5] or {}
r4 = s_reads[3] or {}
check("E4 short: a reading on every new low (and only then), with both extremes, both ROC5s and the comparison",
      all(new_ok) and s_reads[0] is not None and s_reads[0]["prior_ext"] is None and s_reads[0]["prior_roc"] is None
      and abs(r6.get("new_ext", 0) - 408.30) < 1e-9 and abs(r6.get("new_roc", 0) - 0.20) < 1e-9
      and abs(r6.get("prior_ext", 0) - 408.40) < 1e-9 and abs(r6.get("prior_roc", 0) + 0.50) < 1e-9
      and r6.get("diverged") is True and r4.get("diverged") is False
      and r6.get("bar_ts", "").startswith("2026-10-29T09:40") and r6.get("bar_state") == "forming"
      and r6.get("base_ts", "").startswith("2026-10-29T09:15"),
      f"new={new_ok} last={r6}")

xe5 = XE.ExitEngine(paper_trading=True)
a5 = xe5._momentum_divergence("e5", {}, 409.0, "short", None, frame([410.0, 409.0, 408.0]))
b5 = xe5._momentum_divergence("e5", {}, None, "short", None, frame(BASE5 + [409.0]))
rd5 = getattr(xe5, "exhaust_reading", None)
check("E5a a frame of 3 bars / no price: False, as before", a5 is False and b5 is False)
check("E5b ... and no reading is stored (exhaust_reading exists and answers None)",
      callable(rd5) and rd5("e5") is None, f"{rd5('e5') if callable(rd5) else 'no exhaust_reading'}")

xe6 = XE.ExitEngine(paper_trading=True)
XE.now_et = lambda: at(9, 46, 3)                  # past the 09:40 bar's end: a stale frame, its row closed
try:
    xe6._momentum_divergence("e6", {}, 409.0, "short", None, frame(BASE5 + [409.0]))
finally:
    XE.now_et = _orig_now
r6c = (xe6.exhaust_reading("e6") if hasattr(xe6, "exhaust_reading") else None) or {}
check("E6 the 5m bar reads 'closed' past its end and 'forming' inside it",
      r6c.get("bar_state") == "closed" and (s_reads[0] or {}).get("bar_state") == "forming", f"{r6c}")

# ── the management path ──────────────────────────────────────────────────────────────────────────────
ROWS = []
_orig_write = PL.write_row


def _capture(store, symbol, ts, strategy, verdict, reason, direction="", trigger=None, invalidation=None,
             underlying=None, r=None, checks=None, check_notes=None):
    ROWS.append({"strategy": strategy, "verdict": verdict, "reason": reason, "checks": dict(checks or {}),
                 "notes": dict(check_notes or {})})
    return True


def rec(tid, direction):
    long_ = direction == "long"
    return {"trade_id": tid, "strategy": "Breakout", "symbol": "UNH", "direction": direction,
            "option_side": "call" if long_ else "put", "entry_premium": 2.0, "stop_premium": 1.0,
            "target_premium": 0.0, "underlying_entry": 101.0 if long_ else 409.2,
            "underlying_stop": 0.0, "entry_time": "2026-10-29T13:40:04+00:00", "contracts": 4,
            "option_symbol": "UNH   261030P00407500", "current_delta": 0.45, "is_butterfly": 0}


def decide_run(xe, r, seq, base):
    plan = M.get_management_plan()
    out = []
    for now, px, c5 in seq:
        ROWS.clear()
        XE.now_et = lambda now=now: now
        try:
            it = plan.decide(dict(r), 2.2, df_1m=None, open_records=[r], current_price=px,
                             ctx={"df_5m": frame(base + [c5])}, exit_engine=xe)
        finally:
            XE.now_et = _orig_now
        mine = [x for x in ROWS if x["strategy"] == "Breakout/manage"]
        out.append((it, mine[-1] if mine else None))
    return out


_saved = (config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE)
config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE = "off", "off"
PL.write_row = _capture
try:
    xm = XE.ExitEngine(paper_trading=True)
    ms = decide_run(xm, rec("m1-short", "short"), SHORT, BASE5)
    ml = decide_run(xm, rec("m4-long", "long"), LONG, BASE5L)

    class R54Engine(XE.ExitEngine):            # r54's engine surface: no exhaust_reading
        exhaust_reading = None
    m5 = decide_run(R54Engine(paper_trading=True), rec("m5-short", "short"), SHORT, BASE5)
finally:
    PL.write_row = _orig_write
    config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE = _saved

exh = [bool(it is not None and it.action == "CLOSE" and it.condition == "exhaustion") for it, _ in ms]
check("M1 decide() on the short sequence CLOSES on exhaustion on the diverging tick only",
      exh == SHORT_WANT, f"{exh} {[getattr(it, 'reason', None) for it, _ in ms]}")
rs = getattr(ms[5][0], "reason", "") or ""
check("M2 the CLOSE reason keeps its prefix and tail and carries both extremes and both ROC5s",
      rs.startswith("exhaustion: new short extreme 408.30 (ROC5 +0.20, 5m 09:40 forming) vs prior 408.40 (ROC5 -0.50)")
      and rs.endswith("on weaker momentum — continuing on fumes pnl=10.0%")
      and rs.split(" pnl=")[0].split(":")[0] == "exhaustion", repr(rs))
names = ("exhaust_ext", "exhaust_roc", "exhaust_prior_ext", "exhaust_prior_roc", "exhaust_diverged", "exhaust_bar")
has = [row is not None and all(n in row["checks"] for n in names) for _, row in ms]
none_ = [row is not None and not any(n in row["checks"] for n in names) for _, row in ms]
last = ms[5][1] or {"checks": {}, "notes": {}}
c = last["checks"]
ok3 = (all(h for h, w in zip(has, SHORT_NEW) if w) and all(n for n, w in zip(none_, SHORT_NEW) if not w)
       and c.get("exhaust_ext", (None,))[0] == 408.30 and abs(c.get("exhaust_roc", (0,))[0] - 0.20) < 1e-9
       and c.get("exhaust_prior_ext", (None,))[0] == 408.40 and abs(c.get("exhaust_prior_roc", (0,))[0] + 0.50) < 1e-9
       and c.get("exhaust_diverged", (None,))[0] == 1.0
       and str(c.get("exhaust_bar", ("",))[0]).startswith("2026-10-29T09:40:00-04:00 forming")
       and "DIVERGED" in last["notes"].get("exhaust_roc", "")
       and (ms[0][1] or {"checks": {}})["checks"].get("exhaust_prior_roc", (1,))[0] is None
       and (ms[3][1] or {"checks": {}})["checks"].get("exhaust_diverged", (None,))[0] == 0.0)
check("M3 a check row set on each new-extreme tick and on no other; the values and note carry the comparison",
      ok3, f"has={has} none={none_} last={c} notes={last['notes'].get('exhaust_roc')}")
rl = getattr(ml[5][0], "reason", "") or ""
check("M4 long through decide(): CLOSE on the diverging tick with both extremes and ROC5s",
      [bool(it is not None and it.condition == "exhaustion") for it, _ in ml] == LONG_WANT
      and rl.startswith("exhaustion: new long extreme 101.70 (ROC5 -0.20, 5m 09:40 forming) vs prior 101.60 (ROC5 +0.50)"),
      repr(rl))
r5 = getattr(m5[5][0], "reason", "") or ""
check("M5 an engine without exhaust_reading: the same decision and the r54 reason exactly",
      [bool(it is not None and it.condition == "exhaustion") for it, _ in m5] == SHORT_WANT
      and r5 == "exhaustion: new short extreme on weaker momentum — continuing on fumes pnl=10.0%", repr(r5))

print("RESULT:", "FAIL " + ",".join(FAILED) if FAILED else "PASS")
sys.exit(1 if FAILED else 0)
