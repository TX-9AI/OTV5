#!/usr/bin/env python3
"""
tests/scrub_headers.py — v4.1

RESET EVERY PORTED FILE'S HEADER TO 4.0. TOUCH NOTHING ELSE.

v4.1  2026-08-29  r182 — THIS FILE HAD NOT PARSED SINCE r65, AND THE BUMPER
      THAT BROKE IT WROTE ITS CHANGELOG INTO A COMMENT. r65's header pass
      matched the `v4.3` inside the ILLUSTRATIVE EXAMPLE in _autodescribe()
      — a comment line that exists precisely to show what a
      "path vX.Y date TITLE" header looks like — mistook it for this
      file's own version line, spliced a four-line changelog block into the
      middle of it, and left the tail (`  2026-08-15  AUDIT A2: ...`)
      stranded at column 2. The real header at the top of this file was
      never touched and still read v4.0, so the entry described a version
      the file did not claim, in a place Python could not parse. The
      example line is restored verbatim from dfe5910; the body is unchanged.
  🔴 WHY IT SURVIVED SIX DAYS: `gen_file_map.py --check` reported it
      (`UNPARSEABLE: 1`) and returned rc=1 on every run since 2026-08-22 —
      but the land gate globs `tests/check_*.py`, and this generator is
      neither globbed nor rc-checked there. The detector was working; the
      gate was not reading it. Same shape as WA 21: a check that existed
      and proved nothing because nothing executed its verdict.
  ⚠️ THE FAILURE CLASS FOR ANY FUTURE HEADER TOOL: a version-bumping
      script cannot tell a file's OWN header from a header QUOTED as an
      example, and this repo's docs are full of quoted headers by design.
      Anchor on POSITION (the module docstring) or on an explicit marker,
      never on a `vX.Y` pattern found anywhere in the file. WA 24 already
      requires a scripted edit to assert its anchor matched; it must also
      assert it matched the RIGHT one, and re-parse the file afterwards.
      ⚠️ AND BUILD THE STRING BEFORE OPENING THE FILE. Writing this very
      entry, an encoding error fired between `open(p,'w')` and the write:
      the truncate had already happened, so the file went to ZERO BYTES
      and the traceback read like a failed edit rather than a destroyed
      one. Recovered with `git checkout`. Encode first, write second.

v4.0  2026-08-19

    python3 tests/scrub_headers.py --src <otv3> --dst <otv4> --list <manifest>

────────────────────────────────────────────────────────────────────────────
WHAT IT REMOVES AND WHAT IT MUST NOT
────────────────────────────────────────────────────────────────────────────
**REMOVES:** the OTV3 CHANGELOG — the stacked `vX.Y  <date>  <TITLE>` blocks at
the top of each file. OTV4 starts at 4.0 with a fresh history.

⚠️ **KEEPS, ABSOLUTELY: EVERY IN-BODY COMMENT.** Lines like *"this crash-looped
NFLX every 15 seconds"*, *"the veto window and the confirmation window were the
same window"*, *"0 is the permissive answer"* are **the reason the code is the
way it is.** They are not history; they are the guardrails. Stripping them would
discard exactly the knowledge OTV4 exists to inherit — and the next engineer
would rediscover each defect the expensive way.

⚠️ **KEEPS the descriptive first line.** `"analysis/liquidity_mapper.py — named
pools, sections, ladder"` says what the module IS. That survives; only the
version history below it is replaced.

────────────────────────────────────────────────────────────────────────────
WHY A TOOL AND NOT A `sed`
────────────────────────────────────────────────────────────────────────────
Four distinct header shapes exist in OTV3:
  1. `\"\"\"` · `path  vX.Y  date  TITLE` · changelog
  2. `\"\"\"` · `path  addendum vX.Y (see below); original header follows.` · changelog
  3. `\"\"\"` · `path  Description.` · prose · `vX.Y date ...` further down
  4. `#!/bin/bash` · `# ===` · `# path  vX.Y`

A regex that handles three of them silently mangles the fourth. **Every write is
verified: the file must still parse, and the body byte-count must be unchanged.**
"""

import argparse
import ast
import os
import re
import shutil
import sys

VER_LINE = re.compile(r"^\s*#?\s*v[\d]+[\.\-][\w\.]*\s+\d{4}-\d{2}-\d{2}")
VER_ANY = re.compile(r"\bv\d+\.\d+\b")


