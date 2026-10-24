#!/usr/bin/env python3
"""
tests/check_configure_pin_gate.py  v1.0

configure.sh item 7 turns r97's pin-proximity gate ON and OFF, and the value it
writes is the value config.py actually reads.

v1.0  2026-09-24  OTV4TEST r127. REPLACES tests/check_configure_relaxed.py v4.0,
      whose subject (change_relaxed, item 7) this revision removes on the
      operator's ruling: *"make it replace the relaxed entry toggle. Since we
      don't do relaxed entries here."* EVERY PROPERTY IT PINNED IS MOVED, NOT
      DROPPED (WORKING_AGREEMENT 38.4):
        C1-C3 (both answers write, both reload, no undefined helper on the path)
              -> retargeted from change_relaxed to change_pin_gate
        C4 (every `if <helper>` is defined), C5 (every root .sh is 100755 in the
              index), C6 (every set_env caller reloads) -> carried VERBATIM
      NEW: C7 the menu dispatches 7 to change_pin_gate and nothing dispatches or
      defines change_relaxed; C8 END TO END — the value each answer writes, fed
      to config.py, gives the gate state the menu claims; C9 an UNSET key shows
      "not set" with the default READ FROM config.py (r91: nothing displayed
      that the operator did not choose).

WHY C8 EXISTS. A menu can write a key nobody reads — a misspelt name, or a
value config.py parses differently ("0" vs "False") — and every other check
here still passes, because they all read the file back rather than asking the
consumer. r97's switch is `os.environ.get("OT_PIN_PROXIMITY_ACTIVE","1") == "1"`,
so only the literal "1" is ON.

The harness technique is inherited from check_configure_relaxed v4.0: the
function bodies are pulled out of configure.sh (it ends in an interactive loop
and cannot be sourced), get_env/set_env are pointed at a temp file,
reload_daemon announces itself, and command_not_found_handle turns an
undefined helper into a NAMED failure — an unbound name inside an `if` reads as
an honest "no" (the v4.1 `confirm` incident).

BORN RED on 27e5b65 (r126): P0 "change_pin_gate is not defined".

Run:  python3 tests/check_configure_pin_gate.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGURE = os.path.join(ROOT, "configure.sh")
KEY = "OT_PIN_PROXIMITY_ACTIVE"

PROBLEMS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def _functions_only(src: str) -> str:
    """Extract every column-0 `name() {` ... column-0 `}` block.

    configure.sh ends in a top-level `while` loop, so it cannot be sourced —
    sourcing it would launch the interactive menu. Pulling the definitions out
    is what lets the real function body run under a harness.
    """
    out, keep = [], False
    for line in src.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\(\)\s*\{", line):
            keep = True
        if keep:
            out.append(line)
        if keep and line == "}":
            keep = False
    return "\n".join(out)


def _run(call: str, start: str | None, stdin: str = "") -> tuple[str | None, str, str, int]:
    """Run a configure.sh function under the harness. Returns (value, stdout, stderr, rc)."""
    src = open(CONFIGURE).read()
    with tempfile.TemporaryDirectory() as tmp:
        envfile = os.path.join(tmp, "env")
        with open(envfile, "w") as fh:
            if start is not None:
                fh.write(f"{KEY}={start}\n")
        funcs = os.path.join(tmp, "funcs.sh")
        with open(funcs, "w") as fh:
            fh.write(_functions_only(src))
        harness = f"""
command_not_found_handle() {{ echo "MISSING_COMMAND: $1" >&2; exit 42; }}
RESET=""; BOLD=""; GREEN=""; YELLOW=""; CYAN=""; RED=""
BOT_DIR="{ROOT}"
source "{funcs}"
get_env() {{ sed -n "s/^$1=//p" "{envfile}"; }}
set_env() {{ grep -v "^$1=" "{envfile}" > "{envfile}.t" 2>/dev/null;
             mv "{envfile}.t" "{envfile}"; echo "$1=$2" >> "{envfile}"; }}
