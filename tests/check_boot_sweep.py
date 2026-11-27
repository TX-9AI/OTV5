#!/usr/bin/env python3
"""
tests/check_boot_sweep.py  v5.4
v5.4  2026-11-27  OTV5 r163 (SWEEP.8) — B10-B13: THE UNIT'S TIMEOUT FITS THE SWEEP, AND A KILLED SWEEP READS "DID NOT
      FINISH". The 900 s TimeoutStartSec killed the 700-886 s fleet sweeps and a killed sweep wrote nothing, so yesterday's
      SWEEP_RESULT read fresh. B10 renders the unit with sudo / systemctl stubbed and requires TimeoutStartSec >= 1800, the
      rest of the unit as before; B10b requires that nothing in the tree orders on or waits for the unit. B11 drives main()
      on a stand-in checker that reads SWEEP_RESULT while it runs: the STARTED stamp (date, ET time, commit, pid) is there
      BEFORE the first checker, and SWEEP_PREV holds the previous finished run. B12 a real kill: a child sweep on a checker
      that sleeps gets SIGTERM to its whole process group (what systemd sends at the timeout) and the real `--show` then
      reads "DID NOT FINISH (started HH:MM ...)"; while it runs, "RUNNING". B13 the reader on the old format (no date /
      commit) and the new, and the next finished run diffs against SWEEP_PREV, not the killed stamp. Born red on r162 at
      B10 B11 B12 B13.
v5.3  2026-11-15  OTV5 r123 (HYG.27) — B3/B3b RE-POINTED: OT_RESTING_DB is no longer a scratch store - r118 deleted the
      resting-offer store (execution/resting_orders.py), its only reader; B3 no longer requires it and B3b no longer
      expects it in run_one's env. Every other store unchanged.
v5.2  2026-10-31  OTV5 r68 (CFG.5) — B3/B3b RE-POINTED (section 38.4): OT_RESTING_STOP_STATE is no longer a scratch store - the
      resting stop is deleted (the operator, 2026-10-31: "Resting stop was a study. It failed."); B3 no longer requires it
      and B3b no longer expects it in run_one's env. Every other store unchanged.
v5.1  2026-10-25  (HYG.14) — B9 DRIVES THE REAL run_one ON A CHECKER THAT LEAKS A tempfile.mkdtemp() DIR and records its
      path: the dir must sit under that run's bootsweep- scratch (not at /tmp's top level) and be GONE when run_one
      returns. ~110 checkers leak such dirs into /tmp (tmpfs; 2,225 dirs / 814 MB on control). Born red on ffe10bf at B9.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.8  2026-10-25  OTV5 r4 (GATE.6) — B3/B3b REQUIRE THE HEARTBEAT FILE IN SCRATCH TOO: tools/emergency_watchdog.py reads its
      mtime as the bot's liveness and a checker driving position_manager's mark fallback touched the live one. Born red on boot_sweep v1.8.
v1.7  2026-10-20  OTV4TEST r307 (GATE.4) — B3/B3b REQUIRE THE PLAN STATES FILE IN SCRATCH TOO (check_foreign_symbol_board F7
      read the live data/plan_states.json at the 10-20 08:00 sweep).
v1.6  2026-10-18  OTV4TEST r292 (GATE.1) — B3/B3b REQUIRE THE FEED STORE, THE RESTING-STOP STATE FILE AND THE WAREHOUSE
      STATE DIR IN SCRATCH TOO (audit 10-18 B4: 42 checkers read the live 2.5 GB feed_store.db under the sweep).
v1.5  2026-10-15  OTV4TEST r287 (CFDIR.1) — B3/B3b REQUIRE THE COUNTERFACTUAL LOGS IN SCRATCH TOO.
v1.4  2026-10-06  OTV4TEST r257 — B8/B8b: A SWEEP NEVER STARTS INSIDE ANOTHER. B1b's "real subset" drives
      `--only check_boot_sweep`, which recursed without bound (SPX-TEST 10-06: past B1b's 180 s timeout).
      B8 DRIVES the tool with OT_SWEEP_NESTED=1 and requires the refusal (exit 0, "NESTED", no result file,
      seconds not minutes); B8b requires the real run_one to hand every checker OT_SWEEP_NESTED=1.
v1.3  2026-10-03  OTV4TEST r194 (BOX.16) — B3/B3b REQUIRE THE LOG IN SCRATCH TOO, and B3c drives it: a fresh
      interpreter imports main with OT_LOG_FILE set and the only file handler is the scratch log.
v1.2  2026-09-25  OTV4TEST r144 — B3/B3b REQUIRE THE SIGNAL JOURNAL IN SCRATCH TOO
      (OT_SIGNAL_JOURNAL_DIR under the same bootsweep- mkdtemp). The sweep wrote
      ~126 retest_check fixtures a day into the live journal; on SOFI/AAL they
      reached sym=QQQ in the warehouse. Born red at 247facf.
v1.1  2026-09-23  OTV4TEST r109 — B3 NAMES THE THIRD STORE, AND B3b DRIVES IT.
      The live `resting_orders.db` held 91 checker fixture rows because
      run_one isolated only the trades and derived stores. B3b calls the REAL
      run_one with the subprocess intercepted and asserts every store it hands
      a checker lives inside that run's own scratch directory — born red at
      2c17b2e on OT_RESTING_DB.
v1.0  2026-09-21  OTV4TEST r86 — born RED at 4b1e9a2 (the tool does not exist).

🔴 WHY THIS TOOL EXISTS, MEASURED. Landing a ONE-LINE change cost **297
checker invocations** — about 11 minutes — and the operator called it: *"that
is entirely ludicrous… The 30-minute per commit cycle is choking our commit
rate for needed changes."* His own fix was better than the one proposed to
him: *"You have an AWS auto boot daily at 0800. Why not run the full set then
& do the abbreviated when we're actively trying to land."*

⚠️ THE TOOL IS INFRASTRUCTURE AND §29 APPLIES: nothing here may become
load-bearing for trading. These checks exist to keep it that way.

  B1  it ALWAYS exits 0 — a red finding is not an infrastructure fault
  B2  it SKIPS itself when memory is tight rather than racing the live bot
  B3  every checker runs against SCRATCH stores, never the live ones
  B4  the interpreter is PINNED, not inherited (ENV.1)
  B5  the result is a DIFF (new/fixed), not a bare count — 11 standing reds
      mean "134 of 145" tells nobody anything

Run:  python3 tests/check_boot_sweep.py
"""
from __future__ import annotations
import ast, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])