def _split_py(text):
    """(header_lines, body_lines) - leading module docstring OR comment block.

    Two shapes were missed on the first pass and passed through unscrubbed,
    keeping their v3 version strings: a shebang followed by a DOCSTRING (the
    shell splitter grabbed the shebang and stopped), and a .py file whose header
    is a COMMENT BLOCK rather than a docstring. Eight files.
    A splitter that silently declines to recognise a header is a version that
    never gets aligned - and nothing fails to announce it.
    """
    lines = text.split("\n")
    i = 1 if lines and lines[0].startswith("#!") else 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return [], lines
    if lines[i].lstrip().startswith("#"):
        j = i
        while j < len(lines) and (lines[j].lstrip().startswith("#")
                                  or not lines[j].strip()):
            j += 1
        return lines[:j], lines[j:]
    q = None
    for cand in (chr(34) * 3, chr(39) * 3):
        if lines[i].lstrip().startswith(cand):
            q = cand
            break
    if q is None:
        return [], lines
    # A docstring may OPEN AND CARRY CONTENT ON THE SAME LINE:
    #   """shadow/trading_day.py v1.0 - standalone trading-day check
    # If the closing quote is also on that line it is a one-liner; otherwise the
    # scan must start BELOW it. Starting at the opening line matched the opener
    # itself, cut the header one line early, and left prose outside the
    # docstring - two files stopped parsing. The write-verification caught it;
    # nothing shipped.
    if lines[i].count(q) >= 2:
        return lines[:i + 1], lines[i + 1:]
    for k in range(i + 1, len(lines)):
        if q in lines[k]:
            return lines[:k + 1], lines[k + 1:]
    return [], lines


def _split_sh(text):
    """(header_lines, body_lines) — leading `#` comment block after any shebang."""
    lines = text.split("\n")
    i = 1 if lines and lines[0].startswith("#!") else 0
    j = i
    while j < len(lines) and (lines[j].startswith("#") or not lines[j].strip()):
        j += 1
    return lines[:j], lines[j:]


