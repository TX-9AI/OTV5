#!/usr/bin/env bash
# tools/land.sh — v5.2
# v5.2  2026-10-31  OTV5 r68 (CFG.5) — OT_RESTING_STOP_STATE leaves every CHECK's scratch env: the resting stop is deleted (the
#   operator, 2026-10-31: "Resting stop was a study. It failed."), so no checker can write its state file. check_land_tooling T6.
# v5.1  2026-10-25  (DEP.2 mirror, HYG.14) — POS/NEG GREP `-qF --`, AND EVERY CHECK GETS ITS OWN TMPDIR, REMOVED AFTER.
#   DEP.2: `grep -qF "$p"` read a POS/NEG text beginning with `-` as a grep OPTION (exit 2): a NEG could never fire
#   (fails OPEN) and a POS refused a correct delivery (fails CLOSED). Mirrors day_trader_pro's lander v1.14 (dtp r374 /
#   LAND.10): `grep -qF -- "$p" ... 2>/dev/null`. HYG.14: ~110 checkers leave mkdtemp dirs in /tmp, which is tmpfs (RAM;
#   control held 2,225 of them, 814 MB), and the per-CHECK $_scratch was itself never removed. Each CHECK now runs with
#   TMPDIR=$_scratch/tmp and $_scratch is removed when it returns, pass or fail. Gate: tests/check_land_spec_parse.py
#   L15-L17, born red on ffe10bf.
# v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
# v1.24 (2026-10-25) — OTV5 r5 (DOC.35). docs/ENV.md IS REGENERATED AT LAND, LIKE THE TWO MAPS. r4 moved lines in
#   tools/boot_sweep.py and tests/check_clean_deploy.py and shipped without regenerating docs/ENV.md, so check_env_doc E1
#   went red on the next sweep (QQQ-TEST MSG-QQQ-1025-03) - a generated document that depends on an edit after its
#   generation is the r315 lesson again. Now the land runs tests/gen_env_doc.py after the write map (when the tree carries
#   it) and stages docs/ENV.md by name. The regeneration runs BEFORE the CHECK stage, so a spec may list check_env_doc
#   in CHECK and pass on the drift it fixes; it FAILS CLOSED (exit non-zero or an empty file refuses the land by name).
#   Gate: tests/check_land_spec_parse.py L12-L14 (born red on v1.23). Critiqued by QQQ-TEST (MSG-QQQ-1025-05).
# v1.23 (2026-10-25) — OTV5 r4 (GATE.6). OT_HEARTBEAT_FILE UNDER $_scratch on every CHECK: position_manager's mark
#   fallback touches utils.heartbeat (data/BOT_HEARTBEAT unless moved), and tools/emergency_watchdog.py reads that file's
#   mtime as the bot's liveness, so a checker run by a land refreshed the watchdog's signal (QQQ-TEST MSG-QQQ-1024-47,
#   found in the boot sweep, the same gap here). check_land_tooling T6.
# v1.22 (2026-10-24) — OTV5 r1 (LAND.2). THE RESOLVER NAMES EVERY CHECKOUT THAT CARRIES THE MARKERS AND REFUSES
#   AN AMBIGUOUS ONE. It took the FIRST `$HOME/*/` checkout carrying all REPO markers, in glob order, so a second
#   checkout with the same files (this tree beside the one it was seeded from, or beside the mainline tree on
#   control) would silently capture a land meant for the other. Every match is collected; two or more are
#   REFUSED with both named; the optional spec directive `ORIGIN <owner/repo>` picks the one whose `git remote
#   get-url origin` ends in it, and a lone checkout whose origin disagrees with a declared ORIGIN is refused too.
#   A spec with no ORIGIN and one match lands exactly as before. The same rule as day_trader_pro's lander v1.18
#   (otv4 r502 / OPS.19). ALSO: the bookkeeping checker consulted is the TARGET TREE'S OWN
#   tools/check_land_discipline.py when it carries one; the old lookup asked $HOME/day_trader_pro first, so on control
#   this tree was judged by another lineage's checker. Gate: tests/check_land_spec_parse.py L6-L11, born red on v1.21
#   at L6-L9 and L11. OTV5 r0's ledger row claimed the ORIGIN rule for this tree before it was here; this revision
#   makes the claim true.
# v1.21 (2026-10-20) — OTV4TEST r307 (GATE.4). OT_PLAN_STATES_FILE UNDER $_scratch on every CHECK: r303's plans panel
#   (query.show_decisions) reads data/plan_states.json, which the bot writes at start, so a checker's verdict depended on
#   the live bot's plan states (check_foreign_symbol_board F7 RED at the 10-20 08:00 sweep on both boxes). check_land_tooling T6.
# v1.20 (2026-10-18) — OTV4TEST r292 (GATE.1). THREE MORE STORES UNDER $_scratch on every CHECK: OT_FEED_DB (the live
#   feed_store.db was READ by 42 checkers through feed_db_path() at call time), OT_RESTING_STOP_STATE and
#   OT_WAREHOUSE_STATE. Found by the 2026-10-18 audit (B4). check_land_tooling T6.
# v1.19 (2026-10-15) — OTV4TEST r287 (CFDIR.1). THE SIXTH WRITER. Every CHECK also gets
#   OT_COUNTERFACTUAL_DIR under $_scratch: seven bot modules append to data/counterfactual/, and a
#   checker that drives them wrote fixture rows into the LIVE logs (r285: check_liquidity_hunt and
#   check_runaway_plan; r287: check_entry_underwater). check_land_tooling T6.
# v1.18 (2026-10-03) — OTV4TEST r194. THE FIFTH WRITER (BOX.16). Every CHECK also gets
#   OT_LOG_FILE under $_scratch: main attaches its file handler to config.LOG_FILE at import,
#   so every checker that imports main wrote into the box's live bot.log. check_land_tooling T6.
# v1.17 (2026-09-26) — OTV4TEST r146. Every CHECK gets OT_INSTRUMENT explicitly (QQQ when the
#   shell has none): config no longer guesses QQQ, and the checkers were written against it.
# v1.16 (2026-09-25) — OTV4TEST r144. THE FOURTH WRITER. Every CHECK now also gets
#   OT_SIGNAL_JOURNAL_DIR under $_scratch: checkers that drive the ORB engine wrote
#   retest_check fixtures into the live data/signal_journal, and on a pushing box
#   those reached the warehouse as another symbol's events. check_land_tooling T6.
# v1.15 (2026-09-23) — OTV4TEST r109. THE THIRD STORE. r13 pointed the trades and
#   derived stores at scratch for every CHECK, and left `resting_orders.db` live.
#   91 of its 101 rows on 2026-09-23 were checker fixtures (symbol X, strike 81,
#   session 2026-08-25) — `check_entry_gate` drives the paper entry path after
#   09:35 by the clock, and a paper entry places a resting offer wherever
#   `execution/resting_orders._db_path()` resolves. It honours OT_RESTING_DB;
#   nothing set it. Now the CHECK stage does. check_land_tooling T6 pins it.
# v1.14 (2026-09-22) — OTV4TEST r102. EXEC BIT. THE LANDER ITSELF was 100644
#   in the git index, so a fresh clone or a repoint got `Permission denied`
#   on the one script needed to land the fix. Now 100755; check_configure_relaxed
#   C5 pins it. No content change.
# v1.13 (2026-09-19) — OTV4TEST r65. DIRECTIVE PARSING IS WHITESPACE-NORMALISED
#   AND A `NEG` NAMING A MISSING FILE IS REFUSED. Every directive stripped
#   exactly one space while this file's own format block documents aligned
#   columns, so a spec written from the documentation mangled its paths — and
#   POS failed closed while NEG FAILED OPEN, passing an assertion it had never
#   evaluated. Both halves fixed: one `_spec_val` parser, and an unresolvable
#   NEG (or POS) path is a refusal rather than a silent pass.
# v1.12 (2026-09-10) — OTV4TEST r13. CHECKs run with OT_TRADES_DB and OT_DERIVED_DB
#   pointed at scratch files: a checker can never reach the box's live stores again
#   (check_standing_offer S5 landed a fixture as a live open position on 2026-09-10).
# v1.11 (2026-09-08) — OTV4TEST r1. `LEDGER <path>` in a half's land.spec names
#   the revision ledger that half appends to. ABSENT MEANS docs/GENESIS.md, so
#   every mainline half is byte-for-byte unaffected. The isolated fork passes
#   docs/GENESIS-TEST.md, and its inherited docs/GENESIS.md stays FROZEN as the
#   lineage record of where the fork came from.
#   ⚠️ A MISSING LEDGER NOW REFUSES rather than skipping the append. Until now
#   the append ran only `if [ -f ... ]`, so a typo'd path would have committed
#   with NO ledger row and reported success — §35's "a revision absent from the
#   ledger did not happen", violated silently by the tool that enforces it.
#   🔴 THIS FILE NOW EXISTS IN TWO REPOS AND THAT IS A REAL COST, NOT A DETAIL.
#   The fork box is segregated from control and cannot reach day_trader_pro, so
#   it must carry its own copy. They are IDENTICAL as shipped and must stay so:
#   dtp needs this same v1.11 landed, or the two drift and the drift sits in
#   the tool that gates everything else. Recorded as an action item, not solved.
# v1.10 (2026-09-07) — dtp r321. `tools/preflight.sh` is REMOVED. r320 added it
#   without being asked; the operator had already ruled it out of scope. The
#   field-table fix below stays — that one WAS the ask.
# v1.9 (2026-09-07) — dtp r320. The spec field table was INCOMPLETE:
#   it listed REPO/BASE/REV/DESC/DEL/POS/NEG and omitted CHECK and ORDER, both
#   of which the lander enforces. A reference that documents seven of nine
#   fields is how the next author writes a spec that gets refused.
# v1.8 (2026-09-07) — dtp r316 / LAND.7. `BASE <sha>` — THE ARCHIVE DECLARES
#   WHAT IT THINKS HEAD IS, AND A MISMATCH IS REFUSED BEFORE ANYTHING IS
#   EXTRACTED. `tar` overwrites and git never merges a payload, so an archive
#   built against an old clone silently reverts every file it carries — a
#   near-miss three times now (r209, and twice on 2026-09-07). NOTHING refused
#   it: the content gate greps strings a stale file still has, the discipline
#   gate asserts a file agrees with ITSELF, and the maps regenerate after the
#   extract. Every gate was self-consistent and every gate passed.
#   🔑 It does NOT enumerate clobber types — it never looks at the files — so
#   it also catches the case a version-monotonic check cannot: a stale copy of
#   a file with no version header.
#   ⚠️ Compared AFTER the pull; a missing BASE is REFUSED, not skipped.
# v1.7 (2026-09-06) — dtp r309 / LAND.5. A PROGRESS BAR OVER THE SLOW STRETCH.
#   Operator: "this part always takes a long time — can we add a clever progress
#   bar?" 🔑 IT COUNTS REAL STAGES RATHER THAN ESTIMATING TIME: the CHECK count
#   is read from the spec before anything slow runs, plus a fixed tail. A
#   timer-based bar would be inventing a number, and this repo has spent a day
#   removing things that report confidence they do not have.
#   ⚠️ IT NAMES THE STAGE — a bar says it is alive, the label says WHICH check
#   is slow, which is the part worth knowing on a phone.
#   ⚠️ NOT A TTY -> SILENT, or the escape codes land in a log; and the line is
#   cleared before every durable line so nothing printed is overwritten.
# v1.6 (2026-09-05) — dtp r298 / LAND.4. 🔴 `DEL` RAN AFTER THE MAPS WERE
#   REGENERATED, SO EVERY DELETION SHIPPED A STALE FILE_MAP. v1.4 put the
#   removal in the staging block, which sits BELOW `gen_file_map.py`. Landing
#   otv4 r278 — which deletes `tests/check_no_regime.py` — the map was rebuilt
#   while the file still existed, the file was then removed, and the repo's own
#   PRE-COMMIT hook regenerated, found drift and refused the commit. **The land
#   command's own artifact disagreed with the tree it was committing.**
#   ⚠️ AND THE SANDBOX COULD NOT SEE IT. `check_land_sh`'s fixtures are fresh
#   `git init` repos with NO pre-commit hook, so nothing regenerates after the
#   staging block and the drift never surfaces. The r269 docs purge did not
#   expose it either, because `.md` files are not in the import graph. The DEL
#   now runs BEFORE the maps, so they are generated against the tree that is
#   actually committed.
#   ⚠️ AND `die()`'s RECOVERY LINE IS FIXED HERE TOO. r293 corrected the
#   ROLLBACK message and left this one, on the reasoning that a gate refusal
#   stages nothing. A COMMIT failure stages everything — which is what r278
#   hit — so this line needed the unstage as much as the other did.
# v1.5 (2026-09-05) — dtp r293 / LAND.3. 🔴 A ROLLED-BACK HALF SAID "the files
#   are still in the tree, uncommitted" — TRUE, AND MISLEADING. `reset --soft`
#   leaves the payload STAGED, and the habitual cleanup `git checkout -- .`
#   copies the INDEX into the working tree, restoring exactly what it was meant
#   to discard. Observed on a real retry 2026-09-05: the tree read clean, the
#   files were still there, and the next land appended a SECOND GENESIS row for
#   the same revision — caught only by `check_land_discipline`'s duplicate-row
#   check. The message now says STAGED and prints a command that unstages
#   FIRST. ⚠️ The rollback itself is unchanged and stays `--soft`, so an
#   unrelated file the operator had mid-edit survives (§35): the defect was in
#   the sentence and the missing command, not in the mechanism.
# v1.4 (2026-09-05) — dtp r291. `DEL <path>` — A DELIVERY CAN REMOVE A FILE.
#   A payload only ever ADDED or overwrote, so retiring a document meant the
#   operator deleting it by hand after the land: outside the gate, outside the
#   commit, and outside the GENESIS row that is supposed to describe what the
#   revision did. otv4 r269 needed to remove eight spent thread contracts and
#   had nowhere to say so. One path per directive, never a glob, and a target
#   that is already absent is a REFUSAL rather than a no-op — a spec describing
#   a repo that does not exist must not land quietly.
# v1.3 (2026-09-05) — dtp r289 / DEP.2. POS/NEG MATCH AS FIXED STRINGS. See the
#   block in the spec-format header: `grep -q` is a BRE, and it graded two
#   deliveries wrongly in one day — `**r247**` degenerated to `r24` and PASSED
#   against a file with no such row, and `[ "$GO" = "y" ]` read as a character
#   class and REFUSED a correct one. One failed open, one failed closed.
# v1.2 (2026-09-05) — dtp r279. ALL HALVES LAND, OR NONE REACH ORIGIN.
#   Operator, 2026-09-05: "make sure all will land or none."
#
#   🔴 THE FAILURE HE IS CLOSING, OBSERVED RATHER THAN IMAGINED. Landing
#   r277_r2 before r276_r2 in the sandbox: the dtp half passed its gate,
#   committed AND PUSHED, and only then did the otv4 half's gate correctly
#   refuse on a GENESIS row r276 had not yet written. Origin ended up holding
#   the code with no backlog entry — a half delivery, on the shared truth the
#   fleet pulls from — and re-running it then died at `git commit` with nothing
#   left to stage. v1.1 landed halves sequentially and stopped at the first
#   failure, which is one-at-a-time, not all-or-nothing.
#
#   🔑 WHY A PRE-FLIGHT OF EVERY GATE WOULD NOT HAVE WORKED, and this is the
#   whole design. The obvious fix is "verify every half before landing any" —
#   and it is WRONG here, because a half is ALLOWED to gate on an artifact an
#   EARLIER half produces. r277_r2's otv4 half asserts a GENESIS row that
#   r276_r2's otv4 land appends. Pre-flighting it before r276 landed would fail
#   a gate that is not actually failing. The dependency is real and the ordering
#   exists to serve it.
#
#   🔑 SO THE SPLIT IS COMMIT vs PUSH, WHICH IS WHERE THE IRREVERSIBILITY
#   ACTUALLY SITS. Phase 1 verifies and commits each half LOCALLY, in order, so
#   a later half still sees an earlier half's landed files. Nothing is pushed.
#   Phase 2 pushes every repo, and only runs if EVERY half reached a commit.
#   A failure anywhere in phase 1 rolls every repo this run committed to back
#   to the SHA it was on before the run started — so ORIGIN NEVER SEES A
#   PARTIAL DELIVERY, which is the property that matters when fifteen boxes
#   pull from it.
#
#   ⚠️ THE ROLLBACK IS `reset --soft`, NOT `--hard`, AND THAT IS DELIBERATE.
#   A hard reset would also revert an unrelated tracked file the operator had
#   edited — the exact reason §35 already refuses a blind `git checkout -- .`
#   on a failed gate. Soft moves HEAD back and leaves the tree, so a rolled-back
#   half looks EXACTLY like a half that failed its gate today: files present,
#   uncommitted, recovery printed. Nothing of his is destroyed to tidy up after
#   a delivery of mine.
#
#   ⚠️ AND THE HONEST LIMIT IS STATED RATHER THAN PAPERED OVER. Phase 2 pushes
#   to two independent remotes; that is not a transaction and cannot be made
#   one. What it CAN be is ordered last, back to back, with nothing between
#   them but network — and if one push fails the report names exactly which
#   repo is ahead of its remote and the one command that fixes it. A rolled-back
#   push is not attempted: reverting something already on origin is a decision
#   for a human, not a cleanup step.
# v1.1 (2026-09-05) — dtp r278. THREE GAPS BETWEEN WHAT THIS DID AND WHAT THE
#   OPERATOR ASKED A DEPLOY TO DO, plus the menu item LAND.1 refused and he has
#   now asked for. His list, 2026-09-05: unpack, stage, verify the write map,
#   the file map, the file versions, the changelog and the Genesis append,
#   "any smoke tests or canaries are verified", then commit and clean up.
#   v1.0 already did all of that EXCEPT the checks — so this adds the one
#   missing stage rather than rebuilding the nine that worked.
#
#   🔴 (1) IT RAN NO CHECKERS. The content gate greps for a distinctive line;
#   it never EXECUTES anything. That is precisely the r201 shape WA §0.6 names:
#   the gate asserted a function existed and that the file parsed, and both were
#   true of the broken version. `CHECK <path>` directives now RUN in the repo
#   and must exit 0.
#   ⚠️ AND A HALF THAT SHIPS CODE AND DECLARES NO CHECK IS REFUSED — detected,
#   not assumed: if the payload carries a `.py` outside `docs/` and the spec
#   names no check, nothing was executed and the delivery says so by failing.
#   A docs-only half legitimately has nothing to run and reports that out loud
#   rather than passing silently, because "not applicable" and "passed" must
#   never look alike (the CV.1 failure, and r183's own SKIP idiom).
#
#   🔴 (2) `git add -A` STAGED WHATEVER WAS IN THE TREE. The operator's own
#   standing rule is the opposite — "NEVER git add -A; stage shipped files by
#   name" — written after a stray `fit_report.py` was pushed off main. WA §33's
#   sketch of the land order says `git add -A`, so two documents disagreed and
#   the looser one was the one in the code. Now every path is named: the
#   payload's own file list, plus the two regenerated maps and the GENESIS row
#   when the repo has them. An unrelated local edit is no longer swept into a
#   delivery commit.
#
#   🔴 (3) THE ARCHIVE IT DELETED WAS A GUESS. `ls "$HOME"/*_r*.tar* | head -1`
#   takes the first glob match, and the operator routinely has two pending — on
#   2026-09-05 he had r276 and r277 in `/home/ubuntu` at once. The cleanup then
#   `rm -f`s that guess. `LAND_ARCHIVE` is now honoured and `tools/deploy.sh`
#   sets it to the file it actually extracted; without it, an AMBIGUOUS glob
#   deletes NOTHING and says so. Untidy is recoverable; deleting the wrong
#   tarball is not (r206: a derived figure must name the layer it came from).
#
#   ⚠️ NEW OPTIONAL DIRECTIVE `ORDER <n>` sorts the halves when `deploy.sh`
#   discovers them, so a two-repo delivery whose second half cites the first
#   cannot land backwards. Default 50; ties break on name.
# v1.0 (2026-09-01) — otv4 r207 / dtp r235. THE LANDER, GENERIC AND MULTI-REPO.
#   Operator, 2026-09-01: "why don't you package your land script as a generic
#   in the tarball & keep calling it every time we land a new update... we can
#   absolutely ship multi-repo file uploads in the same tarball with different
#   land commands."
#
#   🔴 WHY IT EXISTS. The same deploy was hand-built three times in one session
#   and hand-built wrong twice, both times on TRANSPORT rather than logic: one
#   carried `cd "$R" || exit 0` and CLOSED THE OPERATOR'S SHELL when the path
#   guess was wrong, the next was 4,400 characters and the mobile paste
#   truncated it mid-string at a `>` continuation prompt. WORKING_AGREEMENT §1
#   already said what to do — "if logic needs more than one line, write it as a
#   file, have the user download/stage it, and run it as a script" — and §13
#   says check whether the menu already does it before writing a one-off. A
#   deploy retyped every session is the definition of a one-off.
#
#   🔑 IT LIVES IN day_trader_pro, FOR THE REASON r183 ALREADY GAVE. Control is
#   always present, and one implementation beats two that drift. It also means
#   an otv4 archive can never overwrite the script that is extracting it —
#   bash reads a script incrementally by byte offset, so a delivery that
#   replaced its own running lander would execute garbage from wherever the
#   interpreter had reached. The staging copy in /tmp is what actually runs, so
#   even a dtp delivery that updates this file is safe.
#
# ⚠️ THE SPEC NEVER ENTERS A REPO. Each half of the archive carries its own
#   `land.spec` — the per-delivery content gate, which cannot be generic
#   because the only auto-derivable assertion is "the version moved", and that
#   is precisely the header-bump-with-no-edit the gate exists to catch. The
#   spec sits in the STAGING directory beside the payload and is never copied
#   in, so §27's "the archive carries no MANIFEST or scaffolding" holds by
#   construction rather than by a cleanup step someone has to remember.
#
# ⚠️ NO `exit` HAZARD FOR THE OPERATOR. This is run as `bash land.sh`, a child
#   process. Even so, nothing here assumes an interactive shell.
#
# Usage:
#   mkdir -p /tmp/land && tar xf "$HOME"/<archive>.tar* -C /tmp/land
#   bash /tmp/land/land.sh dtp otv4        # land both, in that order
#   bash /tmp/land/land.sh otv4            # or one at a time
#
# 🔑 v1.13 (r65) — ONE PARSER FOR EVERY DIRECTIVE. Strips the token and ALL
# following whitespace, so the COLUMN-ALIGNED form documented below parses
# identically to the single-space form. Before this the two disagreed and the
# documentation was the losing side.
_origin_matches() {
  # v1.22 — does remote url $2 name repository $1 (owner/repo, or any path suffix)? Scheme, user@, ':' and a
  # trailing .git are ignored; the match is on a whole path component boundary.
  local want="${1%/}" url="$2"
  want="${want%.git}"
  url="${url%/}"; url="${url%.git}"
  url="${url#*://}"; url="${url#*@}"; url="${url//:/\/}"
  case "/$url" in */"$want") return 0 ;; esac
  return 1
}
_spec_val() {                       # $1 = whole line, $2 = directive token
  local v="${1#"$2"}"               # drop the token
  v="${v#"${v%%[![:space:]]*}"}"    # drop every leading space/tab
  printf '%s' "$v"
}

