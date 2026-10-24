#!/usr/bin/env python3
"""tools/claude_boot.py — v1.8
RAISE AN AGENT SESSION AT BOOT, AND PROVE IT IS ACTUALLY RUNNING.

v1.8 (2026-10-23) — OTV4TEST r314 (MENU.2). THE SESSION NAME IS THE BOX'S, NEVER QQQ-TEST'S BY DEFAULT.
      OT_RC_NAME lives only in this unit, so a raise from an SSH shell fell back to "qqq-test" and SPX-TEST
      came up under QQQ-TEST's name (2026-10-23, after an expired login; the operator fixed it with /rename).
      rc_name(): OT_RC_NAME when set (the unit, unchanged), else "✨<INSTRUMENT>-TEST" from
      utils.instrument.box_instrument() (the bot unit's OT_INSTRUMENT, one key, nothing printed), else
      "✨UNSET-TEST" - a named absence, never a guessed box. `--rc-name` prints it, for devtools.sh.
      The operator, 2026-10-23 11:10 ET: "Yes to both" (r313's menu item, and this fix).
v1.7 (2026-10-04) — OTV4TEST r235 — THE PURGE SAYS ZERO. It printed only when it archived something, so a
      purge that ran and found nothing stale looked like one that never ran (SPX-TEST's agent, 2026-10-04,
      §0.5). It now prints "scratch purge: archived N stale scratch dir(s)" every time it runs, 0 included.
      Gate: tests/check_claude_purge.py P10.
v1.6 (2026-10-03) — OTV4TEST r231 (BOOT.7). OT_BRIEF: A BOX CAN HAVE ITS OWN BRIEF. The operator
      brought up SPX-TEST on this repo and its first session believed it was QQQ-TEST, because
      docs/HANDOFF.md is written for QQQ and every box read it. OT_BRIEF names a brief under docs/
      (e.g. docs/HANDOFF_SPX.md); unset, missing, or outside docs/ falls back to HANDOFF.md and says
      so in the log. FIRST_BOOT.md still wins while the installer's marker exists. QQQ-TEST sets
      nothing and is unchanged.

v1.5 (2026-09-29) — OTV4TEST r170 (BOOT.6). THE 08:00 SESSION DIED ON ITS FIRST
      TURN TWO MORNINGS RUNNING, AND THE BOOT ALERT SAID "UP" BOTH TIMES. The
      operator restarted it by hand on 09-28 and 09-29: *"now that it's two in a
      row, would you mind looking into what happened?"*, then *"Yes, it's worth a
      shot"*. MEASURED from the two transcripts: the brief landed at 08:00:28
      and the first reply, 3-4 s later, was a synthetic API error — *"Could not
      refresh your login because another Claude Code process is refreshing it
      (or exited mid-refresh)"* — and Remote Control dropped. The login file was
      rewritten at 08:10:40 and Remote Control came back by itself at 08:10:43,
      but nothing re-sent the brief. Meanwhile the alert read "Claude up
      (handoff)", because "up" meant a live claude PROCESS, and a process that
      failed its only turn is still a process.
      RULED OUT: the Claude Code version (09-28 failed on 2.1.283, which had
      booted cleanly on 09-26 and 09-27); the unit order (identical to the
      second on good and bad days); the boot sweep (its checker uses a fake
      claude); SOFI/AAL (powered off until the 09:15 wake, per 1-REPORTER's
      power ledger); control (a separate login). ⚠️ THE CAUSE IS NOT PROVEN.
      The one other claude process on this box at 08:00 is this file's own
      `claude auth status` (r132), at 08:00:17-20, and nothing refreshed the
      login successfully until 08:10:40. No lock file or debug log survives
      to confirm it, and the weekend boots ran the same check without failing.
      🔑 TWO CHANGES. (1) `auth_ok()` READS THE LOGIN FILE and starts no claude
      process: absent or no OAuth block is False, unreadable is None, exactly
      the old contract. This removes the only suspect on the box. (2) "UP" NOW
      REQUIRES A REAL FIRST REPLY. `first_turn()` reads the new session's own
      transcript: a first assistant entry flagged `isApiErrorMessage` is
      FAILED, one with a real model is OK, none within FIRST_TURN_S is UNSEEN
      (measured: real first replies landed 1-2 s after the brief on 09-26 and
      09-27). FAILED or UNSEEN is written as such to the status, so the boot
      alert cannot say "up" over a dead turn. A DETACHED `--retry` watcher then
      re-raises the handoff once the login file is renewed, or after
      RELAUNCH_AFTER_S (the 09-29 lock cleared in about 10 min), at most
      RETRY_MAX times. It stands down the moment any session replies or a claude
      it did not start appears, so it never kills a session the operator
      raised by hand. ⚠️ IT CANNOT RUN INSIDE THE UNIT: the unit is ordered
      before the bot with TimeoutStartSec=45, and a relaunch that must wait
      out a ten-minute lock would hold up the bot's 08:00 start.
      ⚠️ THE ALERT IS NOT RE-SENT when the watcher recovers (§17: a boot that
      recovers on its own is not an emergency). The recovery is written to the
      status file and to RETRY_LOG, which `--status-only` prints.

v1.4 (2026-09-24) — OTV4TEST r132. A FRESH BOX IS BRIEFED FOR A FRESH BOX, AND
      A MISSING LOGIN IS NAMED INSTEAD OF RAISED. The operator, on the unattended
      install: *"after the first boot on a fresh instance, I want Claude to come
      up with it in a remote control session and look everything over."*
      🔑 THREE CHANGES, NOTHING ELSE MOVES. (1) `choose_brief()`: while the
      installer's first-boot marker exists (`OT_FIRST_BOOT_MARKER`, default
      ~/.optbot/first_boot) the session is briefed from docs/FIRST_BOOT.md — the
      daily HANDOFF.md would send a new box's agent to catch up on a history it
      does not have. The marker is consumed only once a briefed session is
      VERIFIED up, so a failed first raise retries on the next boot. (2)
      `auth_ok()`: `claude auth status` exits 0 logged in and 1 not (measured on
      2.1.281, must-fail control an empty CLAUDE_CONFIG_DIR). A box with no
      login used to raise a session that sat at a login screen and read "up";
      it now records NOT AVAILABLE with the one command that fixes it. An auth
      check that cannot run (timeout, crash) does NOT block the raise — only a
      definite "not logged in" does. (3) `RC_NAME` reads `OT_RC_NAME`, default
      unchanged (qqq-test).

v1.3 (2026-09-23) — OTV4TEST r107. THE PURGE WAS MOVING A LIVE AGENT'S FILES
      OUT FROM UNDER IT, TEN TIMES IN TWO DAYS, AND ITS OWN CHECKER WAS THE
      TRIGGER. `check_claude_boot` B7 runs this file for real with
      `CLAUDE_TMUX` pointed at a session that does not exist, so
      `agent_alive()` — which asks about ONE tmux name — said "nobody is
      running", and `main()` purged the REAL /tmp/claude-<uid>, moving every
      session directory (the live agent's scratchpad AND Claude Code's own
      `bash-edit-diff`) into B7's throwaway HOME, which B7 never removed.
      MEASURED from the orphans left in /tmp: session f3ef910f's files moved at
      06:10 ET 2026-09-22 (the 08:00-boot sweep, two seconds after the agent
      was raised) and at 16:27, 17:26, 17:39, 17:43, 17:47, 18:24, 18:48 and
      19:25 ET — every full sweep that agent ran — and 06831d64's at 21:12 ET.
      That agent reported files vanishing; the operator stopped it at 17:52.
      🔑 TWO LAYERS NOW. (1) `live_claude_pids()` reads /proc: a `claude`
      process owned by this uid is a live agent WHATEVER tmux calls it, and
      both `main()` and `purge_scratch()` refuse the real root while one
      exists. At a genuine cold boot there is none, so the boot purge is
      unchanged. (2) `OT_CLAUDE_SCRATCH_ROOT` lets the gate aim the purge at a
      fixture root; it is held to the same path regex, so it can only ever
      name the real root or a `scratchtest` fixture.
v1.2 (2026-09-21) — OTV4TEST r86. THE BOOT SESSION IS A HANDOFF, NOT A
      CONTINUE. Operator: *"instead of having a continued agent session on
      boot, it should be a handoff agent session that reads the previous
      session thread."* ~~r68's "--continue, with fallback"~~ is SUPERSEDED and
      struck, not deleted — it is why the fallback still exists. A --continue
      resumes wherever yesterday happened to stop; a handoff starts from a
      written brief and then reads the prior session deliberately.
v1.1  2026-09-20 — OTV4TEST r70 (BOX.12). PURGES STALE tmpfs SCRATCHPADS
      before raising, and appends free-tmpfs to the status so it reaches the
      boot alert. /tmp is RAM (455 MB of 908 MB here) and scratch dirs are
      keyed by session id, so they accumulate until every Bash spawn dies
      silently — which is what happened on control.

v1.0  2026-09-20 — OTV4TEST r68 (BOX.11). The operator: *"Can we have a tmux
      session Claude --continue added to the boot sequence on this box so that
      an agent is available from the moment the box auto wakes?"*

🔴 THE CHECK IS THE HARD PART, AND THE TWO OBVIOUS ONES ARE BOTH WRONG.
Measured on the live session 2026-09-20:

    tmux list-panes -t claude -F '#{pane_pid} #{pane_current_command}'
      ->  1727 bash                                  <- says BASH
    ps --ppid 1727
      ->  1731 claude --remote-control qqq-test ...   <- claude is the CHILD

`devtools.sh` launches `"claude ...; exec bash"`, so (1) the pane's foreground
command reads `bash` WHILE CLAUDE IS RUNNING FINE — a check on it would report
"not available" over a working session, and §17 says an alarm that cries wolf
stops being read; and (2) the tmux session OUTLIVES a dead claude, because the
trailing `exec bash` keeps the pane alive — so "the session exists" reports UP
over a crashed agent, which is the laundered green §18 names.
🔑 SO AVAILABILITY IS A LIVE `claude` PROCESS IN THE SESSION'S PROCESS TREE,
verified after a settle delay, and nothing weaker.

⚠️ IT REUSES `devtools.sh`'s SHAPE RATHER THAN INVENTING ONE. Same session
name, same `--remote-control qqq-test` flag (r32: the argument is OPTIONAL, so
a bare flag on the HAND OFF site could swallow the brief as the session name),
same `; exec bash` tail so the operator can attach to a pane that survives.
Two mechanisms for one job is the failure §35 keeps recording.

⚠️ AND AN AVAILABLE SESSION IS NOT A WORKING AGENT. §38.7 — *"the assistant
does not run continuously"* — is untouched by this. A resumed thread sits at a
prompt and does nothing until the operator types. This raises a door, not a
worker.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

from utils.agent_status import record                           # noqa: E402

SESSION = os.environ.get("CLAUDE_TMUX", "claude")

# 🔴 A SYSTEMD UNIT DOES NOT HAVE THE OPERATOR'S PATH, AND THE MENU'S OWN
# RESOLVER WOULD FAIL HERE. `devtools.sh::_claude_bin` is `command -v claude`,
# which works in his login shell because the profile adds `~/.local/bin` —
# measured, that is exactly where the binary is (`/home/ubuntu/.local/bin/
# claude`, 2.1.278). A unit starts with systemd's default PATH and no profile
# is ever read, and tmux runs its command under `/bin/sh`, which reads none
# either. So `claude` would simply not be found AT BOOT, on a box where it is
# plainly installed and works by hand — the §40 shape, where a claim about
# behaviour is a claim about an environment.
_LIKELY = (
    os.path.expanduser("~/.local/bin/claude"),
    "/usr/local/bin/claude",
    "/usr/bin/claude",
)


def claude_bin() -> str:
    """Absolute path to the claude binary, or "" when it is genuinely absent."""
    import shutil
    found = shutil.which("claude")
    if found:
        return found
    for cand in _LIKELY:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return ""
# r314 — the unit's own name when it sets one; rc_name() derives it otherwise.
RC_NAME = (os.environ.get("OT_RC_NAME") or "").strip()


def rc_name() -> str:
    """The Remote Control name: OT_RC_NAME, else "✨<INSTRUMENT>-TEST" from the
    box's own instrument, else "✨UNSET-TEST". Never "qqq-test" on a box that
    is not QQQ-TEST (r314)."""
    if RC_NAME:
        return RC_NAME
    try:
        from utils.instrument import box_instrument, UNSET
        inst = (box_instrument() or UNSET).strip().upper()
    except Exception:                                           # noqa: BLE001
        inst = "UNSET"
    if not inst.replace("_", "").isalnum():
        inst = "UNSET"
    return "✨%s-TEST" % inst


# 🔴 r70 / AUTH.1 — LAUNCH ON THE SUBSCRIPTION, NEVER ON API CREDITS.
# Operator's instruction. Measured 2026-09-20: no key is set anywhere on this
# box and `~/.claude.json` authenticates through `oauthAccount` — so today it
# is right BY ACCIDENT. One stray export would move every boot session onto
# metered credits with nothing saying so. Stripped at the launch rather than
# trusted. ⚠️ IT UNSETS; IT NEVER READS OR PRINTS A VALUE (§18a).
ENV_STRIP = ("env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN"
             " -u CLAUDE_API_KEY -u ANTHROPIC_BASE_URL")
DEFAULT_BRIEF = os.path.join(_root, "docs", "HANDOFF.md")


def _brief_from_env() -> str:
    """r231 (BOOT.7) — OT_BRIEF, a file under docs/, else HANDOFF.md (said in the log)."""
    raw = (os.environ.get("OT_BRIEF") or "").strip()
    if not raw:
        return DEFAULT_BRIEF
    docs = os.path.realpath(os.path.join(_root, "docs"))
    cand = os.path.realpath(raw if os.path.isabs(raw) else os.path.join(_root, raw))
    if os.path.dirname(cand) == docs and cand.endswith(".md") and os.path.isfile(cand):
        return cand
    print("claude_boot: OT_BRIEF=%r is not a readable .md under docs/ - using HANDOFF.md" % raw,
          file=sys.stderr)
    return DEFAULT_BRIEF


BRIEF = _brief_from_env()
# r132 — a fresh box's first session is briefed for a fresh box. The installer
# (setup_ec2.sh) writes the marker; bring_up() consumes it once verified.
FIRST_BOOT_BRIEF = os.path.join(_root, "docs", "FIRST_BOOT.md")
FIRST_BOOT_MARKER = (os.environ.get("OT_FIRST_BOOT_MARKER")
                     or os.path.expanduser("~/.optbot/first_boot"))


def choose_brief() -> tuple[str, bool]:
    """-> (brief path, is_first_boot). FIRST_BOOT.md while the installer's
    marker exists and the brief is readable; HANDOFF.md otherwise."""
    if os.path.exists(FIRST_BOOT_MARKER) and os.path.exists(FIRST_BOOT_BRIEF):
        return FIRST_BOOT_BRIEF, True
    return BRIEF, False


def _claude_dir() -> str:
    """Claude Code's config dir, resolved at CALL time so a fixture HOME or
    CLAUDE_CONFIG_DIR set after import is honoured."""
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def cred_path() -> str:
    return os.path.join(_claude_dir(), ".credentials.json")


def auth_ok(path: str | None = None):
    """True logged in, False definitely not, None when the check itself could
    not run.
    🔴 r170 — IT READS THE LOGIN FILE; IT NO LONGER RUNS `claude auth status`.
    That subprocess was the only other claude process on the box at 08:00,
    11 s before the session whose first login refresh then failed, two
    mornings running (header, v1.5). Same contract as r132: a DEFINITE "not
    logged in" (no file, or a file with no OAuth block) is False and blocks
    the raise; an unreadable or malformed file is None and does not.
    ⚠️ NOTHING IS PRINTED OR RETURNED FROM THE FILE BUT A BOOLEAN (§18a) —
    it holds live tokens."""
    import json
    p = path or cred_path()
    if not os.path.exists(p):
        return False
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:                                           # noqa: BLE001
        return None
    o = d.get("claudeAiOauth") if isinstance(d, dict) else None
    if not isinstance(o, dict):
        return False
    return bool(o.get("refreshToken") or o.get("accessToken"))

# The settle budget. `claude` needs a few seconds to be a real process; the
# unit's own TimeoutStartSec sits above this so systemd never waits longer
# than the script's own worst case.
SETTLE_S = float(os.environ.get("OT_CLAUDE_SETTLE_S", "12"))
POLL_S = 0.5


def tmux_bin() -> str:
    """Absolute path to tmux, for the same reason as `claude_bin` — a unit does
    not read a profile and must not assume the operator's PATH."""
    import shutil
    return (shutil.which("tmux") or
            next((c for c in ("/usr/bin/tmux", "/usr/local/bin/tmux")
                  if os.path.isfile(c) and os.access(c, os.X_OK)), ""))


