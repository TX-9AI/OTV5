# FEED_MANIFOLD.md — THE FUEL MANIFOLD
**otv4 · created 2026-08-22 · ESSENTIAL READING, same standing as
WORKING_AGREEMENT.md and TRADES.md.**

The operator's framing for this repo is a tank: bellcranks and cables, nothing
fly-by-wire. **This document is the fuel manifold.** One inlet, fixed ports,
every port plumbed whether or not anything is currently drinking from it.

---

## THE GOVERNING RULE

> **STOP DISCARDING INFORMATION.**
> Operator, 2026-08-22, stated repeatedly and without qualification.

**Capture everything the wire offers. Give each artifact a home. Consumers
subscribe to homes.** Storage is cheap. Nothing is dropped, nothing is
overwritten, nothing is captured conditionally.

If a strategy can benefit from anything derivable from feed data, we compute it.
The feed's job is to make that possible; it is not the feed's job to decide what
is interesting.

### Why this is the class fix, not a preference

Operator's own diagnosis of this repo's history, and it is confirmed in the code:

> every incremental fix "had to do with unlocking one feed store artifact at a
> time until something started working, where we should have started with
> subscribe to everything, find a place for it, and then if we need it, it's
> there."

FEED.2 unlocked extended 1h **because LIQ.6 starved**. OI.1 unlocked open
interest **because GEX starved**. `EXT_1H_ENABLED` is still behind a flag. Every
unlock shipped scoped to the one consumer that noticed it was hungry.

That is why the same failure recurs: **capture-on-demand means every new
consumer starts life reading something that is not there, and declines politely
instead of erroring.** Five blockers in three days, every one that silhouette.

**A consumer cannot starve on data that was never conditional.**

---

## SCOPE: THE MANIFOLD IS PER BOX

There is no shared store. Each box runs its own `candle-feed` process, holding
its own DXLink socket, writing its own `feed_store.db`. **There are fifteen
manifolds, identical in shape**, each fed by one instrument plus VIX.

The contract is therefore per box: **on any given box, every consumer running
there gets every port it declares.** A port that fails, fails on that box only —
the feed already does this per-subscription (`SUBSCRIBE FAILED … continuing
without it`), so an entitlement gap costs one port on one box and is named.

⚠️ **S3 IS DOWNSTREAM OF THE MANIFOLD, NOT PART OF IT.** The manifold's job ends
at the box's store; the pusher ships it afterwards. This is why the VIX rule
below is a PUSH rule and not a CAPTURE rule.

---

## PORT MAP

Homes are tables in `feed_store.db`, keyed `(symbol, ts)` — **append, never
overwrite**.

