# docs/ROADMAP.md — v4.1 — options_trader v4

> 🔴 **SUPERSEDED SNAPSHOT (marked 2026-10-03, OTV4TEST r226).** Kept for the record it is; it does not describe this fork as it runs. Current state: `docs/TRADES.md` §0 (roster), `docs/BACKLOG.md` (work), `docs/GENESIS-TEST.md` (ledger).

**v4.1 — 2026-10-03 — OTV4TEST r226 — bannered as a superseded snapshot; nothing below was changed.**

**Opened 2026-08-19. This is the governing plan.**

**Success is `docs/VISION.md`: dollars, and an edge that survives a measurable
period. Everything below is in service of that and nothing below is a goal in
itself.**

---

## PHASE 0 — SKELETON AND SALVAGE  ⏳ IN PROGRESS

**0.1** Repo skeleton, `WORKING_AGREEMENT.md` carried verbatim, README, VISION,
INHERITED_FINDINGS. ⬜
**0.2** Port the verbatim set — exits, collection, structure/levels, risk,
warehouse, utils, tooling. **Every header reset to 4.0, every changelog fresh.** ⬜
**0.3** Port the shells — all strategies, `main.py`, `entry_engine` — with
**every regime gate and conviction read stripped.** They will not fire until
Phase 2 gives them triggers. ⬜
**0.4** `check_versions.sh` rebuilt for v4 with **behavioural canaries only** —
never version-string pins (a canary that reddens on a legitimate bump teaches
the operator to ignore a red run). ⬜

⚠️ **PHASE 0 ENDS WITH A REPO THAT COLLECTS AND MANAGES BUT DOES NOT ENTER.**
That is deliberate: exits and collection are the proven parts and can run while
entries are still being mined.

---

## PHASE 1 — MINE THE ENTRY CONDITIONS

> **The triggers are MINED, not theorised.**

**1.1** Derive structural features retroactively from banked OHLC at every
historical entry — swing sequence, channel position, whether the last break
held, distance to prior-session extremes, impulse character of the entry bar.
**They need not have been journaled.** ⬜
**1.2** Split favourable vs never-favourable and find where the structure
separates. Same machinery as `separation_probe.py`, pointed at entry conditions
instead of primitives. ⬜
**1.3** ⚠️ **CALLS AND PUTS SEPARATELY.** At 34.2% put accuracy the bearish
entries are close to ANTI-selected — trades taken short when structure said
otherwise. **The never-favourable puts are the sharpest "do not fire" signature
in the data**, and pooling them with calls would blunt it. ⬜
**1.4** Write the cutoff where the distributions actually part. ⬜

**🔵 WHY THE BROKEN CLASSIFIER MAKES THIS SAMPLE GOOD** (operator's point, and
it is the better framing): a 44.9% engine is close to a **random sampler** of
entry conditions. The favourable trades are therefore not "cases where the
engine was right" — they are **cases where the structure was good enough to work
despite it.** The never-favourable set is an equally broad sample of what does
not work.

⚠️ **THE RESIDUAL BIAS, STATED.** The engine still chose WHEN AND WHERE to look,
so coverage is biased even though direction was noise. **A mined bar needs
forward validation before it sizes anything.**

---

## PHASE 2 — WIRE THE TRIGGERS, LOG-ONLY

**2.1** Each strategy gets a structural trigger from Phase 1. ⬜
**2.2** **LOG-ONLY first.** Journal what would have fired and what was refused;
gate nothing. ⬜
**2.3** ⚠️ **THE REFUSALS ARE HALF THE DATA.** `rejection_ledger` carries over
for exactly this — *a bar that only shrinks the book is not confidence, it is
fear.* A trigger is judged on what it declined as much as what it took. ⬜
**2.4** Compare the log-only book against the real one. **Dollars.** ⬜

---

## PHASE 3 — ADVERSARIAL AUDIT, THEN LIVE

**3.1** Once entry criteria exist on paper, request an adversarial audit before
anything trades on them. ⬜
**3.2** Enable entries on the panel. Exits and sizing unchanged. ⬜
**3.3** Measure dollars over a period long enough that variance cannot explain
it. ⬜

---

## PHASE 4 — EARNED LAYERS (not before)