class _Failed:
    """A subprocess result that did not happen. Stands in for a missing binary
    so every caller sees a clean failure rather than an exception."""
    returncode = 127
    stdout = ""
    stderr = "binary not found"


def _tmux(*args, **kw):
    # 🔴 NEVER RAISE. Found by this file's own gate (B7): with tmux off PATH
    # the raiser died with FileNotFoundError, exited NON-ZERO and recorded NO
    # STATUS AT ALL — so the unit would have gone to `failed` and the boot
    # alert would have said "unknown" with nothing anywhere explaining why.
    # A component whose entire job is REPORTING availability must not have a
    # path on which it reports nothing (§0.5).
    b = tmux_bin()
    if not b:
        return _Failed()
    try:
        return subprocess.run([b, *args], capture_output=True, text=True, **kw)
    except OSError:
        return _Failed()


def has_session(name: str = SESSION) -> bool:
    return _tmux("has-session", "-t", name).returncode == 0


def agent_alive(name: str = SESSION) -> bool:
    """A live `claude` process inside this session's panes. See the header —
    neither the session's existence nor the pane's command answers this."""
    if not has_session(name):
        return False
    r = _tmux("list-panes", "-t", name, "-F", "#{pane_pid}")
    if r.returncode != 0:
        return False
    for pid in [x.strip() for x in r.stdout.split() if x.strip().isdigit()]:
        # the pane process itself, and its children — claude is normally a child
        try:
            ps = subprocess.run(["ps", "-o", "pid=,comm=", "--ppid", pid],
                                capture_output=True, text=True)
            own = subprocess.run(["ps", "-o", "comm=", "-p", pid],
                                 capture_output=True, text=True)
        except OSError:
            continue
        names = [ln.split()[-1] for ln in ps.stdout.splitlines() if ln.strip()]
        names += [ln.strip() for ln in own.stdout.splitlines() if ln.strip()]
        if any(n == "claude" for n in names):
            return True
    return False


