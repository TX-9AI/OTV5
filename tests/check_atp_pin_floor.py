#!/usr/bin/env python3
"""
tests/check_atp_pin_floor.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.2  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject ATPButterfly is DORMANT by default and a dormant plan now
      writes nothing by ruling, so this run switches it ACTIVE (OT_ATP_BUTTERFLY=1); what it pins is unchanged.
v1.1  2026-10-12  OTV4TEST r273 (BFLY.10) — A9 RE-POINTED: ATPButterfly 13:00-15:00, refused at 12:45, admitted at 13:00. r273 (BFLY.10), by ruling - the operator, 2026-10-12: "reduce the fly window to 1300".

The ATP butterfly qualifies on ROUTE A (PINNING and its OWN concentration floor,
0.15) or, only when A fails, ROUTE B (NOT TRENDING and the pin within ±0.05 x EM
of today's VWAP); the pin (travel) butterfly keeps 0.25; nothing else changes.

v1.0  2026-09-30  OTV4TEST r179 (BFLY.9). The operator, 2026-09-30: "The ATP fly
      should be accepting the plan for the EXACT reason GEX pin fly is declining
      (price too close to pin)", then "Drop the ATP to .19" and "Actually .15 sounds better". That day the ATP
      plan held a PREPARED 743/745/747 fly for 148 ticks waiting only on
      concentration (0.18-0.20 against the shared 0.25).

WHAT IT DRIVES (WA 21): the REAL ATPButterflyStrategy.generate_signal over the
REAL plan, on the 2026-09-11 12:28 chain check_atp_butterfly uses (its own
fixture, quotes from that day's tape), and the REAL gex_pin_butterfly
.pin_strength (for the pin fly, which still uses it). VWAP comes from a stub of
derived.anchors.vwap_now, the one reader the plan calls. The plan store is in memory; main is never imported, so nothing
is logged to the live bot.log.

  A1  concentration 0.15, no VWAP -> TAKE
  A2  concentration 0.20 (the 09-30 reading) -> TAKE
  A3  concentration 0.14, no VWAP -> HOLD on pin_concentration, and the row
      names route A's 0.15 floor
  A4  concentration 0.26 -> TAKE the same 713/715/717 put fly at 0.56 as before
  A5  the floor removes nothing else: TRENDING still holds on pinning, an
      unsettled tape still holds on settled, 2.00 off the pin still holds on at_pin
  A6  the pin fly's pin_strength (no floor passed) is unchanged: 0.20 is NOT
      strong and names 0.25; 0.25 is strong
  A7  the two floors are the declared ones: config.ATP_BFLY_PIN_CONC_MIN 0.15,
      the pin fly's PIN_CONC_MIN 0.25
  A8  the ATP plan declares PIN_CONC_MIN FOUNDATIONAL (WA 36)
  A9  the entry-window table says what the plan does: ATPButterfly 13:00-15:00,
      refused on its window at 12:45 and admitted at 13:00 (r273; was 12:00)
  B1  NEUTRAL, concentration 0.10, the pin 0.20 from VWAP (inside ±0.26 = 0.05x
      EM 5.21) -> TAKE on route B, and the row says route B
  B2  NEUTRAL, the pin 0.40 from VWAP (outside ±0.26; inside the old 0.10x band)
      -> HOLD on pin_concentration
  B3  TRENDING, the pin exactly on VWAP -> HOLD on pinning (never trending)
  B4  NEUTRAL with no VWAP -> HOLD, and the row says there was no VWAP (fails closed)
  B5  an UNKNOWN regime, the pin on VWAP -> HOLD on pinning (fails closed)
  B6  PINNING at 0.26 with the pin FAR from VWAP -> TAKE on route A (route B is
      only asked when A fails, and A does not need VWAP)

BORN RED on 59ba004 (r178) under both interpreters: see the ledger row for the
exact list, which is quoted from the run.

Run:  python3 tests/check_atp_pin_floor.py
"""
from __future__ import annotations

