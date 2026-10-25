#!/usr/bin/env python3
"""
tests/check_origin.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-24  CD.1 — ONE REPOSITORY NAME, AND WHAT THE INSTALL CLONES IS THAT ONE. deploy/origin.conf names the
      repository; the two files that run before any clone carry pinned copies. A tree copied into a new repository
      that changed one and not the others would install the old repository "unattended" and still look like a pass.
      Behaviour where it can be driven (WA §21): install.sh's plan-only path runs with a git stub that records the URL
      it was asked to clone; setup_ec2.sh --plan prints the repository it will use; install_claude.sh renders the
      settings in a sandbox HOME (a stub claude binary, nothing installed).
  O1  install.sh (OT_PLAN_ONLY=1, no OT_REPO_URL) clones https://github.com/<origin.conf>.git
  O2  setup_ec2.sh --plan, no GITHUB_REPO in the environment: git_repo = origin.conf
  O3  bootstrap.example.sh's GITHUB_REPO = origin.conf
  O4  install_claude.sh renders {{ORIGIN_REPO}} = origin.conf in ~/.claude/settings.json (both templates), and the
      rendered file is valid JSON with no placeholder left
  O5  the settings TEMPLATES do not name the origin literally (a definition, not a mention - WA §20: GENESIS, docs and
      headers name past repositories by history and are deliberately NOT checked)
Run: python3 tests/check_origin.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  [{detail}]"))
    RAN.append(name)
    if not ok:
        FAILED.append(name.split()[0])


def origin():
    r = subprocess.run(["bash", "-c", f'. "{ROOT}/deploy/origin.conf" && echo "$OT_ORIGIN_REPO"'],
                       capture_output=True, text=True)
    return r.stdout.strip()


def main() -> int:
    if not os.path.isfile(os.path.join(ROOT, "deploy", "origin.conf")):
        check("O0 deploy/origin.conf exists", False, "missing")
        print(f"\nRED — {FAILED}")
        return 1
    o = origin()
    check("O0 origin.conf names OWNER/REPO", bool(re.fullmatch(r"[\w.-]+/[\w.-]+", o)), o)

    # O1
    with tempfile.TemporaryDirectory() as tmp:
        bindir = os.path.join(tmp, "bin")
        os.makedirs(bindir)
        log = os.path.join(tmp, "git.log")
        open(os.path.join(bindir, "git"), "w").write(f'#!/bin/bash\necho "git $*" >> "{log}"\nexit 1\n')
        os.chmod(os.path.join(bindir, "git"), 0o755)
        env = {"PATH": f"{bindir}:/usr/bin:/bin", "HOME": tmp, "OT_PLAN_ONLY": "1"}
        subprocess.run(["bash", os.path.join(ROOT, "deploy", "install.sh")], env=env, capture_output=True,
                       text=True, timeout=60, stdin=subprocess.DEVNULL)
        calls = open(log).read() if os.path.exists(log) else ""
        m = re.search(r"git clone -q (\S+)", calls)
        check("O1 install.sh clones the origin.conf repository", bool(m) and m.group(1) == f"https://github.com/{o}.git",
              calls[:200])

    # O2
    with tempfile.TemporaryDirectory() as home:
        env = {"PATH": "/usr/bin:/bin", "HOME": home, "TT_CLIENT_SECRET": "x", "TT_REFRESH_TOKEN": "x",
               "TT_ACCOUNT_NUMBER": "x", "TELEGRAM_TOKEN": "x", "TELEGRAM_CHAT_ID": "x"}
        r = subprocess.run(["setsid", "-w", "bash", os.path.join(ROOT, "setup_ec2.sh"), "--plan"], env=env,
                           capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        m = re.search(r"^PLAN git_repo=(.*)$", r.stdout, re.M)
        check("O2 setup_ec2.sh --plan uses the origin.conf repository", bool(m) and m.group(1) == o,
              (m.group(1) if m else r.stdout[-200:]))

    # O3
    r = subprocess.run(["bash", "-c", f'eval "$(grep -E "^export GITHUB_REPO=" "{ROOT}/bootstrap.example.sh")"; '
                        'echo "$GITHUB_REPO"'], capture_output=True, text=True)
    check("O3 bootstrap.example.sh GITHUB_REPO = origin.conf", r.stdout.strip() == o, r.stdout.strip())

    # O4
    ver = re.search(r'VERSION="\$\{OT_CLAUDE_VERSION:-([^}]+)\}"',
                    open(os.path.join(ROOT, "deploy", "install_claude.sh")).read())
    for flavour in ("", "pull-only"):
        with tempfile.TemporaryDirectory() as home:
            b = os.path.join(home, ".local", "bin")
            os.makedirs(b)
            v = ver.group(1) if ver else "0"
            open(os.path.join(b, "claude"), "w").write(f'#!/bin/bash\n[ "$1" = --version ] && echo "{v} (Claude Code)"\nexit 0\n')
            os.chmod(os.path.join(b, "claude"), 0o755)
            env = {"PATH": f"{b}:/usr/bin:/bin", "HOME": home}
            if flavour:
                env["OT_CLAUDE_SETTINGS"] = flavour
            subprocess.run(["bash", os.path.join(ROOT, "deploy", "install_claude.sh")], env=env, capture_output=True,
                           text=True, timeout=60, stdin=subprocess.DEVNULL)
            sp = os.path.join(home, ".claude", "settings.json")
            txt = open(sp).read() if os.path.exists(sp) else ""
            try:
                json.loads(txt)
                valid = True
            except ValueError:
                valid = False
            check(f"O4 install_claude.sh renders the origin into the {flavour or 'default'} settings",
                  valid and o in txt and "{{ORIGIN_REPO}}" not in txt, txt[:160])

    # O5
    bad = [f for f in ("claude-user-settings.json", "claude-user-settings-pull-only.json")
           if o in open(os.path.join(ROOT, "deploy", f)).read()]
    check("O5 the settings templates do not name the origin literally (only {{ORIGIN_REPO}})", not bad, f"{bad}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(sorted(set(FAILED))))
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
