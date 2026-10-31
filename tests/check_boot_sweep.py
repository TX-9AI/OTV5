#!/usr/bin/env python3
"""
tests/check_boot_sweep.py  v5.2
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
      and ("OT_RESTING_DB" in _src) and ("OT_SIGNAL_JOURNAL_DIR" in _src)
      and ("OT_LOG_FILE" in _src) and ("OT_COUNTERFACTUAL_DIR" in _src)
      and ("OT_FEED_DB" in _src)                                              # r292 (GATE.1)
      and ("OT_WAREHOUSE_STATE" in _src) and ("OT_PLAN_STATES_FILE" in _src)     # r307 (GATE.4)
      and ("OT_HEARTBEAT_FILE" in _src)                                          # OTV5 r4 (GATE.6)
      and ("mkdtemp" in _src or "TemporaryDirectory" in _src),
      "checkers must never see the live trades/derived/resting stores")


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
    want = ("OT_TRADES_DB", "OT_DERIVED_DB", "OT_RESTING_DB", "OT_SIGNAL_JOURNAL_DIR", "OT_LOG_FILE",
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
check("B3b DRIVEN: run_one hands a checker ONLY scratch stores (trades, derived, resting, journal, log, cf, feed, rest-state, warehouse-state, plan-states, heartbeat)",
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
                 ("OT_RESTING_DB", "resting_orders.db"), ("OT_SIGNAL_JOURNAL_DIR", "signal_journal")):
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

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
