"""tests/check_bootstrap.py — v5.1
v5.1  2026-10-25  OTV5 r10 (BOOT.10) — G18: THE TEMPLATE'S DEFAULTS ARE A FRESH OTV5 BOX'S. Its own export lines,
      evaluated by bash, raise Claude at boot (OT_CLAUDE_AT_BOOT=1), leave GITHUB_TOKEN empty and pushing off,
      and - DRIVEN through the real deploy/install_claude.sh in a fixture HOME with exactly those values - install
      the pull-only settings (the deny rules), not the deny-less default. BORN RED on r9 (AT_BOOT 0, token
      REPLACE_ME, OT_CLAUDE_SETTINGS absent so the default file landed). G18 also bars the predecessor's names
      from the template's instructions.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...

v1.12 2026-10-24 — OTV5 r0. RE-POINTED, NOT DROPPED (section 38.4): G3's planned git_repo is the deploy/origin.conf
      repository (the same value G2 reads), not a literal of one repository's name; a tree seeded into a new repository
      changes origin.conf and the gate follows it.

v1.11 2026-10-24 — CD.1. RE-POINTED, NOT DROPPED (section 38.4): G2 reads the repository from deploy/origin.conf
      (install.sh's OT_DEFAULT_REPO; the template's GITHUB_REPO) and G9 expects the template with {{ORIGIN_REPO}}
      rendered. OT_START_BOT is gone (the operator: "starting the
      bot should be transparent & intuitive, not hidden by some cryptic or occult tag"), so G3's start_bot line
      becomes first_start and data_capture_requested; G3c expects data_capture=standalone with the managed request
      recorded; G16 now pins that setup enables and starts NEITHER the bot NOR candle-feed and leaves both to
      deploy/install_services.sh (whose behaviour tests/check_clean_deploy.py C1/C2 drives).
v1.10 2026-10-03 — OTV4TEST r228. G17 RE-POINTED (section 38.4): the ORB and VOLT scaling
      items left configure.sh; Breakout scaling is item 9, and the two lines that lost their
      item must say so rather than name a number.

v1.9  2026-09-29 — OTV4TEST r170. G10 RE-POINTED (section 38.4): claude_boot's
      auth_ok() reads the login FILE instead of running `claude auth status`
      (the only other claude process at the 08:00 boot on 09-28 and 09-29, when
      the session's first login refresh failed). Same True/False/None
      contract, now driven with a present, an absent and a malformed file.
      Red at G10 alone on the r170 code before this change, measured.

v1.8  2026-09-27 — OTV4TEST r168. G3 RE-POINTED (section 38.4): the suite gains
      deploy/install_emergency_watchdog.sh, before install_claude.sh as setup_ec2 v4.9 lists it.

v1.7  2026-09-27 — OTV4TEST r162. G17 RE-POINTED (section 38.4): item 6's label is
      "Daily catastrophic loss cap" (the operator's name); same key, same item.

v1.6  2026-09-27 — OTV4TEST r161. RE-POINTED, NOT DROPPED (section 38.4): the ramp
      START is merged into risk per trade (the operator: "Merge it"), so setup no
      longer plans or writes OT_ORB_RISK_USD. G3 plans scale_orb/breakout/volt=1
      (the code default, so a fresh box sizes as this one does); G3c's "risk 500
      flows" now reaches the TOP and the loss cap, and an OT_SCALE_ORB=0 from the
      bootstrap wins; G5 requires the three switches in the unit AND that
      OT_ORB_RISK_USD is no longer written there; G17 names items 2, 8, 9, 10, 11.

v1.5  2026-09-25 — OTV4TEST r138. G16: setup installs the bot but never ENABLES or
      STARTS it unless OT_START_BOT=1 (the operator: "defaulted to not started");
      G11's live-unit comparison drops Wants (the installer deliberately no longer
      pulls the bot up) and asserts its absence instead; G17: every sizing line in
      bootstrap.example.sh names its configure.sh item.

v1.4  2026-09-24 — OTV4TEST r136. MOVED, NOT DROPPED (section 38.4): G3's
      "plan masked=s3-push..." is now "plan data_capture=standalone" - the mask
      is what standalone data capture does (check_data_capture D3 proves it), and
      the unattended default must still be standalone. G3c adds managed.

v1.3  2026-09-24 — OTV4TEST r135. G15: a fresh box's FIRST hourly backfill is
      deep enough for everything that reads it, and no deeper than what is kept -
      BACKFILL_DAYS['1h'] > 30 (check_level_tape T7), enough sessions for the
      bot's 1h frame (config.py TIMEFRAMES["1h"]["candles"] at 7 RTH bars a
      session, one holiday allowed), and <= RETENTION_DAYS['1h'] (the nightly
      purge would delete the rest). TastyTrade serves 90 days (measured r135).

v1.2  2026-09-24 — OTV4TEST r134. From the first fresh box's own report. G13:
      nothing setup_ec2.sh makes executable is tracked non-executable, so a fresh
      box starts with a CLEAN `git status` (analysis/get_orb_range.py, 100644, was
      chmod'ed and every box began dirty). G14: FIRST_BOOT.md's warm-up section
      states the hourly backfill as data/candle_feed.py actually sets it (the
      brief cannot drift from the code), names T7, and tells the agent to
      introduce itself to its peers - with ListAgents and SendMessage allowed.
A FRESH BOX CAN BE BUILT FROM THIS REPO, HANDS-FREE, AND IT IS THIS REPO IT BUILDS.

v1.1  2026-09-24 — OTV4TEST r133. G12: every banner the installers draw is
      RENDERED and measured - all box lines one width, in the C and the UTF-8
      locale (the operator circled the overshooting border on the first proving
      run; a 53-character line in a 52 box was caught by this measurement before
      it shipped). G9f: ~/.local/bin is put on PATH in ~/.bashrc exactly once.

v1.0  2026-09-24 — OTV4TEST r132. The operator: "make sure that I can do a boot
      strap install of this repo onto a fresh instance using unattended install
      with pre-seeded boot strap file", "The entire Suite", "freeze every
      software version", a swap file, a toggle for Claude at first boot, and
      "Can we add the Claude authentication into the bootstrap's secret file".
      Nothing gated the install chain before this file; every defect it names
      was found by reading the chain against the reference box:
        · the template was IGNORED (a sorted .gitignore put `!` before the rule),
        · the template and deploy/install.sh installed options_trader_v3,
        · setup_ec2.sh died without a terminal (`exec < /dev/tty` under set -e),
        · git fetch failures were `|| true`, and a public repo still demanded a token,
        · four configure.sh keys were never primed — the pin gate would run ON,
        · no swap, no pins, no boot-sweep installer, no Claude, no timers.

  G1  .gitignore: the template is NOT ignored, bootstrap.sh IS
  G2  the chain points at OTV4TEST (template, installer), not options_trader_v3
  G3  setup_ec2.sh --plan, NO TERMINAL, unattended: rc 0, the primed values,
      the pinned lock, the whole suite present — and it calls NO sudo and
      writes nothing into HOME (a sudo stub that REFUSES and logs is on PATH)
  G3b OT_CLAUDE_AT_BOOT decides whether the claude-boot installer is in the suite
  G3c the bootstrap's own values win over the defaults
  G4  no credentials and no terminal: a NAMED refusal, rc 1, bounded in time
  G5  setup_ec2.sh text: no bare `exec < /dev/tty`, no `git fetch ... || true`,
      no pip upgrade, the four keys in the bot unit, secrets unset before the
      final shell
  G6  requirements.lock: all `==`; covers requirements.txt and every third-party
      import of the runtime tree; equals the reference venv where one exists
  G7  .claude/settings.json (committed, PUBLIC): project keys only, the
      credential denies present, git push asks, no secret-shaped strings
  G8  deploy/claude-user-settings.json: Remote Control on, auto-updater off,
      the auto-mode hard denies present, no secret-shaped strings
  G9  install_claude.sh in a fixture HOME with a fake pinned binary: settings
      written, login installed 0600 and NEVER PRINTED, first-run flags seeded,
      no download attempted, the temp dir gone; G9b a box's own settings are
      never overwritten; G9c not logged in is reported, rc 0; G9d a wrong
      binary version that cannot be replaced is rc 1; G9e a garbage login is
      ignored, not installed
  G10 claude_boot.py: FIRST_BOOT.md while the marker exists, HANDOFF.md after;
      auth_ok True/False/None on a login file present/absent/malformed
      (r170; was rc 0/1/other of `claude auth status`); a definite not-logged-in
      raises NOTHING and says so; OT_RC_NAME names the session
  G11 install_boot_sweep.sh rendered with sudo stubbed: the unit the reference
      box runs (ExecStart, ordering, Nice, timeouts), path-substituted
  G0  /etc/systemd/system untouched; the real ~/.claude untouched
"""
from __future__ import annotations

