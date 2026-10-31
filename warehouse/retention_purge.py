#!/usr/bin/env python3
"""
warehouse/retention_purge.py  v5.1
v5.1  2026-10-31  OTV5 r66 (RET.1) — THE FOUR TICK TABLES ARE KEPT ONE DAY, STILL NEVER PAST THE PUSH MARK.
      quote_series, greeks_series, prints and last_trade: ARTIFACT_DAYS 3 -> 1. session_summary, theo_series and
      underlying_series stay 3. The operator, 2026-10-31, on GOOGL's disk (92%, 721M free of 8.6G; feed_store.db
      1.78G, quote_series 745M / 6.22M rows over 10-27..10-31): "On googl can we delete everything already stored
      in the warehouse & then cleanup & do a 1x reseed", then yes to the long-term change. WHY 1 IS SAFE: (a) the
      3-day reason was "a Friday push that fails silently is not noticed until Monday", and since r136 the cutoff is
      clamped to the push mark (_safe_cutoff), which advances only after a PUT read back byte-identical - an
      unshipped row is never deleted at any window; (b) no trading or indicator code reads these tables older than
      today - seven read sites, windows 60-900 s, proven by tests/check_series_lookback.py L3-L6 (AST inventory,
      every call site's window, and a fixture on which deleting every row older than a day changes no reading).
      A box that never pushes (_box_never_pushes) stays age-only, now at 1 day. WHAT IT BUYS: GOOGL holds ~1.2M
      quote rows a day (~250M with indexes), so the plateau falls from ~3 days of rows plus their freed pages to ~1,
      and reclaim()'s 2.2x VACUUM gate fits on an 8.6G box again; VACUUM INTO and a file swap (OPS.42/OPS.41) are not
      needed. config.py's inert RETENTION_DAYS_ARTIFACTS block (3 days) now differs: this file is the code, per the
      rule below; config.py is left untouched under the benchmark freeze. Gate: tests/check_series_lookback.py L1-L6
      (L1, L2 red on 11b55b1, green on the fix).
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.12 2026-10-13  OTV4TEST r279 (SHARED; MIRROR OF otv4 r416 064070b + r419 b9bb9dc) - THE
      DELETES COMMIT AS THEY GO, AND A VACUUM MUST FIT 2.2x ITS LIVE SIZE. Ruled by the
      operator 10-13 for the Saturday fleet repoint (relayed by 1-REPORTER, MSG-1REP-1013-07,
      "1. Yes"). `_delete_batched` (BATCH_ROWS 200k, BUDGET_S, TRUNCATE checkpoint per chunk,
      absent != failed) is otv4's function byte-for-byte; `_try_delete` is removed; the COUNT
      is dry-run only. VACUUM_HEADROOM 1.15 -> 2.2 with otv4's comment verbatim. This tree's
      own `_safe_cutoff` push clamp (our port of r417) is unchanged and still runs first.
      Gates: tests/check_purge_batched.py and tests/check_vacuum_headroom.py (otv4's, at
      599654c), check_purge_lock K0 repointed.
v1.11 2026-10-04  OTV4TEST r233 (BOX.17, second half; the operator's yes 2026-10-04: "Make sure he has ... pruning
      the retained SPX data") — A BOX THAT NEVER PUSHES IS NOT HELD TO ITS OLD PUSH MARKS. SPX-TEST pushed once
      (2026-10-03, as the ex-AAL managed box) and was then made standalone: its ledgers in ~/.vertigo_warehouse
      froze, and every series cutoff clamped to them, so the series tables would grow without bound once their
      age passed the marks. The clamp now applies ONLY while the box can push. "Cannot push" is PROVEN, never
      inferred from a timer: s3-push.service MASKED, or the never-push drop-in (s3-push.service.d/never-push.conf
      carrying Environment=OT_S3_PUSH=0). A disabled timer is NOT enough (the conductor's quiesce disables it on a
      managed box with rows still unshipped). Unreadable state = assume it pushes = clamp (keeps rows). A mark the
      purge ignores is named in the log. Candles were never clamped and are unchanged. QQQ-TEST has no marks: no
      change there. Gate: tests/check_data_capture.py D6/D6c.
v1.10 2026-10-03  OTV4TEST r192 (AUD.3, MIRROR OF otv4 r420 / OPS.43) — THE RECLAIM NAMES THE REAL trades.db.
      It checkpointed and vacuumed HERE/data/trades.db; the trade record is HERE/trades.db (config.DB_PATH,
      s3_push.TRADES_DB), so the nightly reclaim never touched it. New module constant TRADES_DB, honouring
      OT_TRADES_DB like its other owner. Cost was nil (trades.db is 0.5 MB): a correctness fix. Found by
      the 10-03 audit; mainline fixed it 2026-09-23. Pinned by tests/check_reclaim_paths.py (body identical).
v1.9  2026-09-29  OTV4TEST r175 (SYM.1) — 5m AND 15m ARE KEPT 30 DAYS (were 10 and
      20), so the ~30-day first-boot backfill the operator asked for on
      2026-09-29 is not deleted by the first nightly purge after it lands.
      config.py's declared copy moves with it. 1m (60) and 1h (60) unchanged.
v1.8  2026-09-24  OTV4TEST r136 — THE PURGE NEVER DELETES WHAT S3 HAS NOT CONFIRMED
      (mainline r417's `_safe_cutoff`, ported). The operator, 2026-09-24:
      "Adopt mainline's approach. Should work under managed or standalone."
      Every series cutoff (feed ARTIFACT_DAYS, derived DERIVED_ARTIFACT_DAYS +
      DERIVED_CDC_DAYS) is clamped to the push mark s3_push records for that
      table - `series|<table>` in candle_ledger.json, `dseries|<table>` in
      dseries_ledger.json (the same keys this fork's pusher writes, verified).
      A lagging pusher now GROWS the store instead of silently shredding rows
      nobody shipped. 🔑 BOTH MODES: a STANDALONE box has no push marks, so the
      clamp falls back to age-only - exactly mainline's fresh-box rule - and
      says "no push mark (standalone, or nothing shipped yet)" rather than
      mainline's warning, which would cry wolf every night on a box that never
      pushes by design.
v1.7  2026-09-23  OTV4TEST r108 — 1m candles 5 -> 60 DAYS, to match 1h. The level
      book builds its levels from the HOURLY tape (r36: an hourly high/low is
      the true extreme of its hour, and 1h reaches back 60 days), but the
      operator's BREACHED rule is a 1-MINUTE rule — a 1m close beyond the level
      and the next 1m open beyond it (2026-09-22). MEASURED 2026-09-23 on
      08-25..09-22 warehouse tape, hourly bars built from the SAME 1m bars so
      granularity is the only difference: of 142 session extremes the 1m rule
      breached, the hourly test saw 87 within the hour, 50 more than an hour
      LATE (up to 22 h) and 5 NEVER — 39% of dead levels left live on the
      board. So breaches must be judged on 1m for as far back as levels are
      built on 1h, and 1m retention must cover 1h retention.
      COST, MEASURED: the candles table is 68 bytes a row; 1m across QQQ,
      QQQ_EXT, VIX and VIX_EXT is ~1,400 rows a day, so 60 days is ~85k rows,
      ~6 MB. Every runtime 1m reader is bounded (LIMIT n / LIMIT 1 / one day),
      so nothing loads the longer window into memory. PRUNE_KEEP_ROWS is 0 on
      both services (checked), so this purge is the only 1m deleter.
      Operator, 2026-09-23: "Yes, I agree on All."
v1.6  2026-09-19  OTV4TEST r66 — `plan_tick` / `plan_check` 7 -> 90 DAYS. These
      two ARE the wargaming corpus: the replay harness runs exclusively on the
      tick log, so this number IS its reach. At 7 days a harness run on one
      Saturday sees a different corpus from the run before it, and no refinement
      can be compared against a fixed population. Measured before the ruling
      rather than after: ~7 MB per session (plan_tick 13.3 MB + plan_check
      21.2 MB over five sessions), so 90 days is ~440 MB against 5.9 GB free.
      ⚠️ A LONGER HOLD, NOT AN EXEMPTION — these stay OUT of NEVER_PURGE, and
      the disk arithmetic above is what bounds the window.
v1.5  2026-09-08  OTV4TEST r3 — `level_event` joins NEVER_PURGE beside level_ledger:
      the rejection fact is evidence for every handoff and must outlive the horizons.
v1.4  2026-09-05  r270 / ASK.1 — `character_axis_sample` added at 20 days,
      IN THE SAME REVISION THAT PUSHES IT. It was in no list at all — neither
      purged nor protected — which is the by-absence exposure that let
      `shadow`, `plan_tick` and `plan_check` grow unbounded (S3.15). Adding the
      push without the purge would have left it that way and called the job
      done. ⚠️ 20 days is the sibling default and a RE-PUSH WINDOW, not a fit
      decision: S3 is the durable home, and how much history the bands need is
      answered from the warehouse rather than from the box.
v1.3  2026-09-05  r256 — TWO PURGES FOUGHT OVER ONE DATABASE, AND THIS FILE HAD
      NO LOCK WHILE ITS SIBLING HAS HAD ONE ALL ALONG.
      🔴 MEASURED ON THE FLEET, 2026-09-05, NOT REASONED. The conductor's purge
      phase and a hand-run `--apply` fan-out overlapped, and four boxes died
      with `sqlite3.OperationalError: database is locked` at
      `DELETE FROM candles`. `s3_push.acquire_lock()` has guarded EVERY
      invocation path since WH.6 for exactly this reason — *"the timer and the
      conductor's --verify are different entrypoints to the same work, and
      nothing else was stopping them overlapping"* — and this file, which
      DELETES, had nothing. Same idiom, same `LOCK_WAIT` shape, one lock file.
      🔴 AND `_open()` CONNECTED AT SQLITE'S 5-SECOND DEFAULT. A 2 GB delete
      runs far longer than that, so a brief overlap RAISED instead of waiting.
      `busy_timeout` is now explicit and generous; the lock makes contention
      rare and the timeout makes the rare case wait rather than fail.
      🔴 AND ONE LOCKED TABLE KILLED THE WHOLE RUN. The COUNT was wrapped and
      the DELETE was not, so an error on `candles` escaped `purge()`, took
      `main()` with it, and the RECLAIM NEVER EXECUTED — which is why AMD,
      AVGO, GOOGL and NVDA kept their WALs while the boxes that got through
      returned 8.7 GB. Each DELETE is now guarded per table: it reports, it
      counts the failure, and the run continues to the checkpoint.
      ⚠️ A PARTIAL PURGE IS SAID OUT LOUD. Tables that could not be trimmed are
      named in the summary and the exit code is non-zero, because "removed
      1,452 rows" and "removed 1,452 rows and failed on four tables" are
      different facts and only one of them needs an operator.
      🔑 WHAT TONIGHT PROVED, RECORDED SO IT IS NOT RE-LITIGATED: the reclaim
      itself WORKS. QQQ's WAL went 1.7 GB -> 260 KB and its store 2.4 GB ->
      1.4 GB; TSLA 1.1 GB -> 268 KB and 1.9 GB -> 1020 MB, on a re-run with
      nobody else touching the box. Fleet 23.2 GB -> 9.8 GB. The design was
      right; it had no mutual exclusion.
v1.2  2026-09-05  r255 — TRANSFER, DELETE, **RECLAIM** — AND FOUR STORES THAT
      GREW UNBOUNDED BY ABSENCE FROM EVERY LIST RATHER THAN BY POLICY.
      Operator, 2026-09-05: *"Transfer to s3, then delete, then vacuum. We need
      a nightly hygiene program that aggressively scrubs the boxes after the
      session & leaves only the required tenors."*

      🔴 DELETING ROWS RETURNED NO DISK, AND THIS PROJECT WROTE THAT DOWN
      ITSELF. `purge_verified`'s docstring reads *"NO VACUUM ... SQLite reuses
      freed pages and the store reaches steady state."* Steady state is a
      PLATEAU AT THE HIGH-WATER MARK, not a shrink. Measured fleet-wide
      2026-09-05: `feed_store.db` carries 18-34% free pages — 330-690 MB per
      box, inside files this purge has trimmed nightly since r162. The purge was
      working and the space was never coming back.

      🔴 AND THE WAL WAS LARGER THAN ANYTHING THE PURGE COULD REACH. MU held a
      **1.6 GB `feed_store.db-wal`** beside a 2.3 GB database; META 1.1 GB, AMD
      963 MB, AVGO 596 MB, CRM 500 MB. ⚠️ A WAL IS NOT RECLAIMED BY VACUUM — it
      is reclaimed by a CHECKPOINT, which costs seconds and no temp space, so it
      runs FIRST and unconditionally. SQLite auto-checkpoints near 4 MB, so a
      1.6 GB WAL means checkpoints have not been completing, and the checkpoint
      result is REPORTED rather than assumed: a TRUNCATE blocked by a live
      reader returns busy and looks exactly like one that worked.
      ⚠️ THE WAL WAS INVISIBLE FOR AN HOUR BECAUSE THE MEASUREMENT GLOBBED
      `*.db`. WORKING_AGREEMENT §0.3 records that exact incident — the WAL files
      are `.db-wal`, and the biggest files on the box were excluded by the
      pattern whose job was to find them.

      🔴 VACUUM IS GATED, NOT ATTEMPTED. It writes a COMPLETE SECOND COPY before
      replacing the original, so it needs free disk greater than the live size —
      and on 2026-09-05 the four boxes that needed it most (MU, NVDA, TSLA and
      META, all under 900 MB free) are exactly the four where it would have
      failed. A VACUUM that dies half-way at 16:10 on a 96%-full box is worse
      than no VACUUM. It refuses with the arithmetic printed, and `SQLITE_TMPDIR`
      points at the data directory because `/tmp` is a 476 MB tmpfs and a 1.8 GB
      rewrite cannot fit in it (learned on MU, NVDA and QQQ, 2026-08-27).

      🔑 FOUR STORES GREW BY ABSENCE. `plan_tick`, `plan_check`, `shadow` and
      `chain_snapshots` appear in NONE of `RETENTION_DAYS`, `ARTIFACT_DAYS`,
      `DERIVED_ARTIFACT_DAYS` or `NEVER_PURGE` — nothing deleted them and
      nothing protected them either.
      ⚠️ `chain_snapshots` IS THE SHARPEST: `config.py` has DECLARED 3 days for
      it since v4.4 and no code ever read that. This file's own header rule says
      config is the document and this is the code, so this file moves.
      ⚠️ AND THEY NEEDED SEPARATE LISTS RATHER THAN A BIGGER ONE.
      `check_purge_pushed` C9 proves every `DERIVED_ARTIFACT_DAYS` table ships
      via `push_series`; `plan_tick`/`plan_check` ship via `push_derived` (CDC)
      and the trees via `push_jsonl_tree`/`_push_chain_tree`. Adding them to the
      existing dict would have turned C9 red FOR A TRUE REASON and taught the
      next reader to loosen the one check that caught r191.

      🔴 `shadow` IS DECLARED AND NOT ENFORCED (`None`), AND THAT IS WHY IT
      SHIPS TODAY AT ALL. The 2026-08-25 purge deleted 492,945 `raw/shadow`
      objects believing the stream was dead. It is not: 15/15 boxes carry a live
      unit and 17-32 date directories reaching back to 2026-07-21, and because
      `push_jsonl_tree` resumes from a per-path offset the bucket was never
      re-sent. **The boxes hold the only copy of everything before 08-26, so
      arming shadow before that history is re-pushed and VERIFIED would destroy
      it.** Same sequencing the operator set for the tenors in r80: write the
      number down, argue with it, then give it a consumer.

      ⚠️ IT NOW REPORTS WHAT REMAINS, NOT ONLY WHAT WENT. Aggression has to be
      aimed, and no deletion count explains why MU holds 1.8 GB live against
      CVX's 0.20 GB on identical policy. Per-table remaining rows print every
      run, so the next tuning decision is a query rather than an argument.
v1.1  2026-08-29
v1.1  2026-08-29  r191 — THE DERIVED-SERIES PURGE LIST BECOMES A CONSTANT,
      and its justification is retired. Behaviour is unchanged: the same
      three tables, the same 20 days. What changes is that
      `DERIVED_ARTIFACT_DAYS` is importable, so `check_purge_pushed` can see
      it — which is why it never noticed that all three were being deleted
      with no push stage. See the block above `purge()`'s derived loop for
      why "pure functions of the candles" does not hold, especially for
      `surface_series`.
Trim expired LOCAL data. Dry by default. Never runs unless S3 verified first.

v1.0  2026-08-25  Enforces the policy declared inert in `config.py` v4.4
(RETENTION_DAYS / RETENTION_DAYS_ARTIFACTS). Operator's sequencing:
**"We need to write the per tenor retain before writing any kind of per-tenor
purge"** — the numbers were written down first, argued with, and only then
given a consumer.

🔑 IT RUNS INSIDE `self_close`, AFTER VERIFICATION, NOT ON ITS OWN TIMER.
Two reasons, and the second is the important one:
  · The fleet just went from six EOD timers to two. Adding a third undoes that.
  · **self_close purges at the one moment verification has JUST SUCCEEDED.**
    The rule "never delete unverified data" then falls out of the ORDERING
    rather than needing its own check — if the drain came back SHORT the box
    holds up and this is never reached.

🔑 DAILY, NOT ONE-TIME. A one-shot script has to catch up on ~40 days of
accumulation in a single pass — the largest and riskiest deletion this system
would ever run. A daily pass removes one day's worth and stays boring forever.

🔴 DRY BY DEFAULT. `OT_RETENTION_APPLY=1` arms it. **The policy numbers are
ARITHMETIC FROM EMA_ANCHOR=200, NOT MEASUREMENTS** — 200 bars converted to days
per tenor. Running dry for a week costs nothing and says whether 60 days of 1h
is right or whether the fork (which needs only 21 bars) makes it far too
generous.

⚠️ THE LIFECYCLE TABLES ARE EXCLUDED IN CODE, NOT IN CONFIG. character_ledger,
plan_ledger, gate_disposition, strategy_note and fire_snapshot record STATE
TRANSITIONS AS THEY HAPPENED — a recomputation cannot reconstruct a biography,
so they are as unrecoverable as the tape itself. Indicators, forks and surface
ARE pure functions of the candles and are the safe ones to trim. A hard-coded
exclusion cannot be switched off by a config edit.

⚠️ IT REPORTS WHAT IT REMOVED, ALWAYS. A silent purge is how a wrong threshold
is discovered three weeks later, when the data it took is gone.

Run:  python3 warehouse/retention_purge.py            # dry, prints the plan
      OT_RETENTION_APPLY=1 python3 warehouse/retention_purge.py
"""

