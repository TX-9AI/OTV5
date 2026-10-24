#!/usr/bin/env python3
"""tests/check_no_env_dump.py — v1.0
v1.0  2026-09-05 — r265. NO COMMAND IN EITHER REPO PRINTS A SERVICE ENVIRONMENT
BLOCK.

🔴 WHY IT EXISTS. On 2026-09-05 I ran
`systemctl show shadow-observer -p Environment --value` across all fifteen boxes
to confirm ONE variable. That flag prints the WHOLE block: `TT_REFRESH_TOKEN`
(a live JWT with `read trade` scope on the funded account), `TT_CLIENT_SECRET`,
`GITHUB_TOKEN` with write access to both repos, and `TELEGRAM_TOKEN` — onto the
operator's terminal and into the session record. Four credential rotations
across fifteen boxes, on a Saturday evening, caused entirely by me.

⚠️ AND I HAD WRITTEN THE SAFE FORM EARLIER IN THE SAME SESSION. Knowing the rule
did not put it in the command, which is the whole argument for a checker rather
than a note: the next person to check an env var will reach for exactly what I
reached for.

⚠️ THIS FLEET KEEPS ITS ENV INLINE IN THE UNIT — `optionsbot.service` carries
`Environment=` lines rather than an `EnvironmentFile`, and the observer unit's
comments instruct copying them across. **Every unit on every box is a credential
store**, so there is no unit this is safe against.
"""
import os
import re
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []

# A unit FILE may legitimately contain `Environment=` lines — that is how the
# fleet is configured. What is forbidden is a COMMAND that reads them back out.
SKIP_EXT = (".service", ".timer", ".md")
# The checker and the section that document the incident must quote the unsafe
# form in order to name it. Quoting is not running.
EXEMPT = {"check_no_env_dump.py"}

# 🔑 THE LINE IS *EMITTING* THE BLOCK, NOT READING IT — and the checker's own
# false positives are what established that. Three install scripts do
# `EL=$(systemctl show "$BOTUNIT" -p Environment --value)` and then filter with
# `echo "$EL" | tr ' ' '\n' | grep "^$1="`. That CAPTURES into a variable and
# nothing reaches a terminal; it is the correct idiom and predates me. What I
# did was put the same call inside an `echo`, so the whole block went to his
# screen. A rule that banned reading would have flagged three working scripts
# and taught the next reader to disable the check.
_CAPTURE = re.compile(r"^\s*\w+=\$\(\s*(?:sudo\s+)?systemctl\s+show\b[^)]*\)\s*$")
_FILTERED = re.compile(r"\|\s*(?:tr|grep|cut|awk|sed)\b")

PATTERNS = [
    (re.compile(r"-p\s+Environment"),
     "systemctl -p Environment reaching output — prints EVERY variable"),
    (re.compile(r"\bsystemctl\s+cat\b"),
     "systemctl cat prints the unit, Environment= lines included"),
    (re.compile(r"/proc/\S*/environ"),
     "/proc/<pid>/environ is the whole block"),
    # ⚠️ `env`/`printenv` ANYWHERE A COMMAND STARTS, including after `ssh box`.
    # The first draft anchored on line start and `;&|` only, and missed
    # `ssh box env` — the exact shape a fleet fan-out would take.
    (re.compile(r"(?:^|[;&|]|\bssh\s+\S+\s+)(?:sudo\s+)?(?:env|printenv)\s*(?:$|[;&|])"),
     "bare env/printenv dumps the process environment"),
]


def _offends(line: str) -> str:
    """-> the reason this line would EMIT a credential block, or ""."""
    bare = line.split("#", 1)[0]
    # Captured into a variable and filtered later: the working idiom.
    if _CAPTURE.match(bare):
        return ""
    for pat, why in PATTERNS:
        if pat.search(bare):
            # A filter on the same line means one variable was asked for.
            if pat.pattern.startswith("-p") and _FILTERED.search(bare):
                continue
            return why
    return ""


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    hits = []
    for dirpath, dirnames, filenames in os.walk(_root):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "__pycache__", "venv", "node_modules"}]
        for fn in filenames:
            if fn.endswith(SKIP_EXT) or fn in EXEMPT:
                continue
            if not fn.endswith((".py", ".sh")):
                continue
            full = os.path.join(dirpath, fn)
            try:
                src = open(full, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            for i, line in enumerate(src.splitlines(), 1):
                why = _offends(line)
                if why:
                    hits.append(f"{os.path.relpath(full, _root)}:{i} — {why}")

    check("E1 no command in the repo prints a service environment block",
          not hits, f"{len(hits)}: {hits[:3]}")

    # ⚠️ A GUARD NEVER SEEN RED IS A GUARD NOBODY HAS TESTED. Plant each shape.
    planted = [
        'echo "STAGE $(systemctl show shadow-observer -p Environment --value)"',
        'sudo systemctl cat optionsbot',
        'cat /proc/1234/environ',
        'ssh box env',
    ]
    caught = [p for p in planted if _offends(p)]
    check("E1b ...and every unsafe shape is actually detected",
          len(caught) == len(planted), f"caught {len(caught)}/{len(planted)}")

    # 🔑 AND THE SAFE FORM MUST STILL PASS, or the rule is unusable and the next
    # person works around it instead of following it.
    safe = 'systemctl show shadow-observer -p Environment --value | tr " " "\\n" | grep OT_SHADOW_STAGE'
    check("E1c ...while the filtered form is allowed", not _offends(safe))
    # 🔑 AND THE CAPTURE IDIOM THE INSTALL SCRIPTS USE MUST STAY LEGAL, or the
    # rule flags three working files and gets switched off.
    cap = '    EL=$(systemctl show optionsbot -p Environment --value 2>/dev/null)'
    check("E1d ...and capturing into a variable for later filtering is allowed",
          not _offends(cap))

    # E2 — the rule is written down where a human will meet it.
    wa = os.path.join(_root, "docs", "WORKING_AGREEMENT.md")
    if os.path.exists(wa):
        txt = open(wa, encoding="utf-8").read()
        check("E2 the rule is recorded in the WORKING_AGREEMENT",
              "NO COMMAND PRINTS A SERVICE ENVIRONMENT BLOCK" in txt)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 5 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
