#!/usr/bin/env python3
"""
tests/check_gex_from_chains.py  v5.0
v5.0  2026-10-25  (GEX.2 + GEX.3) — new in OTV5: PORTED VERBATIM FROM MAINLINE otv4 v2.0 (otv4 r391 + r395) with the tool
      it gates. It drives tests/gex_from_chains.py: an empty load must REFUSE non-zero by name before any conclusion, the
      warehouse lookup is keyed (date, symbol) and an absent session returns (None, reason), and a warehouse record reaches
      production's own compute_gex with gamma/OI/strike/mark intact. Born red on ffe10bf: G1, G1b and G2 FAIL (the v1.0
      tool has no run() and a no-argument snapshots()), then G2b's call snapshots(date, symbol) raises TypeError and the
      checker exits non-zero before G3-G6 (v1.0 has no adapter and never reaches compute_gex).

  G1   an absent/empty load REFUSES BY NAME and exits NON-ZERO (a crash is caught and named, not a verdict)
  G1b  the refusal names whose gap it is (the tool's, not the tape's)
  G2   snapshots() is keyed on (date, symbol) — a warehouse lookup, not a machine-local glob
  G2b  an absent symbol-session returns (None, reason), never a bare [] (reads the warehouse, or names why it cannot)
  G3   chain_from_snapshot splits calls/puts and carries spot
  G3b  the four fields compute_gex reads (gamma, open_interest, strike, mark) survive intact
  G3c  production's compute_gex runs on the adapted chain and returns its own labels (orb_bias)
  G3d  --proxy-exposure is reported BY MONEYNESS BAND, never as one number
  G4   the conclusion block is UNREACHABLE on an empty set
  G5   a negative conclusion carries the n it rests on ("LOADED SNAPSHOT")
  G6   the report says production's orb_bias is computed and READ BY NO strategy (true here: ORB is retired)
  G6b  the report names compute_gex as the source of its numbers

otv4 v2.0  2026-09-20  r395 / GEX.2 — REWRITTEN FOR THE ADAPTER (that file's history; its ids are otv4's).
otv4 v1.0  2026-09-19  r391 / GEX.1 — THE INSTRUMENT THE GAMMA HYPOTHESIS WOULD HAVE LEANED ON WAS RETURNING CONFIDENT
      NOTHING.
"""
import io
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import gex_from_chains as g

FAILS, RAN = [], []


def ck(n, ok, msg):
    RAN.append(n)
    print(f"  {n:<4} {'PASS' if ok else 'FAIL'}  {msg}")
    if not ok:
        FAILS.append(n)


# ---------------------------------------------------------------- G1 / G4 / G2
_saved = g.snapshots
try:
    g.snapshots = lambda d, s: (None, "no chain_snapshots for X on Y — this is "
                                      "the TOOL's gap, not the tape's (r39)")
    # ⚠️ A CRASH IS NOT A CLEAN RED AND MUST NOT BE REPORTED AS ONE. Removing
    # the refusal makes `run()` reach `len(None)` and raise, which killed this
    # checker outright and printed no verdict at all — a gate that dies tells
    # you less than one that fails. The exception is caught and NAMED instead.
    buf = io.StringIO()
    rc, exc = None, None
    try:
        with contextlib.redirect_stdout(buf):
            rc = g.run("2026-01-01", "NOPE")
    except Exception as e:                                       # noqa: BLE001
        exc = f"{type(e).__name__}: {e}"
    out = buf.getvalue()
    ck("G1", exc is None and rc == 1 and "REFUSED" in out,
       f"an empty load REFUSES and exits non-zero (rc={rc}"
       + (f", RAISED {exc}" if exc else "") + ")")
    ck("G4", "REAL answer" not in out and "NO GAMMA FLIP" not in out,
       "the conclusion block is UNREACHABLE on an empty set — v1.0 fell "
       "straight through it and declared the nothing a result")
    ck("G1b", "not the tape's" in out or "absence" in out,
       "the refusal NAMES whose gap it is (r39)")
finally:
    g.snapshots = _saved

# ⚠️ BEHAVIOUR, NOT SOURCE TEXT (§21). The first cut of this check grepped the
# file for "/home/claude/cc" and FAILED — because the v2.0 changelog documents
# that path as the defect. A gate satisfied or broken by PROSE is asserting
# about the comment, not the code; the same shape defeated two NEG assertions
# in r390's own land.spec hours earlier.
import inspect
_sig = list(inspect.signature(g.snapshots).parameters)
ck("G2", _sig[:2] == ["date", "symbol"],
   f"snapshots() is keyed on (date, symbol) — a warehouse lookup, not a "
   f"machine-local glob: {_sig}")

_res = g.snapshots("1970-01-01", "NOSUCHSYM")
ck("G2b", isinstance(_res, tuple) and _res[0] is None and _res[1],
   f"an absent symbol-session returns (None, reason) and NEVER a bare [] — "
   f"'nothing was there' and 'nothing came back' cannot be the same value: "
   f"{str(_res)[:70]}")