from __future__ import annotations

import fcntl
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# r192 (otv4 r420 / OPS.43): THE trades.db THE REST OF THE SYSTEM WRITES - the
# repo root, config.DB_PATH and s3_push.TRADES_DB's file - honouring the same
# OT_TRADES_DB override. The reclaim list named HERE/data/trades.db, which does
# not exist on this box, so trades.db was never checkpointed or vacuumed.
TRADES_DB = os.environ.get("OT_TRADES_DB", os.path.join(HERE, "trades.db"))

# ── r136 (mainline r417) — THE CLAMP: never delete past the confirmed push mark ─
# ⚠️ AN ABSENT LEDGER FALLS BACK TO AGE-ONLY RATHER THAN REFUSING TO DELETE: a
# standalone box (and a fresh managed one) has no marks, and a purge that
# declined everything would fill the disk. The absence is NAMED, not hidden.
_STATE_DIR = os.environ.get("OT_WAREHOUSE_STATE",
                            os.path.join(os.path.expanduser("~"),
                                         ".vertigo_warehouse"))
SERIES_LEDGER  = os.path.join(_STATE_DIR, "candle_ledger.json")
DSERIES_LEDGER = os.path.join(_STATE_DIR, "dseries_ledger.json")


def _pushed_hwm(path, ns, table):
    """The ts_epoch S3 has CONFIRMED for this table, or None if unknowable."""
    import json
    try:
        with open(path, "r", encoding="utf-8") as fh:
            led = json.load(fh)
    except (OSError, ValueError):
        return None
    try:
        return float(led.get("%s|%s" % (ns, table)))
    except (TypeError, ValueError):
        return None