# Spec format (one directive per line, `|` separates fields):
#   REPO   <marker-file> <marker-file>     files that identify the target repo
#   ORIGIN <owner/repo>                    (v1.22) the repository those files belong to; required when two
#                                           checkouts under $HOME carry the markers, optional otherwise
#   BASE   <sha>                            commit the payload was built against (v1.8)
#   REV    r207                             revision id, for GENESIS + the gate
#   DESC   <one line>                       GENESIS row AND commit subject
#   DEL    <path>                            REMOVED from the repo (v1.4)
#   POS    <path>|<literal string>          must be present after extraction
#   NEG    <path>|<literal string>          must be ABSENT after extraction
#   CHECK  <path>                           a SCRIPT PATH, run as `python3 <p>`
#   ORDER  <n>                              half sequencing within one archive
#
# 🔴 v1.3 — POS/NEG ARE FIXED STRINGS (`grep -qF`), NOT PATTERNS. They were
# `grep -q`, which is a BASIC REGULAR EXPRESSION, and the gate therefore
# passed twice on patterns it never actually matched:
#   · `POS docs/GENESIS.md|**r247**` — BRE reads `*` as "zero or more of the
#     preceding character", so `**r247**` degenerates to `r24`, and the gate
#     said PASS against a GENESIS with no r247 row in it.
#   · `NEG menu_functions.sh|[ "$GO" = "y" ]` — the brackets are a CHARACTER
#     CLASS, so it matched almost any line and REFUSED a correct delivery.
# ⚠️ ONE FAILED OPEN AND ONE FAILED CLOSED, WHICH IS THE POINT. A gate that
# can do either is not weaker in one direction, it is unrelated to the thing
# it claims to check.
# 🔑 AND THE ASSERTIONS ARE CONTENT, NOT PATTERNS, BY DESIGN — the operator's
# own rule is that a supersession check keys on a distinctive LINE from the
# real change. `**bold**`, `[brackets]`, `$vars`, `(parens)` and `.` are all
# ordinary characters in the text being asserted, so a regex engine here only
# ever misreads them. Nothing was gained by it and two deliveries were graded
# wrongly.
set -u

