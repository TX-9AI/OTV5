"""
tests/check_strike_ladder.py  v1.0
v1.0  2026-10-02  OTV4TEST r185 (LADR.1) — SHARED GATE, byte-identical in
      OTV4TEST and otv4 but for this header. STRIKES ARE READ FROM THE CHAIN,
      NOT A STATIC TABLE. The operator, 2026-09-29: "Yes to all" on reading
      the ladder from the chain; 2026-10-02: "Yes, deploy it. Coordinate
      landing it amongst yourselves." Design agreed with otv4's agent
      2026-09-29 (OTV4TEST authors, otv4 mirrors by sha256; WA section 38.9).

      INTERPRETERS, PER TREE (stated, not claimed for a tree it was not run on):
      OTV4TEST — /usr/bin/python3 (3.14, with the r106 venv bootstrap below)
      and venv/bin/python. otv4 — the dtp venv on control (CHK.11): that
      checkout has no venv/, so the bootstrap below finds nothing there, and
      data/options_chain imports tastytrade, which the bare system python
      lacks on both boxes.

WHAT IT DRIVES (never source text, WA section 21):
  L1  data.options_chain.chain_increment — the REAL function on hand ladders:
      $2.50, $0.50 (SOFI), $1, a $2.50 ladder carrying one stray half-strike
      (the MEDIAN, not the min), and the < 3 strikes fallback.
  L2  strategy.gex_pin_butterfly._chain_increment IS that function — one
      ladder reader, not two copies that can drift.
  L3  OptionsChainFetcher.select_butterfly_strikes is GONE (0 callers in both
      trees; it centred on the table BFLY.3 measured wrong).
  L4  round/floor/ceil_to_strike keep a fractional increment (r137's _strike)
      and still return an int on a whole one (the unchanged path).
  L5  the REAL ORBEngine._check_for_break, long: target_strike is the RAW
      100% target (16.90 + 0.50 = 17.40), not one pre-rounded on
      config.STRIKE_INCREMENT.
  L6  the same, short (16.40 - 0.50 = 15.90).
  L7  the REAL state_snapshot -> file -> load_state_file round trip keeps a
      16.5 target (the int() reload made it 16 after a restart).
  L8  THE TRADE: the engine's target through the REAL select_orb_strike on a
      $2.50 ladder (range 223.40-226.00, target 228.60) buys the NEAREST
      LISTED strike, 227.5 — the pre-round on a $1 or $5 table took 230.
  L9  UNCHANGED PATH: a $1 ladder (range 610.00-612.30, targets 614.60 and
      607.70) buys exactly what the pre-round bought, 615C and 608P.

Run:  python3 tests/check_strike_ladder.py   (exit 0 green, 1 red)
"""
import glob as _glob
import json
import os
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _K:
    def __init__(self, k):
        self.strike = k


def _chain(strikes, spot):
    from data.options_chain import OptionContract, OptionsChain
    ch = OptionsChain(underlying="TEST", expiry="2026-10-02", spot_price=spot)
    ch.calls, ch.puts = [], []
    for k in strikes:
        m = max(0.10, round(3.0 - 0.25 * abs(k - spot), 2))
        ch.calls.append(OptionContract(symbol=f"C{k}", strike=float(k), mark=m,
                                       bid=m - 0.02, ask=m + 0.02,
                                       delta=max(0.05, min(0.95, 0.5 - 0.05 * (k - spot))),
                                       gamma=0.03, expiry="2026-10-02", option_type="C"))
        ch.puts.append(OptionContract(symbol=f"P{k}", strike=float(k), mark=m,
                                      bid=m - 0.02, ask=m + 0.02,
                                      delta=-max(0.05, min(0.95, 0.5 - 0.05 * (spot - k))),
                                      gamma=0.03, expiry="2026-10-02", option_type="P"))
    return ch


def _frame(rows):
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
        index=pd.date_range("2026-10-02 09:40", periods=len(rows), freq="1min"))


def _engine(hi, lo):
    from analysis.orb_engine import ORBEngine, ORBState
    eng = ORBEngine()
    d = eng._data
    d.orb_high, d.orb_low, d.orb_width = hi, lo, round(hi - lo, 2)
    d.state = ORBState.WAITING_FOR_BREAK
    return eng


def _break(hi, lo, direction):
    """The REAL _check_for_break: the candle opens inside, closes beyond, and
    its range-side wick stays inside the range (r131b's valid break)."""
    eng = _engine(hi, lo)
    w = hi - lo
    if direction == "long":
        o, l_, c = lo + 0.6 * w, lo + 0.2 * w, hi + 0.1 * w
        eng._check_for_break(_frame([(o, c + 0.02, l_, c), (c, c + 0.03, c - 0.01, c + 0.01)]))
    else:
        o, h_, c = lo + 0.4 * w, lo + 0.8 * w, lo - 0.1 * w
        eng._check_for_break(_frame([(o, h_, c - 0.02, c), (c, c + 0.01, c - 0.03, c - 0.01)]))
    return eng


