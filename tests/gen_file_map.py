#!/usr/bin/env python3
"""
tests/gen_file_map.py  v4.19
v4.19 2026-10-08  OTV4TEST r261 — tools/rebuild_1m_from_last_trade.py (SEED.3) is an entry point: a hand-run repair tool, run on
      the operator's yes; its gate loads it by path, so undeclared it mapped as an orphan.
v4.18 2026-10-05  OTV4TEST r255 — THE ORIENTATION PROSE STOPS CLAIMING "Nothing flows backwards". It was false
      at HEAD (measured 10-05): strategy/management.py, strategy/condor_roll.py, analysis/entry_snapshot.py,
      analysis/gate_report.py and data/options_chain.py import downstream modules INSIDE functions. The prose
      now says the direction is the intent of module-level imports and the map lists every edge either way.
v4.17 2026-10-04  OTV4TEST r239 — tools/probe_order_dryrun.py is an entry point (run THROUGH run_with_bot_env, like the other probes).
v4.16 2026-10-04  OTV4TEST r233 — TWO NEW HAND-RUN TOOLS ARE ENTRY POINTS: tools/seed_candles_from_warehouse.py (SEED.1) and
      tools/wake_box.py (WAKE.1). Both are run from a shell by design; undeclared they printed as orphans.
v4.15 2026-10-03  OTV4TEST r216 (HYG.14) — THE LAST TWO ORPHANS ARE RULED. tools/segregate_nonrth_bars.py is declared an entry point: it is the
      08-20 repair tool for 24-hour bars landing in the RTH series, kept in case that recurs (the operator: "Sure, why not").
      execution/fill_model.py is DELETED by this delivery ("That's useless"). The map now reports no orphans.
v4.14 2026-10-03  OTV4TEST r210 (AUD.9) — tools/manifold_status.py IS AN ENTRY POINT. r202 listed it as an orphan 'for the operator
      to rule' and I called it dead; the operator, 2026-10-03: "manifold status is not 'dead'". It is his hand-run feed
      check - a tool run by hand has no importer by design. One orphan fewer; nothing else changes.
v4.13 2026-10-03  OTV4TEST r202 (MAP.6) — THE MAP'S PROSE IS COUNTED, NOT TYPED, AND NINE REAL ENTRY POINTS ARE
      DECLARED. The 10-03 audit: the drift check was green while the orientation block said "37 methods on
      ExitEngine" (55), "the eight standing checks" (210 check_*.py) and a dispatch order naming four
      strategies the code left long ago. The two numbers are now computed from the tree; the dispatch line
      points at the code instead of restating it. ENTRY_POINTS gains the agent's and the operator's tools
      (agent_watch, agent_verdict, last_session, plan_board, run_with_bot_env and its three probes,
      counter_pop). The orphan report prints EVERY orphan (it stopped at 10 of 12). Left as orphans, on
      purpose, for the operator to rule: execution/fill_model.py (never wired), tools/manifold_status.py and
      tools/segregate_nonrth_bars.py (dead).
v4.12 2026-09-27  OTV4TEST r168 — `tools/emergency_watchdog.py` DECLARED. Launched by
      deploy/install_emergency_watchdog.sh; caught red by check_map_accuracy E1 on the build.
v4.11 2026-09-24  OTV4TEST r132 — `tools/boot_sweep.py` DECLARED. Its unit now ships
      as deploy/install_boot_sweep.sh (it was hand-written on the reference box), so
      check_map_accuracy E1 sees a deploy/ unit launch it — caught red by E1 on the build.
v4.10 2026-09-24  OTV4TEST r130 — `tools/open_scan.py` DECLARED. It is launched by the
      two units deploy/install_open_scan_timer.sh writes (09:35 ready, 09:45 live);
      undeclared, it would map as an orphan and check_map_accuracy E1 would go red.

v4.9  2026-09-23  OTV4TEST r125 — `shadow/observer.py` and `shadow/trading_day.py`
      leave ENTRY_POINTS: shadow/ and its units are deleted (LVL.15 step 5).

v4.8  2026-09-20  OTV4TEST r68 — `tools/claude_boot.py` DECLARED. It is launched
      by optbot-claude-boot.service (BOX.11) and nothing imports it, so without
      the declaration it would print as an ORPHAN on every land — the noise
      this list exists to prevent — and `check_map_accuracy` E1 would refuse
      the delivery outright.
v4.7  2026-09-17  OTV4TEST r34 — ENTRY_POINTS names query.py and status.py at the
      repo root again (they moved back). An entry point is matched on PATH since
      v4.3, so a stale entry would have printed both as ORPHANS on every land.
v4.6
v4.6  2026-09-14  OTV4TEST r28 (MAP.3) — THREE UNIT-LAUNCHED SCRIPTS AND THE LANDER'S
      OWN BOOKKEEPING CHECK WERE MISSING FROM ENTRY_POINTS. `warehouse/midnight_halt.py`
      (optbot-midnight-halt.service, installed on this box at r21) printed as an
      ORPHAN on every land; `warehouse/retention_purge.py` (optbot-retention-purge,
      r27), `warehouse/self_close.py` (fleet self-close unit) and
      `tools/check_land_discipline.py` (run by tools/land.sh) were undeclared.
      Added, with the fleet-only services labelled as such. Pinned by
      tests/check_map_accuracy.py E1/E2, which read the units and land.sh.
v4.5  2026-09-11  OTV4TEST r14 — the operator readers are entry points under tools/.
v4.4  2026-09-08  OTV4TEST r1 - docs/GENESIS-TEST.md JOINS THE EXCLUSION. The
      fork keeps its own ledger and the lander appends to it BETWEEN
      regenerating this map and verifying it, which is the exact reason
      GENESIS.md was excluded. Without it the map is a function of the fork's
      own commit message and the drift canary fires on every delivery whose
      DESC names a module - it fired on r1 itself, in rehearsal, before
      anything landed.
v4.3  2026-09-07  r312 / DEP.10 - AN ENTRY POINT IS MATCHED ON PATH, AND AN
AMBIGUOUS BASENAME IS NOT EVIDENCE. Two halves, and the first alone did nothing
visible. (1) ENTRY_POINTS fell back to os.path.basename, so ANY file anywhere
named main.py read as a declared entry point - which is how the r288 stray
data/main.py rendered as "(entry point)" for a day on fifteen boxes. (2)
Removing that only MOVED it: _mentions matches basename AND stem, so the stray
inherited every mention of the real main.py and reported "referenced in
check_versions.sh, configure.sh +21" - none of which name it. The basename
match STAYS, because prose cites check_exit_executes and not its path; only the
AMBIGUOUS case changed, where two modules share a filename and a bare mention
cannot say which is meant, so the full path is required. That is exactly the
r288 shape.
v4.2  2026-09-05  r277 — "NEVER IMPORTED" AND "NEVER USED" WERE ONE BUCKET, AND
      IT HELD 130 OF 237 MODULES — 55% OF THE REPO. Operator: *"we have a file
      map for a reason. Try reading it. And if it's not useful, we might want to
      figure out why."* The `orphan or leaf` column mixed standing checks the
      land command runs BY NAME, generators the lander executes — **this file
      listed ITSELF as an orphan** — and genuinely one-shot studies. A column
      that cannot tell `check_ledger_parity` from `tine_order_study` is worse
      than no column: anyone pruning by it deletes a nightly-critical check.
      🔑 THE MISSING SIGNAL IS INVOCATION, NOT IMPORT. Everything launched from
      a shell — `land.spec CHECK` lines, unit files, devtools — is invisible to
      an import graph, so the generator now scans the repo's own `.sh`,
      `.service`, `.timer` and `.md` surface for each module's name and reports
      WHERE it is referenced. **130 unexplained becomes 29.**
      ⚠️ AND IT MATCHES THE STEM, NOT JUST THE FILENAME. A first cut required
      `.py` and put `check_exit_executes` — written so F0 could not recur — in
      the unreferenced bucket while TWO documents named it. A matcher stricter
      than the way people write reports absence where there is none.
      ⚠️ THE RESIDUAL LIST IS FOR REVIEW, NEVER FOR DELETION, and the header
      says so: `land.spec` ships inside a tarball and is never committed here,
      and `day_trader_pro`'s menu is a different repo.

v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Generates docs/FILE_MAP.md from the real import graph; fails on drift.

v4.0  2026-08-19  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THIS IS GENERATED AND NOT WRITTEN.
OTV3's FILE_MAP.md was maintained BY HAND and its own header admitted the
consequence: "Regenerate after structural changes - it is a snapshot, and it
will drift." It did. A map that looks current and is not is worse than no map:
on 2026-08-19 an entire module was nearly excised on a reading of its imports
while the map recorded its fan-in as 12 - third highest in the codebase, behind
only config.py and time_utils.

WHY IT PARSES INSTEAD OF IMPORTING.
`ast` reads the import statements without executing the module. A file that
crashes on import - and at the v4 split there were eight of them - still maps
correctly. An importing mapper would have gone blind exactly when the map was
most needed.

THE THREE FAILURES IT CATCHES, all seen for real during the v3 -> v4 port:
  1. DRIFT. The committed map disagrees with the code. Fails.
  2. BROKEN LOCAL IMPORT. A module imports something that is not there. Eight
     running imports BY HAND rather than by any check.
  3. ORPHANS. A module nothing imports and that is not an entry point. Twenty
     files were silently omitted from the port manifest; nothing errored,
     because a file that is simply absent breaks nothing until it is needed.

DELIBERATE ABSENCES ARE PRESERVED, NOT REGENERATED. The "REMOVED ON PURPOSE"
block is hand-written and carried across every regeneration: a parser cannot
anti-predictive, and without that line someone re-adds it in six months because
a strategy appears to want it.
"""

