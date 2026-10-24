# ENGINE_FEED_REQUIREMENTS.md — WHAT EACH ENGINE EATS
**otv4 · 2026-08-22 · ESSENTIAL READING.**
**Traced from signatures and dispatch call sites, not inferred.**
**Consumer half of `docs/FEED_MANIFOLD.md` — read that first.**

⚠️ THIS TABLE IS THE CONTRACT'S SOURCE. When a strategy's inputs change, this
file changes in the same commit. A signature that drifts from this table is how
a consumer starts reading something nobody guaranteed.

---

## 1 — DEDUPLICATION: what every box pulls that isn't its own symbol

Traced `candle_feed.py:551–581`. Each box subscribes **its own instrument plus
VIX**, and nothing else. There is exactly one fleet-wide duplicate.

| symbol | scope | S3 publisher |
|---|---|---|
| own instrument | that box only | that box |
| **VIX** | **all 15 boxes** | **SPX only** ← operator's call |

**VIX stays local on every box** (macro, vol_state and the crisis lockout all
read it in-process) **and only SPX pushes it.** Friday's `candles` count carried
72 VIX 1m objects from every box — ~14 redundant copies per tenor per day.

**No other duplicate exists.** SPX/QQQ/SPY appear elsewhere in the tree but in
`selector`/`macro` config, not in any box's subscription list. QQQ and SPX are
both panel members and both broad-index proxies, but they are different
underlyings — not redundant capture, so both stay.

---

## 2 — ENGINE REQUIREMENTS (exact parameter lists)

| engine | signature | feed artifacts behind those params |
|---|---|---|
| **ORB** | `orb, regime, vol_state, liq_map, chain, macro, current_price` | 5m+1m (range), 5m+1h (vol), 5m+15m (liq), chain+greeks+**OI**, VIX |
| **Runaway** | `orb, atr_pct, price_now, prev_close, now_et, chain` | 5m, **1d (prev_close)**, chain |
| **Condor** | `plan()` / `check_leg_triggers(regime, chain, current_price)` | **1d → daily pitchfork rails**, chain |
| **Butterfly** | `gex, price_now, now_et, atm_iv, chain` | chain + greeks + **OI** → GEX, **atm_iv** |
| **Sweep** | `liq_map, price_now, now_et, atr_pct, chain` | 5m+15m (liq), 5m (atr), chain |
| **TC.6** | `regime, vol_state, chain, macro, current_price, trend, orb_high/low, session_high/low, condor_active, now_et` | 5m+1h, chain, VIX, trend (all tenors), 5m |

### 🔴 Findings from the trace

**`regime` is still a live parameter on three engines** — ORB, TC.6 and the
condor's `check_leg_triggers` — after r57/r58 stripped it of meaning. It now
carries a `MarketState` with no label. **Dead parameter, live signature.** It
should be replaced by the measurements those engines actually want (`trend`,
`vol_state`) rather than left as a hollow object that looks like an input.

**`prev_close` requires 1d.** Runaway takes it as a scalar, so its 1d
dependency is invisible at the call site — and **1d was absent from S3 on
Friday**. Same silent-dependency shape as the condor's rails.

**`atm_iv` is a scalar derived from the chain.** With greeks history it becomes
a *series* — see §3.

**Every engine needs `chain`.** And `ctx["chain"]` is written at `main.py:2746`
**inside the dispatch path**, so its availability depends on where in the tick
you stand. That is the single highest-value manifold fix on the consumer side.

---

## 3 — WHERE FULL CAPTURE GIVES A BETTER DATASET

Operator asked to be told when a captured-everything design beats what the
engines use today. Four cases, all currently impossible:

**IV term structure and skew, live.** `Greeks.volatility` is dropped today.
Keeping it per strike per tick gives the smile and its *evolution*. Butterfly
uses a single `atm_iv` scalar; with the series it can see whether the smile is
steepening into the pin or flattening away from it.

**True friction from depth.** `Quote.bid_size`/`ask_size` are dropped. FRC.1
concluded the fleet's gross edge is ~2% of its own round-trip spread — computed
from spread width alone, with **no size at the touch**. A 0.05 spread with 400
contracts bid is a different market from the same spread with 3, and every
friction number so far has been blind to the difference.

**🔴 CHARM and VANNA — operator: "absolutely indispensable".** Both are
second-order derivatives of delta OVER A SERIES: charm = dDelta/dt, vanna =
dDelta/dVol. `chain_marks` overwrites one row per symbol, so **neither is
computable at all today.** With `greeks_series` keeping `delta`, `volatility`
and `time` per strike per tick, both are a finite difference.
⚠️ For 0DTE this is not an enhancement, it is the afternoon — charm is the
mechanism behind pin. A 0DTE book that cannot compute charm is ASSERTING pin
risk rather than measuring it. Strategies should rely on both where derivable.

**Real dealer positioning through the day.** GEX is recomputed each cycle from
the *current* snapshot. With a greeks series, gamma *flow* is measurable — where
the wall built, when it moved. `orb=AMPLIFYING/DAMPENING` becomes a measured
trajectory instead of a per-tick label.

---

## 4 — DESIGN CHANGES WORTH MAKING NOW

Nothing traded Friday, so the sample is not corrupted by changing these.

1. **Drop `regime` from all three signatures**, pass `trend`/`vol_state`.
2. **Make `prev_close` an explicit 1d dependency**, not a bare scalar.
3. **Assemble `chain` and `gex` in `assemble_market_state`**, once, like
   everything else — not mid-dispatch.
4. **`atm_iv` → `iv_surface`**, so the butterfly can read the smile.

⬜ **Still owed:** helper scripts (`analysis/*`) have not been traced for their
feed needs — only strategies. `structure_analyzer`, `liquidity_mapper`,
`pitchfork`, `gap_measure`, `entry_snapshot` and `trade_readiness` each read
frames directly and are the next pass.
