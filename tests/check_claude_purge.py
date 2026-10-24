#!/usr/bin/env python3
"""tests/check_claude_purge.py — v1.2
v1.2  2026-10-04  OTV4TEST r235 — P11: a purge that archives NOTHING still says so ("scratch purge: archived 0"),
      driven through the real main() with the raiser, the recorder and the purge itself stubbed (nothing real
      is purged or raised). Silent-on-zero hid a run from SPX-TEST's agent (§0.5).
tmpfs IS PURGED BEFORE A THREAD STARTS, AND CLAUDE LAUNCHES ON THE SUBSCRIPTION.

v1.1  2026-09-23 — OTV4TEST r107. P9 RE-DERIVED TO THE STRONGER CONTRACT, NOT
      LOOSENED. It matched the literal `if a.dry_run or agent_alive():`, and
      r107 made the skip ALSO require that no `claude` process of this user is
      alive (`live_claude_pids()`), because `agent_alive()` asks about one tmux
      name and check_claude_boot B7 defeated it by overriding that name — ten
      times the real scratch root was purged under a running agent. P9 now
      requires BOTH terms in the gate and the pid scan feeding it, so dropping
      either one goes red.
      🔴 AND P1/P2 NOW ARCHIVE INTO A THROWAWAY HOME. They purged fixtures into
      the REAL ~/claude_scratch_archive (60 litter entries by 2026-09-23), and
      the archive name is stamped to the SECOND — so two purges inside one
      second collided: `shutil.move` nested the second `sessOLD` INSIDE the
      first (`20260923-011250-sessOLD/sessOLD` is on disk) or failed into the
      bare `except`, and P1/P2 went red on correct code. Reproduced on the
      unmodified r107 tool, 2 runs of 2 back to back. P8 already redirected
      HOME; P1 and P2 did not.

v1.0  2026-09-20 — OTV4TEST r70 (BOX.12 / AUTH.1).

🔴 WHY THIS EXISTS. `/tmp` is a **tmpfs — it is RAM**: 455 MB here of 908 MB
physical. The agent scratchpad path is keyed by SESSION ID
(`/tmp/claude-<uid>/<project>/<session-uuid>/scratchpad`), so every new session
mints a directory and NOTHING removes the old ones. One session reached 108 MB
in a day. This box was protected only by its daily reboot — tmpfs is volatile —
while the control box, which does not reboot daily, filled its tmpfs and then
**every Bash spawn died instantly with no stdout and no stderr**, because a
temp file is needed for the shell snapshot and the spawn fails before it
executes. Read/Write kept working, so the agent looked brain-dead rather than
out of space, with nothing logged anywhere (§0.5).

🔑 ORDER IS THE OPERATOR'S RULING AND IT IS NOT COSMETIC: **purge, THEN kill,
THEN launch.** If tmpfs is already full the tmux kill may not spawn either, so
freeing space first is what guarantees room for every step after it.

  P0  the purge REFUSES a root that is not /tmp/claude-<digits> (fail closed)
  P1  it removes a stale session directory
  P2  it NEVER removes the LIVE session's own directory (CLAUDE_SCRATCH)
  P3  free-space reporting returns a plausible figure
  P4  the boot status string carries the free-tmpfs figure, so it reaches the
      boot Telegram beside the IP with no change to alert_manager
  P5  every devtools launch site PURGES BEFORE IT KILLS — asserted on line
      order with comments stripped, because a comment naming a step is not the
      step (r37's finding about bake())
  P6  every `claude` launch site strips the API-key variables, so a stray
      export cannot silently move sessions onto metered credits
  P7  CONTROL: this checker never touches the box's real scratch root
  P8  it ARCHIVES rather than deletes — raised by the mainline control agent
      from a near-miss where a deleting purge would have destroyed an entire
      unlanded revision sitting in a handed-off session's scratchpad
  P9  a LIVE session skips the purge ENTIRELY. The first cut purged
      unconditionally while `bring_up()` returns "already running" WITHOUT
      killing anything — so starting the unit against a live session would
      have archived that running agent's working directory out from under it
  P10 the 14-day retention sweep is the only deleting path, and it is bounded

⚠️ TRANSCRIPTS ARE NOT AT RISK AND THAT IS MEASURED, NOT ASSUMED. They live on
EXT4 under `~/.claude/projects/` — a different filesystem — so the purge cannot
reach them and `tools/last_session.py` still reviews the previous thread after
a handoff. That is the property that makes purging safe to do aggressively.
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
        return False
    try:
        d = detail()
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)
    return ok


REAL_ROOT = "/tmp/claude-%d" % os.getuid()
_real_before = sorted(os.listdir(REAL_ROOT)) if os.path.isdir(REAL_ROOT) else None

try:
    _sp = importlib.util.spec_from_file_location(
        "_cb70", os.path.join(_root, "tools", "claude_boot.py"))
    cb = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(cb)
    _WHY = None
except Exception as exc:                                        # noqa: BLE001
    _WHY = "tools/claude_boot.py absent or unimportable: %s: %s" % (
        type(exc).__name__, exc)

    class _Absent:
        def __getattr__(self, n):
            raise RuntimeError(_WHY)

    cb = _Absent()


def _scratch():
    d = tempfile.mkdtemp(prefix="scratchtest_")
    os.makedirs(os.path.join(d, "sessOLD"), exist_ok=True)
    os.makedirs(os.path.join(d, "sessLIVE"), exist_ok=True)
    return d


guard("P0 the purge REFUSES a root outside /tmp/claude-<digits>",
      lambda: cb.purge_scratch("/etc")[0] == 0 and os.path.isdir("/etc"))


def _own_home():
    """A throwaway HOME, so a fixture's archive never lands in the real one."""
    home = tempfile.mkdtemp(prefix="fakehome_")
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    return home, old


