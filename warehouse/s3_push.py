"""
warehouse/s3_push.py  v5.3
v5.3  2026-10-30  OTV5 r57 (TCS.LOG1) — THE SHADOW TRADES ARE THEIR OWN STREAM. A LOG-only TrendCreditSpread books a shadow
      trade in shadow_trades.db (execution/shadow_book.py), never in trades.db. A "shadow_trades" stage right after
      "trades" pushes it with the SAME push_trades (content-hash CDC per trade_id) under raw/shadow_trades/dt=/sym=/
      (datatype "shadow_trade", src_file shadow_trades.db) and its own ledger (shadow_trades_ledger.json), so no reader
      of raw/trades ever sees a shadow. push_trades' keywords default to exactly today's trades push. Gate
      tests/check_tcs_shadow.py.
v5.2  2026-10-25  (WH.20) — push_series FILES EACH OBJECT UNDER ITS ROWS' OWN ET DAY, NOT THE PUSH DAY (otv4 r417's
      pusher half, ported). `day = datetime.now(ET)` filed every batch by PUSH time, and SERIES_BATCH_ROWS caps each run,
      so a backlog that drained after midnight landed in the NEXT day's dt= (mainline 2026-09-23: 566 of 224,336 raw
      series objects mis-filed). The batch is now split at every ET day boundary, one object per day; the high-water
      mark advances only if every group landed (a retry rewrites the same content-hashed keys); an unreadable
      ts_epoch is filed under the push day, never dropped. push_candles / push_derived unchanged (mainline left
      them: candles derive dt= from the row; push_derived is C.9). Gate tests/check_push_row_day.py R1-R4.
v5.1  2026-10-25  OTV5 r20 (PUSH.1) — THE DERIVED STAGE RUNS IN BOUNDED MEMORY. The 2026-10-25 fleet field test measured
      the 5-minute push peaking ~700 MB on 951 MB boxes (220-430 MB into swap, 70-95 s a run) and 1.5 GB on SOFI. The cause
      was push_derived's ledger: derived_ledger.json held a 64-hex hash for EVERY row ever pushed, never pruned (147 MB on
      AMD, 177 MB on SOFI), json-loaded whole each run and rewritten whole at every flush; and every derived table was
      read into one Python list. Now: the ledger is SQLite (derived_ledger.db: tbl, rid, 16-byte digest), read per chunk;
      tables stream by rowid in DERIVED_SCAN_ROWS chunks; changed rows ship in objects of at most DERIVED_BATCH_ROWS (a
      table with a handful of changes is still ONE object); entries for rows the purge removed (rid below the table's
      lowest rowid) are pruned. The old JSON is converted ONCE by a streaming scan (never json-loaded) and removed after
      the conversion commits. The rule is unchanged: a row ships when its content hash differs from the last one S3
      confirmed. A plain dict ledger (the gates) still works. Gate tests/check_push_memory.py M1-M7. The operator:
      "Let's fix those issues".
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.12 2026-10-24  CD.1 — A SYMBOL SWITCH CANNOT MISLABEL A PUSH, AND A PAUSED BOX PUSHES NOTHING FROM ANY ENTRYPOINT.
      (1) own_symbol(): after OT_INSTRUMENT, the BOT UNIT's instrument (utils.instrument.box_instrument) - before the
      newest data/OHLC file. The conductor's ssh `--verify` and self_close run with no OT_INSTRUMENT, and the newest
      OHLC file is a previous symbol's until 16:05 on the day of a switch, so both drains labelled the new symbol's
      rows with the old one. (2) A PAUSED box (~/.optbot/push_paused, written by configure.sh item 1 when the NEW
      symbol is pushed by another host, removed by a typed OVERRIDE or item 14) pushes nothing from ANY entrypoint:
      the timer, the conductor's ssh --verify and self_close all read this one file, which a unit's Environment= is
      not. --verify still prints a DRAIN line, ending PAUSED, so the conductor holds the box visibly instead of
      reading NO_ANSWER. The operator, 2026-10-24: "Agreed entirely".
v4.11 2026-10-04  OTV4TEST r242 (CNDL.1, MIRROR OF otv4 r463 c912ce7, WA 38.2) — push_candles ships only CLOSED bars (_INTERVAL_MS, _closed_bars): the mark stopped advancing past the forming bar, which was never re-sent, so every 5m/15m/1h bar in S3 was its first ~30 s. This box never pushes (masked); mirrored so OTV5 carries the fixed pusher. Hunks applied verbatim.
v4.10 2026-09-26  OTV4TEST r150 — COMMENT ONLY, MIRRORING otv4 r444 (5800e81) UNDER WA section 38.2.
      The classifier's "a gap of 3+ STILL HOLDS THE BOX" predated r180 and was read by both
      agents as the specification; it now states what r180 ruled (heal any short prefix with
      objects on a clean drain, no gap bound; got=0 and failed>0 still hold) and the residual
      trade. Adapted, not copied: the heal's line distance is dropped (it differs per tree and
      moves with this very comment), S3.25 is this tree's S3.15. Operator: "Approve on all".
v4.9  2026-09-25  OTV4TEST r139 — A BOX PUSHES ONLY ITS OWN CANDLES, UNDER ITS OWN NAME.
      Two guards, both from the first SOFI paper box, whose feed had streamed QQQ
      after an instrument change (configure.sh v4.11 fixes the cause):
      (1) push_candles uploads a symbol's candles only when its ROOT is this box's
          instrument (SOFI, SOFI_EXT) - or the VIX family on the SPX box, as
          before. Leftover rows of a previous instrument stay local instead of
          landing in another box's partition. On a normal box the store holds
          only its own family and VIX, so nothing it pushed before changes.
      (2) own_symbol() takes OT_INSTRUMENT FIRST when it is set - the managed
          drop-in sets it explicitly - and falls back to the newest OHLC file.
          The file came first because the unit once carried no instrument; after
          an instrument change the newest file is the OLD symbol's until the
          next candle-logger run, which would have mislabelled every push.
v4.8  2026-09-24  OTV4TEST r136 — THE VIX FAMILY IS SPX'S, MATCHED BY ROOT (mainline
      r350, ported). The exact match `in ("VIX","^VIX")` let every non-SPX box
      push `sym=VIX_EXT` - this fork's feed stores VIX_EXT rows - over the SPX
      box's series in the shared warehouse. Harmless while this fork never
      pushed; the operator's 2026-09-24 ruling puts OTV4TEST boxes under the
      conductor ("managed" data capture), so it had to land before the first
      push. Operator: "Have the same toggle switch off the VIX logging": no
      OTV4TEST box ever uploads the VIX family; the feed still collects VIX for
      the box's own decisions.
v4.7  2026-09-24  OTV4TEST r128 — `level_event` JOINS `DERIVED_TABLES`. It is a
      lifecycle biography — every HELD/BREACHED (legacy: WICKED/REJECTED/ACCEPTED)
      the level engine records — and it has been in retention_purge's NEVER_PURGE
      since OTV4TEST r3, which by check_purge_pushed C6's own reasoning means the
      box held the ONLY copy: a recomputation cannot rebuild a biography. Red at C6
      since r3; BACKLOG PRE.3 had handed it to mainline. Operator, 2026-09-24:
      *"Include. When our branch becomes the successor (otv5) our architecture
      will inherit the 15 symbols & the warehouse."* Keyed on
      (symbol, level_id, bar_ts, event) and an ordinary rowid table, so it takes
      the same CDC-by-rowid path as level_ledger with no other change.
      ⚠️ INERT ON QQQ-TEST: s3-push.service is MASKED here (BOX.1, WA 38.3) because
      the mainline QQQ box owns that prefix and holds the corpus. This lands for
      the fleet this branch will inherit.
v4.6  2026-09-05  r270 / ASK.1 — `character_axis_sample` JOINS
      `DERIVED_SERIES_TABLES`. Operator ruled: push it. Append-only and keyed
      `(symbol, ts_epoch)`, so it takes the HIGH-WATER path, not CDC.
      🔑 IT IS THE ONLY SURVIVING OUTPUT OF THE CHARACTER ENGINE: r85 set
      BANDS_SET=False, `character_ledger` records no transitions and pushed 0
      boxes in the 2026-09-05 census, and `character_engine`'s own comment says
      "the sample IS the deliverable right now — one session of real efficiency
      values is what the bands get derived from." Holding the bands back was
      the reason for collecting it; leaving it on the box meant the corpus the
      bands are derived FROM had no durable home.
      ⚠️ SHIPPED WITH ITS PURGE ENTRY AND ITS COVERAGE ROW, not before them.
v4.5  2026-08-29  r191 — THE THREE DERIVED SERIES ARE WAREHOUSED (backlog
      S3.1). `fork_series`, `indicator_series` and `surface_series` live in
      derived_store.db and had NO PUSH STAGE, while retention_purge deletes
      all three at 20 DAYS. Armed since r162, so they have been going out
      the door unwarehoused — the same loss v4.2 fixed for the feed series,
      one store over.
      🔴 WHY check_purge_pushed DID NOT CATCH IT: it imports
      `ARTIFACT_DAYS`, and this purge list was a HARDCODED TUPLE inside
      `purge()`. A policy the invariant cannot import is a policy outside
      the invariant. retention_purge v1.1 makes it `DERIVED_ARTIFACT_DAYS`
      and the checker now covers it by EXECUTION (C9/C10).
      🔑 THEY ARE SERIES, NOT BIOGRAPHIES, SO THEY DO NOT GO THROUGH
      push_derived. Those tables are append-only and keyed on `ts_epoch`, so
      a high-water mark is right and CDC-by-rowid would re-hash the whole
      table every run for nothing. `push_series` is now parameterised over
      its table tuple and ledger namespace; the feed call is unchanged.
      ⚠️ AND IT GETS ITS OWN LEDGER FILE. `push_series` was called ONLY with
      FEED_DB and the CANDLE ledger; pointing a second call at DERIVED_DB
      while sharing that dict would put two stores' high-water marks in one
      file under one namespace — the r82 class exactly (two meanings, one
      shape, one helper). `dseries_ledger.json`, namespace `dseries|`.
      — KEY LAYOUT IS UNCHANGED ON PURPOSE: `raw/<table>/dt=/sym=/`, the
      same shape push_series already writes, so `warehouse_source.load_series`
      reads them with no reader change. The consumer is backlog SNS.3.
v4.4  2026-08-28  r180 — 🔴 HEAL LEDGER DRIFT, HOLD FOR REAL LOSS. Two
      months of nightly conductor holds and self_close refusing to halt
      traced to ONE defect: the ledger counts PUTs, S3 counts keys, the
      dedupe set is per-run, so re-pushed keys inflate the ledger forever
      and the manual --reconcile never ran. --verify now heals a short
      prefix automatically WHEN this drain confirmed failed=0 AND S3 holds
      objects there (prints HEALED per prefix, saves the ledger,
      re-verifies); a prefix S3 knows nothing about, or any drain with
      failed>0, still reads SHORT and still holds the box. Supersedes
      reconcile()'s never-automatic refusal BY OPERATOR RULING 2026-08-28,
      with the loss alarm kept where loss is possible. Fixes the conductor
      holds AND self_close's halt in one place — both consume this verdict.
v4.3  2026-08-23  R-PROJECT PART 2: THE DERIVED LIFECYCLE TABLES WAREHOUSE.
      retention_purge marks them NEVER_PURGE because "a recomputation cannot
      rebuild a biography" — but nothing pushed them either, so the only copy
      of every biography lived on a box that gets rebuilt, and control (where
      the operator ruled all reporting runs) could not read fire_snapshot or
      plan_ledger at all. push_derived: uniform CDC by sqlite rowid — every
      row hashed, CHANGED rows batched into one object per table per run
      under raw/derived_<table>/, own ledger file (derived_ledger.json) so
      its {rid: sha} shape can never share a dict with another meaning (the
      r82 class). Reader dedupes latest-per-rid by pushed_at.
v4.2  2026-08-23  R-PROJECT: THE SERIES TABLES ARE NOW PUSHED. retention_purge
      v1.0 calls its 3 days on greeks/quotes/prints/etc "a RE-PUSH window" —
      but no push stage existed for any of the seven series tables, so the
      moment OT_RETENTION_APPLY=1 lands, the manifold's series data would be
      deleted having NEVER been warehoused: "pruned before you knew you
      needed it", the exact loss the manifold was built to end. Found while
      building tests/exit_replay.py, whose premium paths read quote_series on
      control. push_series batches each table's rows since a per-table
      high-water mark into ONE object per run (push_candles' pattern — a
      per-row object at ~250 chain symbols × 15s would be tens of thousands
      of PUTs/hour). Guarded by tests/check_purge_pushed.py, born red at r84.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Pushes collected data to S3 and verifies what landed.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

#!/usr/bin/env python3
# options_trader_v3/warehouse/s3_push.py — v1.9
# WH.6: THE COUNTER COUNTED PUTS, NOT KEYS - AND THE LEDGER
#         PERSISTS. Push the same key twice and n reads 2 while S3 holds 1,
#         FOREVER; a prefix re-pushed once is short for good and the gap only
#         grows. That produced two days of "warehouse NOT confirmed - data
#         stranded on box" alarms.
#         MEASURED 08-18: ten prefixes each short by exactly ONE (1561/1560,
#         1147/1146, 1260/1259, 2280/2279, 2359/2358, 1961/1960, 1197/1196,
#         1263/1262, 2046/2045). Listed the bucket directly: shadow/dt=2026-07-24
#         /sym=META held 1560 and trades/dt=2026-08-17/sym=GS held 33 - exactly
#         what verify's own LIST said. NOTHING WAS EVER MISSING.
#         This file's own 07-27 header called it: "wrong counters make the verify
#         line lie in both directions." There was no evidence until WH.5 stopped
#         truncating the diagnosis at the log boundary.
#         FIX: _confirm dedupes by key within the run; `--reconcile` resets the
#         counters to the live S3 truth for the already-poisoned ledger.
#         RECONCILE IS EXPLICIT, NEVER AUTOMATIC - self-healing on every verify
#         would also silently erase a GENUINE loss. A verification that repairs
#         itself is not a verification.
#         And the SHORT report now names which signature it sees: a small,
#         consistent shortfall across many prefixes is counter drift; a varying
#         one is possible real loss.
"""
"""
Box-side warehouse pusher — ships locally-written archives to S3.

CHANGELOG
    v1.8 — 2026-08-16 — ORB REMOVED. It was ONE stage covering both files, so
           eleven stages become TEN — I first wrote "nine", which was a
           miscount of my own change. `raw/orb_state` had captured ZERO objects in thirty days and
           `raw/orb_range` 81, and nothing consumed either. The operator asked
           the right question — "do we even need it? the orb state could be
           derived by the first 5-minute candle of the RTH" — and the answer is
           that ALL of it is already available:
             * the RANGE recomputes from candles, warehoused at 1m and 5m;
             * the ATTEMPTS are logged individually in the signal journal, with
               price and timestamp — `tests/orb_conversion.py` already derives
               break-attempts from `retest_check` events keyed on
               (symbol, date, direction, attempt) and never opens orb_state.json;
             * the state machine is the only unique part and nothing has ever
               asked for it.
           I had argued the attempt counter was not derivable. That was wrong —
           the attempt number rides on every journal event. **A stream nobody
           consumes that captured nothing is not a capture bug to fix; it is a
           stream to stop collecting.** The 81 existing orb_range objects stay
           in raw/ (which never deletes) and simply stop growing.
           warehouse. FOUND WHILE BUILDING THE READER, NOT BY LOOKING: the
           control-side bundle `fleet_trades_<date>.json` has a
           those two tables inside trades.db — and NOTHING WAS PUSHING THEM. WH.2
           scoped itself to the `trades` table and said the other two would
           follow; WH.3 covered six OTHER streams and they were never picked up.
           A reader built on top would have reproduced two permanently empty
           sections and the WH.11 diff would have shown a gap forever, blamed on
           the reader rather than on the missing push.
           Both are append-only (unlike `trades`, which mutates), so they use the
           same per-row content hash with no CDC semantics needed.
    v1.6 — 2026-08-16 — WH.14: the LIQUIDITY LEDGER joins the warehouse, and
           `<SYM>_EXT` is documented as already handled. LIQ.4 wired
           `data/liquidity_ledger/<date>/<SYMBOL>.json` on 08-15 — the level
           book the mapper builds from — and nothing was pushing it. Whole-file,
           like OHLC: the ledger is rewritten on EVERY closed bar, but this
           timer samples it every 5 minutes, so the object count lands near the
           chain archive's rather than near 390/box/day. Each distinct sampled
           state is its own object, so the intraday EVOLUTION of the level book
           survives instead of only its closing shape.
           FEED.2's extended-hours tape needs NO change here: it lands in
           feed_store as its own store symbol `<SYM>_EXT`, and push_candles
           already does SELECT DISTINCT symbol, so it partitions as
           `sym=<SYM>_EXT` automatically.
    v1.5 — 2026-08-13 — WH.6: SINGLE INSTANCE, AND POLITE. Two pushers could run
           at once — the 5-minute timer plus the EOD conductor's SSH `--verify`,
           which drains before it reports. Both loaded the same ledgers and both
           flushed: last write won, progress was lost and redone, and the
           per-prefix counters could end up wrong — which would make `--verify`
           report OK or SHORT INCORRECTLY. No duplicate objects (content-hash
           keys) and no data loss, but the verify signal is the whole point of
           the EOD gate, so an untrustworthy one is worse than none.
           (a) flock on every invocation path. A normal timer run that finds the
               lock held exits 0 silently — the run already in flight is doing
               the work.
           (b) `--verify` waits up to OT_S3_LOCK_WAIT seconds for the lock. If it
               cannot get it, it SKIPS the drain and verifies anyway, reporting
               `drained=no` so control can tell "nothing left to push" apart from
               "someone else is still pushing".
    v1.4 — 2026-08-13 — WH.5: STREAM ORDER. The first full fleet count exposed
           an ordering fault of mine: the streams ran chains -> trades ->
           journal -> shadow -> ohlc -> eod -> orb -> candles, so the 110,639
           object signal-journal backlog consumed the entire run and everything
           BEHIND it starved. ohlc sat at 108 against an expected ~783, eod at
           8 against ~58, candles at 20 — not corruption, just never reached.
           A timeout must truncate the TAIL, not the head, so the order is now
           smallest-and-most-perishable first and the bulk streams last.
           TimeoutStartSec also went 240s -> 1800s: 240 was a guess made before
           any volume was known. systemd skips a timer trigger while the
           oneshot is still running, so a long drain is safe.
    v1.3 — 2026-08-13 — WH.4: survivable drains and box-side verification.
           (a) INCREMENTAL LEDGER SAVES. v1.0-v1.2 saved the ledger ONCE at the
               end of main(). The unit sets TimeoutStartSec=240, so a backlog
               drain longer than four minutes was killed with NO progress
               recorded — every object re-PUT next run, forever. Content-hashed
               keys meant no duplicates appeared, so it would have livelocked
               silently rather than failing loudly. Ledgers now flush every
               FLUSH_EVERY confirmations.
           (b) PER-PREFIX COUNTERS. Each confirmation increments an O(1)
               {n, bytes} counter for its dt=/sym= prefix. No per-object
               bookkeeping.
           (c) `--verify`. Drains, then reconciles those counters against what
               S3 actually holds — per prefix, on COUNT and BYTES, both of
               which list_objects_v2 returns for free. Prints ONE
               machine-readable line and always exits 0. This is what the EOD
               conductor gates a box's shutdown on, so the box answers for
               itself instead of control modelling the box's local state.
    v1.2 — 2026-08-13 — WH.3: the remaining six streams. signal_journal and
           shadow (append-only jsonl, same offset ledger as chains, with
           `ruleset` and `event` lifted into the envelope); OHLC day-CSVs
           (whole-file objects, not one per candle); feed_store candles (all
           intervals, high-water mark per symbol+interval, VIX only from the
           SPX box); the EOD json pair; and ORB state captured on
           state==ESTABLISHED rather than on a clock time.
    v1.1 — 2026-08-13 — WH.2: trades. Plus a LATENT DUPLICATE BUG FIXED in the
           v1.0 key derivation. v1.0 hashed the whole ENVELOPE, which contains
           `pushed_at_utc` — so the same source line pushed at two different
           seconds produced two different keys, i.e. a duplicate. The v1.0 test
           that claimed to prove idempotency passed only because both pushes
           happened inside the same second. The hash is now taken over the
           RECORD alone, which is genuinely stable, and the test now forces a
           clock change between pushes. The 16,782 chain objects already in the
           bucket carry v1.0-basis keys; their ledgers prevent re-push, so they
           are unaffected in place.
    v1.0 — 2026-08-12 — initial release. Chain snapshots only; other streams
           (trades.db, signal journal, feed_store) land in later versions
           behind the same ledger + verify machinery.

WHY THIS EXISTS
    Option chains are NOT reconstructible after the session. A quote for a
    strike nobody selected is gone permanently at 16:00 — no vendor, no
    backfill, no replay recovers it. Today the only copy lives on the box that
    wrote it, and that box is STOPPED after the session. Because the morning
    selector picks movers, a box that traded today may not wake for weeks; its
    archive is unreachable that whole time and lost outright if the box is
    rebuilt. This module moves each snapshot to durable storage within one
    cadence interval of it being written.

DESIGN RULES
  1. NEVER raises. main() returns 0 unconditionally. A full disk, an expired
     credential, a truncated file, a network partition — all degrade to
     "pushed nothing this run", never to a traceback and never to a non-zero
     exit that would make a fleet fan-out discard the output of every box.
  2. NOT IN THE TRADING LOOP. Runs as its own systemd timer under system
     python. The bot's behaviour is byte-identical whether this module exists
     or not, and installing it requires no bot restart.
  3. STDLIB + boto3 ONLY. System python has boto3 1.40.72 fleet-wide; the bot
     venv does not, and this module must never need it. No pandas, no repo
     imports — it reads files, it does not import the writer.
  4. SILENT WHEN IDLE. On any given day ~14 boxes never trade and therefore
     have no chains at all. "Nothing to push" is the NORMAL state and prints
     nothing. An idle box that looks like a failure is how a real failure gets
     ignored (WORKING_AGREEMENT §17).
  5. CONFIRMED MEANS READ-BACK-AND-COMPARE. A 200 from PutObject proves bytes
     were accepted, not that the object is retrievable, parseable or equal to
     what we sent. Every object is re-read and byte-compared before the ledger
     records it. The ledger is what a future scrub will gate deletion on, so a
     false confirmation there is a data-loss bug, not a reporting bug.

KEY CONVENTION
    raw/chain_snapshots/dt=<YYYY-MM-DD>/sym=<SYM>/<epoch_ms>-<sha256[:16]>.json

    Hive-style dt=/sym= so Athena or Glue can discover partitions without a
    custom parser. The suffix is a CONTENT HASH rather than a uuid4: a uuid
    makes every retry write a duplicate object, while a content hash makes the
    push idempotent — a re-run after a crash mid-verify overwrites the same
    key with identical bytes instead of creating a second copy of one snapshot.
    Collision safety is unchanged (concurrent boxes write different symbols,
    and two identical snapshots ARE the same snapshot).

LEDGER
    ~/.vertigo_warehouse/chain_ledger.json, one entry per source file:
        {"<path>": {"n": <lines confirmed>, "last_sha": ..., "last_key": ...,
                    "confirmed_utc": ...}}
    Source files are append-only, so a confirmed line count is a valid resume
    point. Written atomically (tmp + os.replace) so a kill mid-write cannot
    leave a truncated ledger — which would silently re-push or, worse, look
    like more was confirmed than actually was.

    The ledger lives OUTSIDE the repo. Nothing this module writes lands in the
    working tree, so there is no scaffolding to remember to clean up.
"""