import argparse
import ast
import os
import sys

SKIP_DIRS = {".git", "__pycache__", "deploy", "reports", "blind_tapes", "venv"}
# ⚠️ AN ENTRY POINT IS NOT AN ORPHAN. A systemd service or a CLI helper SHOULD
# have no importers - that is what being an entry point means. Listing them here
# is not suppression: an orphan report that flags every service teaches the
# operator to skim it, and then a genuinely unwired module hides in the noise.
# Each of these was verified to be launched by a unit file or run by hand.
# 🔴 r312 / DEP.10 — MATCHED ON PATH ONLY. This used to fall back to
# `os.path.basename(p) in ENTRY_POINTS`, so ANY file anywhere in the tree named
# `main.py` read as a declared entry point. That is exactly how the r288 stray
# `data/main.py` rendered as `called by: (entry point)` for a day, sitting on
# fifteen boxes, indistinguishable from the real one.
# 🔑 r33 RECORDS THE INVERSE FAILURE — the first orphan run flagged 12 modules
# of which only 2 were real — and this is the SAME checker failing the other
# way. A false orphan wastes an investigation; a HIDDEN one wastes nothing and
# costs everything, because nobody investigates a green.
# ⚠️ EVERY ENTRY MUST THEREFORE BE A REPO-RELATIVE PATH. A bare `main.py` here
# means the ROOT main.py and nothing else; a module under a package needs its
# full path, as `shadow/observer.py` and `data/candle_feed.py` already do.
ENTRY_POINTS = {
    # operator / CLI
    "main.py", "query.py", "status.py", "tools/debug_status.py",
    "tools/eod_summary.py", "tools/stress_theta_bleed.py",      # r14: root cleanup
    # systemd-launched services
    "data/candle_logger.py",       # candle-logger.service
    "warehouse/s3_push.py",        # s3-push.service
    "data/candle_feed.py",         # candle-feed.service
    # r28 — the box's own timers (installed here, BOX.2/BOX.4) and a fleet unit.
    # ⚠️ candle-logger and s3-push above are FLEET services: this box
    # has none of them installed (BOX.1). Declared because the units ship in deploy/.
    "warehouse/midnight_halt.py",  # optbot-midnight-halt.service (this box, r21)
    "warehouse/retention_purge.py",  # optbot-retention-purge.service (this box, r27)
    "warehouse/self_close.py",     # self-close unit (fleet only; not on this box)
    # run by tools/land.sh on every land
    "tools/check_land_discipline.py",
    # r68 — optbot-claude-boot.service (this box, BOX.11). Raises an agent
    # session in tmux at boot; nothing imports it, which is what an entry
    # point IS.
    "tools/claude_boot.py",
    "tools/open_scan.py",          # r130 — launched by deploy/install_open_scan_timer.sh
    "tools/boot_sweep.py",         # r132 — launched by deploy/install_boot_sweep.sh
    "tools/emergency_watchdog.py", # r168 — launched by deploy/install_emergency_watchdog.sh
    # r202 — run by the agent session or the operator, found unlisted by the 10-03 audit
    "tools/agent_watch.py",        # the session's alert Monitor (docs/HANDOFF.md)
    "tools/agent_verdict.py",      # the agent's observe-only loss verdicts (AGT.2)
    "tools/last_session.py",       # the handoff digest every session reads first
    "tools/plan_board.py",         # devtools menu
    "tools/run_with_bot_env.py",   # the operator's one allow rule for credentialed probes (r176)
    "tools/probe_aux_streams.py",  # run THROUGH run_with_bot_env
    "tools/probe_candle_depth.py", # run THROUGH run_with_bot_env
    "tools/probe_order_dryrun.py", # r239 — run THROUGH run_with_bot_env; dry_run=True only
    "tools/feed_capabilities.py",  # run THROUGH run_with_bot_env
    "warehouse/counter_pop.py",    # fleet S3 counter repair CLI (WA 38.3 DELETE.1)
    "tools/manifold_status.py",    # r210 — the operator's hand-run feed check ("is the fire hose connected"); NOT dead (his correction, 2026-10-03)
    "tools/segregate_nonrth_bars.py",  # r216 — a hand-run REPAIR tool (moves overnight bars out of the RTH series); kept by ruling 2026-10-03
    "tools/seed_candles_from_warehouse.py",  # r233 SEED.1 — the operator's yes to backfilling a new box's feed from the warehouse (2026-10-04)
    "tools/rebuild_1m_from_last_trade.py",  # r261 SEED.3 — rebuilds MISSING RTH 1m bars from the warehouse's last_trade; --apply on his yes
    "tools/wake_box.py",               # r233 WAKE.1 — QQQ-TEST wakes / stops SPX-TEST, by his grant (2026-10-04)
    # CLI helpers, run by hand or by a script
    "analysis/get_orb_range.py",
    "utils/check_sdk.py",
}
ABSENT_MARK = "<!-- REMOVED-ON-PURPOSE -->"

