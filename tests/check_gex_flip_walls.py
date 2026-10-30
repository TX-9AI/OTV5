#!/usr/bin/env python3
"""
tests/check_gex_flip_walls.py  v5.0
v5.0  2026-10-30  OTV5 r56 (GEX.4) — THE FLIP AND THE WALLS SAY SOMETHING ABOUT TODAY'S PRICE. TELEMETRY ONLY.
      data/gex_data.py walked the front expiry from its LOWEST strike, unbounded, and took the first per-strike net sign
      change, so TSLA 2026-10-29 logged flips of $50-$390 on a ~$404 stock (09:30:19 ET: 215; 09:40:03: 372.5) and,
      with no crossing, copied the pin; the walls were unbounded argmaxes, so call_wall == put_wall on 96% of TSLA 10-29
      readings. The operator, 2026-10-29: "I'm curious about the gex flip you described. Have an agent look into it."
      then "I agree on the gex fix for flip & walls, yes now."
      Driven through the REAL data.gex_data.compute_gex on the recorded TSLA 10-29 chains
      (tests/fixtures/tsla_chain_20261029.json, 09:30:19 and 09:40:03 ET) and on synthetic chains. The r55 compute_gex is
      copied VERBATIM below as the reference for everything that must not move.

  F1  TSLA 09:30:19 (r55: flip 215): the flip is inside the band and within $2 of the cumulative-profile value the
      investigation measured (380.8), and it is not the pin
  F2  TSLA 09:40:03 (r55: flip 372.5, a deep-ITM call's junk gamma): inside the band, within $2 of 380.5
  F3  TSLA both snapshots: call_wall >= spot >= put_wall, the runner-ups and their ratios recorded (09:40: 410 / 420
      at 0.93 - the near-tie), and the two walls differ
  S1  synthetic: far-tail junk (a 60 put at gamma 1e-5, a 62 call at 2e-5, a sub-floor deep-ITM call, a sub-OI-floor
      ATM call) no longer sets the flip; the flip is the analytic cumulative zero 101.67
  S2  no crossing: flip_strike 0.0 (not the pin), flip_crossings 0, and the log line reads "flip=none"
  S3  crossings only outside the band: none
  S4  several crossings: the one nearest spot (97.0 of 91.0 / 93.5 / 97.0), flip_crossings 3
  S5  no real OI anywhere (every contract on the oi_proxy): the flip is none (the proxy is not real OI)
  S6  walls: no call GEX above spot -> call_wall 0.0 and "call_wall=none"; a lone candidate has no runner-up
  S7  the GEX computed line keeps "pin=$" and "env=" where status.py reads them, and appends cw2= / pw2=
  I1  pin_strike, pin_strike_raw, pin_dist_pct, pin_concentration, net_gex_ratio, gex_environment, orb_bias, net_gex,
      totals, valid and the per-strike map IDENTICAL to r55 on both fixtures and on every synthetic chain
  I2  the same identity on 600 seeded random chains (zero gammas, zero OI on the proxy branch, SPX to SOFI scales)

Born red on e80d1ff at F1, F2, F3a, F3b, F3c, S1, S2, S3, S4, S5, S6a, S6b and S7 (I1, I2 pass there by construction).
Run:  python3 tests/check_gex_flip_walls.py
"""
import json
import logging
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    from data import gex_data as G                               # noqa: E402
    from data.gex_data import GEXSnapshot, StrikeGEX             # noqa: E402
    from data.options_chain import OptionContract, OptionsChain  # noqa: E402
except Exception as exc:                                         # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

FAILED = []
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "tsla_chain_20261029.json")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.lines = []

    def emit(self, rec):
        self.lines.append(rec.getMessage())


_cap = _Cap()
_lg = logging.getLogger("data.gex_data")
_lg.addHandler(_cap)
_lg.setLevel(logging.INFO)
_lg.propagate = False


def gex(chain, spot):
    _cap.lines.clear()
    snap = G.compute_gex(chain, spot)
    line = next((m for m in _cap.lines if m.startswith("GEX computed:")), "")
    return snap, line