def _kill(name: str = SESSION) -> None:
    _tmux("kill-session", "-t", name)


def _raise(cmd: str, name: str = SESSION) -> None:
    _tmux("new-session", "-d", "-s", name, "-c", _root, cmd)


def _settle(budget: float = SETTLE_S) -> bool:
    """Poll rather than sleep a flat interval: a fast box reports sooner and a
    slow one still gets its full budget."""
    deadline = time.time() + budget
    while time.time() < deadline:
        if agent_alive():
            return True
        time.sleep(POLL_S)
    return agent_alive()


# ── r170 — "UP" MEANS THE FIRST TURN GOT A REAL REPLY ───────────────────────
# Budgets. The unit gives this script TimeoutStartSec=45: the worst in-unit
# path is a handoff that settles late plus a first turn that never shows
# (SETTLE_S + FIRST_TURN_S), or a handoff that never settles plus the
# --continue fallback (2 x SETTLE_S). check_claude_boot B11d pins both
# under the unit's timeout.
FIRST_TURN_S = float(os.environ.get("OT_CLAUDE_FIRST_TURN_S", "20"))
RETRY_POLL_S = float(os.environ.get("OT_CLAUDE_RETRY_POLL_S", "30"))
RELAUNCH_AFTER_S = float(os.environ.get("OT_CLAUDE_RELAUNCH_AFTER_S", "660"))
RETRY_WINDOW_S = float(os.environ.get("OT_CLAUDE_RETRY_WINDOW_S", "1800"))
RETRY_MAX = int(os.environ.get("OT_CLAUDE_RETRY_MAX", "2"))
RETRY_LOG = (os.environ.get("OT_CLAUDE_BOOT_LOG")
             or os.path.expanduser("~/.optbot/claude_boot.log"))