import glob as _glob
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# A worktree has no venv of its own, so the box's install is the fallback.
for _base in (ROOT, os.path.expanduser("~/options-trader")):
    _found = _glob.glob(os.path.join(_base, "venv", "lib", "python*", "site-packages"))
    for _sp in _found:
        if _sp not in sys.path:
            sys.path.insert(1, _sp)
    if _found:
        break
sys.path.insert(0, ROOT)
os.environ["OT_ATP_BUTTERFLY"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ["OT_RELAXED_ENTRY"] = "0"

FAIL = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(label.split()[0])


def guard(label, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        print(f"  FAIL  {label}  [raised {type(exc).__name__}: {exc}]")
        FAIL.append(label.split()[0])
        return
    check(label, ok, detail())


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def commit(self):
        self.conn.commit()


class _C:
    def __init__(self, k, bid, ask, side):
        self.strike, self.bid, self.ask = float(k), float(bid), float(ask)
        self.mark = (bid + ask) / 2
        self.delta, self.gamma, self.theta = 0.3, 0.02, -0.05
        self.expiry, self.open_interest = "2026-09-11", 500
        self.symbol = f".QQQ260911{side}{k}"


# Friday 2026-09-11 12:28 ET, quote_series (check_atp_butterfly's fixture).
_PUTS = {711: (0.09, 0.10), 712: (0.13, 0.14), 713: (0.20, 0.21), 714: (0.32, 0.33),
         715: (0.54, 0.55), 716: (0.89, 0.90), 717: (1.44, 1.45), 718: (2.16, 2.21),
         719: (3.02, 3.16)}
_CALLS = {711: (4.94, 5.15), 712: (3.99, 4.22), 713: (3.18, 3.29), 714: (2.36, 2.40),
          715: (1.58, 1.59), 716: (0.94, 0.95), 717: (0.49, 0.50), 718: (0.22, 0.23),
          719: (0.10, 0.11)}


class _Chain:
    def __init__(self):
        self.puts = [_C(k, b, a, "P") for k, (b, a) in _PUTS.items()]
        self.calls = [_C(k, b, a, "C") for k, (b, a) in _CALLS.items()]


class _GEX:
    def __init__(self, env="PINNING", pin=715.0, conc=0.26):
        self.gex_environment, self.pin_strike, self.pin_concentration = env, pin, conc


class _Tick:
    """What pin_strength records on; nothing here is asserted on."""
    def check(self, *a, **k):
        pass

    def note(self, *a, **k):
        pass


import pandas as pd                                             # noqa: E402
import config                                                   # noqa: E402
from strategy import plan as P                                  # noqa: E402
import strategy.gex_pin_butterfly as gpb                        # noqa: E402
import strategy.atp_butterfly_plan as ap                        # noqa: E402
from strategy.atp_butterfly import ATPButterflyStrategy         # noqa: E402
from derived import anchors as A                                # noqa: E402

st = _Store()
P.bind_store(st)
ap.ENABLED = True
gpb.EARLIEST_ET, gpb.LATEST_ET = "12:00", "15:00"
gpb.expected_move = lambda u, iv, now=None: 5.21     # Friday's 12:28 value
A._store = lambda: None                              # no VWAP: the waiver cannot mask a case


def bars(closes):
    return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes},
                        index=pd.date_range("2026-09-11 12:00", periods=len(closes),
                                            freq="1min", tz="America/New_York"))


settled = bars([715.2, 715.6, 716.1, 715.8, 715.4, 714.9, 715.3, 715.7, 716.2, 716.4,
                715.9, 715.5, 715.1, 715.6, 716.0, 716.0, 716.01])
ts = [100.0]


