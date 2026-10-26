#!/usr/bin/env python3
"""tests/check_land_spec_parse.py — v5.1
v5.1  2026-10-25  (DEP.2 mirror, HYG.14) — L15: a POS whose text begins with `-` (the payload carries "--dash-led line")
      passes the content gate; L16: a NEG of that same present text FAILS as STILL PRESENT (grep read it as an option:
      the POS refused and the NEG could never fire). L17: a CHECK that calls tempfile.mkdtemp() and records the path got
      a dir OUTSIDE /tmp's top level (under the land's per-check TMPDIR), and that dir is GONE once the land returns.
      Born red on ffe10bf at L15, L16 and L17.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
THE LAND REGENERATES docs/ENV.md, BEFORE THE CHECKS, AND FAILS CLOSED (DOC.35).

v1.2  2026-10-25  OTV5 r5 — L12: the scratch repo carries a stub tests/gen_env_doc.py that writes a marker into docs/ENV.md
      (committed stale); after the land the working tree's docs/ENV.md carries the marker, i.e. the lander ran the
      generator after the payload landed. L13: a spec with check_env_doc in CHECK plus the same drift still LANDS, because
      the regeneration runs before the check stage. L14: a generator that exits 1 refuses the land by name, HEAD untouched
      (QQQ-TEST MSG-QQQ-1025-05). Born red on land.sh v1.23 at L12, L13 and L14.

TWO CHECKOUTS WITH THE SAME MARKERS ARE REFUSED; ORIGIN SAYS WHICH (LAND.2).

v1.1  2026-10-24  OTV5 r1 — L6-L8 drive the v1.22 resolver: the scratch HOME gains a SECOND marker-carrying
      checkout (`twin`, cloned from its own bare origin2.git). L6 no ORIGIN -> AMBIGUOUS refusal naming both,
      HEAD untouched; L7 `ORIGIN origin2` resolves the land into the twin (the repo: line names it); L8 an ORIGIN
      that matches neither is refused. L9 a LONE checkout whose origin disagrees with a declared ORIGIN is refused (a
      resolver that refuses only on 0 or 2+ matches survives L6-L8). L10 _origin_matches on the suffix boundary: the
      declared owner/repo matches the https, https-with-.git and ssh spellings and NOT a longer owner or repo name
      (kills a bare endswith and a missing .git strip). L11 the bookkeeping checker is THE TARGET TREE'S OWN
      tools/check_land_discipline.py when it carries one: a stub at $HOME/day_trader_pro that always fails must not be
      the one consulted (QQQ-TEST MSG-QQQ-1024-45). Born red on v1.21 at L6, L7, L8, L9 and L11 (it landed into the first
      match, never read ORIGIN, and asked day_trader_pro's checker first).
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


def _world(spec_body, payload=("payload.txt", "NEWCONTENT\n"), twin=False, checkers=False, envdoc=False,
           tmpcheck=False):
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
    if checkers:                               # v1.1 / L11 — the tree's OWN checker, and a hostile stub beside it
        own = os.path.join(repo, "tools")
        os.makedirs(own)
        open(os.path.join(own, "check_land_discipline.py"), "w").write(
            "import sys\nprint('OWN-CHECKER consulted', sys.argv[1:])\nsys.exit(0)\n")
        os.makedirs(os.path.join(repo, "docs"))             # the lander appends the ledger BEFORE it asks the checker
        open(os.path.join(repo, "docs", "GENESIS.md"), "w").write("# ledger\n\n| rev | what |\n|---|---|\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "own checker")
        _git(repo, "push", "-q", "origin", "HEAD:refs/heads/master")
        stub = os.path.join(home, "day_trader_pro", "tools")
        os.makedirs(stub)
        open(os.path.join(stub, "check_land_discipline.py"), "w").write(
            "import sys\nprint('STUB-DTP consulted')\nsys.exit(1)\n")
    if envdoc:                                 # v1.2 / L12 — a generated doc the land must regenerate
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
        os.makedirs(os.path.join(repo, "docs"), exist_ok=True)
        if envdoc == "fail":                   # L14: a generator that exits 1 and writes nothing
            open(os.path.join(repo, "tests", "gen_env_doc.py"), "w").write("import sys\nsys.exit(1)\n")
        else:
            open(os.path.join(repo, "tests", "gen_env_doc.py"), "w").write(
                "import os\nopen(os.path.join('docs', 'ENV.md'), 'w').write('ENV-REGEN\\n')\n")
        # a stub check_env_doc: green only once the generator has run (L13 lists it in CHECK)
        open(os.path.join(repo, "tests", "check_env_doc.py"), "w").write(
            "import sys\nsys.exit(0 if 'ENV-REGEN' in open('docs/ENV.md').read() else 1)\n")
        open(os.path.join(repo, "docs", "ENV.md"), "w").write("STALE\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "env doc")
        _git(repo, "push", "-q", "origin", "HEAD:refs/heads/master")
    if tmpcheck:                               # v5.1 / L17 — a CHECK that leaks a mkdtemp dir and says where
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
        open(os.path.join(repo, "tests", "check_tmpleak.py"), "w").write(
            "import os, tempfile\nd = tempfile.mkdtemp(prefix='leak_')\n"
            "open(os.path.join(os.environ['HOME'], 'tmpleak.txt'), 'w').write(d)\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "tmp leak check")
        _git(repo, "push", "-q", "origin", "HEAD:refs/heads/master")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                         capture_output=True, text=True).stdout.strip()
    if twin:                                   # v1.1 — a SECOND checkout carrying the same markers
        bare2 = os.path.join(root, "origin2.git")
        subprocess.run(["git", "init", "--bare", "-q", bare2], check=True)
        repo2 = os.path.join(home, "twin")
        subprocess.run(["git", "clone", "-q", bare2, repo2], check=True)
        _git(repo2, "config", "user.email", "gate@local")
        _git(repo2, "config", "user.name", "gate")
        for m in (".landgate_a", ".landgate_b"):
            open(os.path.join(repo2, m), "w").write("marker\n")
        open(os.path.join(repo2, "tracked.txt"), "w").write("OLDCONTENT\n")
        _git(repo2, "add", "-A")
        _git(repo2, "commit", "-qm", "base")
        _git(repo2, "push", "-q", "origin", "HEAD:refs/heads/master")
        _git(repo2, "branch", "--set-upstream-to=origin/master")
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
    try:                                       # v5.1 — where a CHECK's mkdtemp went, and whether it survived
        _leak = open(os.path.join(home, "tmpleak.txt")).read().strip()
        _TMPLEAK.update(path=_leak, survived=os.path.exists(_leak))
        if _leak.startswith("/tmp/leak_"):     # a pristine lander leaks it into /tmp: do not leave it there
            shutil.rmtree(_leak, ignore_errors=True)
    except OSError:
        pass
    try:                                       # v1.2 — what the land left in the generated doc
        _ENVDOC["after"] = open(os.path.join(repo, "docs", "ENV.md")).read()
    except OSError:
        _ENVDOC["after"] = None
    shutil.rmtree(root, ignore_errors=True)
    return r.returncode, out, sha, head


_ENVDOC = {}
_TMPLEAK = {}


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

# ── L6-L8 (v1.1 / LAND.2) — two checkouts carry the markers ────────────────
rc, out, sha, head = _land(BASE_SPEC.format(extra="POS    payload.txt|NEWCONTENT"), twin=True)
_both = "AMBIGUOUS" in out and "/target" in out and "/twin" in out
check("L6 two marker-carrying checkouts and no ORIGIN -> refused as AMBIGUOUS, both named, HEAD untouched",
      rc != 0 and _both and sha == head,
      f"rc={rc} named={_both} {sha[:8]}->{head[:8]}")

rc, out, sha, head = _land(BASE_SPEC.format(extra="ORIGIN origin2\nPOS    payload.txt|NEWCONTENT"), twin=True)
_res = [l.split("repo:")[1].strip() for l in out.splitlines() if "repo:" in l]
check("L7 ORIGIN naming the twin's origin resolves the land INTO the twin",
      bool(_res) and _res[0].endswith("/twin") and "AMBIGUOUS" not in out,
      _res[0] if _res else "no repo line")

rc, out, sha, head = _land(BASE_SPEC.format(extra="ORIGIN nowhere/else\nPOS    payload.txt|NEWCONTENT"), twin=True)
check("L8 an ORIGIN that matches no checkout is refused", rc != 0 and "ORIGIN nowhere/else matches 0" in out, "")

# ── L9 — ONE checkout, ORIGIN disagrees -> refused (no twin) ───────────────
rc, out, sha, head = _land(BASE_SPEC.format(extra="ORIGIN nowhere/else\nPOS    payload.txt|NEWCONTENT"))
check("L9 a LONE checkout whose origin disagrees with the declared ORIGIN is refused, HEAD untouched",
      rc != 0 and "ORIGIN nowhere/else matches 0 of the 1" in out and sha == head,
      f"rc={rc} {sha[:8]}->{head[:8]}")

# ── L10 — the suffix boundary of _origin_matches, called as bash does ──────
_fn = subprocess.run(["sed", "-n", "/^_origin_matches()/,/^}/p", os.path.join(_root, "tools", "land.sh")],
                     capture_output=True, text=True).stdout
def _m(want, url):
    r = subprocess.run(["bash", "-c", _fn + '\n_origin_matches "$1" "$2"', "_", want, url])
    return r.returncode == 0
_yes = ["https://github.com/TX-9AI/OTV5.git", "https://github.com/TX-9AI/OTV5", "git@github.com:TX-9AI/OTV5.git"]
_no = ["https://github.com/TX-9AI/XOTV5.git", "https://github.com/ATX-9AI/OTV5.git", "https://github.com/TX-9AI/OTV5x.git"]
_bad = [u for u in _yes if not _m("TX-9AI/OTV5", u)] + [u for u in _no if _m("TX-9AI/OTV5", u)]
check("L10 ORIGIN TX-9AI/OTV5 matches the https / .git / ssh spellings and no longer owner or repo name",
      bool(_fn) and not _bad, "" if (_fn and not _bad) else (f"wrong on: {_bad}" if _fn else "no _origin_matches in land.sh"))

# ── L11 — the bookkeeping checker is the target tree's own ─────────────────
rc, out, sha, head = _land(BASE_SPEC.format(extra="POS    payload.txt|NEWCONTENT"), checkers=True)
check("L11 the discipline checker consulted is the target tree's own tools/check_land_discipline.py, not $HOME/day_trader_pro's",
      "OWN-CHECKER consulted" in out and "STUB-DTP" not in out,
      "" if ("OWN-CHECKER consulted" in out and "STUB-DTP" not in out) else
      ("stub consulted" if "STUB-DTP" in out else "own checker never ran"))

# ── L12 (v1.2 / DOC.35) — the land regenerates docs/ENV.md ─────────────────
rc, out, sha, head = _land(BASE_SPEC.format(extra="POS    payload.txt|NEWCONTENT"), envdoc=True)
_env_after = _ENVDOC.get("after") or ""
check("L12 the land runs tests/gen_env_doc.py after the payload lands (docs/ENV.md regenerated, 'env doc: regenerated' said)",
      "ENV-REGEN" in _env_after and "env doc: regenerated" in out,
      "" if "ENV-REGEN" in _env_after else f"docs/ENV.md after the land: {_env_after.strip()[:40]!r}")

# ── L13 — check_env_doc in CHECK plus a drifting edit still LANDS (regen runs before the checks) ──
rc, out, sha, head = _land(BASE_SPEC.format(extra="CHECK  tests/check_env_doc.py\nPOS    payload.txt|NEWCONTENT"), envdoc=True)
check("L13 a spec listing check_env_doc in CHECK passes the check stage on the drift the regeneration fixes",
      "check: tests/check_env_doc.py PASS" in out and "CHECK FAILED" not in out,
      "the check stage refused it" if "CHECK FAILED" in out else "check stage never ran")

# ── L14 — a generator that fails refuses the land by name; nothing is committed ──
rc, out, sha, head = _land(BASE_SPEC.format(extra="POS    payload.txt|NEWCONTENT"), envdoc="fail")
check("L14 a failing tests/gen_env_doc.py refuses the land by name, HEAD untouched",
      rc != 0 and "ENV DOC regeneration failed" in out and sha == head,
      f"rc={rc} {sha[:8]}->{head[:8]}")

# ── L15/L16 (v5.1 / DEP.2 mirror) — a POS/NEG text that begins with "-" ────
_dash = ("payload.txt", "--dash-led line\n")
rc, out, sha, head = _land(BASE_SPEC.format(extra="POS    payload.txt|--dash-led line"), payload=_dash)
check("L15 a POS whose text begins with '-' is matched as text (the content gate passes)",
      "content gate: pass" in out and "MISSING" not in out,
      "" if "content gate: pass" in out else "refused: " + " | ".join(l.strip() for l in out.splitlines() if "MISSING" in l)[:120])
rc, out, sha, head = _land(BASE_SPEC.format(extra="NEG    payload.txt|--dash-led line"), payload=_dash)
check("L16 a NEG whose text begins with '-' and IS present fails as STILL PRESENT, HEAD untouched",
      rc != 0 and "STILL PRESENT" in out and sha == head,
      f"rc={rc} still_present={'STILL PRESENT' in out} {sha[:8]}->{head[:8]}")

# ── L17 (v5.1 / HYG.14) — a CHECK's mkdtemp lands under a per-check TMPDIR that is removed ──
rc, out, sha, head = _land(BASE_SPEC.format(extra="CHECK  tests/check_tmpleak.py\nPOS    payload.txt|NEWCONTENT"),
                           tmpcheck=True)
_lp = _TMPLEAK.get("path", "")
check("L17 a CHECK's tempfile.mkdtemp() is NOT at /tmp's top level and is GONE after the land",
      "check: tests/check_tmpleak.py PASS" in out and bool(_lp)
      and os.path.dirname(_lp) != "/tmp" and not _TMPLEAK.get("survived", True),
      f"path={_lp!r} survived={_TMPLEAK.get('survived')}")

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
