#!/usr/bin/env python3
"""tests/check_midnight_halt.py — v1.1
v1.1  2026-09-13 — OTV4TEST r21 — M4: THE INSTALLER RENDERS A UNIT THAT CAN RUN.
      M1-M3 proved the SCRIPT and never looked at what installs it, so r14 moved
      the installer into deploy/, its script-relative DIR went one level too
      deep, and the unit it would write named deploy/warehouse/midnight_halt.py —
      a file that does not exist — behind a fully green checker. M4 RUNS the real
      installer in a scratch tree with `sudo` STUBBED and inspects the unit it
      writes. Born red at r19 on M4 and M4c; M4a/M4b are controls.
      ⚠️ THE GUARD IS THE FIRST CHECK, NOT AN AFTERTHOUGHT: if `sudo` does not
      resolve to the stub the installer is NOT RUN, because a checker that could
      install a live timer during a land is OTV4TEST r13's defect (a fixture
      reaching a live store) with a worse blast radius. The count printed at the
      end is now COUNTED rather than a literal that silently rots.
v1.0  2026-09-06 — r289 / EOD.3.

🔴 THIS SCRIPT'S ONLY JOB IS TO STOP A MACHINE, so the cases are about the two
ways that goes wrong: halting a box that was deliberately held up, and NOT
halting one that was forgotten.

⚠️ IT MUST NOT ACQUIRE THE 16:45 PATH'S MACHINERY. `self_close` drains,
verifies, and stays up if short — all correct for a CLOSE, all wrong for a
backstop, because every one of those steps is a way to hang. M3 pins that this
file never imports boto3, never touches S3, and never calls the purge.
"""
import os
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []
RAN = []