# ── r277 — "NEVER IMPORTED" AND "NEVER USED" ARE NOT THE SAME FACT ──────────
# 🔴 THE MAP PUT 130 OF 237 MODULES — 55% OF THE REPO — IN ONE BUCKET LABELLED
# "orphan or leaf", and that bucket held three unrelated things:
#   · standing checks the land command runs BY NAME through `land.spec CHECK`;
#   · generators the land command executes — `gen_file_map.py` listed ITSELF
#     as an orphan;
#   · genuinely one-shot studies run once and never referenced again.
# ⚠️ A COLUMN THAT CANNOT TELL `check_ledger_parity` FROM `tine_order_study` IS
# WORSE THAN NO COLUMN: anyone pruning by it would delete a nightly-critical
# check. The operator's question was exactly this — "what the hell do we have a
# useless file map for?"
#
# 🔑 THE MISSING SIGNAL IS INVOCATION, NOT IMPORT. Everything that runs from a
# shell — `land.spec CHECK` lines, `devtools.sh`, unit files, the conductor's
# subprocess calls — is invisible to an import graph. So the generator now also
# scans the repo's own non-Python surface for each module's filename and
# reports WHERE it is referenced.
# ⚠️ AND IT IS HONEST ABOUT WHAT IT STILL CANNOT SEE: `land.spec` files ship
# inside tarballs and are never committed, and `day_trader_pro`'s devtools menu
# is a different repo. A module referenced ONLY from there still reads as
# unreferenced here, and the map says so rather than implying otherwise.
MENTION_EXT = (".sh", ".service", ".timer", ".md", ".txt")
MENTION_SKIP_DIRS = {".git", "__pycache__", "reports", "blind_tapes", "venv"}