# ⚠️ DESCRIPTIONS ARE WRITTEN, NOT SCRAPED. Auto-extraction was tried and
# produced "AUDIT A2: THE INPUT COULD NOT" for the liquidity mapper — a
# CONTINUATION LINE of a changelog entry. OTV3's changelog blocks wrap across
# lines, so any first-line heuristic eventually lifts prose out of the middle of
# a bug report and presents it as what the module does. **A header describing
# the last defect is worse than an empty one.**
# Anything not listed here gets a BLANK description and is reported, so the gap
# is visible rather than filled with garbage.
DESCRIPTIONS = {
    # analysis — structure, levels, geometry. OTV4's raw material.
    "analysis/liquidity_mapper.py": "Named liquidity pools, session sections, and the 3-deep ladder.",
    "analysis/liquidity_ledger.py": "Per-level touch / hold / breach accounting across the session.",
    "analysis/level_grade.py": "Grades a level by TYPE with a rung discount; nearest graded pool.",
    "analysis/pitchfork.py": "Andrews pitchfork / containment envelope construction.",
    "analysis/pitchfork_lifecycle.py": "Fork birth, persistence and invalidation.",
    "analysis/pitchfork_observer.py": "Records fork state per tick for later analysis.",
    "analysis/structure_analyzer.py": "Swing detection and support/resistance mapping.",
    "analysis/orb_engine.py": "Opening range: establish, latch, arm, expire.",
    "analysis/get_orb_range.py": "Opening-range accessor with the date filter.",
    "analysis/gap_measure.py": "Overnight gap, measured rather than inherited as an ATR spike.",
    "analysis/tenor_select.py": "Front / weekly / monthly expiry selection with the collision rule.",
    "analysis/tenor_publish.py": "Publishes narrow ATM bands for the auxiliary tenors.",
    "analysis/chain_snapshot.py": "Archives the full option chain per snapshot to disk.",
    "analysis/entry_snapshot.py": "Captures the decision-time context of an entry.",
    "analysis/signal_journal.py": "Structured event journal for every decision and refusal.",
    "analysis/rejection_ledger.py": "What a gate REFUSED — the other half of every measurement.",
    "analysis/trade_readiness.py": "Pre-trigger confluence logging and arming state.",
    # data — feed and market context
    "data/candle_feed.py": "DXLink candle feed, store, maintenance window, extended hours.",
    "data/market_data.py": "Frame accessors over the candle store, with staleness refusal.",
    "data/data_cache.py": "Short-lived cache in front of the store.",
    "data/options_chain.py": "Chain construction, strike selection, chain_subs publication.",
    "data/gex_data.py": "Gamma exposure, call/put walls, pin, from the live chain.",
    "data/macro_data.py": "VIX and macro context snapshot.",
    "data/tasty_client.py": "TastyTrade session and REST wrapper.",
    "data/candle_logger.py": "Per-session OHLC archival.",
    # execution — the measured winners
    "execution/exit_engine.py": "Exit decisions: trails, structure stops, theta bleed, time.",
    "execution/position_manager.py": "Open-position tracking, pricing and lifecycle.",
    "execution/entry_engine.py": "Entry dispatch and slot assignment.",
    "execution/limit_ladder.py": "Escalating limit ladder for fills.",
    "execution/order_confirm.py": "Order acknowledgement and fill confirmation.",
    "execution/fill_model.py": "Paper fill modelling.",
    "execution/broker_reconcile.py": "Reconciles local state against the broker.",
    "execution/tick_size.py": "Venue tick-size rules per symbol and price band.",
    # strategy — constructions kept, triggers rebuilt in Phase 2
    "strategy/base_strategy.py": "Signal dataclass and the strategy interface.",
    "strategy/structure.py": "Derives trade structure from PERSISTED fields, never a flag.",
    "strategy/credit_vertical.py": "Credit vertical construction, liquidity and POP helpers.",
    "strategy/orb_strategy.py": "Opening-range break and retest. Label-agnostic by design.",
    "strategy/continuation_strategy.py": "Trend continuation. TRIGGER REBUILT IN PHASE 2.",
    "strategy/trend_credit_spread.py": "ORB-bounded credit spread. TRIGGER REBUILT IN PHASE 2.",
    "strategy/iron_condor_strategy.py": "Two-leg condor with ladder. TRIGGER REBUILT IN PHASE 2.",
    "strategy/condor_roll.py": "Condor roll handling.",
    "strategy/butterfly_strategy.py": "Butterfly construction and debit ceiling.",
    "strategy/sweep_reversal_strategy.py": "Liquidity sweep reversal. TRIGGER REBUILT IN PHASE 2.",
    # risk, database, warehouse, utils
    "risk/risk_manager.py": "Position sizing, loss caps, halt state.",
    "risk/session_guard.py": "RTH gating and session boundaries.",
    "risk/setup_scorer.py": "Journaling and gate plumbing. FACTOR SET REMOVED - see VISION.",
    "database/trade_logger.py": "Trade schema, entry/exit logging, migrations.",
    "warehouse/s3_push.py": "Pushes collected data to S3 and verifies what landed.",
    "utils/time_utils.py": "Timezone, RTH session helpers, market-clock utilities.",
    "utils/math_utils.py": "Shared numeric helpers.",
    "utils/blindness_latch.py": "Latches and alerts when the bot is flying blind.",
    "utils/mem_trace.py": "Memory tracing for the OOM investigations.",
    "utils/check_sdk.py": "Verifies the broker SDK surface at startup.",
    # provisioning — unattended install
    "setup_ec2.sh": "EC2 instance provisioning for a fleet box.",
    "bootstrap.example.sh": "Worked example of an unattended box bootstrap.",
    "install.sh": "Installs the bot service on a box.",
    "install_candle_feed.sh": "Installs the candle-feed service.",
    "install_candle_logger_timer.sh": "Installs the candle-logger timer.",
    "install_eod_bot.sh": "Installs the EOD bot.",
    "install_eod_timer.sh": "Installs the EOD timer.",
    "install_s3_push_timer.sh": "Installs the S3 push service and timer.",
    "install_tooling.sh": "Installs shared tooling onto a box.",
    "configure.sh": "Per-box configuration.",
    "harden_hosts.sh": "Host hardening for a fleet box.",
    "check_versions.sh": "Header/canary/parity verification before shipping.",
    # --- ROUND 2: files omitted from the first manifest ------------------
    # ⚠️ THE FIRST MANIFEST WAS BUILT FROM THE DESCRIPTIONS DICT, so anything
    # not described simply did not port - silently, with nothing erroring.
    # 25 files were missing including `main.py` and `config.py`: an entry point
    # and every constant. The canary rebuild found it on its first look, which
    # is the argument for building the canary before trusting the port.
    "main.py": "Tick loop, context assembly, strategy dispatch. GATES STRIPPED - see ROADMAP Phase 2.",
    "config.py": "Every constant, threshold and env override.",
    "notifications/alert_manager.py": "Alert routing and de-duplication.",
    "notifications/telegram_sender.py": "Telegram delivery.",
    "shadow/observer.py": "Shadow observer: records primitives without trading them.",
    "shadow/primitives.py": "Velocity and tick-stream primitives for the observer.",
    "shadow/registry.py": "Registry of shadow primitives and their gates.",
    "shadow/scorers.py": "Post-mortem scoring surface for observed entries.",
    "shadow/eod_compare.py": "End-of-day comparison of shadow vs live.",
    "shadow/trading_day.py": "Session-boundary helper for the observer.",
    "query.py": "Ad-hoc trade and store queries.",
    "status.py": "Box status summary.",
    "debug_status.py": "Verbose diagnostic status dump.",
    "eod_summary.py": "End-of-day per-box summary.",
    "devtools.sh": "Control-side service menu.",
    "snapshot.sh": "Snapshots a directory into a repo-ready tarball.",
    "push.sh": "Pushes the control checkout to GitHub.",
    "pull_today_ohlc.sh": "Pulls the current session's OHLC from a box.",
    "eod_bot.sh": "End-of-day bot wrapper.",
    "stress_theta_bleed.py": "Stress harness for the theta-bleed exit.",
    # --- ROUND 3: over-dropped structure providers, restored ---------------
    # I dropped these on LOCATION AND NAME - they live in analysis/ and have
    # "engine" in the title - rather than on what they COMPUTE. Neither is a
    # `volatility_engine` produces ATR, Bollinger bands, price_vs_bb, VWAP,
    # price_vs_vwap and compression state. `trend_engine` produces ADX, the EMA
    # stack and momentum. **The operator's successor list names ADX and VWAP
    # explicitly** - both were sitting in modules I had cut.
    # corroborator grammar), conviction_integrator (confirmatory by
    # label and the conviction number).
    "analysis/volatility_engine.py": "ATR, Bollinger bands, VWAP, price-vs-band, compression state.",
    "analysis/trend_engine.py": "ADX, EMA stack and momentum per timeframe. DIRECTION VOTE IS DESCRIPTIVE ONLY.",
}


