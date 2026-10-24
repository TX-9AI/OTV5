#!/usr/bin/env python3
"""tests/check_land_spec_parse.py — v1.0
A `NEG` THAT CANNOT BE EVALUATED IS REFUSED, NOT PASSED (LAND.3).

v1.0  2026-09-19  OTV4TEST r65 — every directive in `land.spec` was parsed by
      stripping EXACTLY ONE SPACE (`${line#NEG }`), while the format block in
      `tools/land.sh` itself documents COLUMN-ALIGNED examples. A spec written
      from that documentation mangled its own paths, and the two directives then
      failed in OPPOSITE directions: `POS` greps with `!` so a missing file
      FLAGS (it refused the r61 archive, loudly); `NEG` greps without `!` and
      swallows the error, so a missing file reads as "the string is absent" and
      THE ASSERTION PASSES. A NEG is the only thing proving superseded code is
      gone, so a vacuous one certifies that without looking.

🔑 IT DRIVES THE REAL LANDER. Reading the source would prove nothing about what
bash does with it (§21). Each case runs `bash land.sh` end to end against a
throwaway git repo.

🔴 SAFETY, AND IT IS NOT OPTIONAL. `land.sh` finds its target by scanning
`"$HOME"/*/` for the spec's REPO markers — and the REAL checkout carries
`docs/GENESIS-TEST.md`. So every case runs with **HOME redirected into a scratch
tree** and markers (`.landgate_a`/`.landgate_b`) that exist NOWHERE else, and L0
ABORTS THE WHOLE FILE if the lander ever names a repo outside that tree. A gate
that could reach the live checkout is worse than no gate.

  L0  the harness resolves ONLY the scratch repo (guard; runs first)
  L1  an ALIGNED-COLUMN spec parses — POS is satisfied, the gate passes
  L2  a NEG whose string IS still present fails (the gate still works)
  L3  a NEG naming a MISSING file is REFUSED          <- the fail-open closure
  L4  a POS naming a MISSING file is refused          (control: red both sides)
  L5  a refused land leaves the repo's HEAD untouched

Born red at 71b89ab on L3 (there, the unresolvable NEG PASSES).
Run:  python3 tests/check_land_spec_parse.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def _git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _world(spec_body, payload=("payload.txt", "NEWCONTENT\n")):
    """A throwaway HOME containing one uniquely-marked repo, plus a stage."""
    root = tempfile.mkdtemp(prefix="landgate-")
    home = os.path.join(root, "home")
    os.makedirs(home)
    bare = os.path.join(root, "origin.git")
    subprocess.run(["git", "init", "--bare", "-q", bare], check=True)
    repo = os.path.join(home, "target")
    subprocess.run(["git", "clone", "-q", bare, repo], check=True)
    _git(repo, "config", "user.email", "gate@local")
    _git(repo, "config", "user.name", "gate")
    for m in (".landgate_a", ".landgate_b"):
        open(os.path.join(repo, m), "w").write("marker\n")
    open(os.path.join(repo, "tracked.txt"), "w").write("OLDCONTENT\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "push", "-q", "origin", "HEAD:refs/heads/master")
    _git(repo, "branch", "--set-upstream-to=origin/master")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                         capture_output=True, text=True).stdout.strip()
    stage = os.path.join(root, "stage")
    half = os.path.join(stage, "half")
    os.makedirs(half)
    shutil.copy(os.path.join(_root, "tools", "land.sh"),
                os.path.join(stage, "land.sh"))
    open(os.path.join(half, payload[0]), "w").write(payload[1])
    open(os.path.join(half, "land.spec"), "w").write(spec_body.replace("@SHA@", sha))
    return root, home, repo, stage, sha


def _land(spec_body, **kw):
    root, home, repo, stage, sha = _world(spec_body, **kw)
    env = dict(os.environ)
    env["HOME"] = home
    env.pop("LAND_ARCHIVE", None)
    env.pop("LAND_STAGE", None)
    r = subprocess.run(["bash", os.path.join(stage, "land.sh"), "half"],
                       capture_output=True, text=True, env=env, cwd=root,
                       timeout=180)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          capture_output=True, text=True).stdout.strip()
    out = r.stdout + r.stderr
    shutil.rmtree(root, ignore_errors=True)
    return r.returncode, out, sha, head


BASE_SPEC = """REPO   .landgate_a .landgate_b
BASE   @SHA@
REV    rTEST
DESC   a gate fixture, never landed
{extra}
"""

# ── L0 — the guard. Nothing below may run if this fails. ───────────────────
rc, out, sha, head = _land(BASE_SPEC.format(extra="POS    payload.txt|NEWCONTENT"))
resolved = [l.split("repo:")[1].strip() for l in out.splitlines() if "repo:" in l]
safe = bool(resolved) and all("landgate-" in p for p in resolved)
check("L0 the harness resolves ONLY a scratch repo", safe,
      resolved[0] if resolved else "no repo line — lander did not run")
if not safe:
    print("\n  RED — ABORTING: the lander did not resolve to a scratch repo.")
    sys.exit(1)

check("L1 an aligned-column spec parses (POS satisfied, gate passes)",
      "content gate: pass" in out, out.strip().splitlines()[-1][:60] if out else "")

rc, out, sha, head = _land(BASE_SPEC.format(
    extra="NEG    tracked.txt|OLDCONTENT"))
check("L2 a NEG whose string IS present fails",
      rc != 0 and "STILL PRESENT" in out, "")

rc, out, sha, head = _land(BASE_SPEC.format(
    extra="NEG    no_such_file.txt|anything"))
# ⚠️ THE DETAIL NAMES WHICH HALF FAILED. A first cut printed "refused" whenever
# the lander exited non-zero — which it does at base for an UNRELATED later
# reason — so the red line described the opposite of the finding. A diagnostic
# that contradicts its own diagnosis is the guard() defect r49 fixed in four
# checkers, and it is worth no less care in a detail string.
_named = "DOES NOT EXIST" in out
check("L3 a NEG naming a MISSING file is REFUSED (the fail-open closure)",
      rc != 0 and _named,
      "refused by name" if _named else
      "NOT refused for this reason — the NEG was never evaluated "
      f"(lander rc={rc}, which is a different failure)")

rc2, out2, sha2, head2 = _land(BASE_SPEC.format(
    extra="POS    no_such_file.txt|anything"))
check("L4 a POS naming a MISSING file is refused", rc2 != 0, "")

check("L5 a refused land leaves HEAD untouched", sha == head,
      f"{sha[:8]} -> {head[:8]}")

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