def _mentions(root: str, names: set) -> dict:
    """{module path: [files that NAME it]} across the repo's shell/docs surface.

    ⚠️ A MENTION IS EVIDENCE, NOT PROOF. `docs/TRADES.md` citing a study is the
    map's own stated contract — "a number in a strategy file should be
    traceable to a tool in here" — so a cited study is live evidence even
    though nothing imports it. An UNCITED, UNIMPORTED module is the thing the
    orphan report was always meant to surface, and it could not.
    """
    hits = {n: set() for n in names}
    # 🔴 r312 / DEP.10, SECOND HALF. A BARE BASENAME IS ONLY EVIDENCE WHEN IT
    # IS UNIQUE. Removing the ENTRY_POINTS basename fallback alone did NOT
    # surface the r288 stray: `data/main.py` simply moved from "(entry point)"
    # to "referenced in check_versions.sh, configure.sh, +21" — none of which
    # name `data/main.py`. They name `main.py`, and this matcher takes the
    # BASENAME and the STEM, so the stray inherited every mention of the real
    # file. The stem `main` is worse still: it matches `__main__` and `main()`.
    # ⚠️ THE BASENAME MATCH IS NOT A BUG AND IS NOT BEING REMOVED — prose cites
    # `check_exit_executes`, not `tests/check_exit_executes.py`, and this
    # comment's own history records a stricter matcher reporting absence where
    # there was none. What changes is only the AMBIGUOUS case: when two files
    # share a basename, a bare mention cannot say which is meant, so it is
    # evidence for NEITHER and the full path is required.
    # 🔑 That is precisely the r288 shape — a duplicate appearing beside a real
    # file — and it is the only case where the loose match hides something.
    _by_base: dict = {}
    for n in names:
        _by_base.setdefault(os.path.basename(n), []).append(n)
    _ambiguous = {b for b, v in _by_base.items() if len(v) > 1}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in MENTION_SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(MENTION_EXT):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            # FILE_MAP names every module by construction; counting itself
            # would make every module look referenced.
            # 🔴 GENESIS IS EXCLUDED BECAUSE THE LAND COMMAND APPENDS TO IT
            # BETWEEN REGENERATING THIS MAP AND VERIFYING IT. A revision whose
            # DESC happens to name a module would add a mention the verify pass
            # sees and the generate pass did not — the map becomes a function
            # of its own commit message and the drift canary fires on every
            # such delivery. Caught in the sandbox on this revision, whose own
            # DESC names four modules.
            # FILE_MAP/WRITE_MAP name every module by construction; counting
            # them would make everything look referenced.
            # OTV4TEST r1 — GENESIS-TEST.md is the FORK'S ledger and the lander
            # appends to it for exactly the same reason, so it needs exactly the
            # same exclusion. Without it this map became a function of the
            # fork's own commit message and the drift canary fired on r1 itself
            # — caught in rehearsal, by the gate, before anything landed.
            if rel in ("docs/FILE_MAP.md", "docs/WRITE_MAP.md",
                       "docs/GENESIS.md", "docs/GENESIS-TEST.md"):
                continue
            try:
                text = open(full, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for n in names:
                base = os.path.basename(n)
                stem = base[:-3] if base.endswith(".py") else base
                # ⚠️ MATCH THE STEM TOO. Prose cites a checker as
                # `check_exit_executes`, without the extension — a first cut
                # required `.py` and put that file, written so F0 could not
                # recur, in the unreferenced bucket while two documents named
                # it. A matcher stricter than the way people write is a
                # matcher that reports absence where there is none.
                if base in _ambiguous:
                    # Two or more modules share this filename: only a mention
                    # of the FULL path can be evidence for either of them.
                    if n in text:
                        hits[n].add(rel)
                elif base in text or stem in text:
                    hits[n].add(rel)
    return hits


def _walk(root):
    for r, d, f in os.walk(root):
        d[:] = [x for x in d if x not in SKIP_DIRS and not x.startswith(".")]
        for x in f:
            if x.endswith(".py"):
                yield os.path.relpath(os.path.join(r, x), root)


def _local_imports(path, root, known_files):
    """Local modules this file imports. Parsed, never executed."""
    try:
        tree = ast.parse(open(os.path.join(root, path), encoding="utf-8").read())
    except Exception:                                          # noqa: BLE001
        return set(), True                                     # unparseable
    out = set()
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            mods = [node.module]
            # ⚠️ `from <package> import <module>` - the MODULE is the imported
            # NAME, not `node.module`. Reading only `node.module` resolves the
            # PACKAGE and misses the dependency entirely, so a file imported
            # this way reports as an ORPHAN.
            # Found 2026-08-19: `from strategy import credit_vertical as cv`
            # in BOTH trend_credit_spread.py and iron_condor_strategy.py. The
            # module is live - `cv.pop`, `cv.bars_left` - and TC.6 traded with
            # it four times on 08-17. The checker called it unwired, and an
            # orphan report that accuses live modules is one nobody reads.
            mods += [node.module + "." + a.name for a in node.names]
        for m in mods:
            # ⚠️ RESOLVE TO A REAL FILE OR DROP IT. A first pass turned a bare
            # `import analysis` into "analysis.py" and reported it as a broken
            # import - a PACKAGE is not a module, and a checker that invents
            # missing files teaches the operator to ignore its own output.
            cand = m.replace(".", "/") + ".py"
            if cand in known_files:
                out.add(cand)
                continue
            pkg_init = m.replace(".", "/") + "/__init__.py"
            if pkg_init in known_files:
                out.add(pkg_init)
    return out, False


def build(root):
    files = sorted(_walk(root))
    pkgs = {p.split("/")[0] for p in files if "/" in p}
    pkgs |= {p for p in files if "/" not in p}
    calls, unparsed = {}, []
    for p in files:
        c, bad = _local_imports(p, root, set(files))
        calls[p] = {x for x in c if x != p}
        if bad:
            unparsed.append(p)
    called_by = {p: set() for p in files}
    broken = []
    for p, cs in calls.items():
        for c in cs:
            if c in called_by:
                called_by[c].add(p)
            else:
                broken.append((p, c))
    return files, calls, called_by, broken, unparsed


def _exit_engine_methods(root) -> int:
    """r202: COUNTED, not typed. The map said 37 for months while the class grew to 55."""
    try:
        tree = ast.parse(open(os.path.join(root, "execution", "exit_engine.py"), encoding="utf-8").read())
        for n in tree.body:
            if isinstance(n, ast.ClassDef) and n.name == "ExitEngine":
                return sum(isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) for b in n.body)
    except Exception:                                           # noqa: BLE001
        pass
    return 0


