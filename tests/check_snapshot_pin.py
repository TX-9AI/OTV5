#!/usr/bin/env python3
"""
tests/check_snapshot_pin.py  v1.3
v1.3  2026-09-22  OTV4TEST r99 — S7a-e: the VWAP context on the fire
      snapshot. `price_vs_vwap` was NULL on EVERY row ever written because a
      categorical was run through `_f()`. Pins the number, the SIGNED
      distance, the slope, the text label, and `vwap_source` — plus a forced
      session-VWAP failure that must fall back to the frame AND SAY SO.
v1.2  2026-09-22  OTV4TEST r91 — S2 PINS THE CLOCK. `expected_move` scales by
      sqrt(hours-to-16:00) off `datetime.now(ET)`, so build_payload's call and
      the checker's landed on different instants and disagreed by ~the
      tolerance. After 16:00 the 0.25h floor clamps it constant, so every
      EVENING run was deterministic and every MORNING run a coin flip. The
      1e-9 bar is NOT loosened — it is the whole meaning of the check.
v1.1  2026-09-04  r244 — S6 extends to `pin_concentration` and
      `gex_environment` — recorded RAW, kept as distinct keys, and None rather
      than 0.0 or "" when the gex object carries neither.
v1.0  2026-09-04  r243 — THE PIN AND ITS EM FRACTION REACH THE SNAPSHOT.

🔴 WHY. Operator, 2026-09-04, after the stop-removal and window cases both
failed on evidence: *"then that leaves the EM variable as our last hope of
raising our win rate. What is the furthest EM that this trade will fire on?"*
The band is 0.30–1.00 and hard-capped — but whether the SEVEN winners sat lower
in it than the THIRTEEN losers was UNANSWERABLE: `plan_check` carries
`pin_em_fraction` on every tick and has NO trade_id, and `fire_snapshot` is
keyed BY trade_id and carried no pin and no EM.

🔑 SAME SHAPE AS r240 — a field computed, used for a DECISION, and never
written where the OUTCOME could be joined to it. The bridge existed; it just
did not carry the field.

⚠️ NOTHING ACCRUES RETROACTIVELY. The 20 butterflies already banked stay
unmeasurable. This starts the collection.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


class _Gex:
    def __init__(self, pin, conc=None, env=None):
        self.pin_strike = pin
        if conc is not None:
            self.pin_concentration = conc
        if env is not None:
            self.gex_environment = env


def main():
    from derived.snapshot import SnapshotEngine
    from strategy.gex_pin_butterfly import expected_move, EM_MIN_FRAC, EM_MAX_FRAC
    from datetime import datetime as _dt
    from utils.time_utils import ET as _ET

    e = SnapshotEngine.__new__(SnapshotEngine)
    e.symbol = "TEST"

    # ══ S1 — THE KEYS ARE ALWAYS PRESENT ══════════════════════════════════
    # ⚠️ This file's own contract: every key is emitted even when null, so a
    # study can tell "measured as absent" from "did not exist in that era".
    p = e.build_payload({"price": 100.0, "atm_iv": 0.30})
    check("S1 pin_strike and pin_em_fraction are always emitted",
          "pin_strike" in p and "pin_em_fraction" in p)
    check("S1b unmeasurable reads None, NEVER 0.0",
          p["pin_strike"] is None and p["pin_em_fraction"] is None,
          f"{p['pin_strike']!r} {p['pin_em_fraction']!r}")

    # ══ S2 — THE FRACTION MATCHES THE GATE'S OWN ARITHMETIC ═══════════════
    # 🔴 THE POINT OF THE WHOLE REVISION. If this reproduced the fraction with
    # a second definition, the study would compare a number the gate never saw
    # against an outcome the gate decided — worse than no field at all.
    price, iv, pin = 100.0, 0.30, 103.0
    # 🔴 r91 — THE CLOCK IS PINNED, AND THE TOLERANCE IS NOT TOUCHED.
    # `expected_move` scales by sqrt(hours-to-16:00) read off `datetime.now(ET)`,
    # so `build_payload`'s call and this one landed on DIFFERENT instants and the
    # two fractions disagreed by roughly the tolerance itself. MEASURED on this
    # box: two back-to-back calls differ by 6.75e-10 against a 1e-9 bar, and
    # build_payload does far more work between them than that.
    # ⚠️ IT PASSED FOR A YEAR BY ACCIDENT OF SCHEDULE. After 16:00 ET the
    # `max(hours, 0.25)` floor clamps the value CONSTANT, so the two calls agree
    # EXACTLY (measured: delta 0.0) — every evening run was deterministic and
    # every morning run was a coin flip. r86 moved the sweep to the 08:00 boot
    # and the coin started landing tails.
    # 🔑 LOOSENING THE TOLERANCE WOULD BE THE WRONG FIX AND IS REFUSED. The tight
    # bar is the ENTIRE meaning of this check — "the payload reproduces the
    # gate's own arithmetic rather than inventing a second definition of it"
    # (r243). A slack tolerance would pass a genuine second definition that
    # merely rounds to something similar, which is the defect, not the fixture.
    import strategy.gex_pin_butterfly as _gpb
    _real_em = _gpb.expected_move
    _fixed = _dt.now(_ET).replace(hour=12, minute=0, second=0, microsecond=0)
    _gpb.expected_move = lambda u, atm, now=None, _f=_fixed: _real_em(u, atm, now=_f)
    try:
        # `derived/snapshot.py` imports the name INSIDE the function, so the
        # payload picks up the pinned clock on this call — the real function,
        # the real arithmetic, one instant.
        got = e.build_payload({"price": price, "atm_iv": iv, "gex": _Gex(pin)})
        want = abs(pin - price) / _gpb.expected_move(price, iv)
    finally:
        _gpb.expected_move = _real_em     # never leave the module patched
    check("S2 the fraction equals |pin - spot| / expected_move()",
          abs(got["pin_em_fraction"] - want) < 1e-9,
          f"{got['pin_em_fraction']:.6f} vs {want:.6f}")
    check("S2b and the pin itself round-trips", got["pin_strike"] == pin)

    # ══ S3 — A PIN AT THE MONEY IS 0.0, NOT None ══════════════════════════
    # ⚠️ The opposite fact from S1b and it must not collapse into it: a pin
    # exactly at spot is a MEASURED zero and belongs in the sample.
    atm = e.build_payload({"price": price, "atm_iv": iv, "gex": _Gex(price)})
    check("S3 a pin AT spot reads 0.0, distinct from unmeasurable",
          atm["pin_em_fraction"] == 0.0, repr(atm["pin_em_fraction"]))

    # ══ S4 — IT NEVER RAISES INTO THE FIRE PATH ═══════════════════════════
    # 🔴 `capture()` runs on every fill. A study field that can throw would
    # cost a trade its snapshot — or worse — for a number nobody needs live.
    for bad in ({"price": None, "atm_iv": 0.3, "gex": _Gex(100.0)},
                {"price": 100.0, "atm_iv": None, "gex": _Gex(100.0)},
                {"price": 100.0, "atm_iv": 0.3, "gex": object()},
                {}):
        try:
            e.build_payload(bad)
        except Exception as exc:                               # noqa: BLE001
            check("S4 build_payload never raises on a degenerate ctx", False,
                  f"{type(exc).__name__}: {exc}")
            break
    else:
        check("S4 build_payload never raises on a degenerate ctx", True)

    # ══ S5 — THE BAND IS STILL HARD-CAPPED ════════════════════════════════
    # ⚠️ r208: `cap=EM_MAX_FRAC` makes the relaxed value equal the base, so the
    # ceiling cannot widen. Recording the fraction must not become a reason to
    # loosen the gate that made it worth recording.
    check("S5 the EM band is unchanged at 0.30-1.00",
          EM_MIN_FRAC == 0.30 and EM_MAX_FRAC == 1.00,
          f"{EM_MIN_FRAC}-{EM_MAX_FRAC}")

    # ══ S6 — ALL THREE PIN MEASURES, NOT JUST THE EM FRACTION ════════════
    # 🔴 r244. `pin_concentration` (29% fail) and the GEX environment behind
    # `pinning` (53% fail) GATE every butterfly fire and NEITHER has ever been
    # tested against an outcome. Instrumenting only the EM fraction would let a
    # study conclude "EM predicts nothing" while the real signal sat in a field
    # nobody recorded.
    full = e.build_payload({"price": price, "atm_iv": iv,
                            "gex": _Gex(pin, conc=0.31, env="PINNING")})
    check("S6 pin_concentration is recorded RAW, not as a pass/fail",
          full["pin_concentration"] == 0.31, repr(full["pin_concentration"]))
    check("S6b the GEX environment is recorded",
          full["gex_environment"] == "PINNING", repr(full["gex_environment"]))
    # ⚠️ THE GATE'S ANSWER IS ALREADY IN plan_check. What was missing is the
    # VALUE — a study cannot fit a boundary it can only see one side of.
    check("S6c a gex object carrying neither yields None, not 0.0 or ''",
          got["pin_concentration"] is None and got["gex_environment"] is None,
          f"{got['pin_concentration']!r} {got['gex_environment']!r}")
    # 🔑 SEPARATELY, NOT COMPOSITED — r224: a composite that separates tells you
    # nothing about WHICH PART did the work.
    check("S6d all four pin fields are distinct keys",
          len({"pin_strike", "pin_em_fraction", "pin_concentration",
               "gex_environment"} & set(full)) == 4)

    print()
    # ══ S7 — THE VWAP CONTEXT (r99) ═══════════════════════════════════════
    # 🔴 NULL ON EVERY ROW EVER WRITTEN, back to 09-09, and it took the
    # operator asking *"do we have any VWAP to reference?"* to surface it.
    # `volatility_engine:226` sets "ABOVE"/"BELOW"/"NONE" — a CATEGORICAL —
    # and the payload ran `_f()` on it, so `float("ABOVE")` raised, `_f`
    # swallowed it, and the column stored None. Computed every tick for weeks
    # and discarded at the snapshot boundary.
    import types as _t
    _vol = _t.SimpleNamespace(vwap=740.11, price_vs_vwap="ABOVE")
    _p7 = e.build_payload({"price": 744.90, "atm_iv": 0.19, "vol": _vol})
    check("S7 price_vs_vwap survives as TEXT, not float()-ed to None",
          _p7.get("price_vs_vwap") == "ABOVE", repr(_p7.get("price_vs_vwap")))
    check("S7b the VWAP NUMBER is recorded, not just a direction",
          isinstance(_p7.get("vwap"), float) and _p7["vwap"] > 0,
          repr(_p7.get("vwap")))
    # 🔑 THE DISTANCE IS THE FIELD THAT ANSWERS THE QUESTION. A continuation
    # trade is definitionally a bet on EXTENSION, so "how far from VWAP" is
    # the measurement; a direction cannot answer it. Signed: + is above.
    check("S7c a SIGNED distance in percent is recorded",
          isinstance(_p7.get("vwap_dist_pct"), float), repr(_p7.get("vwap_dist_pct")))
    # ⚠️ S7d — WHICH VWAP ANSWERED MUST BE ON THE ROW. There are TWO in this
    # tree: the session-anchored one (r94/r96) and volatility_engine's own
    # df_5m cumsum. MEASURED 2026-09-22 15:30 ET they differed by 4.86 points.
    # A study that cannot tell them apart is averaging two quantities.
    check("S7d vwap_source names which VWAP answered",
          _p7.get("vwap_source") in ("session", "frame_5m"), repr(_p7.get("vwap_source")))
    # ⚠️ S7e — THE FALLBACK IS LABELLED, NEVER SILENT (§0.5).
    import derived.anchors as _A
    _keep = _A.vwap_now
    _A.vwap_now = lambda *a, **k: (None, "forced for the check")
    try:
        _p7b = e.build_payload({"price": 744.90, "atm_iv": 0.19, "vol": _vol})
    finally:
        _A.vwap_now = _keep
    check("S7e no session VWAP -> falls back to the frame AND says so",
          _p7b.get("vwap") == 740.11 and _p7b.get("vwap_source") == "frame_5m",
          f"{_p7b.get('vwap')} / {_p7b.get('vwap_source')}")

    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 11 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