# A STUB `sudo` for M4. `tee` writes into the scratch etc/, `systemctl` and `rm`
# are logged and never executed, anything else is REFUSED — and MH_ETC must be
# set, so a stub that somehow runs without it cannot write to "/".
_STUB_SUDO = """#!/usr/bin/env bash
: "${MH_ETC:?stub sudo refuses to run without MH_ETC}"
case "$1" in
  tee)       exec tee "$MH_ETC/$(basename "$2")" >/dev/null ;;
  systemctl) echo "[stub] systemctl ${*:2}"; exit 0 ;;
  rm)        echo "[stub] rm ${*:2}"; exit 0 ;;
  *)         echo "[stub] REFUSED: $*" >&2; exit 1 ;;
esac
"""


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def _run(env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    r = subprocess.run([sys.executable,
                        os.path.join(_root, "warehouse", "midnight_halt.py"),
                        "--dry-run"],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def main():
    # ══ 🔴 M1 — IT HALTS BY DEFAULT ══════════════════════════════════════
    with tempfile.TemporaryDirectory() as tmp:
        rc, out = _run({"OT_NO_MIDNIGHT_HALT": os.path.join(tmp, "absent")})
        check("M1 with no hold flag it would halt", rc == 0 and "would run" in out,
              f"rc={rc}")
        check("M1b ...via `shutdown`, the same mechanism self_close uses",
              "shutdown -h now" in out)

    # ══ 🔴 M2 — A HOLD FLAG KEEPS IT UP, SILENTLY AND SUCCESSFULLY ═══════
    # The one night the operator wants a box up all night is the night this
    # must not fight him. A held box is EXPECTED, so it must not read as a
    # failure — a timer that complains teaches him to stop reading its log.
    with tempfile.TemporaryDirectory() as tmp:
        flag = os.path.join(tmp, "NO_MIDNIGHT_HALT")
        open(flag, "w").close()
        rc, out = _run({"OT_NO_MIDNIGHT_HALT": flag})
        check("M2 a hold flag stops it halting", rc == 0 and "staying up" in out,
              f"rc={rc}")
        check("M2b ...and exits 0, because a held box is expected, not a fault",
              rc == 0)

    # ══ 🔴 M3 — IT HAS NONE OF THE 16:45 PATH'S MACHINERY ════════════════
    # Every step self_close takes is a way to hang. A backstop that can hang is
    # not a backstop.
    # ⚠️ ANCHORED ON CODE, NOT ON MENTIONS. A first cut banned the STRING
    # "boto3" and went red on the file's own note explaining why boto3 was
    # removed — the §20 trap, in a checker written to avoid it. An import is a
    # dependency; a sentence about one is documentation.
    src = open(os.path.join(_root, "warehouse", "midnight_halt.py")).read()
    for bad, why in (("import boto3", "no AWS client — no IAM, no network"),
                     ("from warehouse import s3_push", "no drain"),
                     ("import s3_push", "no drain"),
                     ("retention_purge.main", "no purge"),
                     ('urlopen("http://169.254', "no IMDS round trip")):
        check(f"M3 it does not use `{bad}` ({why})", bad not in src)

    # ══ 🔴 M4 — THE INSTALLER RENDERS A UNIT THAT CAN RUN (OTV4TEST r21) ══
    # M1-M3 test the script. Nothing tested what INSTALLS it, and r14 broke that
    # silently: moved into deploy/, the installer's script-relative DIR named
    # deploy/warehouse/midnight_halt.py in ExecStart. So the REAL installer is
    # RUN here — in a scratch copy of the repo layout, with `sudo` stubbed — and
    # the unit it writes is read back. Rendering it, not reasoning about it, is
    # what showed two of the three wrong paths were rescued by accident and only
    # the script path was fatal.
    import shutil
    with tempfile.TemporaryDirectory() as tmp:
        tree, etc, stub = (os.path.join(tmp, d) for d in ("repo", "etc", "stub"))
        for d in (os.path.join(tree, "deploy"), os.path.join(tree, "warehouse"),
                  os.path.join(tree, "data"), etc, stub):
            os.makedirs(d)
        shutil.copy(os.path.join(_root, "deploy", "install_midnight_halt.sh"),
                    os.path.join(tree, "deploy", "install_midnight_halt.sh"))
        shutil.copy(os.path.join(_root, "warehouse", "midnight_halt.py"),
                    os.path.join(tree, "warehouse", "midnight_halt.py"))
        have_venv = os.path.isdir(os.path.join(_root, "venv"))
        if have_venv:
            os.symlink(os.path.join(_root, "venv"), os.path.join(tree, "venv"))
        sudo = os.path.join(stub, "sudo")
        with open(sudo, "w") as f:
            f.write(_STUB_SUDO)
        os.chmod(sudo, 0o755)
        path = stub + os.pathsep + "/usr/bin" + os.pathsep + "/bin"

        resolved = shutil.which("sudo", path=path)
        guard = resolved == sudo
        check("M4a GUARD: `sudo` resolves to the STUB — nothing can reach the real /etc",
              guard, f"resolved={resolved}")
        if not guard:
            check("M4 the installer was NOT RUN, because the guard failed", False)
        else:
            subprocess.run(["bash", os.path.join(tree, "deploy", "install_midnight_halt.sh")],
                           capture_output=True, text=True, timeout=60,
                           env={"PATH": path, "MH_ETC": etc, "HOME": tmp})
            unit = os.path.join(etc, "optbot-midnight-halt.service")
            txt = open(unit).read() if os.path.exists(unit) else ""
            es = next((l.split("=", 1)[1] for l in txt.splitlines()
                       if l.startswith("ExecStart=")), "")
            parts = es.split()
            py, script = (parts[0], parts[-1]) if parts else ("", "")
            check("M4b the installer RENDERS a unit (run with sudo stubbed)",
                  bool(txt) and os.path.exists(os.path.join(etc, "optbot-midnight-halt.timer")))
            check("M4 the script the unit's ExecStart names EXISTS — the r14 defect",
                  bool(script) and os.path.isfile(script),
                  es.replace(tree, "<repo>") or "no ExecStart")
            if have_venv:
                check("M4c ...run by the repo's OWN venv python, not whatever python3 the "
                      "installing shell had on PATH",
                      py == os.path.join(tree, "venv", "bin", "python"),
                      py.replace(tree, "<repo>"))
            else:
                # NOT A PASS AND NOT A FAIL: a red that means ENVIRONMENT teaches
                # the operator to skip reds (§36). Said out loud, by name.
                print("  SKIP  M4c no venv at the repo root in this environment — "
                      "the interpreter cannot be checked here")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