reload_daemon() {{ echo "RELOAD_CALLED" >&2; }}
{call}
"""
        env = {k: v for k, v in os.environ.items() if k != KEY}
        proc = subprocess.run(["bash", "-c", harness], input=stdin, capture_output=True,
                              text=True, timeout=60, env=env)
        value = None
        for line in open(envfile):
            if line.startswith(KEY + "="):
                value = line.strip().split("=", 1)[1]
        return value, proc.stdout, proc.stderr, proc.returncode


def _config_gate(value: str | None) -> str:
    """What config.py makes of a value — the CONSUMER's reading, not the file's."""
    env = {k: v for k, v in os.environ.items() if k != KEY}
    if value is not None:
        env[KEY] = value
    p = subprocess.run([sys.executable, "-c", "import config; print(config.PIN_PROXIMITY_ACTIVE)"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    return p.stdout.strip() or f"IMPORT FAILED: {p.stderr.strip().splitlines()[-1:]}"


def main() -> int:
    print("=" * 68)
    print("CONFIGURE ITEM 7: the pin-proximity gate, ON and OFF")
    print("=" * 68)
    src = open(CONFIGURE).read()
    defined = set(re.findall(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\)", src, re.M))
    if "change_pin_gate" not in defined:
        check("P0 change_pin_gate is defined in configure.sh", False,
              "change_pin_gate is not defined")
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    check("P0 change_pin_gate is defined in configure.sh", True)

    # ── C1 / C2 both answers write, both reload ─────────────────────────
    v_on, _o, e_on, rc_on = _run("change_pin_gate", "0", "y\n")
    check("C1 answering 'y' writes OT_PIN_PROXIMITY_ACTIVE=1", v_on == "1", f"left {v_on!r} (rc={rc_on})")
    check("C1 the ON branch reloads the daemon", "RELOAD_CALLED" in e_on, "systemd would restart the OLD unit")
    v_off, _o, e_off, rc_off = _run("change_pin_gate", "1", "n\n")
    check("C2 answering 'n' writes OT_PIN_PROXIMITY_ACTIVE=0", v_off == "0", f"left {v_off!r} (rc={rc_off})")
    check("C2 the OFF branch reloads the daemon", "RELOAD_CALLED" in e_off, "systemd would restart the OLD unit")

    # ── C3 no undefined helper on the path ──────────────────────────────
    bad = [e for e in (e_on, e_off) if "MISSING_COMMAND" in e]
    check("C3 no command-not-found on the pin-gate path", not bad and 42 not in (rc_on, rc_off),
          (bad[0].strip().splitlines()[-1] if bad else f"rc={rc_on},{rc_off}"))

    # ── C4 the helper it calls is really defined in this file ────────────
    src = open(CONFIGURE).read()
    called = re.findall(r"^\s*if (\w+) \"", src, re.M)
    defined = set(re.findall(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\)", src, re.M))
    # ⚠️ RESOLVE AGAINST THE SHELL, NOT AGAINST A LIST I MAINTAIN. The first
    # draft carried a hand-written allowlist of builtins and flagged `echo` —
    # a checker crying wolf on correct code, which trains an operator to ignore
    # it. `command -v` is the same lookup bash itself will do at runtime.
    undefined = []
    for c in sorted(set(called)):
        if c in defined:
            continue
        if subprocess.run(["bash", "-c", f"command -v {c}"],
                          capture_output=True).returncode != 0:
            undefined.append(c)
    check("C4 every `if <helper> \"...\"` names a defined function",
          not undefined, f"undefined: {undefined}")

    # ── C5 the exec bit, IN THE INDEX — where it actually has to live ────
    # r50 exists because a repointed box hit "Permission denied" on this very
    # file: git does not preserve the executable bit unless it is set in the
    # INDEX, and the working-tree mode is not what a fresh clone gets.
    # ⚠️ AND A TARBALL CANNOT FIX IT. `cp` preserves the DESTINATION file's
    # mode, so a 0755 archive member lands on a 0644 file and stays 0644 —
    # measured, not assumed. The archive's bit is decorative; the index's is
    # the one every clone reads.
    rc = subprocess.run(["git", "ls-files", "-s", "--", "*.sh"], cwd=ROOT,
                        capture_output=True, text=True)
    if rc.returncode != 0:
        # Not a failure: a red that means ENVIRONMENT teaches an operator to
        # ignore reds. Say what was not checked and move on.
        print("  NOTE  C5 skipped - git not available here; index modes "
              "unverified")
    else:
        nonexec = sorted(line.split("\t")[-1] for line in rc.stdout.splitlines()
                         if line and not line.startswith("100755"))
        check("C5 every root .sh is 100755 in the git index", not nonexec,
              f"not executable in the index: {nonexec} — a fresh clone or a "
              f"repoint gets Permission denied on these")

    # ── C6 a unit-file write must be followed by a daemon-reload ─────────
    # `set_env` edits the systemd UNIT FILE. Without `reload_daemon`, systemd
    # restarts from its CACHED unit, so the bot comes back on the OLD value
    # while configure.sh and the menu both report the NEW one — the setting
    # looks applied and is not. change_relaxed shipped that way (v4.1 -> v4.2).
    # ⚠️ EXACT, NOT HEURISTIC: this parses column-0 function blocks and asks
    # "does this body call set_env at all, and if so does it also reload?".
    # One reload after a batch of writes is correct and is what the other six
    # do, so the assertion is presence-per-function, not a count match.
    blocks, cur, fname = {}, [], None
    for line in src.splitlines():
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\)\s*\{", line)
        if m:
            fname, cur = m.group(1), []
        if fname is not None:
            cur.append(line)
            if line == "}":
                blocks[fname] = "\n".join(cur)
                fname = None
    no_reload = sorted(n for n, b in blocks.items()
                       if n != "set_env" and "set_env" in b
                       and "reload_daemon" not in b)
    check("C6 every set_env caller also reloads the daemon", not no_reload,
          f"writes the unit file without reloading: {no_reload} — systemd "
          f"restarts from its cached unit and the bot runs the OLD value")


    # ── C7 the menu dispatches item 7 here, and relaxed is gone ─────────
    case7 = re.findall(r"^\s*7\)\s*(\w+)", src, re.M)
    check("C7 menu item 7 dispatches change_pin_gate", case7 == ["change_pin_gate"], f"7) -> {case7}")
    check("C7 nothing defines or dispatches change_relaxed",
          "change_relaxed" not in defined and not re.search(r"^\s*\d+\)\s*change_relaxed", src, re.M),
          "the removed relaxed toggle is still reachable")
    items = sorted(int(n) for n in re.findall(r"^\s*(\d+)\)\s*\w", src, re.M))
    top = max(items) if items else 0
    check("C7 the out-of-range prompt names the real range",
          f"between 1 and {top}." in src, f"menu has {top} items; prompt says otherwise")

    # ── C8 END TO END: what each answer writes is what config.py reads ──
    g_on, g_off = _config_gate(v_on), _config_gate(v_off)
    check("C8 after 'y', config.PIN_PROXIMITY_ACTIVE is True", g_on == "True", f"config read {g_on}")
    check("C8 after 'n', config.PIN_PROXIMITY_ACTIVE is False", g_off == "False", f"config read {g_off}")

    # ── C9 what is DISPLAYED: set values as set, unset as unset + code default
    lab = {}
    for start in ("1", "0", None):
        _v, out, err, _rc = _run("pin_gate_label", start)
        lab[start] = out.strip()
    dflt = "ON" if _config_gate(None) == "True" else "OFF"
    check("C9 a set 1 displays ON", lab["1"] == "ON", repr(lab["1"]))
    check("C9 a set 0 displays OFF", lab["0"] == "OFF", repr(lab["0"]))
    check("C9 unset displays 'not set' and config.py's own default",
          lab[None] == f"not set (code default: {dflt})", repr(lab[None]))

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  ALL GREEN - item 7 turns the pin gate on and off, and config.py agrees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
