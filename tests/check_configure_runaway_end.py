#!/usr/bin/env python3
"""
tests/check_configure_runaway_end.py  v1.0

configure.sh sets RUNAWAY'S ENTRY END (OT_RUNAWAY_END) per box, and what it
writes is what config.py actually reads.

v1.0  2026-10-05  OTV4TEST r253 (RUNW.2). r189 built OT_RUNAWAY_END and the
      operator approved 11:30 for SPX-TEST on 10-03, but nothing on the menu
      could set it, so it was never set: SPX-TEST measured its Runaway going
      INACTIVE at 10:30:00 ET on 10-05. The operator, 2026-10-05 11:33 ET:
      "If we're gonna allow a per box setting then it needs to be a toggle
      inside configure."

  P0  change_runaway_end is defined in configure.sh
  R1  entering 11:30 writes OT_RUNAWAY_END=11:30 and reloads the daemon
  R2  END TO END: the value written, fed to config.py, gives Runaway's end 11:30
  R3  a malformed value (1130) is REFUSED: nothing written, the reason printed
  R4  an out-of-range value (09:30, 15:45) is REFUSED by config.py's own rule
  R5  a blank answer CLEARS the key and reloads; config.py then gives 10:30
  R6  the menu dispatches an item to change_runaway_end, and the prompt's
      range matches the highest item number (no orphaned or unreachable item)
  R7  the label (R7b: a key exported in the operator's shell is ignored): unset reads "not set (code default: 10:30)" FROM config.py;
      set reads the end in force
  R8  the summary (show_config) names Runaway's end
  R9  no undefined helper on the path
  R10 (R10b: the line really calls it, source-level) the BOT's Service mode line names the end in force and the pin gate (the REAL
      main._banner_dials, imported fresh per case): unset -> 10:30, 11:30 + pin OFF -> both
      read back, a refused 1130 -> named REFUSED (SPX-TEST, 10-05: neither was printed)

The harness is check_configure_pin_gate's: the function bodies are pulled out
of configure.sh (it ends in an interactive loop and cannot be sourced),
get_env/set_env/drop_env are pointed at a temp file, reload_daemon announces
itself, and command_not_found_handle turns an undefined helper into a named
failure.

Run:  python3 tests/check_configure_runaway_end.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGURE = os.path.join(ROOT, "configure.sh")
KEY = "OT_RUNAWAY_END"

PROBLEMS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name.split()[0])


def _functions_only(src: str) -> str:
    out, keep = [], False
    for line in src.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\(\)\s*\{", line):
            keep = True
        if keep:
            out.append(line)
        if keep and line == "}":
            keep = False
    return "\n".join(out)


def _run(call: str, start: str | None, stdin: str = "",
         shell_env: str | None = None) -> tuple[str | None, str, str, int]:
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
drop_env() {{ grep -v "^$1=" "{envfile}" > "{envfile}.t" 2>/dev/null;
              mv "{envfile}.t" "{envfile}"; echo "DROP_CALLED $1" >&2; }}
reload_daemon() {{ echo "RELOAD_CALLED" >&2; }}
{call}
"""
        env = {k: v for k, v in os.environ.items() if k != KEY}
        if shell_env is not None:          # R7b: the operator's shell exported the key
            env[KEY] = shell_env
        proc = subprocess.run(["bash", "-c", harness], input=stdin, capture_output=True,
                              text=True, timeout=60, env=env)
        value = None
        for line in open(envfile):
            if line.startswith(KEY + "="):
                value = line.strip().split("=", 1)[1]
        return value, proc.stdout, proc.stderr, proc.returncode


