"""
data/candle_feed.py  v5.9
v5.9  2026-11-04  OTV5 r74 (ORP.3 + FEED.15) — THE OPENING TAPE IS RE-PULLED WHEN IT IS PARTIAL, AND CONTROL CAN ASSIGN THE
      NODE. ORP.3: _maybe_rescue_opening_range asked only "is there a 09:30 5m row?"; 2026-11-02 AMZN held one, captured
      when the socket dropped at 09:31, so nothing was re-pulled and get_orb_range froze the range from it. It now
      judges the five 1m bars 09:30-09:34 and the 09:30 5m row with analysis/opening_tape.problem() (the same rule
      get_orb_range establishes by) and re-pulls BOTH 1m and 5m from 09:30 on this session (unsubscribe first, the
      store upserts the replay), from 09:36 to ORB_RESCUE_UNTIL_ET 15:00, at most ORB_RESCUE_MAX 6 a session,
      ORB_RESCUE_EVERY_S 120 s apart (it was once a session, so a tape that returned at 10:55 was never re-pulled).
      FEED.15: NodeBook.choose() dials control's assigned node first (data/dxlink_assign.json beside the feed store,
      written by dtp tools/dxlink_assign.py after the 09:15 wake: today's date, this box's symbol, an IPv4 node, at most
      ASSIGN_MAX_AGE_S 12 h old); pre-open only once that node answers its own upgrade probe 101, never while it is
      cooling; anything else falls to the r70 order (pre-open hash spread, last good node, hash, DNS). A missing or
      stale file is one log line a day. Before ASSIGN_SWITCH_BY_ET 09:27 a box connected elsewhere switches to a fresh
      assignment once a day (PlannedNodeSwitch: the old socket closed first, redial in 1-5 s, no node cooled). The
      operator, 2026-11-02: "if we have control over the connections, then spread them out"; 2026-11-03 "Yes to the
      proposal". Gates tests/check_orb_incomplete.py R1-R4, tests/check_feed_session_release.py S22-S25.
v5.8  2026-11-03  OTV5 r72 (PARK.5) — A SHORT GATE TAPE IS RE-PULLED BEFORE 11:01, ON THIS SAME SESSION. The operator,
      2026-11-03, on PARK failing closed for a thin tape: "Fine, but we need to be more responsive when that happens to
      mitigate impacts to trading." _maybe_refill_commit_tape(), riding the flush cadence beside the opening-range rescue,
      on an equity box only (the pair route exists): inside config.PARK_TAPE_WATCH_ET it judges this box's own 1m tape and
      the pair's with strategy/park_plan.tape_gaps (the plan's own early read) and, when one is short, unsubscribes and
      re-subscribes that symbol's 1m from today's 09:30 (from PRIME depth when a PRIOR session is short) on the socket it
      already holds - no new DXLink session. At most every PARK_TAPE_REFILL_EVERY_S and PARK_TAPE_REFILL_MAX times a day
      per symbol, plus ONE forced re-pull inside PARK_TAPE_FINAL_REFILL_ET (after the 10:59 bar closes) whatever the
      cadence says. The store upserts the replay (check_replay_overwrite). Never raises. Gate tests/check_park_commit.py
      T1-T6.
v5.7  2026-11-03  OTV5 r72 (PARK.5) — EVERY EQUITY BOX ALSO SUBSCRIBES QQQ's 1m RTH BARS, ON ITS OWN SESSION. PARK's
      commitment gate (strategy/park_plan v5.4; the operator, 2026-11-03: "Let's modify the park trade on equities using the
      new filters — add a gate in the code 'is an index=false' and start trading it Monday") reads QQQ's first hour, its
      10:00 hour and its prior sessions' first-90-minute volume at 11:01. _park_pair_symbol() names the pair
      (config.PARK_PAIR_SYMBOL) unless this box is an index (config.PARK_INDEXES) or is the pair itself; CandleFeed adds
      ONE subscription (pair, 1m, RTH) routed to store symbol QQQ, beside VIX's - the same socket, no new DXLink session.
      The first subscribe on a store that never held QQQ primes PRIME_DAYS deep (r16). s3_push uploads only the box's own
      family, so the rows stay on the box. The QQQ, SPX boxes' routes are unchanged. Gate tests/check_park_commit.py F1-F4.
v5.6  2026-11-02  OTV5 r70 (FEED.13) — RELEASE THE OLD, ALWAYS: THE QUOTE TOKEN IS REUSED ACROSS RECONNECTS, THE OLD SOCKET IS
      CLOSED BEFORE A NEW ONE, AND A SESSION-LIMIT REFUSAL WAITS 120-180 s. 2026-11-02 09:30 ET the DXLink socket dropped on
      8 boxes at once (WebSocketNetworkError/WouldBlock); AMZN, GOOGL and TSLA were then refused "The number of user
      sessions has exceeded the configured limit" on every ~60 s retry for 10-25+ minutes. The SDK's
      DXLinkStreamer.__asynccontextmanager__ GETs /api-quote-tokens on EVERY open, so each retry minted a new token beside
      the dropped socket's session. SessionReleasingStreamer (a subclass; no SDK file, no venv change) takes the token
      and dxlink-url from QuoteTokenCache, fetched once and reused until QUOTE_TOKEN_MAX_AGE_S (20 h) or until DXLink
      rejects it (AUTH_STATE UNAUTHORIZED after AUTH, ERROR UNAUTHORIZED / token-expired, or no AUTHORIZED within
      AUTH_TIMEOUT_S 45 s); the token is never logged. The SDK path already closes the socket on every exception route
      (httpx2's shielded close in a finally, then the response and the client); the subclass adds its own finally that
      closes it explicitly if anything left it open and closes any recorded-open socket before dialling a new one.
      run(): a session-limit refusal starts a lockout - the next wait is session_limit_wait(0), uniform [120, 180] s, and
      every wait after it (any error) is [200, 300] s, never under 120 s, until a connection succeeds (subscriptions
      live), from the very first attempt after a process start (11-02 09:57 AMZN, restarted into the lockout, made ~16
      refused attempts in 90 s on the 3/6/12 s rungs); each refusal logs one SESSION_LIMIT line with its wait. Without
      one, every error keeps reconnect_wait()'s jittered 3 -> 60 s ladder unchanged. Why hold that long: 09-29 measured
      ~36 sessions on the login (17 boxes x 2) and ~14 boxes were live on 11-02, so the ceiling was most likely refused
      attempts counting as sessions server-side for some minutes, each minting a new token. Operator, 2026-11-02:
      "Release the old, ALWAYS."
      THE LIMIT IS PER DXLINK NODE - MEASURED 2026-11-02 10:50 ET: tasty-openapi-dxlink-md-ws.dxfeed.com resolves to
      different backend nodes; ten boxes and AMZN/GOOGL got 129.153.134.53 on every lookup, TSLA (recovered 09:40) and
      UNH were on AWS nodes 184.195.238.144 / 54.204.44.247, and AMZN/GOOGL, refused for 85 min on 129.153.134.53,
      connected at once when pinned (/etc/hosts, temporary) to the AWS nodes - the 09:30 mass reconnect herded boxes onto
      one node. The operator: "if we have control over the connections, then spread them out." NodeBook keeps every
      IPv4 A record seen (re-resolved at each connect) and the last node that connected, in data/dxlink_nodes.json beside
      the feed store; the socket is dialled to the chosen IP with the hostname kept for TLS SNI (httpcore2's
      `sni_hostname` extension), the certificate check (verify stays on) and the Host header. Choice: the last node that
      connected (sticky - a working node is never left for spread), else the usable nodes ranked by crc32(symbol), else
      the first DNS answer, else the plain URL. A session-limit refusal cools that node 30 min, so the next dial goes to
      another known node; a non-refusal failure before AUTHORIZED cools it 5 min; a node unseen for 14 days is forgotten.
      The node is logged on every dial, connect, error and SESSION_LIMIT line.
      The operator then: "Yes, connect to a known new server & if we can probe to spread out our connections prior to
      the open, it might be worth looking into." (a) IMMEDIATE SWITCH: a refusal with an un-cooled alternate known
      redials it after node_switch_wait() (1-5 s); the 120-180 / 200-300 s hold applies only when no alternate is left
      (its rung counts held waits only). (b) FLEET LIST: six public resolvers answered only 129.153.134.53 that
      afternoon, so DNS alone cannot find the others; warehouse/s3_push.py v5.6 shares every box's book through S3
      (fleet/dxlink_nodes/) and writes the merge to dxlink_nodes_fleet.json beside the feed store, read at each connect;
      the 11-02 nodes are seeded from data/dxlink_nodes_seed.json (data, not code). (c) PRE-OPEN SPREAD: before 09:30 ET
      every usable node gets a TCP+TLS handshake with SNI (_probe_node: no HTTP, no AUTH, no DXLink session) and the box
      takes crc32(symbol) over the reachable ones, stickiness ignored; in RTH the last good node is kept. Forget window
      3 -> 14 days. THE PROBE READS THE UPGRADE, NOT ONLY TLS: from 14:19 ET 11-02 129.153.134.53 completed TLS normally
      and answered every websocket upgrade "HTTP/1.1 502 Bad Gateway", so _probe_node sends ONE bare upgrade request
      (GET <path>, Host + SNI = hostname, certificate verified), reads only the status line and closes at once (no
      SETUP, no AUTH, no quote token; the same request as dtp tools/dxlink_probe.py): 101 = usable, 5xx or anything
      else = not. A 5xx/non-101 upgrade at CONNECT time cools that node 5 min and, with another known node, redials it
      in 1-5 s (one UPGRADE_REFUSED line with node and status). Gate tests/check_feed_session_release.py S1-S20.
      THE TOKEN REUSE IS MEASURED (2026-11-03 16:15 ET, QQQ box, after the close): one /api-quote-tokens token AUTHORIZED
      on five sockets in a row - twice through DNS, then dialled at 52.6.43.252, 184.195.238.144 and 129.153.134.53 with
      SNI/Host kept - SETUP, AUTH_STATE UNAUTHORIZED, AUTH, AUTH_STATE AUTHORIZED each time, no ERROR: a token is
      accepted on a new socket and on another node. THE AUTHORITATIVE NAMESERVERS ARE ASKED TOO: the host itself is
      delegated to Route 53 (ns-313.awsdns-39.com and peers) while recursive resolvers answer one node at a time, so
      _resolve_nodes() appends the A records the zone's own nameservers give (stdlib UDP, NS set cached 1 h, bounded,
      never raises) after the recursive answer, order kept. 54.204.44.247 is removed from the seed (timed out the
      evening of 11-02, failed TLS verification 11-03); 52.6.43.252 (authoritative 11-02, 7 boxes 11-03) is added.
      Gate S19 (seed) and S21 (authoritative lookup).
v5.5  2026-10-28  OTV5 r47 (FEED.12) — A FRACTIONAL SHARE SIZE IS PARSED, NOT THROWN AWAY. tastytrade 13.2.3 types `size`
      as int on TimeAndSale (int | None on Trade) and dxFeed sends fractional shares (0.419652): pydantic raised
      int_from_float and the SDK skipped the event - MEASURED 2026-10-27 about half of QQQ's TimeAndSale events
      (~0.3% of volume) and ~120 of SOFI's 41,645 Trades never reached `prints` / `last_trade`. At import,
      _accept_fractional_size() retypes those fields to Decimal (Decimal | None on Trade, the SDK's own None-ness)
      and rebuilds each model in place (model_rebuild(force=True)); Event.from_stream and DXLinkStreamer._map_message
      both call model_validate on these same class objects, so every parse takes it. A probe validates 0.419652
      through the rebuilt validator; FRACTIONAL_SIZE carries the result and main() logs it (WARNING if not taken).
      prints.size / last_trade.size were already REAL and _n() stores float(v); every reader (tape_at_level,
      order_flow, anchors.aggressor_share) sums floats. The FEED.4 filter stays for any other parse failure.
v5.4  2026-10-26  (FEED.4, journal half) — THE SDK'S PARSE FAILURES ARE COUNTED, ONE LINE A MINUTE, NOT ONE LINE EACH.
      r134 kept every "Failed to parse event" line so dropped prints stay visible; during RTH that is hundreds of
      thousands a box, and on 2026-10-26 it pushed the morning out of the journal (GOOGL's journal began at 14:30).
      _TTNoiseFilter now passes the first in each 60 s window and suppresses the rest, and the next one passed
      carries "[FEED.4: +N more like it in the last Ss, suppressed]", so the count is still in the record. Chatter
      is dropped and WARNING+ kept as before. The prints themselves are still lost (FEED.4 stays open for that).
v5.3  2026-10-25  (TTS.1) — EACH RECONNECT WAIT CARRIES BOUNDED RANDOM JITTER. The streamer's backoff was a fixed 3 -> 6 ->
      ... -> 60 s ladder, so after one server-side DXLink break (2026-09-29 09:30:10 ET, six boxes at once) every box
      retried on the same schedule against the shared TastyTrade session ceiling and the last one in stayed blind
      (09:30-09:37, "number of user sessions has exceeded the configured limit"). reconnect_wait() scales each wait by a
      uniform factor in [1 - RECONNECT_JITTER, 1 + RECONNECT_JITTER] (0.20), never below RECONNECT_MIN_S; the ladder
      itself (doubling, the 60 s cap, the reset on a live socket) is unchanged, and the log names the actual wait.
      Gate tests/check_reconnect_jitter.py J1-J5.
v5.2  2026-10-25  (LVL.20) — A HALF DAY'S RTH ENDS AT ITS BELL. _within_rth ended every intraday window at a FIXED
      16:00 (1h 16:30), so on 2026-11-27 and 12-24 (13:00 close) the 13:00-16:00 bars would be written to the plain RTH
      series and every RTH reader (opening range, session extremes, the level book) would read three after-hours hours
      as the session. The window's end moves earlier by utils.market_calendar.close_shift_minutes (180 on a 13:00 day,
      else 0); a calendar fault keeps the 16:00 window and never drops the write. Port of otv4 r494 (FEED.11), the
      shared half OTV4TEST r300 left open. Gate tests/check_half_day_rth.py H1-H8.
v5.1  2026-10-25  OTV5 r16 (PRIME.1) — A SYMBOL THIS STORE HAS NEVER HELD IS PRIMED FROM TASTYTRADE, DEEP; ANYTHING ELSE
      BACKFILLS AS BEFORE. The operator, 2026-10-25: prime "from tasty trade of whatever's obtainable", never from S3 ("if
      we haven't traded it recently last July's data ... isn't relevant"), "only priming missing data - there is no reason
      to prime stuff that's already on the box", and only at a symbol switch. _backfill_start takes the store's newest
      held bar for that (store symbol, interval): NONE held (a fresh box, or the symbol just switched to) -> PRIME_DAYS
      deep; held -> the old start (BACKFILL_DAYS / today's open), reaching back to the newest held bar if the box was down
      longer, never deeper than PRIME_DAYS. Recomputed at EVERY (re)subscribe from the store, so a reconnect replays only
      what a restart would. TastyTrade's reach, MEASURED 2026-10-25 by QQQ-TEST (MSG-QQQ-1025-14, every ask 20 years back):
      8,000 bars per subscription from the newest back (1m RTH ~21 sessions, 1m EXT ~8, 5m EXT ~34 sessions), else time
      windows (5m/15m ~3 months, 1h ~9.5 months, 1d to 2022-12-29). PRIME_DAYS stays inside RETENTION_DAYS (1m 60, 5m/15m
      30, 1h 60) so the nightly purge never deletes what was just primed; 1d (no retention) 400 days, which clears
      sma50_mtf's 55. A held bar is rewritten only under FEED.9b / FEED.10, unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.21 2026-10-12  OTV4TEST r277 (FEED.10b) — THE REFEREE WAITS 60 s, NOT 5, AND AN IDENTICAL REPLAY IS SILENT. From
      1-REPORTER's critique (MSG-1REP-1012-12): the feed writes in flush batches, so a bar's FINAL live update can
      land a few seconds after its close while its last 1m is still partial in the store; r276 (5 s) refereed it
      against that short 1m sum and KEPT the stale bar (pinned: check_bar_referee R11, red on r276). Only a bar
      closed REFEREE_CLOSE_GRACE_S = 60 s ago is refereed; every live final update takes the FEED.9b rule. An
      identical replay returns before any decision (r276 logged it as an 'override - KEPT': 103 15m / 156 5m
      lines on one restart; R12). The operator, 2026-10-12 19:14 ET: "We need to fix this problem before it
      starts polluting more days than just today"; 19:16 ET: "Yes".
v4.20 2026-10-12  OTV4TEST r276 (FEED.9b MIRROR OF otv4 r486 556bc2c + FEED.10, FORK-FIRST) — (1) FEED.9b: the upsert's
      WHERE is otv4 v4.14's _UPSERT_CANDLE_SQL byte-for-byte (a stored NULL yields; 1d is last-write-wins; a bar with
      volume yields unless the new version lost more than 5% of it; a 0-volume index keeps r271's range/open rule),
      rows run one by one, and the refusal log carries the kept and refused OHLCV. (2) FEED.10, THE 1m REFEREE: a
      CLOSED 5m/15m/1h bar whose every minute this store holds keeps whichever version is closer to its own 1m
      aggregate - an INFLATED replay is caught as well as a shrunken one (10-12: this box's own replays stored every
      complete QQQ 1h bar at exactly 2.0x its 1m volume; FEED.9b passes any version with more volume). Forming bars,
      incomplete minutes, stored NULLs and any referee error take the FEED.9b rule with no extra read. ⚠️ The 1m set
      is the same vendor's and completeness is by count (an open limitation, BACKLOG FEED.10). The operator,
      2026-10-12 19:14 ET: "We need to fix this problem before it starts polluting more days than just today".
      GATES check_replay_overwrite v1.1 U1-U13 (byte-identical with otv4's but its version line), check_bar_referee R1-R9.
v4.19 2026-10-12  OTV4TEST r271 (FEED.9, SHARED; MIRROR OF otv4 r485 eed0069) — A HISTORY REPLAY CANNOT SHRINK A BAR WE
      ALREADY HOLD. upsert_candles was INSERT OR REPLACE (last write wins); every (re)subscribe replays history, and
      the vendor's 2026-10-08 11:50-11:55 history held only the last ~2 minutes, so the live QQQ 5m 11:55 bar
      (S3 V 107877 L 752.39 = the 1m sum) became V 33808 L 752.57, with the 15m 11:45 and 1h 11:00 bars and SPX's
      08-31/09-04 09:00 1h bars (no 09:30 opening print) damaged the same way (found here, MSG-QQQ-1012-01/02).
      The write now keeps the version with more tape: volume no lower, range no narrower, and the same open or
      strictly more of something; a stored NULL price always yields; refusals log per (symbol, interval) only when
      > 0. The poison guard rejects a non-finite price (NaN passed `<= 0` and landed as NULL). Body byte-identical
      to otv4 dce9431's. ⚠️ A vendor correction that LOWERS a high or a volume is refused too (the accepted cost).
      GATE tests/check_replay_overwrite.py U1-U10.
v4.18 2026-09-29  OTV4TEST r175 (SYM.1) — main() refuses a symbol that is not on the list (config.INSTRUMENT_LISTED), exit 78, beside r146's unset refusal: never stream a symbol the bot will not trade.
v4.17 2026-09-26  OTV4TEST r146 — main() refuses to start with OT_INSTRUMENT unset (exit 78), first,
      before logging: the feed would otherwise subscribe a symbol named UNSET.
v4.16 2026-09-24  OTV4TEST r135 — A FRESH BOX BACKFILLS 45 DAYS OF HOURLY BARS, NOT 16.
      The first fresh box's agent found check_level_tape T7 red (it needs more than
      30 days of hourly tape; 16 were backfilled), so every new box ran a shallow
      level book for about two weeks. The operator preferred fixing it with no
      extra provisioning steps over seeding from the warehouse. MEASURED 2026-09-24
      (/var/tmp/probe_1h_depth.py, its own stream): asked 90 days of QQQ{=1h} RTH,
      TastyTrade returned 435 bars over 63 trading days, the full 90 calendar days.
      45 because it clears T7's 30 with holiday margin and stays inside
      RETENTION_DAYS['1h'] = 60 (warehouse/retention_purge.py), so the nightly
      purge never deletes what the next restart would re-fetch. SIDE EFFECT, and a
      correction: 16 calendar days is ~11 sessions x 7 = ~77 bars, UNDER the bot's
      80-bar 1h frame (config.py TIMEFRAMES["1h"]; its comment's "~112" multiplied
      calendar days by 7) - so a fresh box's 1h trend vote also started short.
      45 days is ~220 bars. A box that already holds the history reads the same
      last 80 bars as before; INSERT OR REPLACE rewrites held bars with the
      vendor's own values.
v4.15 2026-09-24  OTV4TEST r134 — THE JOURNAL WAS 97% SOMEONE ELSE'S DEBUG. The
      tastytrade SDK (13.2.3, tastytrade/__init__.py:13) hard-sets its own logger
      to DEBUG, so every websocket frame reached the journal past this file's
      INFO basicConfig: MEASURED 2,895 of 2,988 candle-feed lines in five minutes,
      ~600/min, found by the first fresh box's agent. `_tt_noise_filter` on the
      root handlers drops the SDK's DEBUG records EXCEPT "Failed to parse event",
      because those are DATA BEING DROPPED, not chatter: 173 in 30 minutes, every
      one a TimeAndSale whose `size` was FRACTIONAL (0.27, 0.0013 shares) and the
      SDK's model demands an integer - fractional-share prints never reach
      `prints`. Kept visible; recorded as FEED.4, not fixed here. Our own
      loggers are untouched; the SDK's INFO and above are untouched.
v4.14 2026-09-18  OTV4TEST r52 — THE WAL HAD NO CEILING. `journal_size_limit`
      defaulted to -1 and SQLite reuses the WAL in place rather than shrinking
      it, so the file sits at its high-water mark forever: MEASURED
      `feed_store.db-wal` at 1,581 MB beside a 1.63 GB database, on a box with
      3.4 GB free. Truncating by hand reclaimed 1.5 GB and the limit REVERTED on
      the next open, because the pragma is per connection. Pinned at 128 MB on
      the connection every writer uses.
v4.13  2026-09-18  OTV4TEST r36 — THE UNDERLYING'S OWN QUOTE IS SUBSCRIBED
      (FEED.2, open since 2026-09-13). r64's manifold took FOUR of the five
      streams for the ticker — Trade, TimeAndSale, Summary, Underlying — and left
      Quote, because Quote WAS subscribed: per CONTRACT, in
      `_reconcile_chain_subs`, where the bot needs it to price a spread. So the
      underlying's own bid/ask was never asked for. MEASURED 2026-09-17: **0 of
      22,846,560 `quote_series` rows are a non-option symbol.**
      🔑 IT IS THE ONLY SOURCE OF RESTING DEPTH. The operator's thesis is that
      size parks at coarse levels and is not worried about minute granularity;
      `prints` says what TRADED and cannot answer it. Measured the same day,
      volume within ±$0.25 of a session extreme carries a lift of **1.02x**
      against a random price in the traded band — i.e. none — and a level that
      HELD is one price turned away from, so volume AT it conflates absorption
      with traversal. `bid_size`/`ask_size` do not.
      ⚠️ COLLECTION ONLY (§31). Nothing reads it; it is banked until there is
      enough to answer the question with numbers rather than an argument.
      ⚠️ NO HANDLER CHANGED: `_on_quote` already keys on `event_symbol` and
      writes `bid_size`/`ask_size`, so it is symbol-agnostic — one line.
      ⚠️ AND IT RIDES THE WRAPPED, INDEPENDENT SUBSCRIBE, NOT THE CHAIN'S CHUNKED
      ONE. r118 is why: adding a stream to the per-CONTRACT subscription cost SPX
      its ENTIRE chain subscription mid-session on 2026-08-25. Each stream here
      fails alone and names itself in the log.
      ⚠️ PURGE: it lands in `quote_series`, already `ARTIFACT_DAYS` at 3 days, so
      the new stream inherits the policy — a subscriber cannot create an unpurged
      table by accident.
v4.12 2026-09-06  r288 / DEV.11 — THE DISK GUARD MOVES OUT, to main.py's tick
      loop. v4.11 put it at the top of `run()`'s `while True`, which is the
      RECONNECT loop rather than a tick loop, so the check ran ONCE PER
      CONNECTION — at startup, then not again until the stream dropped.
      📊 MEASURED, NOT INFERRED: the feed restarted 17:24:14 UTC, a drill was
      armed a minute later, and the flag was still sitting there.
      🔑 `main.py` ticks on POLL_INTERVAL_SECONDS and is the service the deploy
      path restarts, so a bake arms the guard without a separate feed bounce.
v4.11 2026-09-06  r285 / DEV.7 — THE BOX SAYS IT IS FULL. NOBODY ASKS IT.
      Operator: *"it should be a statement, not the answer to a question that
      we're constantly asking."* A control-side poller would ask fifteen boxes
      every few minutes, almost always to hear "no", and would inherit S3.19:
      `ssh_run` gives 22s, returns `rc=255 ssh timeout`, and LEAVES THE REMOTE
      PROCESS RUNNING — and a `find /` on a nearly-full box is exactly the walk
      that outlasts 22s, so the poller would abandon scans that then compete
      for the disk it was worried about.
      🔑 AND THE EC2 API CANNOT ANSWER IT ANYWAY: it knows a volume's SIZE,
      never how full it is. Something must run ON the box, and this process
      already is — it writes the candles, holds the WAL open, and fills the
      disk. The thing consuming the space notices.
      ⚠️ ONE `os.statvfs` PER CYCLE, rate-limited to OT_DISK_CHECK_S. The walk
      for the five largest files runs only on the CROSSING, once per episode.
      ⚠️ TOTALLY GUARDED, because this is the feed's loop on fifteen live boxes:
      a bug here does not cost an alert, it costs the TAPE. `disk_watch.check()`
      is written never to raise and the call site catches anyway.
      ⚠️ PLACED ABOVE THE STAND-DOWN GATE ON PURPOSE — a box parked for
      maintenance still has a disk, and a maintenance window is exactly when
      nobody is watching it.
v4.10 2026-08-25  r118 REVERT of r116's TheoPrice subscription. SPX lost its
      whole per-contract subscription this morning at 13:27 UTC — greeks,
      quotes, marks and theo frozen together while ticker events kept flowing —
      and could not build a chain, so it evaluated nothing through the ORB
      window. QQQ, identical code, narrower chain, was fine. The writer and the
      table stay; only the subscribe is withdrawn.
v4.9  2026-08-24  r116: TheoPrice moves to the PER-CONTRACT subscription beside
      Greeks/Quote. It was asked of the plain ticker, which has no publisher for
      it, so theo_series has been empty since the stream was added on 08-22 —
      proven on QQQ by tools/probe_aux_streams.py (12 events on 12 option
      symbols, 0 on the ticker, Greeks/Quote as controls). _on_theo now keeps
      the FULL streamer symbol: _base_symbol collapsed every contract to "QQQ"
      and theo_series is keyed (symbol, ts_epoch), so ~250 strikes would have
      overwritten each other and the table would have looked populated while
      holding one arbitrary contract. Underlying stays on the ticker — that IS
      its symbol space; retest during RTH before calling it uncarried.
v4.8  2026-08-23  AUDIT F3: the rescue tested for ANY 5m bar at or after
    09:30, not for THE 09:30 bar. A feed that came up late (first bar
    09:45) passed the check, the opening bar stayed missing, and
    get_orb_range carried yesterday's range as EXPIRED - the exact
    failure the rescue was built for. The query is now bounded to the
    09:30 bar's own five-minute slot.
v4.7  2026-08-25  OPENING-RANGE RESCUE. If today's 09:30 5m bar is
    missing between 09:36 and the 11:00 ORB cutoff, UNSUBSCRIBE 5m and
    resubscribe it from the open — once per session, guarded by date.
    On 2026-08-21 the feed ate the open and the range only established
    at 10:01; get_orb_range fails SOFT in that case, carrying
    YESTERDAY'S range as EXPIRED, which is why it took an hour to
    notice. Unsubscribe-first is deliberate: two live subscriptions on
    one tenor would race to write the same rows.
v4.6  2026-08-22  MANIFOLD PART 2 — the five event types this feed
    never asked for are subscribed and housed: TimeAndSale (prints,
    WITH aggressor_side — buy vs sell initiated, real order flow),
    Trade (last_trade), Summary (session_summary, carrying
    prev_day_close_price), Underlying (put_call_ratio, front/back
    volatility term structure) and TheoPrice. Ten of ten event types
    are now captured. Each subscribes INDEPENDENTLY and fails open
    per port; the drain is wrapped so no aux stream can stop the
    candle loop.
v4.5  2026-08-22  THE MANIFOLD. Capture everything, give it a home.
    (a) greeks_series + quote_series — ALL 13 Greeks fields and ALL 12 Quote
        fields incl. bid_size/ask_size, append-only, PK (symbol, ts).
        chain_marks is UNCHANGED and stays the fast current-value read.
        CHARM and VANNA are second-order derivatives of delta OVER A SERIES,
        so a last-write-wins row made both uncomputable.
    (b) extended candles on ALL FIVE tenors, not just 1h. Four fifths of the
        overnight tape was never requested.
    (c) VIX at full tenor parity (was 1m+1d). Capture on all 15 boxes,
        publish to S3 from SPX only.
    Series writes are wrapped: they can never stall the raw tape.
v4.4  2026-08-21  `_is_ext_of` polarity INVERTED and fixed. `tho=true` marks the
    RTH echo, not the extended one. 1m/5m/15m/1d were dropped outright (no
    (sym,tf,True) key exists for them) and the two 1h streams were swapped.
    Live fleet-wide outage of the entire intraday tape on the first v4 session.
v4.3  2026-08-20  THE RTH FEED GATE IS REMOVED. Subscriptions are held whenever
    the box is up; MAINTENANCE (OT_FEED_MODE) is the only stand-down left and it
    is now UNCONDITIONAL — the old block slept only until the next open and
    seconds_until_rth_open() returns 0 during RTH, so a maintenance window
    declared inside the session was silently defeated. The gate existed to stop
    a maintenance wake putting 29 boxes on the wire at once; the fleet is now
    15, the same 15 daily, and a normal session already carried ~20 without
    strain. Operator's call, 2026-08-20. The v4.2 write guard below is what
    makes this safe: every non-RTH bar still routes to <SYM>_EXT, for EVERY
    interval, so the plain series stays RTH-pure while the box streams 24h.
v4.2  2026-08-20  RTH GUARD AT THE WRITE — ported from the SMC thread's v3.17.
    The FEED.2 fix corrected STREAMING routes, and the restart's BACKFILL then
    wrote 24-HOUR bars into the plain series anyway. Measured on the fleet
    2026-08-20 after the v3.16 bake: plain-symbol 1h carried hours 00-23 on
    equities from 08-05 forward — ~12 bars/hour overnight against 38-39 in RTH.
    **SPX was clean (hours 13-20 only), and that control is the proof**: an
    index has no overnight session, so it had nothing to be contaminated with.

    ⚠️ THIS IS WORSE THAN THE HOLE IT REPLACED. A gap announces itself; a series
    that silently CHANGES CHARACTER mid-stream does not. 07-31 was RTH-only and
    08-19 was 24-hour, with nothing marking the seam — and structure_analyzer
    (weight 2.0), the pitchfork's 1h fractals, trend_engine's 0.20 context vote
    and entry_snapshot all read plain 1h expecting RTH.

    ⚠️ SEGREGATED, NEVER DROPPED, and that is the SMC thread's improvement on
    what I first proposed. I suggested deleting the non-RTH rows. **EXT_INTERVAL
    is 1h ONLY, so an overnight 5m or 15m bar has no other home anywhere** — and
    DXFeed history is use-it-or-lose-it. A non-RTH bar arriving on a plain route
    is RE-ROUTED to <SYM>_EXT; `tools/segregate_nonrth_bars.py` does the same for
    rows already written (moves, dry-run by default, backs up first, and reports
    destination collisions rather than silently merging them).

v4.1  2026-08-20  FEED.2 — EVERY 1h CANDLE ROUTED TO THE WRONG SYMBOL FOR SIX
    DAYS, FLEET-WIDE. Ported verbatim from the v3/SMC fix (v3.16); the body
    below the header was BYTE-IDENTICAL across all three repos, so this is one
    defect with one fix in three places.

    `symbol_map` was keyed on (dx_symbol, interval), and FEED.2 subscribes the
    SAME symbol at the SAME interval TWICE — RTH and extended. The second
    registration overwrote the first, so **the RTH 1h route was destroyed at
    construction** and every 1h bar landed under the EXT store symbol. Measured
    2026-08-20: plain QQQ and SPX 1h frozen at 2026-08-14 while *_EXT 1h was
    current.

    ⚠️ NOTHING RAISED. BARS_STALE warned every five minutes with
    `refused=False` and the bots traded on 08-14 bars regardless. **Six days of
    stale higher-timeframe structure** fed structure_analyzer's swings and S/R,
    the pitchfork and its observer, and entry_snapshot.

    ⚠️ AND IT LANDS ON WORK DONE THIS WEEK. r183 raised TIMEFRAMES["1h"] from
    50 to 80 because trend_engine needs EMA_SLOW+5=55, and that diagnosis —
    "the 1h vote never fired" — was correct about the DEPTH and blind to the
    STORE BEING FROZEN. **I tuned an instrument's configuration without
    checking whether its input was arriving**, which is the same failure as
    `oi_proxy`, `max_liq` and `vix_at_entry`: a plausible silence, fixed at the
    wrong layer.

    ⚠️ WHAT IS *NOT* AFFECTED: every study run on 2026-08-20 —
    fork_respect_study, tine_order_study, sweep_discriminator,
    magnitude_estimator, chain_feasibility — builds its own bars from the 1m
    OHLC CSVs and never reads the candle store. **Those numbers stand.**

    FIX: the map key carries the extended-hours flag, and the ingest router
    reads `tho=true` off the echoed symbol — the attribute `_interval_of`
    deliberately discards is exactly the one the router needed.
    GUARD: the feed REFUSES TO START if two subscriptions share a route key, if
    a subscription has no route, or if two subscriptions write the same
    (store_symbol, interval). **The defect was not a typo; it was a route table
    that could silently lose an entry, and that must be impossible rather than
    merely fixed.**

    ⚠️ EXISTING ROWS ARE NOT REPAIRED. Plain-symbol 1h history between 08-14 and
    the deploy is simply absent, and DXFeed history is use-it-or-lose-it.
    Backfill on restart refills what the API still serves.
"""
import argparse
import asyncio
import logging
import os
import json
import math
import random
import sqlite3
import traceback
import threading
import time as _time
from datetime import datetime, time as dtime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from tastytrade import DXLinkStreamer           # module-level so tests can patch
from contextlib import asynccontextmanager                         # v5.6 (FEED.13)
from anyio import CancelScope, create_task_group, fail_after         # v5.6 (FEED.13): the SDK's own primitives
from httpx2 import AsyncClient                                       # v5.6 (FEED.13): module-level so the gate can patch
from httpx2.websockets import WebSocketDisconnect                    # v5.6 (FEED.13)
from tastytrade.utils import TastytradeError                         # v5.6 (FEED.13)
import socket                                                        # v5.6 (FEED.13): dxlink node book
import zlib                                                          # v5.6 (FEED.13): stable symbol hash
from urllib.parse import urlsplit, urlunsplit                        # v5.6 (FEED.13)
from tastytrade.dxfeed import (Candle, Greeks, Quote, Trade,
                               Summary, TimeAndSale, Underlying,
                               TheoPrice)