def projects_dir() -> str:
    """Where Claude Code writes THIS repo's transcripts: the cwd with every
    non-alphanumeric character turned into '-' (measured: /home/ubuntu/
    options-trader -> -home-ubuntu-options-trader). The gate overrides it."""
    import re
    return (os.environ.get("OT_CLAUDE_PROJECTS_DIR")
            or os.path.join(_claude_dir(), "projects",
                            re.sub(r"[^A-Za-z0-9]", "-", _root)))


def _ts(s) -> float | None:
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:                                           # noqa: BLE001
        return None


def _replies(since: float):
    """-> [(ts, 'ok'|'failed', reason)] for every assistant entry at or after
    `since`, in every transcript touched since then. Never raises.
    🔑 THE DISCRIMINATOR IS MEASURED, NOT ASSUMED: on 09-28 and 09-29 the dead
    turn's entry carries `isApiErrorMessage: true`, `error: server_error` and
    model `<synthetic>`; on 09-26 and 09-27 the good one carries a real model
    and a `requestId`."""
    import json
    out = []
    d = projects_dir()
    try:
        names = [n for n in os.listdir(d) if n.endswith(".jsonl")]
    except OSError:
        return out
    for n in names:
        p = os.path.join(d, n)
        try:
            if os.path.getmtime(p) < since - 2:
                continue
            with open(p, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for ln in lines:
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            if not isinstance(e, dict) or e.get("type") != "assistant":
                continue
            t = _ts(e.get("timestamp"))
            if t is None or t < since - 1:
                continue
            if e.get("isApiErrorMessage"):
                txt = json.dumps((e.get("message") or {}).get("content", ""))
                why = ("login refresh" if "refresh your login" in txt
                       else "API error: %s" % (e.get("error") or "unknown"))
                out.append((t, "failed", why))
            else:
                out.append((t, "ok", ""))
    out.sort()
    return out


def first_turn(since: float, budget: float | None = None) -> tuple[str, str]:
    """-> ('ok'|'failed'|'unseen', reason). The EARLIEST reply after the raise
    is the first turn's verdict; polls until one appears or `budget` runs out.
    The budget is read at CALL time (module FIRST_TURN_S), not bound at def."""
    budget = FIRST_TURN_S if budget is None else budget
    deadline = time.time() + budget
    while True:
        r = _replies(since)
        if r:
            return r[0][1], r[0][2]
        if time.time() >= deadline:
            return "unseen", "no reply in %ds" % int(budget)
        time.sleep(POLL_S)


def _handoff_cmd(binp: str, brief: str) -> str:
    # ⚠️ The brief is passed as ONE argument. r32 measured the hazard: the file
    # contains double quotes, and expanding it through another shell layer ends
    # the argument at the first one and hands Claude a truncated brief.
    return ("%s %s --remote-control %s \"$(cat %s)\"; exec bash"
            % (ENV_STRIP, binp, _sh_quote(rc_name()), _sh_quote(brief)))


def _et_hm() -> str:
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M ET")
    except Exception:                                           # noqa: BLE001
        return time.strftime("%H:%M UTC", time.gmtime())


def _log(msg: str) -> None:
    """§38.7 — an unattended action leaves a record. Never raises."""
    try:
        os.makedirs(os.path.dirname(RETRY_LOG), exist_ok=True)
        if os.path.exists(RETRY_LOG) and os.path.getsize(RETRY_LOG) > 1_000_000:
            os.replace(RETRY_LOG, RETRY_LOG + ".1")
        with open(RETRY_LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), msg))
    except Exception:                                           # noqa: BLE001
        pass