_p = os.path.join(_root, "tools", "boot_sweep.py")
check("B0 tools/boot_sweep.py exists", os.path.exists(_p),
      "r86 has not landed in this tree")
if not os.path.exists(_p):
    print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
    sys.exit(1)

_src = open(_p, encoding="utf-8").read()
_tree = ast.parse(_src)

# ── B1 — every return from main() is 0, and nothing raises SystemExit(n!=0) ──
# ⚠️ A non-zero exit marks the systemd unit FAILED and puts a red in
# `systemctl status` for a finding that is not an infrastructure fault — the
# operator would learn to ignore a red that means "a checker is red", which is
# §36's named failure one level up.
_bad = []
for node in ast.walk(_tree):
    if isinstance(node, ast.FunctionDef) and node.name == "main":
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return) and sub.value is not None:
                if not (isinstance(sub.value, ast.Constant) and sub.value.value == 0):
                    _bad.append(sub.lineno)
check("B1 main() returns 0 on EVERY path", not _bad,
      f"non-zero returns at lines {_bad}")

# ── B1b — DRIVEN, BECAUSE B1 ALONE WAS NOT ENOUGH AND THE SMOKE TEST PROVED IT.
# 🔴 While r86 was being built, a NameError in the --only wiring made the tool
# EXIT 1 — and B1 still read GREEN, because it walks the AST for `return`
# statements and an exception bypasses every one of them. §21 exactly: a test
# reading source text proves nothing about runtime. A non-zero exit marks the
# systemd unit FAILED, which is a red in `systemctl status` for something that
# is not an infrastructure fault.
import subprocess as _sp
_py = os.path.join(_root, "venv", "bin", "python")
_py = _py if os.path.exists(_py) else sys.executable
_runs = {
    "dry-run":       [_py, _p, "--dry-run"],
    "real subset":   [_py, _p, "--only", "check_boot_sweep"],
    "unknown name":  [_py, _p, "--only", "check_does_not_exist_anywhere"],
}
_nonzero = {}
for _label, _cmd in _runs.items():
    try:
        _r = _sp.run(_cmd, capture_output=True, timeout=180,
                     cwd=_root, env={**os.environ,
                                     "OT_TRADES_DB": os.path.join(tempfile.mkdtemp(), "t.db"),
                                     "OT_DERIVED_DB": os.path.join(tempfile.mkdtemp(), "d.db"),
                                     # 🔴 AND THE RESULT ARTIFACT TOO. Without
                                     # this, driving the tool here OVERWRITES
                                     # data/SWEEP_RESULT and the 08:00 agent
                                     # reads a test fixture instead of the
                                     # overnight sweep. Found by running
                                     # --show right after this checker.
                                     "OT_SWEEP_RESULT_DIR": tempfile.mkdtemp()})
        if _r.returncode != 0:
            _nonzero[_label] = _r.returncode
    except Exception as _e:                                     # noqa: BLE001
        _nonzero[_label] = f"raised {type(_e).__name__}"