| port | event | home | notes |
|---|---|---|---|
| `candles.rth` | Candle ×5 tenors | `SYM` / interval | 1d 1h 15m 5m 1m |
| `candles.ext` | Candle ×5 tenors | `SYM_EXT` / interval | all five, not just 1h |
| `candles.vix` | Candle ×5 tenors | `VIX` / interval | parity with equities |
| `greeks.live` | Greeks | `chain_marks` | current value, fast read — KEEP |
| `greeks.series` | Greeks | `greeks_series` | **ALL 13 FIELDS**, append |
| `quotes.live` | Quote | `chain_marks` | current value — KEEP |
| `quotes.series` | Quote | `quote_series` | **ALL 12 FIELDS**, incl. sizes |
| `prints` | TimeAndSale | `prints` | not subscribed (08-22) — **SUBSCRIBED on OTV4TEST** (r250, measured 2026-10-04 on QQQ-TEST's feed_store: 257,143 rows, newest 10-05 00:34 UTC; the 08-22 'not subscribed' was stale) |
| `last_trade` | Trade | `last_trade` | not subscribed (08-22) — **SUBSCRIBED on OTV4TEST** (r250, measured 2026-10-04 on QQQ-TEST's feed_store: 52,492 rows, newest 10-05 00:34 UTC; the 08-22 'not subscribed' was stale) |
| `session_summary` | Summary | `session_summary` | not subscribed (08-22) — **SUBSCRIBED on OTV4TEST** (r250, measured 2026-10-04 on QQQ-TEST's feed_store: 213 rows, newest 10-05 00:00 UTC; the 08-22 'not subscribed' was stale) |
| `underlying` | Underlying | `underlying` | not currently subscribed |
| `theo` | TheoPrice | `theo` | not currently subscribed |
| `open_interest` | REST daily | chain rows | correct as REST, once/day |

`chain_marks` is unchanged and stays the tick loop's fast path. The series
tables are **additive** — no existing consumer moves. That is FEED.2's lesson
applied deliberately instead of after the fact.

### What was being thrown away before this document existed

- **Four of five tenors had no extended twin.** Only 1h, behind a flag.
- **VIX ran at 2 of 5 tenors.**
- **`chain_marks` was PRIMARY KEY (streamer_symbol)** — last-write-wins. ~250
  chain symbols ticking all session, each overwriting one row. **The entire
  intraday evolution of the greek surface was captured and destroyed.**
- **Fields dropped inside events already received:** Greeks 13 → 7 (lost
  `price`, `volatility`, `rho`, `sequence`, `index`, `time`); Quote 12 → 2
  (lost **`bid_size`**, **`ask_size`**, exchange codes, timestamps).

---

## DEDUPLICATION

Traced `candle_feed.py:551–581`: each box subscribes **its own instrument plus
VIX**, nothing else. Exactly one fleet-wide duplicate exists.

| symbol | captured on | pushed to S3 by |
|---|---|---|
| own instrument | that box | that box |
| **VIX** | **all 15 boxes** | **SPX only** |

VIX is captured everywhere — macro, `vol_state` and the crisis lockout all read
it in-process — and published once. Before this rule, Friday shipped 72 VIX 1m
objects from every box: ~14 redundant copies per tenor per day.

**No other duplicate exists.** SPX/QQQ/SPY appear elsewhere in `selector` and
`macro` config, not in any box's subscription list. QQQ and SPX are both panel
members and both broad-index proxies, but they are different underlyings — not
redundant capture.

---

## WHAT FULL CAPTURE MAKES POSSIBLE

None of these are computable today. All fall straight out of the series tables.

### 🔴 CHARM and VANNA — operator: "absolutely indispensable"
Both are second-order and both are derivatives of **delta over a series**:

- **charm = dDelta/dt** — how delta decays as expiry approaches
- **vanna = dDelta/dVol** — how delta moves as IV moves

`chain_marks` overwrites one row per symbol, so **neither is computable at all
right now.** With `greeks_series` keeping `delta`, `volatility` and `time` per
strike per tick, both are a finite difference over the series.

⚠️ **For 0DTE this is not an enhancement, it is the afternoon.** Charm dominates
the last hours of an expiring contract — it is the mechanism behind pin. A
0DTE book that cannot compute charm is asserting pin risk rather than measuring
it. **Strategies should rely on these where they can derive them.**

### IV surface and its evolution
`Greeks.volatility` is dropped today. Kept per strike per tick it gives the
smile AND its trajectory — the butterfly reads a single `atm_iv` scalar now and
cannot tell a steepening smile from a flattening one.

### True friction, from depth
`Quote.bid_size`/`ask_size` are dropped. FRC.1 concluded the fleet's gross edge
is ~2% of its own round-trip spread — computed **from spread width alone, blind
to size at the touch.** A 0.05 spread with 400 bid is a different market from
the same spread with 3.

### Dealer positioning as a trajectory
GEX is recomputed each cycle from the current snapshot. With a greeks series,
gamma **flow** is measurable — where the wall built and when it moved.
`orb=AMPLIFYING/DAMPENING` becomes a measured path instead of a per-tick label.

---

## THE CONTRACT

Every consumer declares the ports it requires. **A missing required port is an
ERROR, not a decline.**

This is the rule that ends the class. Friday's zero-trade session was five
consumers reading things that were not there and each one standing down in a way
that read as correct behaviour:

| what was missing | how it presented |
|---|---|
| intraday tape (`_is_ext_of` inverted) | "BOT IS BLIND" once, then silence |
| dispatch (regime hard gate) | "NO TRADE — regime UNKNOWN" |
| condor rails (`daily` vs `1d`) | "no usable daily pitchfork (rails=absent)" |
| condor rails (**1d absent from the feed**) | identical message |
| TC.6 (`OT_TCS_ACTIVE` default 0) | **nothing at all** |

⚠️ **Every one of those was a correct-looking refusal.** That is why the contract
must raise: a decline and a starvation are indistinguishable in a log, and this
repo has now paid for that five times in three days.

---

## THE INSTRUMENT

One command, fleet-wide through devtools, printing per box and per port:
row count, newest timestamp, freshness. **"Is the fire hose connected" must be
answerable in five seconds.**

On Friday 2026-08-21 the intraday tape was dead from 09:30 and nothing said so
until the operator went looking at 09:31 — and then the single alert went quiet
because the blind latch pages once per outage.

---

## OPEN — decide before build

⬜ **Should a box refuse to trade when a required port is missing?** A condor
with no `1d` erroring rather than logging NO PLAN is my instinct, but it is a
decision about what trades and belongs to the operator.

⬜ **Write volume**, measured on ONE box before fleet-wide. Greeks+Quote series
at ~250 chain symbols × 15s is tens of thousands of rows/hour on a t2.micro with
SQLite. Probably fine. "Probably" is what has been wrong all weekend.

⬜ **Helper scripts not yet traced** — `structure_analyzer`, `liquidity_mapper`,
`pitchfork`, `gap_measure`, `entry_snapshot`, `trade_readiness` each read frames
directly. Strategies are traced (see `ENGINE_FEED_REQUIREMENTS.md`); the helpers
are the next pass.