def spawn_retry(since: float) -> bool:
    """Start the detached watcher. It outlives this process in the unit's
    cgroup exactly as the tmux server does (RemainAfterExit=yes, B6)."""
    try:
        subprocess.Popen([sys.executable, os.path.abspath(__file__),
                          "--retry", "--since", "%.3f" % since],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True,
                         cwd=_root)
        return True
    except Exception as exc:                                    # noqa: BLE001
        _log("retry watcher could not start: %s" % type(exc).__name__)
        return False


def _mtime(p: str) -> float:
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0.0


def run_retry(since: float, sleep=time.sleep, now=time.time) -> str:
    """The detached watcher. -> the final status text (also recorded).

    Re-raises the handoff when the login file has been RENEWED since the
    failure, or once RELAUNCH_AFTER_S has passed (the 09-29 refresh lock
    cleared in about ten minutes), at most RETRY_MAX times in RETRY_WINDOW_S.
    🔴 IT STANDS DOWN, AND KILLS NOTHING, the moment (a) any session has
    produced a real reply since the failure, or (b) a claude process appears
    that this watcher did not start. That is the operator restarting by hand,
    and his session is never the one killed."""
    t_fail = since
    cred0 = _mtime(cred_path())
    known = set(live_claude_pids())
    attempts = 0
    start = now()
    brief, first = choose_brief()
    _log("watcher up: first turn not confirmed since %.0f; claude pids %s"
         % (since, sorted(known)))
    while now() - start < RETRY_WINDOW_S:
        sleep(RETRY_POLL_S)
        if any(v == "ok" for _, v, _ in _replies(t_fail)):
            text = "up (handoff — a session replied at %s)" % _et_hm()
            record(text); _log(text)
            return text
        new = set(live_claude_pids()) - known
        if new:
            text = ("up? (a claude this watcher did not start is running, pid %s"
                    " — stood down, killed nothing)" % ",".join(map(str, sorted(new))))
            record(text); _log(text)
            return text
        renewed = _mtime(cred_path()) > cred0
        if not (renewed or now() - t_fail >= RELAUNCH_AFTER_S):
            continue
        if attempts >= RETRY_MAX:
            break
        attempts += 1
        binp = claude_bin()
        if not binp or not os.path.exists(brief):
            break
        _log("relaunch %d (%s)" % (attempts, "login renewed" if renewed else "lock window passed"))
        t_launch = now()
        _kill()
        _raise(_handoff_cmd(binp, brief))
        _settle()
        known = set(live_claude_pids())
        v, why = first_turn(t_launch)
        if v == "ok":
            if first:
                try:
                    os.unlink(FIRST_BOOT_MARKER)
                except OSError:
                    pass
            text = "up (handoff, relaunched %s after a failed first turn)" % _et_hm()
            record(text); _log(text)
            return text
        _log("relaunch %d first turn: %s %s" % (attempts, v, why))
        t_fail, cred0 = t_launch, _mtime(cred_path())
    text = ("NOT AVAILABLE (first turn failed; %d relaunch(es) did not recover it"
            " — ssh in and raise it by hand)" % attempts)
    record(text); _log(text)
    return text