def _restore_home(home, old):
    if old is not None:
        os.environ["HOME"] = old
    shutil.rmtree(home, ignore_errors=True)


def _p1():
    d = _scratch()
    home, old = _own_home()
    try:
        os.environ.pop("CLAUDE_SCRATCH", None)
        n, _ = cb.purge_scratch(d)
        return n == 2 and os.listdir(d) == []
    finally:
        _restore_home(home, old)
        shutil.rmtree(d, ignore_errors=True)


guard("P1 it removes stale session directories", _p1)


def _p2():
    d = _scratch()
    home, old = _own_home()
    try:
        os.environ["CLAUDE_SCRATCH"] = os.path.join(d, "sessLIVE")
        n, _ = cb.purge_scratch(d)
        return n == 1 and os.listdir(d) == ["sessLIVE"]
    finally:
        os.environ.pop("CLAUDE_SCRATCH", None)
        _restore_home(home, old)
        shutil.rmtree(d, ignore_errors=True)


guard("P2 it NEVER removes the LIVE session's own directory", _p2)

guard("P3 free-space reporting returns a plausible figure",
      lambda: isinstance(cb.tmpfs_free_mb("/tmp"), int) and cb.tmpfs_free_mb("/tmp") >= 0,
      lambda: "%s MB free on /tmp" % cb.tmpfs_free_mb("/tmp"))


def _src(name):
    return open(os.path.join(_root, name), encoding="utf-8").read()


def _nocomments(txt):
    return "\n".join(ln for ln in txt.splitlines()
                     if not ln.lstrip().startswith("#"))


guard("P4 the boot status carries the free-tmpfs figure",
      lambda: re.search(r'tmpfs %dM free|tmpfs %\dM free|"%s, tmpfs %dM free"',
                        _nocomments(_src("tools/claude_boot.py"))) is not None
      or "tmpfs %dM free" in _nocomments(_src("tools/claude_boot.py")))


def _p5():
    src = _nocomments(_src("devtools.sh")).splitlines()
    kills = [i for i, l in enumerate(src) if l.strip() == "_claude_kill_all_tmux"]
    purges = [i for i, l in enumerate(src) if l.strip() == "_claude_purge_scratch"]
    if not kills or len(purges) != len(kills):
        return False
    # every kill must have a purge on the line immediately before it
    return all((k - 1) in purges for k in kills)


