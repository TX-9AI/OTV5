#!/usr/bin/env python3
"""
tests/gex_from_chains.py  v5.1  (2026-10-25)
v5.1  2026-10-25  (GEX.2 + GEX.3) — PORT OF MAINLINE otv4 v3.0 (otv4 r391 + r395). THE v1.0 THIS TREE CARRIED READ
      ROOT=/home/claude/cc (a path from another machine), GLOBBED NOTHING AND PRINTED A CONFIDENT "NO PIN". Now: input via
      tests/warehouse_source (the one S3 lineage); snapshots(date, symbol) returns (None, reason), never a bare [], and
      run() REFUSES non-zero before any conclusion; chain_from_snapshot rebuilds a production OptionsChain and gex_of hands
      it to production's OWN data.gex_data.compute_gex (one definition, no second formula); --proxy-exposure reports the
      oi_proxy (quadratic) branch STRATIFIED BY MONEYNESS. Code verbatim from otv4 v3.0: every module it imports exists
      here with the fields it reads (warehouse_source Meta/client/_envelopes; OptionContract/OptionsChain; compute_gex
      (chain, spot) and GEXSnapshot pin_strike/flip_strike/net_gex/gex_environment/orb_bias). The otv4 entries below are
      that file's own history; their ids are otv4's (otv4 GEX.1 = OTV5 GEX.2, otv4 GEX.2 = OTV5 GEX.3). Gate
      tests/check_gex_from_chains.py (ported with it).
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ... Previous title: tests/gex_from_chains.py  v1.0  (2026-08-25)
otv4 v3.0  2026-09-20  r395 / GEX.2 — IT STOPS COMPUTING GEX. IT WAS A SECOND
      DEFINITION OF A PRODUCTION QUANTITY AND I GATED IT ONE REVISION AGO
      WITHOUT NOTICING.
      🔴 `data/gex_data.py` is production and has always been authoritative:
        gex_data.py       gamma x oi_proxy x 100 x spot
        this file (v2.0)  gamma x oi       x 100 x spot x spot x 0.01
      The scalar differs by spot/100 (~5.45x on AMD) so SIGN and FLIP LOCATION
      survived, but NET MAGNITUDE was never comparable to production's — and
      the OI differed IN KIND, because production substitutes a SYNTHETIC
      `oi_proxy = max(1, 1000*gamma/mark)` wherever open_interest is 0.
      So a null measured with this file was a claim about MY surface, not
      about the instrument the bot actually trades on. That is the §7 / C.23
      drift this repo keeps finding, in a file whose own v2.0 header said
      "no stub, no proxy".
      🔑 THE FIX IS A DELETION, NOT A REWRITE. `chain_from_snapshot` rebuilds
      an OptionsChain from the warehouse record and hands it to production's
      OWN `compute_gex`. One definition. Verified lossless: `compute_gex`
      reads only gamma, mark, open_interest and strike from a contract, and
      the warehouse carries all four.
      ⚠️ AND THE REPLAY IS EXACT, NOT APPROXIMATE. main.py:4885-4925 feeds the
      SAME `_gex_chain` object to `compute_gex` AND to the snapshot archiver —
      its own comment reads "NO SECOND FETCH ... Same object, one fetch". So
      the warehouse snapshot IS the chain production computed GEX from, and
      feeding it back reproduces production's computation rather than
      resembling it.
      ⚠️ `--proxy-exposure` EXISTS BECAUSE THE PROXY IS A SHAPE CHANGE, NOT A
      CALIBRATION ONE. Where OI is real, GEX is LINEAR in gamma; where it is
      absent, `100000 x gamma^2 x spot / mark` is QUADRATIC. Gamma peaks at
      the money, so the quadratic branch disproportionately amplifies exactly
      the strikes that decide `pin_strike` and `pin_concentration` — and the
      two forms are mixed WITHIN one snapshot, per strike. A single averaged
      disagreement number would bury that as noise, so the exposure is
      reported STRATIFIED BY MONEYNESS. (OTV4TEST's analysis, QQQ-26.)
otv4 v2.0  2026-09-19
otv4 v2.0  2026-09-19  r391 / GEX.1 — 🔴 IT READ A DIRECTORY FROM ANOTHER MACHINE,
      FOUND NOTHING, AND CALLED THE NOTHING A RESULT.
      `ROOT` defaulted to `/home/claude/cc`, which does not exist on control.
      So `snapshots()` globbed an absent tree, returned `[]` in silence, and
      the report printed — verbatim —
        "NO GAMMA FLIP FOUND IN ANY SNAPSHOT — there is no pin on this tape by
         this definition. ... and that is a REAL ANSWER, NOT A MISSING ONE."
      on ZERO loaded snapshots, exit code 0.
      🔑 THAT SENTENCE IS r39 EXACTLY INVERTED. The tool asserted its own
      absence was the tape's answer, which is the one thing r39 forbids, and
      it is the identical failure `exit_replay` carried for its whole life
      (RPL.1: "quote_series needs its first live sessions" printed while the
      quotes sat in the bucket). MEASURED 2026-09-19: `snapshots()` -> 0,
      rc=0, and a confident five-line conclusion underneath it.
      ⚠️ AND IT WAS ABOUT TO BE LOAD-BEARING. The operator's standing prior is
      that gamma or a derivative does the heavy lifting on ORB, so this was
      the instrument his next hypothesis would have leaned on — the third
      ungated analysis tool in one day found returning confident nothing,
      which is [[CHK.8]] measured rather than argued.
      FIX: input comes from the WAREHOUSE through `warehouse_source`, the same
      lineage every other reader uses; an empty load REFUSES BY NAME and exits
      non-zero; and the conclusion block cannot be reached on an empty set.

REAL GEX FROM THE WAREHOUSE CHAINS — no stub, no proxy.

Input: raw/chain_snapshots/dt=<date>/sym=<symbol>/ via warehouse_source.

⚠️ WHAT IS AND IS NOT REAL HERE
  · `gamma` and `oi` ARE POPULATED — verified: 123/222 contracts carry
    non-zero gamma, 159/222 carry non-zero OI (max 7,326). So dealer gamma
    is computable from this data rather than assumed.
  · ⚠️ `vol` IS ZERO ON ALL 222 CONTRACTS. Anything keyed on contract volume
    is DEAD on this payload and must not be silently substituted.
  · ⚠️ THE DEALER SIGN CONVENTION IS AN ASSUMPTION, NOT A MEASUREMENT.
    Standard practice is dealers long calls / short puts, so
    GEX = gamma*OI*(+1 for calls, -1 for puts). That convention is NOT
    verified against this fleet's own definition and the pin location
    depends on it. Marked ⟨ASSUMPTION⟩ everywhere it matters.

GEX per strike = gamma × OI × 100 × spot² × 0.01, signed by the convention
above. The PIN is the strike where cumulative signed gamma flips — the level
dealer hedging pushes price toward.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))


def snapshots(date, symbol):
    """Chain snapshots for one symbol-session, or (None, reason) — NEVER [].

    🔴 THE RETURN CONTRACT IS THE FIX. v1.0 returned a bare list, so "nothing
    was there" and "nothing came back" were the same value and the caller
    could not tell them apart. An empty load now comes back as `None` with a
    NAMED reason, which is the only shape that cannot be mistaken for a tape
    with no pin in it.
    """
    import warehouse_source as ws
    meta = ws.Meta(f"chain_snapshots {date} {symbol}")
    out = []
    try:
        for env in ws._envelopes(ws.client(), "chain_snapshots", [date],
                                 meta, [symbol]):
            r = env.get("record")
            r = json.loads(r) if isinstance(r, str) else r
            if isinstance(r, dict) and r.get("event") == "chain_snapshot":
                out.append(r)
    except Exception as exc:                                    # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    if getattr(meta, "error", None):
        return None, str(meta.error)
    if not out:
        return None, (f"no chain_snapshots for {symbol} on {date} — this is "
                      f"the TOOL's gap, not the tape's (r39)")
    out.sort(key=lambda r: str(r.get("ts_et") or ""))
    return out, ""
    out.sort(key=lambda r: r["ts_et"])
    return out


def chain_from_snapshot(snap):
    """Warehouse chain_snapshot record -> a production OptionsChain.

    🔑 LOSSLESS FOR THIS PURPOSE, AND THAT WAS CHECKED RATHER THAN HOPED:
    `compute_gex` reads only `gamma`, `mark`, `open_interest` and `strike`
    off a contract, and every warehouse row carries all four. Nothing here
    interprets or rescales — it moves fields.
    """
    from data.options_chain import OptionContract, OptionsChain
    spot = float(snap.get("underlying") or 0.0)
    calls, puts = [], []
    for c in snap.get("contracts", []) or []:
        oc = OptionContract(
            symbol=str(c.get("occ") or ""),
            underlying=str(snap.get("symbol") or ""),
            expiry=str(snap.get("expiry") or ""),
            option_type=str(c.get("type") or ""),
            strike=float(c.get("strike") or 0.0),
            bid=float(c.get("bid") or 0.0),
            ask=float(c.get("ask") or 0.0),
            mark=float(c.get("mark") or 0.0),
            delta=float(c.get("delta") or 0.0),
            gamma=float(c.get("gamma") or 0.0),
            theta=float(c.get("theta") or 0.0),
            vega=float(c.get("vega") or 0.0),
            iv=float(c.get("iv") or 0.0),
            open_interest=int(float(c.get("oi") or 0)),
            volume=int(float(c.get("vol") or 0)),
        )
        (calls if oc.option_type == "C" else puts).append(oc)
    return OptionsChain(underlying=str(snap.get("symbol") or ""),
                        expiry=str(snap.get("expiry") or ""),
                        spot_price=spot, calls=calls, puts=puts), spot


def gex_of(snap):
    """Production's OWN GEXSnapshot for a warehouse record. One definition."""
    from data.gex_data import compute_gex
    chain, spot = chain_from_snapshot(snap)
    if spot <= 0 or (not chain.calls and not chain.puts):
        return None, spot
    return compute_gex(chain, spot), spot