check("B1b DRIVEN: the tool exits 0 on every invocation, not just every return",
      not _nonzero,
      f"non-zero exits: {_nonzero} — an exception bypasses every return B1 checks")

check("B1c the __main__ guard catches a CRASH and still exits 0",
      "except BaseException" in _src and "SystemExit(0)" in _src,
      "nothing may put a red in systemctl status for a checker finding")

# ── B2 — the memory guard is REAL, not decoration ──
# MEASURED on this box before the tool was written: with the sweep, the bot and
# the feed all running, MemAvailable floored at 298 MB of 908 and swap rose
# 176 -> 482 MB. Safe, but not by so much that the guard is optional.
check("B2 it reads MemAvailable and has a floor to skip under",
      ("MemAvailable" in _src) and ("MIN_FREE_MB" in _src),
      "a sweep that races the live bot for memory is load-bearing (§29)")

# ── B3 — THE STORES. r13: a fixture once landed as a live open position, and
# the operator's standing rule is that a check once purged live data.
check("B3 every checker runs against SCRATCH stores",
      ("OT_TRADES_DB" in _src) and ("OT_DERIVED_DB" in _src)
      and ("OT_SIGNAL_JOURNAL_DIR" in _src)
      and ("OT_LOG_FILE" in _src) and ("OT_COUNTERFACTUAL_DIR" in _src)
      and ("OT_FEED_DB" in _src)                                              # r292 (GATE.1)
      and ("OT_WAREHOUSE_STATE" in _src) and ("OT_PLAN_STATES_FILE" in _src)     # r307 (GATE.4)
      and ("OT_HEARTBEAT_FILE" in _src)                                          # OTV5 r4 (GATE.6)
      and ("mkdtemp" in _src or "TemporaryDirectory" in _src),
      "checkers must never see the live trades/derived stores")


# ── B3b — DRIVEN (§21): the real run_one, its subprocess intercepted, so no
# checker runs and nothing is written — only the environment it WOULD hand a
# checker is inspected. Every store must resolve inside run_one's own mkdtemp.
_B3B_ENV = {}


def _b3b():
    import importlib.util as _ilu
    import subprocess as _spm
    _s = _ilu.spec_from_file_location("_bs3b", _p)
    _m = _ilu.module_from_spec(_s)
    _s.loader.exec_module(_m)
    seen = {}

    class _R:
        returncode = 0

    def _fake_run(cmd, **kw):
        seen["env"] = dict(kw.get("env") or {})
        _B3B_ENV.update(seen["env"])
        return _R()
    _orig = _m.subprocess.run
    _m.subprocess.run = _fake_run
    try:
        _m.run_one("check_nothing_real.py")
    finally:
        _m.subprocess.run = _orig
    env = seen.get("env") or {}
    want = ("OT_TRADES_DB", "OT_DERIVED_DB", "OT_SIGNAL_JOURNAL_DIR", "OT_LOG_FILE",
            "OT_COUNTERFACTUAL_DIR", "OT_FEED_DB", "OT_WAREHOUSE_STATE",   # r292 (r68: OT_RESTING_STOP_STATE gone)
            "OT_PLAN_STATES_FILE",                                                   # r307 (GATE.4)
            "OT_HEARTBEAT_FILE")                                                     # OTV5 r4 (GATE.6)
    paths = {k: env.get(k) for k in want}
    parents = {os.path.dirname(v) for v in paths.values() if v}
    ok = (all(paths.values()) and len(parents) == 1
          and os.path.basename(next(iter(parents))).startswith("bootsweep-"))
    return ok, paths


try:
    _ok3b, _paths3b = _b3b()
except Exception as _e3b:                                       # noqa: BLE001
    _ok3b, _paths3b = False, f"{type(_e3b).__name__}: {_e3b}"
check("B3b DRIVEN: run_one hands a checker ONLY scratch stores (trades, derived, journal, log, cf, feed, warehouse-state, plan-states, heartbeat)",
      _ok3b, str(_paths3b))