STAGE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# v1.1 — NAMED, NOT GUESSED. deploy.sh exports the file it actually extracted.
# Falling back to a glob is kept for a hand-run, but an ambiguous glob resolves
# to NOTHING rather than to whichever name sorts first, because the only thing
# this variable is used for is `rm -f`.
ARCHIVE="${LAND_ARCHIVE:-}"
if [ -z "$ARCHIVE" ]; then
  _n="$(ls "$HOME"/*_r*.tar* 2>/dev/null | wc -l)"
  if [ "$_n" = "1" ]; then ARCHIVE="$(ls "$HOME"/*_r*.tar* 2>/dev/null)"; fi
  AMBIGUOUS="$_n"
fi
FAILED=0
LANDED=""
declare -A PRE_SHA=()      # v1.2 — repo -> sha before this run touched it
declare -a COMMITTED=()    # v1.2 — repos this run committed to, in order

# ── re-exec from a private copy if we are running from inside a repo ───────
# A dtp delivery that ships a new tools/land.sh would otherwise overwrite this
# file while bash is still reading it.
if [ "${LAND_REEXEC:-}" != "1" ] && [ -d "$STAGE/../.git" ]; then
  cp "${BASH_SOURCE[0]}" /tmp/.land_running.sh 2>/dev/null || true
  LAND_REEXEC=1 exec bash /tmp/.land_running.sh "$@"