def _describe(header, rel):
    """The written description for this file, or "" if none is on file yet."""
    if rel in DESCRIPTIONS:
        return DESCRIPTIONS[rel]
    return _autodescribe(header, rel)


def _autodescribe(header, rel):
    """Last resort: a genuinely descriptive line carrying NO version and NO date."""
    for ln in header:
        s = ln.strip().lstrip("#").strip()
        if not s or s.startswith(('"""', "'''")) or set(s) <= set("=- "):
            continue
        if VER_LINE.match(ln):
            continue
        # ⚠️ A CHANGELOG TITLE IS NOT A MODULE DESCRIPTION. In OTV3's commonest
        # header the path, the version, the date and the last change's TITLE all
        # share one line:
        #   analysis/liquidity_mapper.py  v4.3  2026-08-15  AUDIT A2: THE INPUT...
        # A naive extract yields "AUDIT A2: THE INPUT COULD NOT" as the
        # description — **a header that describes the last bug fix instead of
        # what the module does is worse than no header at all.** If the line
        # carries a version AND a date it is changelog; skip it and leave the
        # description blank for a human to write.
        # ⚠️ ANY version or date anywhere on the line means changelog, and a
        # line that is merely a continuation of one is unidentifiable from the
        # line alone — which is why DESCRIPTIONS exists and this is a fallback.
        if VER_ANY.search(ln) or re.search(r"\d{4}-\d{2}-\d{2}", ln):
            continue
        if not re.match(r"^[A-Z][a-z]", s2 if False else s):
            continue          # a sentence, not a shouted changelog title
        # "path  vX.Y  date  TITLE" -> keep TITLE; "path  Description." -> keep it
        s2 = re.sub(r"^\S*" + re.escape(os.path.basename(rel)) + r"\s*", "", s)
        s2 = VER_ANY.sub("", s2)
        s2 = re.sub(r"\d{4}-\d{2}-\d{2}", "", s2)
        s2 = re.sub(r"^[\s\-—:]+", "", s2).strip()
        s2 = re.sub(r"^\(see below\);?\s*original header follows\.?", "", s2).strip()
        if len(s2) > 12:
            return s2[:120]
    return ""


TRIVIA = re.compile(
    r"(typo|misspell|spelling|hyphen|whitespace|indent(ation)?\s+fix|"
    r"cosmetic|formatting only|renamed?\s+(the\s+)?(dir|directory|folder|file)\b|"
    r"wrong\s+(dir|directory|path)\b|fixed?\s+(the\s+)?path\b|"
    r"lint|flake8|noqa|trailing\s+(comma|space))", re.I)

STAMP = re.compile(r"\bv\d+[\.\-][\w\.]*\s*[\u2014\-]?\s*\d{4}-\d{2}-\d{2}\s*[\u2014\-]?\s*")

TRIPLE_D = chr(34) * 3
TRIPLE_S = chr(39) * 3


