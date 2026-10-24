#!/usr/bin/env python3
"""tools/run_with_bot_env.py — v1.4
RUN ONE APPROVED, READ-ONLY PROBE WITH THE BOT'S BROKER CREDENTIALS, AND NOTHING ELSE.

v1.4 (2026-10-24) — PRB.6 — probe_intraday_candles.py joins PROBES (the operator, 2026-10-24 16:04 ET: "14, yes
      worthwhile" - years of 5m bars for trend-vs-chop studies); tests/check_probe_intraday_candles.py proves it only
      reads and writes one CSV.
v1.3 (2026-10-21) — OTV4TEST r311 (PRB.4) — probe_daily_candles.py joins PROBES (the operator, 2026-10-21 19:10 ET:
      "the daily candle is a yes"); tests/check_probe_daily_candles.py proves it only reads and writes one CSV.
v1.2 (2026-10-20) — OTV4TEST r308 (PRB.3) — probe_live_mark.py joins PROBES (the operator, 2026-10-20 10:53 ET: "Concur"
      to a read-only LIVE.1 F4 probe); tests/check_probe_live_mark.py proves it can only read.
v1.1 (2026-10-04) — OTV4TEST r239 (PRB.2) — probe_order_dryrun.py joins PROBES (the operator: "Yes, to the dry
      run if you can do it without actually spending money"); tests/check_probe_dryrun.py proves it can only dry-run.
v1.0 (2026-09-29) — OTV4TEST r176 (PRB.1). The operator, 2026-09-29, after the
      permission layer refused the agent loading the bot unit's environment for
      a probe: "Yes, set it up so I can approve it & modify the config." On
      09-22 a session had run tools/feed_capabilities.py by sourcing the unit's
      TT_* lines into its own shell; the same outcome was refused on 09-29,
      correctly - the agent's grant and the tool's permission rule are
      separate systems (WORKING_AGREEMENT 38.6), and the fix is a rule the
      OPERATOR writes, naming one fixed command. This is that command.

🔴 WHAT IT WILL RUN IS THE WHOLE POINT, SO IT IS NARROW BY CONSTRUCTION:
  1. ONLY A NAME ON `PROBES` below - never a path the caller supplies.
  2. ONLY IF THAT FILE IS TRACKED AND IDENTICAL TO HEAD. A probe that has been
     edited in the working tree is refused: otherwise an allow rule on this
     wrapper would let whoever edits a listed file (the agent included) run
     arbitrary code with the broker's credentials. What runs is what landed,
     and what landed carried the operator's "yes".
  3. ONLY THE KEYS IT NEEDS: TT_[A-Z_]+, OT_INSTRUMENT, OT_FEED_DB, read from the
     bot unit's Environment in THIS process's memory. TELEGRAM_*, GITHUB_*,
     and everything else in that block never reach the probe.
  4. NOTHING PRINTED BUT KEY NAMES (WORKING_AGREEMENT 18a): not a value, not a
     length, not a prefix. The child's own output passes through.
Exit codes: the probe's own; 64 not an allowed probe; 65 modified or
untracked; 66 missing; 69 the bot unit's environment could not be read or
carried no TT_ key.

Usage (the operator's allow rule names exactly this, with ANY arguments):
    /home/ubuntu/options-trader/venv/bin/python \\
        /home/ubuntu/options-trader/tools/run_with_bot_env.py <probe> [args]
    probes: feed_capabilities.py  probe_aux_streams.py  probe_candle_depth.py  probe_order_dryrun.py
            probe_live_mark.py  probe_daily_candles.py
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT = os.environ.get("OT_BOT_UNIT", "optionsbot")
PROBES = {
    "feed_capabilities.py": "tools/feed_capabilities.py",
    "probe_aux_streams.py": "tools/probe_aux_streams.py",
    "probe_candle_depth.py": "tools/probe_candle_depth.py",
    "probe_order_dryrun.py": "tools/probe_order_dryrun.py",   # r239 - dry_run=True only (check_probe_dryrun)
    "probe_live_mark.py": "tools/probe_live_mark.py",         # r308 - read only (check_probe_live_mark)
    "probe_daily_candles.py": "tools/probe_daily_candles.py", # r311 - read only, one CSV (check_probe_daily_candles)
    "probe_intraday_candles.py": "tools/probe_intraday_candles.py",  # PRB.6 - read only, one CSV (check_probe_intraday_candles)
}
KEEP = re.compile(r"^(TT_[A-Z_]+|OT_INSTRUMENT|OT_FEED_DB)$")


def _say(msg: str) -> None:
    print("run_with_bot_env: " + msg, file=sys.stderr, flush=True)


def committed_and_clean(rel: str) -> bool:
    """Tracked in git and byte-identical to HEAD (working tree AND index)."""
    def git(*a):
        return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True).returncode
    return (git("ls-files", "--error-unmatch", "--", rel) == 0
            and git("diff", "--quiet", "HEAD", "--", rel) == 0)


def unit_env() -> dict:
    """The bot unit's KEEP keys, parsed in memory. Never printed, never written."""
    r = subprocess.run(["systemctl", "show", UNIT, "-p", "Environment", "--value"],
                       capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        return {}
    out = {}
    for tok in shlex.split(r.stdout.strip()):
        k, sep, v = tok.partition("=")
        if sep and KEEP.match(k):
            out[k] = v
    return out


def main(argv) -> int:
    if not argv or argv[0] not in PROBES:
        _say("'%s' is not an allowed probe (%s)" % (argv[0] if argv else "", " ".join(PROBES)))
        return 64
    rel = PROBES[argv[0]]
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        _say("%s is missing" % rel)
        return 66
    if not committed_and_clean(rel):
        _say("%s is modified or untracked - only a committed, unmodified probe runs" % rel)
        return 65
    env = unit_env()
    if not any(k.startswith("TT_") for k in env):
        _say("could not read TT_ keys from the %s unit's environment - nothing run" % UNIT)
        return 69
    _say("running %s with %s from %s (names only)" % (rel, " ".join(sorted(env)), UNIT))
    child = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "TZ") if k in os.environ}
    child.update(env)
    py = os.path.join(ROOT, "venv", "bin", "python")
    return subprocess.run([py if os.path.exists(py) else sys.executable, path, *argv[1:]],
                          cwd=ROOT, env=child).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