def proxy_exposure(snap, buckets=(0.005, 0.01, 0.02, 0.05)):
    """Share of strikes on the QUADRATIC branch, stratified by moneyness.

    🔴 THE STRATIFICATION IS THE POINT. `oi_proxy` fires per contract wherever
    open_interest is 0, and that flips the functional form from linear in
    gamma to quadratic. Gamma peaks ATM, so the quadratic branch amplifies
    the very strikes `pin_strike` and `pin_concentration` are decided on. A
    scalar disagreement rate averages that systematic ATM bias into something
    that looks like noise.
    """
    spot = float(snap.get("underlying") or 0.0)
    if spot <= 0:
        return {}
    out = {}
    for c in snap.get("contracts", []) or []:
        g = float(c.get("gamma") or 0.0)
        if g <= 0:
            continue                      # contributes to neither branch
        m = abs(float(c.get("strike") or 0.0) - spot) / spot
        band = next((f"<={b:.1%}" for b in buckets if m <= b), f">{buckets[-1]:.1%}")
        tot, prox = out.get(band, (0, 0))
        out[band] = (tot + 1, prox + (1 if float(c.get("oi") or 0) <= 0 else 0))
    return out


def pin_from(per, spot):
    # ⚠️ RETAINED ONLY AS A PURE HELPER FOR THE GATE'S SYNTHETIC CASES. It is
    # NOT used to produce any reported number — production's `flip_strike`
    # is. Kept because its "a chain that never flips returns None, not the
    # nearest strike" property is worth pinning somewhere.
    """The strike where cumulative signed gamma crosses zero — the flip.

    ⚠️ If gamma never changes sign the flip does not exist and this returns
    None rather than the nearest strike. A pin that is really 'no pin' is
    exactly the kind of clean-looking wrong answer this project exists to
    prevent."""
    if not per:
        return None, 0.0
    ks = sorted(per)
    cum, prev = 0.0, None
    for k in ks:
        cum += per[k]
        if prev is not None and (prev < 0 <= cum or prev > 0 >= cum):
            return k, cum
        prev = cum
    return None, cum