def live_claude_pids(uid: int | None = None) -> list[int]:
    """PIDs of `claude` processes owned by `uid` (default: this user), from /proc.

    🔴 r107 — THIS IS THE LIVENESS TEST THE PURGE NEEDED. `agent_alive()` asks
    whether ONE named tmux session holds claude, which is the right question
    for "is the boot session up" and the wrong one for "may I move scratch
    directories": a claude in another session, outside tmux, or behind an
    overridden `CLAUDE_TMUX` is invisible to it — and B7 overrides exactly that.
    A process table has no name to override.
    ⚠️ READ-ONLY and never raises: an unreadable /proc entry is skipped."""
    want = os.getuid() if uid is None else int(uid)
    out = []
    try:
        names = os.listdir("/proc")
    except OSError:
        return out
    for n in names:
        if not n.isdigit():
            continue
        try:
            if os.stat("/proc/" + n).st_uid != want:
                continue
            with open("/proc/%s/comm" % n) as fh:
                if fh.read().strip() == "claude":
                    out.append(int(n))
        except OSError:
            continue
    return out


def tmpfs_free_mb(path: str = "/tmp") -> int | None:
    """Free megabytes on the filesystem holding `path`, or None."""
    try:
        st = os.statvfs(path)
        return int(st.f_bavail * st.f_frsize / (1024 * 1024))
    except Exception:                                           # noqa: BLE001
        return None


def purge_scratch(root: str | None = None) -> tuple[int, int | None]:
    """Remove OTHER sessions' scratch directories. -> (removed, free_mb_after).

    🔴 r70 (BOX.12) — /tmp IS tmpfs, WHICH IS RAM. 455 MB here of 908 MB
    physical, and the scratchpad path is keyed by SESSION ID, so every new
    session mints a directory and nothing removes the old ones. This box has
    been protected only by its daily reboot; the control box, which does not
    reboot daily, filled its tmpfs completely and EVERY Bash spawn then died
    instantly with no stdout and no stderr — a temp file is needed for the
    shell snapshot, so it fails before executing. An agent that looks
    brain-dead rather than out of space.
    ⚠️ TRANSCRIPTS ARE ON EXT4 (`~/.claude/projects/...`), a different
    filesystem, so this cannot reach them and `tools/last_session.py` still
    reviews the previous thread afterwards. That is measured, not assumed.
    ⚠️ FAILS CLOSED ON THE PATH. The root is rebuilt from `os.getuid()` and
    must match `/tmp/claude-<digits>` exactly; anything else removes nothing.
    A cleanup that globs wrong is worse than no cleanup.
    ⚠️ AND IT NEVER REMOVES THE LIVE SESSION'S OWN DIRECTORY — `CLAUDE_SCRATCH`
    names it when set, so a purge at boot cannot delete the working directory
    of the session it is about to raise.

    🔴 IT ARCHIVES; IT DOES NOT DELETE. Raised by the mainline control agent
    2026-09-20 from a concrete near-miss on their box: an entire unlanded
    revision — the ported raiser, its unit and its gate — was sitting in the
    scratchpad of a session that had been handed off, and a deleting purge
    would have destroyed it. The transcript described the build without
    containing it. **The harness itself directs every agent to put working
    files in the scratchpad**, so treating that directory as disposable is
    wrong by construction. Bytes move to `~/claude_scratch_archive` on ext4
    (5.9 GB free, no quota) and the retention sweep is the ONLY deleting path.
    Their S3.13 is the same lesson at fleet scale: 492,945 objects deleted on
    a reading that turned out to be wrong.
    """
    import re
    import shutil
    # ⚠️ `root` IS A PARAMETER ONLY SO THE GATE CAN DRIVE THIS WITHOUT TOUCHING
    # THE BOX'S REAL SCRATCH ROOT — production passes nothing. A checker that
    # had to delete from the live path to test itself would be r13's class (a
    # fixture reaching live state) with a very bad blast radius.
    root = root or ("/tmp/claude-%d" % os.getuid())
    if not (re.fullmatch(r"/tmp/claude-\d+", root)
            or re.fullmatch(r"/tmp/[A-Za-z0-9_]*scratchtest[A-Za-z0-9_]*", root)):
        return 0, tmpfs_free_mb()
    if not os.path.isdir(root):
        return 0, tmpfs_free_mb()
    # 🔴 r107 — A REAL ROOT IS NEVER PURGED WHILE ITS OWNER HAS A LIVE AGENT.
    # Checked HERE, at the destructive site, and not only by the caller: every
    # future caller inherits it. The uid is read off the root itself, so the
    # rule is "nobody's files move while that user's claude is running".
    _real = re.fullmatch(r"/tmp/claude-(\d+)", root)
    if _real and live_claude_pids(int(_real.group(1))):
        return 0, tmpfs_free_mb()
    keep = os.environ.get("CLAUDE_SCRATCH", "")
    arch = os.path.join(os.path.expanduser("~"), "claude_scratch_archive")
    # ⚠️ ONE LEVEL UNDER $HOME AND CARRYING NO `.git`, deliberately: `land.sh`
    # resolves its target by scanning `$HOME/*/` for a `.git` plus repo
    # markers, so an archive root that never holds one at its own top level
    # cannot be mistaken for a checkout.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    moved = 0
    for name in os.listdir(root):
        p = os.path.join(root, name)
        if keep and (os.path.abspath(keep) == p
                     or os.path.abspath(keep).startswith(p + os.sep)):
            continue                                  # the live session's own
        try:
            os.makedirs(arch, exist_ok=True)
            shutil.move(p, os.path.join(arch, "%s-%s" % (stamp, name)))
            moved += 1
        except Exception:                                       # noqa: BLE001
            pass
    _sweep_archive(arch)
    return moved, tmpfs_free_mb()