import ast
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

FAILED, RAN = [], []
_TMP = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, "%s: %s" % (type(exc).__name__, exc))
        return
    try:
        d = detail()
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)


def _mk(prefix):
    d = tempfile.mkdtemp(prefix="bootstrapcheck_" + prefix)
    _TMP.append(d)
    return d


def _read(rel):
    """"" for a missing file, so a born-red run reports EVERY red, not the first."""
    try:
        with open(os.path.join(_root, rel), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _json(rel):
    try:
        return json.loads(_read(rel))
    except ValueError:
        return {}


def _code_lines(txt):
    return [ln for ln in txt.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


_SECRETISH = re.compile(r"(sk-ant-|ghp_|github_pat_|xox[bp]-|AKIA[0-9A-Z]{12}|"
                        r"[A-Za-z0-9+/]{60,}={0,2})")

_sysd_before = sorted(os.listdir("/etc/systemd/system")) if os.path.isdir(
    "/etc/systemd/system") else []
_REAL_CLAUDE = os.path.expanduser("~/.claude")


def _snap_claude():
    out = {}
    for n in ("settings.json", ".credentials.json"):
        p = os.path.join(_REAL_CLAUDE, n)
        out[n] = os.stat(p).st_mtime_ns if os.path.exists(p) else None
    return out


_claude_before = _snap_claude()

# ── G1 ────────────────────────────────────────────────────────────────────────
def _ignored(name):
    r = subprocess.run(["git", "-C", _root, "check-ignore", "-v", "--no-index", name],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False
    pattern = r.stdout.split("\t")[0].split(":", 2)[-1]
    return not pattern.startswith("!")


guard("G1 .gitignore: bootstrap.example.sh is NOT ignored",
      lambda: not _ignored("bootstrap.example.sh"))
guard("G1 .gitignore: bootstrap.sh (the secrets copy) IS ignored",
      lambda: _ignored("bootstrap.sh") and _ignored("bootstrap-qqq.sh"))

# ── G2 ────────────────────────────────────────────────────────────────────────
_boot = _read("bootstrap.example.sh")
_inst = _read("deploy/install.sh")
_origin = subprocess.run(["bash", "-c", '. "%s/deploy/origin.conf" && echo "$OT_ORIGIN_REPO"' % _root],
                         capture_output=True, text=True).stdout.strip()
guard("G2 the template installs the origin.conf repository through deploy/install.sh",
      lambda: ('GITHUB_REPO="%s"' % _origin) in _boot
      and "${GITHUB_REPO}/${OT_GIT_REF}/deploy/install.sh" in _boot)
guard("G2 deploy/install.sh clones the origin.conf repository by default (driven: tests/check_origin.py O1)",
      lambda: ('OT_DEFAULT_REPO="%s"' % _origin) in _inst
      and 'REPO="${OT_REPO_URL:-https://github.com/${OT_DEFAULT_REPO}.git}"' in _inst)
guard("G2 no executable line in the chain names options_trader_v3",
      lambda: not any("options_trader_v3" in ln
                      for t in (_boot, _inst, _read("setup_ec2.sh"))
                      for ln in _code_lines(t)))
guard("G2 the template carries no real-looking secret",
      lambda: not _SECRETISH.search("\n".join(_code_lines(_boot))))

# ── G3 / G4 — the real setup_ec2.sh, no terminal ────────────────────────────
_SUDO_LOG = None


def _sandbox():
    global _SUDO_LOG
    home = _mk("home_")
    stubs = _mk("stubs_")
    _SUDO_LOG = os.path.join(stubs, "sudo.log")
    with open(os.path.join(stubs, "sudo"), "w") as fh:
        fh.write('#!/bin/sh\necho "sudo $*" >> "%s"\necho "REFUSED sudo $*" >&2\nexit 90\n'
                 % _SUDO_LOG)
    os.chmod(os.path.join(stubs, "sudo"), 0o755)
    return home, stubs


_CREDS = {"TT_CLIENT_SECRET": "fx-secret", "TT_REFRESH_TOKEN": "fx-refresh",
          "TT_ACCOUNT_NUMBER": "fx-acct", "TELEGRAM_TOKEN": "fx-tg",
          "TELEGRAM_CHAT_ID": "fx-chat"}


def _setup(args, extra=None, creds=True):
    home, stubs = _sandbox()
    env = {"PATH": stubs + ":/usr/bin:/bin", "HOME": home}
    if creds:
        env.update(_CREDS)
    env.update(extra or {})
    r = subprocess.run(["setsid", "-w", "bash", os.path.join(_root, "setup_ec2.sh"), *args],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       env=env, timeout=60)
    plan = {}
    suite = []
    for ln in r.stdout.splitlines():
        m = re.match(r"PLAN (\w+)=(.*)$", ln)
        if m:
            if m.group(1) == "suite":
                suite.append(m.group(2))
            else:
                plan[m.group(1)] = m.group(2)
    sudo_calls = open(_SUDO_LOG).read() if os.path.exists(_SUDO_LOG) else ""
    return r, plan, suite, os.listdir(home), sudo_calls


_R = {}
_R["base"] = _setup(["--plan"], {"OT_CLAUDE_AT_BOOT": "1", "CLAUDE_LOGIN_B64": "x"})
r, plan, suite, home_after, sudo_calls = _R["base"]
_WANT = {"unattended": "true", "tty": "0", "paper": "True", "instrument": "QQQ",
         "risk_usd": "200", "orb_budget_usd": "200",
         "scale_orb": "1", "scale_breakout": "1", "scale_volt": "1",
         "daily_loss_limit": "200", "pin_gate": "0", "swap_gb": "2",
         "requirements": "requirements.lock", "git_repo": _origin,       # v1.12: origin.conf, as G2
         "git_ref": "main", "git_push": "0", "claude_at_boot": "1",
         "claude_login": "provided", "data_capture": "standalone", "data_capture_requested": "standalone"}
guard("G3 --plan with no terminal exits 0", lambda: r.returncode == 0,
      lambda: "rc=%s %s" % (r.returncode, (r.stderr or r.stdout)[-200:]))
for k, v in _WANT.items():
    guard("G3 plan %s=%s" % (k, v), lambda k=k, v=v: plan.get(k) == v,
          lambda k=k: "got %r" % plan.get(k))
_SUITE = ["deploy/harden_hosts.sh", "deploy/install_midnight_halt.sh",
          "deploy/install_retention_purge_timer.sh", "deploy/install_open_scan_timer.sh",
          "deploy/install_boot_sweep.sh", "deploy/install_emergency_watchdog.sh",
          "deploy/install_claude.sh",
          "deploy/install_claude_boot.sh"]
guard("G3 the whole suite is planned and every file is present",
      lambda: [s.split(" ")[0] for s in suite] == _SUITE
      and all(s.endswith("present=yes") for s in suite),
      lambda: "; ".join(suite))
guard("G3 --plan calls NO sudo", lambda: sudo_calls == "", lambda: sudo_calls[:200])
guard("G3 --plan writes nothing into HOME", lambda: home_after == [],
      lambda: str(home_after))

r0, plan0, suite0, _h, _s = _setup(["--plan"], {"OT_CLAUDE_AT_BOOT": "0"})
guard("G3b OT_CLAUDE_AT_BOOT=0 leaves the claude-boot installer out, keeps install_claude",
      lambda: r0.returncode == 0 and plan0.get("claude_at_boot") == "0"
      and not any("install_claude_boot.sh" in s for s in suite0)
      and any(s.startswith("deploy/install_claude.sh") for s in suite0)
      and plan0.get("claude_login") == "absent")

r1, plan1, _s1, _h1, _x1 = _setup(["--plan"], {"OT_RISK_USD": "500", "OT_PIN_PROXIMITY_ACTIVE": "1",
                                               "OT_SWAP_GB": "0", "OT_GIT_PUSH": "1",
                                               "OT_GIT_REF": "abc1234", "OT_DATA_CAPTURE": "managed",
                                               "OT_SCALE_ORB": "0"})
guard("G3c the bootstrap's values win (risk 500 flows to TOP/loss; ORB scaling off; gate, swap, push, ref)",
      lambda: r1.returncode == 0 and "orb_risk_usd" not in plan1
      and plan1.get("scale_orb") == "0" and plan1.get("scale_breakout") == "1"
      and plan1.get("orb_budget_usd") == "500" and plan1.get("daily_loss_limit") == "500"
      and plan1.get("pin_gate") == "1" and plan1.get("swap_gb") == "0"
      and plan1.get("git_push") == "1" and plan1.get("git_ref") == "abc1234"
      and plan1.get("data_capture") == "standalone" and plan1.get("data_capture_requested") == "managed"
      and "start_bot" not in plan1 and "first_start" in plan1,
      lambda: str(plan1))

r4, _p4, _s4, home4, sudo4 = _setup([], creds=False)
guard("G4 no credentials + no terminal: rc 1 with the named refusal, no sudo, no writes",
      lambda: r4.returncode == 1 and "No credentials in the environment" in r4.stdout
      and sudo4 == "" and home4 == [],
      lambda: "rc=%s %s" % (r4.returncode, r4.stdout[-160:]))

# ── G5 ────────────────────────────────────────────────────────────────────────
_setup_txt = _read("setup_ec2.sh")
guard("G5 no bare top-level `exec < /dev/tty`",
      lambda: not re.search(r"^exec < /dev/tty", _setup_txt, re.M))
guard("G5 no silent `git fetch ... || true`",
      lambda: not re.search(r"git fetch[^\n]*\|\| true", _setup_txt))
guard("G5 no pip self-upgrade (a version change the freeze forbids)",
      lambda: "pip install --upgrade pip" not in _setup_txt)
_unit = _setup_txt[_setup_txt.find("${SERVICE_NAME}.service > /dev/null << SVCEOF"):
                   _setup_txt.find("SVCEOF\n\nsudo chmod 600")]
guard("G5 the bot unit no longer writes the merged OT_ORB_RISK_USD (r161)",
      lambda: "Environment=OT_ORB_RISK_USD" not in _unit)
guard("G5 the bot unit carries the keys configure.sh grew",
      lambda: all("Environment=%s=${%s}" % (k, v) in _unit for k, v in (
          ("OT_SCALE_ORB", "SCALE_ORB"), ("OT_SCALE_BREAKOUT", "SCALE_BREAKOUT"),
          ("OT_SCALE_VOLT", "SCALE_VOLT"), ("OT_ORB_BUDGET_USD", "ORB_BUDGET_USD"),
          ("OT_DAILY_LOSS_LIMIT", "DAILY_LOSS_LIMIT"),
          ("OT_PIN_PROXIMITY_ACTIVE", "PIN_GATE"))))
guard("G5 secrets are unset before the final login shell",
      lambda: (lambda u, e: 0 <= u < e)(
          _setup_txt.find("unset TT_CLIENT_SECRET TT_REFRESH_TOKEN TELEGRAM_TOKEN GITHUB_TOKEN CLAUDE_LOGIN_B64"),
          _setup_txt.rfind("exec bash --login")))

# ── G6 ────────────────────────────────────────────────────────────────────────
def _lock():
    pins = {}
    for ln in _read("requirements.lock").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        name, _, ver = ln.partition("==")
        pins[name.lower().replace("_", "-")] = ver
    return pins


_LOCK = _lock()
guard("G6 every lock line is an exact pin",
      lambda: _LOCK and all(v for v in _LOCK.values()), lambda: "%d pins" % len(_LOCK))


def _floors():
    out = []
    for ln in _read("requirements.txt").splitlines():
        ln = ln.split("#")[0].strip()
        if ln:
            out.append(re.split(r"[<>=!~ ]", ln)[0].lower().replace("_", "-"))
    return out


guard("G6 the lock pins every package requirements.txt names",
      lambda: all(p in _LOCK for p in _floors()), lambda: str(_floors()))

_IMPORT_TO_DIST = {"tastytrade": "tastytrade", "pandas": "pandas", "numpy": "numpy",
                   "pytz": "pytz", "boto3": "boto3", "requests": "requests",
                   "botocore": "botocore"}


def _third_party_imports():
    std = set(sys.stdlib_module_names)
    # every module name the repo itself defines, at any depth: tools/ modules are
    # imported by PATH (sys.path.insert), so `import manifold_health` is local.
    local = {n[:-3] if n.endswith(".py") else n for n in os.listdir(_root)}
    for dp, dn, fn in os.walk(_root):
        if "/." in dp or "venv" in dp:
            continue
        local.update(f[:-3] for f in fn if f.endswith(".py"))
        local.update(dn)
    found = set()
    for top in ("analysis", "data", "database", "derived", "execution", "notifications",
                "risk", "strategy", "tools", "utils", "warehouse", "main.py", "config.py"):
        base = os.path.join(_root, top)
        files = [base] if top.endswith(".py") else [
            os.path.join(dp, f) for dp, _dn, fn in os.walk(base) for f in fn if f.endswith(".py")]
        for p in files:
            try:
                tree = ast.parse(open(p, encoding="utf-8", errors="replace").read())
            except (SyntaxError, OSError):
                continue
            for n in ast.walk(tree):
                mods = []
                if isinstance(n, ast.Import):
                    mods = [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                    mods = [n.module]
                for m in mods:
                    t = m.split(".")[0]
                    if t not in std and t not in local and t != "__future__":
                        found.add(t)
    return found


_imports = _third_party_imports()
guard("G6 every third-party import of the runtime tree is pinned",
      lambda: all(_IMPORT_TO_DIST.get(m, m).lower().replace("_", "-") in _LOCK for m in _imports),
      lambda: "imports: %s" % sorted(_imports))

_venv_pip = os.path.join(_root, "venv", "bin", "pip")
if os.path.exists(_venv_pip):
    def _venv_eq():
        fr = subprocess.run([_venv_pip, "freeze", "--exclude-editable"],
                            capture_output=True, text=True).stdout
        have = {}
        for ln in fr.splitlines():
            if "==" in ln:
                a, _, b = ln.partition("==")
                have[a.lower().replace("_", "-")] = b
        return have == _LOCK
    guard("G6 the lock equals this box's venv exactly", _venv_eq)
else:
    check("G6 the lock equals this box's venv exactly (no venv here — not applicable)", True)

# ── G7 / G8 ───────────────────────────────────────────────────────────────────
_proj = _json(".claude/settings.json")
_perm = _proj.get("permissions", {})
_DENY_NEEDED = _json("tests/bootstrap_required_denies.json").get("deny", [])
guard("G7 .claude/settings.json holds project-scope keys only",
      lambda: _proj and set(_proj) <= {"permissions", "env"} and "autoMode" not in _proj
      and "remoteControlAtStartup" not in _proj, lambda: str(sorted(_proj)))
guard("G7 the credential-printing and bypass denies are present",
      lambda: len(_DENY_NEEDED) == 7 and all(d in _perm.get("deny", []) for d in _DENY_NEEDED))
guard("G7 git push and git commit ASK; the lander is allowed",
      lambda: "Bash(git push *)" in _perm.get("ask", [])
      and "Bash(git commit *)" in _perm.get("ask", [])
      and any("land.sh" in a for a in _perm.get("allow", [])))
guard("G7 no secret-shaped string, no box-local parked path",
      lambda: not _SECRETISH.search(_read(".claude/settings.json"))
      and "parked_r110" not in _read(".claude/settings.json"))

_user = _json("deploy/claude-user-settings.json")
guard("G8 user template: Remote Control at startup, auto-updater off",
      lambda: _user.get("remoteControlAtStartup") is True
      and _user.get("env", {}).get("DISABLE_AUTOUPDATER") == "1")
guard("G8 user template: auto-mode hard denies carry the credential and S3 rules",
      lambda: any("printing credentials" in h for h in _user["autoMode"]["hard_deny"])
      and any("S3 warehouse" in h for h in _user["autoMode"]["hard_deny"]))
guard("G8 user template: no secret-shaped string, no box-local parked path",
      lambda: not _SECRETISH.search(_read("deploy/claude-user-settings.json"))
      and "parked_r110" not in _read("deploy/claude-user-settings.json"))

# ── G9 — install_claude.sh in a fixture HOME ─────────────────────────────────
_PIN = (re.search(r'VERSION="\$\{OT_CLAUDE_VERSION:-([0-9.]+)\}"',
                  _read("deploy/install_claude.sh")) or re.match("(.*)", "0")).group(1)
_FAKE_CRED = '{"claudeAiOauth":{"accessToken":"FIXTURE-TOKEN-NEVER-PRINT"}}'


def _login_b64():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in ((".credentials.json", _FAKE_CRED),
                           (".claude.json", '{"oauthAccount":{"emailAddress":"fx@example"},"userID":"fx"}')):
            b = data.encode()
            ti = tarfile.TarInfo(name)
            ti.size = len(b)
            tf.addfile(ti, io.BytesIO(b))
    return base64.b64encode(buf.getvalue()).decode()


def _fixture_home(version, auth_rc):
    home = _mk("claudehome_")
    bindir = os.path.join(home, ".local", "bin")
    os.makedirs(bindir)
    with open(os.path.join(bindir, "claude"), "w") as fh:
        fh.write('#!/bin/sh\ncase "$1" in\n  --version) echo "%s (Claude Code)";;\n'
                 '  auth) exit %d;;\nesac\n' % (version, auth_rc))
    os.chmod(os.path.join(bindir, "claude"), 0o755)
    stubs = _mk("curlstub_")
    with open(os.path.join(stubs, "curl"), "w") as fh:
        fh.write('#!/bin/sh\necho called >> "%s/curl.log"\nexit 7\n' % stubs)
    os.chmod(os.path.join(stubs, "curl"), 0o755)
    return home, stubs


def _run_ic(home, stubs, login=None):
    env = {"HOME": home, "PATH": stubs + ":/usr/bin:/bin"}
    if login is not None:
        env["CLAUDE_LOGIN_B64"] = login
    return subprocess.run(["bash", os.path.join(_root, "deploy", "install_claude.sh")],
                          capture_output=True, text=True, env=env, timeout=60)


_h9, _st9 = _fixture_home(_PIN, 0)
_r9 = _run_ic(_h9, _st9, _login_b64())
_cred9 = os.path.join(_h9, ".claude", ".credentials.json")
_cj9 = os.path.join(_h9, ".claude.json")


def _g9_flags():
    d = json.load(open(_cj9))
    return (d.get("hasCompletedOnboarding") is True and d.get("remoteDialogSeen") is True
            and d["projects"][_root]["hasTrustDialogAccepted"] is True
            and d.get("oauthAccount", {}).get("emailAddress") == "fx@example")


guard("G9 rc 0 and reports logged in", lambda: _r9.returncode == 0 and "✅ logged in" in _r9.stdout,
      lambda: _r9.stdout[-200:])
guard("G9 user settings written from the template",
      lambda: open(os.path.join(_h9, ".claude", "settings.json")).read()
      == _read("deploy/claude-user-settings.json").replace("{{ORIGIN_REPO}}", _origin))
guard("G9 the login is installed, 0600, byte-exact",
      lambda: open(_cred9).read() == _FAKE_CRED and (os.stat(_cred9).st_mode & 0o777) == 0o600)
guard("G9 the login is NEVER printed",
      lambda: "FIXTURE-TOKEN" not in _r9.stdout + _r9.stderr)
guard("G9 first-run flags seeded and the account profile carried (0600)",
      lambda: _g9_flags() and (os.stat(_cj9).st_mode & 0o777) == 0o600)
guard("G9 no download attempted when the pinned binary is present",
      lambda: not os.path.exists(os.path.join(_st9, "curl.log")))
guard("G9 the temporary login directory is gone",
      lambda: not [n for n in os.listdir(_h9) if n.startswith(".claude-login.")])


def _g9b():
    p = os.path.join(_h9, ".claude", "settings.json")
    open(p, "w").write('{"theme":"box-own"}')
    r = _run_ic(_h9, _st9)
    return r.returncode == 0 and open(p).read() == '{"theme":"box-own"}'


guard("G9b a box's own settings are never overwritten on re-run", _g9b)


def _g9c():
    h, st = _fixture_home(_PIN, 1)
    r = _run_ic(h, st)
    return r.returncode == 0 and "NOT logged in" in r.stdout and "claude auth login" in r.stdout


guard("G9c not logged in: named with the fix, rc 0", _g9c)


def _g9d():
    h, st = _fixture_home("0.0.1", 0)
    r = _run_ic(h, st)
    return r.returncode == 1 and os.path.exists(os.path.join(st, "curl.log"))


guard("G9d a wrong binary it cannot replace is rc 1 (the pin is enforced)", _g9d)


def _g9e():
    h, st = _fixture_home(_PIN, 0)
    r = _run_ic(h, st, "not-base64-at-all!!")
    return (r.returncode == 0 and "ignored" in r.stdout
            and not os.path.exists(os.path.join(h, ".claude", ".credentials.json")))


guard("G9e a garbage login is ignored, not installed", _g9e)

# ── G10 — claude_boot.py ─────────────────────────────────────────────────────
_PROBE = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1])
import tools.claude_boot as cb
out = {}
out["rc_name"] = cb.RC_NAME
b, first = cb.choose_brief(); out["with_marker"] = [os.path.basename(b), first]
os.unlink(cb.FIRST_BOOT_MARKER)
b, first = cb.choose_brief(); out["without_marker"] = [os.path.basename(b), first]
out["auth"] = [cb.auth_ok(p) for p in sys.argv[2:5]]
cb.claude_bin = lambda: sys.argv[5]
cb.tmux_bin = lambda: "/usr/bin/tmux" if os.path.exists("/usr/bin/tmux") else "/bin/true"
cb.agent_alive = lambda name=cb.SESSION: False
raised = []
cb._raise = lambda cmd, name=cb.SESSION: raised.append(cmd)
cb._kill = lambda name=cb.SESSION: None
out["bring_up"] = list(cb.bring_up())
out["raised"] = raised
print(json.dumps(out))
'''


def _stub_bin(d, name, rc):
    p = os.path.join(d, name)
    with open(p, "w") as fh:
        fh.write("#!/bin/sh\nexit %d\n" % rc)
    os.chmod(p, 0o755)
    return p


def _g10():
    d = _mk("cb_")
    marker = os.path.join(d, "first_boot")
    open(marker, "w").close()
    # r170 — auth_ok reads the LOGIN FILE (no `claude auth status`): a login,
    # no file at all, and a malformed file. Same True/False/None contract.
    creds = [os.path.join(d, "cred_ok.json"), os.path.join(d, "cred_absent.json"),
             os.path.join(d, "cred_bad.json")]
    open(creds[0], "w").write('{"claudeAiOauth":{"refreshToken":"FIXTURE-NEVER-PRINT"}}')
    open(creds[2], "w").write("{not json")
    binp = _stub_bin(d, "c_ok", 0)
    env = {**os.environ, "OT_FIRST_BOOT_MARKER": marker, "OT_RC_NAME": "fixture-rc",
           "OT_AGENT_STATUS": os.path.join(d, "S"), "HOME": d}
    env.pop("CLAUDE_CONFIG_DIR", None)      # the not-logged-in case reads HOME's
    r = subprocess.run([sys.executable, "-c", _PROBE, _root, *creds, binp], capture_output=True,
                       text=True, env=env, timeout=60)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"err": r.stderr[-300:]}


_G10 = _g10()
guard("G10 FIRST_BOOT.md while the marker exists, HANDOFF.md after",
      lambda: _G10["with_marker"] == ["FIRST_BOOT.md", True]
      and _G10["without_marker"] == ["HANDOFF.md", False], lambda: str(_G10)[:200])
guard("G10 auth_ok (the login file): present True, absent False, malformed None",
      lambda: _G10["auth"] == [True, False, None])
guard("G10 not logged in raises NOTHING and names the fix",
      lambda: _G10["bring_up"][0] is False and "not logged in" in _G10["bring_up"][1]
      and _G10["raised"] == [])
guard("G10 OT_RC_NAME names the Remote Control session", lambda: _G10["rc_name"] == "fixture-rc")
guard("G10 docs/FIRST_BOOT.md exists and is read-only by instruction",
      lambda: "READ-ONLY" in _read("docs/FIRST_BOOT.md")
      and "last_session.py" in _read("docs/FIRST_BOOT.md"))

# ── G11 — install_boot_sweep.sh, sudo stubbed ────────────────────────────────
def _g11():
    d = _mk("bs_")
    repo = os.path.join(d, "repo")
    os.makedirs(os.path.join(repo, "deploy"))
    os.makedirs(os.path.join(repo, "venv", "bin"))
    src = os.path.join(_root, "deploy", "install_boot_sweep.sh")
    if not os.path.exists(src):
        return 1, "", repo
    shutil.copy(src, os.path.join(repo, "deploy", "install_boot_sweep.sh"))
    py = os.path.join(repo, "venv", "bin", "python")
    open(py, "w").write("#!/bin/sh\nexit 0\n")
    os.chmod(py, 0o755)
    out = os.path.join(d, "unit.txt")
    stub = os.path.join(d, "sudo")
    with open(stub, "w") as fh:
        fh.write('#!/bin/sh\ncase "$1" in\n  tee) cat > "%s"; exit 0 ;;\n'
                 '  systemctl) echo "systemctl $*" >> "%s.log"; exit 0 ;;\n'
                 '  *) echo "REFUSED: $*" >&2; exit 90 ;;\nesac\n' % (out, out))
    os.chmod(stub, 0o755)
    fake_sc = os.path.join(d, "systemctl")
    with open(fake_sc, "w") as fh:
        fh.write("#!/bin/sh\nexit 0\n")
    os.chmod(fake_sc, 0o755)
    r = subprocess.run(["bash", os.path.join(repo, "deploy", "install_boot_sweep.sh")],
                       capture_output=True, text=True, timeout=60,
                       env={**os.environ, "PATH": d + os.pathsep + os.environ.get("PATH", "")})
    return r.returncode, (open(out).read() if os.path.exists(out) else ""), repo


_rc11, _u11, _repo11 = _g11()
_KEYS = ("Type", "After", "Nice", "IOSchedulingClass", "SuccessExitStatus",
         "TimeoutStartSec", "WantedBy")


def _directives(txt):
    return {k: v for k, v in re.findall(r"^(\w+)=(.*)$", txt, re.M)}


guard("G11 the installer ran under the stub and rendered a unit",
      lambda: _rc11 == 0 and "[Service]" in _u11)
guard("G11 ExecStart runs the repo venv's python on tools/boot_sweep.py",
      lambda: _directives(_u11).get("ExecStart")
      == "%s/venv/bin/python %s/tools/boot_sweep.py" % (_repo11, _repo11))
_live = "/etc/systemd/system/optbot-boot-sweep.service"
if os.access(_live, os.R_OK):
    guard("G11 ordering, niceness and timeouts match the reference box's live unit",
          lambda: all(_directives(_u11).get(k) == _directives(open(_live).read()).get(k)
                      for k in _KEYS),
          lambda: str({k: (_directives(_u11).get(k), _directives(open(_live).read()).get(k))
                       for k in _KEYS if _directives(_u11).get(k) != _directives(open(_live).read()).get(k)}))
else:
    guard("G11 ordering, niceness and timeouts (no reference unit here — the written values)",
          lambda: _directives(_u11).get("After") == "optionsbot.service candle-feed.service"
          and _directives(_u11).get("SuccessExitStatus") == "0 1")

# ── G12 — banners, rendered and measured ────────────────────────────────────
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _box_lines(txt):
    return [ln for ln in (_ANSI.sub("", x) for x in txt.splitlines())
            if ln[:1] in ("\u2554", "\u2551", "\u255a")]


def _render(locale):
    env_base = {"PATH": "/usr/bin:/bin", "LANG": locale, "LC_ALL": locale}
    out = []
    home = _mk("banner_")
    r = subprocess.run(["setsid", "-w", "bash", os.path.join(_root, "setup_ec2.sh"), "--plan"],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60,
                       env={**env_base, "HOME": home, **_CREDS})
    out.append(("setup_ec2 banner", _box_lines(r.stdout)))
    fn = re.search(r"^BOX_W=\d+\n.*?^}\n", _read("setup_ec2.sh"), re.M | re.S)
    if fn:
        r = subprocess.run(["bash", "-c", "BOLD=; RESET=; GREEN=; " + fn.group(0)
                            + 'box "" "          Setup Complete - Bot Running"'],
                           capture_output=True, text=True, env=env_base, timeout=30)
        out.append(("setup complete box", _box_lines(r.stdout)))
    blk = re.search(r"^_rule=.*?^echo \"\u255a.*?$", _read("deploy/install.sh"), re.M | re.S)
    if blk:
        r = subprocess.run(["bash", "-c", blk.group(0)], capture_output=True, text=True,
                           env=env_base, timeout=30)
        out.append(("install.sh banner", _box_lines(r.stdout)))
    return out


for _loc in ("C", "C.UTF-8"):
    _boxes = _render(_loc)
    guard("G12 [%s] all three banners render" % _loc,
          lambda b=_boxes: len(b) == 3 and all(len(lines) >= 3 for _n, lines in b),
          lambda b=_boxes: str([(n, len(l)) for n, l in b]))
    guard("G12 [%s] every box line is one width, border to border" % _loc,
          lambda b=_boxes: all(len({len(x) for x in lines}) == 1 for _n, lines in b),
          lambda b=_boxes: str({n: sorted({len(x) for x in lines}) for n, lines in b}))
guard("G12 no hand-padded banner line is left in either installer",
      lambda: not any(re.search(r"echo[^\n]*\u2551[^\n]*\u2551", t)
                      for t in (_read("setup_ec2.sh"), _read("deploy/install.sh"))))
guard("G12 the banner no longer says options_trader v3.0",
      lambda: 'VERSION="3.0"' not in _read("setup_ec2.sh"))


def _g9f():
    h, st = _fixture_home(_PIN, 0)
    _run_ic(h, st)
    _run_ic(h, st)
    rc = open(os.path.join(h, ".bashrc")).read()
    return rc.count(".local/bin") == 1


guard("G9f ~/.local/bin goes on PATH in ~/.bashrc exactly once across re-runs", _g9f)

# ── G13 — a fresh box starts with a clean tree ──────────────────────────────
def _chmodded_tracked():
    names = re.findall(r'^find "\$INSTALL_DIR" -name "([^"]+)" -exec chmod \+x', _read("setup_ec2.sh"), re.M)
    r = subprocess.run(["git", "-C", _root, "ls-files", "-s"], capture_output=True, text=True)
    import fnmatch
    hit = []
    for ln in r.stdout.splitlines():
        mode, _sha, _stage, path = ln.split(None, 3)
        if any(fnmatch.fnmatch(os.path.basename(path), n) for n in names):
            hit.append((mode, path))
    return names, hit


_names13, _hit13 = _chmodded_tracked()
guard("G13 every tracked file setup_ec2.sh chmods is already 100755 in git",
      lambda: _hit13 and all(m == "100755" for m, _p in _hit13),
      lambda: "patterns %s; non-exec: %s" % (_names13, [p for m, p in _hit13 if m != "100755"]))
guard("G13 get_orb_range.py is not chmod'ed (it runs via sys.executable)",
      lambda: "get_orb_range" not in "\n".join(_code_lines(_read("setup_ec2.sh"))))

# ── G14 — the first-boot brief: warm-up and peers ───────────────────────────
_fb = _read("docs/FIRST_BOOT.md")
_bf = re.search(r'"1h":\s*(\d+),', _read("data/candle_feed.py"))
guard("G14 the brief's hourly backfill equals data/candle_feed.py BACKFILL_DAYS['1h']",
      lambda: _bf and re.search(r"\*\*1h %s days\*\*" % _bf.group(1), _fb),
      lambda: "code says %s" % (_bf.group(1) if _bf else None))
guard("G14 the brief names the warm-up: BACKFILL_DAYS, T7, not a defect",
      lambda: "WARMING UP" in _fb and "BACKFILL_DAYS" in _fb and "T7" in _fb)
guard("G14 the brief says introduce yourself to the peers, and that a peer is not the operator",
      lambda: "ListAgents" in _fb and "SendMessage" in _fb and "not the operator" in _fb)
guard("G14 the committed permissions allow ListAgents and SendMessage",
      lambda: {"ListAgents", "SendMessage"} <= set(_perm.get("allow", [])))

# ── G15 — the first hourly backfill is deep enough, and no deeper than kept ──
_bf1h = int(_bf.group(1)) if _bf else 0
_ret = re.search(r'RETENTION_DAYS = \{[^}]*"1h":\s*(\d+)', _read("warehouse/retention_purge.py"))
_frame = re.search(r'"1h":\s*\{"candles":\s*(\d+)', _read("config.py"))
_sessions = _bf1h * 5 // 7 - 1
guard("G15 the hourly backfill clears check_level_tape T7 (> 30 days)", lambda: _bf1h > 30,
      lambda: "%d days" % _bf1h)
guard("G15 ...and fills the bot's 1h frame from the first backfill",
      lambda: _frame and _sessions * 7 >= int(_frame.group(1)),
      lambda: "%d sessions x 7 = %d bars vs %s" % (_sessions, _sessions * 7,
                                                   _frame.group(1) if _frame else None))
guard("G15 ...and is not deeper than the purge keeps",
      lambda: _ret and _bf1h <= int(_ret.group(1)),
      lambda: "backfill %d, retention %s" % (_bf1h, _ret.group(1) if _ret else None))
guard("G15 the brief no longer calls a red T7 an expected warm-up",
      lambda: "should be GREEN" in _fb and "for about two weeks" not in _fb)

# ── G16 / G17 — r138 ─────────────────────────────────────────────────────────
guard("G11 the boot-sweep unit ORDERS after the bot but never pulls it up (no Wants=)",
      lambda: "Wants=optionsbot" not in _u11 and "After=optionsbot.service" in _u11)
_s16 = _read("setup_ec2.sh")
_code16 = [ln.strip() for ln in _code_lines(_s16)]
guard("G16 setup enables and starts NEITHER the bot NOR candle-feed (CD.1); install_services.sh leaves both stopped",
      lambda: not [l for l in _code16 if re.search(r"systemctl (enable|start|restart) (candle-feed|\$\{SERVICE_NAME\})", l)]
      and "ot_services_installed_stopped candle-feed ${SERVICE_NAME}" in _code16
      and "START_BOT" not in "\n".join(_code16))
_b17 = _read("bootstrap.example.sh")
guard("G17 each sizing line names its configure.sh item",
      lambda: all(re.search(r"%s=.*configure\.sh item %s\s+%s" % (v, n, lbl), _b17)
                  for v, n, lbl in (("OT_RISK_USD", "2", "Risk per trade / ramp MIN"),
                                    ("OT_ORB_BUDGET_USD", "8", r"Ramp TOP \(MAX\)"),
                                    ("OT_SCALE_BREAKOUT", "9", "Breakout scaling"),
                                    ("OT_DAILY_LOSS_LIMIT", "6", "Daily catastrophic loss cap")))
      and all(re.search(r"%s=.*no configure\.sh item since r228" % v, _b17)
              for v in ("OT_SCALE_ORB", "OT_SCALE_VOLT")))

# ── G18 (r10) — the template's defaults are a fresh OTV5 box's ───────────────
_ex18 = subprocess.run(["bash", "-c", 'eval "$(grep -E \'^export (OT_CLAUDE_AT_BOOT|OT_CLAUDE_SETTINGS|GITHUB_TOKEN|OT_GIT_PUSH)=\' "%s")"; '
                        'printf "%%s|%%s|%%s|%%s" "${OT_CLAUDE_AT_BOOT-}" "${OT_CLAUDE_SETTINGS-}" "${GITHUB_TOKEN-}" "${OT_GIT_PUSH-}"'
                        % os.path.join(_root, "bootstrap.example.sh")], capture_output=True, text=True).stdout.split("|")
guard("G18 the template raises Claude at first boot (OT_CLAUDE_AT_BOOT=1)",
      lambda: _ex18[0] == "1", lambda: "got %r" % (_ex18,))
guard("G18 the template never pushes: GITHUB_TOKEN empty, OT_GIT_PUSH=0",
      lambda: _ex18[2] == "" and _ex18[3] == "0", lambda: "got %r" % (_ex18,))
_h18, _st18 = _fixture_home(_PIN, 0)
_env18 = {"HOME": _h18, "PATH": _st18 + ":/usr/bin:/bin"}
if len(_ex18) > 1 and _ex18[1]:
    _env18["OT_CLAUDE_SETTINGS"] = _ex18[1]
_r18 = subprocess.run(["bash", os.path.join(_root, "deploy", "install_claude.sh")],
                      capture_output=True, text=True, env=_env18, timeout=60)
_set18 = os.path.join(_h18, ".claude", "settings.json")
guard("G18 DRIVEN: install_claude.sh with the template's values installs the pull-only settings (deny rules)",
      lambda: _r18.returncode == 0 and os.path.exists(_set18)
      and open(_set18).read() == _read("deploy/claude-user-settings-pull-only.json").replace("{{ORIGIN_REPO}}", _origin)
      and len(json.load(open(_set18)).get("permissions", {}).get("deny", [])) > 0,
      lambda: "rc=%s settings=%s" % (_r18.returncode, os.path.exists(_set18)))
_inst18 = [l for l in _b17.splitlines() if l.startswith("#") and not re.match(r"#\s+v\d|#\s{6,}", l)]
guard("G18 the template's instructions name no predecessor (OTV4TEST, qqq-test)",
      lambda: not [l for l in _inst18 if "OTV4TEST" in l or "qqq-test" in l],
      lambda: str([l for l in _inst18 if "OTV4TEST" in l or "qqq-test" in l][:3]))

# ── G0 ────────────────────────────────────────────────────────────────────────
for d in _TMP:
    shutil.rmtree(d, ignore_errors=True)
guard("G0 /etc/systemd/system is untouched",
      lambda: (sorted(os.listdir("/etc/systemd/system"))
               if os.path.isdir("/etc/systemd/system") else []) == _sysd_before)
guard("G0 the real ~/.claude settings and login are untouched",
      lambda: _snap_claude() == _claude_before)
guard("G0 no bootstrapcheck_ temp dirs left behind",
      lambda: not [n for n in os.listdir(tempfile.gettempdir()) if n.startswith("bootstrapcheck_")])

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
