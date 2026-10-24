# DERIVED_STORES.md — WHAT GETS A HOME, AND WHY
**otv4 · 2026-08-22 · ESSENTIAL READING. Companion to `FEED_MANIFOLD.md`.**
**Every derived value in the tree, tested against one rule.**

---

## THE RULE

> **Anything whose value depends on HISTORY rather than only on the current bar
> gets a home. Everything else is computed on demand.**

The test is not "is it expensive." It is **"would a consumer rather read this
than recompute it, because recomputation gives a DIFFERENT ANSWER?"**

That difference is the whole point. A value that recomputes identically every
time loses nothing by being derived on the fly. A value that depends on where
its window started, or on state accumulated across bars, is a **different
number** depending on when you ask — and that difference is invisible, which
makes it the most dangerous kind of wrong this repo produces.

⚠️ **DERIVERS ARE CONTRIBUTORS, NEVER GATES.** Operator's ruling, 2026-08-22.
Derived values INFORM; they never authorise. **A missing DERIVED port is NOT a
contract error** — the engine trades without it. Only RAW ports can be hard
requirements. This is the rule the regime labels violated.

---

## TIER 1 — PATH-DEPENDENT (recomputation is not idempotent)

| value | source | why it needs a home |
|---|---|---|
| **ADX** (`primary_adx`, per-tf `adx`) | trend_engine | Wilder smoothing — each value depends on the PREVIOUS one, recursively. Recomputed from a 100-bar window it converges to *roughly* the right answer, and "roughly" depends on where the window started. |
| **ATR** (`atr_current`, `atr_normalized`, `atr_avg_20`) | volatility_engine | Same Wilder recursion, milder. |
| **VWAP** (+ `price_vs_vwap`) | volatility_engine | **The strongest case in the document.** Cumulative Σ(p·v)/Σ(v) from a FIXED anchor. A VWAP anchored to a rolling frame instead of the session open is still a smooth line near price — **nothing about it looks broken.** Store the ACCUMULATORS (Σpv, Σv) with the anchor, not just the value. |
| **EMAs** (`ema_fast/mid/slow/anchor`) | trend_engine | Exponential — every value carries the entire prior series with decaying weight. Window start shifts the level. |

🔴 **EVIDENCE THIS IS NOT THEORETICAL.** Friday's rejection logs show ADX
swinging **16 → 48** on the same symbols across ticks. Some of that is real
market movement. **Some may be window artifact, and there is currently no way
to tell** — nothing keeps the series to compare against. `adx_at_entry` is a
column on every trade and `CONT_BREAKOUT_MIN_ADX` is a live gate, so if there is
a recompute wobble, both the gate and the study are contaminated by it.

⚠️ VWAP has a scar: the **VW.1 saga, five wrong layers**, existed because VWAP
orientation was RECONSTRUCTED after the fact instead of recorded when it
happened. Storing the series turns that class of investigation into a lookup.

---

## TIER 2 — REGRESSIVE / EXPENSIVE (scans backward, dies on restart)

| value | source | why |
|---|---|---|
| **Pitchfork forks** (anchors P0/P1/P2, slope, containment share, span) | pitchfork_observer | Reaches back 60–80 bars to find anchors. Lives in a **process-resident `_cache`** — dies on every deploy. |
| **Fork REJECTION reasons** | pitchfork | 🔴 Six named reasons exist — `FRAME_TOO_SHORT`, `NOT_ANCHOR_TF`, `NO_ATR`, `NO_CONTAINED_WINDOW`, `RECENCY`, `SEPARATION` — and **none reaches storage or a log.** "No usable fork" is one undifferentiated message covering six different problems. This is why the r59 diagnosis took two wrong turns. |
| **Swing highs/lows, S/R levels, FVGs, order blocks** | structure_analyzer | Scans the frame each tick; the objects have identity that recomputation discards. |

⚠️ Storing the fork means a deploy can no longer erase a live anchor —
the same failure class as the 10:39 restart wiping confirmed ORB setups.

---

## TIER 3 — STATEFUL / LIFECYCLE (the object has a biography)

> **OTV4TEST NOTE (r250, 2026-10-04):** this fork's liquidity mapper is the **LEVEL BOOK** - the operator's LVL.15 redesign (r110-r126): `derived/levels.py` (the engine) + `derived/level_book.py` + `derived/level_rules.py`, recording to `level_ledger`. It REPLACED mainline's `analysis/liquidity_mapper.py`, which r123 stopped running and r126 deleted. Rows below naming `liquidity_mapper` describe mainline; here the same jobs are the level book's, under his 2026-10-01/10-03 definitions (a sweep is a defence; a lone level flips S/R; defences and failures counted, r214).

| value | source | why |
|---|---|---|
| **Liquidity pools** — `touch_count`, `swept`, `swept_index`, `rejection_confirmed`, `is_named` | liquidity_mapper | A pool is created, held n times, broken, done. **Recomputing from a rolling window reconstructs that history rather than recording it** — and a pool whose first touches aged out comes back UNDERSTATED. That biases systematically against the OLDEST levels, which are the strongest ones. |
| **Sweeps** — `closes_beyond`, `reclaimed`, `invalidated`, `bars_ago`, `closes_beyond_live` | liquidity_mapper | Sweep state evolves after the sweep. LIQ.3 recomputes invalidation every tick and that running value is correct — but it is not KEPT. |
| **ORB state** — `state`, `confirmed_at`, `attempt_number`, `invalidation_reason`, `entries_expired` | orb_engine | 🔴 The 10:39 restart on 2026-08-21 **erased in-process ORB confirmation on CRM/GOOGL/UNH/SPX**, all of which had confirmed break+retest and none of which traded. v3's `orb_state.json` write-only lesson, recurring. |
| **Named session levels** — prev-day, Asia, London, NY high/low | liquidity_mapper | Once a session closes these are FACTS. Recomputing every tick is waste; worse, LIQ.6's Asia/London sections were empty for a week and it read as zero rather than missing. |