def oc(t, k, g, oi, mark=1.0):
    return OptionContract(option_type=t, strike=float(k), gamma=float(g), open_interest=int(oi), mark=float(mark))


def chain(calls, puts, spot):
    return OptionsChain(underlying="X", calls=list(calls), puts=list(puts), spot_price=spot)


# ── THE r55 compute_gex, COPIED VERBATIM FROM e80d1ff data/gex_data.py (docstring and comments trimmed) ───
def compute_gex_r55(chain: OptionsChain, spot_price: float) -> GEXSnapshot:
    from datetime import datetime, timezone
    snapshot = GEXSnapshot(
        spot_price   = spot_price,
        computed_at  = datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
    )
    if not chain or not chain.calls or not chain.puts:
        return snapshot
    strike_map: dict = {}
    for call in chain.calls:
        if call.gamma == 0:
            continue
        s = call.strike
        if s not in strike_map:
            strike_map[s] = StrikeGEX(strike=s)
        oi_proxy = call.open_interest if call.open_interest > 0 else max(1, int(1000 * call.gamma / max(call.mark, 0.01)))
        gex = call.gamma * oi_proxy * 100 * spot_price
        strike_map[s].call_gex += gex
        strike_map[s].call_oi  += oi_proxy
    for put in chain.puts:
        if put.gamma == 0:
            continue
        s = put.strike
        if s not in strike_map:
            strike_map[s] = StrikeGEX(strike=s)
        oi_proxy = put.open_interest if put.open_interest > 0 else max(1, int(1000 * put.gamma / max(put.mark, 0.01)))
        gex = put.gamma * oi_proxy * 100 * spot_price * -1
        strike_map[s].put_gex += gex
        strike_map[s].put_oi  += oi_proxy
    if not strike_map:
        return snapshot
    for sg in strike_map.values():
        sg.net_gex = sg.call_gex + sg.put_gex
    strikes_sorted = sorted(strike_map.values(), key=lambda s: s.strike)
    snapshot.strikes = strikes_sorted
    snapshot.total_call_gex = sum(s.call_gex for s in strikes_sorted)
    snapshot.total_put_gex  = sum(s.put_gex  for s in strikes_sorted)
    snapshot.net_gex        = snapshot.total_call_gex + snapshot.total_put_gex
    call_wall_strike = max(strikes_sorted, key=lambda s: s.call_gex, default=None)
    if call_wall_strike:
        snapshot.call_wall = call_wall_strike.strike
    put_wall_strike = min(strikes_sorted, key=lambda s: s.put_gex, default=None)
    if put_wall_strike:
        snapshot.put_wall = put_wall_strike.strike
    pin = max(strikes_sorted, key=lambda s: s.net_gex, default=None)
    if pin:
        snapshot.pin_strike_raw = pin.strike
        if spot_price and spot_price > 0:
            snapshot.pin_dist_pct = abs(pin.strike - spot_price) / spot_price
            near = [s for s in strikes_sorted
                    if abs(s.strike - spot_price) / spot_price
                    <= G.PIN_MAX_DIST_PCT]
            best = max(near, key=lambda s: s.net_gex, default=None)
            snapshot.pin_strike = best.strike if best else 0.0
        else:
            snapshot.pin_strike = 0.0
    flip = None
    for i in range(1, len(strikes_sorted)):
        prev = strikes_sorted[i - 1]
        curr = strikes_sorted[i]
        if prev.net_gex < 0 and curr.net_gex >= 0:
            if abs(prev.net_gex) < abs(curr.net_gex):
                flip = prev.strike
            else:
                flip = curr.strike
            break
    if flip:
        snapshot.flip_strike = flip
    elif strikes_sorted:
        snapshot.flip_strike = snapshot.pin_strike
    gross = sum(abs(sg.net_gex) for sg in snapshot.strikes) or 1.0
    net_ratio = snapshot.net_gex / gross
    pin_sg = max(snapshot.strikes, key=lambda s: abs(s.net_gex), default=None)
    pin_conc = (abs(pin_sg.net_gex) / gross) if pin_sg is not None else 0.0
    snapshot.pin_concentration = round(pin_conc, 4)
    snapshot.net_gex_ratio = round(net_ratio, 4)
    if net_ratio > G.GEX_SIGN_RATIO and pin_conc >= G.GEX_PIN_CONCENTRATION:
        snapshot.gex_environment = "PINNING"
        snapshot.orb_bias        = "DAMPENING"
    elif net_ratio < -G.GEX_SIGN_RATIO:
        snapshot.gex_environment = "TRENDING"
        snapshot.orb_bias        = "AMPLIFYING"
    else:
        snapshot.gex_environment = "NEUTRAL"
        snapshot.orb_bias        = "NEUTRAL"
    snapshot.valid = True
    return snapshot