**4.1 Structure-first regime labels.** Vocabulary — in-channel, breakout,
compression, ranging, breakout-volatile, trending — **rebuilt from structure**,
shaped by derived cues. ⚠️ **INFORMS, NEVER AUTHORISES.** Any setup may read
one; no setup may require one. ⬜
**4.2 A scorer, if earned.** From a shadow observer grading entries
post-mortem — **never built ahead of the evidence.** OTV3's was, and A-grade
lost $8,244 at 1.5× size while B made +$1,893. ⬜
**4.3 Sizing on the scorer, if it clears.** Separation with direction ·
selection-clean measurement · window stability · marginal fee-adjusted-ROI
placement. ⬜

---

## ⬜ NEXT ACTIONS — in order, 2026-08-20

**FRI 08-21 — THE FIRE DRILL.** Paper, so a bad day costs information not money.
1. ⬜ Start ONE box, verify, then the other 14. A catastrophic fault gets
   diagnosed once instead of fifteen times.
2. ⬜ **The line that matters most: `ExitEngine.evaluate` reached with a live
   position.** Every exit path was dead code for seven revisions (F0) and the
   fix has only ever been proven by mutation. **The first real stop firing is
   the actual verification.**
3. ⬜ Watch the first chain fetch at 09:30 — the only thing the LLY repoint test
   could not prove.
4. ⬜ Confirm `open_interest` is NON-ZERO in the log. OI.1 landed on v3 and
   collects toward the butterfly's two-week clock; **v4's copy has never run.**
5. ⬜ Watch the first EOD cycle — the v4 pusher is untested.

**MON 08-24 — the session that matters.** Clean, no fires.

**THEN, in rough priority:**
6. ⬜ Relaxed entry on one box, one session. Volume enough to read the logs.
7. ⬜ `orb_bleed_study` against v4 data once `mfe_bars` has values — **the
   grinder stop is the last undefined exit** and a few sessions answer it.
8. ⬜ Trade-frequency measurement → position sizing. ⚠️ **Sizing, never gating:**
   a fleet concurrency gate would censor the sample by arrival order, and WA §29
   makes box independence a feature.
9. ⬜ ~2 weeks of real OI, then `pin_strength.py`, then unpark the butterfly.
   **Its evidence will be structural, not statistical** — it may fire twice a
   month.
10. ⬜ Retire `butterfly_strategy`'s replacement question: while GEX was
    gamma-squared the pin **was** spot, so the two centred identically.
11. ⬜ Measure the real `build_fork_contained`, not the regression stand-in.
    Owed work — the 5%-respected result is why the condor is a nice-to-have.

## STANDING OPERATIONAL WORK

**S.1 Conductor becomes a VERIFIER, not a collector.** Completing the S3 move is
**high priority**. Control remains 1-REPORTER. ⬜
**S.2 All tests and tools live in `/tests`.** Nothing new at repo root; the
existing root sprawl on control migrates. ⬜
**S.3 Bot independence is a FEATURE.** No box may require control to be
reachable in order to trade. ⬜
**S.4 Fleet: 15 boxes. Collection and trading are the SAME SET.** Updated
2026-08-25 — this row previously read "15 traders, 29 collectors / collection is
fleet-wide", which has been false since the 2026-08-20 pare: **the other 14
instances were TERMINATED, not stopped.**

The principle it carried is unchanged and still right: **a box that stops
collecting is a box whose pitchfork and ADX depth quietly dies**, and DXFeed
history is same-evening only, so that depth cannot be recovered afterwards.
Pruning stays disabled so it accumulates.

⚠️ **WHAT THE COUNT CHANGE ACTUALLY COSTS:** the GEX butterfly's unpark depends
on open-interest ACCUMULATION ACROSS THE FLEET. That now runs on 15 symbols,
not 29 — roughly half the breadth, so the accumulation clock is longer than the
original estimate assumed. Do not date the unpark off the old number. ⬜

---

## ⚠️ MIGRATION HAZARD — READ BEFORE ANY RE-FLASH

*"Overwrite execution and regime engines; historical data must not be deleted."*
**On the boxes those live in the same tree.** `~/options-trader/data/feed_store.db`
holds the candle and chain-mark depth that pitchfork and ADX warm-up depend on,
and a re-flash that replaces the repo directory wholesale takes it with it.

**Pruning was disabled (OTV3 FEED.3) specifically so that depth accumulates, and
DXFeed history is same-evening only.** Verify per box **BEFORE** the flash, not
after — the 2026-08-03 loss was 38-byte files nobody noticed for days.

**QQQ is out of scope** — it runs SMC exploration and must not be repointed with
the rest.