### 🔴 THE LEVEL LIFECYCLE — operator's ruling, 2026-08-22

> "In a live session a touch count is a held level, and when it doesn't hold,
> that level is finished."

A touch is a **hold**. Touch count is the length of a run that TERMINATES at
the break — not a score that accumulates forever.

⚠️ **THE CODE DOES NOT MODEL THIS YET.** `touch_count` and `swept` are separate
fields, so a pool can read five-touch AND swept simultaneously — the count
survives its own invalidation. Under the ruling the level is finished at the
break and its five touches are history.

⚠️ **NY IS THE DANGEROUS SESSION and the operator has been bitten by it.** It is
the only session that is LIVE while being traded — Asia and London are closed
and final by the time an RTH box reads them. So "store once at session close" is
wrong for NY. The resolution is the operator's own framing: **do not read
session fields at all.** Walk outward from current price and report the first
level each way WITH ITS PROVENANCE. The session becomes a LABEL ON THE ANSWER,
not the query — and a still-forming NY high that is nearest above genuinely IS
the level that matters, because that is where the stops are.

Levels are ordered by DISTANCE and scored by TOUCH COUNT. The nearest level may
be a one-touch artifact while the one 0.4% beyond has held five times — that is
the whole distinction between trading into something and trading into noise.

**VWAP is a level too** and belongs in the same ordered walk, with its own
provenance label.

---

## TIER 4 — MULTI-SOURCE SECOND-ORDER (impossible without a series)

| value | needs | why |
|---|---|---|
| **CHARM** = dDelta/dt | greeks_series | 🔴 **Operator: "absolutely indispensable."** For 0DTE, charm dominates the afternoon — it is the mechanism behind pin. A 0DTE book that cannot compute charm is ASSERTING pin risk rather than measuring it. |
| **VANNA** = dDelta/dVol | greeks_series | Same class. |
| **GEX / gamma flow** | greeks_series + OI | GEX is recomputed each cycle from the CURRENT snapshot. With a series, gamma **flow** is measurable — where the wall built and when it moved. `orb=AMPLIFYING/DAMPENING` becomes a measured trajectory instead of a per-tick label. |
| **IV surface & skew** | greeks_series (`volatility`) | The butterfly reads a single `atm_iv` scalar and cannot tell a steepening smile from a flattening one. |
| **Depth-aware friction** | quote_series (`bid_size`/`ask_size`) | FRC.1 concluded gross edge is ~2% of round-trip spread — computed from spread WIDTH alone. A 0.05 spread with 400 bid is a different market from the same spread with 3. |

⚠️ **CHARM, VANNA AND GEX ARE UNIVERSAL PORTS** — operator: they must contribute
to every strategy where they could meaningfully contribute. So they are
assembled ONCE in the manifold and offered to all engines, not computed
per-strategy.

---

## NOT STORED — computed on demand

These are pure functions of the current bar or of values already at hand. They
fail the rule and storing them would be noise:

`price` · `price_vs_ema_fast` · `price_vs_bb` · `bb_upper/middle/lower`
(a window function, idempotent) · `is_trending` / `is_bullish` / `is_bearish`
(thresholds over stored ADX) · `is_compressing` / `is_expanding` · `orb_width`
(arithmetic on stored highs/lows) · `stop_atr_distance` (multiple of stored ATR)
· the **level walk itself** — sorting stored levels by distance from current
price is cheap and correct every time.

⚠️ Note the pattern: **the derived STATE is stored; the COMPARISON against
current price is not.** `nearest_sr_distance_pct` changes every tick for reasons
that have nothing to do with the level.

---

## UNIVERSAL CONVENTION — BODIES DECIDE, WICKS TEST

**Operator's ruling, 2026-08-22: the sweep rules apply universally to candles,
wicks and bodies. This is the basis of all his conditions.**

Source is `liquidity_mapper` (mainline; in this fork, the LEVEL BOOK - see the TIER 3 note) and its doctrine is explicit:

> `closes_beyond >= ACCEPT_CLOSES` is no longer a sweep — **it is a breakout.**

- A **wick** through a level is a TEST.
- A **close** through a level is ACCEPTANCE.

⚠️ **THIS IS MEASURED, NOT ASSUMED.** `closes_beyond >= 2` blocked **64.5% of
named-pool sweeps** (measured 2026-08-15). Applying it elsewhere inherits a
tuned number instead of inventing one.

⚠️ **IT ALREADY FIXED THIS EXACT DEFECT ONCE.** The old `rejection_pct` measured
wick-to-last-close and **stamped a breakout as a confirmed sweep** — precisely
the error a wick-based rule produces.

### Settled vs live

A level's status is final only **at bar close**. Intra-bar, price can be beyond
a level and return. The sweep code models this with `closes_beyond_live` —
recomputed each tick and explicitly named "live."

**Generalise it: any derived state may expose a running value, but it must be
LABELLED as provisional.** Same discipline as the NY session — the honest
version is the one that says which it is.

---

## OPEN

⬜ **Does a broken level become support on retest?** Classic flip. If yes, the
level is not finished at the break — it is TRANSFORMED, and the store records
the flip rather than closing the record. Operator's call; not yet ruled.

⬜ **Write volume** for the greeks/quote series, measured on ONE box before
fleet-wide.

⬜ **`trade_readiness` and `entry_snapshot`** not yet traced for their own
derived dependencies.