# ── B3c (r194, BOX.16) — THE LOG HANDLER ITSELF, IN A FRESH INTERPRETER ──────
# main attaches a RotatingFileHandler to config.LOG_FILE at IMPORT. With
# OT_LOG_FILE set, that handler must open the scratch file and the box's real
# bot.log must not grow; with it unset, config names the path it always did.
def _b3c():
    import glob as _g
    import subprocess as _sp
    import tempfile as _tf
    d = _tf.mkdtemp(prefix="check_boot_sweep_log_")
    sps = _g.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages"))
    code = ("import sys; sys.path[1:1] = %r; sys.path.insert(0, %r); import logging, config, main; "
            "hs = [getattr(h, 'baseFilename', '') for h in logging.getLogger().handlers]; "
            "print('LOGFILES=' + '|'.join(x for x in hs if x) + ' CFG=' + config.LOG_FILE)" % (sps, _root))
    env = dict(os.environ)
    for k, f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived_store.db"),
                 ("OT_SIGNAL_JOURNAL_DIR", "signal_journal")):
        env[k] = os.path.join(d, f)
    env.setdefault("OT_INSTRUMENT", "QQQ")
    scratch_log = os.path.join(d, "bot.log")
    env["OT_LOG_FILE"] = scratch_log
    r = _sp.run([sys.executable, "-c", code], cwd=_root, env=env, capture_output=True, text=True, timeout=120)
    line = ([ln for ln in r.stdout.splitlines() if ln.startswith("LOGFILES=")] or [r.stderr.strip()[-200:]])[-1]
    env2 = dict(env); env2.pop("OT_LOG_FILE", None)
    r2 = _sp.run([sys.executable, "-c",
                  "import sys; sys.path.insert(0, %r); import config; print('CFG=' + config.LOG_FILE)" % _root],
                 cwd=_root, env=env2, capture_output=True, text=True, timeout=60)
    unset = (r2.stdout.strip().splitlines() or [r2.stderr.strip()[-120:]])[-1]
    live = os.path.expanduser("~/options-trader/bot.log")
    ok = (("LOGFILES=" + scratch_log + " CFG=" + scratch_log) == line and unset == "CFG=" + live)
    return ok, "set: %s | unset: %s" % (line[-150:], unset)


try:
    _ok3c, _d3c = _b3c()
except Exception as _e3c:                                       # noqa: BLE001
    _ok3c, _d3c = False, f"{type(_e3c).__name__}: {_e3c}"
check("B3c DRIVEN: with OT_LOG_FILE set, importing main opens ONLY the scratch log; unset, config names the live one",
      _ok3c, _d3c)

# ── B4 — ENV.1. System python3 here is 3.14 with NO pandas, and a systemd unit
# reads no profile, so PATH cannot be relied on at all. An inherited
# interpreter turns every pandas checker red for a reason unrelated to its
# content — a verification going red on ENVIRONMENT rather than CONTENT.
check("B4 the interpreter is PINNED to the venv, not inherited",
      'venv' in _src and '"python3"' not in _src.replace('python3 <p>', ''),
      "ENV.1 — a unit reads no profile; PATH is not a source of truth here")

# ── B5 — the signal is the DIFF. This tree carries 11 standing reds.
check("B5 the result is reported as a DIFF against the previous run",
      all(k in _src for k in ("SWEEP_PREV", "new", "fixed")),
      "'134 of 145' is a number, not an answer — what matters is a TWELFTH red")

# ── B6 — it must not abort early. Operator: *"Flag it, finish the sweep, brief
# it with the proposed fix and rationale why the fix works."*
check("B6 a red does not abort the sweep",
      "break" not in _src.split("def main")[0].split("for ")[-1][:400]
      or "continue" in _src,
      "stopping at the first red hides every red behind it")

# ── B7 — THE RESULT ARTIFACT IS SCRATCHABLE, AND THIS CHECKER PROVES IT BY
# READING WHAT THE LIVE ONE SAYS AFTER B1b HAS RUN. Without the override,
# B1b's three driven invocations overwrite data/SWEEP_RESULT and the 08:00
# agent's first act — `boot_sweep.py --show` — returns a test fixture.
check("B7 the result path is overridable so a check cannot clobber it",
      "OT_SWEEP_RESULT_DIR" in _src,
      "a check that writes where production reads breaks production (r13)")