import gzip
import hashlib
import json
import os
import fcntl
import socket
import sqlite3
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SCHEMA_VERSION = 1
DATATYPE = "chain_snapshot"

BUCKET = os.environ.get("OT_S3_BUCKET", "vertigo-warehouse-tx9ai")
REGION = os.environ.get("OT_S3_REGION", "us-east-2")
PREFIX = os.environ.get("OT_S3_PREFIX", "raw")
# Kill switch, house style: one env var per change, default ON.
ENABLED = os.environ.get("OT_S3_PUSH", "1") != "0"
# CD.1 — a file, not an env var, so the conductor's ssh --verify and self_close read it too
PAUSE_FLAG = os.environ.get("OT_PUSH_PAUSE_FLAG", os.path.join(os.path.expanduser("~"), ".optbot", "push_paused"))

_HOME = os.path.expanduser("~")
SRC_ROOT = os.environ.get(
    "OT_CHAIN_ROOT", os.path.join(_HOME, "options-trader", "data", "chain_snapshots")
)
STATE_DIR = os.environ.get("OT_WAREHOUSE_STATE", os.path.join(_HOME, ".vertigo_warehouse"))
LEDGER_PATH = os.path.join(STATE_DIR, "chain_ledger.json")

HOST = socket.gethostname()


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canon(rec) -> bytes:
    """Canonical bytes for the SOURCE RECORD ONLY — the basis for every key.

    Deliberately excludes the envelope. The envelope carries `pushed_at_utc`,
    which changes every run, so hashing it made the key a function of WHEN the
    push happened rather than WHAT was pushed: the same line pushed twice in
    different seconds landed as two objects. Keys must be a pure function of
    content or idempotency is a coincidence.
    """
    return json.dumps(rec, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")


def _et_day(iso_ts: str) -> str:
    """Trading day (ET) from any ISO timestamp carrying an offset.

    `dt=` MUST mean the same thing in every stream or joins silently return
    nothing. Chain snapshots, the journal and OHLC all bucket by ET date, so
    trades — whose timestamps are UTC — are converted rather than truncated.
    """
    try:
        dt = datetime.fromisoformat(str(iso_ts))
        if dt.tzinfo is None:
            return str(iso_ts)[:10]
        return dt.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        return str(iso_ts)[:10]


def _epoch_ms(rec: dict, fallback_ms: int) -> int:
    """Snapshot time in epoch ms, from the record's own ET timestamp."""
    try:
        dt = datetime.fromisoformat(str(rec.get("ts_et", "")))
        if dt.tzinfo is None:
            return fallback_ms
        return int(dt.timestamp() * 1000)
    except Exception:
        return fallback_ms


def read_lines(path: str):
    """All COMPLETE lines from a multi-member gzip file.

    The bot appends to this file while we read it, so the final member may be
    partially written. gzip raises at that point; every line already yielded
    is intact, so we keep those and stop. The partial line is picked up on the
    next run once the writer has finished it.
    """
    out = []
    try:
        with gzip.open(path, "rb") as f:
            for raw in f:
                out.append(raw)
    except Exception:
        pass
    if out and not out[-1].endswith(b"\n"):
        out.pop()
    return out


def load_ledger(path: str = LEDGER_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = data if isinstance(data, dict) else {}
    except Exception:
        data = {}
    _OPEN[path] = data          # register for mid-drain flushing
    return data


def flush_all():
    """Persist every open ledger. Called mid-drain, not just at the end.

    The whole point: a drain killed at TimeoutStartSec must leave PROGRESS
    behind. Saving only at the end meant a long backlog could never finish and
    would silently repeat itself forever.
    """
    ok = True
    for path, data in _OPEN.items():
        if not save_ledger(data, path):
            ok = False
    return ok


def acquire_lock(wait_s: int = 0):
    """Exclusive flock, or None. Guards EVERY invocation path.

    The timer and the EOD conductor's `--verify` are different entrypoints to
    the same work, and nothing else was stopping them overlapping. Two
    processes sharing one ledger is not a duplicate-object problem — the keys
    are content-hashed — it is a LOST PROGRESS and WRONG COUNTERS problem, and
    wrong counters make the verify line lie in both directions.
    """
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        fh = open(LOCK_PATH, "w")
    except Exception:
        return None
    deadline = time.time() + max(0, wait_s)
    while True:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fh
        except OSError:
            if time.time() >= deadline:
                try:
                    fh.close()
                except Exception:
                    pass
                return None
            time.sleep(1)


_SEEN_KEYS = set()          # WH.6: keys confirmed in THIS process


def _confirm(key: str, body: bytes, counters: dict):
    """Record one confirmed object: bump its prefix counters, flush if due.

    ⚠️ WH.6 (2026-08-18) — THIS COUNTED PUTS, NOT KEYS, AND THE LEDGER PERSISTS.
    Push the same key twice and `n` reached 2 while S3 held 1 — **permanently**,
    because the ledger is saved to disk and the gap can only ever grow. A prefix
    re-pushed once was short forever.
    That is what produced two days of *"warehouse NOT confirmed — data stranded
    on box"* alarms. **Verified 2026-08-18: S3 held 1560 objects for
    `raw/shadow/dt=2026-07-24/sym=META/` and the LIST agreed — the counter said
    1561. NOTHING WAS EVER MISSING.** Ten prefixes, ten off-by-ones: the
    signature of a systematic count error, not of data loss, which scatters.
    This module's own header called the hazard on 2026-07-27: *"wrong counters
    make the verify line lie in both directions."* It did.

    ⚠️ THE SET IS PER-PROCESS, NOT PERSISTED. Bounding it by run size keeps it
    small (a drain pushes hundreds, not the 40k+ objects in history), and the
    cross-run case is handled by `--reconcile` instead. A persisted key set
    would be a second ledger with its own drift.
    """
    prefix = key.rsplit("/", 1)[0] + "/"
    c = counters.setdefault(prefix, {"n": 0, "bytes": 0})
    if key in _SEEN_KEYS:
        return                  # same key, same content-hash: S3 has ONE object
    _SEEN_KEYS.add(key)
    c["n"] += 1
    c["bytes"] += len(body)
    _SINCE_FLUSH[0] += 1
    if _SINCE_FLUSH[0] >= FLUSH_EVERY:
        _SINCE_FLUSH[0] = 0
        flush_all()


def save_ledger(ledger: dict, path: str = LEDGER_PATH) -> bool:
    """Atomic write. A torn ledger is worse than no ledger: it can claim more
    lines confirmed than actually landed, and a future scrub keys on it."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ledger, f, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def envelope(rec: dict, sym: str, day: str, line_idx: int, src_file: str) -> bytes:
    """Wrap the raw snapshot with provenance and a schema version.

    The version is stamped per object, never inferred from the key, because
    journal shapes have already changed several times this month and a
    warehouse that cannot tell v1 rows from v3 rows pools incompatible data.
    """
    env = {
        "schema_version": SCHEMA_VERSION,
        "datatype": DATATYPE,
        "symbol": sym,
        "dt": day,
        "src_host": HOST,
        "src_file": src_file,
        "src_line": line_idx,
        "pushed_at_utc": _now_utc(),
        "record": rec,
    }
    return json.dumps(env, separators=(",", ":"), default=str).encode("utf-8")


def put_and_verify(s3, bucket: str, key: str, body: bytes, counters=None) -> bool:
    """PUT then GET then byte-compare. Anything short of equality is False.

    On success the object is recorded against its dt=/sym= prefix counters,
    which is what `--verify` later reconciles against S3.
    """
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=body)
    except Exception:
        return False
    try:
        got = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception:
        return False
    if got != body:
        return False
    if counters is not None:
        _confirm(key, body, counters)
    return True


def push_file(s3, bucket, path, day, sym, ledger, counters=None):
    """Push every unconfirmed line of one source file. Returns (pushed, failed)."""
    lines = read_lines(path)
    entry = ledger.get(path) or {}
    start = int(entry.get("n", 0) or 0)
    if start > len(lines):
        # File shrank — a rotation, a rebuild, or a different file at the same
        # path. Resuming from a stale offset would skip real data, so restart.
        start = 0

    pushed = 0
    failed = 0
    mtime_ms = 0
    try:
        mtime_ms = int(os.path.getmtime(path) * 1000)
    except Exception:
        pass

    for idx in range(start, len(lines)):
        raw = lines[idx]
        try:
            rec = json.loads(raw)
        except Exception:
            # Not valid JSON yet. Stop here rather than skipping: skipping
            # would advance the offset past a line that never got pushed.
            break
        sha = _sha256(_canon(rec))       # content only — never the envelope
        body = envelope(rec, sym, day, idx, os.path.basename(path))
        key = "{}/{}s/dt={}/sym={}/{}-{}.json".format(
            PREFIX, DATATYPE, day, sym, _epoch_ms(rec, mtime_ms), sha[:16]
        )
        if not put_and_verify(s3, bucket, key, body, counters):
            failed += 1
            break  # stop this file; next run retries from the same offset
        ledger[path] = {
            "n": idx + 1,
            "last_sha": sha,
            "last_key": key,
            "confirmed_utc": _now_utc(),
        }
        pushed += 1
    return pushed, failed


def discover(root: str = SRC_ROOT, suffix: str = ".jsonl.gz"):
    """(path, day, symbol) for every <date>/<SYM><suffix> file under root.

    All four date-partitioned trees on a box share this shape — chain
    snapshots, the signal journal, shadow and OHLC — so one walker serves them
    all rather than four near-identical copies drifting apart.
    """
    found = []
    try:
        for day in sorted(os.listdir(root)):
            day_dir = os.path.join(root, day)
            if not os.path.isdir(day_dir):
                continue
            for name in sorted(os.listdir(day_dir)):
                if not name.endswith(suffix):
                    continue
                found.append((os.path.join(day_dir, name), day, name[: -len(suffix)]))
    except Exception:
        pass
    return found


# ─────────────────────────────────────────────────────────────────────────────
# TRADES  (WH.2)
# ─────────────────────────────────────────────────────────────────────────────
TRADES_DB = os.environ.get(
    "OT_TRADES_DB", os.path.join(_HOME, "options-trader", "trades.db"))
TRADES_LEDGER = os.path.join(STATE_DIR, "trades_ledger.json")
# r57 (TCS.LOG1) — the shadow store, beside trades.db unless named (execution/shadow_book.shadow_db_path reads the same).
SHADOW_TRADES_DB = os.environ.get("OT_SHADOW_TRADES_DB") or os.path.join(
    os.path.dirname(os.path.abspath(TRADES_DB)), "shadow_trades.db")
SHADOW_TRADES_LEDGER = os.path.join(STATE_DIR, "shadow_trades_ledger.json")


def trade_envelope(rec: dict, sym: str, day: str, datatype: str = "trade",
                   src_file: str = "trades.db") -> bytes:
    env = {
        "schema_version": SCHEMA_VERSION,
        "datatype": datatype,
        "symbol": sym,
        "dt": day,
        "trade_id": rec.get("trade_id"),
        "status": rec.get("status"),
        "src_host": HOST,
        "src_file": src_file,
        "pushed_at_utc": _now_utc(),
        "record": rec,
    }
    return json.dumps(env, separators=(",", ":"), default=str).encode("utf-8")


def push_trades(s3, bucket: str, db_path: str, ledger: dict, counters=None,
                ns: str = "trades", datatype: str = "trade", src_file: str = "trades.db"):
    """Push every trade row whose CONTENT has changed since last push.

    Trade rows MUTATE — written at entry, rewritten at exit. So this is not
    append-only like the chain archive, and a line-offset resume would be
    wrong. Instead the ledger holds one content hash per trade_id: an
    unchanged row costs a hash and nothing else, and each distinct STATE of a
    row lands as its own immutable object. That is change-data-capture for
    free, and it preserves more than `fleet_trades_<date>.json` does today —
    that file only ever sees the end state.

    SELECT * deliberately: the schema is 84 columns and has grown before
    (consolidate_trades.py's docstring still says ~55). Enumerating columns
    here would silently drop any future ALTER TABLE ADD COLUMN.
    """
    pushed = failed = 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM trades").fetchall()
        con.close()
    except Exception:
        return 0, 0          # no db, locked, or no table — nothing to push

    for row in rows:
        rec = dict(row)
        tid = str(rec.get("trade_id", ""))
        sha = _sha256(_canon(rec))
        if ledger.get(tid) == sha:
            continue                      # unchanged since last push
        sym = str(rec.get("symbol") or "UNKNOWN")
        ts = rec.get("entry_time") or ""
        day = _et_day(ts)
        try:
            ems = int(datetime.fromisoformat(str(ts)).timestamp() * 1000)
        except Exception:
            ems = 0
        key = "%s/%s/dt=%s/sym=%s/%d-%s.json" % (PREFIX, ns, day, sym, ems, sha[:16])
        if not put_and_verify(s3, bucket, key, trade_envelope(rec, sym, day, datatype, src_file), counters):
            failed += 1
            break
        ledger[tid] = sha
        pushed += 1
    return pushed, failed


# ─────────────────────────────────────────────────────────────────────────────
# WH.3 — the remaining streams
# ─────────────────────────────────────────────────────────────────────────────
_OT = os.path.join(_HOME, "options-trader")
JOURNAL_ROOT = os.path.join(_OT, "data", "signal_journal")
SHADOW_ROOT  = os.path.join(_OT, "data", "shadow")
OHLC_ROOT    = os.path.join(_OT, "data", "OHLC")
LIQ_ROOT     = os.path.join(_OT, "data", "liquidity_ledger")
FEED_DB      = os.path.join(_OT, "data", "feed_store.db")
EOD_DIR      = os.path.join(_HOME, "eod")

LOCK_PATH     = os.path.join(STATE_DIR, "s3_push.lock")
LOCK_WAIT     = int(os.environ.get("OT_S3_LOCK_WAIT", "120"))
COUNTERS_PATH = os.path.join(STATE_DIR, "prefix_counters.json")
FLUSH_EVERY   = int(os.environ.get("OT_S3_FLUSH_EVERY", "200"))

# Every ledger this process has opened, so a mid-drain flush can persist all of
# them. Registered by load_ledger; flushed by _confirm.
_OPEN = {}
_SINCE_FLUSH = [0]

MISC_LEDGER    = os.path.join(STATE_DIR, "misc_ledger.json")
CANDLE_LEDGER  = os.path.join(STATE_DIR, "candle_ledger.json")
DERIVED_LEDGER = os.path.join(STATE_DIR, "derived_ledger.json")   # r20: legacy; converted once, then removed
DERIVED_LEDGER_DB = os.path.join(STATE_DIR, "derived_ledger.db")  # r20 PUSH.1: the CDC ledger
DERIVED_SCAN_ROWS = int(os.environ.get("OT_S3_DERIVED_SCAN", "5000"))
DERIVED_BATCH_ROWS = int(os.environ.get("OT_S3_DERIVED_BATCH", "10000"))
# v4.5 — the derived SERIES high-water marks. Its own file: derived_ledger.json
# holds {table: {rid: sha}} and candle_ledger.json holds {SYM|interval: hwm}.
# A flat float map in either of those is two meanings in one dict, which is
# the r82 failure this project has already paid for once.
DSERIES_LEDGER = os.path.join(STATE_DIR, "dseries_ledger.json")
DERIVED_DB     = os.path.join(_OT, "data", "derived_store.db")


def _eod_day(eod_dir):
    """Trading day for the EOD pair, taken from pnl_today.json's own date_et.

    The filenames carry no date and are overwritten each SESSION, so a box idle
    since July still holds July's file. Bucketing by today would file it under
    the wrong day; the file states its own.
    """
    try:
        with open(os.path.join(eod_dir, "pnl_today.json"), encoding="utf-8") as fh:
            d = json.load(fh).get("date_et")
        if d:
            return str(d)[:10]
    except Exception:
        pass
    return datetime.now(tz=timezone.utc).astimezone(
        ZoneInfo("America/New_York")).date().isoformat()


def own_symbol():
    """This box's instrument, read off disk.

    `data/OHLC/<date>/<SYM>.csv` is written for every box every session, so the
    basename IS the instrument. Preferred over OT_INSTRUMENT because this
    process does not inherit the bot unit's environment, and over an EC2 tag
    lookup because the box role deliberately carries no ec2:Describe.
    """
    # r139 — the explicit instrument wins (data_capture.sh's drop-in sets it);
    # the newest OHLC file can still be a PREVIOUS instrument's after a change.
    _env = os.environ.get("OT_INSTRUMENT", "").strip()
    if _env:
        return _env
    # CD.1 — the bot unit's instrument before any OHLC file (a switch's first day still has the old symbol's file)
    try:
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from utils.instrument import box_instrument, UNSET
        _unit = box_instrument()
        if _unit and _unit != UNSET:
            return _unit
    except Exception:
        pass
    try:
        days = sorted(d for d in os.listdir(OHLC_ROOT)
                      if os.path.isdir(os.path.join(OHLC_ROOT, d)))
        for day in reversed(days):
            for n in os.listdir(os.path.join(OHLC_ROOT, day)):
                if n.endswith(".csv"):
                    return n[:-4]
    except Exception:
        pass
    return os.environ.get("OT_INSTRUMENT", "")


def _wrap(datatype, rec, sym, day, extra=None):
    env = {
        "schema_version": SCHEMA_VERSION,
        "datatype": datatype,
        "symbol": sym,
        "dt": day,
        "src_host": HOST,
        "pushed_at_utc": _now_utc(),
        "record": rec,
    }
    if extra:
        env.update(extra)
    return json.dumps(env, separators=(",", ":"), default=str).encode("utf-8")


def push_table(s3, bucket, db_path, table, ts_col, datatype, ledger, me, counters=None):
    """Push every row of an append-only table in trades.db, one object per row.

    do not mutate, so there is no change-data-capture to reason about: a row's
    content hash is stable for its lifetime and the ledger simply records which
    hashes have landed.

    `SELECT *` for the same reason as trades — a future ALTER TABLE ADD COLUMN
    is carried automatically instead of silently dropped.
    """
    pushed = failed = 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute("SELECT * FROM %s" % table)]
        con.close()
    except Exception:
        return 0, 0          # table absent on an older schema — not an error

    seen = ledger.setdefault(table, {})
    for rec in rows:
        sha = _sha256(_canon(rec))
        rid = str(rec.get("id") or sha[:16])
        if seen.get(rid) == sha:
            continue
        ts = rec.get(ts_col) or ""
        day = _et_day(ts)
        try:
            ems = int(datetime.fromisoformat(str(ts)).timestamp() * 1000)
        except Exception:
            ems = 0
        sym = str(rec.get("symbol") or me or "UNKNOWN")
        key = "%s/%s/dt=%s/sym=%s/%d-%s.json" % (PREFIX, datatype, day, sym, ems, sha[:16])
        body = _wrap(datatype, rec, sym, day, {"row_id": rec.get("id")})
        if not put_and_verify(s3, bucket, key, body, counters):
            failed += 1
            break
        seen[rid] = sha
        pushed += 1
    return pushed, failed


def push_jsonl_tree(s3, bucket, root, datatype, ledger, counters=None):
    """signal_journal and shadow: <date>/<SYM>.jsonl, append-only, plain text.

    Same offset-resume contract as the chain archive. `ruleset` and `event` are
    lifted into the envelope: ruleset fingerprints the DEPLOYED LOGIC that
    produced the event, and pooling journal events across a deploy boundary
    without grouping by it blends incompatible decision-making.
    """
    pushed = failed = 0
    for path, day, sym in discover(root, ".jsonl"):
        entry = ledger.get(path) or {}
        start = int(entry.get("n", 0) or 0)
        try:
            with open(path, "rb") as fh:
                lines = fh.readlines()
        except Exception:
            continue
        if lines and not lines[-1].endswith(b"\n"):
            lines.pop()                      # writer mid-line
        if start > len(lines):
            start = 0
        for idx in range(start, len(lines)):
            try:
                rec = json.loads(lines[idx])
            except Exception:
                break
            sha = _sha256(_canon(rec))
            extra = {"src_line": idx}
            for f in ("ruleset", "event"):
                if isinstance(rec, dict) and rec.get(f) is not None:
                    extra[f] = rec[f]
            body = _wrap(datatype, rec, sym, day, extra)
            ems = _epoch_ms(rec, 0) if isinstance(rec, dict) else 0
            key = "%s/%s/dt=%s/sym=%s/%d-%s.json" % (PREFIX, datatype, day, sym, ems, sha[:16])
            if not put_and_verify(s3, bucket, key, body, counters):
                failed += 1
                break
            ledger[path] = {"n": idx + 1, "last_sha": sha, "confirmed_utc": _now_utc()}
            pushed += 1
    return pushed, failed


def push_whole_files(s3, bucket, items, datatype, ledger, counters=None):
    """One object per FILE, not per row. For OHLC day-CSVs and the EOD pair.

    A day-CSV holds ~390 candles; one object per candle would be 390x the
    request count for data that is only ever read as a day. The file is pushed
    as a unit and re-pushed only when its CONTENT hash changes, so a day still
    filling produces one object per distinct state and a finished day settles.
    """
    pushed = failed = 0
    for path, day, sym in items:
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except Exception:
            continue
        if not raw:
            continue
        sha = _sha256(raw)
        if ledger.get(path) == sha:
            continue
        body = _wrap(datatype, raw.decode("utf-8", "replace"), sym, day,
                     {"src_file": os.path.basename(path), "content_sha256": sha})
        key = "%s/%s/dt=%s/sym=%s/%s-%s.json" % (PREFIX, datatype, day, sym,
                                                 os.path.basename(path), sha[:16])
        if not put_and_verify(s3, bucket, key, body, counters):
            failed += 1
            continue
        ledger[path] = sha
        pushed += 1
    return pushed, failed


# 🔴 CNDL.1 — A BAR IS PUSHED ONLY ONCE IT HAS CLOSED. The high-water mark
# below advances to the newest bar sent, and the next run selects only bars
# AFTER it — so the bar that was still forming when it was sent never had its
# final version pushed. Each run lands ~30 s after a bar opens, so EVERY stored
# 5m/15m/1h bar was its first ~30 s (QQQ 2026-10-01: 78 of 78 5m bars disagree
# with their own 1m bars; range understated $0.92 on average) and 1 in ~5 1m
# bars too. Found by OTV4TEST's SPX-TEST agent (MSG-1004-03).
_INTERVAL_MS = {"1m": 60_000, "2m": 120_000, "3m": 180_000, "5m": 300_000,
                "10m": 600_000, "15m": 900_000, "30m": 1_800_000,
                "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000,
                "1d": 86_400_000}
_CLOSE_GRACE_MS = 5_000      # the feed writes the final print a moment after the edge


def _closed_bars(rows, iv, now_ms):
    """Only the bars whose interval has ENDED (ts + length + grace <= now).
    An interval this table does not know is passed through unchanged (and the
    caller's old behaviour stands) rather than silently withheld forever."""
    span = _INTERVAL_MS.get(str(iv))
    if span is None:
        return list(rows)
    return [r for r in rows
            if int(r["ts_epoch_ms"]) + span + _CLOSE_GRACE_MS <= now_ms]


def push_candles(s3, bucket, db_path, ledger, me, counters=None):
    """feed_store candles — ALL intervals, high-water mark per symbol+interval.

    The store is a rolling window (pruned), not an archive, so re-reading it
    every run would re-push the same bars. A high-water mark pushes only bars
    newer than the last confirmed one, batched into a single object per
    symbol+interval per run.

    VIX is logged by EVERY box. Operator's decision: SPX owns it, the other 28
    skip it — otherwise the warehouse takes 29 identical copies. Safe because
    SPX trades every day without exception.
    """
    pushed = failed = 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        pairs = [(r["symbol"], r["interval"]) for r in
                 con.execute("SELECT DISTINCT symbol, interval FROM candles")]
    except Exception:
        return 0, 0
    for sym, iv in pairs:
        # r136 (mainline r350) — FAMILY MATCH BY ROOT, so VIX_EXT and any future
        # VIX_W / VIX_9D cannot slip; VIXY does not match (a different product).
        if str(sym).upper().split("_")[0] in ("VIX", "^VIX") and me != "SPX":
            continue                                  # SPX owns the VIX family
        # r139 — only this box's own family (and SPX's VIX): a previous
        # instrument's rows are never pushed into another box's partition.
        _root = str(sym).upper().split("_")[0]
        if me and _root != str(me).upper() and _root not in ("VIX", "^VIX"):
            continue
        lk = "%s|%s" % (sym, iv)
        hwm = int(ledger.get(lk, 0) or 0)
        try:
            rows = [dict(r) for r in con.execute(
                "SELECT * FROM candles WHERE symbol=? AND interval=? AND ts_epoch_ms>?"
                " ORDER BY ts_epoch_ms", (sym, iv, hwm))]
        except Exception:
            continue
        rows = _closed_bars(rows, iv, int(time.time() * 1000))   # CNDL.1
        if not rows:
            continue
        top = int(rows[-1]["ts_epoch_ms"])
        day = datetime.fromtimestamp(top / 1000, tz=timezone.utc).astimezone(
            ZoneInfo("America/New_York")).date().isoformat()
        sha = _sha256(_canon(rows))
        body = _wrap("candles", rows, sym, day,
                     {"interval": iv, "n_bars": len(rows),
                      "ts_from": int(rows[0]["ts_epoch_ms"]), "ts_to": top})
        key = "%s/candles/dt=%s/sym=%s/interval=%s/%d-%s.json" % (
            PREFIX, day, sym, iv, top, sha[:16])
        if put_and_verify(s3, bucket, key, body, counters):
            ledger[lk] = top
            pushed += 1
        else:
            failed += 1
    con.close()
    return pushed, failed




SERIES_TABLES = ("greeks_series", "quote_series", "prints", "last_trade",
                 "session_summary", "theo_series", "underlying_series")

# v4.3 — the lifecycle biographies. Mutating (plans transition, characters
# close, snapshots replace), so CDC by rowid rather than a high-water mark.
# 🔴 r126b — `plan_tick` and `plan_check` added. They are the only record of
# what each plan SAW and what it would have COST; bot.log is bounded by
# rotation and the fit needs weeks. `plan_check` is the higher-volume of the
# two (one row per variable per plan per cycle) — it goes here, never before
# `shadow` in the ordering, per the standing push-order rule.
# v4.5 — the RECOMPUTABLE series in derived_store.db. Append-only and keyed on
# ts_epoch, so they take the high-water path, not the CDC path. Kept in sync
# with retention_purge.DERIVED_ARTIFACT_DAYS by tests/check_purge_pushed.py.
# 🔴 r270 — `character_axis_sample` JOINS THE LIST. Operator ruled 2026-09-05:
# push it. It is APPEND-ONLY and keyed `(symbol, ts_epoch)`, so it takes the
# high-water path with its siblings rather than the CDC path.
# 🔑 IT IS THE ONLY SURVIVING OUTPUT OF THE CHARACTER ENGINE. r85 set
# `BANDS_SET=False`, so `character_ledger` records no transitions and pushes
# 0 boxes — measured in the 2026-09-05 stream census. `character_engine`'s own
# comment states the consequence: **"the sample IS the deliverable right now —
# one session of real efficiency values is what the bands get derived from."**
# Holding the bands back was the whole point of collecting this, and leaving it
# on the box meant the thing the bands are derived FROM lived nowhere durable.
# ⚠️ IT IS STRIDED, NOT PER TICK (`BASELINE_STRIDE_S`), deliberately: a 15s
# cadence would write ~1,560 rows per symbol-day to answer a question a few
# hundred answers just as well. So this is a small stream, not a new SPX chain.
DERIVED_SERIES_TABLES = ("fork_series", "indicator_series", "surface_series",
                         "character_axis_sample")

DERIVED_TABLES = ("fire_snapshot", "strategy_note", "plan_ledger",
                  "plan_tick", "plan_check",
                  "gate_disposition", "character_ledger", "level_ledger",
                  "level_event",              # r128 — NEVER_PURGE since r3, never shipped
                  "exit_counterfactual")


class _DictSeen:
    """The {table: {rid: sha}} dict ledger behind the SQLite one's interface (the gates pass a dict)."""

    def __init__(self, d):
        self.d = d

    def get_many(self, table, rids):
        seen = self.d.get(table, {})
        return {r: seen[r] for r in rids if r in seen}

    def put_many(self, table, items):
        self.d.setdefault(table, {}).update(items)

    def prune_below(self, table, min_rid):
        seen = self.d.get(table)
        if seen:
            for r in [r for r in seen if int(r) < min_rid]:
                del seen[r]

    def commit(self):
        pass

    def close(self):
        pass


class DerivedLedger:
    """r20 PUSH.1 — the CDC ledger on disk, read a chunk at a time. Stores a 16-byte digest per (table, rid):
    the hex sha256 the row is compared by, truncated to 128 bits (a collision would need 2**64 rows)."""

    def __init__(self, path=None, legacy_json=None):
        self.path = path or DERIVED_LEDGER_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.con = sqlite3.connect(self.path, timeout=30)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("CREATE TABLE IF NOT EXISTS seen (tbl TEXT NOT NULL, rid INTEGER NOT NULL, "
                         "sha BLOB NOT NULL, PRIMARY KEY (tbl, rid)) WITHOUT ROWID")
        self.con.commit()
        legacy = DERIVED_LEDGER if legacy_json is None else legacy_json
        if legacy and os.path.exists(legacy):
            self._convert(legacy)

    @staticmethod
    def _d(sha_hex):
        return bytes.fromhex(sha_hex[:32])

    def _convert(self, path):
        """Stream the legacy {table: {rid: sha}} JSON in 1 MB reads (never json.load: the file is what blew the
        memory). It was written with separators (",", ":"), so its tokens are fixed; a file this cannot read is
        kept and named, and the next run tries again."""
        import re
        tok = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)":\{|"(\d+)":"([0-9a-f]{64})"')
        table, n, buf, batch = None, 0, "", []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                while True:
                    chunk = fh.read(1 << 20)
                    buf += chunk
                    end = len(buf) if not chunk else max(0, len(buf) - 200)
                    pos = 0
                    for m in tok.finditer(buf):
                        if m.end() > end:
                            break
                        pos = m.end()
                        if m.group(1):
                            table = m.group(1)
                        elif table:
                            batch.append((table, int(m.group(2)), self._d(m.group(3))))
                            if len(batch) >= 50000:
                                self.con.executemany("INSERT OR REPLACE INTO seen VALUES (?,?,?)", batch)
                                n += len(batch)
                                batch = []
                    buf = buf[pos:]
                    if not chunk:
                        break
            if batch:
                self.con.executemany("INSERT OR REPLACE INTO seen VALUES (?,?,?)", batch)
                n += len(batch)
            self.con.commit()
            os.replace(path, path + ".converted")
            os.remove(path + ".converted")
            print("s3_push: derived ledger converted to SQLite ({} rows)".format(n))
        except Exception as exc:                                # noqa: BLE001
            self.con.rollback()
            print("s3_push: derived ledger conversion FAILED ({}); the JSON is kept".format(
                type(exc).__name__))

    def get_many(self, table, rids):
        out = {}
        for i in range(0, len(rids), 900):
            part = rids[i:i + 900]
            q = "SELECT rid, sha FROM seen WHERE tbl=? AND rid IN (%s)" % ",".join("?" * len(part))
            for rid, sha in self.con.execute(q, [table] + [int(r) for r in part]):
                out[str(rid)] = sha
        return out

    def put_many(self, table, items):
        self.con.executemany("INSERT OR REPLACE INTO seen VALUES (?,?,?)",
                             [(table, int(r), v) for r, v in items.items()])

    def prune_below(self, table, min_rid):
        cur = self.con.execute("DELETE FROM seen WHERE tbl=? AND rid<?", (table, int(min_rid)))
        self.pruned = getattr(self, "pruned", 0) + max(0, cur.rowcount or 0)

    def compact_if_pruned(self, threshold=100000):
        """Give a large prune's pages back to the disk (the first run after the conversion frees ~80%)."""
        if getattr(self, "pruned", 0) >= threshold:
            self.con.commit()
            self.con.execute("VACUUM")
            self.pruned = 0

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()


def _derived_stage(s3, me, counters):
    """The production derived stage: the SQLite ledger, opened and closed around one push_derived."""
    led = DerivedLedger()
    try:
        out = push_derived(s3, BUCKET, DERIVED_DB, led, me, counters)
        led.compact_if_pruned()
        return out
    finally:
        led.close()


def push_derived(s3, bucket, db_path, ledger, me, counters=None):
    """derived_store.db lifecycle tables — CDC by rowid, batched per table.

    Every row is `SELECT rowid AS _rid, *`; its content hash is compared to
    the ledger's last confirmed hash for that rid and CHANGED rows ship. A plan
    that transitions re-ships its row with a newer pushed_at; the reader keeps
    latest-per-rid. ⚠️ THE LEDGER IS ITS OWN STORE: its nested shape must never
    share a dict with the offset or high-water ledgers — same helper, different
    meaning, is exactly the r82 failure class.
    🔴 r20 PUSH.1 — BOUNDED MEMORY. Rows stream in DERIVED_SCAN_ROWS chunks and
    the ledger is read per chunk (DerivedLedger, SQLite); changed rows ship in
    objects of at most DERIVED_BATCH_ROWS, so a table with a few changes is
    still ONE object per run. `ledger` may be a plain dict (the gates) or a
    DerivedLedger (production).
    """
    pushed = failed = 0
    store = ledger if hasattr(ledger, "get_many") else _DictSeen(ledger)
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
    except Exception:
        return 0, 0
    day = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    is_dict = isinstance(store, _DictSeen)

    def _ship(table, changed):
        batch = [rec for _r, _s, rec in changed]
        sha_b = _sha256(_canon(batch))
        body = _wrap("derived_%s" % table, batch, me or "UNKNOWN", day,
                     {"n_rows": len(batch)})
        key = "%s/derived_%s/dt=%s/sym=%s/%d-%s.json" % (
            PREFIX, table, day, me or "UNKNOWN",
            int(time.time() * 1000), sha_b[:16])
        if put_and_verify(s3, bucket, key, body, counters):
            store.put_many(table, {rid: (sha if is_dict else DerivedLedger._d(sha))
                                   for rid, sha, _rec in changed})
            store.commit()
            return 1, 0
        return 0, 1

    for table in DERIVED_TABLES:
        try:
            cur = con.execute("SELECT rowid AS _rid, * FROM %s ORDER BY rowid" % table)
        except Exception:
            continue                     # table absent on this box — fine
        changed, min_rid = [], None
        while True:
            chunk = cur.fetchmany(DERIVED_SCAN_ROWS)
            if not chunk:
                break
            recs = [dict(r) for r in chunk]
            if min_rid is None:
                min_rid = recs[0]["_rid"]
            known = store.get_many(table, [str(r["_rid"]) for r in recs])
            for rec in recs:
                sha = _sha256(_canon(rec))
                rid = str(rec["_rid"])
                k = known.get(rid)
                if k != (sha if is_dict else DerivedLedger._d(sha)):
                    changed.append((rid, sha, rec))
                    if len(changed) >= DERIVED_BATCH_ROWS:
                        p_, f_ = _ship(table, changed)
                        pushed += p_
                        failed += f_
                        changed = []
        if changed:
            p_, f_ = _ship(table, changed)
            pushed += p_
            failed += f_
        if min_rid is not None:
            store.prune_below(table, min_rid)   # rows the purge removed no longer need a hash
            store.commit()
    con.close()
    return pushed, failed


SERIES_BATCH_ROWS = int(os.environ.get("OT_S3_SERIES_BATCH", "50000"))


def push_series(s3, bucket, db_path, ledger, me, counters=None,
                tables=None, ns="series"):
    """Series tables — batched, high-water per table.

    v4.5: `tables` and `ns` are parameters so the SAME implementation serves
    feed_store's seven and derived_store's three. Defaults reproduce the v4.2
    call exactly, so every existing caller and test is unaffected.

    Same contract as push_candles: rows are append-only and keyed on
    ts_epoch, so a per-table high-water mark pushes only what is new, as ONE
    object per table per ET day of its rows per run (WH.20; capped at SERIES_BATCH_ROWS; a backlog drains
    over successive runs, tail-safe like every other stage). Key carries the
    batch's top ts + content hash, so a retry overwrites the same object.

    ⚠️ THE LEDGER KEY IS NAMESPACED `series|<table>` — the candle ledger holds
    `SYM|interval` in the same file, and two shapes in one dict is the r82
    class. The namespace makes a collision impossible rather than unlikely.
    """
    pushed = failed = 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
    except Exception:
        return 0, 0
    push_day = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    for table in (SERIES_TABLES if tables is None else tables):
        lk = "%s|%s" % (ns, table)
        hwm = float(ledger.get(lk, 0) or 0)
        try:
            rows = [dict(r) for r in con.execute(
                "SELECT * FROM %s WHERE ts_epoch > ? ORDER BY ts_epoch"
                " LIMIT ?" % table, (hwm, SERIES_BATCH_ROWS))]
        except Exception:
            continue                     # table absent on an older schema
        if not rows:
            continue
        # ── WH.20 (otv4 r417, ported) — `dt=` IS THE ROW'S OWN ET DAY, NEVER THE PUSH DAY ──
        # The batch is SPLIT at every ET day boundary and each group is filed
        # under ITS day, so one object can never hold two days and no object
        # can land in a partition its rows do not belong to. The old
        # `day = datetime.now(ET)` filed by PUSH time, so a backlog that drained
        # after midnight (SERIES_BATCH_ROWS caps each run) landed in the NEXT
        # day's partition - measured on mainline 2026-09-23: 566 of 224,336 raw
        # series objects in the wrong dt=.
        groups = {}
        for r in rows:
            try:
                d = datetime.fromtimestamp(
                    float(r["ts_epoch"]),
                    ZoneInfo("America/New_York")).date().isoformat()
            except (TypeError, ValueError, OSError, OverflowError):
                # ⚠️ AN UNREADABLE ts_epoch IS FILED UNDER THE PUSH DAY AND NOT
                # DROPPED: mis-filing one row beats losing it, and the old
                # behaviour filed EVERY row this way.
                d = push_day
            groups.setdefault(d, []).append(r)
        # ⚠️ THE HIGH-WATER MARK ADVANCES ONLY IF EVERY GROUP LANDED. A partial
        # batch that advanced the mark would skip the unwritten rows FOREVER -
        # the box deletes them on its retention clock and S3 is the only durable
        # home. A re-push writes the same key (the name carries the content hash
        # of the SAME rows), so the retry is idempotent.
        all_ok = True
        for d in sorted(groups):
            grp = groups[d]
            top_g = float(grp[-1]["ts_epoch"])
            sha = _sha256(_canon(grp))
            body = _wrap(table, grp, me or "UNKNOWN", d,
                         {"n_rows": len(grp),
                          "ts_from": float(grp[0]["ts_epoch"]),
                          "ts_to": top_g})
            key = "%s/%s/dt=%s/sym=%s/%d-%s.json" % (
                PREFIX, table, d, me or "UNKNOWN", int(top_g * 1000), sha[:16])
            if put_and_verify(s3, bucket, key, body, counters):
                pushed += 1
            else:
                failed += 1
                all_ok = False
                break
        if all_ok:
            ledger[lk] = float(rows[-1]["ts_epoch"])
    con.close()
    return pushed, failed


def _push_chain_tree(s3, ledger, counters, files):
    """Chain snapshots across every day-file, as one stage."""
    pushed = failed = 0
    for path, day, sym in files:
        a, b = push_file(s3, BUCKET, path, day, sym, ledger, counters)
        pushed += a
        failed += b
    return pushed, failed


def reconcile(s3, bucket: str, counters: dict):
    """Reset every prefix counter to the live S3 truth. Returns {prefix: (was, now)}.

    ⚠️ EXPLICIT, NEVER AUTOMATIC — and that is a deliberate refusal. Self-healing
    the counter on every verify would ALSO silently erase a genuine loss: if S3
    really dropped an object, reconciling would quietly agree with the smaller
    number and the alarm we built this to raise would never fire again.
    **A verification that repairs itself is not a verification.**

    So this runs only on `--reconcile`, and only makes sense once a human has
    established that the objects are actually present — which they were on
    2026-08-18: LIST said 1560, the bucket held 1560, the counter said 1561.
    """
    fixed = {}
    for prefix in sorted(counters.keys()):
        n = b = 0
        try:
            pg = s3.get_paginator("list_objects_v2")
            for page in pg.paginate(Bucket=bucket, Prefix=prefix):
                for o in page.get("Contents", []) or []:
                    n += 1
                    b += int(o.get("Size", 0) or 0)
        except Exception:                                      # noqa: BLE001
            continue
        was = int((counters[prefix] or {}).get("n", 0))
        if was != n:
            fixed[prefix] = (was, n)
        counters[prefix] = {"n": n, "bytes": b}
    return fixed


def verify(s3, bucket: str, counters: dict):
    """Reconcile this box's confirmations against what S3 actually holds.

    Per dt=/sym= prefix, on COUNT and BYTES. Both come back from
    list_objects_v2 at no extra cost, so this is a handful of LIST calls
    rather than a HEAD per object — fast enough to gate a wake/verify/stop
    cycle on.

    Deliberately NOT a content hash: every object was already read back and
    byte-compared at PUT time, so content was verified against the source when
    it landed. The failure still live afterwards is "it never arrived", which
    counts catch, and "it arrived short", which bytes catch.
    """
    short = []
    tot_local = tot_s3 = 0
    for prefix, exp in sorted(counters.items()):
        n = b = 0
        try:
            pg = s3.get_paginator("list_objects_v2")
            for page in pg.paginate(Bucket=bucket, Prefix=prefix):
                for o in page.get("Contents", []) or []:
                    n += 1
                    b += int(o.get("Size", 0) or 0)
        except Exception:
            short.append((prefix, exp["n"], -1))
            continue
        tot_local += int(exp["n"])
        tot_s3 += n
        if n < int(exp["n"]) or b < int(exp["bytes"]):
            short.append((prefix, exp["n"], n))
    return short, tot_local, tot_s3


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    report = "--report" in argv
    do_verify = "--verify" in argv
    do_reconcile = "--reconcile" in argv

    try:
        if not ENABLED:
            if report:
                print("s3_push: DISABLED via OT_S3_PUSH=0")
            return 0
        if os.path.exists(PAUSE_FLAG):
            try:
                _why = open(PAUSE_FLAG).read().strip()
            except Exception:
                _why = "?"
            print("s3_push: PAUSED ({}) - nothing pushed. configure.sh item 14 (or a typed OVERRIDE at item 1) "
                  "resumes it.".format(_why))
            if do_verify:
                print("DRAIN host={} sym={} drained=no pushed=0 failed=0 prefixes=0 local=0 s3=0 short=0 "
                      "PAUSED".format(HOST, own_symbol() or "?"))
            return 0

        files = discover()
        if (not files and not report and not do_verify
                and not os.path.exists(TRADES_DB)
                and not os.path.isdir(OHLC_ROOT)):
            return 0  # idle box with nothing at all. Say nothing.

        # ── ONE PUSHER AT A TIME ────────────────────────────────────────────
        # A normal run that loses the race exits silently: the run already in
        # flight is doing exactly this work. --verify waits, because the EOD
        # conductor is blocking on its answer, and falls back to verify-only.
        lock = acquire_lock(LOCK_WAIT if do_verify else 0)
        drained = lock is not None
        if lock is None and not do_verify:
            return 0

        import boto3  # imported late so a missing SDK cannot break --report

        s3 = boto3.client("s3", region_name=REGION)
        counters = load_ledger(COUNTERS_PATH)
        ledger = load_ledger()
        t_ledger = load_ledger(TRADES_LEDGER)
        st_ledger = load_ledger(SHADOW_TRADES_LEDGER)      # r57 (TCS.LOG1)
        misc = load_ledger(MISC_LEDGER)
        c_ledger = load_ledger(CANDLE_LEDGER)
        ds_ledger = load_ledger(DSERIES_LEDGER)
        me = own_symbol()
        total_pushed = 0
        total_failed = 0

        eod_items = []
        try:
            for n in sorted(os.listdir(EOD_DIR)):
                if n.endswith(".json"):
                    eod_items.append((os.path.join(EOD_DIR, n), _eod_day(EOD_DIR), me))
        except Exception:
            pass

        # ── ORDER MATTERS, AND THIS IS THE ORDER ────────────────────────────
        # Smallest and most perishable first; bulk last. A run that runs out of
        # time then loses the TAIL, not the head. Before v1.4 the journal sat
        # third and starved everything behind it for a full evening.
        #   trades  — feeds reports 40/41, small, mutates
        #   eod     — one day only, overwritten per session, silent loss
        #   orb     — ephemeral, rewritten every tick, no log anywhere
        #   ohlc    — one object per day-file, bounded
        #   candles — high-water mark, small batches
        #   chains  — large, but already drained and unreconstructable
        #   shadow  — moderate
        #   journal — largest by far, and the most tolerant of lag
        stages = [
            ("trades", lambda: push_trades(s3, BUCKET, TRADES_DB, t_ledger, counters)),
            # r57 (TCS.LOG1) — the shadow trades, their own prefix and ledger (absent store: nothing, silently).
            ("shadow_trades", lambda: push_trades(s3, BUCKET, SHADOW_TRADES_DB, st_ledger, counters,
                                                  ns="shadow_trades", datatype="shadow_trade",
                                                  src_file="shadow_trades.db")),
            ("circuit_breaker", lambda: push_table(
                s3, BUCKET, TRADES_DB, "circuit_breaker_events", "event_time",
                "circuit_breaker", t_ledger, me, counters)),
            ("eod", lambda: push_whole_files(s3, BUCKET, eod_items, "eod", misc, counters)),
            ("ohlc", lambda: push_whole_files(
                s3, BUCKET, discover(OHLC_ROOT, ".csv"), "ohlc", misc, counters)),
            ("candles", lambda: push_candles(s3, BUCKET, FEED_DB, c_ledger, me, counters)),
            # v4.2 — after candles (same store, same perishability), before the
            # bulk streams so a timeout cannot starve the only copy of the
            # greeks/quote tape. Batched: one object per table per run.
            ("series", lambda: push_series(s3, BUCKET, FEED_DB, c_ledger, me, counters)),
            # v4.3 — the biographies. Small tables, but they are the ONLY copy.
            # v4.5 — beside "series", not beside "derived": same shape, same
            # perishability, and both are read by warehouse_source.load_series.
            ("derived_series", lambda: push_series(
                s3, BUCKET, DERIVED_DB, ds_ledger, me, counters,
                tables=DERIVED_SERIES_TABLES, ns="dseries")),
            # r20 PUSH.1 — opened inside the stage, so a ledger that cannot open fails THIS stage only.
            ("derived", lambda: _derived_stage(s3, me, counters)),
            ("liquidity_ledger", lambda: push_whole_files(
                s3, BUCKET, discover(LIQ_ROOT, ".json"), "liquidity_ledger",
                misc, counters)),
            ("chain_snapshots", lambda: _push_chain_tree(s3, ledger, counters, files)),
            ("shadow", lambda: push_jsonl_tree(
                s3, BUCKET, SHADOW_ROOT, "shadow", misc, counters)),
            ("signal_journal", lambda: push_jsonl_tree(
                s3, BUCKET, JOURNAL_ROOT, "signal_journal", misc, counters)),
        ]

        for name, fn in stages:
            if not drained:
                break                  # verify-only: another pusher holds the lock
            try:
                p_, f_ = fn()
            except Exception:
                p_, f_ = 0, 1          # rule 1: a stream may fail, never raise
            total_pushed += p_
            total_failed += f_
            if p_ or f_:
                flush_all()            # a stage's progress survives the next one

        flush_all()      # always: a run that pushed nothing may still have
                         # nothing to save, and one that did must not lose it

        if do_verify:
            # ONE machine-readable line. The EOD conductor parses this to decide
            # whether a box may be stopped, so it must be stable and exit 0.
            if not drained:
                # Another pusher is mid-drain and owns the ledgers; re-read from
                # disk so we verify against ITS progress, not our stale copy.
                counters = load_ledger(COUNTERS_PATH)
            short, loc, remote = verify(s3, BUCKET, counters)
            # ── r180 — HEAL LEDGER DRIFT, HOLD FOR REAL LOSS ──────────────
            # Operator, 2026-08-28, after TWO MONTHS of nightly holds in
            # which the data was in the bucket every single time: "whatever
            # the disagreement is it's actually costing me money … the
            # disagreement needs to be resolved … we have to solve it
            # tonight." The mechanism: the ledger counts PUTS, S3 counts
            # KEYS; the dedupe set is per-run, so a key re-pushed in a later
            # run inflates the ledger PERMANENTLY, and --reconcile (the
            # manual reset) never ran. reconcile()'s docstring refused
            # automatic healing because it could silence a genuine loss.
            # That refusal is SUPERSEDED BY OPERATOR RULING, with the real
            # alarm kept where it is real: heal a prefix only when (a) THIS
            # drain confirmed zero failed PUTs — every object of the run was
            # read back at PUT, so today's data cannot be the gap — and (b)
            # S3 holds objects on the prefix (n>0). A prefix S3 knows
            # NOTHING about, or any drain with failed>0, still reads SHORT
            # and still HOLDS the box. Historical integrity beyond that
            # belongs to the warehouse-side sweeps (dtp 73/77/78).
            # LOUD, never silent: every healed prefix prints its delta.
            if short and total_failed == 0:
                _healed = []
                for _pfx, _exp, _got in short:
                    if _got > 0:
                        _n = _b = 0
                        try:
                            _pg = s3.get_paginator("list_objects_v2")
                            for _pg_page in _pg.paginate(Bucket=BUCKET, Prefix=_pfx):
                                for _o in _pg_page.get("Contents", []) or []:
                                    _n += 1
                                    _b += int(_o.get("Size", 0) or 0)
                        except Exception:                       # noqa: BLE001
                            continue
                        if _n > 0:
                            _was = int((counters.get(_pfx) or {}).get("n", 0))
                            counters[_pfx] = {"n": _n, "bytes": _b}
                            _healed.append((_pfx, _was, _n))
                if _healed:
                    save_ledger(counters, COUNTERS_PATH)
                    for _pfx, _was, _now in _healed:
                        print("  HEALED {} ledger {} -> s3 {} (PUT-count drift; "
                              "failed=0 this drain)".format(_pfx, _was, _now))
                    short, loc, remote = verify(s3, BUCKET, counters)
            print("DRAIN host={} sym={} drained={} pushed={} failed={} "
                  "prefixes={} local={} s3={} short={} {}".format(
                      HOST, me or "?", "yes" if drained else "no",
                      total_pushed, total_failed, len(counters),
                      loc, remote, len(short),
                      "OK" if (not short and not total_failed) else "SHORT"))
            for pfx, exp, got in short[:5]:
                print("  SHORT {} expected>={} got={}".format(pfx, exp, got))
            # ⚠️ WH.6 — SAY WHICH KIND OF SHORTFALL THIS LOOKS LIKE. A counter
            # that over-counted duplicate PUTs is short by a SMALL, CONSISTENT
            # amount on many prefixes; genuine loss scatters. On 2026-08-18 ten
            # prefixes were each short by exactly ONE and the bucket held every
            # object — two days of "data stranded" alarms for a fencepost.
            # The heuristic does not decide anything; it tells the reader which
            # question to ask first.
            _gaps = [e - g for _p, e, g in short if g >= 0]
            # 🔴 r171 — THE PREFIX-COUNT REQUIREMENT IS DROPPED. It was
            # `len(short) >= 3`, so a box short on ONE or TWO prefixes never
            # earned the drift verdict even when the gap was 1 — the conductor
            # HELD it and it ran all night.
            # ⚠️ MEASURED, from eod_conductor.log on 2026-08-27: **14 of 15
            # boxes held on short=1..3, every night**, and the operator
            # confirmed on the held boxes each time that nothing was actually
            # missing. That is a full night of EC2 per box, indefinitely, for a
            # fencepost. The conductor's own comment already says "holding a
            # box for drift is worse than the bug."
            # ⚠️ THE GAP SIZE IS THE SIGNAL, NOT THE PREFIX COUNT. Duplicate
            # PUTs inflate a counter by a SMALL amount wherever they land;
            # genuine loss scatters and is larger. A 1-object gap on one prefix
            # is the same fencepost as a 1-object gap on ten.
            # 🔴 r444 (otv4; mirrored as OTV4TEST r150) — THIS COMMENT USED TO
            # PROMISE SOMETHING THE CODE HAS NOT DONE SINCE r180, AND TWO
            # SESSIONS READ IT AS THE SPECIFICATION.
            # It said: "a gap of 3+ on ANY prefix still reads as possible loss
            # and STILL HOLDS THE BOX." That is PRE-r180 behaviour. The r180
            # heal runs ABOVE this classifier (the `if _got > 0:` block) and
            # repairs any short prefix where S3 holds objects, whatever the gap
            # size — so a 3+ gap on a NON-EMPTY prefix never reaches this line.
            # ⚠️ AND THAT IS THE RULING, NOT A REGRESSION. r180, 2026-08-28:
            # the per-prefix ledger counts PUTs while S3 counts KEYS, and the
            # dedupe set is per-run DELIBERATELY, so any key re-pushed by the
            # timer, a harvest or a restart inflates the ledger PERMANENTLY.
            # Its row: "the drift diagnosis only forgave gaps <=2 and TWO
            # MONTHS OF ACCUMULATION EXCEEDED IT." Operator: "there's never
            # been a time that the data actually didn't go to the bucket …
            # it's actually costing me money … we have to solve it tonight."
            # 🔑 WHAT STILL HOLDS THE BOX, AND IT IS NOT GAP SIZE:
            #   · a prefix S3 knows NOTHING about (got=0). The heal is gated on
            #     `_got > 0`, so an EMPTIED prefix never heals and stays SHORT
            #     permanently — that is the counter-orphan case (otv4 r436;
            #     OTV4TEST S3.15).
            #   · ANY drain with failed>0, which the heal requires to be zero.
            # ⚠️ THE RESIDUAL RISK IS DELIBERATE AND IS r180's TRADE: on a
            # CLEAN drain a genuine PARTIAL loss IS healed and LOGGED, and is
            # neither held nor alerted. Measured on this tree with a 10 -> 6
            # loss: healed, box halted normally. That trade was made with the
            # operator's reasoning attached and is HIS to revisit.
            # ⚠️ DO NOT "FIX" THE CODE TO MATCH A COMMENT. On 2026-09-26 both
            # the otv4 session and this one read the old text as a live
            # invariant, called the code self-contradictory, and proposed
            # bounding the heal at gaps <=2 — which would have REINSTATED the
            # exact nightly outage r180 was written in one evening to end. A
            # comment is not a specification until you know which ruling
            # wrote it (§0.7).
            if _gaps and max(_gaps) <= 2:
                print("  ⚠️ SMALL, CONSISTENT SHORTFALL ON {} PREFIXES (max {}). "
                      "That is the signature of COUNTER DRIFT, not data loss — "
                      "duplicate PUTs inflate the ledger permanently. VERIFY "
                      "with `aws s3 ls <prefix> --recursive | wc -l` and, if the "
                      "objects are present, run `--reconcile` once."
                      .format(len(short), max(_gaps)))
            elif _gaps:
                print("  ⚠️ SHORTFALL VARIES (max {}) — that is NOT the counter-"
                      "drift signature. Treat as possible real loss."
                      .format(max(_gaps)))

        if do_reconcile:
            _fixed = reconcile(s3, BUCKET, counters)
            # 🔴 THIS WROTE THE PREFIX COUNTERS OVER `chain_ledger.json` — the
            # FILE-OFFSET ledger — instead of `prefix_counters.json`. Found
            # 2026-08-23 after three reconcile/verify cycles made the numbers
            # WORSE each time (222 -> 300 while S3 held 74).
            # ⚠️ THE MECHANISM: chain_ledger maps SOURCE PATH -> lines already
            # pushed. Overwriting it with {prefix: {n, bytes}} means the next
            # `push_file` looks up its path, FINDS NOTHING, starts at line 0 and
            # RE-PUSHES THE WHOLE FILE. So every reconcile destroyed the record
            # of what had been sent, and the next verify re-sent everything —
            # which is what inflated the counter reconcile had just fixed.
            # ⚠️ NOTHING WAS LOST: keys are content-hashed, so the re-pushes
            # overwrote identical objects. The cost was PUTs and a counter that
            # climbed every cycle.
            save_ledger(counters, COUNTERS_PATH)
            print("reconcile: {} prefix counter(s) reset to the S3 truth"
                  .format(len(_fixed)))
            for _p2, (_was, _now) in sorted(_fixed.items())[:10]:
                print("  {} {} -> {}".format(_p2, _was, _now))
            if len(_fixed) > 10:
                print("  ... and {} more".format(len(_fixed) - 10))
            return 0

        if total_pushed or total_failed or report:
            print(
                "s3_push host={} files={} pushed={} failed={} bucket={}".format(
                    HOST, len(files), total_pushed, total_failed, BUCKET
                )
            )
        return 0
    except Exception as exc:  # noqa: BLE001 — rule 1
        try:
            print("s3_push: run aborted, nothing confirmed: {}".format(exc))
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