# ------------------------------------------------------------------------- G3
# 🔑 G3 PINS THE ADAPTER. What must be guarded is that a warehouse record
# reaches production's own compute_gex with its four load-bearing fields
# intact — gamma, open_interest, strike, mark are the only ones it reads.
snap = {"event": "chain_snapshot", "ts_et": "2026-09-18T10:00:00-04:00",
        "expiry": "2026-09-18", "symbol": "T", "underlying": "100.0",
        "contracts": [
            {"occ": "T 260918C00095000", "type": "C", "strike": 95.0,
             "gamma": 0.05, "oi": 1000, "mark": 6.0, "bid": 5.9, "ask": 6.1,
             "delta": 0.8, "theta": -0.1, "vega": 0.2, "iv": 0.4, "vol": 0},
            {"occ": "T 260918P00105000", "type": "P", "strike": 105.0,
             "gamma": 0.09, "oi": 9000, "mark": 6.5, "bid": 6.4, "ask": 6.6,
             "delta": -0.8, "theta": -0.1, "vega": 0.2, "iv": 0.4, "vol": 0}]}
chain, spot = g.chain_from_snapshot(snap)
ck("G3", spot == 100.0 and len(chain.calls) == 1 and len(chain.puts) == 1,
   f"the adapter splits calls/puts and carries spot: {len(chain.calls)}C/"
   f"{len(chain.puts)}P spot={spot}")

c0 = chain.calls[0]
ck("G3b", (c0.gamma, c0.open_interest, c0.strike, c0.mark) == (0.05, 1000, 95.0, 6.0),
   f"the FOUR fields compute_gex reads survive intact: gamma={c0.gamma} "
   f"oi={c0.open_interest} strike={c0.strike} mark={c0.mark}")

gx_, _sp = g.gex_of(snap)
ck("G3c", gx_ is not None and hasattr(gx_, "orb_bias"),
   f"production's compute_gex ran and returned its own labels: "
   f"env={getattr(gx_, 'gex_environment', None)} "
   f"orb_bias={getattr(gx_, 'orb_bias', None)}")

# 🔴 THE PROXY IS A SHAPE CHANGE, NOT A CALIBRATION ONE. Where OI is real GEX
# is LINEAR in gamma; where absent it is 100000*gamma^2*spot/mark — QUADRATIC.
# Gamma peaks ATM, so a scalar disagreement rate buries a systematic ATM bias
# as noise. Measured 2026-09-18 AMD: 0.0% proxy within 5% of spot, 10.8%
# beyond — the amplification does NOT bite on current data, and only the
# stratification shows that.
_ps = {"event": "chain_snapshot", "ts_et": "x", "symbol": "T",
       "underlying": "100.0", "contracts": [
           {"type": "C", "strike": 100.0, "gamma": 0.10, "oi": 500, "mark": 5.0},
           {"type": "C", "strike": 100.5, "gamma": 0.10, "oi": 0,   "mark": 5.0},
           {"type": "C", "strike": 140.0, "gamma": 0.01, "oi": 0,   "mark": 0.2}]}
ex = g.proxy_exposure(_ps)
ck("G3d", any(not k.startswith(">") for k in ex) and any(k.startswith(">") for k in ex),
   f"proxy exposure is reported BY MONEYNESS BAND, never as one number: {ex}")

# ---------------------------------------------------------------- G5 / G6
_saved = g.snapshots
try:
    # ⚠️ TWO FIXTURES, DELIBERATELY. An empty-contract snapshot returns before
    # the summary is reached, so G5 and G6 cannot be asserted against one run
    # — a single fixture would have made one of them vacuous.
    nofl = dict(snap)
    nofl["contracts"] = []
    g.snapshots = lambda d, s: ([nofl], "")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        g.run("2026-09-18", "T")
    out = buf.getvalue()
    ck("G5", "LOADED SNAPSHOT" in out,
       "a negative conclusion is printed WITH the n it rests on, so it can "
       "never be read as a verdict on a tape that was never loaded")

    # 🔴 G6 IS REVERSED ON PURPOSE. v1.0 asserted the dealer-sign convention
    # was declared an UNVERIFIED ASSUMPTION. It is not one — `data/gex_data.py`
    # documents it and v3.0 defers to production entirely, so keeping the old
    # assertion would require the report to call a settled thing unsettled: a
    # gate demanding a falsehood. What deserves declaring now is the live
    # finding — production computes `orb_bias` and NO STRATEGY READS IT.
    g.snapshots = lambda d, s: ([snap], "")
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        g.run("2026-09-18", "T")
    out2 = buf2.getvalue()
    ck("G6", "orb_bias" in out2 and "READ BY NO" in out2.upper(),
       "the report declares production's orb_bias is computed and read by "
       "nothing — an instrument on disk and unread")
    ck("G6b", "compute_gex" in out2,
       "the report NAMES production's function as the source, so a reader "
       "cannot mistake these numbers for the tool's own arithmetic")
finally:
    g.snapshots = _saved

print()
if FAILS:
    print(f"FAILED: {', '.join(FAILS)}")
    sys.exit(1)
print(f"ALL PASS ({len(RAN)})")