ARCHIVE_DAYS = 14


def _sweep_archive(arch: str, days: int = ARCHIVE_DAYS) -> int:
    """The ONLY path that deletes. Bounded retention so archiving is not an
    unbounded trade of disk for reversibility."""
    import shutil
    if not os.path.isdir(arch):
        return 0
    cutoff = time.time() - days * 86400
    gone = 0
    for name in os.listdir(arch):
        p = os.path.join(arch, name)
        try:
            if os.path.getmtime(p) < cutoff:
                shutil.rmtree(p) if os.path.isdir(p) else os.unlink(p)
                gone += 1
        except Exception:                                       # noqa: BLE001
            pass
    return gone


def bring_up(dry: bool = False) -> tuple[bool, str]:
    """-> (ok, status text). Raises a HANDOFF thread from the brief, falls back
    to --continue, and reports WHICH ONE came up.

    ~~r68, 2026-09-20: *"--continue, with fallback"*.~~ SUPERSEDED at r86 by
    the operator, 2026-09-21: *"instead of having a continued agent session on
    boot, it should be a handoff agent session that reads the previous session
    thread. Which I believe is already standard in the turnover."*
    ⚠️ STRUCK, NOT DELETED (r33/r43/r64) — r68's ruling is the reason the
    fallback still exists, and reading only the new one would make the second
    branch look arbitrary.
    🔑 HE IS RIGHT THAT IT IS ALREADY STANDARD: `docs/HANDOFF.md` opens by
    telling the agent to run `tools/last_session.py` — the prior thread's
    operator messages, the revisions that landed in that window and how it
    ended, in 2-7k tokens rather than a 50MB transcript. So the handoff path
    ALREADY reads the previous session; it was simply second in line.
    ⚠️ WHY THE ORDER MATTERS RATHER THAN BEING A PREFERENCE. `--continue`
    resumes a thread whose context is whatever it happened to end on —
    mid-task, mid-diagnosis, possibly compacted. A handoff STARTS from a
    written brief and then goes and reads the prior session deliberately. The
    first is an accident of where yesterday stopped; the second is a briefing.
    ⚠️ `--continue` IS KEPT AS THE FALLBACK and that is deliberate: a missing
    or unreadable brief must not leave the box with no agent at 08:00, and
    resuming yesterday's thread is strictly better than silence (§0.5).
    The mode is still named in the status, because "Claude up" must never be a
    guess about which thread he is attaching to.
    """
    if dry:
        return True, "up (dry-run, nothing raised)"

    if not tmux_bin():
        return False, "NOT AVAILABLE (tmux not found)"

    if agent_alive():
        return True, "up (already running)"

    binp = claude_bin()
    if not binp:
        return False, "NOT AVAILABLE (claude binary not found)"

    # r132 — a DEFINITE "not logged in" is named, not raised into a login
    # screen that reads "up". None (the check could not run) does not block.
    # r170 — read from the login FILE; no claude process is started for it.
    if auth_ok() is False:
        return False, ("NOT AVAILABLE (not logged in — ssh in and run: "
                       "claude auth login)")

    # 1 — r86, THE OPERATOR'S CURRENT RULING: a HANDOFF session, briefed.
    # r132 — FIRST_BOOT.md on a freshly installed box (choose_brief).
    brief, first = choose_brief()
    if os.path.exists(brief):
        _kill()
        t_launch = time.time()
        _raise(_handoff_cmd(binp, brief))
        if _settle():
            # 🔴 r170 — A LIVE PROCESS IS NOT A WORKING TURN. On 09-28 and 09-29
            # this branch returned "up (handoff)" over a session whose only
            # turn had already died on a login refresh.
            label = "first boot" if first else "handoff"
            v, why = first_turn(t_launch)
            if v == "ok":
                if first:
                    try:
                        os.unlink(FIRST_BOOT_MARKER)
                    except OSError:
                        pass
                return True, "up (%s)" % label
            # ⚠️ NO --continue FALLBACK HERE: it would hit the same login.
            retry = spawn_retry(t_launch)
            tail = "auto-retry running" if retry else "auto-retry DID NOT START"
            if v == "failed":
                return False, ("FIRST TURN FAILED (%s, %s) — %s"
                               % (label, why, tail))
            return False, ("up? (%s: process live, %s) — %s" % (label, why, tail))

    # 2 — the fallback, which is r68's ruling kept for exactly this case: a
    # MISSING or UNREADABLE brief, or a handoff that refuses to settle, must
    # not leave the box with no agent at 08:00. Resuming yesterday's thread is
    # strictly better than silence (§0.5).
    _kill()
    _raise("%s %s --remote-control %s --continue; exec bash"
           % (ENV_STRIP, binp, _sh_quote(rc_name())))
    if _settle():
        return True, ("up (continue — FALLBACK, brief missing)"
                      if not os.path.exists(BRIEF) else
                      "up (continue — FALLBACK, handoff did not settle)")

    # 3 — named absence, never silence (§0.5).
    why = "session exists but no claude process" if has_session() else "tmux session did not start"
    return False, "NOT AVAILABLE (%s)" % why