# ── B8 / B8b — r257: A SWEEP NEVER STARTS INSIDE ANOTHER (DRIVEN, §21). A name that matches no
# checker keeps the UNFIXED tool from recursing here: it reports ERROR and exits 0 without NESTED.
import time as _t8
_rd8 = tempfile.mkdtemp()
_t0 = _t8.time()
try:
    _r8 = _sp.run([_py, _p, "--only", "check_does_not_exist_anywhere"], capture_output=True, text=True,
                  timeout=60, cwd=_root, env={**os.environ, "OT_SWEEP_NESTED": "1",
                                              "OT_SWEEP_RESULT_DIR": _rd8})
    _out8, _rc8 = (_r8.stdout or "") + (_r8.stderr or ""), _r8.returncode
except Exception as _e8:                                        # noqa: BLE001
    _out8, _rc8 = f"raised {type(_e8).__name__}: {_e8}", None
_dt8 = _t8.time() - _t0
check("B8 DRIVEN: under OT_SWEEP_NESTED=1 the tool refuses - exit 0, says NESTED, writes no result",
      _rc8 == 0 and "NESTED" in _out8 and not os.listdir(_rd8) and _dt8 < 30,
      f"rc={_rc8} secs={_dt8:.1f} result_dir={os.listdir(_rd8)} out={_out8.strip()[:160]!r}")
check("B8b DRIVEN: run_one hands every checker OT_SWEEP_NESTED=1",
      _B3B_ENV.get("OT_SWEEP_NESTED") == "1", f"OT_SWEEP_NESTED={_B3B_ENV.get('OT_SWEEP_NESTED')!r}")

# ── B9 (v5.1, HYG.14) — a checker's mkdtemp dies with its run ──────────────
def _b9():
    import importlib.util as _ilu
    import shutil as _sh
    _s = _ilu.spec_from_file_location("_bs9", _p)
    _m = _ilu.module_from_spec(_s)
    _s.loader.exec_module(_m)
    tdir = tempfile.mkdtemp(prefix="chk_bs9_")
    rec = os.path.join(tdir, "where.txt")
    try:
        with open(os.path.join(tdir, "check_leaks_tmp.py"), "w") as fh:
            fh.write("import tempfile\nd = tempfile.mkdtemp(prefix='leak9_')\n"
                     "open(%r, 'w').write(d)\n" % rec)
        _m.TESTS, _m.PY = tdir, sys.executable
        ok_run = _m.run_one("check_leaks_tmp.py")
        where = open(rec).read().strip() if os.path.exists(rec) else ""
        survived = bool(where) and os.path.exists(where)
        if survived and where.startswith("/tmp/leak9_"):
            _sh.rmtree(where, ignore_errors=True)        # a pristine tool leaks it; do not leave it
        parent = os.path.basename(os.path.dirname(os.path.dirname(where))) if where else ""
        return (ok_run and bool(where) and parent.startswith("bootsweep-") and not survived), \
            f"ran={ok_run} path={where!r} survived={survived}"
    finally:
        _sh.rmtree(tdir, ignore_errors=True)


try:
    _ok9, _d9 = _b9()
except Exception as _e9:                                        # noqa: BLE001
    _ok9, _d9 = False, f"{type(_e9).__name__}: {_e9}"
check("B9 DRIVEN: a checker's tempfile.mkdtemp() lands under its run's bootsweep- scratch and is GONE after run_one",
      _ok9, _d9)

# ── B10 / B10b (v5.4, SWEEP.8) — the unit's timeout fits the sweep; nothing waits on it ────────────────────────────
import io as _io
import json as _json
from contextlib import redirect_stdout as _redir
import re as _re
import shutil as _shutil
import signal as _signal
import time as _time


def _b10():
    d = tempfile.mkdtemp(prefix="chk_bs10_")
    try:
        repo = os.path.join(d, "repo")
        os.makedirs(os.path.join(repo, "deploy"))
        os.makedirs(os.path.join(repo, "venv", "bin"))
        _shutil.copy(os.path.join(_root, "deploy", "install_boot_sweep.sh"), os.path.join(repo, "deploy"))
        py = os.path.join(repo, "venv", "bin", "python")
        open(py, "w").write("#!/bin/sh\nexit 0\n")
        os.chmod(py, 0o755)
        unit, calls = os.path.join(d, "unit.txt"), os.path.join(d, "calls.txt")
        for name, body in (("sudo", '#!/bin/sh\ncase "$1" in\n  tee) cat > "%s"; exit 0 ;;\n'
                                    '  systemctl) echo "$*" >> "%s"; exit 0 ;;\n  *) exit 90 ;;\nesac\n' % (unit, calls)),
                           ("systemctl", "#!/bin/sh\nexit 0\n")):
            open(os.path.join(d, name), "w").write(body)
            os.chmod(os.path.join(d, name), 0o755)
        r = _sp.run(["bash", os.path.join(repo, "deploy", "install_boot_sweep.sh")], capture_output=True, text=True,
                    timeout=60, env={**os.environ, "PATH": d + os.pathsep + os.environ.get("PATH", "")})
        txt = open(unit).read() if os.path.exists(unit) else ""
        dirs = dict(_re.findall(r"^(\w+)=(.*)$", txt, _re.M))
        return r.returncode, dirs, (open(calls).read() if os.path.exists(calls) else ""), repo
    finally:
        _shutil.rmtree(d, ignore_errors=True)