# ── v5.5 (FEED.12) — A FRACTIONAL SHARE SIZE IS PARSED, NOT THROWN AWAY ──────
# tastytrade 13.2.3 types `size` as int on TimeAndSale (int | None on Trade); dxFeed sends fractional shares
# (0.419652), pydantic raises int_from_float and Event.from_stream / DXLinkStreamer._map_message catch the
# ValidationError and SKIP the event: about half of QQQ's TimeAndSale events (~0.3% of volume) never reached
# `prints`. Both parse paths call cls.model_validate on the SAME class objects imported here (streamer.MAP_EVENTS
# holds them), so retyping the field and rebuilding the class's validator in place reaches every parse. The new
# type is Decimal (the SDK's own type for every other size and price; prints.size / last_trade.size are REAL and
# _n() stores float(v)), keeping the SDK's own None-ness. Only an int-typed field is touched, so an SDK that
# fixes this itself is left alone. A probe validates 0.419652 through the rebuilt validator; the result is in
# FRACTIONAL_SIZE and logged at start. Never raises: a failure leaves the SDK as it was (events skipped as before).
def _accept_fractional_size() -> dict:
    import typing
    from decimal import Decimal
    out = {}
    for cls in (TimeAndSale, Trade):
        name = cls.__name__
        try:
            field = cls.model_fields.get("size")
            if field is None:
                out[name] = "no size field"
                continue
            args = typing.get_args(field.annotation)
            nullable = type(None) in args
            if field.annotation is int or (nullable and set(args) == {int, type(None)}):
                field.annotation = typing.Optional[Decimal] if nullable else Decimal
                cls.model_rebuild(force=True)
            probe = cls.__pydantic_validator__.validate_assignment(cls.model_construct(), "size", 0.419652)
            ok = probe.size == Decimal("0.419652")
            out[name] = "ok" if ok else f"FAILED: probe parsed {probe.size!r}"
        except Exception as exc:                                   # noqa: BLE001
            out[name] = f"FAILED: {type(exc).__name__}: {exc}"
    return out


FRACTIONAL_SIZE = _accept_fractional_size()

from config import INSTRUMENT, TIMEFRAMES
from analysis import opening_tape                                    # v5.9 (r74, ORP.3)
from data.tasty_client import get_session, get_loop

logger = logging.getLogger(__name__)

# ── Poison-candle sanity window (v3.2) ────────────────────────────────────────
# Any candle timestamp outside this window is junk. The observed failure is the
# signed-32-bit rollover (2**31 * 1000 = 2147483648000 ms => 2038-01-19), which
# is far in the future; a 0 / negative ts is equally invalid. Upper bound is
# computed at call time (now + 2 days) so a legitimately-fresh bar is never
# rejected for clock skew, while a 2038 bar always is.
TS_MS_MIN = 1_262_304_000_000        # 2010-01-01 — older than any bar we'd want


def _ts_ms_max() -> int:
    """Newest acceptable candle ts: now + 2 days (tolerates clock skew, kills 2038)."""
    return int((_time.time() + 172_800) * 1000)
ET = ZoneInfo("America/New_York")

# ─── Store location — single definition, imported by every reader ─────────────

def feed_db_path() -> str:
    """Resolve the shared store path. $OT_FEED_DB overrides; default is
    self-locating inside the repo's data/ dir so producer and consumers on the
    same checkout always agree."""
    env = os.environ.get("OT_FEED_DB", "").strip()
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "feed_store.db")


# ─── Tunables ──────────────────────────────────────────────────────────────────

SESSION_OPEN_HM   = (9, 30)          # ET

FLUSH_INTERVAL_S  = 2.0              # buffer -> SQLite cadence (also heartbeat)
PRUNE_FACTOR      = 4                # legacy; unused while PRUNE_KEEP_ROWS is 0
# FEED.3: 0 = NO PRUNING (default). Set OT_PRUNE_KEEP_ROWS to a positive row
# count to re-enable a flat per-(symbol,interval) cap. Kept as a mechanism
# rather than deleted so it is one env var to reverse, not a code change.
PRUNE_KEEP_ROWS   = int(os.environ.get("OT_PRUNE_KEEP_ROWS", "0"))
# TERM.1: an auxiliary-tenor subscription older than this is ignored. Stale
# strikes burn socket budget against a measured ~40-session cap for contracts
# nothing reads.
AUX_MAX_AGE_S     = 6 * 3600
PRUNE_EVERY_S     = 300
RECONNECT_MIN_S   = 3

# v4.3 — FEED_WARM_LEAD_S and the is_rth/seconds_until_rth_open imports are
# GONE with the RTH gate. There is no longer an open to warm up to: the feed
# holds its subscriptions continuously while the box is up, so the frames are
# never cold. `OT_FEED_WARM_LEAD_S` is now INERT — if it is still set in a
# box .env it does nothing, which is stated here so a future reader does not
# spend an evening looking for the code that reads it.

# ── FEED MODE (FEED.1, 2026-08-15) — THE THIRD PURPOSE ───────────────────────
# `_feed_stood_down` (v4.3, formerly `_idle_outside_session`) already says the
# right thing: **"THE DISTINCTION IS
# PURPOSE, NOT TIME."** It only had TWO purposes — service (hold a socket for a
# live session) and one-shot (`--once`, pull history and exit). A `--once` run
# is therefore allowed at ANY hour, which is correct for the EOD pull and wrong
# for the thing v3.9 was actually protecting: **a maintenance wake that brings
# all 29 boxes up for work needing no market data.**
#
# Operator's requirement: a dedicated MAINTENANCE window where the whole fleet
# can be up for fleet updates "without involving the feed or using api
# resources". That cannot be expressed as a clock rule — maintenance and the
# overnight capture pass happen at the same hours and want opposite behaviour.
#
#   service      today's behaviour, unchanged. The default, so nothing moves.
#   capture      a scoped one-shot pull. Same as service for gating; the name
#                exists so a capture wake is DISTINGUISHABLE in the logs from a
#                trader wake, and so a future window argument has somewhere to
#                live.
#   maintenance  HARD OFF. No socket, no subscription, not even `--once`.
#
# ⚠️ AND IT MUST ANNOUNCE ITSELF. On 2026-08-03/04 the gate silently blocked the
# EOD pull: the log read `Feed idle — outside RTH` at INFO four times, then
# `0 bars`, and fourteen 38-byte header-only CSVs were written. Nothing raised,
# and DXFeed history is same-evening only, so BOTH SESSIONS ARE PERMANENTLY
# LOST. A maintenance-suppressed run must never look like a failed fetch: it
# logs at WARNING and says the mode by name.
# ⚠️ A SENTINEL FILE, NOT ONLY AN ENV VAR. `Environment=` in the unit is read
# ONCE AT IMPORT, so flipping the mode on a RUNNING feed would need a restart —
# and the restart window is precisely when the box is on the wire during the
# maintenance it is supposed to be excused from. The file is checked on every
# gate evaluation, so `touch`/`rm` takes effect on the next loop with nothing
# to restart and no race to lose.
MAINT_FLAG = os.environ.get(
    "OT_FEED_MAINT_FLAG",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "FEED_MAINTENANCE"))


def _maintenance_now() -> bool:
    """True if this box is in a maintenance window RIGHT NOW.

    Sentinel file first (live, no restart), env second (set at wake time).
    ⚠️ FAILS OPEN TO service ON AN UNREADABLE PATH: a box that cannot stat the
    flag must keep FEEDING, because the alternative is a silent tape loss that
    DXFeed's same-evening history makes permanent. A stray socket during
    maintenance is recoverable; a missing session is not.
    """
    try:
        if os.path.exists(MAINT_FLAG):
            return True
    except Exception:                                          # noqa: BLE001
        pass
    return FEED_MODE == "maintenance"


FEED_MODE = os.environ.get("OT_FEED_MODE", "service").strip().lower()
_VALID_FEED_MODES = ("service", "capture", "maintenance")
if FEED_MODE not in _VALID_FEED_MODES:
    # An unknown mode must not silently become "maintenance" (a box that never
    # feeds) NOR silently become "service" (a box on the wire during
    # maintenance). Fail to the DEFAULT and say so loudly.
    logging.getLogger(__name__).warning(
        "[feed-mode] OT_FEED_MODE=%r is not one of %s - falling back to "
        "'service'. Fix the unit/env; do not rely on this default.",
        FEED_MODE, ", ".join(_VALID_FEED_MODES))
    FEED_MODE = "service"
RECONNECT_MAX_S   = 60
# v5.2 (TTS.1) — JITTER ON EVERY RECONNECT WAIT. Fourteen boxes share one TastyTrade
# login's session ceiling; a server-side break hits them together, and a fixed
# ladder made them retry together (2026-09-29). +/-20% de-phases the retries.
RECONNECT_JITTER  = 0.20


def reconnect_wait(backoff: float, rng=None) -> float:
    """The seconds to sleep for this rung of the ladder: backoff scaled by a uniform
    factor in [1 - RECONNECT_JITTER, 1 + RECONNECT_JITTER], never below RECONNECT_MIN_S.
    `rng` (anything with .uniform) is for the gate; production passes nothing."""
    r = rng if rng is not None else random
    return max(float(RECONNECT_MIN_S),
               float(backoff) * r.uniform(1.0 - RECONNECT_JITTER, 1.0 + RECONNECT_JITTER))


# ── v5.6 (FEED.13) — RELEASE THE OLD, ALWAYS: ONE QUOTE TOKEN, ONE SOCKET, A LONG WAIT AT THE CEILING ─────────────────
# 2026-11-02 09:30 ET the DXLink socket dropped on 8 boxes at once; AMZN, GOOGL and TSLA were then refused on every
# ~60 s retry for 10-25+ minutes: "Fatal streamer error: The number of user sessions has exceeded the configured limit"
# (one TastyTrade login, 14 boxes). The SDK's DXLinkStreamer.__asynccontextmanager__ calls GET /api-quote-tokens on
# EVERY open, so every retry minted a NEW token while the server still held the dropped socket's session. The operator,
# 2026-11-02: "Release the old, ALWAYS."
#   (1) QuoteTokenCache: the token + dxlink-url are fetched once and REUSED on every reconnect; refreshed only when older
#       than QUOTE_TOKEN_MAX_AGE_S (20 h; TastyTrade quote tokens live 24 h), when the server answers AUTH with
#       UNAUTHORIZED, when it sends ERROR UNAUTHORIZED / a token-expired message, or when no AUTHORIZED arrives within
#       AUTH_TIMEOUT_S (a server that silently ignored a reused token would otherwise hang the feed with no reconnect).
#       The token itself is never logged.
#   (2) The SDK's path already closes the socket on every exception route (httpx2's session closes in a shielded
#       `finally`, then the response and the AsyncClient); SessionReleasingStreamer keeps that body and adds a
#       `finally` of its own that closes the socket explicitly if anything left it open (bounded by WS_CLOSE_TIMEOUT_S),
#       and closes any socket still recorded as open BEFORE a new one is dialled.
#   (3) A session-limit refusal starts a LOCKOUT: the next wait is session_limit_wait(0) - uniform [120, 180] s - and
#       every wait after it, whatever the error, is session_limit_wait(n >= 1) - [200, 300] s - until a connection
#       succeeds (subscriptions live), which clears it. This holds from the very first attempt after a process start:
#       a fresh feed begins on the 3 s rung, and 2026-11-02 09:57 AMZN, restarted into the lockout, made ~16 refused
#       attempts in 90 s on the 3/6/12 s rungs. Each refusal logs ONE SESSION_LIMIT line with its wait. Without a
#       session-limit refusal every other error keeps the jittered 3 -> 60 s ladder exactly as before.
#       WHY A LONG HOLD: 2026-09-29 measured ~36 sessions on the login (17 boxes x 2); on 11-02 ~14 boxes were live,
#       so the ceiling was most likely reached by refused attempts counting as sessions server-side for some minutes,
#       each attempt minting a new token - retrying fast only refills the ceiling it is waiting on.
# No SDK file and no venv is changed: the subclass replaces only the context manager; _reader, _heartbeat and every
# subscribe call are the SDK's own (they see the socket through _AuthWatch, which forwards everything).
QUOTE_TOKEN_MAX_AGE_S     = 20 * 3600
AUTH_TIMEOUT_S            = 45.0
WS_CLOSE_TIMEOUT_S        = 5.0
SESSION_LIMIT_WAIT_MIN_S  = 120.0       # the floor of every wait while the lockout is held
SESSION_LIMIT_WAIT_MAX_S  = 180.0       # the first lockout wait is uniform [MIN, MAX]
SESSION_LIMIT_WAIT_CAP_S  = 300.0       # later lockout waits: 250 s +/-20% = [200, 300]
_SESSION_LIMIT_RUNG_S     = (150.0, 250.0)
_SESSION_LIMIT_TEXT       = "number of user sessions has exceeded"