def _config_end(value: str | None) -> str:
    """What config.py makes of a value - the CONSUMER's reading, not the file's."""
    env = {k: v for k, v in os.environ.items() if k != KEY}
    if value is not None:
        env[KEY] = value
    p = subprocess.run([sys.executable, "-c", "import config; print(config.RUNAWAY_CUTOFF_ET)"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    return p.stdout.strip() or f"IMPORT FAILED: {p.stderr.strip().splitlines()[-1:]}"


def main() -> int:
    print("=" * 68)
    print("CONFIGURE: Runaway's entry end (OT_RUNAWAY_END), per box")
    print("=" * 68)
    src = open(CONFIGURE).read()
    defined = set(re.findall(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\)", src, re.M))
    if "change_runaway_end" not in defined:
        check("P0 change_runaway_end is defined in configure.sh", False,
              "change_runaway_end is not defined")
        print(f"RED - {len(PROBLEMS)} problem(s): {' '.join(PROBLEMS)}")
        return 1
    check("P0 change_runaway_end is defined in configure.sh", True)

    v1, _o1, e1, rc1 = _run("change_runaway_end", None, "11:30\n")
    check("R1 entering 11:30 writes OT_RUNAWAY_END=11:30", v1 == "11:30", f"left {v1!r} (rc={rc1})")
    check("R1 the write reloads the daemon", "RELOAD_CALLED" in e1, "systemd would restart the OLD unit")
    check("R2 END TO END: config.py reads the written value as Runaway's end 11:30",
          _config_end(v1) == "11:30", f"config gives {_config_end(v1)!r}")

    v3, o3, _e3, rc3 = _run("change_runaway_end", "11:30", "1130\n")
    check("R3 a malformed 1130 is REFUSED - the stored 11:30 is untouched", v3 == "11:30",
          f"left {v3!r} (rc={rc3})")
    check("R3 the refusal says so", "REFUSED" in o3.upper(), o3.strip().splitlines()[-1:] or "silent")

    bad = []
    for val in ("09:30", "15:45", "25:00"):
        v4, o4, _e4, _rc4 = _run("change_runaway_end", None, f"{val}\n")
        if v4 is not None or "REFUSED" not in o4.upper():
            bad.append(f"{val} -> wrote {v4!r}")
    check("R4 out-of-range values (09:30, 15:45, 25:00) are REFUSED, nothing written", not bad, "; ".join(bad))

    v5, _o5, e5, rc5 = _run("change_runaway_end", "11:30", "\n")
    check("R5 a blank answer CLEARS the key", v5 is None, f"left {v5!r} (rc={rc5})")
    check("R5 the clear reloads the daemon", "RELOAD_CALLED" in e5, "systemd would restart the OLD unit")
    check("R5 cleared, config.py gives the 10:30 default", _config_end(v5) == "10:30",
          f"config gives {_config_end(v5)!r}")

    m = re.search(r"^\s*(\d+)\)\s*change_runaway_end\b", src, re.M)
    items = [int(n) for n in re.findall(r"^\s*(\d+)\)\s", src[src.find('case "$menu_choice"'):], re.M)]
    rng = re.search(r'Select \[1-(\d+)\]', src)
    check("R6 the menu dispatches an item to change_runaway_end", bool(m), "no `N) change_runaway_end` case")
    check("R6 the prompt's range matches the highest item",
          bool(rng) and bool(items) and int(rng.group(1)) == max(items),
          f"prompt {rng.group(1) if rng else None} vs items {items}")

    _v, o7u, _e, _rc = _run("runaway_end_label", None)
    _v, o7s, _e, _rc = _run("runaway_end_label", "11:30")
    check("R7 unset reads 'not set (code default: 10:30)' from config.py",
          o7u.strip() == "not set (code default: 10:30)", repr(o7u.strip()))
    check("R7 set reads the end in force", o7s.strip().startswith("11:30"), repr(o7s.strip()))
    _v, o7b, _e, _rc = _run("runaway_end_label", None, shell_env="11:45")
    check("R7b unset in the UNIT reads the code default even when the shell exports OT_RUNAWAY_END",
          o7b.strip() == "not set (code default: 10:30)", repr(o7b.strip()))

    body = re.search(r"^show_config\(\)\s*\{(.*?)^\}", src, re.M | re.S)
    check("R8 the summary names Runaway's end",
          bool(body) and "runaway_end_label" in body.group(1), "show_config never calls runaway_end_label")

    errs = [e for e in (e1, e5) if "MISSING_COMMAND" in e]
    check("R9 no undefined helper on the path", not errs and 42 not in (rc1, rc3, rc5),
          errs[0].strip().splitlines()[-1] if errs else "")

    def _banner(extra: dict) -> str:
        env = {k: v for k, v in os.environ.items() if k not in (KEY, "OT_PIN_PROXIMITY_ACTIVE")}
        with tempfile.TemporaryDirectory() as d:
            env.update(OT_INSTRUMENT="QQQ", OT_TRADES_DB=os.path.join(d, "t.db"),
                       OT_DERIVED_DB=os.path.join(d, "d.db"), OT_FEED_DB=os.path.join(d, "f.db"),
                       OT_RESTING_DB=os.path.join(d, "r.db"), OT_LOG_FILE=os.path.join(d, "b.log"))
            env.update(extra)
            p = subprocess.run([sys.executable, "-c", "import main; print('BANNER' + main._banner_dials())"],
                               cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
        line = [ln for ln in p.stdout.splitlines() if ln.startswith("BANNER")]
        return line[-1][6:] if line else f"NO BANNER: {(p.stderr.strip().splitlines() or ['?'])[-1][:120]}"
    b0 = _banner({})
    b1 = _banner({KEY: "11:30", "OT_PIN_PROXIMITY_ACTIVE": "0"})
    b2 = _banner({KEY: "1130"})
    check("R10 the Service line names the end and the pin gate, from config",
          "runaway_end=10:30" in b0 and "pin_gate=ON" in b0
          and "runaway_end=11:30" in b1 and "pin_gate=OFF" in b1
          and "runaway_end=10:30" in b2 and "'1130' REFUSED" in b2, f"{b0!r} | {b1!r} | {b2!r}")
    _main = open(os.path.join(ROOT, "main.py")).read()
    _svc = _main[_main.find('f"Service mode:'):][:3000]
    check("R10b SOURCE-LEVEL (like check_contract_scale S6/S7): the Service mode line calls _banner_dials()",
          'f"{_banner_dials()}"' in _svc, "the Service mode f-string never calls _banner_dials()")

    print(("RED - " + f"{len(PROBLEMS)} problem(s): {' '.join(PROBLEMS)}") if PROBLEMS
          else "GREEN - all checks pass")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