try:
    _rc10, _u10, _calls10, _repo10 = _b10()
except Exception as _e10:                                       # noqa: BLE001
    _rc10, _u10, _calls10, _repo10 = f"raised {type(_e10).__name__}: {_e10}", {}, "", ""
_tmo10 = int(_u10.get("TimeoutStartSec", "0") or 0) if str(_u10.get("TimeoutStartSec", "0")).isdigit() else -1
check("B10 the rendered unit's TimeoutStartSec is >= 1800 s (fleet sweeps take 700-886 s; 900 killed them), the rest unchanged",
      _rc10 == 0 and _tmo10 >= 1800
      and _u10.get("Type") == "oneshot" and _u10.get("After") == "optionsbot.service candle-feed.service"
      and _u10.get("ExecStart") == "%s/venv/bin/python %s/tools/boot_sweep.py" % (_repo10, _repo10)
      and _u10.get("Nice") == "19" and _u10.get("IOSchedulingClass") == "idle" and _u10.get("SuccessExitStatus") == "0 1"
      and _u10.get("WantedBy") == "multi-user.target" and "Wants" not in _u10 and "Before" not in _u10
      and "daemon-reload" in _calls10 and "enable optbot-boot-sweep.service" in _calls10,
      f"rc={_rc10} TimeoutStartSec={_u10.get('TimeoutStartSec')} unit={ {k: _u10.get(k) for k in ('Type', 'After', 'Nice', 'WantedBy', 'Before', 'Wants')} }")