KEEP = ("pin_strike", "pin_strike_raw", "pin_dist_pct", "pin_concentration", "net_gex_ratio", "gex_environment",
        "orb_bias", "net_gex", "total_call_gex", "total_put_gex", "valid")


def same_as_r55(ch, spot):
    """'' when every kept field and the strike map equal r55's on this input, else the first difference."""
    a, b = G.compute_gex(ch, spot), compute_gex_r55(ch, spot)
    for f in KEEP:
        if getattr(a, f) != getattr(b, f):
            return f"{f}: {getattr(a, f)!r} != r55 {getattr(b, f)!r}"
    ka = [(s.strike, s.call_gex, s.put_gex, s.net_gex, s.call_oi, s.put_oi) for s in a.strikes]
    kb = [(s.strike, s.call_gex, s.put_gex, s.net_gex, s.call_oi, s.put_oi) for s in b.strikes]
    return "" if ka == kb else "strikes differ"


def fixture_chains():
    d = json.load(open(FIXTURE, encoding="utf-8"))
    out = []
    for sn in d["snapshots"]:
        c, p = [], []
        for t, k, m, g, oi in sn["contracts"]:
            (c if t == "C" else p).append(oc(t, k, g, oi, m))
        out.append((sn["ts_et"][11:19], chain(c, p, sn["underlying"]), float(sn["underlying"])))
    return out


def in_band(flip, spot):
    return flip > 0 and abs(flip - spot) / spot <= getattr(G, "GEX_FLIP_BAND_PCT", 0.15)