def run(date: str, symbol: str, mode: str = "gex") -> int:
    snaps, why = snapshots(date, symbol)
    # 🔴 THE REFUSAL COMES FIRST AND EXITS. v1.0 fell straight through an empty
    # list into the conclusion block and declared "no pin on this tape ... a
    # REAL answer, not a missing one" having loaded NOTHING.
    if snaps is None:
        print(f"\n  ⚠️ REFUSED: {why}")
        print("  Nothing is concluded from an empty load — r39: a tool-caused "
              "absence must not wear the costume of a null.")
        return 1

    if mode == "proxy":
        print("=" * 74)
        print(f"  PROXY EXPOSURE — {symbol} {date} · {len(snaps)} snapshot(s)")
        print("=" * 74)
        print("  Share of gamma-bearing strikes on the QUADRATIC branch")
        print("  (open_interest == 0 -> oi_proxy -> 100000*gamma^2*spot/mark)\n")
        agg = {}
        for sn in snaps:
            for band, (tot, prox) in proxy_exposure(sn).items():
                t, p = agg.get(band, (0, 0))
                agg[band] = (t + tot, p + prox)
        order = sorted(agg, key=lambda b: (b.startswith(">"), b))
        for band in order:
            tot, prox = agg[band]
            print(f"    |K-S|/S {band:>8}   {prox:6d} / {tot:6d}   {prox/max(1,tot):6.1%} on the proxy")
        gt, gp = sum(t for t, _ in agg.values()), sum(p for _, p in agg.values())
        print(f"\n    {'ALL':>16}   {gp:6d} / {gt:6d}   {gp/max(1,gt):6.1%}")
        print("\n  ⚠️ A RISING SHARE TOWARD THE MONEY IS THE FINDING, NOT THE TOTAL.")
        print("  Gamma peaks ATM, so proxy strikes there are squared and amplified")
        print("  exactly where pin_strike and pin_concentration are decided.")
        return 0

    print("=" * 74)
    print(f"  {symbol} {date} · {len(snaps)} chain snapshot(s) · expiry "
          f"{snaps[0].get('expiry', '?')}")
    print("  GEX computed by PRODUCTION'S data.gex_data.compute_gex — one definition")
    print("=" * 74)
    print(f"\n  {'TIME':>8}  {'SPOT':>8}  {'PIN':>8}  {'FLIP':>8}  "
          f"{'NET GEX ($M)':>13}  {'ENV':>9}  {'ORB BIAS':>10}")
    rows = []
    for sn in snaps:
        g, spot = gex_of(sn)
        if g is None:
            continue
        rows.append((str(sn.get("ts_et"))[11:16], spot,
                     getattr(g, "pin_strike", 0.0), getattr(g, "flip_strike", 0.0),
                     getattr(g, "net_gex", 0.0) / 1e6,
                     str(getattr(g, "gex_environment", "?")),
                     str(getattr(g, "orb_bias", "?"))))
    for t, spot, pin, flip, net, env, ob in rows[::6]:
        print(f"  {t:>8}  {spot:8.2f}  {pin:8.0f}  {flip:8.0f}  {net:13.1f}  "
              f"{env:>9}  {ob:>10}")
    print(f"\n{'='*74}\n  WHAT THIS SAYS\n{'='*74}")
    if not rows:
        print(f"  NO GEX COMPUTED FROM {len(snaps)} LOADED SNAPSHOT(S) — every one "
              f"had no spot or no contracts.")
        return 0
    import collections as _c
    envs = _c.Counter(r[5] for r in rows)
    bias = _c.Counter(r[6] for r in rows)
    print(f"  environments over {len(rows)} snapshot(s): " +
          ", ".join(f"{k} {v}" for k, v in envs.most_common()))
    print(f"  orb_bias:                       " +
          ", ".join(f"{k} {v}" for k, v in bias.most_common()))
    # 🔑 orb_bias IS WRITTEN BY PRODUCTION AND READ BY NOTHING — grep finds one
    # comment in status.py and no consumer. It is printed here so the label the
    # repo already computes is at least visible to a human.
    print("\n  ⚠️ `orb_bias` is computed by production on every snapshot and is "
          "READ BY NO STRATEGY.\n     It is shown here because an instrument "
          "already on disk and unread is the\n     cheapest thing in the repo.")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-18")
    ap.add_argument("--symbol", default="AMD")
    ap.add_argument("--proxy-exposure", action="store_true",
                    help="share of strikes on the quadratic branch, by moneyness")
    a = ap.parse_args()
    print(__doc__)
    sys.exit(run(a.date, a.symbol, "proxy" if a.proxy_exposure else "gex"))
