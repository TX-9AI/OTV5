#!/usr/bin/env python3
"""tests/check_claude_boot.py — v1.2
AN AGENT SESSION IS RAISED AT BOOT, AND "UP" MEANS A LIVE CLAUDE PROCESS
WHOSE FIRST TURN GOT A REAL REPLY.

v1.2  2026-09-29 — OTV4TEST r170 (BOOT.6). The 08:00 session died on its
      first turn on 09-28 and 09-29 ("Could not refresh your login because
      another Claude Code process is refreshing it") and the boot alert said
      "Claude up (handoff)" both times. B10-B13 drive the REAL functions with
      every side effect recorded: tmux, the raise, the kill, the spawn, the
      clock. No real claude is started and no real transcript, login file,
      status stamp or watcher log is read or written: OT_CLAUDE_PROJECTS_DIR,
      CLAUDE_CONFIG_DIR, OT_AGENT_STATUS and OT_CLAUDE_BOOT_LOG are pointed at
      this checker's TMP BEFORE the module is imported. The transcript
      fixtures copy the KEYS of the two real 09-29/09-27 first replies
      (isApiErrorMessage/error/<synthetic> vs a real model + requestId), not
      a guess at them (§0.4).
        B10  auth_ok reads the login FILE: present True, absent False, no
             OAuth block False, malformed None
        B10b bring_up starts NO claude process before the raise (a stub
             binary logs every invocation) — the r132 `auth status` is gone
        B11  a FAILED first turn is reported FAILED, not up; the watcher is
             spawned once; NO --continue fallback is raised
        B11b an OK first turn is "up (handoff)" and spawns nothing
        B11c no reply in the budget reads "up?", never "up", and spawns
        B11d the worst in-unit path fits inside the unit's TimeoutStartSec
        B12  watcher: login renewed -> ONE relaunch -> OK -> "relaunched"
        B12b watcher: a claude it did not start appears -> stands down,
             kills NOTHING (the operator's hand restart)
        B12c watcher: a real reply appears -> stands down, kills nothing
        B12d watcher: every relaunch fails -> exactly RETRY_MAX kills, then
             NOT AVAILABLE by name
        B12e watcher: no renewal and inside the lock window -> no relaunch
        B11e the EARLIEST reply is the verdict (a failed turn answered later
             is still a failed first turn)
        B13  the REAL spawn path: a detached `--retry` process runs,
             records a status and a log line in the fixture, and exits;
             B13c it leads its own session; B13b the real log is untouched

v1.1  2026-09-23 — OTV4TEST r107. 🔴 THIS CHECKER WAS MOVING THE LIVE AGENT'S
      FILES OUT FROM UNDER IT. B7 ran the REAL raiser with `CLAUDE_TMUX` aimed
      at a session that does not exist, so `agent_alive()` said nobody was
      running and `main()` purged the REAL /tmp/claude-<uid> into B7's temp
      HOME, which B7 never removed. Ten orphans in /tmp prove it: session
      f3ef910f's scratchpad at 06:10 ET 2026-09-22 (the boot sweep) and at
      eight of that agent's full sweeps, and 06831d64's at 21:12 ET. B7 now
      aims the purge at a `scratchtest` fixture (`OT_CLAUDE_SCRATCH_ROOT`) and
      removes what it made; B7b pins the real root UNCHANGED across this whole
      checker; B7c pins that the purge refuses a real root while its owner
      has a live claude; B7d pins that `live_claude_pids()` really sees one.
      ⚠️ B7b's born-red was demonstrated on a FIXTURE uid, not by running this
      file at 60e0408: doing that would move the live agent's files again.

v1.0  2026-09-20 — OTV4TEST r68 (BOX.11). The operator asked for a
      `claude --continue` session at boot and for the boot Telegram — the one
      already carrying the IP — to say whether it came up.

🔴 THE WHOLE DIFFICULTY IS THE WORD "UP", AND BOTH OBVIOUS CHECKS ARE WRONG.
Measured on the live session 2026-09-20, `devtools.sh` launches
`"claude ...; exec bash"`, so:
  · `#{pane_current_command}` reads **bash** WHILE CLAUDE IS RUNNING — a check
    on it reports "not available" over a working session, and §17 says an
    alarm that cries wolf stops being read;
  · the tmux session OUTLIVES a dead claude, because `exec bash` keeps the
    pane — so "the session exists" reports UP over a crashed agent, which is
    the laundered green §18 names.
B1 and B1b are that pair, driven for real.

  B0c no tmux session is left behind (HYG.9's class, found on the born-red run)
  B0  THE GUARD, FIRST: the installer is NOT run unless sudo resolves to the
      stub (r21's M4a — a checker that could install a live unit is worse than
      no gate), and B0b proves /etc/systemd/system was untouched
  B1  a tmux session that EXISTS with no claude in it reads NOT alive
  B1b ...and one with a claude-named process as a pane child reads ALIVE
  B2  the binary resolves under a systemd-like PATH (the menu's own
      `command -v claude` would NOT — no profile is read in a unit)
  B3  the installed unit's ExecStart script exists and runs the venv python
  B4  it is ordered Before the bot and takes NO Requires/Wants on it (§29)
  B5  HOME is set explicitly (credentials live in ~/.claude)
  B6  RemainAfterExit keeps the cgroup under the tmux server
  B7  the raiser exits 0 even when it can raise nothing (§29: ordering must
      never become a dependency that can hold up trading)
  B7b CONTROL: the box's REAL scratch root is identical before and after
  B7c the purge REFUSES a real root while its owner has a live claude, and
      still purges one with none
  B7d `live_claude_pids()` sees a real process named claude owned by this uid
  B8  the status round-trips, and a stale stamp reads as unknown
  B9  the REAL send_startup_alert carries the agent field, B9b says UNKNOWN
      when the stamp is absent — nothing here can reach Telegram (r22's idiom)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

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


TMP = tempfile.mkdtemp(prefix="cb_")
os.environ["OT_AGENT_STATUS"] = os.path.join(TMP, "AGENT_STATUS")
# 🔴 r170 — EVERY NEW PATH IS A FIXTURE, SET BEFORE THE IMPORT (the module
# reads them at import time). Without these the watcher tests would read the
# live agent's transcripts and append to the real ~/.optbot/claude_boot.log.
PROJ = os.path.join(TMP, "projects")
CCFG = os.path.join(TMP, "claude_cfg")
os.makedirs(PROJ); os.makedirs(CCFG)
os.environ["OT_CLAUDE_PROJECTS_DIR"] = PROJ
os.environ["CLAUDE_CONFIG_DIR"] = CCFG
os.environ["OT_CLAUDE_BOOT_LOG"] = os.path.join(TMP, "claude_boot.log")
REAL_LOG = os.path.expanduser("~/.optbot/claude_boot.log")
_real_log_before = os.path.getsize(REAL_LOG) if os.path.exists(REAL_LOG) else None

# 🔴 r107 — snapshot the REAL scratch root BEFORE anything runs; B7b compares.
REAL_ROOT = "/tmp/claude-%d" % os.getuid()
_real_before = sorted(os.listdir(REAL_ROOT)) if os.path.isdir(REAL_ROOT) else None

try:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "_cb", os.path.join(_root, "tools", "claude_boot.py"))
    cb = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(cb)
except Exception as exc:                                        # noqa: BLE001
    _WHY = "tools/claude_boot.py absent or unimportable: %s: %s" % (
        type(exc).__name__, exc)

    class _Absent:
        def __getattr__(self, n):
            raise RuntimeError(_WHY)

    cb = _Absent()

HAVE_TMUX = shutil.which("tmux") is not None
SESS = "cbcheck_%d" % os.getpid()


def _kill(s=SESS):
    subprocess.run(["tmux", "kill-session", "-t", s],
                   capture_output=True)


# ── B1 / B1b — the pair that defines "up" ────────────────────────────────────
def _b1():
    if not HAVE_TMUX:
        raise RuntimeError("tmux absent — NOT RUN rather than passed (§38.7)")
    # ⚠️ try/finally, AND IT IS NOT DECORATION. The first cut killed the session
    # on the LAST line, so when `cb` was the absent-module stub the raise
    # escaped BEFORE the cleanup and left a live `cbcheck_*` tmux session on the
    # box — found in the post-sweep `tmux ls`. That is HYG.9/HYG.10's class, a
    # checker leaving its fixtures behind on the real machine, and it showed up
    # on exactly the born-red run this gate exists to produce.
    _kill()
    try:
        subprocess.run(["tmux", "new-session", "-d", "-s", SESS,
                        "echo dead; exec bash"], capture_output=True)
        time.sleep(1.0)
        exists = subprocess.run(["tmux", "has-session", "-t", SESS],
                                capture_output=True).returncode == 0
        alive = cb.agent_alive(SESS)
        return exists and not alive
    finally:
        _kill()


guard("B1 a session that exists with no claude reads NOT alive", _b1)


def _b1b():
    if not HAVE_TMUX:
        raise RuntimeError("tmux absent — NOT RUN rather than passed (§38.7)")
    # A stand-in named exactly `claude` so `ps -o comm=` reports it. The real
    # binary is never launched: a checker that starts an agent session on the
    # box is r13's class (a fixture reaching live state).
    d = tempfile.mkdtemp(prefix="fakebin_")
    fake = os.path.join(d, "claude")
    with open(fake, "w") as fh:
        fh.write("#!/bin/sh\nsleep 30\n")
    os.chmod(fake, 0o755)
    _kill()
    try:
        subprocess.run(["tmux", "new-session", "-d", "-s", SESS,
                        "%s; exec bash" % fake], capture_output=True)
        time.sleep(1.5)
        pane_cmd = subprocess.run(
            ["tmux", "list-panes", "-t", SESS, "-F", "#{pane_current_command}"],
            capture_output=True, text=True).stdout.strip()
        alive = cb.agent_alive(SESS)
        # the naive check would have said "bash"; ours must say alive
        return alive and pane_cmd != "claude"
    finally:
        _kill()
        shutil.rmtree(d, ignore_errors=True)


guard("B1b a claude process as a pane child reads ALIVE (pane cmd says bash)", _b1b)

guard("B2 the binary resolves under a systemd-like PATH",
      lambda: bool(subprocess.run(
          [sys.executable, os.path.join(_root, "tools", "claude_boot.py"),
           "--status-only"],
          capture_output=True, text=True,
          env={"HOME": os.path.expanduser("~"), "PATH": "/usr/bin:/bin",
               "OT_AGENT_STATUS": os.environ["OT_AGENT_STATUS"]}
      ).stdout.strip()),
      lambda: "resolver ran under PATH=/usr/bin:/bin")


# ── B0 / B3-B6 — drive the REAL installer with sudo stubbed ──────────────────
UNIT_TXT = {}


def _run_installer():
    d = tempfile.mkdtemp(prefix="inst_")
    repo = os.path.join(d, "repo")
    os.makedirs(os.path.join(repo, "deploy"))
    os.makedirs(os.path.join(repo, "tools"))
    os.makedirs(os.path.join(repo, "venv", "bin"))
    shutil.copy(os.path.join(_root, "deploy", "install_claude_boot.sh"),
                os.path.join(repo, "deploy", "install_claude_boot.sh"))
    shutil.copy(os.path.join(_root, "tools", "claude_boot.py"),
                os.path.join(repo, "tools", "claude_boot.py"))
    py = os.path.join(repo, "venv", "bin", "python")
    open(py, "w").write("#!/bin/sh\nexit 0\n")
    os.chmod(py, 0o755)

    out = os.path.join(d, "unit.txt")
    stub = os.path.join(d, "sudo")
    with open(stub, "w") as fh:
        fh.write(
            "#!/bin/sh\n"
            "# stubbed sudo: tee writes to scratch, everything else is logged\n"
            'case "$1" in\n'
            '  tee) cat > "$CB_UNIT_OUT"; exit 0 ;;\n'
            '  systemctl) echo "systemctl $*" >> "$CB_UNIT_OUT.log"; exit 0 ;;\n'
            '  rm) echo "rm $*" >> "$CB_UNIT_OUT.log"; exit 0 ;;\n'
            '  *) echo "REFUSED: $*" >&2; exit 90 ;;\n'
            "esac\n")
    os.chmod(stub, 0o755)
    env = {**os.environ, "PATH": d + os.pathsep + os.environ.get("PATH", ""),
           "CB_UNIT_OUT": out}
    r = subprocess.run(["bash", os.path.join(repo, "deploy",
                                             "install_claude_boot.sh")],
                       capture_output=True, text=True, env=env, cwd=repo)
    UNIT_TXT["repo"] = repo
    UNIT_TXT["rc"] = r.returncode
    UNIT_TXT["txt"] = open(out).read() if os.path.exists(out) else ""
    UNIT_TXT["stub"] = stub
    return UNIT_TXT["txt"]


_sysd_before = sorted(os.listdir("/etc/systemd/system")) if os.path.isdir(
    "/etc/systemd/system") else []

guard("B0 the guard: sudo resolves to the stub before the installer is run",
      lambda: bool(_run_installer()) and UNIT_TXT.get("rc") == 0,
      lambda: "rc=%s unit=%d bytes" % (UNIT_TXT.get("rc"), len(UNIT_TXT.get("txt", ""))))

if FAILED:
    print("\nREFUSING TO CONTINUE — the installer did not run under the stub.")
    sys.exit(1)

_txt = UNIT_TXT["txt"]
_repo = UNIT_TXT["repo"]


def _execstart():
    m = re.search(r"^ExecStart=(\S+)\s+(\S+)", _txt, re.M)
    return m.groups() if m else ("", "")


guard("B3 the unit's ExecStart script exists and runs the venv python",
      lambda: (lambda py, sc: os.path.isfile(sc)
               and sc.startswith(_repo) and py.endswith("venv/bin/python"))(*_execstart()),
      lambda: " ".join(_execstart()))

guard("B4 ordered Before the bot, with NO Requires/Wants on it (§29)",
      lambda: "Before=optionsbot.service" in _txt
      and not re.search(r"^(Requires|Wants|BindsTo)=.*optionsbot", _txt, re.M),
      lambda: "Before=yes requires=no")

guard("B5 HOME is set explicitly in the unit",
      lambda: re.search(r"^Environment=HOME=/home/ubuntu\s*$", _txt, re.M) is not None)

guard("B6 RemainAfterExit keeps the cgroup under the tmux server",
      lambda: re.search(r"^RemainAfterExit=yes\s*$", _txt, re.M) is not None
      and re.search(r"^Type=oneshot\s*$", _txt, re.M) is not None)

guard("B6b the unit bounds how long it can delay the bot",
      lambda: re.search(r"^TimeoutStartSec=(\d+)", _txt, re.M) is not None
      and int(re.search(r"^TimeoutStartSec=(\d+)", _txt, re.M).group(1)) <= 60,
      lambda: re.search(r"^TimeoutStartSec=(\d+)", _txt, re.M).group(0))


# ── B7 — the raiser never fails its unit ─────────────────────────────────────
def _b7():
    d = tempfile.mkdtemp(prefix="nobin_")
    # 🔴 r107 — THE PURGE IS AIMED AT A FIXTURE, AND BOTH DIRS ARE REMOVED.
    # Without OT_CLAUDE_SCRATCH_ROOT this ran the real purge on the real root
    # (the fake CLAUDE_TMUX makes agent_alive() say nobody is running) and
    # parked every session's files in `d`, which was never cleaned up.
    fx = tempfile.mkdtemp(prefix="scratchtest_")
    os.makedirs(os.path.join(fx, "sessFIXTURE"), exist_ok=True)
    try:
        # no claude anywhere on PATH and none at the likely paths
        env = {"HOME": d, "PATH": d, "OT_AGENT_STATUS": os.path.join(d, "S"),
               "CLAUDE_TMUX": "cb_nobin_%d" % os.getpid(),
               "OT_CLAUDE_SETTLE_S": "1", "OT_CLAUDE_SCRATCH_ROOT": fx}
        r = subprocess.run([sys.executable,
                            os.path.join(_root, "tools", "claude_boot.py")],
                           capture_output=True, text=True, env=env)
        txt = ""
        if os.path.exists(env["OT_AGENT_STATUS"]):
            txt = open(env["OT_AGENT_STATUS"]).read()
        return r.returncode == 0 and "NOT AVAILABLE" in txt
    finally:
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(fx, ignore_errors=True)


guard("B7 it exits 0 and records NOT AVAILABLE when it can raise nothing", _b7)


# ── B7c — the destructive site refuses while its owner's agent is alive ──────
def _b7c():
    """In-process, on a FIXTURE uid's root, with HOME redirected: never the box's."""
    fake = 900000 + os.getpid() % 90000
    assert fake != os.getuid()
    root = "/tmp/claude-%d" % fake
    home = tempfile.mkdtemp(prefix="b7chome_")
    old_home = os.environ.get("HOME")
    real = cb.live_claude_pids
    try:
        os.environ["HOME"] = home
        shutil.rmtree(root, ignore_errors=True)
        os.makedirs(os.path.join(root, "sessA")); os.makedirs(os.path.join(root, "sessB"))
        cb.live_claude_pids = lambda uid=None: [4242] if uid == fake else real(uid)
        n_live, _ = cb.purge_scratch(root)
        kept = sorted(os.listdir(root))
        cb.live_claude_pids = lambda uid=None: []
        n_idle, _ = cb.purge_scratch(root)
        return n_live == 0 and kept == ["sessA", "sessB"] and n_idle == 2 \
            and os.listdir(root) == []
    finally:
        cb.live_claude_pids = real
        if old_home is not None:
            os.environ["HOME"] = old_home
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(home, ignore_errors=True)


guard("B7c the purge REFUSES a real root while its owner has a live claude", _b7c)


# ── B7d — the liveness test sees a real process, not a mock ─────────────────
def _b7d():
    """A copy of the Python interpreter named `claude` IS a claude process to
    /proc. Makes this deterministic even when no agent is running (a plain SSH
    land).
    ⚠️ THE FIRST CUT COPIED `sleep` AND PASSED ON A ZOMBIE. On this box `sleep`
    is a multi-call coreutils binary: renamed `claude` it printed "unknown
    program 'claude'" and exited at once, and the un-reaped zombie still showed
    comm=claude in /proc. §40.1 — a check whose shape destroys what it asserts.
    So the process must be PROVEN RUNNING at the moment it is detected."""
    src = os.path.realpath(sys.executable)
    d = tempfile.mkdtemp(prefix="b7d_")
    fake = os.path.join(d, "claude")
    shutil.copy(src, fake)
    p = subprocess.Popen([fake, "-c", "import time; time.sleep(30)"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.5)
        running = p.poll() is None
        return running and p.pid in cb.live_claude_pids()
    finally:
        p.kill(); p.wait()
        shutil.rmtree(d, ignore_errors=True)


guard("B7d live_claude_pids() sees a real process named claude", _b7d)


# ── B8 — the stamp ───────────────────────────────────────────────────────────
def _b8():
    from utils import agent_status as ast_
    ast_.record("up (continue)")
    fresh = ast_.read() == "up (continue)"
    stale = ast_.read(now=time.time() + ast_.MAX_AGE_S + 10) is None
    return fresh and stale


guard("B8 the status round-trips and a stale stamp reads as unknown", _b8)


# ── B9 — the REAL alert, captured, never sent ────────────────────────────────
def _alert(with_stamp: bool):
    import notifications.alert_manager as am
    from utils import agent_status as ast_
    try:
        os.unlink(ast_.path())
    except Exception:                                           # noqa: BLE001
        pass
    if with_stamp:
        ast_.record("up (continue)")
    mgr = am.AlertManager.__new__(am.AlertManager)
    mgr._tg, mgr._enabled = None, False
    sent = []
    mgr._send = lambda msg: (sent.append(msg), True)[1]
    am.public_ip = lambda: ("1.2.3.4", "")
    mgr.send_startup_alert(paper=True, instrument="QQQ", risk_usd=1050.0,
                           restart_type="fresh boot")
    return sent[0] if sent else ""


_A = {}
guard("B9 the real startup alert carries the agent field",
      lambda: "Claude up (continue)" in _A.setdefault("on", _alert(True)),
      lambda: _A.get("on", "")[:120])

guard("B9b it says UNKNOWN when there is no stamp, never guessing",
      lambda: "Claude status unknown" in _A.setdefault("off", _alert(False)),
      lambda: _A.get("off", "")[:120])

# ── B10-B13 — r170: the first turn decides "up" ─────────────────────────────
import json as _json
from datetime import datetime as _dt, timezone as _tz


def _iso(t):
    return _dt.fromtimestamp(t, _tz.utc).isoformat().replace("+00:00", "Z")


# The KEYS of the real first replies (09-29 failed, 09-27 ok), values trimmed.
def _entry(kind, t):
    if kind == "failed":
        return {"type": "assistant", "timestamp": _iso(t), "isApiErrorMessage": True,
                "error": "server_error",
                "message": {"model": "<synthetic>", "stop_reason": "stop_sequence",
                            "content": [{"type": "text", "text":
                                         "Could not refresh your login because another "
                                         "Claude Code process is refreshing it (or exited "
                                         "mid-refresh)"}]}}
    return {"type": "assistant", "timestamp": _iso(t), "requestId": "req_fixture",
            "message": {"model": "claude-opus-5-5", "stop_reason": "tool_use",
                        "content": [{"type": "thinking", "thinking": ""}]}}


def _transcript(kind, t=None, name=None):
    t = time.time() if t is None else t
    p = os.path.join(PROJ, name or "fx-%d-%s.jsonl" % (int(t * 1000), kind))
    with open(p, "a") as fh:
        fh.write(_json.dumps({"type": "user", "timestamp": _iso(t),
                              "message": {"content": "brief"}}) + "\n")
        if kind:
            fh.write(_json.dumps(_entry(kind, t + 0.2)) + "\n")
    # the watcher runs on a FAKE clock and the reader filters on mtime
    os.utime(p, (t + 0.2, t + 0.2))
    return p


def _clear_proj():
    for n in os.listdir(PROJ):
        os.unlink(os.path.join(PROJ, n))


def _write_cred(obj):
    with open(os.path.join(CCFG, ".credentials.json"), "w") as fh:
        fh.write(obj if isinstance(obj, str) else _json.dumps(obj))


def _b10():
    cp = os.path.join(CCFG, ".credentials.json")
    if os.path.exists(cp):
        os.unlink(cp)
    absent = cb.auth_ok()
    _write_cred({"claudeAiOauth": {"refreshToken": "FIXTURE", "accessToken": "FIXTURE"}})
    present = cb.auth_ok()
    _write_cred({"somethingElse": 1})
    no_oauth = cb.auth_ok()
    _write_cred("{not json")
    bad = cb.auth_ok()
    _write_cred({"claudeAiOauth": {"refreshToken": "FIXTURE"}})
    return [present, absent, no_oauth, bad] == [True, False, False, None]


guard("B10 auth_ok reads the login FILE: present/absent/no-oauth/malformed",
      _b10)


_MISSING = object()


class _Rig:
    """Every side effect of bring_up/run_retry recorded, nothing real run."""

    def __init__(self, first_reply):
        self.first_reply = first_reply          # 'ok' | 'failed' | None
        self.raised, self.killed, self.spawned = [], 0, []
        self.saved = {}
        d = tempfile.mkdtemp(prefix="stubbin_")
        self.stub_log = os.path.join(d, "invoked.log")
        self.stub = os.path.join(d, "claude")
        with open(self.stub, "w") as fh:
            fh.write('#!/bin/sh\necho "$@" >> "%s"\nexit 0\n' % self.stub_log)
        os.chmod(self.stub, 0o755)
        self.dir = d

    def _raise(self, cmd, name=None):
        self.raised.append(cmd)
        if self.first_reply is not None:
            _transcript(self.first_reply)

    def _kill(self, name=None):
        self.killed += 1

    def __enter__(self):
        for n, v in (("claude_bin", lambda: self.stub),
                     ("tmux_bin", lambda: "/usr/bin/tmux"),
                     ("agent_alive", lambda name=None: False),
                     ("has_session", lambda name=None: True),
                     ("_settle", lambda budget=None: True),
                     ("_raise", self._raise), ("_kill", self._kill),
                     ("spawn_retry", lambda since: (self.spawned.append(since), True)[1]),
                     ("FIRST_TURN_S", 1.0)):
            # ⚠️ getattr with a sentinel: on the unfixed tree the r170 names do
            # not exist, and the born-red run must be a FAIL, not a crash (§40.1)
            self.saved[n] = getattr(cb, n, _MISSING)
            setattr(cb, n, v)
        _clear_proj()
        _write_cred({"claudeAiOauth": {"refreshToken": "FIXTURE"}})
        return self

    def __exit__(self, *a):
        for n, v in self.saved.items():
            if v is _MISSING:
                delattr(cb, n)
            else:
                setattr(cb, n, v)
        shutil.rmtree(self.dir, ignore_errors=True)
        _clear_proj()


_B11 = {}


def _run_bring_up(kind):
    with _Rig(kind) as r:
        ok, text = cb.bring_up()
        _B11[kind] = (ok, text)
        stub_ran = os.path.exists(r.stub_log)
        return ok, text, r.raised, r.spawned, stub_ran


def _b10b():
    ok, text, raised, spawned, stub_ran = _run_bring_up("ok")
    return not stub_ran and len(raised) == 1


guard("B10b bring_up starts NO claude process before the raise", _b10b)


def _b11():
    ok, text, raised, spawned, _ = _run_bring_up("failed")
    return (ok is False and text.startswith("FIRST TURN FAILED")
            and "login refresh" in text and "up (" not in text
            and len(spawned) == 1 and len(raised) == 1
            and "--continue" not in raised[0])


guard("B11 a FAILED first turn is reported FAILED, watcher spawned, no --continue",
      _b11, lambda: str(_B11.get("failed")))


def _b11b():
    ok, text, raised, spawned, _ = _run_bring_up("ok")
    return ok is True and text == "up (handoff)" and spawned == []


guard("B11b an OK first turn is 'up (handoff)' and spawns nothing", _b11b,
      lambda: str(_B11.get("ok")))


def _b11c():
    ok, text, raised, spawned, _ = _run_bring_up(None)
    return (ok is False and text.startswith("up? (") and not text.startswith("up (")
            and len(spawned) == 1)


guard("B11c no reply in the budget reads 'up?', never 'up', and spawns", _b11c,
      lambda: str(_B11.get(None)))


def _b11d():
    tmo = int(re.search(r"^TimeoutStartSec=(\d+)", _txt, re.M).group(1))
    s, f = float(cb.SETTLE_S), float(cb.FIRST_TURN_S)
    _B11["budget"] = (tmo, s, f)
    return s + f + 5 <= tmo and 2 * s + 5 <= tmo


guard("B11d the worst in-unit path fits inside the unit's TimeoutStartSec", _b11d,
      lambda: "TimeoutStartSec, SETTLE_S, FIRST_TURN_S = %s" % (_B11.get("budget"),))


def _b11e():
    """The EARLIEST reply is the verdict: a turn that failed and replied later
    (the operator typed into it) is still a failed FIRST turn."""
    _clear_proj()
    t = time.time()
    p = _transcript("failed", t, name="two.jsonl")
    with open(p, "a") as fh:
        fh.write(_json.dumps(_entry("ok", t + 5)) + "\n")
    os.utime(p, (t + 5, t + 5))
    try:
        return cb.first_turn(t, budget=0.5)[0] == "failed"
    finally:
        _clear_proj()


guard("B11e the EARLIEST reply is the first turn's verdict", _b11e)


class _Clock:
    def __init__(self, t0):
        self.t = t0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _watch(first_reply, renew_at=None, pid_at=None, reply_at=None):
    """Drive the REAL run_retry on a fake clock. -> (text, kills, raises)."""
    c = _Clock(time.time())
    since = c.t
    extra = {"pids": [111]}
    ticks = {"n": 0}

    def sleep(s):
        c.sleep(s)
        ticks["n"] += 1
        if renew_at is not None and ticks["n"] == renew_at:
            _write_cred({"claudeAiOauth": {"refreshToken": "FIXTURE2"}})
            os.utime(os.path.join(CCFG, ".credentials.json"), (c.t, c.t + 5))
        if pid_at is not None and ticks["n"] == pid_at:
            extra["pids"] = [111, 222]
        if reply_at is not None and ticks["n"] == reply_at:
            _transcript("ok", c.t, name="operator-session.jsonl")

    with _Rig(first_reply) as r:
        os.utime(os.path.join(CCFG, ".credentials.json"), (since - 100, since - 100))
        _transcript("failed", since, name="failed-session.jsonl")
        saved_pids = cb.live_claude_pids
        cb.live_claude_pids = lambda uid=None: list(extra["pids"])
        try:
            # the relaunched session's reply must carry the FAKE clock's time
            r._raise = (lambda cmd, name=None: (r.raised.append(cmd),
                        first_reply and _transcript(first_reply, c.t)))
            cb._raise = r._raise
            text = cb.run_retry(since, sleep=sleep, now=c.now)
        finally:
            cb.live_claude_pids = saved_pids
        return text, r.killed, len(r.raised), round(c.t - since)


_B12 = {}


def _b12():
    _B12["renew"] = res = _watch("ok", renew_at=2)
    text, kills, raises, took = res
    # PROMPT: it acted on the renewal, not on the lock-window fallback
    return (text.startswith("up (handoff, relaunched") and kills == 1 and raises == 1
            and took < cb.RELAUNCH_AFTER_S)


guard("B12 watcher: login renewed -> one relaunch -> OK -> 'relaunched'", _b12,
      lambda: str(_B12.get("renew")))


def _b12b():
    _B12["pid"] = res = _watch("ok", pid_at=2)
    text, kills, raises, _ = res
    return "stood down, killed nothing" in text and kills == 0 and raises == 0


guard("B12b watcher: a claude it did not start -> stands down, kills NOTHING", _b12b,
      lambda: str(_B12.get("pid")))


def _b12c():
    _B12["reply"] = res = _watch("ok", reply_at=2)
    text, kills, raises, _ = res
    return text.startswith("up (handoff — a session replied") and kills == 0


guard("B12c watcher: a real reply appears -> stands down, kills nothing", _b12c,
      lambda: str(_B12.get("reply")))


def _b12d():
    _B12["fail"] = res = _watch("failed", renew_at=1)
    text, kills, raises, _ = res
    return (text.startswith("NOT AVAILABLE (first turn failed; %d relaunch" % cb.RETRY_MAX)
            and kills == cb.RETRY_MAX and raises == cb.RETRY_MAX)


guard("B12d watcher: every relaunch fails -> RETRY_MAX kills, then NOT AVAILABLE",
      _b12d, lambda: str(_B12.get("fail")))


def _b12e():
    saved = cb.RETRY_WINDOW_S
    cb.RETRY_WINDOW_S = cb.RELAUNCH_AFTER_S - 2 * cb.RETRY_POLL_S
    try:
        _B12["quiet"] = res = _watch("ok")
    finally:
        cb.RETRY_WINDOW_S = saved
    text, kills, raises, _ = res
    return kills == 0 and raises == 0 and text.startswith("NOT AVAILABLE")


guard("B12e watcher: no renewal inside the lock window -> no relaunch", _b12e,
      lambda: str(_B12.get("quiet")))


def _b13():
    """The REAL spawn: a detached `--retry` that can relaunch NOTHING
    (RETRY_MAX=0, no claude reachable) records its status and a log line."""
    saved = {k: os.environ.get(k) for k in
             ("OT_CLAUDE_RETRY_MAX", "OT_CLAUDE_RETRY_WINDOW_S", "OT_CLAUDE_RETRY_POLL_S",
              "CLAUDE_TMUX", "HOME", "PATH")}
    status = os.environ["OT_AGENT_STATUS"]
    log = os.environ["OT_CLAUDE_BOOT_LOG"]
    for p in (status, log):
        if os.path.exists(p):
            os.unlink(p)
    fakehome = tempfile.mkdtemp(prefix="b13home_")
    os.environ.update({"OT_CLAUDE_RETRY_MAX": "0", "OT_CLAUDE_RETRY_WINDOW_S": "1",
                       "OT_CLAUDE_RETRY_POLL_S": "0.2",
                       "CLAUDE_TMUX": "cb_b13_%d" % os.getpid(),
                       "HOME": fakehome, "PATH": "/usr/bin:/bin"})
    try:
        started = cb.spawn_retry(time.time())
        # B13c — DETACHED: the watcher leads its own session, so a signal to
        # the raiser's process group (or its exit) never reaches it
        detached = None
        t_end = time.time() + 5
        while detached is None and time.time() < t_end:
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue
                # ⚠️ MATCH THE ARGV, NOT A SUBSTRING. The first cut searched the
                # joined cmdline for "claude_boot.py --retry" and found the
                # SHELL that launched this checker, whose command line quoted
                # that text, in our own session: a false FAIL on a detached
                # watcher (§40.1's shape, caught before it could go the other way).
                try:
                    argv = open("/proc/%s/cmdline" % pid, "rb").read().split(b"\0")
                except OSError:
                    continue
                if (len(argv) > 2 and argv[1].endswith(b"tools/claude_boot.py")
                        and argv[2] == b"--retry"):
                    try:
                        detached = os.getsid(int(pid)) != os.getsid(0)
                    except OSError:
                        continue
                    break
            time.sleep(0.05)
        _B12["detached"] = detached
        deadline = time.time() + 20
        txt = ""
        while time.time() < deadline:
            if os.path.exists(status):
                txt = open(status).read()
                if "NOT AVAILABLE" in txt:
                    break
            time.sleep(0.2)
        logged = os.path.exists(log) and "watcher up" in open(log).read()
        _B12["spawn"] = (started, txt.strip()[:100], logged)
        return started and "NOT AVAILABLE (first turn failed; 0 relaunch" in txt and logged
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(fakehome, ignore_errors=True)


guard("B13 the REAL detached --retry runs, records a status and a log line", _b13,
      lambda: str(_B12.get("spawn")))

guard("B13c the watcher is DETACHED (its own session, not the raiser's)",
      lambda: _B12.get("detached") is True, lambda: "detached=%s" % _B12.get("detached"))

guard("B13b CONTROL: the real watcher log is untouched by this checker",
      lambda: (os.path.getsize(REAL_LOG) if os.path.exists(REAL_LOG) else None)
      == _real_log_before, lambda: REAL_LOG)


guard("B0c no tmux session is left behind by this checker",
      lambda: subprocess.run(["tmux", "has-session", "-t", SESS],
                             capture_output=True).returncode != 0,
      lambda: "session %s absent" % SESS)

guard("B7b CONTROL: the box's REAL scratch root is untouched by this checker",
      lambda: (sorted(os.listdir(REAL_ROOT)) if os.path.isdir(REAL_ROOT) else None)
      == _real_before,
      lambda: REAL_ROOT)

guard("B0b /etc/systemd/system is untouched",
      lambda: (sorted(os.listdir("/etc/systemd/system"))
               if os.path.isdir("/etc/systemd/system") else []) == _sysd_before)

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