def run(**kw):
    S = ATPButterflyStrategy()
    S.planner.symbol = "TST"
    ts[0] += 1.0
    P.begin_tick(ts[0])
    args = dict(now_et="12:28", atm_iv=0.20, gex=_GEX(), chain=_Chain(), price_now=716.01,
                df_1m=settled)
    args.update(kw)
    sig = S.generate_signal(**args)
    row = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='ATPButterfly' "
                          "AND ts_epoch=?", (ts[0],)).fetchone()
    return sig, (row or ("", ""))


_R = {}


def _take(key, conc):
    _R[key] = run(gex=_GEX(conc=conc))
    sig, row = _R[key]
    return sig is not None and row[0] == "TAKE"


def _d(key):
    return lambda: "%s: %s" % (_R[key][1][0], _R[key][1][1][-150:]) if key in _R else ""


guard("A1 concentration 0.15, no VWAP -> TAKE", lambda: _take("a1", 0.15), _d("a1"))
guard("A2 concentration 0.20 (the 09-30 reading) -> TAKE", lambda: _take("a2", 0.20), _d("a2"))


def _a3():
    _R["a3"] = run(gex=_GEX(conc=0.14))
    sig, row = _R["a3"]
    return (sig is None and row[0] == "HOLD" and "pin_concentration=0.14" in row[1]
            and "route A: PINNING and conc >= 0.15" in row[1])


guard("A3 concentration 0.14, no VWAP -> HOLD on pin_concentration, route A's 0.15 floor named",
      _a3, _d("a3"))


def _a4():
    _R["a4"] = run(gex=_GEX(conc=0.26))
    sig, row = _R["a4"]
    return (sig is not None and row[0] == "TAKE" and "buy 713/715/717 put fly" in row[1]
            and "debit 0.56" in row[1])


guard("A4 concentration 0.26 -> TAKE the same 713/715/717 put fly at 0.56 as before", _a4,
      _d("a4"))


def _a5():
    a = run(gex=_GEX(env="TRENDING", conc=0.15))
    b = run(gex=_GEX(conc=0.15), df_1m=bars([719.0] * 10 + [715.5] * 6 + [716.01]))
    c = run(gex=_GEX(conc=0.15), price_now=717.0, df_1m=bars([717.0] * 17))
    _R["a5"] = (None, ("", " | ".join(x[1][0] + ":" + x[1][1][-60:] for x in (a, b, c))))
    return (a[0] is None and "pinning=" in a[1][1] and b[0] is None and "settled=" in b[1][1]
            and c[0] is None and "at_pin=" in c[1][1])


guard("A5 at 0.15 the other conditions still bind: TRENDING, an unsettled tape, 2.00 off the pin",
      _a5, _d("a5"))


def _a6():
    lo = gpb.pin_strength(_Tick(), 715.0, 0.20, 5.21)
    hi = gpb.pin_strength(_Tick(), 715.0, 0.25, 5.21)
    _R["a6"] = (None, ("", "0.20 -> %s need '%s' | 0.25 -> %s" % (lo[0], lo[1][:12], hi[0])))
    return lo[0] is False and lo[1].startswith(">= 0.25") and hi[0] is True


guard("A6 the pin fly's pin_strength is unchanged: 0.20 is not strong (needs 0.25), 0.25 is",
      _a6, _d("a6"))

check("A7 the declared floors: config.ATP_BFLY_PIN_CONC_MIN 0.15, the pin fly's PIN_CONC_MIN 0.25",
      abs(float(getattr(config, "ATP_BFLY_PIN_CONC_MIN", -1)) - 0.15) < 1e-9
      and abs(float(gpb.PIN_CONC_MIN) - 0.25) < 1e-9
      and abs(float(getattr(ap, "PIN_CONC_MIN", -1)) - 0.15) < 1e-9,
      "config=%s pin fly=%s atp=%s" % (getattr(config, "ATP_BFLY_PIN_CONC_MIN", None),
                                       gpb.PIN_CONC_MIN, getattr(ap, "PIN_CONC_MIN", None)))
