#!/usr/bin/env python3
"""tests/check_push_deploy.py — v5.0
v5.0  2026-10-25  OTV5 r21 (DEPLOY.1) — `push.sh --deploy` DEPLOYS AN OTV5 BOX. It chose the service by matching
      "options_trader" in the origin URL, so on TX-9AI/OTV5 it refused ("Could not detect repo from git remote") and
      control's `fleet.py update` deployed 0/14 on 2026-10-25.

🔑 END TO END, OFFLINE. The REAL deploy/push.sh runs in a throwaway "box" whose origin is the real GitHub URL; a
temporary global git config rewrites that URL to a local bare repository (url.<bare>.insteadOf), a git shim makes
`remote get-url` report the configured URL as on a box, and fake `sudo` and `systemctl` on PATH record what would have
been restarted. Nothing leaves this machine and nothing real is touched.

  D1  an OTV5 box (origin https://github.com/TX-9AI/OTV5.git, origin.conf TX-9AI/OTV5) deploys: the tree moves to
      the remote's new commit and optionsbot is restarted
  D2  the old rule still holds: an options_trader_v4 remote is optionsbot
  D3  a crypto_trader remote is still cryptobot
  D4  a remote that is neither, and not the origin this tree names, still REFUSES and moves nothing

Born red on e6b42e1 (OTV5 r20) at D1.
Run:  python3 tests/check_push_deploy.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUSH = os.path.join(ROOT, "deploy", "push.sh")
_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


def sh(args, cwd, env):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)


def scenario(tmp, url, origin_repo):
    """-> (rc, moved, restarted_services, output)."""
    base = os.path.join(tmp, "s%d" % len(os.listdir(tmp)))
    os.makedirs(base)
    fake = os.path.join(base, "bin")
    os.makedirs(fake)
    log = os.path.join(base, "systemctl.log")
    with open(os.path.join(fake, "sudo"), "w") as fh:
        fh.write('#!/bin/bash\nexec "$@"\n')
    with open(os.path.join(fake, "systemctl"), "w") as fh:
        fh.write('#!/bin/bash\necho "$@" >> %s\n[ "$1" = "is-active" ] && echo active\nexit 0\n' % log)
    # `git remote get-url` applies url.insteadOf, so it would report the bare path; on a box it reports the URL.
    real_git = shutil.which("git")
    with open(os.path.join(fake, "git"), "w") as fh:
        fh.write('#!/bin/bash\nif [ "$1 $2" = "remote get-url" ]; then exec %s config --get "remote.$3.url"; fi\n'
                 'exec %s "$@"\n' % (real_git, real_git))
    for f in ("sudo", "systemctl", "git"):
        os.chmod(os.path.join(fake, f), 0o755)
    env = dict(os.environ, HOME=base, PATH=fake + os.pathsep + os.environ["PATH"],
               GIT_CONFIG_GLOBAL=os.path.join(base, "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    bare = os.path.join(base, "remote.git")
    seed = os.path.join(base, "seed")
    os.makedirs(os.path.join(seed, "deploy"))
    for n in ("main.py", "config.py"):
        open(os.path.join(seed, n), "w").write("# stub\n")
    shutil.copy(PUSH, os.path.join(seed, "deploy", "push.sh"))
    open(os.path.join(seed, "deploy", "origin.conf"), "w").write('OT_ORIGIN_REPO="%s"\n' % origin_repo)
    sh(["git", "init", "-q", "-b", "main"], seed, env)
    sh(["git", "add", "-A"], seed, env)
    sh(["git", "commit", "-qm", "one"], seed, env)
    sh(["git", "clone", "-q", "--bare", seed, bare], base, env)
    sh(["git", "config", "--global", "url.%s.insteadOf" % bare, url], base, env)
    box = os.path.join(base, "options-trader")
    sh(["git", "clone", "-q", bare, box], base, env)
    sh(["git", "remote", "set-url", "origin", url], box, env)
    open(os.path.join(seed, "main.py"), "a").write("# two\n")
    sh(["git", "commit", "-qam", "two"], seed, env)
    sh(["git", "push", "-q", bare, "main"], seed, env)
    want = sh(["git", "rev-parse", "HEAD"], seed, env).stdout.strip()
    before = sh(["git", "rev-parse", "HEAD"], box, env).stdout.strip()
    r = sh(["bash", "deploy/push.sh", "--deploy"], box, env)
    after = sh(["git", "rev-parse", "HEAD"], box, env).stdout.strip()
    calls = open(log).read().split("\n") if os.path.exists(log) else []
    restarted = [c.split()[1] for c in calls if c.startswith("restart ")]
    return r.returncode, (after == want and after != before), restarted, r.stdout + r.stderr


def main():
    tmp = tempfile.mkdtemp()
    try:
        rc, moved, rs, out = scenario(tmp, "https://github.com/TX-9AI/OTV5.git", "TX-9AI/OTV5")
        ck("D1", rc == 0 and moved and rs == ["optionsbot"], f"rc={rc} moved={moved} restarted={rs}")
        rc, moved, rs, _ = scenario(tmp, "https://github.com/TX-9AI/options_trader_v4.git", "TX-9AI/OTV5")
        ck("D2", rc == 0 and moved and rs == ["optionsbot"], f"rc={rc} moved={moved} restarted={rs}")
        rc, moved, rs, _ = scenario(tmp, "https://github.com/TX-9AI/crypto_trader.git", "TX-9AI/OTV5")
        ck("D3", rc == 0 and moved and rs == ["cryptobot"], f"rc={rc} moved={moved} restarted={rs}")
        rc, moved, rs, out = scenario(tmp, "https://github.com/TX-9AI/somebody_else.git", "TX-9AI/OTV5")
        ck("D4", rc != 0 and not moved and not rs and "Could not detect repo" in out,
           f"rc={rc} moved={moved} restarted={rs}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
    print("FAIL: " + " ".join(_fails) if _fails else "ALL PASS")
    sys.exit(1 if _fails else 0)