fi

# ⚠️ A FAILED GATE DOES NOT LEAVE A CLEAN WORKING TREE, and §35 already
# records that: the payload is extracted BEFORE it is verified, so a refusal
# leaves the new files in place, uncommitted. That is the safe direction — the
# alternative is a blind `git checkout -- .`, which would also discard any
# unrelated local edit. So it is REPORTED with its recovery rather than
# tidied away, because a dirty tree nobody was told about is the next
# session's mystery.
die() {
  echo "  $1"
  echo "  NOTHING WAS COMMITTED OR PUSHED. Archive and staging kept in $HOME."
  if [ -n "${repo:-}" ] && [ -d "${repo:-}/.git" ]; then
    local n; n="$(cd "$repo" && git status --porcelain | wc -l)"
    if [ "$n" != "0" ]; then
      echo "  ⚠️ $repo has $n uncommitted file(s) from the extract."
      # 🔴 v1.6 — `git reset HEAD --` FIRST, AND THE OMISSION WAS MEASURED.
      # I decided at r293 that this line was safe because a CONTENT-GATE
      # refusal stages nothing. **A COMMIT failure does** — the payload is
      # staged by then — and that is exactly what the r278 land hit. Without
      # the unstage, `git checkout -- .` copies the INDEX back into the tree
      # and restores what the operator meant to discard.
      echo "     To discard them:  cd $repo && git reset -q HEAD -- . && git checkout -- . && git clean -fd"
    fi
  fi
  FAILED=1
}