def _standing_checks(root) -> int:
    """r202: COUNTED. The map said "eight" - the count is every tests/check_*.py."""
    try:
        return sum(1 for f in os.listdir(os.path.join(root, "tests"))
                   if f.startswith("check_") and f.endswith(".py"))
    except OSError:
        return 0


def render(root, files, calls, called_by, broken, unparsed, absent_block):
    # Computed once per render; the scan is a few dozen small files.
    MENTIONS = _mentions(root, set(files))
    L = []
    L.append("# FILE_MAP - every module, what it calls, and what calls it")
    L.append("")
    L.append("**GENERATED by `tests/gen_file_map.py` from the real import graph.**")
    L.append("Do not edit by hand: the generator runs inside the land command and")
    L.append("the canary fails on drift (WORKING_AGREEMENT 33).")
    L.append("")
    L.append(f"{len(files)} Python modules across {len({p.split('/')[0] for p in files if '/' in p})} local packages.")
    L.append("")
    # ── r277 — THE THREE WAYS A MODULE IS REACHED ──────────────────────────
    _imp = sum(1 for p in files if called_by.get(p))
    _ep = sum(1 for p in files if not called_by.get(p)
              and (p in ENTRY_POINTS))
    _ref = sum(1 for p in files if not called_by.get(p)
               and not (p in ENTRY_POINTS)
               and MENTIONS.get(p))
    _none = len(files) - _imp - _ep - _ref
    L.append(f"**Reached by:** {_imp} imported · {_ep} declared entry points · "
             f"{_ref} referenced from a script, unit or doc but never imported "
             f"· **{_none} by nothing here**.")
    L.append("")
    L.append("⚠️ The last group is a REVIEW LIST, not a delete list. A")
    L.append("`land.spec CHECK` line ships inside a tarball and is never")
    L.append("committed here, and `day_trader_pro`'s devtools menu is a")
    L.append("different repo — a module run from either still reads as")
    L.append("unreferenced. Confirm before removing anything.")
    L.append("")
    # ── orientation, emitted every run (v4.1, 2026-08-20) ──────────────────
    # ⚠️ THIS BELONGS IN THE GENERATOR, NOT THE OUTPUT. A hand-edit to
    # docs/FILE_MAP.md vanishes on the next run - correct behaviour for a
    # generated file, and the reason this text lives here instead.
    L.append("## How to read this repo - orientation")
    L.append("")
    L.append("**The one-way flow:** `data/` fetches -> `analysis/` describes ->")
    L.append("`strategy/` decides -> `execution/` acts -> `database/` records.")
    L.append("That is the intended direction of MODULE-LEVEL imports, and it is what")
    L.append("let v3's defects be isolated. ⚠️ It is not absolute: some modules import")
    L.append("downstream INSIDE a function (e.g. strategy/management.py ->")
    L.append("execution.exit_engine); every such edge is listed below like any other.")
    L.append("")
    L.append("**Where the decisions live:**")
    L.append("")
    L.append("- `main.py::attempt_new_entry` - the dispatch chain. **Order is")
    L.append("  load-bearing; read it there.** This map does not restate it:")
    L.append("  the line that did named four strategies in an order the code")
    L.append("  left long ago (r202).")
    L.append("- `strategy/<name>.py` - one file per setup, each with a `GATES`")
    L.append("  dict naming every constant SELECTION / FOUNDATIONAL /")
    L.append("  FEASIBILITY. **Foundational conditions are tested inline")
    L.append("  against no constant** - the safest form, since there is nothing")
    L.append("  to relax even by mistake.")
    L.append(f"- `execution/exit_engine.py` - {_exit_engine_methods(root)} methods on `ExitEngine`.")
    L.append("  ⚠️ **F0: a function inserted at column 0 above a method bisected")
    L.append("  this class and every intraday exit became dead code for seven")
    L.append("  revisions behind a green board.** `check_exit_executes.py`")
    L.append("  exists so it cannot happen silently again.")
    L.append("- `analysis/market_state.py` - the structural state assembly.")
    L.append("  **Carries the vocabulary, classifies nothing.**")
    L.append("")
    L.append(f"**Where the evidence lives:** `tests/` holds {_standing_checks(root)} standing")
    L.append("checks (`check_*.py`, all run by `tools/boot_sweep.py` at boot)")
    L.append("plus the studies that produced every threshold in")
    L.append("`docs/TRADES.md`. **A number in a strategy file should be")
    L.append("traceable to a tool in here.**")
    L.append("")
    L.append("## Fan-in leaderboard - widest blast radius")
    L.append("")
    L.append("Change these with the most care; a break here reaches everything downstream.")
    L.append("")
    L.append("| module | imported by | some of the importers |")
    L.append("|---|---|---|")
    for p in sorted(files, key=lambda x: -len(called_by[x]))[:12]:
        n = len(called_by[p])
        if not n:
            continue
        some = ", ".join(sorted(os.path.basename(x) for x in called_by[p])[:4])
        L.append(f"| `{p}` | {n} | {some} |")
    L.append("")
    L.append("## Every module")
    L.append("")
    for p in files:
        L.append(f"### `{p}`")
        c = sorted(calls[p])
        b = sorted(called_by[p])
        L.append(f"- **calls:** {', '.join('`'+x+'`' for x in c) if c else '(none)'}")
        if b:
            L.append(f"- **called by:** {', '.join('`'+x+'`' for x in b)}")
        elif p in ENTRY_POINTS:
            L.append("- **called by:** (entry point)")
        elif MENTIONS.get(p):
            # 🔑 REFERENCED WITHOUT BEING IMPORTED — a check the lander runs, a
            # script a unit file launches, a study a doc cites. This is the
            # distinction that makes the orphan column usable.
            where = sorted(MENTIONS[p])[:4]
            more = f" +{len(MENTIONS[p]) - 4}" if len(MENTIONS[p]) > 4 else ""
            L.append("- **called by:** (not imported) — referenced in "
                     + ", ".join("`" + w + "`" for w in where) + more)
        else:
            # ⚠️ NOW IT MEANS SOMETHING: no importer, and its name appears in no
            # script, unit, or document in this repo. ⚠️ IT MAY STILL BE RUN
            # FROM day_trader_pro's MENU OR FROM A `land.spec CHECK` LINE, which
            # ships in a tarball and is never committed here — so this is a
            # candidate for review, never an instruction to delete.
            L.append("- **called by:** (nothing — no importer and no mention "
                     "in any script, unit or doc here)")
        L.append("")
    L.append(absent_block.rstrip())
    # ⚠️ NORMALISE THE TAIL OR THE MAP DRIFTS FROM ITSELF. `render` appended a
    # newline to a block that already ended with one, and `_absent_block`
    # re-read that grown tail on the next run - so the file gained a blank line
    # EVERY regeneration and `--check` reported drift immediately after a
    # successful write. The checker was right and the writer was wrong.
    return "\n".join(L).rstrip() + "\n"