def _b10b():
    hits = []
    for base, _dirs, files in os.walk(_root):
        if any(x in base for x in (os.sep + ".git", os.sep + "venv", "__pycache__", os.sep + "tests")):
            continue
        for f in files:
            if not (f.endswith((".sh", ".service", ".timer", ".target", ".py")) or f == "setup_ec2.sh"):
                continue
            try:
                txt = open(os.path.join(base, f), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for ln in txt.splitlines():
                if _re.match(r"^\s*(After|Before|Requires|Wants|BindsTo|Requisite|PartOf)=.*optbot-boot-sweep", ln):
                    hits.append(f"{os.path.relpath(os.path.join(base, f), _root)}: {ln.strip()}")
                if _re.search(r"systemctl\s+(start|restart)\s+optbot-boot-sweep", ln) and "--no-block" not in ln:
                    hits.append(f"{os.path.relpath(os.path.join(base, f), _root)}: {ln.strip()}")
    return hits


_hits10b = _b10b()
check("B10b nothing in the tree orders on, waits for or synchronously starts optbot-boot-sweep.service",
      not _hits10b, "; ".join(_hits10b[:5]))


# ── B11 — the STARTED stamp is written FIRST, and SWEEP_PREV keeps the last finished run ─────────────────────────────
def _load_tool(tag):
    import importlib.util as _ilu
    _s = _ilu.spec_from_file_location(tag, _p)
    _m = _ilu.module_from_spec(_s)
    _s.loader.exec_module(_m)
    return _m


def _b11():
    m = _load_tool("_bs11")
    tdir, rdir = tempfile.mkdtemp(prefix="chk_bs11_t_"), tempfile.mkdtemp(prefix="chk_bs11_r_")
    try:
        seen = os.path.join(tdir, "seen.json")
        with open(os.path.join(tdir, "check_aaa_reads_result.py"), "w") as fh:
            fh.write("import shutil\nshutil.copy(%r, %r)\n" % (os.path.join(rdir, "SWEEP_RESULT"), seen))
        with open(os.path.join(tdir, "check_bbb_red.py"), "w") as fh:
            fh.write("raise SystemExit(1)\n")
        old = {"state": "RAN", "at": 1700000000.0, "secs": 1.0, "total": 2, "failed": ["check_bbb_red.py"]}
        open(os.path.join(rdir, "SWEEP_RESULT"), "w").write(_json.dumps(old))
        m.TESTS, m.PY = tdir, sys.executable
        m.RESULT, m.PREV = os.path.join(rdir, "SWEEP_RESULT"), os.path.join(rdir, "SWEEP_PREV")
        with _redir(_io.StringIO()):
            rc = m.main([])
        st = _json.load(open(seen)) if os.path.exists(seen) else {}
        fin = _json.load(open(m.RESULT))
        prev = _json.load(open(m.PREV)) if os.path.exists(m.PREV) else {}
        ok = (rc == 0 and st.get("state") == "STARTED" and st.get("done") == 0 and st.get("pid")
              and _re.match(r"^\d{4}-\d{2}-\d{2}$", st.get("date") or "") and _re.match(r"^\d{2}:\d{2}:\d{2}", st.get("time") or "")
              and st.get("commit") not in (None, "")
              and prev == old and fin.get("state") == "RAN" and fin.get("total") == 2
              and fin.get("failed") == ["check_bbb_red.py"] and fin.get("diff", {}).get("baseline") is True
              and fin.get("commit") == st.get("commit") and fin.get("date") == st.get("date"))
        return ok, f"stamp seen by checker 1: {st} | final {fin.get('state')} diff={fin.get('diff')} | prev==old {prev == old}"
    finally:
        _shutil.rmtree(tdir, ignore_errors=True)
        _shutil.rmtree(rdir, ignore_errors=True)


try:
    _ok11, _d11 = _b11()
except Exception as _e11:                                       # noqa: BLE001
    _ok11, _d11 = False, f"{type(_e11).__name__}: {_e11}"
check("B11 DRIVEN: SWEEP_RESULT holds a STARTED stamp (date, ET time, commit, pid) BEFORE the first checker runs; "
      "SWEEP_PREV holds the previous finished run", _ok11, _d11[:400])


# ── B12 — a REAL kill (SIGTERM to the process group, what systemd sends at TimeoutStartSec) reads "DID NOT FINISH" ──
def _b12():
    tdir, rdir = tempfile.mkdtemp(prefix="chk_bs12_t_"), tempfile.mkdtemp(prefix="chk_bs12_r_")
    proc = None
    try:
        open(os.path.join(tdir, "check_aaa_quick.py"), "w").write("pass\n")
        open(os.path.join(tdir, "check_zzz_sleeps.py"), "w").write("import time\ntime.sleep(120)\n")
        old = {"state": "RAN", "at": 1700000000.0, "secs": 1.0, "total": 2, "failed": []}
        open(os.path.join(rdir, "SWEEP_RESULT"), "w").write(_json.dumps(old))
        drv = os.path.join(tdir, "drive_boot_sweep.py")     # the name carries boot_sweep, as the unit's process does
        open(drv, "w").write(
            "import importlib.util, sys\n"
            "s = importlib.util.spec_from_file_location('boot_sweep_under_test', %r)\n"
            "m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
            "m.TESTS, m.PY = %r, sys.executable\n"
            "m.RESULT, m.PREV = %r, %r\n"
            "raise SystemExit(m.main([]))\n" % (_p, tdir, os.path.join(rdir, "SWEEP_RESULT"), os.path.join(rdir, "SWEEP_PREV")))
        env = {k: v for k, v in os.environ.items() if k != "OT_SWEEP_NESTED"}
        proc = _sp.Popen([sys.executable, drv], cwd=_root, env=env, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                         start_new_session=True)
        st, t0 = {}, _time.time()
        while _time.time() - t0 < 60:
            try:
                st = _json.load(open(os.path.join(rdir, "SWEEP_RESULT")))
            except (OSError, ValueError):
                st = {}
            if st.get("state") == "STARTED" and st.get("done") == 1:
                break
            _time.sleep(0.2)
        show = lambda: _sp.run([_py, _p, "--show"], capture_output=True, text=True, timeout=60, cwd=_root,  # noqa: E731
                               env={**env, "OT_SWEEP_RESULT_DIR": rdir}).stdout
        running = show()
        os.killpg(proc.pid, _signal.SIGTERM)
        proc.wait(timeout=30)
        try:
            os.killpg(proc.pid, _signal.SIGKILL)               # the sleeping checker, if SIGTERM left it
        except OSError:
            pass
        after = show()
        first = (after.splitlines() or [""])[0]
        hhmm = (st.get("time") or "??:??")[:5]
        prev = _json.load(open(os.path.join(rdir, "SWEEP_PREV"))) if os.path.exists(os.path.join(rdir, "SWEEP_PREV")) else {}
        ok = (st.get("state") == "STARTED" and running.startswith("boot_sweep: RUNNING")
              and first.startswith("boot_sweep: DID NOT FINISH (started ") and f" {hhmm}" in first
              and "reached 1/2 checkers, last check_aaa_quick.py" in first and prev == old)
        return ok, f"running={running.splitlines()[:1]} after={first[:220]!r} prev==old {prev == old}"
    finally:
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, _signal.SIGKILL)
            except OSError:
                pass
        _shutil.rmtree(tdir, ignore_errors=True)
        _shutil.rmtree(rdir, ignore_errors=True)