# ── PROGRESS BAR (v1.7) ──────────────────────────────────────────────────────
# 🔑 IT COUNTS REAL STAGES, IT DOES NOT ESTIMATE TIME. Operator: "this part
# always takes a long time — can we add a clever progress bar?" The honest
# version is a COUNT, because the stage list is known before the run starts:
# every CHECK named in the spec, plus a fixed tail. A timer-based bar would be
# inventing a number, and this repo has spent a day removing things that report
# confidence they do not have.
# ⚠️ IT NAMES THE STAGE. A bar alone says it is alive; the label says WHICH
# check is slow, which is the part worth knowing on a phone.
# ⚠️ NOT A TTY -> SILENT. Under a pipe the escape codes would land in a log, and
# a bar that corrupts a transcript is worse than no bar. The line is cleared
# before every durable line, so nothing printed is ever overwritten.
_PB_TOTAL=0
_PB_DONE=0

pb_init() { _PB_TOTAL="${1:-0}"; _PB_DONE=0; }

pb_step() {
  _PB_DONE=$((_PB_DONE+1))
  [ -t 1 ] || return 0
  [ "$_PB_TOTAL" -gt 0 ] || return 0
  local pct=$(( _PB_DONE * 100 / _PB_TOTAL ))
  [ "$pct" -gt 100 ] && pct=100
  local fill=$(( pct * 24 / 100 )) bar="" i=0
  while [ "$i" -lt "$fill" ]; do bar="${bar}="; i=$((i+1)); done
  [ "$fill" -lt 24 ] && bar="${bar}>"
  while [ ${#bar} -lt 24 ]; do bar="${bar}."; done
  printf '\r  [%s] %3d%%  %-26.26s' "$bar" "$pct" "${1:-}"
}

pb_clear() { [ -t 1 ] && printf '\r%*s\r' 58 ''; return 0; }

land_one() {
  local half="$1" d="$STAGE/$half" spec="$STAGE/$half/land.spec"
  echo
  echo "=============================================================="
  echo " LANDING: $half"
  echo "=============================================================="
  [ -d "$d" ]     || { die "no such half in the archive: $half"; return 1; }
  [ -f "$spec" ]  || { die "$half carries NO land.spec — refusing. A delivery with no content gate is the one you most want stopped."; return 1; }

  local rev desc markers repo="" ledger=""
  rev="$(_spec_val "$(grep -E '^REV[[:space:]]' "$spec" | head -1)" REV)"
  # r1 (OTV4TEST) — WHICH LEDGER THIS HALF APPENDS TO. Optional; absent means
  # docs/GENESIS.md, which is every mainline half ever shipped. The fork keeps
  # its own ledger (docs/GENESIS-TEST.md) so a rewire revision is never
  # mistaken for a fleet revision, and the INHERITED GENESIS.md stays frozen
  # as the lineage record it already is.
  # ⚠️ ONE LANDER, TWO LEDGERS — deliberately not a forked copy of this file.
  # A second lander drifts from this one silently, and the drift would be in
  # the tool that gates everything else.
  ledger="$(_spec_val "$(grep -E '^LEDGER[[:space:]]' "$spec" | head -1)" LEDGER)"
  [ -n "$ledger" ] || ledger="docs/GENESIS.md"
  desc="$(_spec_val "$(grep -E '^DESC[[:space:]]' "$spec" | head -1)" DESC)"
  markers="$(_spec_val "$(grep -E '^REPO[[:space:]]' "$spec" | head -1)" REPO)"
  [ -n "$rev" ]     || { die "spec carries no REV"; return 1; }
  [ -n "$desc" ]    || { die "spec carries no DESC"; return 1; }
  [ -n "$markers" ] || { die "spec carries no REPO markers"; return 1; }

  # ── find the repo rather than guess the path (WORKING_AGREEMENT §3) ──────
  # v1.22 / LAND.2 — EVERY match is collected, never the first in glob order.
  local cand ok origin_declared matches=() url
  origin_declared="$(_spec_val "$(grep -E '^ORIGIN[[:space:]]' "$spec" | head -1)" ORIGIN)"
  for cand in "$HOME"/*/; do
    [ -d "${cand}.git" ] || continue
    ok=1
    for m in $markers; do [ -f "${cand}${m}" ] || ok=0; done
    [ "$ok" = "1" ] && matches+=("${cand%/}")
  done
  if [ "${#matches[@]}" = "0" ]; then
    die "no checkout under $HOME carries all of: $markers"; return 1
  fi
  if [ -n "$origin_declared" ]; then
    # the spec names its repository: the candidate whose origin ends in it, and only that one
    local picked=() c
    for c in "${matches[@]}"; do
      url="$(git -C "$c" remote get-url origin 2>/dev/null)"
      _origin_matches "$origin_declared" "$url" && picked+=("$c")
    done
    if [ "${#picked[@]}" != "1" ]; then
      die "ORIGIN $origin_declared matches ${#picked[@]} of the ${#matches[@]} checkout(s) carrying the markers (${matches[*]}) — refusing to guess."
      return 1
    fi
    repo="${picked[0]}"
  elif [ "${#matches[@]}" != "1" ]; then
    die "AMBIGUOUS: ${#matches[@]} checkouts under $HOME carry all of [$markers]: ${matches[*]}. Add 'ORIGIN <owner/repo>' to the spec to say which (LAND.2)."
    return 1
  else
    repo="${matches[0]}"
  fi
  echo "  repo: $repo"
  echo "  rev:  $rev"

  cd "$repo" || { die "cannot cd $repo"; return 1; }

  # v1.2 — WHERE THIS REPO WAS BEFORE WE TOUCHED IT. Captured BEFORE the pull,
  # so a rollback returns it to the operator's own starting point rather than
  # to whatever origin happened to hold mid-run.
  PRE_SHA["$repo"]="$(git rev-parse HEAD 2>/dev/null)"

  # ── pull FIRST so the extract lands on true HEAD (§15) ──────────────────
  git pull --ff-only || { die "PULL FAILED — nothing extracted."; return 1; }

  # ── BASE (v1.8) — THE ARCHIVE DECLARES WHAT IT THINKS HEAD IS ───────────
  # 🔴 THE PROBLEM IT SOLVES, AND WHY THE ENUMERATED CHECKS DID NOT.
  # `tar` OVERWRITES; git never merges a payload. So an archive built against
  # an old clone silently reverts every file it carries. That has already been
  # a near-miss three times: GENESIS r209 records `docs/BACKLOG.md` about to
  # revert r207 and r208, and it was caught twice more on 2026-09-07 by a
  # human noticing a version number.
  # ⚠️ NOTHING IN THE PIPELINE REFUSED IT. The content gate greps for strings
  # the stale file still contains; `check_land_discipline` asserts a file's
  # title matches its own newest changelog entry, which a stale file does; and
  # the maps are regenerated AFTER extraction, so they document whatever
  # landed. Every gate was self-consistent and every gate passed.
  # 🔑 SO THIS DOES NOT ENUMERATE CLOBBER TYPES. The operator's framing, and it
  # is the better one: the package declares the commit it was BUILT AGAINST,
  # and the lander refuses if the repo has moved. It catches a stale clone, a
  # replayed archive, two archives cut in parallel, and — the case a
  # version-monotonic check cannot see — a stale copy of a file that carries
  # no version header at all. It never looks at the files.
  # ⚠️ COMPARED AFTER THE PULL, DELIBERATELY. Against a pre-pull HEAD a stale
  # archive would pass whenever the checkout happened to be behind too, which
  # is exactly the situation this exists for.
  # ⚠️ A MISSING `BASE` IS REFUSED, NOT SKIPPED. An absent line meaning "no
  # check" leaves every archive that forgets it silently unprotected — the
  # §36 docstring-check shape, where the gate only proved somebody wrote the
  # right words. Operator, 2026-09-07: *"I could care less if we have to
  # generate a new number to issue a correction."* Re-cut; do not warn.
  local base_declared head_now
  base_declared="$(grep -m1 '^BASE ' "$spec" | awk '{print $2}')"
  head_now="$(git rev-parse HEAD 2>/dev/null)"
  if [ -z "$base_declared" ]; then
    die "$half declares no BASE. Every half must state the commit it was built against — re-cut it. (Nothing was extracted.)"
    return 1
  fi
  # Short or full sha, either way: compare on the declared length.
  if [ "${head_now:0:${#base_declared}}" != "$base_declared" ]; then
    die "STALE ARCHIVE — $half was built against $base_declared but $repo is now at ${head_now:0:${#base_declared}}. This payload would OVERWRITE work landed since. Re-cut from a fresh clone. (Nothing was extracted.)"
    return 1
  fi
  echo "  base: $base_declared — matches HEAD"

  # ── copy the payload in, spec excluded by name ──────────────────────────
  ( cd "$d" && find . -type f ! -name land.spec -print0 \
      | tar cf - --null -T - ) | tar xf - -C "$repo" \
    || { die "EXTRACT FAILED"; return 1; }

  # ── THE CONTENT GATE: this delivery's own assertions (§15) ──────────────
  # Keyed on CONTENT, not version strings: a header bump with no real edit
  # must fail. On any flag: fail loudly, stage nothing, keep the archive.
  #
  # 🔴 v1.13 (r65) — THE DIRECTIVE VALUE IS WHITESPACE-NORMALISED, AND A `NEG`
  # THAT NAMES A MISSING FILE IS NOW REFUSED RATHER THAN PASSED.
  # These parsers stripped EXACTLY ONE SPACE (`${line#NEG }`), while the format
  # block in this very file documents COLUMN-ALIGNED examples:
  #     NEG    <path>|<literal string>        must be ABSENT after extraction
  # A spec written from the documentation therefore produced a path with leading
  # spaces, and the two directives then failed in OPPOSITE directions:
  #   · `POS` greps with `!`, so a missing file flags -> FAILS CLOSED, loudly.
  #     (Measured: this refused the r61 archive with every POS reading MISSING.)
  #   · `NEG` greps without `!` and swallows the error, so a missing file reads
  #     as "the string is absent" -> THE ASSERTION PASSES. Silently. Every time.
  # ⚠️ A `NEG` IS THE ONLY THING PROVING SUPERSEDED CODE IS GONE. A vacuous one
  # certifies that without looking, which is §15 v1.3's own finding — *"one
  # failed open and one failed closed… a gate that can do either is unrelated to
  # the thing it claims to check"* — recurring in the PARSER rather than in the
  # pattern it was written about.
  # 🔑 BOTH HALVES ARE NEEDED. Normalising alone would fix a spec written from
  # the docs and still let a TYPO'd path pass a NEG in silence; refusing a
  # missing file alone would leave the aligned form failing for a wrong reason.
  local g=0 f p val
  while IFS= read -r line; do
    val="$(_spec_val "$line" POS)"; p="${val#*|}"; f="${val%%|*}"
    if [ ! -f "$repo/$f" ]; then
      echo "  POS NAMES A FILE THAT DOES NOT EXIST: '$f'"; g=1
    elif ! grep -qF -- "$p" "$repo/$f" 2>/dev/null; then
      echo "  MISSING in $f: $p"; g=1
    fi
  done < <(grep -E '^POS[[:space:]]' "$spec")
  while IFS= read -r line; do
    val="$(_spec_val "$line" NEG)"; p="${val#*|}"; f="${val%%|*}"
    # 🔴 THE FAIL-OPEN CLOSURE. Without this branch a NEG whose path does not
    # resolve asserts NOTHING and reports PASS.
    if [ ! -f "$repo/$f" ]; then
      echo "  NEG NAMES A FILE THAT DOES NOT EXIST: '$f' — refusing rather than"
      echo "     passing an assertion that cannot have been evaluated."; g=1
    elif grep -qF -- "$p" "$repo/$f" 2>/dev/null; then
      echo "  STILL PRESENT in $f: $p"; g=1
    fi
  done < <(grep -E '^NEG[[:space:]]' "$spec")
  if [ "$g" != "0" ]; then
    die "CONTENT GATE FAILED"; return 1
  fi
  echo "  content gate: pass"

  # ⚠️ SIZED FROM THE SPEC, BEFORE ANYTHING SLOW RUNS. The CHECK count is known
  # here; the tail is fixed (maps, GENESIS, staging, commit).
  # ⚠️ `|| true`, NOT `|| echo 0`. `grep -c` PRINTS 0 AND EXITS 1 on no match,
  # so `|| echo 0` appended a SECOND zero and the arithmetic died — taking the
  # docs-only path with it. The same grep-counts-are-not-exit-codes trap the
  # fleet commands have, in a new costume.
  _nc=$(grep -c '^CHECK ' "$spec" 2>/dev/null || true); _nc=${_nc:-0}
  pb_init $(( _nc + 4 ))

  # ── THE CHECKS: EXECUTED, NOT GREPPED (v1.1) ────────────────────────────
  # WA §0.6 — "the land gate RUNS the thing and requires its output, not its
  # presence." §21 says the same one level up: a test that reads source text
  # proves nothing about runtime. Each CHECK runs with the repo as cwd, which
  # is how every checker in these trees expects to be invoked.
  # ── docs/ENV.md is regenerated BEFORE the checks (v1.24 / DOC.35) ─────────
  # It depends only on the code that just landed, so it is regenerated here, ahead of the CHECK stage: a spec that
  # lists check_env_doc in CHECK then passes on exactly the drift the regeneration fixes (the maps stay after the
  # checks for their own reasons). FAILS CLOSED: a generator that exits non-zero or leaves the file empty refuses the
  # land by name; the stale document is never staged and carried on.
  if [ -f "$repo/tests/gen_env_doc.py" ]; then
    if ! ( cd "$repo" && python3 tests/gen_env_doc.py >/dev/null 2>&1 ) || [ ! -s "$repo/docs/ENV.md" ]; then
      die "ENV DOC regeneration failed (tests/gen_env_doc.py exited non-zero or wrote nothing) — refusing."; return 1
    fi
    pb_step "env doc"; pb_clear
    echo "  env doc: regenerated"
  fi

  local nchk=0 chk
  while IFS= read -r line; do
    chk="$(_spec_val "$line" CHECK)"
    nchk=$((nchk+1))
    # 🔴 A CHECK MUST NOT INHERIT THIS DELIVERY'S OWN CONTROL VARIABLES, and
    # this was found by the CHECK stage biting its own delivery: r279's
    # `check_land_sh.py` itself invokes a land, that nested run inherited
    # `LAND_ARCHIVE` from the outer one, and on success its cleanup would have
    # `rm -f`d THE TARBALL CURRENTLY BEING LANDED. It surfaced as a check that
    # failed under the lander and passed by hand — the worst shape of red,
    # because it looks like a flaky test rather than a leak.
    # The general rule: a CHECK is arbitrary code and gets a clean slate of
    # everything that names this delivery.
    pb_step "$(basename "$chk")"
    # r13 — CHECKS NEVER TOUCH THE BOX'S STORES. A test fixture (check_standing_offer
    # S5) landed as a live open position on 2026-09-10; every checker now runs
    # with the trades and derived stores pointed at scratch files, whatever it does.
    # r109 — AND THE RESTING-ORDER STORE, the third one r13 missed (v1.15 above).
    _scratch="$(mktemp -d /tmp/land-check.XXXXXX)"
    # v5.1 (HYG.14) — THE CHECK'S TEMP FILES DIE WITH IT. /tmp is tmpfs (RAM) and
    # ~110 checkers mkdtemp without removing; TMPDIR points them into $_scratch,
    # which is removed below on both branches.
    mkdir -p "$_scratch/tmp"
    if ( cd "$repo" && env -u LAND_ARCHIVE -u LAND_STAGE TMPDIR="$_scratch/tmp" OT_TRADES_DB="$_scratch/trades.db" OT_DERIVED_DB="$_scratch/derived_store.db" OT_RESTING_DB="$_scratch/resting_orders.db" OT_SIGNAL_JOURNAL_DIR="$_scratch/signal_journal" OT_LOG_FILE="$_scratch/bot.log" OT_COUNTERFACTUAL_DIR="$_scratch/counterfactual" OT_FEED_DB="$_scratch/feed_store.db" OT_WAREHOUSE_STATE="$_scratch/warehouse_state" OT_PLAN_STATES_FILE="$_scratch/plan_states.json" OT_HEARTBEAT_FILE="$_scratch/BOT_HEARTBEAT" OT_INSTRUMENT="${OT_INSTRUMENT:-QQQ}" python3 "$chk" ) >/dev/null 2>&1; then
      rm -rf "${_scratch:?}"
      pb_clear
      echo "  check: $chk PASS"
    else
      rm -rf "${_scratch:?}"
      pb_clear
      echo "  🔴 CHECK FAILED: $chk"
      echo "     re-run it yourself:  cd $repo && python3 $chk"
      die "A DECLARED CHECK DID NOT PASS"; return 1
    fi
  done < <(grep -E '^CHECK[[:space:]]' "$spec")

  # ⚠️ A CODE HALF WITH NO CHECK IS REFUSED. Detected from the payload rather
  # than trusted to the author: if this half ships a .py outside docs/ and
  # declared nothing to run, then nothing ran, and a delivery that verified
  # nothing must not read the same as one that verified everything.
  local ncode
  ncode="$(cd "$d" && find . -name '*.py' -not -path './docs/*' | wc -l)"
  if [ "$nchk" = "0" ] && [ "$ncode" != "0" ]; then
    die "THIS HALF SHIPS $ncode .py FILE(S) AND DECLARES NO CHECK — nothing was executed. Add a CHECK line to land.spec."
    return 1
  fi
  [ "$nchk" = "0" ] && echo "  checks: NONE DECLARED (docs-only half — nothing was executed)"

  # ── generated maps regenerate INSIDE the land command (§33) ─────────────
  # Detected, not assumed: dtp carries neither, and "not applicable" must
  # never look like "passed" (the CV.1 failure).
  # ── DEL (v1.4) — A DELIVERY CAN REMOVE A FILE ───────────────────────────
  # 🔴 UNTIL NOW IT COULD NOT. A payload only ADDS or overwrites, so retiring a
  # document meant the operator deleting it by hand afterwards — outside the
  # gate, outside the commit, and outside the record. r269 needed to remove
  # eight spent thread contracts and had nowhere to say so.
  # ⚠️ ONE PATH PER DIRECTIVE, NEVER A GLOB. A pattern here would delete
  # whatever happened to match at land time, which is the same class as the
  # `ls | head -1` archive guess v1.1 removed and the BRE gate v1.3 removed.
  # ⚠️ AND A MISSING TARGET IS A REFUSAL, NOT A NO-OP. If the file is already
  # gone the spec is describing a repo that does not exist, and landing it
  # would record a deletion that never happened.
  local deleted=0
  while IFS= read -r line; do
    local target; target="$(_spec_val "$line" DEL)"
    [ -z "$target" ] && continue
    if [ ! -e "$repo/$target" ]; then
      die "DEL $target — not present in $repo. The spec describes a repo this is not."
      return 1
    fi
    git rm -q -- "$target" || { die "DEL $target failed"; return 1; }
    deleted=$((deleted+1))
  done < <(grep -E '^DEL[[:space:]]' "$spec" 2>/dev/null || true)
  [ "$deleted" -gt 0 ] && echo "  removed $deleted file(s) named by DEL"

  if [ -f "$repo/tests/gen_file_map.py" ]; then
    python3 tests/gen_file_map.py >/dev/null 2>&1 || { die "FILE MAP regeneration failed"; return 1; }
    pb_step "file map"; pb_clear
    echo "  file map: regenerated"
  fi
  if [ -f "$repo/tests/gen_write_map.py" ]; then
    python3 tests/gen_write_map.py >/dev/null 2>&1 || { die "WRITE MAP regeneration failed"; return 1; }
    pb_step "write map"; pb_clear
    echo "  write map: regenerated"
  fi

  # ── GENESIS is appended BEFORE git add, so the row ships inside the
  #    commit it describes (§35). One string becomes both.
  if [ -f "$repo/$ledger" ]; then
    printf '| **%s** | %s |\n' "$rev" "$desc" >> "$repo/$ledger"
    pb_step "GENESIS"; pb_clear
    echo "  GENESIS: appended -> $ledger"
  else
    die "$ledger does not exist in $repo — a revision absent from the ledger did not happen (§35)."; return 1
  fi

  # ── and a script confirms the bookkeeping (r183) ────────────────────────
  # It verifies exactly one GENESIS row for this rev AND that it is LAST,
  # that both maps regenerate identical, that every changed source file bumped
  # its TITLE version, and that the newest dated changelog entry AGREES with
  # that title. ⚠️ It proves the BOOKKEEPING, never the edit — the content
  # gate above is what proves that. Citing this one for both would be the
  # laundered green §18 names.
  # v1.22 / LAND.2 — THE TARGET TREE'S OWN CHECKER FIRST. The loop below asked $HOME/day_trader_pro before
  # anything else, so on control every landing into THIS tree was judged by another lineage's checker (QQQ-TEST,
  # MSG-QQQ-1024-45). A tree that ships tools/check_land_discipline.py is checked by it; the loop is only the
  # fallback for a tree that carries none, and the path consulted is printed either way.
  local ld=""
  if [ -f "$repo/tools/check_land_discipline.py" ]; then
    ld="$repo"
  else
    for cand in "$HOME"/day_trader_pro "$HOME"/*/; do
      [ -f "${cand%/}/tools/check_land_discipline.py" ] && { ld="${cand%/}"; break; }
    done
  fi
  if [ -z "$ld" ]; then
    die "check_land_discipline.py NOT FOUND — cannot confirm the bookkeeping."; return 1
  fi
  echo "  discipline checker: $ld/tools/check_land_discipline.py"
  python3 "$ld/tools/check_land_discipline.py" --repo "$repo" --rev "$rev" \
    --ledger "$ledger" \
    || { die "LAND DISCIPLINE FAILED"; return 1; }

  # ── STAGE BY NAME (v1.1) ────────────────────────────────────────────────
  # Operator's standing rule: "NEVER git add -A — stage shipped files by name",
  # written after a stray file was pushed off main. The set is the payload's
  # own file list plus the artifacts THIS command generated, and nothing else.
  local staged=0
  while IFS= read -r rel; do
    git add -- "$rel" && staged=$((staged+1))
  done < <(cd "$d" && find . -type f ! -name land.spec -printf '%P\n')

  for gen in docs/FILE_MAP.md docs/WRITE_MAP.md docs/ENV.md "$ledger"; do
    [ -f "$repo/$gen" ] && git add -- "$gen"
  done
  pb_step "staging"; pb_clear
  echo "  staged $staged payload file(s) by name"
  git commit -q -m "$rev: $desc" || { die "COMMIT FAILED"; return 1; }
  # v1.2 — COMMITTED, NOT PUSHED. Phase 2 pushes, and only if every half got
  # this far. Recording the repo and its PRE-RUN sha here is what makes the
  # rollback possible and what makes it precise: we can only undo what this
  # run did.
  COMMITTED+=("$repo")
  echo "  committed $rev locally — holding the push until every half is in"
  LANDED="$LANDED $half"
  return 0
}

if [ "$#" -eq 0 ]; then
  echo "usage: bash $0 <half> [half ...]   (halves present: $(cd "$STAGE" && ls -d */ 2>/dev/null | tr -d / | tr '\n' ' '))"
  exit 1
fi

# ── PHASE 1 — VERIFY AND COMMIT EVERY HALF, LOCALLY ────────────────────────
for half in "$@"; do
  land_one "$half" || break
done

# ── ROLLBACK — nothing reaches origin unless everything got here ───────────
# 🔑 THIS IS THE POINT OF v1.2. A half that failed leaves the others' commits
# undone, so the operator is never left reconciling a delivery that half
# happened on a remote fifteen boxes pull from.
if [ "$FAILED" != "0" ]; then
  if [ "${#COMMITTED[@]}" -gt 0 ]; then
    echo
    echo "ROLLING BACK ${#COMMITTED[@]} half/halves that had already committed —"
    echo "NOTHING WAS PUSHED, so origin is untouched."
    for r in "${COMMITTED[@]}"; do
      sha="${PRE_SHA[$r]:-}"
      if [ -n "$sha" ] && ( cd "$r" && git reset --soft "$sha" ); then
        # 🔴 v1.5 — "IN THE TREE, UNCOMMITTED" WAS TRUE AND MISLEADING. After
        # `reset --soft` the payload is still STAGED IN THE INDEX, and the
        # operator's habitual cleanup — `git checkout -- .` — copies the INDEX
        # back into the working tree, restoring exactly what he meant to
        # discard. Observed 2026-09-05: the tree read clean, the files were
        # still there, and the next attempt appended a SECOND GENESIS row for
        # the same revision. `check_land_discipline` caught the duplicate,
        # which is the only reason it was not silent.
        # ⚠️ THE ROLLBACK STAYS `--soft` — that is deliberate, so an unrelated
        # file the operator had mid-edit survives (§35). The defect was in what
        # the operator was TOLD, and in the absence of a command to act on.
        echo "  $r -> $sha (soft: the payload is STAGED, not discarded)"
        echo "     re-land as-is, or discard with:"
        echo "     cd $r && git reset -q HEAD -- . && git checkout -- . && git clean -fd"
      else
        # ⚠️ NAMED, NEVER SWALLOWED. A rollback that fails silently is worse
        # than no rollback, because the operator would believe origin and his
        # checkout agree when they do not.
        echo "  🔴 $r — COULD NOT ROLL BACK. It holds a commit that is NOT on"
        echo "     origin. Inspect it: cd $r && git log --oneline -3"
      fi
    done
  fi
  echo
  echo "INCOMPLETE. Archive and staging KEPT so nothing has to be re-downloaded."
  exit 1
fi

if [ -z "$LANDED" ]; then
  echo
  echo "INCOMPLETE — nothing landed."
  exit 1
fi

# ── PHASE 2 — PUSH, LAST, BACK TO BACK ─────────────────────────────────────
# ⚠️ TWO REMOTES ARE NOT A TRANSACTION and this does not pretend otherwise.
# What it can do is leave nothing but network between the pushes, and name the
# exact recovery if one of them fails.
PUSHED=""
for r in "${COMMITTED[@]}"; do
  if ( cd "$r" && git push -q ); then
    PUSHED="$PUSHED $r"
    echo "  pushed $r"
  else
    echo
    echo "🔴 PUSH FAILED for $r."
    [ -n "$PUSHED" ] && echo "   ALREADY ON ORIGIN:$PUSHED"
    echo "   This one is committed locally and ahead of its remote."
    echo "   Fix the remote, then:  cd $r && git push"
    echo "   ⚠️ NOT rolled back — reverting something already pushed is a"
    echo "      decision for you, not a cleanup step."
    echo
    echo "INCOMPLETE. Archive and staging KEPT."
    exit 1
  fi
done

echo
# ── delivery scaffolding cleans itself up (§27) ────────────────────────────
rm -rf "$STAGE" /tmp/.land_running.sh
if [ -n "$ARCHIVE" ]; then
  rm -f "$ARCHIVE"
  echo "ALL LANDED:$LANDED — archive and staging removed."
else
  echo "ALL LANDED:$LANDED — staging removed."
  echo "⚠️ ${AMBIGUOUS:-0} tarball(s) matched in \$HOME and none was named, so"
  echo "   NOTHING was deleted. Remove the one you landed by hand."
fi
exit 0