guard("P5 every launch site PURGES BEFORE IT KILLS", _p5,
      lambda: "%d kill site(s)" % _nocomments(_src("devtools.sh")).count(
          "_claude_kill_all_tmux\n"))


def _p6():
    sh = _nocomments(_src("devtools.sh"))
    launches = [l for l in sh.splitlines() if "claude --remote-control" in l]
    if not launches:
        return False
    if not all("$CLAUDE_ENV" in l for l in launches):
        return False
    py = _nocomments(_src("tools/claude_boot.py"))
    return "ANTHROPIC_API_KEY" in py and "ENV_STRIP" in py


guard("P6 every claude launch strips the API-key variables (subscription)",
      _p6, lambda: "%d shell launch site(s)" % len(
          [l for l in _nocomments(_src("devtools.sh")).splitlines()
           if "claude --remote-control" in l]))

def _p8():
    """The purge must ARCHIVE, never delete — bytes have to still exist after."""
    d = _scratch()
    home = tempfile.mkdtemp(prefix="fakehome_")
    marker = os.path.join(d, "sessOLD", "unlanded_revision.txt")
    open(marker, "w").write("r401-style payload that must survive")
    old_home = os.environ.get("HOME")
    try:
        os.environ["HOME"] = home
        os.environ.pop("CLAUDE_SCRATCH", None)
        n, _ = cb.purge_scratch(d)
        arch = os.path.join(home, "claude_scratch_archive")
        found = []
        for dp, _dn, fn in os.walk(arch):
            found += [os.path.join(dp, f) for f in fn]
        survived = any(open(f).read().startswith("r401-style") for f in found)
        return n == 2 and os.listdir(d) == [] and survived
    finally:
        if old_home is not None:
            os.environ["HOME"] = old_home
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(home, ignore_errors=True)


guard("P8 it ARCHIVES rather than deletes — the bytes still exist after", _p8)


def _p9():
    """A live session must make the purge a NO-OP, not a smaller purge."""
    src = _nocomments(_src("tools/claude_boot.py"))
    # the decision must be gated on agent_alive() AND on no live claude
    # process (r107), in main(), before purging
    m = re.search(r"if a\.dry_run or agent_alive\(\) or _live:", src)
    fed = re.search(r"_live = live_claude_pids\(\)", src)
    return m is not None and fed is not None and "scratch purge SKIPPED" in src


guard("P9 a LIVE session skips the purge entirely (the ordering hazard)", _p9)


def _p10():
    d = tempfile.mkdtemp(prefix="arch_")
    old = os.path.join(d, "20000101-000000-old")
    new = os.path.join(d, "29991231-000000-new")
    os.makedirs(old); os.makedirs(new)
    os.utime(old, (0, 0))                       # ancient
    gone = cb._sweep_archive(d, days=14)
    left = sorted(os.listdir(d))
    shutil.rmtree(d, ignore_errors=True)
    return gone == 1 and left == ["29991231-000000-new"]


guard("P10 the retention sweep is the only deleting path, and it is bounded", _p10)

def _p11():
    import contextlib, io
    saved = {k: getattr(cb, k) for k in ("agent_alive", "live_claude_pids", "purge_scratch",
                                         "bring_up", "record", "tmpfs_free_mb")}
    try:
        cb.agent_alive = lambda: False
        cb.live_claude_pids = lambda: []
        cb.purge_scratch = lambda root=None: (0, 123)
        cb.bring_up = lambda dry=False: (True, "up (fixture)")
        cb.record = lambda text: None
        cb.tmpfs_free_mb = lambda: 123
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cb.main([])
        return rc == 0 and "scratch purge: archived 0 stale scratch dir(s)" in buf.getvalue()
    finally:
        for k, v in saved.items():
            setattr(cb, k, v)


guard("P11 a purge that archives NOTHING still says so (0 is printed, through the real main())", _p11)

guard("P7 CONTROL: the box's real scratch root is untouched",
      lambda: (sorted(os.listdir(REAL_ROOT)) if os.path.isdir(REAL_ROOT) else None)
      == _real_before,
      lambda: REAL_ROOT)

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