def _preserve_header(header, rel, is_py):
    """Keep the load-bearing header, strip trivia, reset the version to 4.0."""
    kept, dropped = [], 0
    for ln in header:
        raw = ln.strip().lstrip("#").strip()
        if not raw or raw in (TRIPLE_D, TRIPLE_S):
            continue
        # A preserved line may still CARRY its opening triple-quote:
        #     """shadow/trading_day.py v1.0 - standalone trading-day check
        # Kept verbatim it closes the new docstring early and dumps the rest of
        # the doctrine into the module as bare prose - two files stopped
        # parsing. Strip the quotes, keep the words.
        for _q in (TRIPLE_D, TRIPLE_S):
            raw = raw.replace(_q, "")
            ln = ln.replace(_q, "")
        if not raw.strip():
            continue
        if set(raw) <= set("=-_ "):
            continue
        if TRIVIA.search(raw):
            dropped += 1
            continue
        cleaned = STAMP.sub("", ln.rstrip())
        if cleaned.strip().lstrip("#").strip():
            kept.append(cleaned)

    desc = DESCRIPTIONS.get(rel, "")
    banner = [
        "v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.",
        "",
        "INHERITED DOCTRINE",
        "MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.",
        "Dated release framing and trivia are stripped; what remains is the",
        "reasoning behind the thresholds, the design guarantees, and the",
        "defects that recur when forgotten. WORKING_AGREEMENT 32 requires",
        "this block be read before the file is edited.",
        "",
    ]
    if is_py:
        out = [TRIPLE_D, rel + "  v4.0"]
        if desc:
            out.append(desc)
        out += [""] + banner + kept + [TRIPLE_D]
    else:
        sb = [header[0]] if header and header[0].startswith("#!") else []
        out = sb + ["# " + "=" * 74, "# " + rel + "  v4.0"]
        if desc:
            out.append("# " + desc)
        out += ["#"] + ["# " + b if b else "#" for b in banner]
        out += [l if l.lstrip().startswith("#") else "# " + l.lstrip() for l in kept]
        out += ["# " + "=" * 74]
    return out, dropped


def scrub(src, dst, rel, dry=False):
    text = open(src, encoding="utf-8").read()
    is_py = rel.endswith(".py")
    header, body = (_split_py(text) if is_py else _split_sh(text))
    if not header:
        if not dry:
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            shutil.copy2(src, dst)
        return "copied-verbatim", 0

    new_header, dropped = _preserve_header(header, rel, is_py)
    out = "\n".join(new_header + body)
    if not dry:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        open(dst, "w", encoding="utf-8").write(out)
        written = open(dst, encoding="utf-8").read()
        if is_py:
            ast.parse(written)
        b2 = (_split_py(written) if is_py else _split_sh(written))[1]
        if "\n".join(body).strip() != "\n".join(b2).strip():
            raise AssertionError("BODY CHANGED for " + rel + " - refusing")
    return "scrubbed", dropped


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--list", required=True, help="manifest, one relative path per line")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv[1:])

    rels = [l.strip() for l in open(a.list) if l.strip()
            and not l.strip().startswith("#")]
    ok = miss = verbatim = 0
    NEEDS_DESC = []
    total_removed = 0
    for rel in rels:
        s = os.path.join(a.src, rel)
        if not os.path.exists(s):
            print(f"  MISSING  {rel}")
            miss += 1
            continue
        try:
            what, removed = scrub(s, os.path.join(a.dst, rel), rel, a.dry_run)
        except Exception as exc:                                # noqa: BLE001
            print(f"  FAILED   {rel}: {exc}")
            miss += 1
            continue
        total_removed += removed
        if not _describe([], rel) and rel not in DESCRIPTIONS:
            NEEDS_DESC.append(rel)
        if what == "copied-verbatim":
            verbatim += 1
        else:
            ok += 1

    print(f"\n  scrubbed {ok} · copied-verbatim {verbatim} · "
          f"missing/failed {miss} · trivia lines dropped {total_removed}")
    if NEEDS_DESC:
        print(f"\n  ⚠️ {len(NEEDS_DESC)} file(s) have NO written description and no")
        print("     safely-extractable one. They ship with a blank description")
        print("     line rather than a scraped changelog fragment. Fill them in")
        print("     DESCRIPTIONS at the top of this file:")
        for r in NEEDS_DESC[:12]:
            print(f"       {r}")
        if len(NEEDS_DESC) > 12:
            print(f"       ... and {len(NEEDS_DESC) - 12} more")
    if miss:
        print("  ⚠️ MISSING OR FAILED FILES — the manifest and the source disagree.")
        print("     Fix before shipping: a silently absent module is a repo that")
        print("     imports until the day it does not.")
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