def main():
    synth = []

    # ── F1-F3: the recorded TSLA 2026-10-29 chains ───────────────────────────────────────────
    fx = fixture_chains()
    want = {"09:30:19": 380.8, "09:40:03": 380.5}
    for i, (ts, ch, spot) in enumerate(fx):
        s, line = gex(ch, spot)
        tag = "F1" if ts == "09:30:19" else "F2"
        check(f"{tag} TSLA {ts}: flip inside the band near the cumulative zero {want[ts]}, not the pin",
              in_band(s.flip_strike, spot) and abs(s.flip_strike - want[ts]) <= 2.0 and s.flip_strike != s.pin_strike,
              f"flip={s.flip_strike} spot={spot} pin={s.pin_strike} (r55: {compute_gex_r55(ch, spot).flip_strike})")
        cwr = getattr(s, "call_wall_runner", None)
        pwr = getattr(s, "put_wall_runner", None)
        check(f"F3{'ab'[i]} TSLA {ts}: call_wall >= spot >= put_wall, walls differ, runner-ups recorded",
              s.call_wall >= spot >= s.put_wall > 0 and s.call_wall != s.put_wall
              and cwr is not None and cwr >= spot and pwr is not None and 0 < pwr <= spot
              and 0 < getattr(s, "call_wall_runner_ratio", 0) <= 1 and 0 < getattr(s, "put_wall_runner_ratio", 0) <= 1,
              f"cw={s.call_wall} (2nd {cwr} @{getattr(s, 'call_wall_runner_ratio', None)}) "
              f"pw={s.put_wall} (2nd {pwr} @{getattr(s, 'put_wall_runner_ratio', None)}) | {line[14:]}")
        if ts == "09:40:03":
            check("F3c TSLA 09:40:03: the near-tie is visible (call wall 410, runner 420 at >= 0.9)",
                  s.call_wall == 410.0 and cwr == 420.0 and getattr(s, "call_wall_runner_ratio", 0) >= 0.9,
                  f"cw={s.call_wall} 2nd={cwr} ratio={getattr(s, 'call_wall_runner_ratio', None)}")
        d = same_as_r55(ch, spot)
        check(f"I1{'ab'[i]} TSLA {ts}: pin / raw / dist / conc / ratio / env / orb / net / strikes identical to r55",
              d == "", d)

    # ── S1: far-tail junk must not set the flip ──────────────────────────────────────────────
    # cumulative (x 0.05*100*100 = 500 per OI): 90 -1000, 95 -2000, 100 -500, 105 +1000 (OI units)
    # -> zero between 100 and 105 at 100 + 5 * 500/1500 = 101.667
    spot = 100.0
    calls = [oc("C", 100, 0.05, 1500), oc("C", 105, 0.05, 1500),
             oc("C", 62, 0.00002, 50),          # far tail: base's first "crossing"
             oc("C", 86, 0.0004, 20),           # deep-ITM junk, below the gamma floor (1% of 0.05)
             oc("C", 98, 0.05, 5)]              # real gamma, OI below MIN_OI_THRESHOLD
    puts = [oc("P", 90, 0.05, 1000), oc("P", 95, 0.05, 1000), oc("P", 60, 0.00001, 5000)]
    ch = chain(calls, puts, spot)
    synth.append((ch, spot))
    s, line = gex(ch, spot)
    r = compute_gex_r55(ch, spot)
    check("S1 junk tails do not set the flip: the analytic cumulative zero 101.67",
          abs(s.flip_strike - 101.667) <= 0.01 and getattr(s, "flip_crossings", None) == 1,
          f"flip={s.flip_strike} crossings={getattr(s, 'flip_crossings', None)} (r55: {r.flip_strike})")

    # ── S2: no crossing -> none, never the pin ───────────────────────────────────────────────
    ch = chain([oc("C", 95, 0.05, 2000), oc("C", 100, 0.05, 2000), oc("C", 105, 0.05, 2000)],
               [oc("P", 95, 0.05, 100), oc("P", 100, 0.05, 100)], 100.0)
    synth.append((ch, 100.0))
    s, line = gex(ch, 100.0)
    check("S2 no crossing: flip 0.0 (not the pin), crossings 0, the line reads flip=none",
          s.flip_strike == 0.0 and s.pin_strike > 0 and getattr(s, "flip_crossings", None) == 0
          and " flip=none " in line,
          f"flip={s.flip_strike} pin={s.pin_strike} | {line[14:]}")

    # ── S3: a crossing only outside the band ─────────────────────────────────────────────────
    ch = chain([oc("C", 72, 0.05, 3000), oc("C", 100, 0.05, 2000), oc("C", 102, 0.05, 2000)],
               [oc("P", 70, 0.05, 1000)], 100.0)
    synth.append((ch, 100.0))
    s, line = gex(ch, 100.0)
    check("S3 a crossing only outside the band is not a flip", s.flip_strike == 0.0 and " flip=none " in line,
          f"flip={s.flip_strike} (r55: {compute_gex_r55(ch, 100.0).flip_strike})")

    # ── S4: several crossings -> nearest spot ────────────────────────────────────────────────
    # per-strike net (OI units): 90 -1000, 92 +2000, 95 -2000, 99 +2000 -> cum -1, +1, -1, +1 (x1000)
    # crossings 91.0, 93.5, 97.0 -> nearest 100 is 97.0
    ch = chain([oc("C", 92, 0.05, 2000), oc("C", 99, 0.05, 2000)],
               [oc("P", 90, 0.05, 1000), oc("P", 95, 0.05, 2000)], 100.0)
    synth.append((ch, 100.0))
    s, line = gex(ch, 100.0)
    check("S4 several crossings: the one nearest spot (97.0), crossings 3",
          abs(s.flip_strike - 97.0) <= 0.01 and getattr(s, "flip_crossings", None) == 3,
          f"flip={s.flip_strike} crossings={getattr(s, 'flip_crossings', None)}")

    # ── S5: no real OI -> no flip (the oi_proxy is not open interest) ────────────────────────
    ch = chain([oc("C", 100, 0.05, 0, 2.0), oc("C", 105, 0.05, 0, 1.0)],
               [oc("P", 90, 0.05, 0, 1.0), oc("P", 95, 0.05, 0, 1.5)], 100.0)
    synth.append((ch, 100.0))
    s, line = gex(ch, 100.0)
    check("S5 every contract on the oi_proxy: flip none", s.flip_strike == 0.0 and " flip=none " in line,
          f"flip={s.flip_strike} (r55: {compute_gex_r55(ch, 100.0).flip_strike})")

    # ── S6: walls on their side of spot ──────────────────────────────────────────────────────
    ch = chain([oc("C", 90, 0.05, 3000), oc("C", 95, 0.05, 3000)],
               [oc("P", 95, 0.05, 500), oc("P", 105, 0.05, 4000)], 100.0)
    synth.append((ch, 100.0))
    s, line = gex(ch, 100.0)
    check("S6a no call GEX at or above spot: call_wall 0.0 and call_wall=none",
          s.call_wall == 0.0 and " call_wall=none " in line and getattr(s, "call_wall_runner", None) == 0.0,
          f"cw={s.call_wall} (r55: {compute_gex_r55(ch, 100.0).call_wall}) | {line[14:]}")
    check("S6b a lone put candidate below spot is the put wall with no runner-up",
          s.put_wall == 95.0 and getattr(s, "put_wall_runner", None) == 0.0
          and getattr(s, "put_wall_runner_ratio", None) == 0.0 and " pw2=none" in line,
          f"pw={s.put_wall} (r55: {compute_gex_r55(ch, 100.0).put_wall}) 2nd={getattr(s, 'put_wall_runner', None)}")

    # ── S7: the log line still parses where status.py reads it ───────────────────────────────
    s, line = gex(fx[0][1], fx[0][2])
    pin_tok = line.split("pin=$")[1].split()[0].rstrip(")") if "pin=$" in line else None
    env_tok = line.split("env=")[1].split()[0] if "env=" in line else None
    check("S7 GEX computed keeps pin=$ / env= for status.py and appends cw2= / pw2=",
          pin_tok == f"{s.pin_strike:.0f}" and env_tok == s.gex_environment
          and " cw2=$410@0.79 " in line + " " and " pw2=$395@0.88" in line,
          line[14:])

    # ── I1 (synthetic) and I2: nothing that decides anything moved ──────────────────────────
    bad = [d for d in (same_as_r55(c, sp) for c, sp in synth) if d]
    check(f"I1c the {len(synth)} synthetic chains: every kept field identical to r55", not bad, "; ".join(bad[:3]))
    rng = random.Random(56)
    bad, n = [], 600
    for _ in range(n):
        spot = rng.choice((7700.0, 712.0, 404.0, 83.0, 17.3)) * rng.uniform(0.98, 1.02)
        step = spot * rng.choice((0.0025, 0.005, 0.01))
        ks = [round(spot + step * j, 2) for j in range(-rng.randint(3, 40), rng.randint(3, 40))]
        cs, ps = [], []
        for k in ks:
            for side, lst in (("C", cs), ("P", ps)):
                if rng.random() < 0.15:
                    continue
                g = 0.0 if rng.random() < 0.1 else rng.uniform(0, 0.06) * (404.0 / spot)
                oi = 0 if rng.random() < 0.2 else rng.randint(0, 20000)
                lst.append(oc(side, k, round(g, 6), oi, rng.uniform(0.01, 30)))
        if not cs or not ps:
            continue
        d = same_as_r55(chain(cs, ps, spot), spot)
        if d:
            bad.append(d)
    check(f"I2 {n} seeded random chains: every kept field and the strike map identical to r55",
          not bad, f"{len(bad)} differ: " + "; ".join(bad[:3]))


main()
print("RESULT:", "FAIL " + ",".join(FAILED) if FAILED else "PASS")
sys.exit(1 if FAILED else 0)