def _absent_block(dst):
    """Carry the hand-written REMOVED-ON-PURPOSE section across regenerations."""
    default = (ABSENT_MARK + "\n"
               "## Removed on purpose\n\n"
               "Hand-written. **Preserved across regenerations** - a parser cannot\n"
               "know WHY something is absent, and without that a dropped module gets\n"
               "re-added by someone who finds a strategy that appears to want it.\n\n"
               "| module | removed | why |\n|---|---|---|\n"
               "| `analysis/conviction_integrator.py` | v4 split | Confirmatory by construction: a leaky integrator over argmax agreement is only confident once winning has persisted. |\n"
               "⚠️ `analysis/volatility_engine.py` and `analysis/trend_engine.py` were\n"
               "dropped at first and **RESTORED**: they are structure providers, not\n"

               "stack. They were cut on location and name rather than on what they\n"
               "compute. See `docs/INHERITED_FINDINGS.md`.\n")
    if not os.path.exists(dst):
        return default
    txt = open(dst, encoding="utf-8").read()
    return txt[txt.index(ABSENT_MARK):] if ABSENT_MARK in txt else default


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="docs/FILE_MAP.md")
    ap.add_argument("--check", action="store_true",
                    help="fail on drift instead of writing")
    a = ap.parse_args(argv[1:])

    files, calls, called_by, broken, unparsed = build(a.root)
    dst = os.path.join(a.root, a.out)
    text = render(a.root, files, calls, called_by, broken, unparsed,
                  _absent_block(dst))

    fail = False
    if broken:
        print(f"  BROKEN LOCAL IMPORTS: {len(broken)}")
        for p, c in broken[:10]:
            print(f"    {p} imports {c} - which does not exist")
        fail = True
    if unparsed:
        print(f"  UNPARSEABLE: {len(unparsed)}")
        for p in unparsed[:6]:
            print(f"    {p}")
        fail = True
    orphans = [p for p in files if not called_by[p]
               and p not in ENTRY_POINTS
               and os.path.basename(p) not in ENTRY_POINTS
               and not p.endswith("__init__.py")
               and not p.startswith("tests/")]
    if orphans:
        print(f"  ORPHANS (nothing imports them, not entry points): {len(orphans)}")
        for p in orphans:                       # r202: ALL of them - it printed 10 of 12
            print(f"    {p}")

    if a.check:
        cur = open(dst, encoding="utf-8").read() if os.path.exists(dst) else ""
        if cur != text:
            print("  DRIFT: docs/FILE_MAP.md does not match the code.")
            print("     Regenerate before shipping - the land command does this")
            print("     automatically; a hand-landed change did not.")
            fail = True
        else:
            print("  file map is current")
    else:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        open(dst, "w", encoding="utf-8").write(text)
        print(f"  wrote {a.out}: {len(files)} modules, "
              f"{sum(len(v) for v in calls.values())} local edges")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