try:
    _ok12, _d12 = _b12()
except Exception as _e12:                                       # noqa: BLE001
    _ok12, _d12 = False, f"{type(_e12).__name__}: {_e12}"
check("B12 DRIVEN: a sweep killed mid-run (SIGTERM to its process group) reads 'DID NOT FINISH (started HH:MM ...)' "
      "in the real --show, 'RUNNING' while alive, and SWEEP_PREV keeps the last finished run", _ok12, _d12)


# ── B13 — the reader on old and new formats; the next finished run diffs against SWEEP_PREV, not the killed stamp ──
def _b13():
    m = _load_tool("_bs13")
    notes, ok = [], True
    old_ran = {"state": "RAN", "at": 1795700000.0, "secs": 812.3, "total": 150, "failed": ["check_a.py"],
               "diff": {"new": ["check_a.py"], "fixed": [], "baseline": True}}
    line = m.describe(old_ran)
    ok &= line.startswith("boot_sweep: RAN 2026-11-") and "149/150 pass in 812.3s; 1 red; NEW: check_a.py" in line
    notes.append(line)
    other = _sp.Popen(["sleep", "30"])                          # a live pid that is not a boot_sweep (a reused pid)
    try:
        dead = {"state": "STARTED", "at": 1795700000.0, "date": "2026-11-30", "time": "09:15:02 ET", "commit": "abc1234",
                "pid": other.pid, "done": 131, "total": 150, "last": "check_q.py", "failed": []}
        line = m.describe(dead)
    finally:
        other.kill()
        other.wait()
    ok &= line.startswith("boot_sweep: DID NOT FINISH (started 2026-11-30 09:15:02 ET at abc1234; reached 131/150")
    notes.append(line[:90])
    ok &= m.describe({}) == "boot_sweep: no sweep result recorded"
    ok &= m.describe({"state": "SKIPPED", "at": 1795700000.0, "why": "only 90MB"}).startswith("boot_sweep: SKIPPED 2026-11-")
    tdir, rdir = tempfile.mkdtemp(prefix="chk_bs13_t_"), tempfile.mkdtemp(prefix="chk_bs13_r_")
    try:
        open(os.path.join(tdir, "check_a.py"), "w").write("pass\n")
        open(os.path.join(tdir, "check_b.py"), "w").write("raise SystemExit(1)\n")
        prev = {"state": "RAN", "at": 1795600000.0, "secs": 1.0, "total": 2, "failed": ["check_a.py"]}
        open(os.path.join(rdir, "SWEEP_RESULT"), "w").write(_json.dumps({**dead, "pid": 0}))
        open(os.path.join(rdir, "SWEEP_PREV"), "w").write(_json.dumps(prev))
        m.TESTS, m.PY = tdir, sys.executable
        m.RESULT, m.PREV = os.path.join(rdir, "SWEEP_RESULT"), os.path.join(rdir, "SWEEP_PREV")
        with _redir(_io.StringIO()):
            m.main([])
        fin = _json.load(open(m.RESULT))
        kept = _json.load(open(m.PREV))
        d = fin.get("diff") or {}
        ok &= (fin.get("state") == "RAN" and d.get("baseline") is True and d.get("new") == ["check_b.py"]
               and d.get("fixed") == ["check_a.py"] and kept == prev
               and (fin.get("previous_unfinished") or {}).get("done") == 131)
        line = m.describe(fin)
        ok &= "(the run before DID NOT FINISH: started 2026-11-30 09:15:02 ET, reached 131/150)" in line
        notes.append(line[-90:])
    finally:
        _shutil.rmtree(tdir, ignore_errors=True)
        _shutil.rmtree(rdir, ignore_errors=True)
    return bool(ok), " | ".join(notes)


try:
    _ok13, _d13 = _b13()
except Exception as _e13:                                       # noqa: BLE001
    _ok13, _d13 = False, f"{type(_e13).__name__}: {_e13}"
check("B13 the reader names old-format (no date / commit) and new results, and a finished run after a killed one diffs "
      "against SWEEP_PREV and records previous_unfinished", _ok13, _d13[:400])

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