def _sh_quote(p: str) -> str:
    return "'" + p.replace("'", "'\\''") + "'"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would happen; raise nothing")
    ap.add_argument("--status-only", action="store_true",
                    help="report current availability without raising anything")
    ap.add_argument("--retry", action="store_true",
                    help="r170: the detached first-turn watcher (spawned by bring_up)")
    ap.add_argument("--since", type=float, default=None,
                    help="with --retry: epoch of the raise whose first turn failed")
    ap.add_argument("--rc-name", action="store_true",
                    help="r314: print the Remote Control name this box raises under; raise nothing")
    a = ap.parse_args(argv)

    if a.rc_name:
        print(rc_name())
        return 0

    if a.status_only:
        ok = agent_alive()
        print("agent_alive=%s session=%s bin=%s"
              % (ok, has_session(), claude_bin() or "(not found)"))
        # r170 — the watcher's last line, so a recovery is visible without
        # opening the log (the boot alert is never re-sent, header v1.5).
        try:
            with open(RETRY_LOG, encoding="utf-8") as fh:
                last = fh.readlines()[-1:]
            if last:
                print("last watcher line: %s" % last[0].rstrip())
        except OSError:
            pass
        return 0 if ok else 1

    if a.retry:
        # ⚠️ NEVER RAISES, like the raiser — its status IS its report.
        try:
            run_retry(a.since if a.since is not None else time.time())
        except Exception as exc:                                # noqa: BLE001
            text = "NOT AVAILABLE (retry watcher error: %s)" % type(exc).__name__
            record(text); _log(text)
        return 0

    # ⚠️ ANY escape still leaves a STATUS and still exits 0. The unit is ordered
    # before the bot; a traceback here must never become a failed unit with no
    # explanation on the alert. B7 drives exactly this path.
    # 🔴 r70 — ONLY PURGE WHEN WE ARE ACTUALLY GOING TO RAISE. Found by the
    # mainline control agent's review before this shipped: the first cut ran
    # the purge UNCONDITIONALLY and `bring_up()` returns "already running"
    # WITHOUT killing anything when a session is live. Under systemd
    # `CLAUDE_SCRATCH` is unset, so nothing was protected — meaning
    # `systemctl start optbot-claude-boot.service` against a LIVE session would
    # have archived that running agent's working directory out from under it
    # and left it running. The operator ran exactly that command on 2026-09-20.
    # 🔑 GATING ON `agent_alive()` MAKES THE PURGE AND THE RAISE ONE DECISION:
    # we only reclaim when we are replacing, which is the only moment it is safe.
    freed = tmpfs_free_mb()
    # 🔴 r107 — AND ANY LIVE claude PROCESS, NOT ONLY THE NAMED SESSION. The
    # named-session test alone let B7 purge under a running agent ten times.
    _live = live_claude_pids()
    if a.dry_run or agent_alive() or _live:
        print("claude_boot: a session is live — scratch purge SKIPPED"
              + (" (claude pid(s) %s)" % ",".join(map(str, _live)) if _live else ""))
    else:
        try:
            # ⚠️ r107 — the gate aims this at a FIXTURE root; production sets
            # nothing. `purge_scratch` refuses any root that is not the real
            # one or a `scratchtest` path, so this cannot widen the target.
            n, freed = purge_scratch(os.environ.get("OT_CLAUDE_SCRATCH_ROOT") or None)
            print("claude_boot: scratch purge: archived %d stale scratch dir(s)" % n)   # r235: 0 is said too
        except Exception as exc:                                # noqa: BLE001
            print("claude_boot: scratch purge skipped (%s)" % type(exc).__name__)

    try:
        ok, text = bring_up(dry=a.dry_run)
    except Exception as exc:                                    # noqa: BLE001
        ok, text = False, "NOT AVAILABLE (raiser error: %s)" % type(exc).__name__
    # 🔑 THE FREE-SPACE FIGURE RIDES THE STATUS STRING, so it reaches the boot
    # Telegram beside the IP with NO change to alert_manager — the operator
    # sees "tmpfs 454M free" every morning instead of discovering a full one
    # when a shell dies three days later.
    if freed is not None:
        text = "%s, tmpfs %dM free" % (text, freed)
    record(text)
    print("claude_boot: %s" % text)
    # ⚠️ EXIT 0 EVEN ON FAILURE, DELIBERATELY. This unit is ordered BEFORE the
    # bot; a non-zero exit would mark it failed and, with the wrong dependency
    # later added, could hold up trading. §29 — nothing on this box may be
    # load-bearing for the bot. THE STATUS FILE IS THE REPORT, not the exit
    # code, and the operator reads it on the boot alert.
    return 0


if __name__ == "__main__":
    sys.exit(main())