def main():
    import data.options_chain as OC
    import utils.math_utils as MU
    from analysis.orb_engine import ORBEngine, ORBState

    # ── L1 the ladder reader ─────────────────────────────────────────────
    ci = getattr(OC, "chain_increment", None)
    if ci is None:
        check("L1 data.options_chain.chain_increment exists", False,
              "absent - the ladder is read only inside the butterfly")
    else:
        got = {
            "2.5": ci([_K(k) for k in (220, 222.5, 225, 227.5, 230, 232.5)], 226.0),
            "0.5": ci([_K(k) for k in (15.5, 16, 16.5, 17, 17.5)], 16.6),
            "1":   ci([_K(k) for k in range(605, 620)], 612.0),
            "mix": ci([_K(k) for k in (185, 187.5, 190, 190.5, 192.5, 195, 197.5)], 190.0),
        }
        check("L1 chain_increment reads $2.50, $0.50, $1 and the MEDIAN of a mixed ladder",
              abs(got["2.5"] - 2.5) < 1e-9 and abs(got["0.5"] - 0.5) < 1e-9
              and abs(got["1"] - 1.0) < 1e-9 and abs(got["mix"] - 2.5) < 1e-9, str(got))
        check("L1b fewer than 3 strikes -> the caller's default",
              ci([_K(190)], 190.0, 1.0) == 1.0 and ci(None, 190.0, 2.5) == 2.5
              and ci([], 190.0, 0.5) == 0.5)

    # ── L2 one reader ────────────────────────────────────────────────────
    import strategy.gex_pin_butterfly as B
    check("L2 the butterfly's _chain_increment IS data.options_chain.chain_increment",
          ci is not None and getattr(B, "_chain_increment", None) is ci,
          f"fly={getattr(B, '_chain_increment', None)} chain={ci}")

    # ── L3 the dead fly selector is gone ─────────────────────────────────
    check("L3 OptionsChainFetcher.select_butterfly_strikes is deleted",
          not hasattr(OC.OptionsChainFetcher, "select_butterfly_strikes"))

    # ── L4 strike helpers keep fractions ─────────────────────────────────
    r, f, c = MU.round_to_strike, MU.floor_to_strike, MU.ceil_to_strike
    frac = (r(16.4, 0.5), f(16.7, 0.5), c(16.1, 0.5))
    whole = (r(612.3, 1), f(612.7, 1), c(612.1, 1), r(7637.0, 5))
    check("L4 round/floor/ceil_to_strike keep a 0.5 increment (16.5, 16.5, 16.5)",
          frac == (16.5, 16.5, 16.5), str(frac))
    check("L4b UNCHANGED: a whole increment still returns an int (612, 612, 613, 7635)",
          whole == (612, 612, 613, 7635) and all(isinstance(v, int) for v in whole),
          str(whole))

    # ── L5/L6 the engine carries the raw target ──────────────────────────
    el = _break(16.90, 16.40, "long")
    check("L5pre the real engine armed long", el._data.state == ORBState.ARMED_LONG,
          str(el._data.state))
    check("L5 long target_strike is the RAW 100% target 17.40",
          abs(float(el._data.target_strike) - 17.40) < 1e-9,
          f"target_strike={el._data.target_strike} target_100pct={el._data.target_100pct}")
    es = _break(16.90, 16.40, "short")
    check("L6pre the real engine armed short", es._data.state == ORBState.ARMED_SHORT,
          str(es._data.state))
    check("L6 short target_strike is the RAW 100% target 15.90",
          abs(float(es._data.target_strike) - 15.90) < 1e-9,
          f"target_strike={es._data.target_strike}")

    # ── L7 a restart keeps it ────────────────────────────────────────────
    e7 = _break(16.90, 16.40, "long")
    e7._data.target_strike = 16.5
    snap = e7.state_snapshot(16.95)
    tmp = tempfile.mkdtemp(prefix="check_strike_ladder_")
    path = os.path.join(tmp, "orb_state.json")
    with open(path, "w") as fh:
        json.dump(snap, fh)
    fresh = ORBEngine()
    loaded = fresh.load_state_file(path)
    check("L7pre load_state_file accepted today's snapshot", loaded is True, str(loaded))
    check("L7 the reload keeps a 16.5 target (int() made it 16)",
          abs(float(fresh._data.target_strike) - 16.5) < 1e-9,
          f"reloaded={fresh._data.target_strike}")

    # ── L8 the trade: nearest LISTED strike on a $2.50 ladder ────────────
    fetcher = OC.OptionsChainFetcher.__new__(OC.OptionsChainFetcher)
    e8 = _break(226.00, 223.40, "long")
    ch8 = _chain((220, 222.5, 225, 227.5, 230, 232.5, 235), 226.0)
    k8 = fetcher.select_orb_strike(ch8, "long", e8._data.target_strike)
    check("L8 a $2.50 ladder buys the nearest listed strike to 228.60: 227.5C",
          k8 is not None and abs(float(k8.strike) - 227.5) < 1e-9,
          f"target={e8._data.target_strike} bought={getattr(k8, 'strike', None)}")

    # ── L9 unchanged on a $1 ladder ──────────────────────────────────────
    ch9 = _chain(range(600, 625), 611.0)
    e9l, e9s = _break(612.30, 610.00, "long"), _break(612.30, 610.00, "short")
    k9l = fetcher.select_orb_strike(ch9, "long", e9l._data.target_strike)
    k9s = fetcher.select_orb_strike(ch9, "short", e9s._data.target_strike)
    check("L9 UNCHANGED: a $1 ladder buys what the pre-round bought, 615C and 608P",
          k9l is not None and k9s is not None and float(k9l.strike) == 615.0
          and float(k9s.strike) == 608.0,
          f"targets {e9l._data.target_strike}/{e9s._data.target_strike} -> "
          f"{getattr(k9l, 'strike', None)}/{getattr(k9s, 'strike', None)}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — strikes are read from the chain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