def session_limit_wait(level: int = 0, rng=None) -> float:
    """Seconds to wait inside a session-limit lockout. level 0 (the refusal just seen) is uniform in
    [SESSION_LIMIT_WAIT_MIN_S, SESSION_LIMIT_WAIT_MAX_S] = [120, 180]; level >= 1 (still locked out) is 250 s +/-20%,
    [200, 300]. Never below 120 s, never above SESSION_LIMIT_WAIT_CAP_S. `rng` is for the gate."""
    r = rng if rng is not None else random
    rung = _SESSION_LIMIT_RUNG_S[0] if level <= 0 else _SESSION_LIMIT_RUNG_S[1]
    w = rung * r.uniform(1.0 - RECONNECT_JITTER, 1.0 + RECONNECT_JITTER)
    return float(min(SESSION_LIMIT_WAIT_CAP_S, max(SESSION_LIMIT_WAIT_MIN_S, w)))


def _is_session_limit(e) -> bool:
    """True when the error (or anything wrapped inside it) is TastyTrade's session-ceiling refusal."""
    return _SESSION_LIMIT_TEXT in _explain_exc(e).lower()


def _is_auth_error_text(text: str) -> bool:
    t = (text or "").lower()
    if _SESSION_LIMIT_TEXT in t:
        return False
    return "unauthorized" in t or ("token" in t and ("expired" in t or "invalid" in t))


class QuoteTokenRejected(Exception):
    """DXLink refused (or never accepted) the cached quote token; the cache is already invalidated."""


class QuoteTokenCache:
    """The one /api-quote-tokens answer this process holds. `clock` is for the gate."""

    def __init__(self, max_age_s: float = None, clock=None):
        self.max_age_s = max_age_s
        self.clock = clock or _time.time
        self._url = self._token = None
        self._fetched_at = None
        self._session_id = None
        self._stale_reason = None
        self.fetches = 0
        self.reuses = 0

    def age_s(self) -> Optional[float]:
        return None if self._fetched_at is None else self.clock() - self._fetched_at

    def invalidate(self, reason: str) -> None:
        if self._token is not None:
            logger.warning("FEED.13 quote token dropped (%s) - the next connect fetches a new one", reason)
        self._url = self._token = self._fetched_at = None
        self._stale_reason = reason

    async def get(self, session) -> Tuple[str, str]:
        max_age = QUOTE_TOKEN_MAX_AGE_S if self.max_age_s is None else self.max_age_s
        age = self.age_s()
        if self._token is not None and self._session_id == id(session) and age is not None and age < max_age:
            self.reuses += 1
            logger.info("FEED.13 quote token reused (age %.0fs, reuse #%d)", age, self.reuses)
            return self._url, self._token
        why = (self._stale_reason or "first connect") if self._token is None else (
            "older than %.0fs" % max_age if self._session_id == id(session) else "new session")
        data = await session._get("/api-quote-tokens")
        self._url, self._token = data["dxlink-url"], data["token"]
        self._fetched_at, self._session_id, self._stale_reason = self.clock(), id(session), None
        self.fetches += 1
        logger.info("FEED.13 quote token fetched (%s; fetch #%d)", why, self.fetches)
        return self._url, self._token


_QUOTE_TOKENS = QuoteTokenCache()
_OPEN_WS = {"ws": None}          # the one socket this process has open, if any


# ── FEED.13 (2) — THE DXLINK NODE IS CHOSEN, A REFUSED NODE IS LEFT AT ONCE, AND THE FLEET SPREADS BEFORE THE OPEN ──
# MEASURED 2026-11-02 10:50 ET: tasty-openapi-dxlink-md-ws.dxfeed.com resolves to different backend nodes. Ten boxes and
# AMZN/GOOGL got 129.153.134.53 on every lookup; TSLA (recovered 09:40) and UNH were on AWS nodes 184.195.238.144 and
# 54.204.44.247. AMZN/GOOGL were refused "user sessions exceeded" for 85 min on 129.153.134.53 and connected AT ONCE when
# pinned (/etc/hosts, temporary) to the AWS nodes: the session limit is PER NODE, and the 09:30 mass reconnect herded
# the boxes onto one. Later the same day six public resolvers (Google, Cloudflare, Quad9, OpenDNS) all answered only
# 129.153.134.53 with no CNAME, so the answer changes over time and one lookup cannot find the others.
# The operator: "if we have control over the connections, then spread them out", then "Yes, connect to a known new
# server & if we can probe to spread out our connections prior to the open, it might be worth looking into."
# CANDIDATES (no IP is written in this code): (a) this box's book, data/dxlink_nodes.json beside the feed store - every
# IPv4 A record it has resolved (re-resolved at each connect) and every node it connected to or probed; (b) the FLEET
# list, dxlink_nodes_fleet.json beside it, merged from every box's book by warehouse/s3_push.py through S3
# (fleet/dxlink_nodes/), so a node any box has seen is known to all; (c) the seed, data/dxlink_nodes_seed.json, the
# nodes observed 2026-11-02. The socket is dialled to the chosen IP while the URL's hostname stays the TLS SNI name
# (httpcore2's `sni_hostname` extension), the certificate check (verify stays on) and the Host header. Choice:
#   PRE-OPEN (ET clock before 09:30): every un-cooled candidate is probed - TCP, TLS with SNI and the certificate
#      checked, ONE bare websocket upgrade request, the status line read, closed at once (no SETUP, no AUTH, no
#      quote token); a node answering 101 is usable, a 5xx (129.153.134.53 answered 502 from 14:19 ET 11-02 while
#      its TLS was normal) or anything else is not; the usable ones are ranked by crc32(symbol) and the box takes its
#      own - stickiness is ignored, so the fleet starts the session spread instead of herded;
#   OTHERWISE: 1. the last node that connected, unless it is cooling (sticky: a working node is never left for
#      spread); 2. else the usable candidates ranked by crc32(symbol); 3. else the first fresh DNS answer, and if DNS
#      fails too, the plain URL (normal DNS).
# A node that refused for the session limit cools NODE_REFUSED_COOLDOWN_S (30 min) on this box; one that failed before
# AUTHORIZED for any other reason (a 502 upgrade among them) cools NODE_FAIL_COOLDOWN_S (5 min). With an un-cooled alternate known, run() redials
# after node_switch_wait() (1-5 s) instead of the 120-300 s lockout hold. A book or fleet node unseen and unused for
# NODE_FORGET_S (14 days) is dropped; the seed is always a candidate (a dead one fails its probe or cools 5 min).
# Never raises: any fault falls back to the plain URL.
# v5.9 (r74, ORP.3) — the opening-tape rescue's window and cadence (see _maybe_rescue_opening_range).
ORB_RESCUE_UNTIL_ET = (15, 0)
ORB_RESCUE_MAX = 6
ORB_RESCUE_EVERY_S = 120.0
NODE_REFUSED_COOLDOWN_S = 30 * 60
NODE_FAIL_COOLDOWN_S    = 5 * 60
NODE_FORGET_S           = 14 * 86400
NODE_DNS_TIMEOUT_S      = 5.0
NODE_PROBE_TIMEOUT_S    = 3.0
NODE_SWITCH_WAIT_S      = (1.0, 5.0)
_LAST_ATTEMPT = {"ip": None, "authorized": False}     # the node the current/last dial went to

# ── v5.9 (r74, FEED.15) — CONTROL ASSIGNS THE NODE ───────────────────────────────────────────────────────────────────
# dtp tools/dxlink_assign.py (after the 09:15 wake, from control's own probe) writes data/dxlink_assign.json beside the
# feed store over ssh: {"date": "YYYY-MM-DD" (ET), "symbol": <this box's symbol>, "node": <IPv4>, "written_at": epoch,
# "by": ...}. choose() dials the assigned node FIRST at every connect (pre-open only after it answers its own probe 101;
# never while it is cooling), then the normal order above. A file that is missing, unreadable, for another day or
# symbol, older than ASSIGN_MAX_AGE_S, from the future or naming a non-IPv4 node is ignored, with one log line a day
# per reason. Before ASSIGN_SWITCH_BY_ET a box already connected elsewhere switches to a fresh assignment ONCE a day
# (a planned reconnect: the old socket closed first by SessionReleasingStreamer, redial in 1-5 s, no node cooled).
ASSIGN_MAX_AGE_S = 12 * 3600
ASSIGN_FUTURE_SLACK_S = 300
ASSIGN_SWITCH_BY_ET = (9, 27)


class PlannedNodeSwitch(Exception):
    """v5.9 (r74, FEED.15) — raised inside the stream to leave a working node for control's assignment, pre-open."""


def _planned_switch(e) -> Optional[BaseException]:
    """The PlannedNodeSwitch in e or anywhere inside it (an anyio task group wraps the stream body's exceptions in an
    ExceptionGroup), else None."""
    seen, stack = 0, [e]
    while stack and seen < 64:
        x = stack.pop()
        seen += 1
        if isinstance(x, PlannedNodeSwitch):
            return x
        stack.extend(getattr(x, "exceptions", None) or ())
        for nxt in (getattr(x, "__cause__", None), getattr(x, "__context__", None)):
            if nxt is not None:
                stack.append(nxt)
    return None


def _assign_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(feed_db_path())), "dxlink_assign.json")


def read_assignment(path: str, symbol: str, now_epoch: float, today_et: str) -> Tuple[Optional[str], str]:
    """(node, why) from control's assignment file; node None when it must be ignored, `why` saying why."""
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return None, "no control assignment file"
    except Exception as exc:                                               # noqa: BLE001
        return None, "control assignment unreadable (%s)" % type(exc).__name__
    if not isinstance(d, dict):
        return None, "control assignment is not an object"
    if str(d.get("date", "")) != today_et:
        return None, "control assignment is for %s, not today" % d.get("date")
    if str(d.get("symbol", "")).upper() != str(symbol).upper():
        return None, "control assignment names %s, not this box" % d.get("symbol")
    try:
        age = now_epoch - float(d.get("written_at"))
    except (TypeError, ValueError):
        return None, "control assignment has no written_at"
    if age > ASSIGN_MAX_AGE_S or age < -ASSIGN_FUTURE_SLACK_S:
        return None, "control assignment is stale (age %.0fs)" % age
    ip = d.get("node")
    if not _valid_v4(ip):
        return None, "control assignment names no IPv4 node (%r)" % ip
    return str(ip), "control assignment (%s)" % (d.get("by") or "control")


def node_switch_wait(rng=None) -> float:
    """Seconds before redialling a DIFFERENT node after a refusal: uniform in NODE_SWITCH_WAIT_S (1-5 s)."""
    r = rng if rng is not None else random
    return float(r.uniform(*NODE_SWITCH_WAIT_S))


def _preopen(now_et: Optional[datetime] = None) -> bool:
    """True before the 09:30 ET open (the 09:15 wake and any restart before the bell)."""
    t = (now_et or datetime.now(ET)).time()
    return t < dtime(*SESSION_OPEN_HM)


def _nodes_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(feed_db_path())), "dxlink_nodes.json")


def _fleet_nodes_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(feed_db_path())), "dxlink_nodes_fleet.json")


def _seed_nodes_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "dxlink_nodes_seed.json")


def _valid_v4(ip) -> bool:
    try:
        import ipaddress
        return isinstance(ipaddress.ip_address(str(ip)), ipaddress.IPv4Address)
    except Exception:                                                      # noqa: BLE001
        return False


async def _resolve_v4(host: str, port: int) -> List[str]:
    """Every IPv4 A record for host, in the resolver's order. [] on any failure."""
    try:
        import anyio
        with fail_after(NODE_DNS_TIMEOUT_S):
            infos = await anyio.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
        out = []
        for info in infos:
            ip = info[4][0]
            if ip not in out:
                out.append(ip)
        return out
    except Exception as exc:                                               # noqa: BLE001
        logger.warning("FEED.13 dxlink DNS lookup of %s failed (%s)", host, _explain_exc(exc))
        return []


# ── FEED.13 (3) — THE AUTHORITATIVE NAMESERVERS ARE ASKED TOO ─────────────────────────────────────────────────────────
# MEASURED 2026-11-02/03: the recursive resolvers (the VPC resolver and six public ones) answered ONE node at a time for
# tasty-openapi-dxlink-md-ws.dxfeed.com (129.153.134.53 on 11-02, 52.6.43.252 / 184.195.238.144 on 11-03), while the
# zone's own Route 53 nameservers (ns-313.awsdns-39.com and its peers, TTL 60) answered the AWS pair; 54.204.44.247,
# UNH's answer on the morning of 11-02, timed out that evening and failed TLS verification on 11-03 (it is not a dxlink
# node any more, and is not in the seed). So every lookup also asks the authoritative nameservers directly: the zone's
# NS set is found through the system resolver (the host, then its parents, longest first; on 11-03 the host
# itself is delegated to Route 53 while dxfeed.com is on devexperts.com's servers), each NS name is resolved, and each
# is asked for the host's A records over UDP (stdlib only - no dnspython on the boxes). The NS set is cached
# NODE_AUTH_NS_TTL_S (1 h). Their answers are appended AFTER the recursive answer (whose first record is what the
# plain URL would dial), so the order of fresh[0] is unchanged. Bounded by NODE_DNS_TIMEOUT_S; never raises: any fault
# returns [] and the recursive answer stands alone. Nothing here sends a token or opens a websocket.
NODE_AUTH_NS_TTL_S = 3600
NODE_AUTH_NS_MAX = 4
NODE_DNS_PORT = 53
_AUTH_NS_CACHE = {"host": None, "ns": [], "at": 0.0}


def _dns_query_bytes(name: str, qtype: int, qid: int) -> bytes:
    """One standard query (RD set) for name/qtype, class IN."""
    import struct
    q = b"".join(bytes([len(lab)]) + lab.encode("ascii") for lab in name.strip(".").split(".") if lab) + b"\0"
    return struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0) + q + struct.pack(">HH", qtype, 1)


def _dns_read_name(buf: bytes, off: int) -> Tuple[str, int]:
    """A (possibly compressed) domain name at off -> (name, offset after it). Pointer loops are bounded."""
    labels, jumped, end, hops = [], False, off, 0
    while True:
        if off >= len(buf) or hops > 64:
            raise ValueError("bad name")
        n = buf[off]
        if n & 0xC0 == 0xC0:
            if off + 1 >= len(buf):
                raise ValueError("bad pointer")
            if not jumped:
                end = off + 2
            off = ((n & 0x3F) << 8) | buf[off + 1]
            jumped, hops = True, hops + 1
            continue
        if n == 0:
            if not jumped:
                end = off + 1
            return ".".join(labels), end
        labels.append(buf[off + 1:off + 1 + n].decode("ascii", "replace"))
        off += 1 + n


def _dns_parse(buf: bytes, qid: int, qtype: int) -> List[str]:
    """The answer section's records of qtype: A -> dotted IPv4, NS -> the nameserver name. [] on a bad/foreign reply."""
    import struct
    if len(buf) < 12:
        return []
    rid, flags, qd, an, _ns, _ar = struct.unpack(">HHHHHH", buf[:12])
    if rid != qid or not flags & 0x8000 or flags & 0x000F:
        return []
    off = 12
    for _ in range(qd):
        _, off = _dns_read_name(buf, off)
        off += 4
    out = []
    for _ in range(an):
        _, off = _dns_read_name(buf, off)
        if off + 10 > len(buf):
            break
        rtype, _rcls, _ttl, rdlen = struct.unpack(">HHIH", buf[off:off + 10])
        off += 10
        rdata_off = off
        off += rdlen
        if rtype != qtype:
            continue
        if qtype == 1 and rdlen == 4:
            out.append(".".join(str(b) for b in buf[rdata_off:rdata_off + 4]))
        elif qtype == 2:
            out.append(_dns_read_name(buf, rdata_off)[0])
    return out


def _dns_udp(server: str, name: str, qtype: int, timeout: float) -> List[str]:
    """Ask server (an IPv4 address) for name/qtype over UDP. [] on any failure."""
    qid = random.randint(1, 0xFFFF)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(max(0.2, timeout))
            s.sendto(_dns_query_bytes(name, qtype, qid), (server, NODE_DNS_PORT))
            buf, _ = s.recvfrom(4096)
        return _dns_parse(buf, qid, qtype)
    except Exception:                                                      # noqa: BLE001
        return []


