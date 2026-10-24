#!/usr/bin/env python3
"""
tests/check_bake.py  v1.0
THE BAKE IS BOTH SERVICES, IN ORDER, WITH THE BYTECODE PURGED (OTV4TEST r37).

v1.0  2026-09-18  OTV4TEST r37 — born red at r36 (3aa6cfd), where `bake()`
      restarts `$BOT` only and never purges `__pycache__`.

🔴 WHY THIS FILE EXISTS. The bake is the one command whose entire job is making
a landed revision LIVE, and it was half a bake:
  · it restarted the BOT and never the FEED — so r36's underlying-Quote
    subscription, which lives in `data/candle_feed.py`, could not take from a
    menu bake while the line printed "baked → active";
  · it never purged `__pycache__`, which the migrated operating notes name as
    *"the single most common cause of 'I pushed the fix but it's still broken'"*.
A green line that means only half of what it says is the failure class this repo
keeps finding in its own code, and it was sitting inside the deploy path.

Operator's sequence, 2026-09-18, adopted verbatim: stop both, pull, purge, start
the FEED first, then the bot, report both.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    src = open(os.path.join(ROOT, "devtools.sh"), encoding="utf-8").read()
    i = src.index("\nbake() {")
    body = src[i:src.index("\n}", i)]
    # the CODE only — a comment naming a step is not the step (§20/§21)
    code = "\n".join(l for l in body.splitlines() if not l.strip().startswith("#"))

    check("B1 the bake STOPS both services",
          re.search(r'systemctl stop "\$BOT" "\$FEED"|systemctl stop "\$FEED" "\$BOT"', code) is not None,
          "down together")
    check("B2 it pulls, and refuses to go on if the pull fails",
          "git pull --ff-only" in code and "pull FAILED" in body, "gated")
    check("B3 it PURGES the bytecode cache — the operating notes' first rule",
          "__pycache__" in code and "rm -rf" in code, "purge present")
    check("B3b ...and the purge cannot reach into venv/",
          '-not -path "*/venv/*"' in code, "venv excluded")
    check("B4 check_imports still BLOCKS a start on a tree that cannot import",
          "check_imports.py" in code and "check_imports FAILED" in body, "gate kept")
    check("B5 it starts the FEED, then the BOT — the bot reads what the feed writes",
          re.search(r'systemctl start "\$FEED".*?systemctl start "\$BOT"', code, re.S) is not None,
          "dependency order")
    check("B6 it reports BOTH units, so a half-bake cannot read as a whole one",
          re.search(r'baked.*\$FEED.*\$BOT', code, re.S) is not None, "both named")

    # ── the menu is read on a phone: r17's 54-column rule ───────────────────
    line = [l for l in src.splitlines() if "|mi_bake" in l]
    check("B7 the BAKE menu label still fits the 54-column rule (r17)",
          bool(line) and len("  99) " + line[0].split("|")[1]) <= 54,
          f'{len("  99) " + line[0].split("|")[1])} cols' if line else "no item")

    # ── it must actually parse ──────────────────────────────────────────────
    r = subprocess.run(["bash", "-n", os.path.join(ROOT, "devtools.sh")],
                       capture_output=True, text=True)
    check("B8 devtools.sh parses", r.returncode == 0, r.stderr.strip()[:80])

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