check("A8 the ATP plan declares PIN_CONC_MIN and VWAP_STRICT_EM_FRAC FOUNDATIONAL, route B at 0.05",
      ap.GATES.get("PIN_CONC_MIN") == "FOUNDATIONAL"
      and ap.GATES.get("VWAP_STRICT_EM_FRAC") == "FOUNDATIONAL"
      and abs(float(getattr(config, "ATP_BFLY_VWAP_STRICT_EM_FRAC", -1)) - 0.05) < 1e-9,
      str(ap.GATES))

# ── route B: a stubbed VWAP through the one reader the plan calls ────────────
_real_vwap = A.vwap_now


def _with_vwap(v, **kw):
    A.vwap_now = (lambda *a, **k: (v, "fixture")) if v is not None else \
        (lambda *a, **k: (None, "no VWAP row (fixture)"))
    try:
        return run(**kw)
    finally:
        A.vwap_now = _real_vwap


def _b(key, v, expect, **kw):
    _R[key] = _with_vwap(v, **kw)
    sig, row = _R[key]
    return expect(sig, row)


guard("B1 NEUTRAL, conc 0.10, the pin 0.20 from VWAP (inside ±0.26) -> TAKE on route B",
      lambda: _b("b1", 715.20, lambda s, r: s is not None and r[0] == "TAKE" and "route B" in r[1],
                 gex=_GEX(env="NEUTRAL", conc=0.10)), _d("b1"))
guard("B2 NEUTRAL, the pin 0.40 from VWAP (outside ±0.26, inside the old 0.10x) -> HOLD on pin_concentration",
      lambda: _b("b2", 715.40, lambda s, r: s is None and r[0] == "HOLD" and "pin_concentration=" in r[1]
                 and "(now 0.40 off)" in r[1], gex=_GEX(env="NEUTRAL", conc=0.10)), _d("b2"))
guard("B3 TRENDING, the pin exactly on VWAP -> HOLD on pinning",
      lambda: _b("b3", 715.0, lambda s, r: s is None and r[0] == "HOLD" and "pinning=" in r[1],
                 gex=_GEX(env="TRENDING", conc=0.10)), _d("b3"))
guard("B4 NEUTRAL with no VWAP -> HOLD, and the row says there was no VWAP (fails closed)",
      lambda: _b("b4", None, lambda s, r: s is None and r[0] == "HOLD" and "no VWAP" in r[1],
                 gex=_GEX(env="NEUTRAL", conc=0.10)), _d("b4"))
guard("B5 an UNKNOWN regime, the pin on VWAP -> HOLD on pinning (fails closed)",
      lambda: _b("b5", 715.0, lambda s, r: s is None and r[0] == "HOLD" and "pinning=" in r[1],
                 gex=_GEX(env="", conc=0.30)), _d("b5"))
guard("B6 PINNING at 0.26, the pin FAR from VWAP -> TAKE on route A",
      lambda: _b("b6", 700.0, lambda s, r: s is not None and r[0] == "TAKE" and "route A" in r[1],
                 gex=_GEX(conc=0.26)), _d("b6"))

from execution import position_manager as PMOD                  # noqa: E402
_w = config.ENTRY_WINDOWS.get("ATPButterfly")
_f = lambda hm: PMOD.decide(PMOD.Facts(strategy="ATPButterfly", now_et=hm, trading_day=True,   # noqa: E731
                                       orb_established=True, cap_intact=True))
check("A9 the window table matches the plan: ATPButterfly 13:00-15:00 (12:45 refused on window, 13:00 admitted)",
      _w == ((13, 0), (15, 0)) and _f((12, 45)).gate == "window" and _f((13, 0)).admitted,
      "table=%s 12:45=%s 13:00=%s" % (_w, _f((12, 45)).gate, _f((13, 0)).admitted))

print()
if FAIL:
    print(f"RED — {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN — ATP route A at 0.15, route B on a strict VWAP only when A fails; the pin fly unchanged")
sys.exit(0)
