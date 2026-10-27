"""
derived/levels.py  v5.8
v5.8  2026-10-27  OTV5 r44 (BAR.1) — THE BOOK'S BAR KEY AND THE RAIL JUDGEMENT USE THE LAST BAR CLOSED BY TIME. Both read
      d1.index[-2] / d1.iloc[-2], one bar stale on a tick before the new minute's first row exists (META 2026-10-27 3f2b1372: a Breakout short fired 10:10:00 ET on the 10:08 bar while 10:09 had already closed back inside the 623.20 edge). They read
      utils.time_utils.closed_pos(d1, time.time()); unchanged when the forming row is present. GATE
      tests/check_last_closed_bar.py.
v5.7  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ... (v5.0 was already spent by this file's own history, so the reset lands at v5.7.)
v6.10  2026-10-24  CD.2 — EVERY PUBLISHED EVENT CARRIES ITS MARKET TIME (level_event.bar_close_epoch = the judging
      bar's start + its span: 60 s for a 1m judgement, 3600 s for "1h"), so latest_event() judges by the bar, not by
      when the row was written. The RAIL path had no market-age check at write: after a restart or with a stalled
      df_1m it could publish an old bar's REJECTED stamped now. It now skips a bar that closed more than BOOK_FRESH_S
      ago, the same rule the book path already keeps. AND THE BOARD FAILS CLOSED UNTIL THE BOOK HAS SYNCED: board()
      serves ledger levels only when derived_store.level_sync says the book was synced against a closed 1m bar that
      closed within BOARD_SYNC_MAX_AGE_S (180 s); otherwise state="not_synced" with empty lists. Before the first sync,
      after "no tape" or after a failed sync, the ledger holds yesterday's (or a seeded box's) live levels, and every
      level-trading plan read them as candidates. The operator, 2026-10-24: fail closed, approved.
v6.9  2026-10-18  OTV4TEST r296 (LVL.19) — THE BOOK REPLAYS CLOSED BARS ONLY. _book_sync fed build() every 1m/1h bar in
      the store, the forming minute included (the feed flushes it within 2 s), and level_rules decided HELD on that
      provisional close; _book_emitted then kept the verdict for good. Audit 2026-10-18 H1: 10 of the 40 newest
      REJECTED/FLIP_REJECTED rows were judged 12-19 s into their bar with a close that differs from the final one.
      Now a 1m bar counts once ts+60 s <= now, an hourly once ts+3600 s <= now, and build() receives now_ms.
v6.8  2026-10-03  OTV4TEST r214 (LVL.18) — A LEVEL'S DEFENCES AND FAILURES ARE COUNTED, RECORD-ONLY, IN NEW COLUMNS. The
      operator, 2026-10-03: "a sweep of a level is a successful defense. and any level that historically
      repeats that process is a higher quality level", and "I would much rather have fewer levels if they're
      higher quality". `_book_sync` now writes, per level, defended_count (the book's HELD events: price
      went to or through it and closed back), failed_count (BREACHED), tested_count and last_defended_ts
      over the tape the book reads. NEW columns, added here by ALTER: touch_count / closes_beyond stay
      untouched (they have readers; the 10-03 audit B6 found them hard-coded 0 since r126), so NO plan,
      board or strategy sees these numbers until he rules one should. A zone's event credits every member.
v6.7  2026-10-01  OTV4TEST FLIP.1 — THE BOOK'S FLIPPED LEVELS ARE RECORDED, AND NO PLAN
      SEES ONE. `_book_sync` writes each flip to `level_ledger` ONCE, live or
      already retired (one that flipped and broke again between two syncs, or
      while the bot was down, is still recorded): kind 'flip_support' /
      'flip_resistance', provenance 'flip', timeframe 'flip_of:<the level it
      came from>', created at the flip bar; its second break or the opening
      range retires it BREACHED / TRAVERSED. The original keeps its BREACHED,
      as before. Its events go to `level_event` as FLIPPED, FLIP_REJECTED and
      FLIP_ACCEPTED with kind flip_*. 🔑 WHY THAT IS RECORD-ONLY, MEASURED:
      board(), walk() and live_levels() all filter kind IN ('support',
      'resistance'), and every plan's trigger asks latest_event() for
      REJECTED/ACCEPTED BY NAME — so no reader a plan trades on can return a
      flip. Making one tradeable is a later ruling (break-and-retest, designed
      2026-10-03). tests/check_level_flip.py F8-F12.
v6.6  2026-09-23  OTV4TEST r126 - THE LEGACY LEVEL PATH IS DELETED (LVL.15 step 5,
      the operator: "Yes, for sure" / "Yep, delete"). `derive()` publishes the
      book, and nothing else: the LEVEL_SOURCE switch, the legacy body of
      derive(), `_sources`, `_tape_sources`, `_reconcile`, `_derive_events`,
      `_walked`, `split_rails`, `pd_ts`, the legacy-only constants
      (TOUCH_TOL_PCT, ACCEPT_CLOSES, CLOSES_BACK, EXCURSION_MAX_BARS) and nine
      engine attributes only they touched are removed. Found by a reachability
      pass from the live roots (the book sync, the rails, board/tines_now/
      rail_projection/walk and the module functions other files import), not
      by reading: 21 functions are live, 7 were not. SHALLOW/DEEP_PIERCE_PCT
      stay - the book and rail syncs read them. derived/level_map.py, which
      only this path still imported, is deleted with it.
v6.5  2026-09-23  OTV4TEST r124 - THE BOARD NO LONGER READS derived/level_map
      (LVL.15 step 5). `board()` grouped the book's levels into zones with
      `level_map.zone_width(self._tape)`, `level_map.zones` and `level_map.walk`,
      measuring the width from `ctx["level_tape"]` (main.py's hourly tape read).
      The SAME width is now taken from the book `_book_sync` builds every closed
      bar (`book.width`: level_book.zone_width over the same SYM+SYM_EXT hourly
      bars - MEASURED EQUAL on the live store, 828 bars, 0.5600 both), and the
      two dict-based helpers are MOVED here verbatim as `_zones`/`_walk`, so the
      board runs the same code on the same numbers. level_map is left to the
      legacy path alone, which r125 deletes with it.
v6.4  2026-09-23  OTV4TEST r116 - the rails are read at the CURRENT minute:
      `tines_now` adds the fraction of the forming hour elapsed (from the
      ForkEngine's `last_bar_start`) to the bar index; the fork's life is the
      builder's containment test alone (forks v4.4).
v6.3  2026-09-23  OTV4TEST r115 - A FORK'S DEATH BELONGS TO ITS BUILDER. r114 judged
      rail breaches HERE and kept a private dead-set, while the ForkEngine went on
      serving the same fork to every other reader. Operator: "it's gone when the
      engine says it's gone, not when a strategy says it's gone." The breach
      judgement, the dead-set, the INVALIDATED record and the restart restore all
      moved to derived/forks.py v4.3; this engine keeps only the TOUCHES (HELD ->
      REJECTED for the sweep) and reads the fork's identity from
      forks.fork_identity, the one definition.
v6.2  2026-09-23  OTV4TEST r114 - THE RAILS ON THE OPERATOR'S DEFINITIONS. "Any
      interaction that doesn't cause the fork object to destruct is a touch. A
      breech is an event that invalidates the fork." The book path's rails no
      longer run the old _derive_events tine branch (0.15% close tolerance,
      depth-graded WICKED/REJECTED); `_rails_sync` judges each rail with
      level_rules at the rail's price on the closed bar's own minute: HELD ->
      REJECTED on the rail id (a legitimate sweep point, softer than a level);
      BREACHED -> the fork's identity is INVALIDATED, `tines_now` serves nothing
      for it again (board, projection, anchors all read "absent"), and the
      INVALIDATED row carries the identity so a restart cannot resurrect it (§22).
      AND `_fork_key` IS NOW THE ANCHORS' PRICES + KINDS: `idx` is a position in
      the rolling frame and shifted every bar (one fork wore 17 keys 09-09..09-14),
      so r19's identity fired hourly on the same fork (R7 pins it).
Owns `level_ledger` and `level_event`. Tier 3 — stateful; the object has a biography.
v6.1  2026-09-23  OTV4TEST r111 — the two rulings reach the engine: LEVEL_SPIKE_REJECT
      now defaults to level_book.SPIKE_REJECT_USD ($1.00, ON; one number, config
      key LEVEL_SPIKE_REJECT overrides), and a level the book retired inside the
      day's opening range is retired TRAVERSED in the ledger, never BREACHED (E8).
v6.0  2026-09-23  LVL.15 STEP 2 — THE LEVEL BOOK IS THE SOURCE. With
      LEVEL_SOURCE "book" (the default) `derive()` stops computing levels and
      events itself: once per CLOSED 1m bar it rebuilds `derived/level_book`
      from the feed store's 1h+1m tape and PUBLISHES it — the ledger holds
      exactly the book's live levels (old rows retire NOT_A_LEVEL, breached
      ones BREACHED), HELD is written as REJECTED with the episode's deepest
      pierce (r44), BREACHED as ACCEPTED. The plans read the same two tables
      and are unchanged (step 3 retargets them). The old 0.15% close
      tolerance, ACCEPT_CLOSES count, opening-range TRAVERSED rule and zone-
      containing-spot retirement do not run on this path: the operator's
      definitions replace them. §37: only events from the last BOOK_FRESH_S
      (180s) are published, so a restart — which replays the whole book —
      never hands a plan an old trigger. THE RAILS ARE UNTOUCHED: they still
      take the r15..r104 path (`_derive_events(tines_only=True)`). "legacy"
      keeps the old path whole. Gate: check_level_engine_book E1-E7.
      ⚠️ FOUND BY MUTATION ON THE FIRST CUT: a HELD judged on the HOUR has no
      1m candle in its episode, max() of the empty span raised, and the whole
      sync failed — the ledger would have frozen through any hour-long 1m
      feed hole. The pierce now falls back to the hourly candles (E7).
v5.6  2026-09-22  OTV4TEST r104 - `rails_after_held()` and `split_rails()`:
      ONE definition of the invariant every level-trading plan must honour -
      held extremes rank first, rails rank after. The KEY is the caller's,
      because the three plans rank differently and each is right for its own
      trade; a shared function that imposed one ordering would have broken two
      of them.
v5.5  2026-09-22  OTV4TEST r103 - THE PROJECTION MAP: THE RAILS OUTWARD IN
      TIME. `rail_projection()` and `rail_projection_for()`. The operator has
      ruled this repeatedly - "the rails belong in a projection map so that you
      can go outward in time because you already know the slope of the channel
      if a fork is present". r19 BUILT the primitive: `tines_now(price,
      minutes_back)` walks a rail along its own slope so an interaction is
      measured when it happened. A NEGATIVE minutes_back walks it FORWARD, and
      nothing ever called it that way - so the slope, computed every 15s tick
      since the fork was built, has never once answered where a rail is going.
      Orientation is inherited from the tine rule, so a wrong-side rail is
      never projected; a dead fork yields an explicit absence.
v5.4  2026-09-18  OTV4TEST r44 — THE PIERCE IS THE EXCURSION, NOT THE RECLAIM
      BAR'S WICK. `_derive_events` skipped every bar that traded beyond a level
      without closing back, so depth was measured on the ONE bar that closed
      back. ⚠️ THE BIAS RAN AGAINST THE BEST SETUPS: a one-bar wick measured
      correctly, a REAL grab always reported the shallowest bar of the sequence.
      Operator's case, 09-18 london 716.38: true 0.0688%, recorded 0.0102% —
      refused as "a touch, not a sweep" against a floor it cleared by 3.4x.
      MEASURED: of 182 banked REJECTED events, 58 under-reported by >1.5x and
      23 were refused when the true excursion cleared the floor.
v5.3  2026-09-18  OTV4TEST r39 (LVL.13) — THE BOARD WALKS ZONES, AND A ZONE
      HOLDING PRICE IS FINISHED. Operator, 2026-09-17: *"it's just grouping and
      only the outer members of the group declare anything"*, *"only points of
      recording interactions is at the extremes of the cluster — nothing in
      between gets to declare anything"*, and *"when we have a breach of the
      cluster everything that was a part of the cluster needs to go with it."*
      Each rung now carries TWO recording prices: `near_edge`, which takes the
      touch, and `far_edge`, which takes the breach — and `zone_ids`, so the
      breach retires every member and not just the one price was at.
      🔴 `board()` NO LONGER PRE-THINS WITH `_walked()`, AND THAT WAS THE WHOLE
      DEFECT. r29's walk keeps the nearest level per direction-step, which is
      correct for single levels and DESTRUCTIVE before grouping: measured
      2026-09-18 on the live ledger, 43 rows became 21 and the six levels stacked
      on spot (716.75 … 718.04) became ONE before any zone could see them. The
      cluster has to form from everything the ledger holds; the walk then thins
      ZONES. Cluster first, walk second.
      ⚠️ A ZONE CONTAINING PRICE IS RETIRED TRAVERSED, not reported. Operator:
      *"'one zone containing spot' isn't a zone, then. It's done — as a zone is
      defined, it's finished. There's no reclaim trade for that."* It is judged
      on a CLOSED BAR and never a tick, because r5 ruled a wick never spends a
      level and retirement has no undo. The opening-range TRAVERSED rule is
      untouched and still runs at tick rate.
v5.2  2026-09-17  OTV4TEST r33 — ONE BOARD, THE FORK BESIDE IT, AND THE LEDGER
      EMPTIED OF WHAT WAS NEVER A LEVEL.
      🔴 VWAP IS NO LONGER A SOURCE. It wrote a `kind="dynamic"` row every tick
      keyed on the PRICE, so a moving average minted a new identity each time it
      moved — 844 rows, and NO READER HAS EVER SEEN ONE, because `live_levels()`,
      `board()` and `walk()` all filter `kind IN ('support','resistance')`. It is
      r19's defect in a second costume: a MOVING object given a FROZEN horizontal
      identity. VWAP stays available at `ctx["vol"].vwap`, where the butterfly's
      own band already reads it. r30's STALE_VWAP sweep — which existed only to
      clean up after this producer — is retired with it.
      🔴 THE LEDGER WAS CLEANED IN THE SAME REVISION, on the operator's
      instruction: 855 vwap/dynamic rows and 55 fork-rail remnants DELETED
      (1,016 rows to 107). The live tradeable count was 11 before and 11 after —
      the invariant that mattered, checked either side of the delete, with the
      table dumped to `/home/ubuntu/level_ledger_backup_*.sql` first. The 63
      pre-r29 ladder rows (prev_day, PDH/PDL, R1-R3) are LEFT as history: all
      retired, none live, and they were real levels once.
      ONE BOARD FOR EVERY PLAN THAT TRADES LEVELS, AND
      THE FORK IS A SECOND PRODUCT BESIDE IT, NEVER INSIDE IT. Operator 2026-09-17:
      *"Make every fucking trade that relies on levels get it from the same place
      and include the fork when present"* and *"the fork projection is separate
      from the levels map. Those are two separate products. Both are to be
      consulted. The fork is a common informer but not mandatory if it's not
      there."* That was already the ruling at r5 — *"LEVELS IN PLAY come from the
      derived store, NEVER A PRIVATE MAP: 3 named up, 3 named down, plus the 1h
      pitchfork's tines"* — and three plans had three private compositions of it:
      the hunt through `board()`, the sweep through a local `level_map.walk()`
      with the rails APPENDED INTO the level list, and the TCS through a raw
      `live_levels()` filtered to `provenance == "ny"` with no fork at all.
      🔴 `board()` IS NOW THE ONE ACCESSOR AND ITS ORB BOUNDS ARE OPTIONAL. With
      them it answers the hunt's question unchanged (levels BEYOND the opening
      range, measured outward from the edge — r12's reach, which is the hunt's
      own design and is not touched). Without them it walks from SPOT, nearest
      first, each older level further out — the operator's rule, and the same
      `_walked()` the ORB path already used, so this merges two compositions
      rather than adding a third.
      ⚠️ THE RAILS ARE NEVER IN `above`/`below`. They stay in `tines`, with
      `fork` reading "built" or "absent" — r19's co-inform-not-conjoin, which the
      sweep had rebuilt one layer up by appending them in memory at read time.
      `walk()` now DELEGATES here so there is one implementation, not two.
v5.1  2026-09-14  OTV4TEST r30 — TWO DEFECTS IN r29, FOUND READING THE NOON BAKE.
      (1) A CONFIRMED LEGACY ROW KEPT ITS OLD `timeframe`. The reconcile stamped
      `created_ts` on a pre-r29 row the tape holds but not `timeframe`, which
      `upsert_level` never rewrites, so the 9 held rows on the box read `session`
      and not `session:YYYY-MM-DD`. The book-beyond-the-tape rule matches only
      `session:%`, so once Saturday's purge trims the 1m tape past 09-09, the held
      720.06 / 719.70 / 717.68 would have retired NOT_A_LEVEL. The kept row now
      gets its formation time AND its dated timeframe (`set_level_created`).
      (2) r29's changelog said the reconcile retires "stale VWAP ids"; it skipped
      every `dynamic` row, and 515 were live after the bake. Every VWAP id but the
      current one now retires `STALE_VWAP`. No level reader sees `dynamic` rows,
      so neither changes a trade — (1) prevents one silently losing its levels.
v5.0  2026-09-14  OTV4TEST r29 (LVL.8, LVL.9) — THE SESSION LEVELS COME FROM THE
      TAPE, AND THE LEDGER IS RECONCILED TO IT EVERY CLOSED BAR. Operator: *"Levels
      are session extremes that held. Starting from spot, map the most recent up/down
      levels going backwards in time and further up/down from the recent ones. A
      level is spent if it didn't hold & price accepted through it."* — the rulings
      already on record in fork PLAN_SPEC §31.1 and mainline §38 / LVL.3 / LVL.17.
      (1) SOURCES. When main hands `ctx["level_tape"]` (the feed store's 1m tape,
      `SYM` and `SYM_EXT` merged) the session levels are `level_map.session_levels`
      — every CLOSED Asia/London/NY section's high and low on the mapper's own
      clock — that HELD, plus ledger rows formed BEFORE the tape begins (the book
      reaches further than the purged tape; §38 *"reach is what the ledger has"*).
      The mapper's pools (PDH/PDL, `(R1)` rungs, the named ladder) are NO LONGER a
      source: they were the wick-broken ladder, and at 09:10 ET they carried a
      single 715.42 print as `London High (R1)` beside the same price as `london`.
      (2) RECONCILE, once per new tape bar: a live row that is not a held tape
      level and not older than the tape is RETIRED — `ACCEPTED_THROUGH` at the bar
      the tape shows acceptance (an `ACCEPTED` event only when that bar is fresh, so
      history never fires a trade: LVL.17), otherwise `NOT_A_LEVEL`. That retires
      the r5 `fork1h/*` rails, the pre-r19 tine rows, stale VWAP ids and every
      duplicate the old producers left, and it cannot fight a restart: nothing is
      held in memory that the tape does not re-derive.
      (3) `created_ts` IS THE BAR THE EXTREME PRINTED ON, so the board's walk can
      order newest first. (4) `board()` and `walk()` WALK: newest held level each
      side of spot, older ones only if further out, then the board keeps what
      stands beyond each opening-range edge.
      ⚠️ WITHOUT `level_tape` IN ctx THE v4.6 SOURCES RUN UNCHANGED. Only the check
      fixtures take that path (main always supplies the key, None on a dead feed,
      which yields no session levels and retires nothing). Recorded as LVL.10: the
      `check_level_rejection` fixtures must move onto a tape and that branch go.
v4.6  2026-09-13  OTV4TEST r19 — THE FORK PROJECTION IS SEPARATED FROM THE LEVEL
      BOOK. Operator, 2026-09-13: "I want the session extremes separated from the
      1-hr fork object... The job of the fork projection should be a co-informer
      and not conjoined. The projection should only persist as long as the one
      hour fork persists; if a new fork is born a new projection needs to be
      graphed and plotted. There should be no drift from when triggers fired.
      They should be recorded at the moment of the interaction and not in
      hindsight." Four changes, one per clause.
      (1) SEPARATION. `_sources()` SKIPS any pool flagged `moving`. `publish_tines`
      puts every active rail on the map as a named pool, and this loop admitted
      them into a book of HORIZONTAL levels where `_lid` bakes the price into the
      id — so ONE rail became a NEW LEDGER ROW EVERY TIME IT DRIFTED A CENT.
      Measured here: 22 simultaneously-live `1h upper tine` rows spanning 5.79
      points, none retired, including four positions of a fork that had already
      died and been superseded. Mainline reached the same fix from the other end
      (r378: "main.py also stops admitting a MOVING tine into a book of
      horizontal levels").
      ⚠️ r15 BELIEVED IT HAD CLOSED THIS and pinned it with "no fork1h/* row in
      the ledger" — but the mapper names its rails "1h upper tine", so
      `_is_tine()` was False and they entered through the POOL door. The canary
      was scoped to the name that had been REMOVED, not the one that REMAINED.
      (2) IDENTITY. `_fork_key()` is the held fork's three anchors (p0/p1/p2).
      `build_fork_contained` runs every derive, so the OBJECT is rebuilt
      constantly; the anchors are what say whether it is the same fork.
      (3) LIFETIME. On a change of `_fork_key` every tine pierce state is
      dropped. r15 dropped state only when a tine NAME vanished — and a reborn
      fork republishes the SAME three names at new prices, so that condition
      could never fire and a dead fork's interaction state was inherited by its
      successor.
      (4) NO DRIFT. `tines_now(price, minutes_back)` walks the rail back along
      its own slope, and the emitter reads it ONE BAR BACK because the extreme
      being judged is on `df.index[-2]`, the last CLOSED bar. Mainline measured
      the cost of getting this wrong (r377): for a clean touch the extreme sits
      ON the rail, so the reported depth was slope x bars_since — THE STALENESS
      OF THE TOUCH AND NOT ITS DEPTH, clearing the rejection floor on 57.9%% of
      samples from drift alone. `minutes_back=0` is byte-identical to r15.
      🔑 WHAT STAYS CONJOINED, DELIBERATELY: the rails are still READ beside the
      ledger's levels by the emitter and the board. That is the co-informing.
      What ends is the rail being STORED as though it were a level.
v4.5  2026-09-13  OTV4TEST r18 — THE ACCOUNTING RAN PER TICK, NOT PER BAR, AND
      TWO TRADES WERE FIRING ON A WORD THAT DID NOT MEAN WHAT IT SAID. `derive()`
      is called EVERY TICK and the touch/acceptance block had NO BAR GUARD AT ALL
      (the one at `_derive_events` covers only WICKED/REJECTED). Three defects,
      each proven by DRIVING this engine rather than reading it, and each fixed
      to the operator's ruling of 2026-09-13.
      (1) A TOUCH WAS A POLL. One 5m bar polled 20 times scored touch_count=20.
      On this box: QQQ:PDH (R1):717.52 logged 399 touches in a 390-bar session,
      and 566 of 607 levels (93%) logged zero. RULED: one per CLOSED BAR. The
      guard is PER LEVEL, so a level created mid-session counts from its own
      first bar instead of inheriting someone else's.
      (2) ACCEPT_CLOSES=2 COUNTED TICKS AGAINST A 5m CLOSE. The same close was
      re-read every tick, so the SECOND TICK always satisfied it — ~15 seconds
      and ONE close, not two. Operator on moving to two 5m bars: "Hell no. 10
      minutes leaves us nothing actionable, the move is already long over."
      RULED and BUILT: the accounting runs on the CLOSED 1m BAR — the same bar
      the rejection fact already used, so this engine is finally on ONE CLOCK —
      which makes the same ACCEPT_CLOSES=2 mean TWO MINUTES, deterministic
      rather than accidental, and it is a real config key now.
      (3) THE RUN NEVER RESET ON AN INSIDE CLOSE. Only a touch — within
      TOUCH_TOL_PCT — cleared `beyond`, so a close that was plainly inside left
      the run standing: two excursions NINETY MINUTES APART, price six points
      inside for an hour between them, retired the level as ACCEPTED. RULED:
      a close back inside breaks the run.
      ⚠️ WHY THIS WAS NEVER COSMETIC: the runaway ARMS on ACCEPTED (§30), the
      TCS TRIGGERS on it (§34), and acceptance RETIRES the level — pulling it
      off the very board r15 had just repaired. Nothing flagged any of it:
      every gate was green and every existing level check passed.
      🔑 SUPERSEDES r18's bar_ts fix by subsuming it: the ACCEPTED row is
      stamped with the closed 1m bar it was judged on, so the literal "5m" is
      gone for a better reason than the one r18 gave.
v4.4  2026-09-13  OTV4TEST r18 — THE ACCEPTED FACT COULD NOT SAY WHICH BAR MADE
      IT. The ACCEPTED emit site passed the literal string "5m" as `bar_ts` —
      the column whose declared job is "the CLOSED 1m bar that produced it" —
      while the WICKED and REJECTED sites both passed a real timestamp. All 10
      ACCEPTED rows on this box carried `bar_ts='5m'`; all 76 WICKED/REJECTED
      rows carried a bar. TWO CONSEQUENCES, BOTH SILENT. (1) `level_event`'s
      PRIMARY KEY is (symbol, level_id, bar_ts, event) and `insert_level_event`
      is INSERT OR IGNORE, so a SECOND acceptance of the same level was dropped
      with no error — the ledger under-reported acceptances and the under-report
      was invisible. (2) `tcs_plan` keys its once-per-event latch on
      (level_id, bar_ts); with `bar_ts` constant that latch degenerated from
      ONCE PER ACCEPTANCE to ONCE PER LEVEL FOR THE LIFE OF THE PROCESS.
      `sweep_plan` uses the identical idiom on REJECTED and was always correct —
      only the TCS's upstream fact was stamped with a constant.
      ⚠️ FRESHNESS WAS NEVER AFFECTED: `accepted_age_bars` is computed from
      `ts_epoch`, so ACCEPT_FRESH_BARS always read true. The defect is identity,
      not staleness, which is why nothing looked wrong.
      🔑 ACCEPTANCE IS JUDGED ON THE 5m CLOSE (the block above says why), so the
      stamp is the 5m bar's own timestamp — the bar that decided. The fallback
      when no frame is present carries the tick clock rather than a constant, so
      a degenerate tick can never collapse onto a key that already exists.
      FORWARD-ONLY: the 10 rows already written keep `bar_ts='5m'`.
v4.3  2026-09-12  OTV4TEST r15 — TWO LEVEL DEFECTS, mainline r364's fix ported in its
      own shape (one implementation for otv5). (1) A POOL IS CLASSIFIED BY SIDE:
      the detector wrote "high"/"low" and `live_levels()` filters
      support/resistance, so PDH/PDL and the whole R1/R2/R3 ladder were
      invisible to the hunt, the sweep and the TCS — above the live price is
      resistance, below is support, formation as the fallback. (2) A TINE IS
      NEVER STORED: `_tines()` is gone from `_sources()`; `tines_now(price)`
      computes the rails from the fork the ForkEngine holds right now (with a
      rate: `bars_to_contact`), and a dead fork yields nothing on the next read
      — there is no row to go stale. The emitter reads the tines beside the
      ledger's levels and drops their pierce state when the fork goes. (3)
      `board(price, orb_high, orb_low, limit)` — the level board the plans read
      (PLAN_SPEC §38): held levels beyond the opening range ordered outward,
      the rails, four distinct empty answers, `count` never padded.
v4.2  2026-09-08  OTV4TEST r5 — THREE RULINGS FROM THE SWEEP UNTANGLE.
      · THE 1H PITCHFORK'S TINES ARE LEVELS. Moving ones (time + slope), so
        they are keyed on the TINE, not the price: `fork1h/upper`,
        `fork1h/median`, `fork1h/lower` (the `_level_id` price part is fixed at
        0.00 for them), and the price is read at the bar from the fork the
        ForkEngine built (`forks.last_forks["1h"]`). WICKED / REJECTED /
        ACCEPTED accrue on the tine.
      · THE TINE RULE: a top tine can never be a floor, a bottom tine never a
        ceiling. Upper -> resistance only; lower -> support only; median ->
        whichever side price is on at the bar. A wick UP through the lower
        tine is not an event.
      · NO LEVEL INSIDE THE OPENING RANGE. Once the 09:30 five-minute bar has
        printed (ctx["orb"] carries orb_high/orb_low), every level with
        orb_low <= price <= orb_high is retired TRAVERSED — price has been
        through it — and leaves every consumer at once. Tines are exempt
        (they move; the rule is evaluated per bar for them instead: a tine
        inside the range at the bar emits nothing).
v4.1  2026-09-08  OTV4TEST r3 — THE REJECTION FACT, EMITTED ONCE, HERE. Before
      this the only thing in the tree that could see a wick through a pool was
      the sweep strategy's private rule; this engine read the 5m CLOSE and never
      a high or a low, so a rejection was invisible to the derived layer. Now,
      on every CLOSED 1m bar (iloc[-2], processed once per bar timestamp), for
      every live support/resistance level:
        · close beyond the level (outside tolerance)  -> `beyond` += 1; at
          ACCEPT_CLOSES (2, measured) the level retires ACCEPTED_THROUGH and
          an ACCEPTED event is written. Any pierce state is cleared.
        · wick beyond, close inside                    -> WICKED, with depth:
            shallow  pierce <= SHALLOW_PIERCE_PCT (the sweep's strict ceiling,
                     SWEEP_CS_MAX_REJECTION_PCT = 0.25%)
            deep     pierce <= DEEP_PIERCE_PCT (3x, the relaxed ceiling)
            beyond   deeper than that — the level is being TAKEN, not swept;
                     recorded, never rejected
          Operator, 2026-09-08: *"one on a shallow and 2 on a deep pierce just
          to be sure"* — closes back inside COUNT THE WICKING BAR'S OWN CLOSE.
          A shallow pierce is REJECTED on that bar; a deep pierce needs the
          next bar to close inside too. A close beyond in between clears it.
      Consumers read `DerivedStore.latest_rejection()`; nobody re-detects.
      Wicks are tests, closes are acceptance — the whole emitter is that line.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

🔴 THE OPERATOR'S RULING, 2026-08-22:
    "In a live session a touch count is a HELD level, and when it doesn't
     hold, that level is FINISHED."

A touch is a HOLD. `touch_count` is the length of a run that TERMINATES at the
break — not a score that accumulates forever.

⚠️ THE EXISTING CODE DOES NOT MODEL THIS. `LiquidityPool` carries `touch_count`
and `swept` as separate fields, so a pool can read five-touch AND swept at the
same time — the count survives its own invalidation. Here the break is a
RECORDED EVENT: `retired_ts` + `retired_reason`, after which the level is
history and stops competing for attention.

🔴 BODIES DECIDE, WICKS TEST — universal convention, operator 2026-08-22, taken
from the sweep rules whose own doctrine says it plainly:
    `closes_beyond >= ACCEPT_CLOSES` is no longer a sweep — it is a BREAKOUT.
A wick through a level is a TEST. A close through is ACCEPTANCE.
⚠️ MEASURED, NOT INVENTED: closes_beyond >= 2 blocked 64.5% of named-pool
sweeps (2026-08-15). And it already fixed this exact defect once — the old
`rejection_pct` measured wick-to-last-close and STAMPED A BREAKOUT AS A
CONFIRMED SWEEP, which is precisely the error a wick-based rule produces.

🔴 NY IS THE DANGEROUS SESSION and the operator has been bitten by it. It is
the only session that is LIVE while being traded; Asia and London are closed
and final by the time an RTH box reads them. So "store once at session close"
is WRONG for NY. The resolution is the operator's own framing: **do not read
session fields at all.** Walk outward from price and report the first level
each way WITH ITS PROVENANCE — the session becomes a LABEL ON THE ANSWER, not
the query. A still-forming NY high that is nearest above genuinely IS the level
that matters, because that is where the stops are. `is_live_session` marks it
as still forming so nothing mistakes it for settled.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from derived.base import DerivedEngine
from utils.time_utils import closed_pos as _closed_pos   # r44 (BAR.1): the last CLOSED bar, by time

logger = logging.getLogger(__name__)

try:
    import config as _cfg
except Exception:                                               # noqa: BLE001
    _cfg = None
# v4.1 — pierce depth bands, from the sweep's own ceiling (strict / relaxed x3).
# 🔴 r18 — THIS KEY DID NOT EXIST IN config.py AND THE DEFAULT WAS WHAT RAN.
# `SWEEP_CS_MAX_REJECTION_PCT` was never defined, so every pierce band on every
# box came from the literal below — while `SWEEP_MIN_REJECTION_PCT = 0.003` sat
# in config with ZERO readers. A live threshold from a getattr default with a
# differently-named orphan beside it is the same defect the predecessor found at
# 15x; ours was 1.20x, which is why nobody saw it. The key is now DEFINED at the
# value that was already running, so this changes no behaviour and makes the
# knob real. The orphan is named in config so the next reader is not misled.
try:
    SHALLOW_PIERCE_PCT = float(getattr(_cfg, "SWEEP_CS_MAX_REJECTION_PCT", 0.0025))
except Exception:                                               # noqa: BLE001
    SHALLOW_PIERCE_PCT = 0.0025
DEEP_PIERCE_PCT = SHALLOW_PIERCE_PCT * 3.0
# Lone-print filter for session extremes, outside RTH — RULED 2026-09-23
# ("1. Yes"); the value lives in level_book.SPIKE_REJECT_USD ($1.00) so there is
# one number, overridable here by config key LEVEL_SPIKE_REJECT.
def _spike_default() -> float:
    from derived import level_book as _B
    return float(getattr(_cfg, "LEVEL_SPIKE_REJECT", _B.SPIKE_REJECT_USD)) if _cfg else _B.SPIKE_REJECT_USD
LEVEL_SPIKE_REJECT = _spike_default()
# §37 — only events this recent are published. A restart replays the whole book
# (it is a pure function of the tape), and an older HELD must never reach a plan
# as a fresh trigger: an interrupted firing sequence is never re-entered.
BOOK_FRESH_S = 180.0
BOARD_SYNC_MAX_AGE_S = 180.0      # CD.2: the board serves levels only this long after the newest synced 1m bar closed
_BLOCKS = ((4, 0, "overnight"), (9, 30, "premarket"), (16, 0, "rth"), (20, 0, "afterhours"))


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def board_for(store, symbol: str, price: float, orb_high=None, orb_low=None, limit: int = 3):
    """THE ONE ENTRY POINT EVERY LEVEL-TRADING PLAN CALLS (r33).

    Prefers the LIVE `LevelEngine` — it is the one holding the fork, so the
    rails only exist there — and falls back to an engine over whatever store the
    caller is bound to, which is what the checkers bind and what r13 made
    mandatory (a plan must use ITS store, never reach a global one).

    ⚠️ THIS EXISTS BECAUSE THE FALLBACK ITSELF WAS DUPLICATED. `liquidity_hunt`
    had it; the sweep and the TCS did not, and the first cut of r33 gave them a
    registry-only read that returned ZERO levels under every fixture — five
    green checks went red and that is how it was found. One composition, called
    three times, rather than three copies of the same eight lines.
    """
    eng = None
    try:
        from derived.registry import level_engine
        eng = level_engine()
    except Exception:                                           # noqa: BLE001
        eng = None
    if eng is not None and getattr(eng, "_store", None) is not None:
        return eng.board(price, orb_high, orb_low, limit)
    if store is None:
        return {"state": "no_store", "above": [], "below": [], "tines": [],
                "fork": "absent", "anchor": "spot",
                "count": {"above": 0, "below": 0, "tines": 0}}
    return LevelEngine(store, symbol, forks=None).board(price, orb_high, orb_low, limit)


def _zones(levels, width):
    """Cluster levels into ZONES {lo, hi, members, seed}, merged to a FIXED POINT.

    MOVED VERBATIM from derived/level_map.zones (r39; the operator's spec of
    2026-09-18: the outermost members of a cluster are its only voice, and a
    breach of the cluster takes every member with it) at r124, so the board
    stops importing level_map. `levels` are dicts with `price` and `formed_ts`;
    `seed` is the NEWEST member. derived/level_book.zones is the same merge over
    Level objects, used by the book itself."""
    if not levels or not width or width <= 0:
        return [{"lo": l["price"], "hi": l["price"], "members": [l], "seed": l}
                for l in sorted(levels, key=lambda x: x["price"])]
    zs = [{"lo": l["price"], "hi": l["price"], "members": [l]} for l in levels]
    changed = True
    while changed:
        changed = False
        zs.sort(key=lambda z: z["lo"])
        out = []
        for z in zs:
            if out and z["lo"] - out[-1]["hi"] <= width:
                out[-1]["hi"] = max(out[-1]["hi"], z["hi"])
                out[-1]["members"] += z["members"]
                changed = True
            else:
                out.append(z)
        zs = out
    for z in zs:
        z["seed"] = max(z["members"], key=lambda l: l["formed_ts"])
    return zs


def _walk(levels, spot: float) -> dict:
    """From spot outward, newest first, each older level only if further out
    (r29). MOVED VERBATIM from derived/level_map.walk at r124.
    -> {"up": [...], "down": [...]}, nearest first."""
    import pandas as pd
    newest_first = sorted(levels, key=lambda l: (-pd.Timestamp(l["formed_ts"]).value,
                                                 abs(float(l["price"]) - spot)))
    up, down = [], []
    last_up, last_dn = spot, spot
    for lv in newest_first:
        p = float(lv["price"])
        if p > spot and p > last_up:
            up.append(lv)
            last_up = p
        elif p < spot and p < last_dn:
            down.append(lv)
            last_dn = p
    up.sort(key=lambda l: float(l["price"]))
    down.sort(key=lambda l: -float(l["price"]))
    return {"up": up, "down": down}


def _level_id(symbol: str, provenance: str, price: float) -> str:
    """Stable identity so touches land on the SAME row across ticks.

    ⚠️ ROUNDED INTO THE ID ON PURPOSE. A level is a zone, not a float; without
    rounding, a price that wobbles in the fifth decimal creates a NEW level
    every tick and every one of them has touch_count=1 — which would silently
    destroy the entire premise of scoring by touches.
    """
    return f"{symbol}:{provenance}:{price:.2f}"


class LevelEngine(DerivedEngine):
    name = "levels"
    table = "level_ledger"
    min_interval_s = 0.0

    def __init__(self, store=None, symbol: str = "", forks=None):
        super().__init__(store)
        self.symbol = symbol
        self._forks = forks              # v4.2: the ForkEngine, for tine prices
        self.last_events: list = []      # events emitted on the most recent derive()
        # v6.0 — the book path's own state
        self._book_bar = ""              # the closed 1m bar the book was last synced on
        # v6.5 — the zone width the board groups by: the book's own (book.width),
        # set on every sync; None until the first one (the board is then ungrouped)
        self._zone_width: Optional[float] = None
        self._book_live: set = set()     # level_ids the ledger holds live, per the book
        self._book_emitted: set = set()  # (level_ids, ts_ms, event) already published
        self._flip_written: set = set()  # FLIP.1 — (flip_id, retire ts | None) already in the ledger
        # v6.2 — the rails' TOUCHES (a fork's death is the ForkEngine's alone, v6.3)
        self._rail_eps: dict = {}        # (fork_key, rail, role) -> {"ep": Episode, "ext": price}
        self._rail_bar = ""              # the closed 1m bar the rails were last judged on
        self.last_book_ms = None         # build time of the last sync, for the log


    def tines_now(self, price: float, minutes_back: float = 0.0):
        """The 1h fork's rails at THIS read, from the fork the ForkEngine holds
        right now — never a stored row (mainline r364, the operator's rule: "as
        long as there's a fork present, there should be a map of its points. And
        if the fork stops emitting, then the map has to go with it"). A dead
        fork yields [] on the next read; there is no row to go stale.
        A tine has a RATE: `bars_to_contact` is the convergence at a standing
        price — None when diverging, never a negative time. Kind by the tine
        rule: upper resistance, lower support, median by the side price is on."""
        fe = self._forks
        fork = (getattr(fe, "last_forks", {}) or {}).get("1h") if fe is not None else None
        if fork is None:
            return []
        # v6.3 — NO PRIVATE DEAD-SET HERE. A breached fork is withdrawn by the
        # ForkEngine that builds it (last_forks cleared), so `fork is None` above
        # already answers for every reader. Operator, 2026-09-23: "it's gone when
        # the engine says it's gone, not when a strategy says it's gone."
        idx = _f((getattr(fe, "last_idx", {}) or {}).get("1h")) or 0.0
        # r116 — WALK THE RAIL TO THE CURRENT MINUTE. `idx` is the forming hour's
        # START, so without this a sloped rail sat still all hour and then jumped.
        _bs = _f((getattr(fe, "last_bar_start", {}) or {}).get("1h"))
        if _bs:
            idx += min(1.0, max(0.0, (time.time() - _bs) / 3600.0))
        slope = _f(getattr(fork, "slope", None)) or 0.0
        # r19 — THE RAIL WHERE IT STOOD, NOT WHERE IT IS. `minutes_back` walks
        # the rail back along its own slope so an interaction is measured at the
        # instant it happened. The tines are parallel, so one slope moves all
        # three. Operator: "There should be no drift from when triggers fired.
        # They should be recorded at the moment of the interaction and not in
        # hindsight." Mainline measured the cost of getting this wrong (r377):
        # for a clean touch the extreme sits ON the rail, so the reported depth
        # was slope x bars_since — THE STALENESS OF THE TOUCH, NOT ITS DEPTH.
        # ⚠️ `minutes_back=0` is the live read and is byte-identical to r15's
        # behaviour, which is what keeps the board unchanged.
        back = (slope * (float(minutes_back or 0.0) / 60.0)) if slope else 0.0
        fkey = self._fork_key()
        out = []
        for name, fn in (("fork1h/upper", "upper_at"), ("fork1h/median", "median_at"),
                         ("fork1h/lower", "lower_at")):
            try:
                p = _f(getattr(fork, fn)(idx))
            except Exception:                                   # noqa: BLE001
                continue
            if not p or p <= 0:
                continue
            p = p - back
            gap = p - (price or 0.0)
            bars = None
            if slope and price:
                b = -gap / slope
                bars = round(b, 2) if b > 0 else None
            out.append({"provenance": name, "price": p,
                        # r33 — THE RAIL'S NATURE NAMES IT; ITS POSITION DECIDES
                        # WHETHER IT COUNTS THIS TICK. `side_ok` below carries the
                        # operator's rule, 2026-09-17: "lower fork tines
                        # projected below spot must inform the plan that they are a
                        # SUPPORT level, and upper fork tines projected above spot
                        # that a valid RESISTANCE exists above spot." A rail's
                        # position moves every tick, so its side is a per-tick fact.
                        # ⚠️ KIND IS NOT RELABELLED AND THAT IS DELIBERATE. r5's TINE
                        # RULE binds — a top tine can never be a floor, a bottom tine
                        # never a ceiling — so a rail on the wrong side of spot is
                        # DROPPED by `board()`, never renamed into the level it is not.
                        # The emitter reads `kind` for WICKED/REJECTED/ACCEPTED and
                        # relabelling would have made a lower rail emit resistance
                        # events the moment price fell under it (caught by
                        # check_level_rejection T2, which went red on the first cut).
                        "kind": "resistance" if name.endswith("upper") else
                                ("support" if name.endswith("lower") else
                                 ("resistance" if price and price < p else "support")),
                        "side_ok": (name.endswith("upper") and bool(price) and p > price)
                                   or (name.endswith("lower") and bool(price) and p < price)
                                   or not name.endswith(("upper", "lower")),
                        "slope_per_bar": slope, "bars_to_contact": bars,
                        "fork_key": fkey,          # r19: which projection this is
                        "minutes_back": float(minutes_back or 0.0),
                        "dist_pct": (abs(gap) / price * 100.0) if price else None})
        return out

    def board(self, price: float, orb_high=None, orb_low=None, limit: int = 3):
        """THE ONE LEVEL BOARD every plan that trades levels reads (r33).

        Two ANCHORINGS, one composition, one source:
        · `orb_high`/`orb_low` GIVEN — the held levels BEYOND the opening range,
          up to `limit` each side, ordered outward from the edge. That is the
          liquidity hunt's reach (r12: the bias is measured from the range edge)
          and it is unchanged.
        · BOUNDS OMITTED — the walk from SPOT: nearest first, each older level
          further out, `limit` each side. The operator's rule, r5 and r29:
          *"the session is a label on the answer, not the query."*

        🔴 THE FORK IS A SECOND PRODUCT, NOT A LEVEL IN THIS LIST. The rails are
        returned in `tines` with `fork` = "built"/"absent" and NEVER merged into
        `above`/`below` (r19: co-inform, do not conjoin). A caller that wants
        them consults them; a caller that does not is unaffected, and an absent
        fork is an explicit answer rather than an empty list.

        Empty answers stay distinct — no_store, no_range, no fork, none that
        side; fewer than `limit` is an answer (`count`), never padded. VWAP is
        not a level a trade contends with."""
        out = {"state": "ok", "above": [], "below": [], "tines": [], "fork": "absent",
               "anchor": "range" if (orb_high and orb_low) else "spot",
               "as_of": time.time()}
        if self._store is None or not price:
            out["state"] = "no_store"
            return out
        # CD.2 — NOT SYNCED IS NOT A BOARD. The ledger's "live" rows are only as current as the last book sync
        # against the tape; without a recent one (this process or the last, on this store) they are yesterday's.
        _sync = None
        try:
            _sync = self._store.level_sync_bar_close(self.symbol)
        except Exception:                                       # noqa: BLE001
            _sync = None
        if _sync is None or (time.time() - float(_sync)) > BOARD_SYNC_MAX_AGE_S:
            out["state"] = "not_synced"
            out["synced_bar_close"] = _sync
            return out
        _ranged = bool(orb_high and orb_low and orb_high > orb_low)
        if (orb_high or orb_low) and not _ranged:
            # a HALF range is a broken input, not a spot walk — fail closed (§22)
            out["state"] = "no_range"
            return out
        try:
            rows = self._store.conn.execute(
                "SELECT price, kind, provenance, touch_count, is_live_session, level_id, created_ts"
                " FROM level_ledger WHERE symbol=? AND retired_ts IS NULL"
                " AND kind IN ('support','resistance')", (self.symbol,)).fetchall()
        except Exception:                                       # noqa: BLE001
            out["state"] = "no_store"
            return out
        # 🔴 r39 — `_walked` NO LONGER RUNS HERE, AND THAT IS THE WHOLE FIX.
        # It applies r29's rule to individual LEVELS — "the newest each side,
        # older ones only if further out" — which discards cluster members before
        # any grouping can see them. Measured 2026-09-18: 43 ledger rows became
        # 21, and the six levels stacked on spot (716.75 … 718.04) became ONE.
        # Zoning the survivors is inert. The rule still applies, at ZONE
        # granularity, in `_side()` below — group first, then walk what you
        # grouped.
        # r33 — the EDGE each side is measured from: the range when one was given,
        # otherwise spot. One sort, one formatter; only the reference moves.
        edge_up = orb_high if _ranged else price
        edge_dn = orb_low if _ranged else price
        # r39 — the per-LEVEL split is gone: the zone is the object now, and the
        # sides are taken from the zones below.
        def fmt(r, edge):
            return {"price": r[0], "kind": r[1], "provenance": r[2], "touches": r[3],
                    "live": bool(r[4]), "level_id": r[5],
                    "dist_pct": abs(r[0] - edge) / edge * 100.0}
        # ══ r39 — CLUSTER FIRST, THEN WALK THE ZONES ══════════════════════
        # Operator's spec, 2026-09-18: extremes that cluster in close proximity
        # are ONE zone, and "only the outer members of the group declare
        # anything" — a plan trades the NEAR edge, and a breach needs acceptance
        # beyond the FAR edge, which takes the whole cluster with it.
        # 🔴 THE ORDER IS THE WHOLE POINT, AND THE FIRST CUT HAD IT BACKWARDS.
        # `_walked` applies r29's rule — "the newest held level each side, older
        # ones only if further out" — which ALREADY discards most cluster members
        # before any grouping can see them. Zoning the survivors is inert: on
        # 2026-09-18 it grouped 43 levels into zones of n=1 and missed a
        # six-member cluster sitting on top of spot. TWO DEDUPLICATION RULES WERE
        # STACKED, doing different jobs. Now the zone is the object and r29's
        # walk is applied TO ZONES, at zone granularity, which is what the spec
        # implies: group, then walk what you grouped.
        # ⚠️ FAILS OPEN: no width, no grouping — every level is its own zone,
        # which is exactly the pre-r39 board.
        # v6.5 (r124) — the book's width; the grouping and walk are this
        # module's `_zones`/`_walk` (moved verbatim from level_map).
        _w = getattr(self, "_zone_width", None)
        out["zone_width"] = _w

        import pandas as _pdz
        _lv = [{"price": float(r[0]),
                "formed_ts": _pdz.Timestamp(float(r[-1] or 0.0), unit="s", tz="UTC"),
                "row": r} for r in rows]
        _zs = _zones(_lv, _w) if _w else [
            {"lo": x["price"], "hi": x["price"], "members": [x], "seed": x} for x in _lv]

        # a zone is walked by its NEAR edge and dated by its NEWEST member, so
        # r29's rule reads exactly as it always did — one rung further out each
        # time — only the rungs are zones now.
        def _side(edge, ascending):
            reps = []
            for z in _zs:
                if ascending and z["lo"] <= edge:
                    continue
                if (not ascending) and z["hi"] >= edge:
                    continue
                near = z["lo"] if ascending else z["hi"]
                reps.append({"price": near, "formed_ts": z["seed"]["formed_ts"], "z": z})
            w2 = _walk(reps, float(edge))
            return (w2["up"] if ascending else w2["down"])

        def fmtz(rep, edge, ascending):
            z = rep["z"]
            member = min(z["members"], key=lambda m: abs(m["price"] - edge))
            d = fmt(member["row"], edge)
            d.update({"zone_lo": z["lo"], "zone_hi": z["hi"], "zone_n": len(z["members"]),
                      "near_edge": z["lo"] if ascending else z["hi"],
                      "far_edge": z["hi"] if ascending else z["lo"],
                      "zone_ids": [m["row"][5] for m in z["members"]]})
            return d

        out["above"] = [fmtz(r, edge_up, True) for r in _side(edge_up, True)[:limit]]
        out["below"] = [fmtz(r, edge_dn, False) for r in _side(edge_dn, False)[:limit]]
        # 🔴 THERE IS NO "INSIDE" ANSWER. Operator, 2026-09-18: *"one zone
        # containing spot isn't a zone, then. It's done — as a zone is defined,
        # it's finished. There's no reclaim trade for that."* A zone is a region
        # price held AWAY from; once price is inside it, its near edge has been
        # gone through and the object is spent. It is RETIRED in `derive()`
        # (TRAVERSED), not reported here — which makes r5's opening-range rule
        # one instance of a general one rather than a special case.
        out["tines"] = [t_ for t_ in self.tines_now(price) if t_.get("side_ok", True)]
        for t_ in out["tines"]:
            t_["level_id"] = self._lid(self.symbol, t_["provenance"], 0.0)
        out["fork"] = "built" if out["tines"] else "absent"
        out["count"] = {"above": len(out["above"]), "below": len(out["below"]),
                        "tines": len(out["tines"])}
        return out

    # ══ r103 — THE PROJECTION MAP: THE RAILS OUTWARD IN TIME ═══════════════
    RAIL_HORIZONS_MIN = (0, 15, 30, 60)

    def rail_projection(self, price: float, horizons=None):
        """Where each correctly-oriented rail IS, and where it WILL BE.

        🔑 THE OPERATOR'S RULING, given repeatedly and last on 2026-09-22: *"the
        rails belong in a projection map so that you can go outward in time
        because you already know the slope of the channel if a fork is
        present"*, and r19's clause — *"the projection persists only as long as
        the one hour fork persists and if a new fork is born a new projection
        must be graphed"*.

        🔑 THE PRIMITIVE ALREADY EXISTED AND WAS ONLY EVER WALKED BACKWARD.
        r19 built `tines_now(price, minutes_back)` to walk a rail along its own
        slope so an interaction is measured at the instant it happened. A
        NEGATIVE `minutes_back` walks it FORWARD. Nothing ever called it that
        way, so the slope — computed every tick since the fork was built — has
        never once answered "where is this rail going to be".

        ⚠️ ORIENTATION IS THE TINE RULE AND IT IS NOT NEGOTIABLE (r5): an upper
        rail is resistance forever, a lower rail support forever, the median by
        the side price is on. A rail on the wrong side of spot is DROPPED by
        `side_ok`, never relabelled — price above the top rail does not acquire
        a floor. The projection inherits that: it projects only rails that are
        correctly oriented RIGHT NOW.

        ⚠️ A DEAD FORK YIELDS `{}`. There is no stored row to go stale — the
        projection dies with the fork that graphed it, by construction.

        Returns {"fork": "built"|"absent", "fork_key": ..., "slope_per_bar": ...,
                 "above": {...}|None, "below": {...}|None, "horizons": {...}}
        where each side names the NEAREST correctly-oriented rail and carries
        `dist_pts`/`dist_pct`/`bars_to_contact` plus its projected price at each
        horizon.
        """
        hz = tuple(horizons if horizons is not None else self.RAIL_HORIZONS_MIN)
        live = [t for t in self.tines_now(price) if t.get("side_ok", True)]
        out = {"fork": "built" if live else "absent", "fork_key": None,
               "slope_per_bar": None, "above": None, "below": None,
               "horizons": {}}
        if not live:
            return out
        out["fork_key"] = live[0].get("fork_key")
        out["slope_per_bar"] = live[0].get("slope_per_bar")
        px = float(price or 0.0)
        ups = [t for t in live if t["kind"] == "resistance" and float(t["price"]) > px]
        dns = [t for t in live if t["kind"] == "support" and float(t["price"]) < px]
        near_up = min(ups, key=lambda t: float(t["price"]) - px) if ups else None
        near_dn = min(dns, key=lambda t: px - float(t["price"])) if dns else None

        def _side(t):
            if t is None:
                return None
            return {"provenance": t["provenance"], "price": float(t["price"]),
                    "kind": t["kind"],
                    "dist_pts": round(abs(float(t["price"]) - px), 4),
                    "dist_pct": t.get("dist_pct"),
                    "bars_to_contact": t.get("bars_to_contact"),
                    "slope_per_bar": t.get("slope_per_bar")}

        out["above"], out["below"] = _side(near_up), _side(near_dn)
        # ⚠️ PROJECTED AT A STANDING PRICE. This says where the RAIL goes, not
        # where price goes — the rail's slope is known, price's is not, and
        # conflating them would be inventing a forecast (§0).
        for m in hz:
            fwd = {t["provenance"]: round(float(t["price"]), 4)
                   for t in self.tines_now(px, -float(m))
                   if t["provenance"] in {x["provenance"] for x in live}}
            out["horizons"][int(m)] = fwd
        return out

    @staticmethod
    def _is_tine(prov: str) -> bool:
        return str(prov).startswith("fork1h/")

    def _fork_key(self):
        """The 1h fork's IDENTITY — its three anchors — or None if none is held.

        🔑 r19 — A NEW FORK IS A NEW PROJECTION, AND THE OLD ONE'S STATE GOES
        WITH IT. `build_fork_contained` runs every derive, so the Fork OBJECT is
        rebuilt constantly; what says whether it is the SAME fork is `p0/p1/p2`.
        ⚠️ r15's drop was keyed on the tine's NAME disappearing — and a reborn
        fork publishes the SAME three names at new prices, so the condition could
        never fire and a dead fork's pierce state was inherited by its successor.
        The operator: "if a new fork is born a new projection needs to be
        graphed and plotted."
        """
        fe = self._forks
        fork = (getattr(fe, "last_forks", {}) or {}).get("1h") if fe is not None else None
        if fork is None:
            return None
        from derived.forks import fork_identity               # v6.3 — the ONE definition
        return fork_identity(fork)
        # 🔴 v6.2 — IDENTITY IS THE ANCHORS' PRICES AND KINDS, NOT THEIR POSITIONS.
        # `idx` is the anchor's position inside the ForkEngine's rolling frame, so
        # once the frame is full EVERY new bar shifts it by one: measured on this
        # box, one fork (724.125 / 704.66 / 721.886, alive 09-09..09-14) wore 17
        # different keys, and 5 of 15 forks drifted the same way. r19's "a new
        # fork is a new projection" was therefore firing hourly on the SAME fork,
        # and a breach invalidation keyed on it would have expired at the next
        # bar. Found by the 15m-fork study (2026-09-23), confirmed on fork_series.
        key = []
        for a in ("p0", "p1", "p2"):
            piv = getattr(fork, a, None)
            if piv is None:
                return None
            key.append((round(_f(getattr(piv, "price", None)) or 0.0, 4), str(getattr(piv, "kind", ""))))
        return tuple(key)

    def _lid(self, sym: str, prov: str, price: float) -> str:
        # a tine's identity is the tine; its price moves every bar
        return _level_id(sym, prov, 0.0 if self._is_tine(prov) else price)

    def derive(self, ctx: dict) -> int:
        store = self._store
        if store is None:
            return 0
        sym = self.symbol or ctx.get("symbol") or ""
        price = _f(ctx.get("price"))
        if not sym or not price:
            return 0
        return self._derive_book(ctx, sym)

    # ══ v6.0 — THE BOOK PATH ══════════════════════════════════════════════
    def _derive_book(self, ctx: dict, sym: str) -> int:
        """Once per CLOSED 1m bar: rebuild the book from the tape, make the
        ledger hold exactly its live levels, publish its fresh events. The
        rails keep their own path. Never raises into the tick loop."""
        written = 0
        d1 = ctx.get("df_1m")
        try:
            bar_key = (str(d1.index[_closed_pos(d1, time.time())])       # r44 (BAR.1): by time
                       if d1 is not None and len(d1) >= 2 else "")
        except Exception:                                       # noqa: BLE001
            bar_key = ""
        if bar_key and bar_key != self._book_bar:
            self._book_bar = bar_key
            try:
                written += self._book_sync(sym)
            except Exception as exc:                            # noqa: BLE001
                # ⚠️ LOUD, NOT SILENT (§0.5): the ledger keeps its last good state
                logger.error("[level] book sync FAILED — ledger unchanged this bar: %s: %s",
                             type(exc).__name__, exc)
        written += self._rails_sync(ctx, sym)
        return written

    def _rails_sync(self, ctx: dict, sym: str) -> int:
        """v6.2 — the 1h fork's rails judged by `derived/level_rules`, the same
        HELD/BREACHED as a level, at the rail's price on the CLOSED bar's own
        minute (r19). Operator, 2026-09-23: "Any interaction that doesn't cause
        the fork object to destruct is a touch." So: a HELD is a touch ->
        published REJECTED on the rail's id (the sweep's legitimate sweep point,
        softer than a level). A BREACHED is NOT judged here: since r116 a fork
        lives while the ForkEngine's containment test can build it ("If the
        channel gets disrespected briefly but persists it still serving us
        somewhat of a guide"), so a breach only ends the rail's episode. (r126:
        this docstring still described r114's invalidation until now.) No
        tolerance, no depth grade."""
        from derived import level_rules as R
        store = self._store
        d1 = ctx.get("df_1m")
        try:
            if d1 is None or len(d1) < 2:
                return 0
            _cp = _closed_pos(d1, time.time())                  # r44 (BAR.1): by time, was iloc[-2]
            bar_ts = str(d1.index[_cp]); row = d1.iloc[_cp]
            bar = (0, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]))
            import pandas as _pd
            _b0 = _pd.Timestamp(d1.index[_cp])
            from zoneinfo import ZoneInfo as _Z
            _b0 = _b0.tz_localize(_Z("America/New_York")) if _b0.tzinfo is None else _b0
            bar_close_epoch = _b0.timestamp() + 60.0                # CD.2: the closed 1m bar's close
        except Exception:                                       # noqa: BLE001
            return 0
        if time.time() - bar_close_epoch > BOOK_FRESH_S:
            return 0                                            # CD.2: an old bar is not a fresh touch
        if bar_ts == self._rail_bar:
            return 0
        self._rail_bar = bar_ts
        fkey = self._fork_key()
        if fkey is None:
            return 0
        self._rail_eps = {k: v for k, v in self._rail_eps.items() if k[0] == fkey}
        now, written = time.time(), 0
        for t_ in self.tines_now(bar[4], minutes_back=1.0):     # the rail where it stood that minute
            name, px, kind = t_["provenance"], float(t_["price"]), t_["kind"]
            key = (fkey, name, kind)
            st = self._rail_eps.get(key)
            if st is None:
                st = self._rail_eps[key] = {"ep": R.Episode(kind), "ext": None}
            evs = st["ep"].step(bar, (px, px))
            reach = bar[2] if kind == R.RESISTANCE else bar[3]
            if R.TESTED in evs or st["ep"].episode or R.HELD in evs:
                st["ext"] = reach if st["ext"] is None else (
                    max(st["ext"], reach) if kind == R.RESISTANCE else min(st["ext"], reach))
            lid = self._lid(sym, name, 0.0)
            if R.BREACHED in evs:
                # v6.3 — NOT THIS ENGINE'S CALL. The ForkEngine judges the same bar
                # and withdraws the fork; here a breach is simply not a touch.
                st["ext"] = None
                continue
            if R.HELD in evs:
                ext = st["ext"] if st["ext"] is not None else reach
                pierce = max(0.0, (ext - px) if kind == R.RESISTANCE else (px - ext)) / px if px else 0.0
                depth = ("shallow" if pierce <= SHALLOW_PIERCE_PCT
                         else "deep" if pierce <= DEEP_PIERCE_PCT else "beyond")   # recorded only
                written += self._emit(store, sym, lid, px, kind, name, bar_ts, now, "REJECTED",
                                      {"pierce_pct": pierce, "depth": depth, "closes_back": 1}, bar[4],
                                      bar_close_epoch=bar_close_epoch)
                st["ext"] = None
        return written

    @staticmethod
    def _block_of(ts_ms: int) -> str:
        """The session block a formation time falls in — a display label only;
        identity is side + price (ruling 2026-09-22)."""
        import datetime as _dt
        from zoneinfo import ZoneInfo
        t = _dt.datetime.fromtimestamp(ts_ms / 1000.0, ZoneInfo("America/New_York"))
        hm = (t.hour, t.minute)
        for h, m, name in _BLOCKS:
            if hm < (h, m):
                return name
        return "overnight"                        # 20:00 onward opens the next overnight

    _DEF_COLS = (("defended_count", "INTEGER DEFAULT 0"), ("failed_count", "INTEGER DEFAULT 0"),
                 ("tested_count", "INTEGER DEFAULT 0"), ("last_defended_ts", "REAL"))

    def _record_defences(self, store, sym: str, book) -> int:
        """r214 (LVL.18) — each level's biography in counts, from the book's own events.

        HELD = price went to or through the level and closed back: a DEFENCE (the
        operator's definition of a sweep). BREACHED = it failed. TESTED = touched.
        RECORD-ONLY, in columns nothing reads. Rewritten only when a count moves.
        Never raises: a failed write warns and the ledger is otherwise untouched."""
        try:
            if not getattr(self, "_def_ready", False):
                have = {r[1] for r in store.conn.execute("PRAGMA table_info(level_ledger)")}
                for col, typ in self._DEF_COLS:
                    if col not in have:
                        store.conn.execute(f"ALTER TABLE level_ledger ADD COLUMN {col} {typ}")
                store.commit()
                self._def_ready, self._def_written = True, {}
            counts: dict = {}
            for e in getattr(book, "events", None) or []:
                ev = e.get("event")
                if ev not in ("HELD", "BREACHED", "TESTED"):
                    continue
                for lid in e.get("level_ids") or ():
                    c = counts.setdefault(lid, [0, 0, 0, None])
                    if ev == "HELD":
                        c[0] += 1
                        c[3] = float(e["ts"]) / 1000.0
                    elif ev == "BREACHED":
                        c[1] += 1
                    else:
                        c[2] += 1
            n = 0
            for lid, c in counts.items():
                t = tuple(c)
                if self._def_written.get(lid) == t:
                    continue
                store.conn.execute(
                    "UPDATE level_ledger SET defended_count=?, failed_count=?, tested_count=?,"
                    " last_defended_ts=? WHERE level_id=? AND symbol=?", (c[0], c[1], c[2], c[3], lid, sym))
                self._def_written[lid] = t
                n += 1
            if n:
                store.commit()
            return n
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[level] defence counts not recorded: %s", exc)
            return 0

    def _book_sync(self, sym: str) -> int:
        from derived import level_book as B
        from data.candle_feed import feed_db_path
        store = self._store
        t0 = time.time()
        db = feed_db_path()
        h1, m1 = B.load_bars(db, sym, "1h"), B.load_bars(db, sym, "1m")
        if not h1 or not m1:
            logger.warning("[level] book: no tape in %s (1h=%s 1m=%s) — ledger unchanged",
                           db, len(h1 or []), len(m1 or []))
            return 0
        # r296 (LVL.19) — CLOSED BARS ONLY. load_bars has no upper bound and the feed flushes the
        # forming minute within 2 s, so the replay's last tape bar was the bar still being built and
        # level_rules decided HELD on its provisional close - permanently (_book_emitted dedupes).
        # Measured 2026-10-18 on the 40 newest REJECTED/FLIP_REJECTED rows: 10 were judged 12-19 s
        # into their bar and recorded a close that differs from the bar's final close (e.g. 10-14
        # 10:40 support 735.69 recorded vs 736.13 final). A bar counts once its whole span has
        # elapsed; the hour likewise. now_ms also goes to build() so the session blocks agree.
        now_ms = int(time.time() * 1000)
        m1 = [b for b in m1 if b[0] + 60_000 <= now_ms] or None
        h1 = [b for b in h1 if b[0] + 3_600_000 <= now_ms] or None
        if not h1 or not m1:
            logger.info("[level] book: no CLOSED tape yet (1h=%s 1m=%s) — ledger unchanged",
                        len(h1 or []), len(m1 or []))
            return 0
        book = B.build(sym, h1, m1, now_ms=now_ms, spike_reject=LEVEL_SPIKE_REJECT)
        self._zone_width = getattr(book, "width", None)   # v6.5 — board() groups by it
        now = time.time()
        written = 0
        import datetime as _dt
        from zoneinfo import ZoneInfo
        _et = ZoneInfo("America/New_York")

        # ── 1. the ledger holds exactly the book's live levels ──
        live_ids = set(book.live)
        for lid in sorted(live_ids - self._book_live):
            lv = book.live[lid]
            day = _dt.datetime.fromtimestamp(lv.formed_ts / 1000.0, _et).date()
            tf = f"session:{day}"
            store.upsert_level((lid, sym, float(lv.price), lv.side, self._block_of(lv.formed_ts),
                                tf, lv.formed_ts / 1000.0, 0, None, 0, None, None, 0))
            store.set_level_created(lid, lv.formed_ts / 1000.0, tf)   # a re-formed price re-dates
            written += 1
        try:
            rows = store.conn.execute(
                "SELECT level_id FROM level_ledger WHERE symbol=? AND retired_ts IS NULL",
                (sym,)).fetchall()
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[level] book: ledger read failed — nothing retired: %s", exc)
            rows = []
        # ── 1b. FLIP.1 — the flipped levels, RECORD-ONLY. kind is 'flip_support' /
        # 'flip_resistance': every reader that trades levels (board(), walk(),
        # live_levels()) filters kind IN ('support','resistance'), so no plan
        # sees one until the operator rules it does. timeframe names the level
        # it came from; created_ts is the bar it flipped on.
        # ⚠️ EVERY flip the book knows is written ONCE, live or already retired:
        # one that flipped and broke again between two syncs, or while the bot
        # was down, would otherwise never reach the record. The upsert is
        # idempotent (ON CONFLICT on level_id), so a restart rewriting them is
        # harmless; `_flip_written` keeps it to once per process.
        flip_ids = set(getattr(book, "flipped", {}) or {})
        flip_dead = getattr(book, "flip_dead", {}) or {}
        for e in book.events:
            if e.get("event") != "FLIPPED":
                continue
            fid = e["level_ids"][0]
            dead_ts = flip_dead.get(fid)
            state = (fid, dead_ts)
            if state in self._flip_written:
                continue
            self._flip_written.add(state)
            side = e["side"]
            reason = None if dead_ts is None else (
                "TRAVERSED" if fid in book.traversed else "BREACHED")
            store.upsert_level((fid, sym, float(e["near"]), f"flip_{side}", "flip",
                                f"flip_of:{e.get('from', '')}", e["ts"] / 1000.0,
                                0, None, 0, None if dead_ts is None else dead_ts / 1000.0,
                                reason, 0))
            written += 1
        retired = 0
        for (lid,) in rows:
            if lid in live_ids or lid in flip_ids:
                continue
            if lid in flip_dead:
                # its SECOND break (ruling 4) or the opening range (ruling 5)
                store.retire_level(lid, flip_dead[lid] / 1000.0,
                                   "TRAVERSED" if lid in book.traversed else "BREACHED")
            elif lid in book.traversed:
                store.retire_level(lid, book.dead[lid] / 1000.0, "TRAVERSED")   # inside the opening range
            elif lid in book.dead:
                store.retire_level(lid, book.dead[lid] / 1000.0, "BREACHED")
            else:
                store.retire_level(lid, now, "NOT_A_LEVEL")
            retired += 1
        self._book_live = live_ids | flip_ids
        self._record_defences(store, sym, book)                 # r214: counts, record-only

        # ── 2. fresh events, under the names every plan already reads ──
        import bisect
        m_ts = [b[0] for b in m1]
        tested: dict = {}
        cutoff = (now - BOOK_FRESH_S) * 1000.0
        published = 0
        for e in book.events:
            key = tuple(e["level_ids"])
            if e["event"] == "TESTED":
                tested[key] = e["ts"]
                continue
            if e["ts"] < cutoff:
                continue
            mark = (key, e["ts"], e["event"])
            if mark in self._book_emitted:
                continue
            self._book_emitted.add(mark)
            near, side = float(e["near"]), e["side"]
            # the member the board shows for this zone: the one AT the near edge
            lid = min(e["level_ids"], key=lambda i: abs(float(i.rsplit(":", 1)[1]) - near))
            i1 = bisect.bisect_right(m_ts, e["ts"])
            close = float(m1[i1 - 1][4]) if i1 else None
            if e["event"] == "HELD":
                # the pierce is the deepest point beyond the near edge over the
                # WHOLE episode, TESTED -> HELD (r44: never one bar's wick)
                t_open = tested.get(key, e["ts"])
                i0 = bisect.bisect_left(m_ts, t_open)
                span = m1[i0:i1]
                if not span:
                    # judged on the HOUR (no 1m candle in the episode — a feed
                    # hole, or before the minute tape): the hourly candles that
                    # judged it carry the extreme. Found by mutation 2026-09-23:
                    # an empty span raised inside max() and failed the whole sync.
                    span = [b for b in h1 if t_open <= b[0] <= e["ts"]]
                if span and near:
                    ext = (max(b[2] for b in span) - near) if side == "resistance" else \
                          (near - min(b[3] for b in span))
                    pierce = max(0.0, ext) / near
                else:
                    pierce = 0.0
                depth = ("shallow" if pierce <= SHALLOW_PIERCE_PCT
                         else "deep" if pierce <= DEEP_PIERCE_PCT else "beyond")
                name, p = "REJECTED", {"pierce_pct": pierce, "depth": depth, "closes_back": 1}
            elif e["event"] == "BREACHED":
                name, p = "ACCEPTED", {"pierce_pct": 0.0, "depth": "accepted", "closes_back": 0}
            elif e["event"] == "FLIPPED" and e.get("flip"):
                name, p = "FLIPPED", {"pierce_pct": 0.0, "depth": "flipped", "closes_back": 0}
            else:
                continue
            bar_ts = str(_dt.datetime.fromtimestamp(e["ts"] / 1000.0, _et))
            prov = self._block_of(book.live[lid].formed_ts) if lid in book.live else "book"
            kind = side
            if e.get("flip"):
                # FLIP.1 — RECORD-ONLY names and kind: every plan asks
                # latest_event() for REJECTED/ACCEPTED by name, so a flipped
                # level's retest is FLIP_REJECTED / FLIP_ACCEPTED and no plan
                # reads it until the operator rules one should.
                name = name if name == "FLIPPED" else f"FLIP_{name}"
                kind, prov = f"flip_{side}", "flip"
            _span = 3600.0 if str(e.get("judged_on") or "1m") == "1h" else 60.0
            written += self._emit(store, sym, lid, near, kind, prov, bar_ts, now, name, p, close,
                                  bar_close_epoch=e["ts"] / 1000.0 + _span)    # CD.2
            published += 1
        self.last_book_ms = round((time.time() - t0) * 1000.0)
        logger.info("[level] book synced in %d ms — %d live, %d retired, %d event(s) published",
                    self.last_book_ms, len(live_ids), retired, published)
        try:                                                    # CD.2: the market time this sync is good to
            store.mark_level_sync(sym, max(b[0] for b in m1) / 1000.0 + 60.0)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[level] sync mark not written: %s", exc)
        return written

    # ── v4.1: the rejection fact, from the CLOSED 1m bar ────────────────
    def _emit(self, store, sym, lid, lvl, kind, prov, bar_ts, now, name, p, close, bar_close_epoch=None):
        row = (sym, lid, bar_ts, now, name, lvl, kind, prov,
               float(p["pierce_pct"]), p["depth"], int(p["closes_back"]), close,
               None if bar_close_epoch is None else float(bar_close_epoch))   # CD.2: the market time
        self.last_events.append({"event": name, "level_id": lid, "price": lvl,
                                 "kind": kind, "provenance": prov, "bar_ts": bar_ts,
                                 "pierce_pct": p["pierce_pct"], "depth": p["depth"],
                                 "closes_back": p["closes_back"], "bar_close": close})
        logger.info("[level] %s %s %s %.2f (%s) pierce %.3f%% %s closes_back=%d bar=%s",
                    sym, name, kind, lvl, prov, p["pierce_pct"] * 100, p["depth"],
                    p["closes_back"], bar_ts)
        return store.insert_level_event(row) if store is not None else 0


    def walk(self, price: float, limit: int = 3):
        """The walk from SPOT — nearest first, each older level further out.

        🔴 THE OPERATOR'S OWN FRAMING: walk up from where price is until you
        hit the last session high — which could be overnight, previous day or
        previous session — and the same going down. **The session is a label on
        the answer, not the query.**

        ⚠️ DISTANCE ORDERS, TOUCH COUNT SCORES. The nearest level may be a
        one-touch artifact while the one 0.4% beyond has held five times.

        r33 — THIS DELEGATES TO `board()` AND HOLDS NO COMPOSITION OF ITS OWN.
        It was a second implementation of the same query over the same rows, and
        two implementations is how the plans came to disagree. Kept as a name
        because `main.py` and `derived/snapshot.py` call it; it returns only the
        levels, since its callers never consulted the fork.
        """
        b = self.board(price, limit=limit)
        return {"above": b.get("above", []), "below": b.get("below", [])}


def rail_projection_for(store, symbol: str, price: float, horizons=None):
    """THE ONE ACCESSOR for the rail projection, resolved exactly as `board_for`
    resolves the board: prefer the LIVE engine, because it is the only thing
    holding a fork, and fall back to an engine over the caller's own store.

    🔴 IT DOES NOT READ `level_ledger`. r19 guarantees no rail is ever stored
    there, which is precisely why `anchors.nearest_tine` — which queried that
    table for `fork1h/%` — returned None on every row ever written."""
    eng = None
    try:
        from derived.registry import level_engine
        eng = level_engine()
    except Exception:                                           # noqa: BLE001
        eng = None
    if eng is not None and getattr(eng, "_store", None) is not None:
        return eng.rail_projection(price, horizons)
    if store is None:
        return {"fork": "absent", "fork_key": None, "slope_per_bar": None,
                "above": None, "below": None, "horizons": {}}
    return LevelEngine(store, symbol, forks=None).rail_projection(price, horizons)


def rails_after_held(held, rails, key):
    """r104 — HELD EXTREMES RANK FIRST; RAILS RANK AFTER. The one invariant
    every level-trading plan must honour, expressed so each plan keeps its OWN
    ordering key.

    🔑 THE OPERATOR'S RULING, 2026-09-22: *"It's just SEPARATE from held levels
    with testing orders. It's SOFTER than held levels."* A held session extreme
    is a fixed price with resting stops beyond it; a fork rail is a sloped line
    price tends to respect and where no pool sits. Ranking them in one list by
    distance makes the softer thing beat the harder one whenever it happens to
    be nearer.

    ⚠️ THE KEY IS THE CALLER'S, DELIBERATELY. The three plans rank differently
    and each is correct for its own trade: the sweep walks outward from spot,
    the TCS ranks by ABSOLUTE distance and does NOT filter by side (after the
    move the accepted high sits BELOW price and is exactly what it sells
    against), and the hunt orders outward from the ORB edge. A shared function
    that imposed one ordering would have broken two of them.

    ⚠️ IT DOES NOT CAP. Capping is the sweep's rule, applied to the HELD list
    before this is called. Operator: *"Three would be ideal ... if there's more
    I would like to have more, if there's less we can accept that too."*
    """
    return sorted(held, key=key) + sorted(rails, key=key)