def _system_nameservers() -> List[str]:
    """The IPv4 nameservers in /etc/resolv.conf (the VPC resolver on a box)."""
    out = []
    try:
        with open("/etc/resolv.conf", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "nameserver" and _valid_v4(parts[1]):
                    out.append(parts[1])
    except Exception:                                                      # noqa: BLE001
        pass
    return out


def _authoritative_ns_ips(host: str, deadline: float, clock=None) -> List[str]:
    """IPv4 addresses of the authoritative nameservers for host's zone (cached NODE_AUTH_NS_TTL_S)."""
    now = (clock or _time.time)()
    c = _AUTH_NS_CACHE
    if c["host"] == host and c["ns"] and now - c["at"] < NODE_AUTH_NS_TTL_S:
        return list(c["ns"])
    resolvers = _system_nameservers()
    labels = host.strip(".").split(".")
    names = []
    for i in range(0, max(1, len(labels) - 1)):             # the host itself first (it is delegated)
        zone = ".".join(labels[i:])
        for r in resolvers:
            left = deadline - _time.monotonic()
            if left <= 0:
                return []
            names = _dns_udp(r, zone, 2, min(1.5, left))
            if names:
                break
        if names:
            break
    ips = []
    for nm in sorted(set(names))[:NODE_AUTH_NS_MAX]:
        if deadline - _time.monotonic() <= 0:
            break
        try:
            for info in socket.getaddrinfo(nm, NODE_DNS_PORT, family=socket.AF_INET, type=socket.SOCK_DGRAM):
                ip = info[4][0]
                if ip not in ips:
                    ips.append(ip)
                break
        except Exception:                                                  # noqa: BLE001
            continue
    if ips:
        c.update(host=host, ns=list(ips), at=now)
    return ips


def _authoritative_v4_sync(host: str, budget: float) -> List[str]:
    deadline = _time.monotonic() + budget
    out = []
    for ns in _authoritative_ns_ips(host, deadline):
        left = deadline - _time.monotonic()
        if left <= 0:
            break
        for ip in _dns_udp(ns, host, 1, min(1.5, left)):
            if _valid_v4(ip) and ip not in out:
                out.append(ip)
    return out


async def _resolve_authoritative(host: str) -> List[str]:
    """host's A records as its zone's authoritative nameservers answer them. [] on any failure."""
    try:
        import anyio
        with fail_after(NODE_DNS_TIMEOUT_S + 1.0):
            return await anyio.to_thread.run_sync(_authoritative_v4_sync, host, NODE_DNS_TIMEOUT_S)
    except Exception as exc:                                               # noqa: BLE001
        logger.warning("FEED.13 authoritative DNS lookup of %s failed (%s)", host, _explain_exc(exc))
        return []


async def _resolve_nodes(host: str, port: int) -> List[str]:
    """The recursive answer first (what the plain URL dials), then any node only the authoritative servers named."""
    rec = await _resolve_v4(host, port)
    auth = await _resolve_authoritative(host)
    extra = [ip for ip in auth if ip not in rec]
    if extra:
        logger.info("FEED.13 authoritative DNS named %d node(s) the resolver did not (%s)", len(extra), ", ".join(extra))
    return rec + extra


def _upgrade_request(host: str, path: str) -> bytes:
    """The exact bytes a probe sends: ONE bare websocket upgrade request and nothing else - no SETUP, no AUTH, no quote
    token (the same request as dtp tools/dxlink_probe.py)."""
    import base64
    key = base64.b64encode(os.urandom(16)).decode()
    return ("GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\nUser-Agent: otv5-candle-feed-probe\r\n\r\n"
            % (path or "/", host, key)).encode("ascii")


async def _probe_node(ip: str, host: str, port: int, path: str = "/realtime", ssl_context=None) -> Optional[int]:
    """Is this node USABLE? TCP to ip, TLS with SNI = host and the certificate checked against host, then one bare
    websocket upgrade request (Host = host); only the STATUS LINE is read and the socket is closed at once. Returns
    the HTTP status (101 = usable; 5xx or anything else = not), or None when TCP/TLS/the read failed. MEASURED
    2026-11-02 from 14:19 ET: 129.153.134.53 completed TLS normally and answered every upgrade "HTTP/1.1 502 Bad
    Gateway", so a TLS-only probe would have called it reachable. Never raises."""
    stream = None
    try:
        import ssl
        import anyio
        ctx = ssl_context or ssl.create_default_context()
        with fail_after(NODE_PROBE_TIMEOUT_S):
            stream = await anyio.connect_tcp(ip, port, ssl_context=ctx, tls_hostname=host,
                                             tls_standard_compatible=False)
            await stream.send(_upgrade_request(host, path))
            buf = b""
            while b"\r\n" not in buf and len(buf) < 1024:
                chunk = await stream.receive(1024 - len(buf))
                if not chunk:
                    break
                buf += chunk
        parts = buf.split(b"\r\n", 1)[0].decode("latin-1", "replace").strip().split(" ", 2)
        if len(parts) >= 2 and parts[0].startswith("HTTP/") and parts[1].isdigit():
            return int(parts[1])
        return None
    except Exception:                                                      # noqa: BLE001
        return None
    finally:
        if stream is not None:
            try:
                with CancelScope(shield=True):
                    with fail_after(1.0):
                        await stream.aclose()
            except Exception:                                              # noqa: BLE001
                pass


def _probe_usable(result) -> bool:
    return result is True or result == 101


def _upgrade_status(e, _depth=0) -> Optional[int]:
    """The HTTP status of a refused websocket upgrade anywhere in e (groups, causes), else None."""
    if e is None or _depth > 5:
        return None
    try:
        from httpx2.websockets import WebSocketUpgradeError
        if isinstance(e, WebSocketUpgradeError):
            code = getattr(getattr(e, "response", None), "status_code", None)
            return int(code) if code is not None else None
    except Exception:                                                      # noqa: BLE001
        pass
    for sub in list(getattr(e, "exceptions", None) or []) + [getattr(e, "__cause__", None),
                                                               getattr(e, "__context__", None)]:
        if sub is not None and sub is not e:
            c = _upgrade_status(sub, _depth + 1)
            if c is not None:
                return c
    return None


class NodeBook:
    """The dxlink nodes this box knows. Every path, the clock, the resolver and the prober are for the gate."""

    def __init__(self, path: str = None, clock=None, resolver=None, fleet_path: str = None, seed_path: str = None,
                 prober=None, assign_path: str = None, symbol: str = None, today=None):
        self._path, self._fleet_path, self._seed_path = path, fleet_path, seed_path
        self.clock = clock or _time.time
        self.resolver = resolver or _resolve_nodes                          # v5.6 r70 (3): + authoritative NS
        self.prober = prober or _probe_node
        self._data = None
        self._assign_path, self._symbol = assign_path, symbol               # v5.9 (r74, FEED.15)
        self._today = today or (lambda: datetime.now(ET).date().isoformat())
        self._assign_noted: set = set()

    def assignment(self, symbol: str = None) -> Tuple[Optional[str], str]:
        """v5.9 (r74, FEED.15) — (node, why): control's assignment for this box, or None with the reason (one log line
        a day per reason). Never raises."""
        try:
            sym = symbol or self._symbol or INSTRUMENT
            ip, why = read_assignment(self._assign_path or _assign_path(), sym, self.clock(), self._today())
            key = (self._today(), why if ip is None else "ok:" + ip)
            if key not in self._assign_noted:
                self._assign_noted.add(key)
                if ip:
                    logger.info("FEED.15 %s: node %s", why, ip)
                else:
                    logger.info("FEED.15 %s - normal node choice", why)
            return ip, why
        except Exception as exc:                                           # noqa: BLE001
            return None, "control assignment failed (%s)" % type(exc).__name__

    def path(self) -> str:
        return self._path or _nodes_path()

    def _load(self) -> dict:
        if self._data is None:
            try:
                with open(self.path(), encoding="utf-8") as fh:
                    d = json.load(fh)
                self._data = d if isinstance(d, dict) else {}
            except Exception:                                              # noqa: BLE001
                self._data = {}
            self._data.setdefault("nodes", {})
        return self._data

    def _save(self) -> None:
        try:
            p = self.path()
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=1, sort_keys=True)
            os.replace(tmp, p)
        except Exception as exc:                                           # noqa: BLE001
            logger.warning("FEED.13 dxlink node book not saved (%s)", exc)

    @staticmethod
    def _read_nodes(path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            nodes = d.get("nodes", {}) if isinstance(d, dict) else {}
            return {ip: (n if isinstance(n, dict) else {}) for ip, n in nodes.items() if _valid_v4(ip)}
        except Exception:                                                  # noqa: BLE001
            return {}

    def _node(self, ip: str) -> dict:
        return self._load()["nodes"].setdefault(ip, {})

    def _cool_until(self, ip: str) -> float:
        n = self._load()["nodes"].get(ip, {})
        return max(n.get("refused", 0) + NODE_REFUSED_COOLDOWN_S if n.get("refused") else 0,
                   n.get("failed", 0) + NODE_FAIL_COOLDOWN_S if n.get("failed") else 0)

    def candidates(self) -> List[str]:
        """Every node known from the book, the fleet list and the seed (the seed is never forgotten)."""
        now = self.clock()

        def fresh(n):
            return now - max([float(n.get(k, 0) or 0) for k in ("seen", "ok", "reachable")] or [0]) <= NODE_FORGET_S
        out = {ip for ip, n in self._load()["nodes"].items() if _valid_v4(ip) and fresh(n)}
        out |= {ip for ip, n in self._read_nodes(self._fleet_path or _fleet_nodes_path()).items() if fresh(n)}
        out |= set(self._read_nodes(self._seed_path or _seed_nodes_path()))
        return sorted(out)

    def usable(self) -> List[str]:
        now = self.clock()
        return [ip for ip in self.candidates() if self._cool_until(ip) <= now]

    def alternate_available(self) -> bool:
        """True when some known node is not cooling - after a refusal (which cools the refusing node) that is a
        DIFFERENT node, so run() redials at once."""
        try:
            return bool(self.usable())
        except Exception:                                                  # noqa: BLE001
            return False

    @staticmethod
    def _by_hash(ips: List[str], symbol: str) -> str:
        ips = sorted(ips)
        return ips[zlib.crc32(str(symbol).encode()) % len(ips)]

    async def choose(self, host: str, port: int, symbol: str, preopen: bool = False,
                     path: str = "/realtime") -> Tuple[Optional[str], str]:
        """(ip, why). ip None = dial the plain URL (normal DNS)."""
        try:
            now = self.clock()
            fresh = await self.resolver(host, port)
            d = self._load()
            for ip in fresh:
                if _valid_v4(ip):
                    self._node(ip)["seen"] = now
            for ip in list(d["nodes"]):
                n = d["nodes"][ip]
                if now - max(n.get("seen", 0), n.get("ok", 0), n.get("reachable", 0)) > NODE_FORGET_S:
                    del d["nodes"][ip]
            asg, asg_why = self.assignment(symbol)                          # v5.9 (r74, FEED.15): control's node first
            if asg:
                self._node(asg)["seen"] = now
                if self._cool_until(asg) > now:
                    logger.warning("FEED.15 assigned node %s is cooling on this box - normal node choice", asg)
                elif preopen:
                    code = await self.prober(asg, host, port, path=path)
                    if _probe_usable(code):
                        self._node(asg)["reachable"] = now
                        self._save()
                        return asg, asg_why + ", pre-open probe 101"
                    logger.warning("FEED.15 assigned node %s failed its pre-open probe (%s) - normal node choice",
                                   asg, "HTTP %s" % code if code else "no answer")
                else:
                    self._save()
                    return asg, asg_why
            usable = self.usable()
            if preopen and usable:
                import anyio
                res = {}

                async def _one(ip):
                    res[ip] = await self.prober(ip, host, port, path=path)
                async with anyio.create_task_group() as tg:
                    for ip in usable:
                        tg.start_soon(_one, ip)
                reach = [ip for ip in usable if _probe_usable(res.get(ip))]
                for ip in reach:
                    self._node(ip)["reachable"] = now
                self._save()
                logger.info("FEED.13 pre-open probe: %d/%d node(s) reachable (%s)", len(reach), len(usable),
                            ", ".join("%s %s" % (ip, "ok" if _probe_usable(res.get(ip)) else
                                                 ("HTTP %s" % res.get(ip) if res.get(ip) else "no answer"))
                                      for ip in usable))
                if reach:
                    return self._by_hash(reach, symbol), ("pre-open spread by symbol hash over %d reachable node(s)"
                                                          % len(reach))
            self._save()
            last = d.get("last_ok")
            if last in usable:
                return last, "last good node"
            if usable:
                return self._by_hash(usable, symbol), "spread by symbol hash over %d node(s)" % len(usable)
            if fresh:
                return fresh[0], "dns (no usable alternate known)"
            return None, "dns (plain URL; no node known)"
        except Exception as exc:                                           # noqa: BLE001
            logger.warning("FEED.13 dxlink node choice failed (%s) - plain URL", _explain_exc(exc))
            return None, "dns (plain URL; node choice failed)"

    def refused(self, ip: Optional[str]) -> None:
        if ip:
            self._node(ip)["refused"] = self.clock()
            if self._load().get("last_ok") == ip:
                self._data["last_ok"] = None
            self._save()

    def failed(self, ip: Optional[str]) -> None:
        if ip:
            self._node(ip)["failed"] = self.clock()
            self._save()

    def ok(self, ip: Optional[str]) -> None:
        if ip:
            n = self._node(ip)
            n["ok"] = self.clock()
            n.pop("refused", None)
            n.pop("failed", None)
            self._data["last_ok"] = ip
            self._save()


_NODES = NodeBook()


def _pinned_target(url: str, ip: Optional[str]):
    """(dial_url, headers, extensions) for a websocket to `url` dialled at `ip`, keeping the hostname for SNI, the
    certificate check and the Host header. ip None -> the URL unchanged, no headers, no extensions."""
    if not ip:
        return url, None, None
    u = urlsplit(url)
    host = u.hostname
    netloc = ip if u.port is None else "%s:%d" % (ip, u.port)
    host_hdr = host if u.port is None else "%s:%d" % (host, u.port)
    return urlunsplit((u.scheme, netloc, u.path, u.query, u.fragment)), {"Host": host_hdr}, {"sni_hostname": host}


def _ws_closed(ws) -> bool:
    flag = getattr(ws, "_should_close", None)       # httpx2 AsyncWebSocketSession sets it first thing in close()
    try:
        return bool(flag is not None and flag.is_set())
    except Exception:                                                      # noqa: BLE001
        return False


async def _release_ws(where: str) -> bool:
    """Close the recorded socket if it is still open. True when an explicit close was needed. Never raises."""
    ws, _OPEN_WS["ws"] = _OPEN_WS["ws"], None
    if ws is None or _ws_closed(ws):
        return False
    logger.warning("FEED.13 websocket still open %s - closing it before going on", where)
    with CancelScope(shield=True):
        try:
            with fail_after(WS_CLOSE_TIMEOUT_S):
                await ws.close()
        except Exception as exc:                                            # noqa: BLE001
            logger.warning("FEED.13 websocket close %s failed (%s) - aborting its stream", where, _explain_exc(exc))
            try:
                with fail_after(WS_CLOSE_TIMEOUT_S):
                    await ws.stream.aclose()
            except Exception:                                               # noqa: BLE001
                pass
    return True


class _AuthWatch:
    """The SDK's socket, seen by the SDK's own _reader/_heartbeat/subscribe; notes AUTH and reads its answer."""

    def __init__(self, ws, cache: QuoteTokenCache):
        self._ws, self._cache, self._auth_sent = ws, cache, False

    def __getattr__(self, name):
        return getattr(self._ws, name)

    async def send_json(self, message, *args, **kwargs):
        if isinstance(message, dict) and message.get("type") == "AUTH":
            self._auth_sent = True
        return await self._ws.send_json(message, *args, **kwargs)

    async def receive_json(self, *args, **kwargs):
        message = await self._ws.receive_json(*args, **kwargs)
        if isinstance(message, dict):
            kind = message.get("type")
            if kind == "AUTH_STATE" and message.get("state") == "UNAUTHORIZED" and self._auth_sent:
                self._cache.invalidate("DXLink answered AUTH with UNAUTHORIZED")
                raise QuoteTokenRejected("DXLink answered AUTH with UNAUTHORIZED - quote token refused")
            if kind == "ERROR" and (str(message.get("error", "")).upper() == "UNAUTHORIZED"
                                    or _is_auth_error_text(str(message.get("message", "")))):
                self._cache.invalidate("DXLink ERROR %s" % message.get("error", "?"))
        return message


class SessionReleasingStreamer(DXLinkStreamer):
    """DXLinkStreamer with the token reused across reconnects and the old socket always released (FEED.13).
    The body is the SDK __asynccontextmanager__ (identical in 13.2.2 and the boxes' locked 13.2.3) with three changes: the token comes from `_QUOTE_TOKENS`,
    the socket is wrapped in _AuthWatch with AUTH bounded by AUTH_TIMEOUT_S, and a `finally` releases the socket."""

    @asynccontextmanager
    async def __asynccontextmanager__(self):
        cache = _QUOTE_TOKENS
        await _release_ws("before a new connect")
        self._wss_url, self._auth_token = await cache.get(self.session)
        u = urlsplit(self._wss_url)
        ip, why = await _NODES.choose(u.hostname, u.port or 443, INSTRUMENT, preopen=_preopen(), path=u.path or "/")
        _LAST_ATTEMPT["ip"], _LAST_ATTEMPT["authorized"] = ip, False
        dial_url, headers, extensions = _pinned_target(self._wss_url, ip)
        logger.info("FEED.13 dxlink node %s for %s (%s)", ip or "dns", u.hostname, why)
        async with AsyncClient(**self.session.client_kwargs) as client:
            try:
                async with client.websocket(dial_url, keepalive_ping_interval_seconds=None,
                                            headers=headers, extensions=extensions) as raw_ws:
                    _OPEN_WS["ws"] = raw_ws
                    self._websocket = _AuthWatch(raw_ws, cache)
                    async with create_task_group() as tg:
                        try:
                            with fail_after(AUTH_TIMEOUT_S):
                                await tg.start(self._reader)
                        except TimeoutError:
                            cache.invalidate("no AUTHORIZED within %.0fs" % AUTH_TIMEOUT_S)
                            raise QuoteTokenRejected("no AUTHORIZED within %.0fs" % AUTH_TIMEOUT_S) from None
                        _LAST_ATTEMPT["authorized"] = True
                        tg.start_soon(self._heartbeat)
                        yield self
                        tg.cancel_scope.cancel()
            except* WebSocketDisconnect as eg:
                if eg.subgroup(lambda e: getattr(e, "code", None) == 1009):
                    raise TastytradeError(
                        "Subscription message too long! Try reducing the number of symbols.") from eg
                raise
            finally:
                await _release_ws("after the stream ended")
def _is_ext_route(store_symbol: str) -> bool:
    """v3.17 — is this store symbol the extended-hours stream?"""
    return str(store_symbol or "").endswith("_EXT")


# v3.17 — RTH windows by interval, in ET, as (start, end) inclusive of start
# and exclusive of end. Interval-aware because DXFeed aligns hour bars to the
# HOUR: the 09:00 ET hour bar contains the 09:30 open and is legitimate RTH
# data, while a 09:00 ET *minute* bar is pre-market. Getting this wrong in the
# permissive direction leaves contamination; getting it wrong in the strict
# direction deletes real bars, so the hour case is deliberately generous.
_RTH_BY_INTERVAL = {
    "1m":  ((9, 30), (16, 0)),
    "5m":  ((9, 30), (16, 0)),
    "15m": ((9, 30), (16, 0)),
    "1h":  ((9, 0),  (16, 30)),
}


def _within_rth(ts_ms: int, interval: str) -> bool:
    """Does this bar START inside the regular session, in ET?

    Daily and coarser are always accepted — a 1d bar is stamped at midnight
    and would fail every intraday test, which would silently delete the daily
    series. That mistake is one line away and would be invisible until
    something asked for a daily level.
    """
    win = _RTH_BY_INTERVAL.get(interval)
    if win is None:                      # 1d, 1w, anything coarser
        return True
    try:
        et = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(ET)
    except (OverflowError, OSError, ValueError):
        return True                      # unparseable: let the poison guard rule
    if et.weekday() >= 5:                # weekend bars are never RTH
        return False
    (sh, sm), (eh, em) = win
    minutes = et.hour * 60 + et.minute
    # LVL.20 (otv4 r494): the table is written against a 16:00 bell; a half day's ends earlier
    try:
        from utils import market_calendar as _mc
        shift = _mc.close_shift_minutes(et.date())
    except Exception:                    # noqa: BLE001 - a calendar fault keeps the 16:00 window, never drops the write
        shift = 0
    return (sh * 60 + sm) <= minutes < (eh * 60 + em) - shift


# ── v4.20 FEED.10 — the 1m referee's spans, grace and helpers ───────────────────
_REFEREE_SPAN_MIN = {"5m": 5, "15m": 15, "1h": 60}
REFEREE_CLOSE_GRACE_S = 60.0    # r277: a bar is refereed only once its span + this has passed - the final live
                                # update and the bar's last 1m both land well inside it (was 5.0 in r276)


def _referee_minutes(store_symbol: str, ts_ms: int, span: int) -> List[int]:
    """The 1m starts a COMPLETE bar must hold. *_EXT: every minute of the span. A
    plain (RTH) route: only the minutes inside 09:30 to the day's bell (half days
    included), so the 09:00 hour bar needs its 30. [] = not refereeable (no
    trading day / no RTH minute)."""
    mins = [int(ts_ms) + k * 60_000 for k in range(span)]
    if _is_ext_route(store_symbol):
        return mins
    from utils import market_calendar as _mc
    d = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(ET).date()
    if not _mc.is_trading_day(d):
        return []
    bell = _mc.close_time(d)
    lo, hi = 9 * 60 + 30, bell.hour * 60 + bell.minute
    out = []
    for m in mins:
        et = datetime.fromtimestamp(m / 1000.0, tz=timezone.utc).astimezone(ET)
        if lo <= et.hour * 60 + et.minute < hi:
            out.append(m)
    return out


def _referee_dist(v: Tuple, agg: Tuple) -> Tuple:
    """Distance of one OHLCV version from the 1m aggregate, compared as a tuple:
    with volume, relative volume error first, then |high|+|low|; a 0-volume index,
    |high|+|low| first, then |open|+|close|. Rounded so float noise is a tie."""
    o, h, l, c = (float(x) for x in v[:4])
    vol = float(v[4] or 0.0)
    ao, ah, al, ac, av = (float(x or 0.0) for x in agg)
    hl = abs(h - ah) + abs(l - al)
    if av > 0:
        return (round(abs(vol - av) / av, 9), round(hl, 9))
    return (round(hl, 9), round(abs(o - ao) + abs(c - ac), 9))


VIX_SYMBOL        = os.environ.get("OT_DXFEED_VIX", "VIX")
VIX_INTERVALS     = ("1m", "1d")


def _park_pair_symbol() -> str:
    """v5.7 (PARK.5) - the pair symbol whose 1m RTH bars this box also subscribes, or "" for none: an index box
    (config.PARK_INDEXES) or a box whose own symbol (or dx symbol) is the pair subscribes nothing extra. Constants
    only - no env key (the operator, 2026-10-31: "Do NOT add anything else to my config following a study or test")."""
    try:
        from config import PARK_INDEXES, PARK_PAIR_SYMBOL
    except Exception:                                           # noqa: BLE001
        return ""
    pair = str(PARK_PAIR_SYMBOL or "").strip().upper()
    me = str(INSTRUMENT or "").strip().upper()
    if not pair or not me or me in tuple(s.upper() for s in PARK_INDEXES):
        return ""
    if me == pair or _dxfeed_symbol().strip().upper() == pair:
        return ""
    return pair

# Backfill depth per interval: calendar days back from now that comfortably
# cover TIMEFRAMES count (RTH ~6.5h/day, ~78 5m bars, ~26 15m bars, ~7 1h bars).
# ── FEED.2 — the overnight (extended-hours) 1h stream ────────────────────────
# Stored under its OWN symbol so nothing that reads plain "1h" changes.
EXT_INTERVAL     = os.environ.get("OT_EXT_INTERVAL", "1h").strip()
EXT_STORE_SYMBOL = f"{INSTRUMENT}_EXT"
EXT_1H_ENABLED   = os.environ.get("OT_EXT_1H", "1").strip() not in ("0", "false", "")

BACKFILL_DAYS = {
    "1m":  1,      # today's session (plus yesterday if pre-open)
    "5m":  4,      # 100 bars ≈ 1.3 sessions -> 4 cal days covers weekends
    "15m": 6,      # 50 bars ≈ 2 sessions
    "1h":  45,     # r135: ~31 sessions ≈ 220 bars; > T7's 30 days, < 60-day retention
    "1d":  30,     # 10 bars ≈ 2 weeks + margin
}


def _dxfeed_symbol() -> str:
    return os.environ.get("OT_DXFEED_SYMBOL", "").strip() or INSTRUMENT


def _explain_exc(e, _depth=0):
    """Flatten an exception (incl. ExceptionGroup / __cause__) to a readable line.
    v3.8 — asyncio TaskGroup wraps the real failure in an ExceptionGroup whose
    str() is just 'unhandled errors in a TaskGroup (1 sub-exception)', which hid
    XOM's actual stream-reject cause for two days."""
    if _depth > 5:
        return repr(e)
    parts = ["%s: %s" % (type(e).__name__, e)]
    subs = getattr(e, "exceptions", None)
    if subs:
        parts.append("[" + " | ".join(_explain_exc(x, _depth + 1) for x in subs) + "]")
    cause = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
    if cause is not None and cause is not e:
        parts.append("<- caused by " + _explain_exc(cause, _depth + 1))
    return " ".join(parts)


def _base_symbol(event_symbol: str) -> str:
    """'QQQ{=5m}' -> 'QQQ'."""
    return (event_symbol or "").split("{")[0]


# OTV5 r16 (PRIME.1) — how deep a symbol the store has NEVER held is primed, per interval, from TastyTrade.
# Inside RETENTION_DAYS (warehouse/retention_purge.py) for every purged interval; TastyTrade caps 1m at its newest
# 8,000 bars (~21 RTH sessions), so the 1m ask returns what it can.
PRIME_DAYS = {
    "1m":  60,
    "5m":  30,
    "15m": 30,
    "1h":  60,
    "1d":  400,
}


def _backfill_start(interval: str, now_et: Optional[datetime] = None,
                    newest_held_ms: Optional[int] = None, held: bool = True) -> datetime:
    """Where a subscription's history starts. held=False: the store has NO bar for this (store symbol, interval) -
    a fresh box or a symbol just switched to - so prime PRIME_DAYS deep. held=True: the old start (BACKFILL_DAYS, or
    today's open for 1m), reaching back to the newest held bar when that is older, never deeper than PRIME_DAYS."""
    now_et = now_et or datetime.now(ET)
    deep = now_et - timedelta(days=PRIME_DAYS.get(interval, BACKFILL_DAYS.get(interval, 4)))
    if not held:
        return deep
    days = BACKFILL_DAYS.get(interval, 4)
    if interval == "1m":
        # Today's session open; if pre-open, previous calendar day's open so the
        # most recent session is available (readers scope to one session).
        d = now_et.date()
        if now_et.time() < dtime(*SESSION_OPEN_HM):
            d = d - timedelta(days=1)
        start = datetime.combine(d, dtime(*SESSION_OPEN_HM), tzinfo=ET)
    else:
        start = now_et - timedelta(days=days)
    if newest_held_ms is not None:
        start = min(start, datetime.fromtimestamp(newest_held_ms / 1000.0, tz=ET))
    return max(deep, start)


# ─── SQLite store (WAL, one writer — this process) ────────────────────────────

class FeedStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # check_same_thread=False + an explicit lock (v3.3).
        # The store is constructed on the MAIN thread but every write
        # (_flush -> upsert_candles/heartbeat/commit) is driven from the asyncio
        # event-loop thread created by get_loop(). Python's sqlite3 rejects that
        # by default:
        #   ProgrammingError: SQLite objects created in a thread can only be
        #   used in that same thread.
        # which killed candle-feed on its first flush, every start (GOOGL,
        # 2026-07-13). We remain a SINGLE writer — the lock serializes access so
        # allowing cross-thread use is safe.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        # 🔴 r52 — THE WAL HAD NO CEILING AND GREW TO 1.58 GB. `journal_size_limit`
        # defaults to -1 (unbounded), and SQLite REUSES the WAL in place rather
        # than shrinking it — so the file sits at its own high-water mark
        # forever. MEASURED 2026-09-18: `feed_store.db-wal` at 1,581 MB beside a
        # 1.63 GB database on a box with 3.4 GB free. The repo had already paid
        # for this once — `warehouse/retention_purge.py`'s own notes record
        # "1.6 GB feed_store.db-wal beside a 2.3 GB database" on the fleet.
        # ⚠️ A CHECKPOINT DOES NOT FIX IT AND THAT IS THE TRAP. Truncating by
        # hand reclaimed 1.5 GB and the limit reverted to -1 on the next open,
        # because the pragma is PER CONNECTION. The only durable fix is here, on
        # the connection every writer uses.
        # ⚠️ IT COSTS NOTHING IN SAFETY: the limit caps the file AFTER a
        # checkpoint, it does not force checkpoints or weaken durability.
        # `synchronous=NORMAL` above is unchanged.
        self.conn.execute("PRAGMA journal_size_limit=134217728;")   # 128 MB
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                symbol      TEXT NOT NULL,
                interval    TEXT NOT NULL,
                ts_epoch_ms INTEGER NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                PRIMARY KEY (symbol, interval, ts_epoch_ms)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_meta (
                symbol   TEXT NOT NULL,
                interval TEXT NOT NULL,
                last_write_epoch REAL NOT NULL,
                PRIMARY KEY (symbol, interval)
            );""")
        # ── v3.4: chain-marks transport (Option 1b) ──────────────────────────
        # chain_subs: single row WRITTEN BY THE BOT (options_chain v3.2) naming
        # the streamer symbols + expiry it wants live marks for. chain_marks:
        # latest-value Greeks/Quote per option symbol, WRITTEN BY THE FEED.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chain_subs (
                id            INTEGER PRIMARY KEY CHECK (id = 1),
                expiry        TEXT NOT NULL,
                symbols       TEXT NOT NULL,          -- JSON list
                updated_epoch REAL NOT NULL
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chain_marks (
                streamer_symbol TEXT PRIMARY KEY,
                bid REAL, ask REAL,
                delta REAL, gamma REAL, theta REAL, vega REAL, iv REAL,
                updated_epoch REAL NOT NULL
            );""")

        # ── 🔴 THE MANIFOLD (2026-08-22) — FULL-FIDELITY SERIES HOMES ────────
        # Operator's governing rule: **STOP DISCARDING INFORMATION.** See
        # docs/FEED_MANIFOLD.md. `chain_marks` above is PRIMARY KEY
        # (streamer_symbol) — last-write-wins — so ~250 chain symbols ticking
        # all session each overwrote ONE row. The entire intraday evolution of
        # the greek surface was captured and then destroyed.
        #
        # ⚠️ chain_marks IS UNCHANGED AND STAYS. It is the tick loop's fast
        # current-value read; every existing consumer keeps working untouched.
        # These tables are ADDITIVE. That is FEED.2's lesson applied on purpose
        # instead of after the fact.
        #
        # ⚠️ EVERY FIELD THE EVENT CARRIES IS STORED. Greeks has 13 and we kept
        # 7; Quote has 12 and we kept 2 — losing bid_size/ask_size, which is
        # depth at the touch and the signal FRC.1 needed and never had.
        #
        # 🔴 CHARM AND VANNA LIVE HERE. Both are second-order derivatives of
        # delta OVER A SERIES — charm = dDelta/dt, vanna = dDelta/dVol — so
        # NEITHER was computable from a single overwritten row. For 0DTE charm
        # is the mechanism behind pin; a 0DTE book that cannot compute it is
        # asserting pin risk rather than measuring it. Storing `delta`,
        # `volatility` and `time` per strike per tick makes both a finite
        # difference over this table.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS greeks_series (
                streamer_symbol TEXT NOT NULL,
                ts_epoch        REAL NOT NULL,
                event_time      REAL, event_flags INTEGER, idx REAL,
                ev_time         REAL, sequence INTEGER,
                price REAL, volatility REAL,
                delta REAL, gamma REAL, theta REAL, rho REAL, vega REAL,
                PRIMARY KEY (streamer_symbol, ts_epoch)
            );""")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_greeks_series_ts "
            "ON greeks_series(ts_epoch)")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS quote_series (
                streamer_symbol TEXT NOT NULL,
                ts_epoch        REAL NOT NULL,
                event_time      REAL, sequence INTEGER, time_nano_part INTEGER,
                bid_time REAL, bid_exchange_code TEXT,
                ask_time REAL, ask_exchange_code TEXT,
                bid_price REAL, ask_price REAL,
                bid_size REAL, ask_size REAL,
                PRIMARY KEY (streamer_symbol, ts_epoch)
            );""")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_quote_series_ts "
            "ON quote_series(ts_epoch)")

        # ── 🔴 MANIFOLD PART 2 (2026-08-22) — THE FIVE UNSUBSCRIBED EVENTS ───
        # The SDK offers TEN event types. Until now this feed subscribed THREE.
        # These five were never asked for, so no consumer could ever starve on
        # them loudly — they simply did not exist. Operator's rule: capture
        # everything the wire offers, give it a home, let consumers subscribe.
        #
        # ⚠️ TWO OF THESE CARRY THINGS THIS REPO HAS BEEN MISSING BY NAME:
        #   · TimeAndSale.aggressor_side — BUY vs SELL initiated, per print.
        #     Real order flow. Nothing here has ever seen who lifted the offer
        #     versus hit the bid, and FRC.1's friction work was blind to it.
        #   · Underlying.put_call_ratio / front_volatility / back_volatility —
        #     term structure and flow skew from the VENDOR, no derivation.
        #   · Summary.prev_day_close_price — `runaway_continuation` takes
        #     prev_close as a BARE SCALAR whose 1d dependency is invisible at
        #     the call site, and 1d was absent from the warehouse on
        #     2026-08-21. This is a second, independent source for it.
        #
        # ⚠️ ALL APPEND-ONLY, PK (symbol, ts). Nothing overwrites.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS prints (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, idx REAL, ev_time REAL, sequence INTEGER,
                exchange_code TEXT, price REAL, size REAL,
                bid_price REAL, ask_price REAL,
                aggressor_side TEXT, spread_leg INTEGER,
                extended_trading_hours INTEGER, valid_tick INTEGER,
                type TEXT, buyer TEXT, seller TEXT,
                exchange_sale_conditions TEXT,
                PRIMARY KEY (symbol, ts_epoch, sequence)
            );""")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_prints_ts ON prints(ts_epoch)")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS last_trade (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, ev_time REAL, sequence INTEGER,
                exchange_code TEXT, day_id INTEGER, tick_direction TEXT,
                extended_trading_hours INTEGER,
                price REAL, change REAL, size REAL,
                day_volume REAL, day_turnover REAL,
                PRIMARY KEY (symbol, ts_epoch)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS session_summary (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, day_id INTEGER, prev_day_id INTEGER,
                open_interest REAL,
                day_open_price REAL, day_high_price REAL,
                day_low_price REAL, day_close_price REAL,
                prev_day_close_price REAL, prev_day_volume REAL,
                PRIMARY KEY (symbol, ts_epoch)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS underlying_series (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, idx REAL, ev_time REAL, sequence INTEGER,
                volatility REAL, front_volatility REAL, back_volatility REAL,
                call_volume REAL, put_volume REAL, option_volume REAL,
                put_call_ratio REAL,
                PRIMARY KEY (symbol, ts_epoch)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS theo_series (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, idx REAL, ev_time REAL, sequence INTEGER,
                price REAL, underlying_price REAL,
                delta REAL, gamma REAL, dividend REAL, interest REAL,
                PRIMARY KEY (symbol, ts_epoch)
            );""")
        self.conn.commit()

    def newest_held_ms(self, symbol: str, interval: str) -> Optional[int]:
        """OTV5 r16 — the newest stored bar's ts for (symbol, interval), or None when the store holds none."""
        with self._lock:
            row = self.conn.execute("SELECT MAX(ts_epoch_ms) FROM candles WHERE symbol=? AND interval=?",
                                    (symbol, interval)).fetchone()
        return int(row[0]) if row and row[0] is not None else None

    def upsert_candles(self, rows: List[Tuple]):
        """rows: (symbol, interval, ts_ms, o, h, l, c, v). Last write wins."""
        if not rows:
            return
        with self._lock:
            self._upsert_candles_locked(rows)

    # v4.14 FEED.9b — when a stored bar yields. Three cases, in this order:
    #   · a stored NULL price always yields;
    #   · 1d is last-write-wins, as before v4.13: the vendor's daily is its
    #     official bar and a replay CORRECTS it (CVX 2026-10-12 stored an
    #     off-tape low of 211.02 against a 1m low of 213.75; v4.13 refused the
    #     vendor's correction twice, and that bar becomes tomorrow's prior-day
    #     low);
    #   · a bar WITH volume yields unless the new version lost more than 5% of
    #     it. The 10-08 slices lost 14-90%; a correction that removes a bad
    #     print loses almost none and is now taken, narrower range or not;
    #   · a 0-volume bar (index: SPX, VIX; SQLite stores NaN as NULL, hence
    #     the coalesce) keeps v4.13's rule: range no narrower, and the same
    #     open or a wider range.
    _UPSERT_CANDLE_SQL = (
        "INSERT INTO candles "
        "(symbol, interval, ts_epoch_ms, open, high, low, close, volume) "
        "VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT(symbol, interval, ts_epoch_ms) DO UPDATE SET "
        "open=excluded.open, high=excluded.high, low=excluded.low, "
        "close=excluded.close, volume=excluded.volume "
        "WHERE candles.open IS NULL OR candles.high IS NULL "
        "OR candles.low IS NULL OR candles.close IS NULL "
        "OR excluded.interval = '1d' "
        "OR (coalesce(candles.volume,0) > 0 AND "
        "coalesce(excluded.volume,0) >= 0.95 * candles.volume) "
        "OR (coalesce(candles.volume,0) = 0 "
        "AND excluded.high >= candles.high AND excluded.low <= candles.low "
        "AND (excluded.open = candles.open "
        "OR excluded.high > candles.high OR excluded.low < candles.low))")

    # v4.20 FEED.10 (fork-first) — THE 1m REFEREE. FEED.9/9b decide from the two
    # versions alone, so they can catch a SHRUNKEN replay (10-08: the vendor's
    # slice) but never an INFLATED one: on 2026-10-12 this box's own 16:11/16:17
    # replays stored every complete QQQ 1h bar at EXACTLY 2.0x the volume of its
    # 60 minutes (mainline's live-pushed 15:00 bar: 1,629,246 = the 1m sum; ours:
    # 3,258,492), and a version with MORE volume always passes the 9b rule. For a
    # CLOSED 5m/15m/1h bar whose every minute this store holds, the referee keeps
    # whichever version (stored or replayed) is closer to the 1m aggregate
    # (first open, max high, min low, last close, volume sum): volume first, then
    # high/low; a 0-volume index compares high/low, then open/close. A tie keeps
    # the stored row. Anything else - a forming bar, a minute missing, a stored
    # NULL, any error - takes the FEED.9b rule unchanged, with NO extra read on
    # a forming bar (every live update of the forming bar conflicts with its own
    # stored row). ⚠️ THE REFEREE'S SOURCE IS THE SAME VENDOR: the 1m rows are
    # themselves guarded only by FEED.9/9b and are never refereed, and
    # completeness is by minute COUNT - a 1m slice (thin minutes) would pass as
    # complete and mislead it. Named as an open limitation (BACKLOG FEED.10).
    def _upsert_candles_locked(self, rows: List[Tuple]):
        # Refusals are reported per (symbol, interval) with the stored and the
        # refused values: *_EXT has two sources (the RTH guard's re-key and the
        # EXT subscription), and a refusal has to be judgeable after the fact.
        refused: Dict[Tuple[str, str], List[Tuple]] = {}
        overrode: Dict[Tuple[str, str], List[Tuple]] = {}
        now_ms = _time.time() * 1000.0
        for r in rows:
            span = _REFEREE_SPAN_MIN.get(r[1])
            if span is not None and r[2] + span * 60_000 + REFEREE_CLOSE_GRACE_S * 1000.0 <= now_ms:
                done = self._referee_one_locked(r, span, refused, overrode)
                if done:
                    continue
            if self.conn.execute(self._UPSERT_CANDLE_SQL, r).rowcount == 0:
                refused.setdefault((r[0], r[1]), []).append(r)
        for (sym, iv), rr in refused.items():
            first = rr[0]
            kept = self.conn.execute(
                "SELECT open, high, low, close, volume FROM candles WHERE "
                "symbol=? AND interval=? AND ts_epoch_ms=?",
                (sym, iv, first[2])).fetchone()
            logger.info("FEED.9: kept %d stored %s %s bar(s) a smaller "
                        "version would have overwritten; first ts=%d kept "
                        "OHLCV=%s refused OHLCV=%s", len(rr), sym, iv,
                        first[2], kept, tuple(first[3:8]))
        for (sym, iv), oo in overrode.items():
            r, stored, agg, take = oo[0]
            logger.info("FEED.10: the 1m referee overrode the FEED.9b rule on %d %s %s bar(s); "
                        "first ts=%d %s stored OHLCV=%s replay OHLCV=%s 1m aggregate OHLCV=%s",
                        len(oo), sym, iv, r[2], "TOOK the replay" if take else "KEPT the stored bar",
                        stored, tuple(r[3:8]), agg)
        now = _time.time()
        touched = {(r[0], r[1]) for r in rows}
        self.conn.executemany(
            "INSERT OR REPLACE INTO feed_meta (symbol, interval, last_write_epoch) "
            "VALUES (?,?,?)", [(s, i, now) for (s, i) in touched])

    def _referee_one_locked(self, r: Tuple, span: int, refused, overrode) -> bool:
        """FEED.10 for ONE closed 5m/15m/1h row. True when it handled the row; False
        sends the row to the FEED.9b rule unchanged. Never raises."""
        try:
            if self.conn.execute(
                    "INSERT OR IGNORE INTO candles "
                    "(symbol, interval, ts_epoch_ms, open, high, low, close, volume) "
                    "VALUES (?,?,?,?,?,?,?,?)", r).rowcount == 1:
                return True                          # a new bar: nothing to referee
            stored = self.conn.execute(
                "SELECT open, high, low, close, volume FROM candles WHERE "
                "symbol=? AND interval=? AND ts_epoch_ms=?", (r[0], r[1], r[2])).fetchone()
            if stored is None or any(x is None for x in stored[:4]):
                return False                         # a stored NULL yields: FEED.9b's case
            if tuple(r[3:8]) == tuple(stored):
                return True                          # r277: an identical replay - nothing to decide or log
            want = _referee_minutes(r[0], r[2], span)
            if not want:
                return False
            mins = self.conn.execute(
                "SELECT ts_epoch_ms, open, high, low, close, volume FROM candles WHERE "
                "symbol=? AND interval='1m' AND ts_epoch_ms>=? AND ts_epoch_ms<? "
                "ORDER BY ts_epoch_ms", (r[0], want[0], want[-1] + 60_000)).fetchall()
            got = [m for m in mins if m[0] in set(want)]
            if len(got) != len(want) or any(x is None for m in got for x in m[1:5]):
                return False                         # incomplete: the 9b rule decides
            agg = (got[0][1], max(m[2] for m in got), min(m[3] for m in got), got[-1][4],
                   sum((m[5] or 0.0) for m in got))
            take = _referee_dist(tuple(r[3:8]), agg) < _referee_dist(stored, agg)
            self.conn.execute("SAVEPOINT feed10")
            took = self.conn.execute(self._UPSERT_CANDLE_SQL, r).rowcount > 0
            if took and not take:
                self.conn.execute("ROLLBACK TO feed10")
            elif take and not took:
                self.conn.execute(
                    "UPDATE candles SET open=?, high=?, low=?, close=?, volume=? WHERE "
                    "symbol=? AND interval=? AND ts_epoch_ms=?", tuple(r[3:8]) + tuple(r[0:3]))
            self.conn.execute("RELEASE feed10")
            if took != take:
                overrode.setdefault((r[0], r[1]), []).append((r, tuple(stored), agg, take))
            elif not take:
                refused.setdefault((r[0], r[1]), []).append(r)
            return True
        except Exception as exc:                     # noqa: BLE001 — fall back, never raise
            try:                                     # undo anything half-done, then close the savepoint
                self.conn.execute("ROLLBACK TO feed10")
                self.conn.execute("RELEASE feed10")
            except Exception:                        # noqa: BLE001 — no savepoint was open
                pass
            if not getattr(self, "_referee_err_logged", False):
                self._referee_err_logged = True
                logger.warning("FEED.10: the 1m referee failed (%s) - falling back to the "
                               "FEED.9b rule; said once", exc)
            return False

    def purge_poison(self) -> int:
        """Delete any poison rows already in the store (v3.2). Runs at feed
        startup so a box whose DB was poisoned before this guard existed
        self-heals on restart — no manual sqlite surgery across the fleet."""
        with self._lock:
            cur = self.conn.execute(
                "DELETE FROM candles WHERE open <= 0 OR high <= 0 OR low <= 0 "
                "OR close <= 0 OR ts_epoch_ms < ? OR ts_epoch_ms > ?",
                (TS_MS_MIN, _ts_ms_max()))
            self.conn.commit()
            n = cur.rowcount or 0
        if n:
            logger.warning("purged %d poison candle row(s) from the store", n)
        return n

    def heartbeat(self):
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO feed_meta (symbol, interval, last_write_epoch) "
                "VALUES ('__feed__','heartbeat',?)", (_time.time(),))

    def commit(self):
        with self._lock:
            self.conn.commit()

    # ── v3.4: chain-marks transport ───────────────────────────────────────────
    def read_chain_subs(self):
        """(expiry, [streamer_symbols]) requested by the bot, or ("", []).

        ⚠️ TERM.1 (2026-08-18): the returned symbol list is the FRONT expiry
        UNIONED with any auxiliary tenors. `chain_subs` is `CHECK (id = 1)` — a
        single row by design — so extra expiries ride in a SEPARATE table and
        the front-expiry contract is untouched. The returned `expiry` string
        still names the FRONT expiry only: every existing caller reads it that
        way and none of them changes.

        ⚠️ FAILS OPEN, DELIBERATELY. A missing, empty or malformed aux table
        returns the front expiry exactly as before. **This function decides what
        a live trading box subscribes to** — the auxiliary tenors are archival
        enrichment and must never be able to cost the bot its own chain.
        """
        with self._lock:
            row = self.conn.execute(
                "SELECT expiry, symbols FROM chain_subs WHERE id=1").fetchone()
        if not row:
            return "", []
        try:
            expiry = row[0] or ""
            syms = json.loads(row[1] or "[]")
        except (ValueError, TypeError):
            return "", []
        try:
            aux = self._read_chain_subs_aux()
            if aux:
                seen = set(syms)
                for s in aux:
                    if s not in seen:
                        seen.add(s)
                        syms.append(s)
        except Exception:                                      # noqa: BLE001
            pass          # archival enrichment never costs the bot its chain
        return expiry, syms

    def _read_chain_subs_aux(self):
        """Extra-tenor streamer symbols, or [] if the table is absent/stale.

        ⚠️ STALENESS BOUND. An aux row older than the front expiry's own update
        is a leftover from a previous session — subscribing to last week's
        strikes wastes socket budget against a measured ~40-session cap and
        pollutes `chain_marks` with contracts nothing reads.
        """
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='chain_subs_aux'")
        if not cur.fetchone():
            return []
        cutoff = _time.time() - AUX_MAX_AGE_S
        rows = self.conn.execute(
            "SELECT symbols FROM chain_subs_aux WHERE updated_epoch >= ?",
            (cutoff,)).fetchall()
        out = []
        for r in rows:
            try:
                out.extend(json.loads(r[0] or "[]"))
            except (ValueError, TypeError):
                continue
        return out

    def upsert_chain_quotes(self, rows):
        """rows: (streamer_symbol, bid, ask, epoch) — preserves greeks columns."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT INTO chain_marks (streamer_symbol, bid, ask, updated_epoch) "
                "VALUES (?,?,?,?) ON CONFLICT(streamer_symbol) DO UPDATE SET "
                "bid=excluded.bid, ask=excluded.ask, "
                "updated_epoch=excluded.updated_epoch", rows)

    def upsert_chain_greeks(self, rows):
        """rows: (streamer_symbol, delta, gamma, theta, vega, iv, epoch) —
        preserves quote columns."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT INTO chain_marks (streamer_symbol, delta, gamma, theta, "
                "vega, iv, updated_epoch) VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(streamer_symbol) DO UPDATE SET "
                "delta=excluded.delta, gamma=excluded.gamma, theta=excluded.theta, "
                "vega=excluded.vega, iv=excluded.iv, "
                "updated_epoch=excluded.updated_epoch", rows)

    # ── MANIFOLD WRITERS (2026-08-22) — append-only, every field ────────────
    # ⚠️ INSERT OR IGNORE, not UPSERT. The PK is (symbol, ts) so a duplicate
    # tick is a no-op rather than a silent overwrite — the whole point of these
    # tables is that nothing is ever destroyed.
    def append_greeks_series(self, rows):
        """rows: 13-tuples, full Greeks fidelity. See docs/FEED_MANIFOLD.md."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT OR IGNORE INTO greeks_series (streamer_symbol, ts_epoch,"
                " event_time, event_flags, idx, ev_time, sequence, price,"
                " volatility, delta, gamma, theta, rho, vega)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_quote_series(self, rows):
        """rows: 13-tuples, full Quote fidelity INCLUDING bid_size/ask_size."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT OR IGNORE INTO quote_series (streamer_symbol, ts_epoch,"
                " event_time, sequence, time_nano_part, bid_time,"
                " bid_exchange_code, ask_time, ask_exchange_code, bid_price,"
                " ask_price, bid_size, ask_size)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    # ── MANIFOLD PART 2 WRITERS — append-only, every field ──────────────
    def append_prints(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO prints (symbol, ts_epoch, event_time, idx,"
            " ev_time, sequence, exchange_code, price, size, bid_price,"
            " ask_price, aggressor_side, spread_leg, extended_trading_hours,"
            " valid_tick, type, buyer, seller, exchange_sale_conditions)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_last_trade(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO last_trade (symbol, ts_epoch, event_time,"
            " ev_time, sequence, exchange_code, day_id, tick_direction,"
            " extended_trading_hours, price, change, size, day_volume,"
            " day_turnover) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_session_summary(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO session_summary (symbol, ts_epoch,"
            " event_time, day_id, prev_day_id, open_interest, day_open_price,"
            " day_high_price, day_low_price, day_close_price,"
            " prev_day_close_price, prev_day_volume)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_underlying(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO underlying_series (symbol, ts_epoch,"
            " event_time, idx, ev_time, sequence, volatility,"
            " front_volatility, back_volatility, call_volume, put_volume,"
            " option_volume, put_call_ratio)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_theo(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO theo_series (symbol, ts_epoch, event_time,"
            " idx, ev_time, sequence, price, underlying_price, delta, gamma,"
            " dividend, interest) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def _append_many(self, sql, rows) -> int:
        """Shared append. Never raises — a lost observation must not stall
        the tape (same rule as the series writes)."""
        if not rows:
            return 0
        try:
            with self._lock:
                self.conn.executemany(sql, rows)
            return len(rows)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("append failed (%d rows): %s — raw candles "
                           "unaffected", len(rows), exc)
            return 0

    def clear_chain_marks(self):
        with self._lock:
            self.conn.execute("DELETE FROM chain_marks")
            self.conn.commit()

    def prune(self, symbol: str, interval: str, keep: int):
        with self._lock:
            self._prune_locked(symbol, interval, keep)

    def _prune_locked(self, symbol: str, interval: str, keep: int):
        self.conn.execute("""
            DELETE FROM candles WHERE symbol=? AND interval=? AND ts_epoch_ms NOT IN
            (SELECT ts_epoch_ms FROM candles WHERE symbol=? AND interval=?
             ORDER BY ts_epoch_ms DESC LIMIT ?)""",
            (symbol, interval, symbol, interval, keep))

    def bar_count(self, symbol: str, interval: str) -> int:
        with self._lock:
            cur = self.conn.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol=? AND interval=?",
                (symbol, interval))
            return int(cur.fetchone()[0])

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass


# ─── The producer ──────────────────────────────────────────────────────────────

class CandleFeed:
    """Persistent single subscription -> in-memory last-write-wins buffer ->
    periodic flush to the shared store."""

    def __init__(self, store: FeedStore):
        self.store = store
        self.dx_symbol = _dxfeed_symbol()
        # (dxfeed_symbol, interval) -> store symbol name
        self.symbol_map: Dict[Tuple[str, str], str] = {}
        # (dx_sym, interval, start, extended_trading_hours)
        self.subs: List[Tuple[str, str, datetime, bool]] = []
        for tf in TIMEFRAMES.keys():
            self.subs.append((self.dx_symbol, tf, _backfill_start(tf), False))
            # v3.16 — the key now carries the EXTENDED-HOURS FLAG, because
            # (dx_symbol, interval) is NOT unique: FEED.2 subscribes the same
            # symbol+interval twice and the second registration used to
            # overwrite the first. Three-tuple, one entry per subscription.
            self.symbol_map[(self.dx_symbol, tf, False)] = INSTRUMENT
        # ── 🔴 MANIFOLD (2026-08-22) — VIX AT FULL TENOR PARITY ──────────────
        # Was `VIX_INTERVALS = ("1m","1d")` — 2 of 5. VIX feeds macro,
        # vol_state and SessionGuard's crisis lockout, and none of them could
        # ever see a 5m/15m/1h VIX because it was never requested.
        # ⚠️ CAPTURE ON ALL 15 BOXES, PUBLISH FROM SPX ONLY. VIX is the one
        # fleet-wide duplicate (traced: each box subscribes its own instrument
        # plus VIX, nothing else). It is needed locally everywhere and is
        # identical everywhere, so the S3 push is SPX's job — operator's call,
        # 2026-08-22. See docs/FEED_MANIFOLD.md.
        for tf in TIMEFRAMES.keys():
            self.subs.append((VIX_SYMBOL, tf, _backfill_start(tf), False))
            self.symbol_map[(VIX_SYMBOL, tf, False)] = "VIX"
        # ── v5.7 (PARK.5) — QQQ's 1m RTH BARS ON EVERY EQUITY BOX, ON THIS SAME SESSION ─────────────────────
        # PARK's commitment gate (strategy/park_plan v5.4) reads QQQ's first hour and its prior sessions at 11:01 on
        # every NON-index box. One more candle subscription on the socket this box already holds - no new DXLink
        # session (the per-node session limit, FEED.13) and no dependency on another box or on S3's push lag. Stored
        # under the plain store symbol QQQ: no consumer of this box's own INSTRUMENT moves, s3_push uploads only the
        # box's own family (r139) so these rows never reach the warehouse, and a store that has never held QQQ primes
        # PRIME_DAYS deep at the first subscribe (r16; TastyTrade gives ~21 RTH sessions of 1m). The index boxes
        # (config.PARK_INDEXES) and a box whose own symbol IS the pair subscribe nothing extra.
        _pair = _park_pair_symbol()
        if _pair:
            self.subs.append((_pair, "1m", _backfill_start("1m"), False))
            self.symbol_map[(_pair, "1m", False)] = _pair

        # ── FEED.2 (2026-08-15) — THE OVERNIGHT STREAM ───────────────────────
        # ⚠️ THE TAPE WAS NEVER UNAVAILABLE. WE WERE ASKING DXFEED TO EXCLUDE IT.
        # `subscribe_candle(..., extended_trading_hours=False)` is the SDK
        # DEFAULT, and when it is False the SDK appends **`tho=true`**
        # (trading-hours-only) to the symbol: `QQQ{=1h,tho=true}`. Every
        # subscription this feed has ever made carried it.
        #
        # That single default is what produced `ext=0` on 28 of 29 boxes, an
        # RTH-only 1h store (252 bars = 36 sessions x 7), and LIQ.6's Asia and
        # London sections having nothing to build from. It is NOT the session
        # guard, NOT the warm lead, NOT S3, NOT an entitlement tier.
        #
        # ⚠️ A SEPARATE STREAM, NOT A FLAG ON THE EXISTING 1h. `1h` is read by
        # structure_analyzer's swings and S/R, by the pitchfork and its observer,
        # and by entry_snapshot. Flipping it in place would silently rebuild all
        # of them on 24h bars — the pitchfork is a v4.0 milestone and its forks
        # would change shape overnight with nothing announcing it. This lands
        # under its OWN store symbol so **no existing consumer moves at all**;
        # only the named-level frame reads it.
        # ── 🔴 MANIFOLD (2026-08-22) — EXTENDED ON EVERY TENOR, NOT JUST 1h ──
        # The block above is the FEED.2 finding and it is still correct; what
        # was wrong is that it was applied to ONE tenor. 1h got an extended
        # twin because LIQ.6 starved and noticed. 1m/5m/15m/1d never had one —
        # so four fifths of the overnight tape had no home and was simply not
        # requested.
        # ⚠️ THIS IS THE CAPTURE-ON-DEMAND PATTERN ITSELF. Operator, 2026-08-22:
        # every fix in this repo "had to do with unlocking one feed store
        # artifact at a time until something started working, where we should
        # have started with subscribe to everything, find a place for it, and
        # then if we need it, it's there." A consumer cannot starve on data
        # that was never conditional.
        # ⚠️ STILL SEPARATE STORE SYMBOLS — the reasoning above holds for all
        # five: extended bars land under SYM_EXT/interval, so NO existing
        # consumer moves. The RTH series stay byte-identical.
        # ⚠️ FAILS OPEN PER TENOR. If an entitlement does not cover extended on
        # some tenor, that ONE subscription logs SUBSCRIBE FAILED and the rest
        # continue — the loop that opens these already guarantees it.
        if EXT_1H_ENABLED:
            for tf in TIMEFRAMES.keys():
                self.subs.append((self.dx_symbol, tf,
                                  _backfill_start(tf), True))
                self.symbol_map[(self.dx_symbol, tf, True)] = EXT_STORE_SYMBOL
        # ── v3.16 — COLLISION GUARD. REFUSE TO START ON A DUPLICATE ROUTE ───
        # The FEED.2 defect was not that someone wrote a wrong key; it was that
        # TWO subscriptions could legally resolve to the SAME store target and
        # nothing said so. Six days of stale 1h structure followed, fleet-wide,
        # with no error. A route table that can silently lose an entry must not
        # be allowed to start.
        # Two invariants, both cheap and both checked before a socket opens:
        #   1. no two SUBSCRIPTIONS share a map key (one would overwrite the
        #      other, which is exactly what happened)
        #   2. no two map keys point at the SAME (store_symbol, interval) —
        #      two live streams writing one table is a silent merge
        _seen_keys, _seen_targets = set(), {}
        for (_ds, _tf, _st, _ex) in self.subs:
            _k = (_ds, _tf, bool(_ex))
            if _k in _seen_keys:
                raise RuntimeError(
                    f"candle_feed: DUPLICATE SUBSCRIPTION KEY {_k} — two "
                    f"subscriptions resolve to one route and one would "
                    f"silently overwrite the other (the FEED.2 defect, "
                    f"2026-08-14..20). Refusing to start.")
            _seen_keys.add(_k)
            _tgt = (self.symbol_map.get(_k), _tf)
            if _tgt[0] is None:
                raise RuntimeError(
                    f"candle_feed: SUBSCRIPTION {_k} HAS NO ROUTE in "
                    f"symbol_map — its candles would be dropped. Refusing "
                    f"to start.")
            if _tgt in _seen_targets:
                raise RuntimeError(
                    f"candle_feed: TWO SUBSCRIPTIONS WRITE {_tgt} — "
                    f"{_seen_targets[_tgt]} and {_k}. One stream would "
                    f"silently merge into the other's table. Refusing to "
                    f"start.")
            _seen_targets[_tgt] = _k
        logger.info("candle_feed routes verified: %d subscription(s), "
                    "%d distinct store target(s)",
                    len(_seen_keys), len(_seen_targets))

        # buffer[(store_symbol, interval)][ts_ms] = row tuple
        self.buffer: Dict[Tuple[str, str], Dict[int, Tuple]] = {}
        self._unmapped_seen: set = set()   # v3.7: warn-once on unmapped candles
        # v3.17 — non-RTH bars SEGREGATED per (symbol, interval). Warn ONCE
        # then count: a per-bar warning during a 15-day backfill buries the log.
        self._rth_moved: Dict[Tuple[str, str], int] = {}
        self.backfill_logged: Dict[Tuple[str, str], bool] = {}
        # ── v3.4 chain-marks state (reset on every socket (re)connect) ────────
        self._chain_expiry: str = ""
        self._chain_subscribed: set = set()
        self._quotes_buf: Dict[str, tuple] = {}    # sym -> (sym,bid,ask,epoch)
        self._greeks_buf: Dict[str, tuple] = {}    # sym -> (sym,d,g,t,v,iv,epoch)
        # MANIFOLD (2026-08-22) — LISTS, not dicts. The two buffers above are
        # keyed by symbol precisely so the newest tick REPLACES the previous
        # one; that is correct for a current-value cache and fatal for history.
        # These append, so every tick survives to the flush.
        self._greeks_series_buf: List[tuple] = []
        self._quote_series_buf: List[tuple] = []
        # MANIFOLD PART 2 — one append-buffer per new event type.
        # r72 — the opening-range rescue fired AT MOST ONCE per session; v5.9 (r74, ORP.3) allows ORB_RESCUE_MAX (6),
        # ORB_RESCUE_EVERY_S (120 s) apart, because a tape that returns at 10:55 needs a pull after it returns.
        # ⚠️ A RETRY LOOP HERE WOULD BE WORSE THAN THE BUG. Fifteen boxes
        # re-subscribing 5m every tick during an outage is a self-inflicted
        # stampede on the same socket that is already struggling.
        self._orb_rescue_done_for: str = ""      # kept for older callers; v5.9 (r74) counts in _orb_rescue
        self._orb_rescue: list = []                # v5.9 (r74, ORP.3): [day, attempts, last monotonic]
        # v5.8 (PARK.5) — the gate-tape refill: {store symbol: [day, attempts, last monotonic, final_done]}
        self._commit_refill: Dict[str, list] = {}
        self._prints_buf: List[tuple] = []
        self._trade_buf: List[tuple] = []
        self._summary_buf: List[tuple] = []
        self._underlying_buf: List[tuple] = []
        self._theo_buf: List[tuple] = []


    def _start_for(self, dx_sym: str, tf: str, ext: bool, fallback: datetime) -> datetime:
        """OTV5 r16 (PRIME.1) — this subscription's history start, read from the store NOW: a (store symbol, interval)
        the store has never held is primed PRIME_DAYS deep; a held one backfills as before. A store read error keeps
        the start computed at construction (named, never silent)."""
        sym = self.symbol_map.get((dx_sym, tf, ext))
        if not sym:
            return fallback
        try:
            newest = self.store.newest_held_ms(sym, tf)
        except Exception as exc:                                    # noqa: BLE001
            logger.warning("backfill start for %s %s: store read failed (%s) - using %s",
                           sym, tf, _explain_exc(exc), fallback.isoformat())
            return fallback
        start = _backfill_start(tf, newest_held_ms=newest, held=newest is not None)
        if newest is None:
            logger.info("PRIME %s %s: the store holds none - priming %d days from TastyTrade (from %s)",
                        sym, tf, PRIME_DAYS.get(tf, 0), start.isoformat())
        return start
    def _interval_of(self, event_symbol: str) -> Optional[str]:
        """Map DXFeed's echoed candle symbol back to OUR config timeframe key.

        'AAPL{=5m}'            -> '5m'
        'AAPL{=5m,tho=true}'   -> '5m'    (attributes stripped)
        'AAPL{=m,tho=true}'    -> '1m'    (DXFeed canonicalizes 1m -> m)
        'AAPL{=h,tho=true}'    -> '1h'
        'AAPL{=d,tho=true}'    -> '1d'

        v3.7 — TWO bugs that each SILENTLY DROP EVERY CANDLE (feed stays 'active',
        authenticated, streaming, store takes ZERO writes; bots read yesterday's
        bars; no ORB range for today; fleet EXPIRED/UNKNOWN; not one error logged
        — recurred every morning 07-13/14/15):
        (1) DXFeed echoes the symbol back WITH ATTRIBUTES ('...,tho=true'); the
            old parser returned '5m,tho=true' and never matched symbol_map.
        (2) DXFeed CANONICALIZES a leading 1: we subscribe '1m'/'1h'/'1d', it
            echoes 'm'/'h'/'d'. 1m is what fetch_quote() reads (the bot's price).
        """
        if "{=" not in (event_symbol or ""):
            return None
        token = event_symbol.split("{=", 1)[1].rstrip("}")
        token = token.split(",", 1)[0].strip()      # drop ',tho=true' etc.
        return {"m": "1m", "h": "1h", "d": "1d", "s": "1s"}.get(token, token)

    @staticmethod
    def _is_ext_of(event_symbol: str) -> bool:
        """v3.16 — IS THIS ECHO FROM THE EXTENDED-HOURS SUBSCRIPTION?

        🔴 THE BUG THIS EXISTS FOR. FEED.2 subscribes the SAME dx symbol at the
        SAME interval twice — once RTH-only, once with extended_trading_hours —
        and registered both in `symbol_map` under `(dx_symbol, interval)`. The
        keys are identical, so the second assignment silently overwrote the
        first and EVERY 1h candle was routed to the EXT store symbol. Measured
        2026-08-20 across the fleet: plain `QQQ`/`SPX` 1h frozen at 2026-08-14
        while `*_EXT` 1h was current — SIX DAYS of stale higher-timeframe
        structure feeding structure_analyzer's swings and S/R, the pitchfork
        and its observer, and entry_snapshot. Nothing raised; BARS_STALE warned
        every five minutes with `refused=False` and the bots kept trading on
        08-14 bars.
        `tho=true` is the ONLY thing that distinguishes the two echoes, and
        `_interval_of` deliberately discards it. So read it here instead: the
        attribute the parser drops is exactly the attribute the router needs.
        """
        if "{=" not in (event_symbol or ""):
            return False
        attrs = event_symbol.split("{=", 1)[1].rstrip("}")
        # 🔴 v4.4 (2026-08-21) — THE POLARITY WAS BACKWARDS. This read
        #     return "tho=true" in attrs
        # but `tho` is TRADING-HOURS-ONLY: `tho=true` marks the RTH echo, and
        # its ABSENCE marks the extended one. v3.16 named the right attribute
        # and inverted its meaning.
        #
        # WHAT IT COST, measured live 2026-08-21 09:31-09:52:
        # · 1m/5m/15m/1d register ONLY (sym, tf, False). Every RTH echo looked
        #   up True, missed, and was DROPPED — the whole intraday tape, fleet
        #   wide, for a full session. The bots priced off the previous day's
        #   close because fetch_quote reads the newest 1m bar.
        # · 1h registers BOTH keys, so nothing missed — the two streams simply
        #   SWAPPED. Plain `SYM` 1h received the EXTENDED tape and `SYM_EXT`
        #   received RTH. Both looked current. That is why 1h alone appeared
        #   healthy and hid the rest.
        #
        # ⚠️ THE WRITE GUARD PARTLY MASKED IT, which is why it survived a day.
        # v3.17 re-segregates non-RTH bars off the plain route, so the misrouted
        # extended 1h bars were caught and moved — leaving plain 1h roughly
        # right BY ACCIDENT while the log said "RTH GUARD ... SEGREGATING" every
        # session and was read as the guard doing its job. A correct-looking
        # output produced by two errors cancelling is this project's failure
        # class in its purest form.
        return "tho=true" not in attrs.replace(" ", "").lower()

    def _on_candle(self, c: Candle):
        ev_sym = getattr(c, "event_symbol", "")
        base = _base_symbol(ev_sym)
        interval = self._interval_of(ev_sym) or ""
        is_ext = self._is_ext_of(ev_sym)
        key_sym = self.symbol_map.get((base, interval, is_ext))
        if key_sym is None:
            # v3.7: NEVER drop a candle silently. This branch swallowed the whole
            # feed on 07-13/14/15 (unparsed interval) with no log anywhere. Warn
            # once per distinct unmapped key so a future echo-format change is
            # visible within one line instead of a wasted session.
            if ev_sym and (base, interval, is_ext) not in self._unmapped_seen:
                self._unmapped_seen.add((base, interval, is_ext))
                logger.warning(
                    "DROPPING candles: event_symbol=%r -> (base=%r, interval=%r, "
                    "ext=%r) NOT in symbol_map %r — storing nothing for it",
                    ev_sym, base, interval, is_ext,
                    sorted(self.symbol_map.keys()))
            return
        if c.time is None or c.open is None:
            return

        # ── POISON GUARD (v3.2) ───────────────────────────────────────────────
        # DXFeed intermittently emits a junk candle: timestamp at the signed
        # 32-bit rollover (2147483648xxx ms => year 2038) with all prices 0.0.
        # Observed live on GOOGL 2026-07-13 (1m, then 15m). It is fatal
        # downstream: fetch_quote() sorts by ts DESC, so the 2038 row wins, its
        # age computes NEGATIVE (passes the freshness check), and it returns
        # close=0.0. run_analysis() treats 0.0 as falsy -> "Could not fetch
        # current price" -> the tick loop dies EVERY TICK while the unit still
        # reports ACTIVE. Silent, total. Reject it at the door: bad data must
        # never enter the store.
        try:
            ts_ms = int(c.time)
            o, h, l, cl = float(c.open), float(c.high), float(c.low), float(c.close)
        except (TypeError, ValueError):
            return

        if not (TS_MS_MIN <= ts_ms <= _ts_ms_max()):
            logger.warning(
                "REJECTED poison candle %s %s: insane ts=%d (%.1f) — outside sane window",
                key_sym, interval, ts_ms, ts_ms / 1000.0)
            return
        # v4.13 FEED.9: NaN slipped past `<= 0` and landed as NULL, which no
        # later version of the bar could ever replace.
        if not all(math.isfinite(x) and x > 0 for x in (o, h, l, cl)):
            logger.warning(
                "REJECTED poison candle %s %s ts=%d: non-positive or "
                "non-finite price "
                "(o=%.4f h=%.4f l=%.4f c=%.4f)", key_sym, interval, ts_ms, o, h, l, cl)
            return

        # ── RTH GUARD (v3.17) ────────────────────────────────────────────────
        # 🔴 THE SECOND HALF OF THE FEED.2 DEFECT. Streaming routes correctly
        # after v3.16, but a RESTART's backfill asked DXFeed for plain-symbol
        # history and got 24-HOUR BARS back — ~12 bars/hour overnight against
        # 38–39 in RTH, reaching ~15 days back (the 08-05 boundary). SPX proves
        # it is real extended-hours data and not a timezone artifact: an index
        # has no overnight session, so it shows hours 13–20 UTC only and had
        # nothing to contaminate.
        # ⚠️ WORSE THAN THE ORIGINAL HOLE. A gap announces itself; this does
        # not. The series CHANGES CHARACTER MID-STREAM — 07-31 is RTH-only,
        # 08-19 is 24-hour — with nothing marking the seam, so swings, S/R and
        # the hourly pitchfork read a discontinuity they cannot detect.
        # THE FLAG IS NOT ENOUGH. `extended_trading_hours=False` is passed on
        # the subscription and the vendor returned 24h history anyway, so the
        # guarantee has to live HERE, at the write, where it is ours to
        # enforce: a PLAIN-symbol route accepts only RTH bars. `*_EXT` routes
        # are untouched — carrying overnight is their entire purpose.
        if not _is_ext_route(key_sym) and not _within_rth(ts_ms, interval):
            # SEGREGATE, DO NOT DROP. For 5m/15m/1m there is NO extended
            # stream — EXT_INTERVAL is 1h only — so an overnight bar arriving
            # here is the ONLY copy that will ever exist, and DXFeed history is
            # use-it-or-lose-it. Discarding it to protect the RTH series would
            # trade one irreversible loss for another.
            # The plain series stays RTH-pure (which is what structure_analyzer
            # at weight 2.0, the pitchfork's 1h fractals, trend_engine's 0.20
            # context vote and entry_snapshot were all built to read), and the
            # bar is still stored — under the symbol that means "this carries
            # overnight". Nothing RTH-scoped reads it; everything can query it.
            alt = f"{key_sym}_EXT"
            self._rth_moved[(key_sym, interval)] = \
                self._rth_moved.get((key_sym, interval), 0) + 1
            if self._rth_moved[(key_sym, interval)] == 1:
                logger.warning(
                    "RTH GUARD: non-RTH bars on the plain route for %s %s "
                    "(first ts=%d) — SEGREGATING to %s so the RTH series stays "
                    "pure and no bar is lost. Counting silently from here.",
                    key_sym, interval, ts_ms, alt)
            key_sym = alt

        row = (key_sym, interval, ts_ms, o, h, l, cl,
               float(getattr(c, "volume", 0) or 0))
        self.buffer[(key_sym, interval)] = self.buffer.get((key_sym, interval), {})
        self.buffer[(key_sym, interval)][ts_ms] = row

    # ── v3.4: chain-marks handlers ─────────────────────────────────────────
    def _on_quote(self, q: Quote):
        sym = getattr(q, "event_symbol", "") or ""
        if not sym:
            return
        try:
            bid = float(q.bid_price or 0)
            ask = float(q.ask_price or 0)
        except (TypeError, ValueError):
            return
        now = _time.time()
        self._quotes_buf[sym] = (sym, bid, ask, now)
        # MANIFOLD — full fidelity alongside the fast path. Nothing dropped.
        def _f(v):
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None
        self._quote_series_buf.append((
            sym, now, _f(getattr(q, "event_time", None)),
            getattr(q, "sequence", None), getattr(q, "time_nano_part", None),
            _f(getattr(q, "bid_time", None)),
            getattr(q, "bid_exchange_code", None),
            _f(getattr(q, "ask_time", None)),
            getattr(q, "ask_exchange_code", None),
            bid, ask,
            _f(getattr(q, "bid_size", None)), _f(getattr(q, "ask_size", None)),
        ))

    def _on_greeks(self, g: Greeks):
        sym = getattr(g, "event_symbol", "") or ""
        if not sym:
            return
        try:
            row = (sym, float(g.delta or 0), float(g.gamma or 0),
                   float(g.theta or 0), float(g.vega or 0),
                   float(g.volatility or 0), _time.time())
        except (TypeError, ValueError):
            return
        self._greeks_buf[sym] = row
        # MANIFOLD — all 13 fields. `volatility`, `rho` and `price` were being
        # thrown away; volatility is the smile and rho is simply free here.
        def _g(v):
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None
        self._greeks_series_buf.append((
            sym, _time.time(), _g(getattr(g, "event_time", None)),
            getattr(g, "event_flags", None), _g(getattr(g, "index", None)),
            _g(getattr(g, "time", None)), getattr(g, "sequence", None),
            _g(getattr(g, "price", None)), _g(getattr(g, "volatility", None)),
            _g(getattr(g, "delta", None)), _g(getattr(g, "gamma", None)),
            _g(getattr(g, "theta", None)), _g(getattr(g, "rho", None)),
            _g(getattr(g, "vega", None)),
        ))

    # ── 🔴 r72 — OPENING-RANGE RESCUE ───────────────────────────────────
    # WHY THIS EXISTS. On 2026-08-21 the feed ate the open: overnight "no 5m
    # data returned" warnings, and the ORB range only ESTABLISHED at 10:01-10:03
    # ET after a manual fix. ORB entries die at 11:00, so losing the open costs
    # the WHOLE ORB DAY — and ORB is the flagship trade (96% win, +$30,696,
    # worst loss -$16). Nothing in code prevented a repeat.
    #
    # ⚠️ `get_orb_range` FAILS SOFT AND THAT IS THE TRAP. With today's 09:30 bar
    # absent it falls through to EXPIRED carrying YESTERDAY'S RANGE — a
    # plausible-looking range for the wrong day. It does not raise, it does not
    # warn loudly. That is why the outage took until 10:01 to notice.
    #
    # ⚠️ UNSUBSCRIBE FIRST, THEN RESUBSCRIBE — operator's requirement, and it
    # matters: leaving the original 5m subscription warm while adding a second
    # for the same tenor means two live subscriptions racing to write the same
    # rows. One in, one out.
    #
    # ⚠️ ONCE PER SESSION, GUARDED BY DATE. Worst case is all 15 boxes doing
    # this at the same moment during an unusual event; one extra subscribe each
    # is survivable, a retry loop is not.
    async def _maybe_rescue_opening_range(self, streamer, now: Optional[datetime] = None) -> bool:
        """If today's opening tape is missing, short or disagreeing after the window, re-pull it on this session.

        v5.9 (r74, ORP.3): not only a MISSING 09:30 5m bar. 2026-11-02 AMZN held a 09:30 1m and 5m bar captured when
        the socket dropped, so the v4.8 check (any 09:30 5m row) passed and nothing was re-pulled; get_orb_range then
        froze the range from it. Now analysis/opening_tape.problem() judges the five 1m bars 09:30-09:34 and the 09:30
        5m row the way get_orb_range does, and any problem re-pulls BOTH tenors from 09:30 (unsubscribe first, then
        resubscribe; the store upserts the replay). From 09:36 to ORB_RESCUE_UNTIL_ET, at most ORB_RESCUE_MAX times a
        session and ORB_RESCUE_EVERY_S apart (the first at once). Returns True if a rescue was attempted. Never raises.
        """
        try:
            now = now or datetime.now(ET)
            today = now.date().isoformat()
            if not (now.weekday() < 5 and (9, 36) <= (now.hour, now.minute) < tuple(ORB_RESCUE_UNTIL_ET)):
                return False
            rec = getattr(self, "_orb_rescue", None)
            if not rec or rec[0] != today:
                rec = [today, 0, 0.0]
                self._orb_rescue = rec
            if rec[1] >= ORB_RESCUE_MAX or (rec[1] and _time.monotonic() - rec[2] < ORB_RESCUE_EVERY_S):
                return False
            _open_ms = int(datetime.combine(
                now.date(), dtime(9, 30), tzinfo=ET).timestamp() * 1000)
            con = self.store.conn
            # v4.8 — THE 09:30 BAR ITSELF, not "anything since the open".
            n5 = con.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol=? AND interval='5m'"
                " AND ts_epoch_ms >= ? AND ts_epoch_ms < ?",
                (INSTRUMENT, _open_ms, _open_ms + 300_000)).fetchone()
            if not (n5 and n5[0]):
                why = "today's 09:30 5m bar is MISSING"
            else:
                row5 = con.execute(
                    "SELECT high, low FROM candles WHERE symbol=? AND interval='5m'"
                    " AND ts_epoch_ms >= ? AND ts_epoch_ms < ? ORDER BY ts_epoch_ms LIMIT 1",
                    (INSTRUMENT, _open_ms, _open_ms + 300_000)).fetchone()
                bars = {}
                for ts, hi, lo in con.execute(
                        "SELECT ts_epoch_ms, high, low FROM candles WHERE symbol=? AND interval='1m'"
                        " AND ts_epoch_ms >= ? AND ts_epoch_ms < ?",
                        (INSTRUMENT, _open_ms, _open_ms + 300_000)).fetchall():
                    bars[30 + int((int(ts) - _open_ms) // 60_000)] = (hi, lo)
                why = opening_tape.problem(bars, (row5[0], row5[1]))
                if why is None:
                    return False                # the tape is complete; nothing to do
            rec[1] += 1
            rec[2] = _time.monotonic()          # set BEFORE the attempt
            logger.warning("ORB RESCUE: %s at %s - re-pulling 1m and 5m from the open (attempt %d of %d). "
                           "get_orb_range will not establish the range from this tape.",
                           why, now.strftime("%H:%M:%S"), rec[1], ORB_RESCUE_MAX)
            start = datetime.combine(now.date(), dtime(9, 30), tzinfo=ET)
            for tf in ("5m", "1m"):
                try:
                    await streamer.unsubscribe_candle(self.dx_symbol, tf)
                    logger.info("ORB RESCUE: unsubscribed %s %s", self.dx_symbol, tf)
                except Exception as exc:                        # noqa: BLE001
                    # ⚠️ NOT FATAL, BUT NAMED. If the unsubscribe fails the
                    # resubscribe below may leave two live subscriptions for one
                    # tenor, so the operator needs to see it rather than have it
                    # swallowed.
                    logger.warning("ORB RESCUE: unsubscribe %s failed (%s) — "
                                   "resubscribing anyway; watch for duplicate %s",
                                   tf, _explain_exc(exc), tf)
                await streamer.subscribe_candle(
                    [self.dx_symbol], tf, start_time=start,
                    extended_trading_hours=False)
                logger.warning("ORB RESCUE: resubscribed %s %s from %s",
                               self.dx_symbol, tf, start.isoformat())
            return True
        except Exception as exc:                                # noqa: BLE001
            logger.error("ORB RESCUE failed: %s — the feed is unaffected",
                         _explain_exc(exc))
            return False

    def _maybe_follow_assignment(self, now: Optional[datetime] = None) -> Optional[str]:
        """v5.9 (r74, FEED.15) — the node to switch to, ONCE a day and only before ASSIGN_SWITCH_BY_ET: control has
        assigned a node this box is not on, the current connection is authorized and the assigned node is not cooling.
        None otherwise. Never raises."""
        try:
            now = now or datetime.now(ET)
            if now.weekday() >= 5 or (now.hour, now.minute) >= tuple(ASSIGN_SWITCH_BY_ET):
                return None
            today = now.date().isoformat()
            if getattr(self, "_assign_switch_done_for", "") == today or not _LAST_ATTEMPT.get("authorized"):
                return None
            asg, _why = _NODES.assignment()
            if not asg or asg == _LAST_ATTEMPT.get("ip"):
                return None
            if _NODES._cool_until(asg) > _NODES.clock():
                return None
            self._assign_switch_done_for = today
            return asg
        except Exception:                                      # noqa: BLE001
            return None

    # ── v5.8 (PARK.5) — THE GATE TAPE IS RE-PULLED BEFORE PARK READS IT ─────────────────────────────────────────────
    def _commit_refill_due(self, sym: str, today: str, now_mono: float, final: bool) -> bool:
        """Cadence and cap for one store symbol's refill (pure bookkeeping; the caller has found a gap)."""
        from config import PARK_TAPE_REFILL_EVERY_S, PARK_TAPE_REFILL_MAX
        rec = self._commit_refill.get(sym)
        if rec is None or rec[0] != today:
            rec = [today, 0, 0.0, False]
            self._commit_refill[sym] = rec
        if final and not rec[3]:
            rec[3] = True                                   # the one forced pull after the 10:59 bar
        elif rec[1] >= PARK_TAPE_REFILL_MAX or (rec[2] and now_mono - rec[2] < PARK_TAPE_REFILL_EVERY_S):
            return False
        rec[1] += 1
        rec[2] = now_mono
        return True

    async def _maybe_refill_commit_tape(self, streamer, now: Optional[datetime] = None) -> List[str]:
        """On an equity box, inside PARK_TAPE_WATCH_ET: re-pull a SHORT 1m gate tape (own or pair) from today's 09:30,
        or PRIME-deep when a prior session is short, on this streamer. Returns the store symbols re-pulled. Never
        raises."""
        done: List[str] = []
        try:
            pair = _park_pair_symbol()
            if not pair:
                return done
            from config import PARK_TAPE_WATCH_ET, PARK_TAPE_FINAL_REFILL_ET
            now = now or datetime.now(ET)
            hm = (now.hour, now.minute)
            if now.weekday() >= 5 or not (tuple(PARK_TAPE_WATCH_ET[0]) <= hm < tuple(PARK_TAPE_FINAL_REFILL_ET[1])):
                return done
            final = tuple(PARK_TAPE_FINAL_REFILL_ET[0]) <= hm < tuple(PARK_TAPE_FINAL_REFILL_ET[1])
            from strategy.park_plan import session_bars, tape_gaps, judged_upto
            upto = judged_upto(hm)
            today = now.date()
            for store_sym, dx_sym in ((str(INSTRUMENT), self.dx_symbol), (pair, pair)):
                gaps = tape_gaps(session_bars(store_sym, today), upto)
                if not gaps or not self._commit_refill_due(store_sym, today.isoformat(), _time.monotonic(), final):
                    continue
                prior_short = any("prior" in g for g in gaps)
                start = (_backfill_start("1m", now_et=now, held=False) if prior_short
                         else datetime.combine(today, dtime(*SESSION_OPEN_HM), tzinfo=ET))
                logger.warning("PARK TAPE REFILL: %s 1m short at %s (%s) - re-pulling from %s on this session",
                               store_sym, now.strftime("%H:%M:%S"), "; ".join(gaps[:3]), start.isoformat())
                try:
                    await streamer.unsubscribe_candle(dx_sym, "1m")
                except Exception as exc:                        # noqa: BLE001
                    logger.warning("PARK TAPE REFILL: unsubscribe %s 1m failed (%s) - resubscribing anyway",
                                   dx_sym, _explain_exc(exc))
                await streamer.subscribe_candle([dx_sym], "1m", start_time=start, extended_trading_hours=False)
                done.append(store_sym)
        except Exception as exc:                                # noqa: BLE001
            logger.error("PARK TAPE REFILL failed: %s - the feed is unaffected", _explain_exc(exc))
        return done

    # ── MANIFOLD PART 2 HANDLERS ────────────────────────────────────────
    # ⚠️ EVERY FIELD THE EVENT CARRIES IS BUFFERED. No selection at capture:
    # the feed's job is to make analysis possible, not to decide what will
    # turn out to be interesting.
    @staticmethod
    def _n(v):
        """Number or None — NEVER 0.0 as a fallback."""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return None if f != f else f

    @staticmethod
    def _s(v):
        return None if v is None else str(v)

    def _on_trade(self, t):
        sym = _base_symbol(getattr(t, "event_symbol", "") or "")
        if not sym:
            return
        n, ss = self._n, self._s
        self._trade_buf.append((
            sym, _time.time(), n(getattr(t, "event_time", None)),
            n(getattr(t, "time", None)), getattr(t, "sequence", None),
            ss(getattr(t, "exchange_code", None)), getattr(t, "day_id", None),
            ss(getattr(t, "tick_direction", None)),
            1 if getattr(t, "extended_trading_hours", False) else 0,
            n(getattr(t, "price", None)), n(getattr(t, "change", None)),
            n(getattr(t, "size", None)), n(getattr(t, "day_volume", None)),
            n(getattr(t, "day_turnover", None))))

    def _on_time_and_sale(self, ts_ev):
        """Every print. ⚠️ `aggressor_side` IS THE PRIZE — buy vs sell
        initiated, per print. Nothing in this repo has ever seen who lifted
        the offer versus hit the bid."""
        sym = _base_symbol(getattr(ts_ev, "event_symbol", "") or "")
        if not sym:
            return
        n, ss = self._n, self._s
        self._prints_buf.append((
            sym, _time.time(), n(getattr(ts_ev, "event_time", None)),
            n(getattr(ts_ev, "index", None)), n(getattr(ts_ev, "time", None)),
            getattr(ts_ev, "sequence", None),
            ss(getattr(ts_ev, "exchange_code", None)),
            n(getattr(ts_ev, "price", None)), n(getattr(ts_ev, "size", None)),
            n(getattr(ts_ev, "bid_price", None)),
            n(getattr(ts_ev, "ask_price", None)),
            ss(getattr(ts_ev, "aggressor_side", None)),
            1 if getattr(ts_ev, "spread_leg", False) else 0,
            1 if getattr(ts_ev, "extended_trading_hours", False) else 0,
            1 if getattr(ts_ev, "valid_tick", False) else 0,
            ss(getattr(ts_ev, "type", None)), ss(getattr(ts_ev, "buyer", None)),
            ss(getattr(ts_ev, "seller", None)),
            ss(getattr(ts_ev, "exchange_sale_conditions", None))))

    def _on_summary(self, sm):
        """⚠️ CARRIES prev_day_close_price — a SECOND, independent source for
        the scalar `runaway_continuation` takes as `prev_close`, whose 1d
        dependency is invisible at its call site and which was missing from the
        warehouse entirely on 2026-08-21."""
        sym = _base_symbol(getattr(sm, "event_symbol", "") or "")
        if not sym:
            return
        n = self._n
        self._summary_buf.append((
            sym, _time.time(), n(getattr(sm, "event_time", None)),
            getattr(sm, "day_id", None), getattr(sm, "prev_day_id", None),
            n(getattr(sm, "open_interest", None)),
            n(getattr(sm, "day_open_price", None)),
            n(getattr(sm, "day_high_price", None)),
            n(getattr(sm, "day_low_price", None)),
            n(getattr(sm, "day_close_price", None)),
            n(getattr(sm, "prev_day_close_price", None)),
            n(getattr(sm, "prev_day_volume", None))))

    def _on_underlying(self, u):
        """⚠️ put_call_ratio, front/back volatility — TERM STRUCTURE AND FLOW
        SKEW FROM THE VENDOR, no derivation needed."""
        sym = _base_symbol(getattr(u, "event_symbol", "") or "")
        if not sym:
            return
        n = self._n
        self._underlying_buf.append((
            sym, _time.time(), n(getattr(u, "event_time", None)),
            n(getattr(u, "index", None)), n(getattr(u, "time", None)),
            getattr(u, "sequence", None), n(getattr(u, "volatility", None)),
            n(getattr(u, "front_volatility", None)),
            n(getattr(u, "back_volatility", None)),
            n(getattr(u, "call_volume", None)), n(getattr(u, "put_volume", None)),
            n(getattr(u, "option_volume", None)),
            n(getattr(u, "put_call_ratio", None))))

    def _on_theo(self, tp):
        # 🔴 r116 — THE FULL STREAMER SYMBOL, NOT THE BASE. TheoPrice is a
        # PER-CONTRACT analytic: `.QQQ260825C495`, `.QQQ260825C500`, ... and
        # `theo_series` is keyed PRIMARY KEY (symbol, ts_epoch). Collapsing to
        # "QQQ" via _base_symbol would land every contract on the SAME key at
        # the same second, so ~250 strikes would overwrite one another and the
        # table would look populated while holding one arbitrary contract.
        # That is worse than the empty table it replaces: an empty table is
        # visibly empty, and this would have been silently wrong.
        sym = str(getattr(tp, "event_symbol", "") or "").strip()
        if not sym:
            return
        n = self._n
        self._theo_buf.append((
            sym, _time.time(), n(getattr(tp, "event_time", None)),
            n(getattr(tp, "index", None)), n(getattr(tp, "time", None)),
            getattr(tp, "sequence", None), n(getattr(tp, "price", None)),
            n(getattr(tp, "underlying_price", None)),
            n(getattr(tp, "delta", None)), n(getattr(tp, "gamma", None)),
            n(getattr(tp, "dividend", None)), n(getattr(tp, "interest", None))))

    async def _reconcile_chain_subs(self, streamer):
        """Every flush cycle: make the socket's Greeks/Quote subscriptions match
        what the bot requested via chain_subs. Expiry rollover unsubscribes all
        and clears the marks table (yesterday's 0DTE symbols are dead air)."""
        expiry, symbols = self.store.read_chain_subs()
        if not symbols:
            return
        if expiry != self._chain_expiry:
            if self._chain_subscribed:
                logger.info("chain marks: expiry rollover %s -> %s — resubscribing",
                            self._chain_expiry or "(none)", expiry)
                await streamer.unsubscribe_all(Greeks)
                await streamer.unsubscribe_all(Quote)
                # r118 — nothing to unsubscribe; TheoPrice is no longer
                # subscribed. Left as a comment so the next reader does not
                # re-add an unsubscribe for a stream that has no subscription.
            self._chain_subscribed.clear()
            self._quotes_buf.clear()
            self._greeks_buf.clear()
            self.store.clear_chain_marks()
            self._chain_expiry = expiry
        new = [s for s in symbols if s not in self._chain_subscribed]
        if new:
            # v3.5: CHUNKED subscribes. An SPX 0DTE chain is hundreds of
            # strikes; one giant subscribe frame risks a websocket 1009
            # (message too long) that would bounce the ENTIRE socket —
            # candles included. 75 symbols per frame is comfortably small.
            for i in range(0, len(new), 75):
                chunk = new[i:i + 75]
                await streamer.subscribe(Greeks, chunk)
                await streamer.subscribe(Quote,  chunk)
                # r116 — TheoPrice rides the SAME per-contract subscription.
                # It was subscribed to the plain ticker with the four
                # underlying-level aux events, where nothing publishes it:
                # accepted, then silent since 2026-08-22. Proven on QQQ
                # 2026-08-24 by tools/probe_aux_streams.py — 12 events on 12
                # option symbols, 0 on the ticker, with Greeks/Quote as
                # controls. Wrapped alone so an entitlement gap costs THIS
                # stream and not the chain marks everything trades on.
                # 🔴 r118 — REVERTED, 2026-08-25 09:40 ET, MID-SESSION.
                # r116 added TheoPrice here and it landed on the fleet last
                # night. This morning SPX lost its ENTIRE per-contract
                # subscription at 13:27 UTC — greeks, quotes, chain marks and
                # theo all stopped at the SAME instant (age 688-698s) while
                # ticker-level events kept arriving, so options_chain returned
                # None every tick and SPX could not evaluate a single strategy
                # during the ORB window. QQQ on identical code stayed healthy.
                # ⚠️ THE ASYMMETRY IS WIDTH: SPX is 500 contracts (7 chunks),
                # QQQ 372 (5). Adding a THIRD event type to each chunk is the
                # only change, and SPX is where it first crossed whatever the
                # limit is. The per-chunk try/except did NOT save it — the
                # subscribe succeeded (theo had 5026 rows) and the connection
                # degraded later, which is a failure mode a wrapper cannot see.
                # ⚠️ THE COST OF KEEPING IT IS A TRADING DAY; the cost of
                # dropping it is a stream NOTHING READS YET. Not a close call.
                # theo_series and _on_theo stay — the writer is correct and the
                # probe proved the symbol space. Re-enable only behind a
                # per-symbol opt-in, tested on ONE narrow box, never fleet-wide
                # on a session morning.
            self._chain_subscribed.update(new)
            logger.info("chain marks: subscribed %d new symbols (%d total, expiry %s)",
                        len(new), len(self._chain_subscribed), expiry)

    def _flush(self):
        rows: List[Tuple] = []
        for bucket in self.buffer.values():
            rows.extend(bucket.values())
        self.buffer = {}
        self.store.upsert_candles(rows)
        # v3.4: chain marks ride the same flush cadence
        q, g = list(self._quotes_buf.values()), list(self._greeks_buf.values())
        self._quotes_buf.clear()
        self._greeks_buf.clear()
        self.store.upsert_chain_quotes(q)
        self.store.upsert_chain_greeks(g)
        # ── MANIFOLD (2026-08-22) — the full-fidelity series ride the same
        # flush. Taken and cleared BEFORE the write so a raising writer cannot
        # make the buffer grow without bound across cycles.
        # ⚠️ WRAPPED SO A SERIES WRITE CAN NEVER STALL CAPTURE. Operator's
        # rule: derived/observational data INFORMS, it never blocks. The raw
        # candle and chain_marks writes above have already committed; if these
        # fail the tape is still intact and the gap shows up as a short series
        # rather than as a dead feed.
        gs, qs = self._greeks_series_buf, self._quote_series_buf
        self._greeks_series_buf, self._quote_series_buf = [], []
        pr, tr = self._prints_buf, self._trade_buf
        sm, un, th = self._summary_buf, self._underlying_buf, self._theo_buf
        self._prints_buf, self._trade_buf = [], []
        self._summary_buf, self._underlying_buf, self._theo_buf = [], [], []
        try:
            self.store.append_greeks_series(gs)
            self.store.append_quote_series(qs)
            self.store.append_prints(pr)
            self.store.append_last_trade(tr)
            self.store.append_session_summary(sm)
            self.store.append_underlying(un)
            self.store.append_theo(th)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("series append failed (%d greeks, %d quotes): %s "
                           "— raw tape unaffected", len(gs), len(qs), exc)
        self.store.heartbeat()
        self.store.commit()
        return len(rows) + len(q) + len(g)

    def _log_backfill_depth(self):
        """One-time per (symbol, interval): report depth vs required count so
        entitlement gaps surface in the journal (FIRST-RUN CHECKLIST #1)."""
        for (dx_sym, tf, _start, _ext) in self.subs:
            sym = self.symbol_map[(dx_sym, tf, bool(_ext))]
            if self.backfill_logged.get((sym, tf)):
                continue
            n = self.store.bar_count(sym, tf)
            need = TIMEFRAMES.get(tf, {}).get("candles", 0) if sym == INSTRUMENT else 1
            level = logging.INFO if n >= need else logging.WARNING
            logger.log(level, "backfill %s %s: %d bars in store (need %d)%s",
                       sym, tf, n, need, "" if n >= need else "  << SHORT — check entitlement")
            self.backfill_logged[(sym, tf)] = True

    @staticmethod
    def _feed_stood_down() -> bool:
        """Should this run stand down? v4.3: MAINTENANCE, and nothing else.

        ONE predicate, TWO call sites (the reconnect gate and the RTH-over
        break). v3.9 wrote the same condition inline in both places and v3.10
        had to patch both; a third caller would have had to remember a third
        time. It is a method so the two can never disagree again.

        THE DISTINCTION IS PURPOSE, NOT TIME — which is the whole lesson of
        2026-08-01..08-04. What the gate protects against is a box HOLDING a
        live DXLink subscription when there is no session to serve it: the
        maintenance wake that put 29 boxes on the wire for work needing no
        market data. A `--once` run holds nothing. It connects, pulls HISTORY
        from 09:30, flushes and exits, and history does not stop existing at
        16:00 — so gating it on the clock blocked the ONLY path the EOD candle
        retrieval has, silently, for two sessions.

        SERVICE MODE (once=False) is unchanged from v3.9 in every respect.

        ── FEED.1 (2026-08-15) — THE THIRD PURPOSE ────────────────────────────
        MAINTENANCE is HARD OFF and overrides everything, `--once` included.
        It exists because the operator needs a window where all 29 boxes can be
        up for fleet updates with nothing on the wire — and that CANNOT be a
        clock rule, because the overnight capture pass runs at the same hours
        and wants the opposite.

        ⚠️ IT ANNOUNCES ITSELF AT WARNING. The 2026-08-03/04 loss was a silent
        gate: `Feed idle — outside RTH` at INFO, then `0 bars`, then fourteen
        38-byte header-only CSVs, and DXFeed history is same-evening only so
        both sessions are gone. **A suppressed run must never be mistakable for
        a failed fetch**, so this says the mode by name and says the data is
        NOT being collected.
        """
        if _maintenance_now():
            if not getattr(CandleFeed, "_maint_said", False):
                CandleFeed._maint_said = True
                # v4.3 — the trailing "%s" arg used to read
                # `"including this --once run" if once else "service mode"`.
                # `once` is no longer a parameter, so that line raised
                # NameError the first time maintenance was declared — and
                # `import candle_feed` could not see it, because the name is
                # only resolved when this branch RUNS. Found by
                # tests/check_feed_always_on.py driving the predicate, which is
                # the whole argument for executing checks rather than reading
                # source (WORKING_AGREEMENT 21).
                logger.warning(
                    "[feed-mode] MAINTENANCE - standing down completely. NO "
                    "candles will be collected on this box until OT_FEED_MODE "
                    "is cleared. This is DELIBERATE, not a fetch failure; if "
                    "you expected tape, the mode is wrong.")
            return True
        # v4.3 — THE RTH CLAUSE IS GONE. It used to read
        #     `return not is_rth() and not once`
        # and its own rationale above is what retired it: the gate existed so a
        # MAINTENANCE wake could not put 29 BOXES on the wire at once. The fleet
        # is 15 and they are the same 15 every day; a normal session already
        # carried ~20 boxes on this feed without strain, so the crowd the gate
        # was sized for no longer exists. Operator, 2026-08-20: boxes subscribe
        # whenever they are up.
        #
        # ⚠️ MAINTENANCE SURVIVES, AND IT IS NOW THE ONLY REASON TO STAND DOWN.
        # It was never the clock rule — it is the window where the fleet can be
        # up with nothing on the wire, and it must stay expressible.
        # ⚠️ `once` IS NO LONGER A PARAMETER. It existed to exempt the one-shot
        # EOD pull from a CLOCK rule; with no clock rule there is nothing to be
        # exempt from, and maintenance overrode it anyway. A parameter that can
        # no longer change the answer is a parameter that misleads the reader.
        return False

    async def run(self, once: bool = False):
        session = get_session()
        backoff = RECONNECT_MIN_S
        limit_level = None          # v5.6 (FEED.13): None = no session-limit lockout; n = lockout waits so far - 1
        limit_holds = 0             # v5.6 (FEED.13): lockout waits HELD (no alternate node) - picks the hold's rung
        while True:
            # ── FEED STAND-DOWN GATE ─────────────────────────────────────────
            # HISTORY, kept because it is the reasoning and not the rule.
            # 2026-08-01 this became an RTH gate: the loop had no time gate at
            # all (`Restart=always`, no timer), so while a box was UP the feed
            # subscribed continuously — invisible on a normal day because
            # phase_report stopped the instances at EOD, but it meant every
            # MAINTENANCE wake put 29 boxes back on the wire at once for work
            # needing no market data. FEED.1 then added maintenance as a third
            # purpose, and v3.9/v3.10 had to exempt `--once` from the clock rule
            # after two sessions of tape were lost to header-only CSVs.
            #
            # v4.3 (2026-08-20) RETIRES THE CLOCK RULE ENTIRELY. The crowd it
            # was sized for is gone: 15 boxes, the same 15 daily. What remains
            # is MAINTENANCE — a purpose, not a time — which is exactly what
            # `_feed_stood_down`'s own doctrine said the distinction always was.
            #
            # ⚠️ WHAT HOLDING THE SOCKET 24h DOES AND DOES NOT DO.
            # It does NOT contaminate the RTH series: the v4.2 write guard
            # routes every non-RTH bar to <SYM>_EXT, for EVERY interval, so
            # overnight 1m/5m/15m are stored and segregated rather than dropped
            # or merged. It does NOT add chain snapshots outside RTH:
            # `analysis.chain_snapshot.snapshot()` takes the chain as an
            # ARGUMENT and is called from main.py's tick loop, which returns
            # early on `not is_rth()` — so chain archival is still RTH-only and
            # this change cannot alter it in either direction.
            # ⚠️ SPX HAS NO OVERNIGHT SESSION. An index producing nothing
            # between 16:00 and 09:30 is correct, not a fetch failure — it is
            # the same control that proved the v4.2 contamination was real.
            # v4.3 — MAINTENANCE ONLY. The sleep-until-open block that lived
            # here is deleted rather than left dead: a branch that can no longer
            # run still reads as live to anyone auditing the file.
            #
            # ⚠️ AND IT FIXES A LATENT DEFECT ON THE WAY OUT, stated because it
            # is a behaviour change and not merely a deletion. The old block
            # slept only while `seconds_until_rth_open() > FEED_WARM_LEAD_S`,
            # and that function RETURNS 0 DURING RTH — so maintenance declared
            # inside the session fell straight through and connected anyway.
            # The hard-off was silently defeated in exactly the hours a fleet
            # update is most disruptive. Standing down is now unconditional.
            # ⚠️ r288 — THE DISK GUARD WAS HERE AND HAS MOVED TO main.py's TICK
            # LOOP. This `while True` is the RECONNECT loop, not a tick loop: an
            # `async with DXLinkStreamer` below opens the stream and an inner
            # loop handles events for the life of that connection, so a check
            # here ran ONCE PER CONNECTION.
            if self._feed_stood_down():
                await asyncio.sleep(60)
                continue
            _LAST_ATTEMPT["ip"], _LAST_ATTEMPT["authorized"] = None, False   # v5.6 (FEED.13): this attempt's node
            try:
                async with SessionReleasingStreamer(session) as streamer:   # v5.6 (FEED.13)
                    # v3.4: fresh socket — chain subscriptions must be rebuilt
                    self._chain_expiry = ""
                    self._chain_subscribed.clear()
                    # v3.8: subscribe each (symbol, tf) INDEPENDENTLY. A single
                    # failing subscribe_candle used to throw out of the whole
                    # `async with`, killing the ENTIRE stream — so one bad symbol
                    # or timeframe (e.g. an entitlement gap on XOM) took down all
                    # candles, for two days, with only a wrapped "unhandled errors
                    # in a TaskGroup" to show for it. Now a failure is logged with
                    # its REAL cause (see _explain_exc) and skipped.
                    ok_subs = 0
                    for (dx_sym, tf, start, ext) in self.subs:
                        start = self._start_for(dx_sym, tf, ext, start)   # r16: from the store, every (re)subscribe
                        try:
                            await streamer.subscribe_candle(
                                [dx_sym], tf, start_time=start,
                                extended_trading_hours=ext)
                            logger.info("subscribed %s %s from %s%s", dx_sym, tf,
                                        start.isoformat(),
                                        "  [EXTENDED HOURS]" if ext else "")
                            ok_subs += 1
                        except Exception as sub_e:
                            logger.error("SUBSCRIBE FAILED %s %s: %s — continuing without it",
                                         dx_sym, tf, _explain_exc(sub_e))
                    if ok_subs == 0:
                        raise RuntimeError("no candle subscriptions succeeded")
                    logger.info("%d/%d candle subscriptions live", ok_subs, len(self.subs))
                    await self._reconcile_chain_subs(streamer)
                    backoff = RECONNECT_MIN_S
                    _NODES.ok(_LAST_ATTEMPT["ip"])         # v5.6 (FEED.13): this node works - stay on it
                    logger.info("FEED.13 connected on dxlink node %s", _LAST_ATTEMPT["ip"] or "dns")
                    if limit_level is not None:             # v5.6 (FEED.13): a live connection ends the lockout
                        logger.info("SESSION_LIMIT lockout cleared - connected after %d lockout wait(s), %d held",
                                    limit_level + 1, limit_holds)
                        limit_level, limit_holds = None, 0
                    last_flush = 0.0
                    last_prune = _time.time()
                    # ── 🔴 MANIFOLD PART 2 (2026-08-22) — SUBSCRIBE THE REST ─
                    # Five event types the SDK offers that this feed never
                    # asked for. Each is subscribed INDEPENDENTLY and wrapped,
                    # so an entitlement gap costs THAT ONE PORT on THIS ONE BOX
                    # and is named in the log — never the whole socket.
                    # r116 — TheoPrice is NOT here any more: it is per-CONTRACT
                    # and now rides the chain subscription in
                    # _reconcile_chain_subs. Underlying stays: it IS an
                    # underlying-level event and the ticker is the right space
                    # for it, though it has never published either — retest
                    # during RTH before calling it uncarried, since the 45s
                    # after-hours probe saw only 1 Trade on this arm.
                    # 🔴 r36 — QUOTE JOINS THE UNDERLYING SET (FEED.2). r64 took
                    # FOUR of the five streams for the ticker and left Quote,
                    # because Quote WAS subscribed — per CONTRACT, in
                    # `_reconcile_chain_subs`, where the bot needs it to price a
                    # spread. So the underlying's own bid/ask was never asked
                    # for: measured 2026-09-17, **0 of 22,846,560 `quote_series`
                    # rows are a non-option symbol**.
                    # ⚠️ IT IS THE ONLY SOURCE OF RESTING DEPTH. `prints` says
                    # what TRADED; `bid_size`/`ask_size` say what is WAITING —
                    # and the operator's question is where size parks, which
                    # traded volume cannot answer. Measured the same day:
                    # volume within ±$0.25 of a session extreme carries a lift of
                    # 1.02x against a random price in the traded band, i.e. none.
                    # A level that HELD is one price turned away from, so volume
                    # AT it conflates absorption with traversal. Depth does not.
                    # ⚠️ COLLECTION ONLY, AND NOTHING READS IT (§31). It is
                    # subscribed here, stored by `_on_quote` — which already keys
                    # on `event_symbol` and is symbol-agnostic, so no handler
                    # changes — and read by no decision. It is banked until there
                    # is enough of it to answer the question with numbers.
                    # ⚠️ AND IT RIDES THE WRAPPED, INDEPENDENT SUBSCRIBE BELOW,
                    # NOT THE CHAIN'S CHUNKED ONE. r118 is why that distinction
                    # matters: adding a stream to the per-CONTRACT subscription
                    # cost SPX its ENTIRE chain subscription mid-session on
                    # 2026-08-25 — greeks, quotes and marks all stopped at the
                    # same instant. Each stream here fails alone and says so.
                    for _ev, _label in ((Trade, "Trade"),
                                        (TimeAndSale, "TimeAndSale"),
                                        (Summary, "Summary"),
                                        (Underlying, "Underlying"),
                                        (Quote, "Quote")):
                        try:
                            await streamer.subscribe(_ev, [self.dx_symbol])
                            logger.info("subscribed %s %s", self.dx_symbol, _label)
                        except Exception as exc:                # noqa: BLE001
                            logger.warning("SUBSCRIBE FAILED %s %s: %s — "
                                           "continuing without it",
                                           self.dx_symbol, _label, exc)
                    quiet_since: Optional[float] = None
                    while True:
                        try:
                            c = await asyncio.wait_for(streamer.get_event(Candle), timeout=1.0)
                            self._on_candle(c)
                            quiet_since = None
                        except asyncio.TimeoutError:
                            if quiet_since is None:
                                quiet_since = _time.monotonic()
                        # v3.4: drain any queued Greeks/Quote events, non-blocking
                        while True:
                            g = streamer.get_event_nowait(Greeks)
                            if g is None:
                                break
                            self._on_greeks(g)
                        while True:
                            q = streamer.get_event_nowait(Quote)
                            if q is None:
                                break
                            self._on_quote(q)
                        # MANIFOLD PART 2 — drain the five new streams the
                        # same way. Wrapped as a group: an unexpected payload
                        # shape from any one of them must not stop the candle
                        # loop, which is the tape everything else depends on.
                        try:
                            for _ev, _fn in ((Trade, self._on_trade),
                                             (TimeAndSale, self._on_time_and_sale),
                                             (Summary, self._on_summary),
                                             (Underlying, self._on_underlying),
                                             (TheoPrice, self._on_theo)):
                                while True:
                                    _e = streamer.get_event_nowait(_ev)
                                    if _e is None:
                                        break
                                    _fn(_e)
                        except Exception as exc:                # noqa: BLE001
                            logger.debug("aux stream drain: %s", exc)
                        now = _time.monotonic()
                        if now - last_flush >= FLUSH_INTERVAL_S:
                            await self._reconcile_chain_subs(streamer)
                            # r72 — rides the flush cadence, so the check costs
                            # one indexed COUNT every ~15s and only inside the
                            # 09:36-11:00 window. Self-disarming after one
                            # attempt per date.
                            await self._maybe_rescue_opening_range(streamer)
                            _asg = self._maybe_follow_assignment()          # v5.9 (r74, FEED.15)
                            if _asg:
                                raise PlannedNodeSwitch("control assigned dxlink node %s; leaving %s"
                                                        % (_asg, _LAST_ATTEMPT["ip"] or "dns"))
                            n = self._flush()
                            # v5.8 (PARK.5) — AFTER the flush, so a bar still buffered never reads as a gap
                            await self._maybe_refill_commit_tape(streamer)
                            last_flush = now
                            if n:
                                logger.debug("flushed %d bars", n)

                            # v3.9 — SESSION IS OVER: drop the socket. The gate at
                            # the top of the reconnect loop only decides whether
                            # to CONNECT; without this the feed would stream on
                            # past 16:00 for as long as the box happened to stay
                            # up. That is the case that matters — the operator
                            # must be able to FORGET a box is up and have it not
                            # be a problem, which is this project's standing rule
                            # about anything depending on someone remembering.
                            # Rides the existing flush cadence rather than adding
                            # a timer: we are already here, once per cycle.
                            # Flushed first (above), so no buffered bar is lost.
                            # v3.9 — `and not once` here too, and this one is the
                            # blocker a naive fix would have missed. This break
                            # sits ABOVE the --once drain-exit, so a one-shot run
                            # outside RTH would connect, break out on its first
                            # flush cycle, return to the outer loop, hit the gate
                            # again and sleep — the same hang, one layer down,
                            # with the backfill still undrained. Both sites had
                            # to move together or neither works.
                            # v4.3 — no longer an "RTH over" break: the socket
                            # is held through the close. This fires only when
                            # MAINTENANCE is declared mid-run, which must take
                            # effect without waiting for a restart.
                            if self._feed_stood_down():
                                logger.warning(
                                    "MAINTENANCE declared — closing DXLink "
                                    "socket and releasing all subscriptions. "
                                    "NO candles collected until OT_FEED_MODE "
                                    "is cleared."
                                )
                                break
                            self._log_backfill_depth()
                            if once and quiet_since is not None and (now - quiet_since) > 8.0:
                                logger.info("--once: backfill drained, exiting")
                                return
                        # ── FEED.3 (2026-08-15) — PRUNING IS OFF BY DEFAULT ──
                        # ⚠️ THE BOUND WAS SIZED FOR THE LIVE LOOP AND KEPT
                        # SILENTLY CONSTRAINING ANALYTICAL CONSUMERS THAT
                        # ARRIVED LATER. It has now bitten twice: PF.2 found the
                        # boxes held 84 daily bars while the engine was handed
                        # 10 ("the history was never missing - the frame was"),
                        # and LIQ.6's 10-day section lookback landed on exactly
                        # the 240-row 1h ceiling with ZERO margin.
                        #
                        # AND IT WAS NEVER BUYING ANYTHING. Measured: a FULL
                        # YEAR of every interval, extended hours, is **54 MB per
                        # box** - on an 8 GB root. Ten days is 1.5 MB. The
                        # pruner was tidiness, not capacity.
                        #
                        # Operator's call: no pruning. The local store keeps
                        # what it collects; S3 is the archive and the weekend
                        # reporting reads the bucket, so the box no longer has
                        # to be the deep copy of anything.
                        # ⚠️ THE POISON PURGE IS UNTOUCHED AND MUST STAY - it
                        # deletes BAD rows (non-positive prices, 2038-stamped
                        # DXFeed rollover junk), not OLD ones. Different method,
                        # different purpose.
                        if PRUNE_KEEP_ROWS and _time.time() - last_prune >= PRUNE_EVERY_S:
                            for (dx_sym, tf, _s, _e) in self.subs:
                                sym = self.symbol_map[(dx_sym, tf, bool(_e))]
                                self.store.prune(sym, tf, PRUNE_KEEP_ROWS)
                            self.store.commit()
                            last_prune = _time.time()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._flush()
                _sw = _planned_switch(e)
                if _sw is not None:                                    # v5.9 (r74, FEED.15): leave for control's node
                    wait = node_switch_wait()
                    logger.warning("FEED.15 %s - redialling in %.1fs (planned, pre-open; no node cooled)", _sw, wait)
                    await asyncio.sleep(wait)
                    continue
                # v3.8: UNWRAP. asyncio TaskGroup raises an ExceptionGroup whose
                # str() is only "unhandled errors in a TaskGroup (1 sub-exception)"
                # — the real DXFeed cause is in .exceptions and was thrown away,
                # leaving XOM in a 60s reconnect loop with NO diagnosable reason
                # for two days (07-13 -> 07-15).
                limited = _is_session_limit(e)
                node = _LAST_ATTEMPT["ip"] or "dns"
                upgrade_code = None if limited else _upgrade_status(e)   # v5.6 (FEED.13): 502 at the upgrade
                if limited:
                    _NODES.refused(_LAST_ATTEMPT["ip"])    # v5.6 (FEED.13): the next dial goes to another node
                elif not _LAST_ATTEMPT["authorized"]:
                    _NODES.failed(_LAST_ATTEMPT["ip"])
                if limited or limit_level is not None:
                    # v5.6 (FEED.13): the ceiling is per dxlink node - with another node known, redial it in 1-5 s;
                    # with none, hold >= 120 s (first 120-180 s, then 200-300 s) until a connection succeeds, from
                    # the very first attempt. The quote token is kept.
                    limit_level = 0 if limit_level is None else limit_level + 1
                    switch = _NODES.alternate_available()   # v5.6 (FEED.13): another node known -> go now
                    if switch:
                        wait = node_switch_wait()
                    else:
                        wait = session_limit_wait(limit_holds)
                        limit_holds += 1
                    if limited:
                        logger.error("SESSION_LIMIT: TastyTrade refused the streamer on dxlink node %s (user sessions "
                                     "over the configured limit) - %s in %.1fs (lockout wait #%d), quote token "
                                     "kept (age %s)", node,
                                     "switching to another known node" if switch else
                                     "no other node known, holding; next attempt", wait, limit_level + 1,
                                     "%.0fs" % _QUOTE_TOKENS.age_s() if _QUOTE_TOKENS.age_s() is not None
                                     else "none")
                    else:
                        if _is_auth_error_text(_explain_exc(e)):
                            _QUOTE_TOKENS.invalidate("auth error: %s" % type(e).__name__)
                        logger.error("feed stream error on dxlink node %s: %s%s — session-limit lockout %s, "
                                     "reconnecting in %.1fs", node, _explain_exc(e),
                                     " (upgrade HTTP %s)" % upgrade_code if upgrade_code is not None else "",
                                     "switching node" if switch else "held", wait)
                elif (upgrade_code is not None and upgrade_code != 101 and _LAST_ATTEMPT["ip"]
                      and _NODES.alternate_available()):
                    # v5.6 (FEED.13): the node answered the upgrade with an error (502 Bad Gateway, 11-02 14:19 ET);
                    # it is cooled 5 min above (failed before AUTHORIZED) - go to another known node now.
                    wait = node_switch_wait()
                    logger.error("UPGRADE_REFUSED: dxlink node %s answered the websocket upgrade with HTTP %s - "
                                 "switching to another known node in %.1fs", node, upgrade_code, wait)
                else:
                    if _is_auth_error_text(_explain_exc(e)):
                        _QUOTE_TOKENS.invalidate("auth error: %s" % type(e).__name__)
                    wait = reconnect_wait(backoff)       # v5.2 (TTS.1): jittered, never in lockstep
                    logger.error("feed stream error on dxlink node %s: %s — reconnecting in %.1fs",
                                 node, _explain_exc(e), wait)
                logger.debug("feed stream traceback:\n%s",
                             "".join(traceback.format_exception(type(e), e, e.__traceback__)))
                await asyncio.sleep(wait)
                backoff = min(backoff * 2, RECONNECT_MAX_S)


class _TTNoiseFilter(logging.Filter):
    """r134 — drop the tastytrade SDK's DEBUG chatter, keep its parse failures.
    A HANDLER filter, not a logger level: the SDK logs from child loggers
    (tastytrade.streamer), and a filter on the parent never sees their records."""

    KEEP = ("Failed to parse event",)
    WINDOW_S = 60.0                      # FEED.4 (v5.4): at most one kept line per window, carrying the count
    _clock = staticmethod(_time.monotonic)

    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self._t0 = None                  # when the last kept line passed
        self._n = 0                      # suppressed since then

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno > logging.DEBUG or not record.name.startswith("tastytrade"):
            return True
        msg = record.getMessage()
        if not msg.startswith(self.KEEP):
            return False
        now = self._clock()
        if self._t0 is not None and now - self._t0 < self.WINDOW_S:
            self._n += 1
            return False
        if self._n:
            record.msg, record.args = (f"{msg} [FEED.4: +{self._n} more like it in the last "
                                       f"{now - self._t0:.0f}s, suppressed]"), None
        self._t0, self._n = now, 0
        return True


def _install_tt_noise_filter() -> None:
    for h in logging.getLogger().handlers:
        if not any(isinstance(f, _TTNoiseFilter) for f in h.filters):
            h.addFilter(_TTNoiseFilter())


def main():
    # r146 — never stream a guessed symbol (see config.INSTRUMENT_UNSET).
    import sys
    from config import INSTRUMENT_UNSET
    if INSTRUMENT == INSTRUMENT_UNSET:
        sys.stderr.write("CRITICAL: OT_INSTRUMENT is not set - candle feed refusing to start.\n")
        sys.exit(78)
    from config import INSTRUMENT_LISTED          # r175 (SYM.1)
    if not INSTRUMENT_LISTED:
        sys.stderr.write("CRITICAL: OT_INSTRUMENT=%s is not in config.STRIKE_INCREMENTS - "
                         "candle feed refusing to start.\n" % INSTRUMENT)
        sys.exit(78)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    _install_tt_noise_filter()
    _bad = {k: v for k, v in FRACTIONAL_SIZE.items() if v != "ok"}   # v5.5 (FEED.12)
    (logger.warning if _bad else logger.info)(
        "FEED.12: fractional share sizes %s (%s)", "NOT accepted - those events are still skipped" if _bad
        else "accepted", ", ".join(f"{k} {v}" for k, v in FRACTIONAL_SIZE.items()))
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="backfill, flush, exit (smoke test)")
    ap.add_argument("--db", default=None, help="override store path")
    args = ap.parse_args()

    if args.db:
        os.environ["OT_FEED_DB"] = args.db
    store = FeedStore(feed_db_path())
    logger.info("candle_feed v3.8 — store=%s symbol=%s (dxfeed=%s) vix=%s",
                feed_db_path(), INSTRUMENT, _dxfeed_symbol(), VIX_SYMBOL)
    store.purge_poison()   # v3.2: self-heal any pre-existing poison rows

    feed = CandleFeed(store)
    loop = get_loop()
    fut = asyncio.run_coroutine_threadsafe(feed.run(once=args.once), loop)
    try:
        fut.result()          # blocks for service lifetime
    except KeyboardInterrupt:
        fut.cancel()
    finally:
        store.close()


if __name__ == "__main__":
    main()
