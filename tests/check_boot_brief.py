#!/usr/bin/env python3
"""
tests/check_boot_brief.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.3  2026-10-25  OTV5 r6 (BOOT.9) — RE-POINTED, NOT DROPPED (WA §38.4): B6/B7 pin the OTV5 daily brief. B6: still symbol
      agnostic with BOX IDENTITY and the operator's boot order, and now the observe-only role ("NO TRADING DECISIONS",
      "## WHO OWNS WHAT", 1-REPORTER the custodian) and the push rule as the operator's switch (OT_S3_PUSH=0 named as
      the standalone guard); the predecessor's "NO TEST BOX PUSHES" and its QQQ-TEST-as-controller lines must be ABSENT.
      B7: the awake announcement is still the LAST step, and every code fix goes through 1-REPORTER.
v1.2  2026-10-04  OTV4TEST r233 — B7: the wake announcement is the LAST boot step and every code fix goes through
      QQQ-TEST; B8: deploy/claude-user-settings-pull-only.json denies git push and the lander, and grants nothing
      QQQ-TEST alone holds (the lander, the wake tool), and keeps the hook, the model and the S3 hard deny.
v1.1  2026-10-03  OTV4TEST r232 — ONE AGNOSTIC BRIEF: HANDOFF_SPX.md is retired. B2 uses docs/FIRST_BOOT.md as the
      override target (the switch stays); B6 now pins HANDOFF.md as symbol agnostic.
v1.0  2026-10-03  OTV4TEST r231 (BOOT.7) — A BOX CAN BOOT FROM ITS OWN BRIEF.

  SPX-TEST's first session believed it was QQQ-TEST: every box read docs/HANDOFF.md.
  B1  OT_BRIEF unset -> docs/HANDOFF.md (QQQ-TEST unchanged)
  B2  OT_BRIEF=<a .md under docs/> -> that file (docs/FIRST_BOOT.md as the fixture)
  B3  a missing file, a file outside docs/, a non-.md -> HANDOFF.md, said on stderr
  B4  the first-boot marker still wins over OT_BRIEF
  B5  the installer writes OT_BRIEF into the unit only when it is set
  B6  docs/HANDOFF.md is SYMBOL AGNOSTIC and OBSERVE-ONLY: BOX IDENTITY, WHO OWNS WHAT (1-REPORTER custody, no trading
      decisions), the push as the operator's switch, the boot order; no predecessor controller or no-push lines
  B7  the boot order ends with the awake announcement, after the sweep / alert watch / box safety; fixes go through 1-REPORTER
  B8  the pull-only user settings: push and the lander denied, no QQQ-TEST-only grant, hook/model/S3 hard deny kept
  B9  no action on the box: service control, pulls, configure.sh and broker-credential tools denied, none allowed (OTV5 r6)
Fresh interpreter per case. Run: python3 tests/check_boot_brief.py
"""
import json, os, subprocess, sys, tempfile
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []
def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])
_P = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1])
import tools.claude_boot as cb
b, first = cb.choose_brief()
print("@@" + json.dumps([os.path.relpath(cb.BRIEF, sys.argv[1]), os.path.relpath(b, sys.argv[1]), first]))
'''
def run(brief=None, marker=False):
    env = {k: v for k, v in os.environ.items() if k not in ("OT_BRIEF", "OT_FIRST_BOOT_MARKER")}
    d = tempfile.mkdtemp(prefix="check_boot_brief_")
    m = os.path.join(d, "first_boot")
    if marker:
        open(m, "w").close()
    env["OT_FIRST_BOOT_MARKER"] = m
    if brief is not None:
        env["OT_BRIEF"] = brief
    r = subprocess.run([sys.executable, "-c", _P, _root], env=env, capture_output=True, text=True, timeout=60)
    line = [x for x in r.stdout.splitlines() if x.startswith("@@")]
    return (json.loads(line[0][2:]) if line else None), r.stderr
def main():
    try:
        got, _ = run()
        check("B1 unset -> docs/HANDOFF.md", got == ["docs/HANDOFF.md", "docs/HANDOFF.md", False], str(got))
        got, _ = run("docs/FIRST_BOOT.md")
        check("B2 OT_BRIEF=<a .md under docs/> is the brief", got == ["docs/FIRST_BOOT.md", "docs/FIRST_BOOT.md", False], str(got))
        bad = []
        for v in ("docs/NO_SUCH.md", "README.md", "tools/claude_boot.py", "docs/../README.md"):
            g, err = run(v)
            if g is None or g[1] != "docs/HANDOFF.md" or "OT_BRIEF" not in err:
                bad.append((v, g, err[-80:]))
        check("B3 missing / outside docs / not .md fall back to HANDOFF.md, named on stderr", not bad, str(bad))
        got, _ = run("docs/WORKING_AGREEMENT.md", marker=True)
        check("B4 the first-boot marker still wins", got is not None and got[1] == "docs/FIRST_BOOT.md" and got[2] is True, str(got))
        src = open(os.path.join(_root, "deploy", "install_claude_boot.sh")).read()
        check("B5 the installer carries OT_BRIEF only when set", "${OT_BRIEF:+Environment=OT_BRIEF=$OT_BRIEF}" in src)
        h = open(os.path.join(_root, "docs", "HANDOFF.md")).read()
        check("B6 HANDOFF.md is symbol agnostic and observe-only: identity read at boot, the push switch, the operator's boot order, 1-REPORTER custody",
              "You exist on QQQ-TEST" not in h and "## BOX IDENTITY" in h and "NO TEST BOX PUSHES" not in h
              and "OT_S3_PUSH=0" in h and "tell me it's mandate, then notify you that it's awake" in h
              and "## WHO OWNS WHAT" in h and "NO TRADING DECISIONS" in h and "custodian of OTV5 is 1-REPORTER" in h
              and "QQQ-TEST is the one box that lands" not in h and "GENESIS-TEST" not in h)
        import re
        steps = re.findall(r"^(\d)\. (.*)$", h.split("## EVERY BOOT", 1)[1].split("FIRST, CATCH UP", 1)[0], re.M)
        last = steps[-1] if steps else ("", "")
        sweep_i = [i for i, (_, t) in enumerate(steps) if "sweep" in t and "alert watch" in t and "box-safety" in t]
        check("B7 the awake announcement is the LAST boot step, after the sweep/alert watch/box safety; fixes go through 1-REPORTER",
              "announce that you are awake" in last[1] and "only after steps 1-" in last[1]
              and sweep_i and sweep_i[0] == len(steps) - 2
              and not any("awake" in t for _, t in steps[:-1])
              and "EVERY code fix MUST go through 1-REPORTER" in h, str(steps))
        sp = os.path.join(_root, "deploy", "claude-user-settings-pull-only.json")
        raw = open(sp).read()
        u = json.loads(raw)
        pm = u["permissions"]
        hard = u["autoMode"]["hard_deny"]
        secret = re.compile(r"(sk-ant-|ghp_|github_pat_|xox[bp]-|AKIA[0-9A-Z]{12}|[A-Za-z0-9+/]{60,}={0,2})")
        check("B8 pull-only settings: push + lander denied, no QQQ-TEST-only grant, hook/model/S3 rule kept",
              {"Bash(git push)", "Bash(git push *)", "Bash(LAND_ARCHIVE=*)"} <= set(pm["deny"])
              and not any("land.sh" in a or "LAND_ARCHIVE" in a or "wake_box" in a or "git push" in a for a in pm["allow"] + pm.get("ask", []))
              and not any("landing an OPERATOR-APPROVED delivery" in a for a in u["autoMode"]["allow"])
              and any("PULL-ONLY BOX" in x for x in hard) and any("S3 warehouse" in x for x in hard)
              and any("printing credentials" in x for x in hard)
              and "UserPromptSubmit" in u.get("hooks", {}) and u.get("model") and u.get("remoteControlAtStartup") is True
              and pm.get("defaultMode") == "auto"
              and not secret.search(raw) and "parked_r110" not in raw)
        # B9 (v1.3, OTV5 r6) — NO ACTION ON THE BOX: the operator, 2026-10-25, "a trading box under your control will
        # not be making repo decisions or trading decisions". Nothing that starts, stops or restarts a service, pulls,
        # runs configure.sh or runs a tool under the bot's broker credentials may be allowed or merely asked; each is DENIED.
        _deny = set(pm["deny"])
        _need = {"Bash(sudo systemctl start *)", "Bash(sudo systemctl stop *)", "Bash(sudo systemctl restart *)",
                 "Bash(sudo systemctl enable *)", "Bash(sudo systemctl disable *)", "Bash(git pull*)",
                 "Bash(bash configure.sh*)", "Bash(./configure.sh*)", "Bash(*run_with_bot_env.py*)"}
        _loose = [a for a in pm["allow"] + pm.get("ask", [])
                  if "systemctl start" in a or "systemctl stop" in a or "systemctl restart" in a or "daemon-reload" in a
                  or "run_with_bot_env" in a or "git pull" in a or "configure.sh" in a]
        _am = [a for a in u["autoMode"]["allow"] if "38.2 GRANTED" in a or "the bake on this box" in a]
        check("B9 no action on the box: service starts/stops/restarts, pulls, configure.sh and broker-credential tools DENIED, none allowed",
              _need <= _deny and not _loose and not _am and any("NO TRADING DECISIONS" in x for x in u["autoMode"]["hard_deny"]),
              f"missing deny {sorted(_need - _deny)}; loose {_loose}; auto-allow {[x[:40] for x in _am]}")
    except Exception as exc:  # noqa: BLE001
        check("B0 (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {sorted(set(FAILED))}"); return 1
    print("\nGREEN — one symbol-agnostic brief; the OT_BRIEF override still works"); return 0
if __name__ == "__main__":
    sys.exit(main())