NEVER_PUSH_DROPIN = "/etc/systemd/system/s3-push.service.d/never-push.conf"


def _unit_state(unit):
    """`systemctl is-enabled <unit>` as printed ('masked', 'enabled', ...), or '' when unreadable."""
    import subprocess
    try:
        return subprocess.run(["systemctl", "is-enabled", unit], capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001 - unreadable means unknown, and unknown clamps
        return ""


_NEVER = None


def _box_never_pushes():
    """(True, why) only when this box PROVABLY cannot push (r233). Cached for the run."""
    global _NEVER
    if _NEVER is None:
        import re
        try:
            with open(NEVER_PUSH_DROPIN, "r", encoding="utf-8") as fh:
                txt = fh.read()
        except OSError:
            txt = ""
        if re.search(r"^Environment=OT_S3_PUSH=0\s*$", txt, re.M):
            _NEVER = (True, "the never-push drop-in (OT_S3_PUSH=0)")
        elif _unit_state("s3-push.service") == "masked":
            _NEVER = (True, "s3-push.service is masked")
        else:
            _NEVER = (False, "")
    return _NEVER


def _safe_cutoff(table, age_cutoff, path, ns):
    """(cutoff, note) — the age cutoff, clamped to what S3 has confirmed while this box can push."""
    hwm = _pushed_hwm(path, ns, table)
    if hwm is None:
        return age_cutoff, ""       # standalone, or nothing shipped yet: age only
    never, why = _box_never_pushes()
    if never and hwm < age_cutoff:
        return age_cutoff, ("push mark IGNORED (%.0f, %.1f day(s) old): this box never "
                            "pushes - %s - so the mark is frozen, not lagging"
                            % (hwm, (age_cutoff - hwm) / 86400, why))
    if hwm < age_cutoff:
        return hwm, ("CLAMPED to the push mark (%.0f): S3 is %.1f day(s) "
                     "behind the retention window and the rows above it are "
                     "NOT YET SHIPPED" % (hwm, (age_cutoff - hwm) / 86400))
    return age_cutoff, ""
sys.path.insert(0, HERE)

# ── The policy. Mirrors the (commented-out) block in config.py v4.4. ────────
# ⚠️ DUPLICATED DELIBERATELY, AND THE DUPLICATION IS THE POINT: config's copy
# is INERT so the numbers can be read and argued with without a consumer
# existing. If they diverge, config is the document and this is the code — fix
# this file, and say so.
# 🔴 r108 — "1m" WAS 5 AND IS NOW 60, EQUAL TO "1h", AND THE EQUALITY IS THE
# RULE. Levels are built from the 1h tape; the operator's BREACHED is judged on
# 1m. A 1m window shorter than the 1h one leaves every older level's breaches
# unjudgeable, and measured on real tape the hourly stand-in left 39% of dead
# levels live. `check_level_tape` T8 pins 1m >= 1h. See the v1.7 note above.
RETENTION_DAYS = {"1m": 60, "5m": 30, "15m": 30, "1h": 60, "1d": None}   # r175: 5m/15m 30

# Non-candle raw artifacts. A RE-PUSH window, not a warm-up requirement:
# verified in source that the surface engine reads a 15-minute window and
# nothing reaches across sessions. Three days rather than two because a Friday
# push that fails silently is not noticed until Monday. (r66: the four tick tables are
# now 1 day - the push-mark clamp, not the window, is what keeps an unshipped row.)
# 🔴 r191 — THE DERIVED SERIES PURGE IS NOW A CONSTANT, AND IT WAS THE REASON
# NOTHING CAUGHT THIS. These three were deleted at 20 days by a HARDCODED TUPLE
# inside `purge()`, while `tests/check_purge_pushed.py` proves its invariant by
# importing `ARTIFACT_DAYS` and `NEVER_PURGE` — module constants. A purge list
# the checker cannot see is a purge list outside the invariant, so all three
# were being trimmed with NO PUSH STAGE for as long as the purge has been armed
# (r162). Same shape as the v1.0 finding, one level down.
DERIVED_ARTIFACT_DAYS = {
    "indicator_series":  20,
    "fork_series":       20,
    "surface_series":    20,
    # 🔴 r270 — ADDED WITH ITS PUSH, NOT AFTER IT. Until this revision
    # `character_axis_sample` was in NO list — not purged and not protected,
    # the same by-absence exposure that let `shadow`, `plan_tick` and
    # `plan_check` grow unbounded (S3.15). Adding the push without the purge
    # would have left it that way and called the job done.
    # ⚠️ 20 DAYS IS THE SIBLING DEFAULT AND A RE-PUSH WINDOW, NOT A FIT
    # DECISION. S3 is the durable home once r270 ships it there; how much
    # history the BANDS need is a question for whoever fits them, and it is
    # answered from the warehouse rather than from the box.
    "character_axis_sample": 20,
}

# 🔑 r255 — CDC LIFECYCLE TABLES, PUSHED BY `push_derived`, NOT `push_series`.
# Its own list because the invariant differs: `check_purge_pushed` C9 proves a
# DERIVED_ARTIFACT_DAYS table ships via push_series, and these do not. Folding
# them in would turn C9 red for a TRUE reason, and a check that goes red for the
# wrong reason is the one that gets loosened (the CV.1 lesson).
# ⚠️ 7 DAYS IS A PRIOR, NOT A FIT, and it is a RE-PUSH window like the artifacts
# above rather than a warm-up requirement: nothing on the box reads plan rows
# across sessions — `query.py`'s panels are scoped to TODAY since r210 — so the
# days exist only so a Friday push that failed silently is still recoverable on
# Monday. ⚠️ NOT in NEVER_PURGE despite being plan-shaped: `plan_ledger` is the
# biography and is protected; these two are the per-TICK spine, 2.38M rows over
# five days fleet-wide, and the warehouse is their home.
# 🔴 r66 — 7 -> 90 DAYS. THIS IS THE WARGAMING CORPUS, NOT TELEMETRY.
# Operator's ruling, 2026-09-19: the replay harness runs EXCLUSIVELY on the tick
# log, so its reach IS this number. At 7 days a harness run on a Saturday sees a
# different corpus from the one run the Saturday before, and no refinement can
# be compared against a fixed population.
# 📊 MEASURED BEFORE THE RULING, so the cost was known rather than assumed:
# plan_tick 13.3 MB + plan_check 21.2 MB over five trading sessions = ~7 MB per
# session. 30 days ~145 MB · 60 ~290 MB · 90 ~440 MB, against 5.9 GB free and a
# feed_store that already holds 1.6 GB. 90 days buys ~63 sessions for a quarter
# of what the feed costs.
# ⚠️ AND IT IS WHAT THE LOG CAN ANSWER THAT JUSTIFIES IT: 141 distinct named
# checks, each carrying its VALUE and its VERDICT, 24,663 plan/tick pairs joined
# on ts_epoch+symbol+strategy, median 14 checks per plan per tick. That supports
# re-thresholding any existing gate, re-evaluating the whole conjunction, and
# promoting a record-only `n/a` anchor into a gate — none of which needs the
# feed, and none of which is possible on a corpus that has already been deleted.
# ⚠️ NOT `NEVER_PURGE`. A bounded window is still a purge; this is a longer
# hold, not an exemption, and the disk argument above is what bounds it.
DERIVED_CDC_DAYS = {
    "plan_tick":   90,
    "plan_check":  90,
}

# 🔑 r255 — DATE-PARTITIONED FILE TREES under data/. Not tables: the unit of
# deletion is a `<date>/` directory, and the cutoff is an ET TRADING DAY rather
# than an epoch, because the directory name IS a date and a date predicate is an
# exchange fact (r125). The boxes run UTC, so a naive `date.today()` here rolls
# the day at 20:00 ET and would take a directory that is still today's.
# ⚠️ `chain_snapshots` CLOSES A DIVERGENCE RATHER THAN OPENING A POLICY:
# config.py has declared 3 days for it since v4.4 and nothing ever read it.
# 🔴 `shadow` IS None — DECLARED, NOT ENFORCED. The boxes hold the ONLY copy of
# everything before 2026-08-26 (the 08-25 purge deleted 492,945 objects on a
# finding that was wrong, and the per-path push offsets meant it was never
# re-sent). Arming this before that history is re-pushed AND VERIFIED destroys
# it. The number is written down so it can be argued with; it gets a consumer
# when the extraction has landed.
TREE_DAYS = {
    "chain_snapshots": 3,
    "shadow":          None,
}

# 🔑 r66 (RET.1) — THE FOUR TICK TABLES 3 -> 1. The clamp below (`_safe_cutoff`) is what makes a short window
# safe: the cutoff never passes the push mark, and the mark moves only on a verified PUT, so the "Friday push that
# fails silently" the 3 days were for keeps its rows anyway. Every runtime reader looks back <= 900 s
# (tests/check_series_lookback.py). The other three stay 3: small, and not part of the operator's ruling.
ARTIFACT_DAYS = {
    "greeks_series":     1,
    "quote_series":      1,
    "prints":            1,
    "last_trade":        1,
    "theo_series":       3,
    "underlying_series": 3,
    "session_summary":   3,
}

# 🔴 NEVER PURGED. Not configurable, not overridable.
NEVER_PURGE = {
    "character_ledger", "plan_ledger", "gate_disposition",
    "strategy_note", "fire_snapshot", "level_ledger", "level_event",
    "exit_counterfactual", "circuit_breaker_events", "trades",
}

DAY = 86400.0

# ── r256 — MUTUAL EXCLUSION, MIRRORING `s3_push.acquire_lock` ──────────────
# One lock file per box, its own name: this and the pusher touch the same
# stores but are different work, and sharing a lock would make a long drain
# block a purge for no reason.
LOCK_PATH  = os.path.join(HERE, "data", "retention_purge.lock")
LOCK_WAIT  = int(os.environ.get("OT_PURGE_LOCK_WAIT", "300"))
# SQLite's default is FIVE SECONDS, which is shorter than a single 2 GB delete.
BUSY_MS    = int(os.environ.get("OT_PURGE_BUSY_MS", "120000"))


def acquire_lock(wait_s: int = None):
    """Exclusive flock, or None. Guards EVERY invocation path.

    🔴 THE CONDUCTOR PHASE AND A HAND-RUN ARE DIFFERENT ENTRYPOINTS TO THE SAME
    WORK, and on 2026-09-05 they overlapped: four boxes raised `database is
    locked` on `DELETE FROM candles`, and the boxes that lost the race kept
    their WALs because the reclaim never ran. `s3_push` has had this guard on
    every path since WH.6; this file, which DELETES, had none.
    ⚠️ IT WAITS RATHER THAN REFUSING. A purge that gives up because a drain is
    still finishing is a purge that silently does not run, which is the r162
    failure in a new costume — and the caller is a nightly chain with minutes
    to spare, not an interactive prompt.
    """
    wait_s = LOCK_WAIT if wait_s is None else wait_s
    try:
        os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
        fh = open(LOCK_PATH, "w")
    except Exception:                                          # noqa: BLE001
        return None                     # cannot lock -> caller decides
    deadline = time.time() + max(0, wait_s)
    while True:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fh
        except OSError:
            if time.time() >= deadline:
                try:
                    fh.close()
                except Exception:                              # noqa: BLE001
                    pass
                return None
            time.sleep(1)

# VACUUM needs a full second copy of the LIVE pages before it can replace the
# original; 1.15 is that plus a margin. Below VACUUM_MIN_FREE_BYTES there is
# nothing worth a multi-minute rewrite in the middle of a takedown.
# 🔴 r419 — 1.15 WAS NEVER RIGHT FOR ANY JOURNAL MODE, AND IN WAL IT IS
# DANGEROUS. `VACUUM` builds a COMPLETE SECOND COPY of the database and only
# then replaces the original, so it needs roughly TWICE the live size — in WAL
# mode it writes that copy THROUGH THE WAL, which is worse again. At 1.15 this
# gate cleared a vacuum that could not possibly fit and handed the failure to
# SQLite at the moment of least slack.
# 📊 MEASURED ON PLTR, 2026-09-22, TWICE: `database or disk is full` at 530MB
# AND at 656MB free, on a file whose live size was measured at 401.9MB from
# page_count/freelist_count/page_size. That brackets the real requirement above
# 1.63x and is consistent with ~2x. The old gate would have STARTED both.
# ⚠️ 2.2 RATHER THAN 2.0 — the margin is over the LIVE size at the moment of
# measurement, and a busy box writes while the vacuum runs.
# ⚠️ THIS ONLY EVER MAKES THE GATE MORE CONSERVATIVE. The failure it prevents
# is a half-finished rewrite on a nearly-full volume at 16:10; the cost is a
# vacuum deferred to a night with more room, which the refusal already prints
# in full. `VACUUM INTO` needs only ~1x and is the better long-term answer, but
# it requires a file SWAP, and r418/OPS.41 records exactly how a swap done
# carelessly corrupts the database it was meant to shrink — so it gets its own
# revision and its own gate, not a line in this one.
VACUUM_HEADROOM        = 2.2
# ⚠️ ENV-OVERRIDABLE AND READ PER CALL, not frozen at import. Two reasons and
# the second is the honest one: an 8.6 GB box and a 19 GB box do not want the
# same floor, and a checker has to be able to drive the REAL resolution path
# rather than reach in and reassign a module constant — a test that monkeypatches
# the threshold is testing its own patch (C.23).
VACUUM_MIN_FREE_MB     = 200


def _vacuum_min_free() -> int:
    try:
        return int(os.environ.get("OT_VACUUM_MIN_FREE_MB",
                                  VACUUM_MIN_FREE_MB)) * 1024 * 1024
    except ValueError:
        return VACUUM_MIN_FREE_MB * 1024 * 1024


def _mb(n) -> str:
    n = float(n or 0)
    return "%.0fMB" % (n / 1048576) if n < 1073741824 else "%.2fGB" % (n / 1073741824)


def _log(msg: str) -> None:
    print(f"[retention] {msg}", flush=True)


def _et_cutoff(days: int) -> str:
    """The ET trading day `days` back, as YYYY-MM-DD.

    ⚠️ ET, NOT THE BOX CLOCK. The boxes run UTC and these directories are named
    for the ET session that wrote them, so a naive `date.today()` rolls the day
    at 20:00 ET and a nightly purge running at 16:10 would be comparing against
    tomorrow (r125, and the operator's own long-standing symptom).
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/New_York"))
    return (now - timedelta(days=days)).date().isoformat()


def _tree_purge(root: str, days, apply: bool) -> int:
    """Remove whole `<date>/` directories older than the cutoff. -> dirs removed.

    ⚠️ `days is None` MEANS DECLARED-BUT-INERT AND RETURNS -1, which the caller
    reports as such. It is NOT the same as zero directories removed, and the two
    must never render alike — a policy nobody is enforcing has to say so out
    loud or it reads as a policy that found nothing to do.
    ⚠️ THE NAME IS THE GUARD. Only a directory whose name parses as a date is
    ever considered, so a stray file or a scratch folder under the tree cannot
    be deleted by a rule written for dates.
    """
    if days is None:
        return -1
    cutoff = _et_cutoff(int(days))
    removed = 0
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return 0                       # tree absent on this box — fine
    for n in names:
        if len(n) != 10 or n[4] != "-" or n[7] != "-":
            continue
        try:
            int(n[:4]); int(n[5:7]); int(n[8:10])
        except ValueError:
            continue
        if n >= cutoff:
            continue
        removed += 1
        if apply:
            import shutil
            shutil.rmtree(os.path.join(root, n), ignore_errors=True)
    return removed


def _db_stat(path: str) -> dict:
    """page_count / freelist / page_size / wal bytes for one store. Read-only."""
    out = {"live": 0, "free": 0, "wal": 0}
    try:
        out["wal"] = os.path.getsize(path + "-wal")
    except OSError:
        pass
    try:
        c = sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=5)
    except sqlite3.Error:
        return out
    try:
        g = lambda p: c.execute("pragma " + p).fetchone()[0]
        pc, fl, ps = g("page_count"), g("freelist_count"), g("page_size")
        out["live"] = (pc - fl) * ps
        out["free"] = fl * ps
    except sqlite3.Error:
        pass
    finally:
        c.close()
    return out


def reclaim(paths, apply: bool) -> dict:
    """CHECKPOINT then GATED VACUUM. -> {path: one-line verdict}.

    🔑 ORDER IS THE DESIGN, NOT A PREFERENCE. The checkpoint is cheap, needs no
    temp space and returns the WAL — 1.6 GB on MU, more than the whole free-page
    total — so it runs first and always. The vacuum is expensive, needs a full
    second copy on disk, and on the boxes that most need it there is no room; so
    it runs last and only when the arithmetic says it fits.

    ⚠️ NEITHER STEP MAY BLOCK THE HALT. Every failure is caught and reported;
    the box still comes down, because a box left running all night costs money
    and a large file does not (`purge_verified`'s rule, applied here).
    """
    out = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        before = _db_stat(path)
        note = []
        # ── 1. CHECKPOINT — always, and its RESULT is read ──────────────────
        # ⚠️ `wal_checkpoint(TRUNCATE)` returns (busy, log_pages, checkpointed).
        # busy=1 means a reader held the WAL open and NOTHING was truncated —
        # which is almost certainly why a 1.6 GB WAL exists at all. Reporting
        # the flag is the difference between knowing that and assuming it.
        if apply:
            try:
                c = sqlite3.connect(path, timeout=30)
                busy, _lp, _ck = c.execute(
                    "pragma wal_checkpoint(TRUNCATE)").fetchone()
                c.close()
                after_wal = 0
                try:
                    after_wal = os.path.getsize(path + "-wal")
                except OSError:
                    pass
                if busy:
                    note.append("checkpoint BUSY (a reader holds the WAL) "
                                "wal %s -> %s" % (_mb(before["wal"]),
                                                  _mb(after_wal)))
                else:
                    note.append("checkpoint ok, wal %s -> %s"
                                % (_mb(before["wal"]), _mb(after_wal)))
            except Exception as exc:                            # noqa: BLE001
                note.append("checkpoint FAILED: %s" % exc)
        else:
            note.append("[dry] would checkpoint, wal %s" % _mb(before["wal"]))

        # ── 2. VACUUM — gated on the arithmetic, refused with it printed ────
        st = _db_stat(path)
        need = int(st["live"] * VACUUM_HEADROOM)
        try:
            v = os.statvfs(os.path.dirname(path) or ".")
            free = v.f_bavail * v.f_frsize
        except OSError:
            free = 0
        if st["free"] < _vacuum_min_free():
            note.append("vacuum skipped: only %s reclaimable" % _mb(st["free"]))
        elif free < need:
            # 🔴 THE REFUSAL CARRIES THE NUMBERS. "vacuum skipped" alone is the
            # kind of line nobody acts on; naming the shortfall is what turns it
            # into a volume decision.
            note.append("vacuum REFUSED: needs %s free, disk has %s "
                        "(%s reclaimable is stranded until the volume grows)"
                        % (_mb(need), _mb(free), _mb(st["free"])))
        elif not apply:
            note.append("[dry] would vacuum, reclaiming ~%s" % _mb(st["free"]))
        else:
            # ⚠️ SQLITE_TMPDIR ON THE DATA DIRECTORY. /tmp is a 476 MB tmpfs and
            # a 1.8 GB rewrite cannot fit in it — measured on MU, NVDA and QQQ,
            # 2026-08-27.
            os.environ["SQLITE_TMPDIR"] = os.path.dirname(path) or "."
            try:
                c = sqlite3.connect(path, timeout=60)
                c.execute("vacuum")
                c.close()
                note.append("vacuumed, reclaimed ~%s" % _mb(st["free"]))
            except Exception as exc:                            # noqa: BLE001
                note.append("vacuum FAILED: %s" % exc)
        out[os.path.basename(path)] = " | ".join(note)
    return out


def _open(path: str):
    if not os.path.exists(path):
        return None
    try:
        c = sqlite3.connect(path, timeout=BUSY_MS / 1000.0)
        # ⚠️ BOTH, DELIBERATELY. The `timeout=` argument governs the Python
        # driver's own retry loop; `busy_timeout` governs SQLite's. They are
        # different knobs and the default of five seconds on either is shorter
        # than one 2 GB delete.
        c.execute("pragma busy_timeout=%d" % BUSY_MS)
        return c
    except sqlite3.Error:
        return None


# ── r416 — THE DELETE COMMITS AS IT GOES, OR IT NEVER COMMITS AT ALL ───────
# 🔴 THE DEFECT THIS REPLACES, MEASURED ON PLTR AND QQQ 2026-09-22. Every
# DELETE across every table ran inside ONE transaction that committed only
# after the last table. On the two highest-volume boxes that transaction
# CANNOT FINISH inside the conductor's 900s per-box budget — measured at ~93
# seconds per million rows, so PLTR's 18M backlog needed ~28 minutes and QQQ's
# 53M needed ~82. The run was killed every night, EVERYTHING rolled back
# including the small tables that had finished, and the next night faced more
# rows. **A ratchet: the further a box falls behind, the more certain it is to
# stay behind.** PLTR reached 19.8 days against a 3-day policy and filled its
# disk to 97%; QQQ reached 19.9 days and 59.5M rows.
# 🔴 AND IT REPORTED SUCCESS THROUGHOUT. `removed[table]` was set from the
# COUNT, never from the commit, so the conductor logged
# `PLTR: plan_check 478,995` on a night when PLTR still held 479,001 of them.
# Thirteen boxes were fine, which is why nothing looked wrong: the two that
# were not are exactly the two the log could not distinguish.
# 🔑 BATCHING IS NOT AN OPTIMISATION HERE, IT IS THE CORRECTNESS FIX. With a
# commit per chunk a killed run KEEPS what it has already done, so a box that
# cannot drain in one night drains over two instead of resetting to zero. The
# checkpoint after each chunk also bounds the WAL, which is what let this run
# on a volume with 266MB free — the unbatched form would have filled it.
# ⚠️ AND THE COUNT IS GONE FROM THE APPLY PATH. It decided nothing: the DELETE
# carries its own WHERE, and `rowcount` is free. It cost 153 SECONDS on QQQ's
# quote_series ([[r405]] found the identical waste in `manifold_health`, where
# a COUNT(*) bought a truthiness test for 28.75s). The dry run still counts,
# because there it is the entire product.
BATCH_ROWS = int(os.environ.get("OT_PURGE_BATCH_ROWS", "200000"))
BUDGET_S   = int(os.environ.get("OT_PURGE_BUDGET_S", "0"))     # 0 = drain fully


def _delete_batched(conn, table, where, args, failed, deadline=0.0):
    """DELETE in committed chunks. Returns (rows_committed, outcome).

    outcome: "drained" | "budget" | "failed"
    ⚠️ RETURNS WHAT COMMITTED. The caller reports this number and nothing else,
    because a count of what we INTENDED to delete is what hid this defect for
    weeks.
    """
    # 🔴 ABSENT IS NOT FAILED, AND CONFLATING THEM CRIES WOLF NIGHTLY.
    # The code this replaces swallowed EVERY sqlite error as "table absent on
    # this box" — which is what hid the real defect. The first cut of this
    # function over-corrected and called an absent table a FAILURE, which
    # appends to `failed`, raises PARTIAL PURGE and returns non-zero: a red
    # every night on every box missing an optional table (§17 — an alarm that
    # fires on an expected condition stops being read). Both facts are real
    # and they are now DISTINGUISHED at source, cheaply, before either can be
    # mistaken for the other.
    try:
        present = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,)).fetchone()
    except sqlite3.Error as exc:                                # noqa: BLE001
        _log(f"⚠️ {table}: schema unreadable ({exc}) — table skipped")
        failed.append(table)
        return 0, "failed"
    if not present:
        return 0, "absent"          # expected on this box; silent by design

    total = 0
    while True:
        if deadline and time.time() >= deadline:
            _log(f"⏱️ {table}: budget reached — {total:,} row(s) COMMITTED and "
                 f"kept; the remainder goes next run")
            return total, "budget"
        try:
            cur = conn.execute(
                f"DELETE FROM {table} WHERE rowid IN "
                f"(SELECT rowid FROM {table} WHERE {where} LIMIT ?)",
                tuple(args) + (BATCH_ROWS,))
            n = cur.rowcount or 0
            conn.commit()
            # ⚠️ TRUNCATE, not PASSIVE — a PASSIVE checkpoint leaves the file
            # at its high-water mark, which is what filled PLTR's disk.
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error as exc:                            # noqa: BLE001
            _log(f"⚠️ {table}: DELETE FAILED after {total:,} committed "
                 f"({exc}) — table skipped, run continues")
            failed.append(table)
            return total, "failed"
        total += n
        if n == 0:
            return total, "drained"


# ⬛ r416 — `_try_delete` REMOVED. It ran ONE unbatched DELETE per table and
# every caller now uses `_delete_batched`, which keeps r256's guarantee (a
# locked table costs that table, not the run) AND adds the one r256 could not
# give: a run that is cut keeps what it committed. Deleted rather than left
# dead, because a gate asserting a function nothing calls is the shape §21
# names — `check_purge_lock` K0 now pins `_delete_batched`.


def purge(apply: bool = False, feed_db: str = "", derived_db: str = "") -> dict:
    """Returns {label: rows_removed}. Reports rather than raising."""
    feed_db = feed_db or os.path.join(HERE, "data", "feed_store.db")
    derived_db = derived_db or os.environ.get(
        "OT_DERIVED_DB", os.path.join(HERE, "data", "derived_store.db"))
    now = time.time()
    # ⚠️ 0 MEANS DRAIN FULLY, which is the right default for a hand run.
    # The conductor passes a budget so the close is not held; either way
    # progress is committed per chunk and survives being cut.
    deadline = (now + BUDGET_S) if BUDGET_S else 0.0
    removed: dict = {}
    failed: list = []

    fc = _open(feed_db)
    if fc is not None:
        for interval, days in RETENTION_DAYS.items():
            if not days:
                continue                      # None = keep everything
            cutoff_ms = int((now - days * DAY) * 1000)
            try:
                n = fc.execute(
                    "SELECT COUNT(*) FROM candles WHERE interval=?"
                    " AND ts_epoch_ms < ?", (interval, cutoff_ms)).fetchone()[0]
            except sqlite3.Error:
                continue
            removed[f"candles/{interval}"] = n
            if apply and n:
                # 🔴 r256 — GUARDED. This exact statement raised
                # `database is locked` on four boxes on 2026-09-05, escaped
                # purge(), killed main(), and took the RECLAIM with it — which
                # is why those boxes kept their WALs while the rest returned
                # 8.7 GB. One table failing must cost that table, not the run.
                # 🔴 r256 GUARDED THE FAILURE; r416 GUARDS THE DURATION. One
                # table failing must cost that table and not the run — and a
                # run that cannot finish must keep what it finished.
                got, _out = _delete_batched(
                    fc, "candles", "interval=? AND ts_epoch_ms < ?",
                    (interval, cutoff_ms), failed, deadline)
                removed[f"candles/{interval}"] = got

        for table, days in ARTIFACT_DAYS.items():
            if table in NEVER_PURGE:
                continue                      # belt and braces
            cutoff = now - days * DAY
            cutoff, _note = _safe_cutoff(table, cutoff, SERIES_LEDGER, "series")
            if _note:
                _log(f"🛡️ {table}: {_note}")
            # ⚠️ THE COUNT IS DRY-RUN ONLY (r416). On the apply path it bought
            # nothing and cost 153s on QQQ's quote_series; `rowcount` is free.
            # ⚠️ AND THE `except: continue` BELOW IS WHY IT HAD TO GO: it reads
            # EVERY sqlite error as "table absent on this box" and skips in
            # SILENCE — no log, no PARTIAL, nothing. A slow table that timed
            # out here vanished from the run without a trace.
            if not apply:
                try:
                    removed[table] = fc.execute(
                        f"SELECT COUNT(*) FROM {table}"
                        " WHERE ts_epoch < ?", (cutoff,)).fetchone()[0]
                except sqlite3.Error as exc:                    # noqa: BLE001
                    _log(f"⚠️ {table}: dry COUNT unavailable ({exc})")
                continue
            got, _out = _delete_batched(
                fc, table, "ts_epoch < ?", (cutoff,), failed, deadline)
            removed[table] = got
        if apply:
            fc.commit()
        fc.close()

    # ── derived: the series the engines recompute ───────────────────────
    # ⚠️ THE ORIGINAL JUSTIFICATION WAS "pure functions of the candles, so
    # trimming them costs a recomputation and nothing more". r191 keeps the
    # policy and RETIRES that reasoning, for two measured objections:
    #   · A recomputation tells you what TODAY'S CODE would have said, not what
    #     the bot ACTUALLY SAW. Those differ exactly when there is a bug, which
    #     is the only time anyone goes looking. The operator made this same
    #     argument about ORB state: the derived value is what the range SHOULD
    #     have been, the recorded value is what was used.
    #   · `surface_series` (charm / vanna / GEX) is NOT a function of the
    #     candles at all. It comes off the options chain and `greeks_series`,
    #     and chain snapshots are explicitly NOT reconstructible after the
    #     session. For that table the premise was simply false.
    # So the purge stands — 20 days of intraday series is a real disk cost —
    # but it is now safe because s3_push v4.5 warehouses all three first, and
    # DERIVED_ARTIFACT_DAYS above puts them inside check_purge_pushed's reach.
    dc = _open(derived_db)
    if dc is not None:
        # r255 — the two lists are walked together but kept SEPARATE above,
        # because their push stages differ and so does the invariant that
        # proves each one is safe to delete.
        for table, days in list(DERIVED_ARTIFACT_DAYS.items()) + \
                           list(DERIVED_CDC_DAYS.items()):
            if table in NEVER_PURGE:
                continue
            cutoff = now - days * DAY
            cutoff, _note = _safe_cutoff(table, cutoff, DSERIES_LEDGER, "dseries")
            if _note:
                _log(f"🛡️ derived/{table}: {_note}")
            if not apply:
                try:
                    removed[f"derived/{table}"] = dc.execute(
                        f"SELECT COUNT(*) FROM {table}"
                        " WHERE ts_epoch < ?", (cutoff,)).fetchone()[0]
                except sqlite3.Error as exc:                    # noqa: BLE001
                    _log(f"⚠️ derived/{table}: dry COUNT unavailable ({exc})")
                continue
            got, _out = _delete_batched(
                dc, table, "ts_epoch < ?", (cutoff,), failed, deadline)
            removed[f"derived/{table}"] = got
        if apply:
            dc.commit()
        dc.close()

    # ── r255: date-partitioned file trees ───────────────────────────────────
    for tree, days in TREE_DAYS.items():
        root = os.path.join(HERE, "data", tree)
        n = _tree_purge(root, days, apply)
        # ⚠️ -1 IS "DECLARED, NOT ENFORCED" AND MUST NOT RENDER AS ZERO.
        removed[f"tree/{tree}"] = ("declared, not enforced" if n < 0 else n)

    # ── r255: RECLAIM — checkpoint, then vacuum if it fits ──────────────────
    # 🔑 AFTER the deletions, because a checkpoint before them would return a
    # WAL that the deletes immediately refill, and a vacuum before them would
    # copy rows that are about to go.
    removed["_reclaim"] = reclaim(
        [feed_db, derived_db, TRADES_DB], apply)

    # ── r255: WHAT REMAINS, so the next tuning decision is a query ──────────
    # ⚠️ THIS IS NOT DECORATION. Nothing in a deletion count explains why MU
    # holds 1.8 GB live against CVX's 0.20 GB on identical policy, and the
    # aggression has to be aimed at whichever table that is.
    removed["_remaining"] = _remaining(feed_db, derived_db)
    removed["_failed"] = failed
    return removed


def _remaining(feed_db: str, derived_db: str) -> dict:
    """Row counts left behind, per purgeable table. Read-only, best effort."""
    out = {}
    for db, tables in ((feed_db, list(ARTIFACT_DAYS)),
                       (derived_db, list(DERIVED_ARTIFACT_DAYS)
                        + list(DERIVED_CDC_DAYS))):
        c = _open(db)
        if c is None:
            continue
        for t in tables:
            try:
                out[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except sqlite3.Error:
                continue                # table absent on this box — fine
        try:
            out["candles"] = c.execute(
                "SELECT COUNT(*) FROM candles").fetchone()[0]
        except sqlite3.Error:
            pass
        c.close()
    return out


def main(argv=None) -> int:
    """`--apply` arms it. So does OT_RETENTION_APPLY=1, for the CLI.

    🔴 r162 — WHY THE ARGUMENT EXISTS. This shipped DRY BY DEFAULT, armed only
    by an environment variable, pending a review of the policy numbers that was
    never scheduled. `self_close` has called `main([])` since it was written —
    an EMPTY argv, with no environment set — so **the purge ran dry every night
    for two months, printed what it WOULD delete, and deleted nothing.**
    ⚠️ THE COST, 2026-08-27: `feed_store.db` reached 1.5-1.8 GB per box, the
    6.7 GiB roots hit 100%, and the fleet went blind MID-SESSION. QQQ and MU
    crash-looped; recovering them cost their swapfiles, a failed VACUUM that
    left the database LARGER, and a 14-box volume rebuild to 10 GiB.
    ⚠️ AND IT WAS INVISIBLE BY CONSTRUCTION. A dry run logs the same line every
    night. **Sixty identical log lines are indistinguishable from a job that
    works** — the same failure class as the pytest chain that was decorative
    for weeks and the tooling check that printed green on a broken environment.
    ⚠️ SO THE ARMING IS NOW EXPLICIT AT THE CALL SITE, not ambient in an
    environment nobody sets. `self_close` passes `--apply`; a human running it
    by hand still gets DRY unless they ask for it.
    """
    argv = list(argv or [])
    apply = ("--apply" in argv) or os.environ.get("OT_RETENTION_APPLY") == "1"
    # 🔴 r256 — THE LOCK IS TAKEN HERE, AROUND EVERYTHING, so a hand-run and
    # the conductor phase cannot both be inside purge() at once. Waiting is the
    # right behaviour: the caller is a nightly chain with minutes to spare, and
    # a purge that silently declines is the r162 failure again.
    lock = acquire_lock()
    if lock is None:
        _log(f"⚠️ ANOTHER PURGE HOLDS THE LOCK after {LOCK_WAIT}s — declining. "
             f"Nothing was deleted, nothing was reclaimed.")
        return 3
    try:
        removed = purge(apply=apply)
    finally:
        # ⚠️ RELEASED IN A `finally`. A lock file left held by a crashed run
        # would silently disable every later purge, which is exactly the
        # invisible-no-op class r162 already cost this fleet two months for.
        try:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
        except Exception:                                      # noqa: BLE001
            pass
    # r255 — the result now carries three shapes: integer row counts, the
    # string "declared, not enforced" for an inert tree, and the two report
    # dicts. Only the integers are rows, and summing blindly would have raised.
    failed = removed.pop("_failed", [])
    reclaimed = removed.pop("_reclaim", {})
    remaining = removed.pop("_remaining", {})
    counts = {k: v for k, v in removed.items() if isinstance(v, int)}
    inert = [k for k, v in removed.items() if not isinstance(v, int)]
    total = sum(counts.values())
    if not removed:
        _log("nothing to evaluate (no stores found)")
        return 0
    verb = "removed" if apply else "WOULD remove"
    _log(f"{verb} {total:,} row(s)" + ("" if apply else "  [DRY — set "
                                       "OT_RETENTION_APPLY=1 to arm]"))
    # ── 🔴 r162 — A DRY PURGE AT SHUTDOWN IS A DEFECT, NOT A LOG LINE ────────
    # ⚠️ THE WHOLE FAILURE WAS SILENCE. Sixty nights of "WOULD remove 1.7M
    # rows" at INFO is indistinguishable from a job that works — nobody reads
    # an unchanging line. Name the consequence so the next silence is visible.
    if not apply and total:
        _log(f"⚠️⚠️ RETENTION IS DRY — {total:,} row(s) were NOT removed. The "
             f"store will keep growing; this is how the fleet reached 100% "
             f"disk and went blind mid-session on 2026-08-27.")
    for label in sorted(counts, key=lambda k: -counts[k]):
        if counts[label]:
            _log(f"   {label:<28} {counts[label]:>9,}")
    # ⚠️ AN INERT POLICY ANNOUNCES ITSELF. "declared, not enforced" and "found
    # nothing to remove" are different facts and must never render alike — the
    # whole reason `shadow` ships with None is that somebody has to see it is
    # not yet armed.
    for label in sorted(inert):
        _log(f"   {label:<28} {removed[label]}")

    # ── r255 — RECLAIM ──────────────────────────────────────────────────────
    # 🔴 THIS BLOCK REPLACES THE "VACUUM IS NOT RUN" NOTE THAT STOOD HERE. That
    # note was right about the cost and wrong about the consequence: freed pages
    # do NOT come back as the store grows, they plateau at the high-water mark,
    # and fleet measurement on 2026-09-05 found 18-34% of every feed_store
    # sitting free while the boxes ran out of disk.
    for name, verdict in sorted(reclaimed.items()):
        _log(f"   reclaim {name:<20} {verdict}")

    # ── r255 — WHAT REMAINS ─────────────────────────────────────────────────
    # ⚠️ REPORTED EVEN WHEN NOTHING WAS DELETED. The question this answers is
    # not "did the purge work" but "which table is the 1.8 GB", and that one is
    # unanswerable from a deletion count.
    if remaining:
        _log("   remaining rows after purge:")
        for t in sorted(remaining, key=lambda k: -remaining[k]):
            _log(f"     {t:<26} {remaining[t]:>12,}")

    # ── r256 — A PARTIAL PURGE IS NOT A SUCCESS ─────────────────────────────
    # ⚠️ "removed 1,452 rows" and "removed 1,452 rows and failed on four
    # tables" are different facts, and only one of them needs an operator. The
    # non-zero exit is what lets the conductor's phase say so per box.
    if failed:
        _log(f"⚠️⚠️ PARTIAL PURGE — {len(failed)} table(s) could not be "
             f"trimmed: {', '.join(sorted(set(failed)))}. The reclaim still "
             f"ran; those tables keep their rows until the next pass.")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
