"""tests/check_data_capture.py — v5.3
v5.3  2026-10-30  OTV5 r57 (TCS.LOG1) — D4 RE-POINTED, NOT DROPPED (section 38.4): TCS joined configure.sh's menu as item 16,
      so Done is 17 and the prompt names 1-17. Data capture stays item 14; properties unchanged.
v5.2  2026-10-27  OTV5 r46 (PARC.1) — D4 RE-POINTED, NOT DROPPED (section 38.4): PARC joined configure.sh's menu as item 15,
      so Done is 16 and the prompt names 1-16. Data capture stays item 14; properties unchanged.
v5.1  2026-10-27  OTV5 r41 (GATE.8) — D5c STUBS THE BOT UNIT, AND D5d PINS CD.1'S ORDER. D5c expected the OHLC file to be the
      fallback with OT_INSTRUMENT unset, but CD.1 (own_symbol reads the bot unit's instrument before any file) made the
      LIVE box's unit answer instead, so D5c passed only on QQQ and was a standing red in every other box's boot sweep
      (SOFI and AMD read their own symbols, 2026-10-26). D5c now stubs the unit away; D5d: a unit symbol wins over a
      stale file. Test-only; own_symbol unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...

v1.10 2026-10-24 — CD.1. D7 RE-POINTED (section 38.4): an install always applies STANDALONE through
      deploy/install_services.sh ot_capture_install (the bootstrap's managed is recorded, applied by configure.sh);
      still no hard-coded s3-push mask in setup_ec2.sh.
v1.9  2026-10-13 — OTV4TEST r279 (mirror of otv4 r416). D6b RE-POINTED, NOT DROPPED (section 38.4): the purge's
      DELETE moved into `_delete_batched`, so D6b finds that call after `_safe_cutoff` (segment 1500 -> 2500).
v1.8  2026-10-10 — OTV4TEST r266 (STOP.1). D4 RE-POINTED, NOT DROPPED (section 38.4): the resting stop joined the
      menu as item 13, so Data capture is item 14 and Done 15. Properties unchanged.

v1.7  2026-10-10 — OTV4TEST r265 (BRK.8/BRK.9). D4 RE-POINTED, NOT DROPPED (section 38.4): Breakout's entry
      end (11) and no-progress exit (12) joined the menu, so Data capture is item 13 and Done 14. Properties unchanged.

v1.6  2026-10-05 — OTV4TEST r253 (RUNW.2). D4 RE-POINTED, NOT DROPPED (section 38.4): Runaway's entry end
      joined the menu as item 10, so Data capture is item 11 and Done 12. Properties unchanged.

v1.5  2026-10-04 — OTV4TEST r233 (BOX.17). D6 now pins the box as ABLE to push (the probe overrides
      the unit read and the drop-in path), because on a standalone box the clamp is meant to be off;
      D6c: a masked s3-push or the never-push drop-in IGNORES a frozen push mark and names it; a
      drop-in saying OT_S3_PUSH=1, or an unreadable unit, still clamps (keeps rows). D3b: standalone
      writes the never-push drop-in and REPORTS a failed mask instead of hiding it; D3c: managed
      removes the drop-in before it installs the pusher; D1b: status names the push guard.

v1.4  2026-10-03 — OTV4TEST r228. D4 RE-POINTED (section 38.4): the ORB and VOLT scaling items
      left the menu, so Data capture is item 10 and Done 11. Properties unchanged.

v1.3  2026-09-27 — OTV4TEST r161. D4 RE-POINTED, NOT DROPPED (§38.4): the menu grew
      the three scaling switches (9-11), so Data capture is item 12 and Done 13. The
      properties are unchanged: data capture does not mark the bot for restart, and
      the prompt names the real range.

v1.2  2026-09-25 — OTV4TEST r139. D5b: a SOFI box whose store still holds a previous
      instrument's candles (QQQ, QQQ_EXT - the first SOFI box's feed streamed QQQ)
      pushes only SOFI/SOFI_EXT (and VIXY stays out now: not its family); D5c:
      own_symbol() takes OT_INSTRUMENT over a stale OHLC file of the old symbol.

v1.1  2026-09-25 — OTV4TEST r138. D2c: when the shell's OT_INSTRUMENT and the bot
      unit's DISAGREE, managed REFUSES and changes nothing (the SOFI box printed
      "pushing as sym=QQQ" from a shell still carrying the bootstrap's QQQ);
      when they agree it proceeds; the unit wins over an empty shell (D2).
ONE SWITCH, "MANAGED" OR "STANDALONE" DATA CAPTURE, AND THE TWO MAINLINE FIXES
A PUSHING BOX NEEDS.

v1.0  2026-09-24 — OTV4TEST r136. The operator: "Make the s3 push compatible with
      the conductor through a toggle in configure.sh call it 'managed' or
      'standalone' data capture", "Have the same toggle switch off the cleanup
      for 'managed'", "Have the same toggle switch off the VIX logging", "Adopt
      mainline's approach. Should work under managed or standalone."

  D1  status is READ FROM THE UNITS: managed / standalone / MIXED, and a missing
      unit reads "not-found" once (systemctl prints it AND exits non-zero)
  D2  managed: unmasks s3-push, gives the unit OT_INSTRUMENT (a drop-in), runs
      the s3-push, candle-logger and self-close installers, DISABLES this box's
      16:05 purge - under a sudo stub that writes nothing real
  D2b managed with no instrument anywhere REFUSES (never pushes as UNKNOWN)
  D3  standalone: disables and MASKS s3-push, turns candle-logger and self-close
      off, turns this box's own purge back on
  D4  configure.sh: item 11 runs the ONE script; it does not restart the bot;
      Done is 12; the summary shows the mode
  D5  VIX family (mainline r350): a non-SPX box uploads SOFI and SOFI_EXT and
      VIXY, never VIX or VIX_EXT; the SPX box still uploads the family
  D6  purge clamp (mainline r417): a push mark older than the age cutoff WINS;
      a newer mark changes nothing; NO ledger (standalone) = age only, silently
  D6b both purge call sites route the cutoff through _safe_cutoff before the
      DELETE (AST) - the purge itself is NOT run: it also prunes the repo's
      data/ trees, and a checker must never reach live state
  D7  setup_ec2.sh applies the mode through data_capture.sh (no hard-coded mask)
      and installs python3-boto3 and tzdata-legacy
  D0  /etc/systemd/system untouched
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED, RAN, _TMP = [], [], []


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


def _mk(p):
    d = tempfile.mkdtemp(prefix="datacapcheck_" + p)
    _TMP.append(d)
    return d


def _read(rel):
    try:
        return open(os.path.join(_root, rel), encoding="utf-8").read()
    except OSError:
        return ""


_sysd_before = sorted(os.listdir("/etc/systemd/system")) if os.path.isdir("/etc/systemd/system") else []

# ── fixture: data_capture.sh in a planted repo, systemctl/sudo/installers stubbed ─
def _fixture(states, instrument_in_unit=None):
    d = _mk("repo_")
    repo = os.path.join(d, "repo")
    os.makedirs(os.path.join(repo, "deploy"))
    src = os.path.join(_root, "deploy", "data_capture.sh")
    if os.path.exists(src):
        shutil.copy(src, os.path.join(repo, "deploy", "data_capture.sh"))
    log = os.path.join(d, "log")
    for inst in ("install_s3_push_timer.sh", "install_candle_logger_timer.sh",
                 "install_self_close.sh", "install_retention_purge_timer.sh"):
        with open(os.path.join(repo, "deploy", inst), "w") as fh:
            fh.write('#!/bin/sh\necho "installer %s" >> "%s"\n' % (inst, log))
    stubs = os.path.join(d, "bin")
    os.makedirs(stubs)
    stdir = os.path.join(d, "states")
    os.makedirs(stdir)
    for u, st in states.items():
        open(os.path.join(stdir, u), "w").write(st)
    with open(os.path.join(stubs, "systemctl"), "w") as fh:
        fh.write('#!/bin/sh\n'
                 'if [ "$1" = "is-enabled" ]; then\n'
                 '  f="%s/$2"; if [ -f "$f" ]; then cat "$f"; [ "$(cat "$f")" = enabled ] && exit 0; exit 1; fi\n'
                 '  echo not-found; exit 4\n'
                 'fi\n'
                 'echo "systemctl $*" >> "%s"; exit 0\n' % (stdir, log))
    dropin = os.path.join(d, "dropin.conf")
    unitfile = os.path.join(d, "optionsbot.service")
    if instrument_in_unit:
        open(unitfile, "w").write("[Service]\nEnvironment=OT_INSTRUMENT=%s\n" % instrument_in_unit)
    with open(os.path.join(stubs, "sudo"), "w") as fh:
        fh.write('#!/bin/sh\n'
                 'case "$1" in\n'
                 '  tee) cat > "%s"; echo "sudo tee $2" >> "%s" ;;\n'
                 '  grep) shift; exec grep "$@" ;;\n'
                 '  *) echo "sudo $*" >> "%s" ;;\n'
                 'esac\nexit 0\n' % (dropin, log, log))
    for s in ("systemctl", "sudo"):
        os.chmod(os.path.join(stubs, s), 0o755)
    return repo, stubs, log, dropin, unitfile


def _run(mode, states, instrument_env=None, instrument_in_unit=None):
    repo, stubs, log, dropin, unitfile = _fixture(states, instrument_in_unit)
    script = os.path.join(repo, "deploy", "data_capture.sh")
    txt = open(script).read() if os.path.exists(script) else ""
    open(script, "w").write(txt.replace('UNIT_FILE="/etc/systemd/system/optionsbot.service"',
                                        'UNIT_FILE="%s"' % unitfile)
                             .replace('NEVER_PUSH_CONF="/etc/systemd/system/s3-push.service.d/never-push.conf"',
                                      'NEVER_PUSH_CONF="%s"' % dropin))
    env = {"PATH": stubs + ":/usr/bin:/bin", "HOME": os.path.dirname(repo)}
    if instrument_env:
        env["OT_INSTRUMENT"] = instrument_env
    r = subprocess.run(["bash", script, mode], capture_output=True, text=True, env=env, timeout=60)
    return (r, open(log).read() if os.path.exists(log) else "",
            open(dropin).read() if os.path.exists(dropin) else "")


MANAGED_ST = {"s3-push.timer": "enabled", "candle-logger.timer": "enabled",
              "optbot-self-close.timer": "enabled", "optbot-retention-purge.timer": "disabled"}
STANDALONE_ST = {"s3-push.timer": "masked", "optbot-retention-purge.timer": "enabled"}

r, _l, _d = _run("status", MANAGED_ST)
guard("D1 status reads MANAGED from the units", lambda: r.stdout.startswith("data capture: managed"),
      lambda: r.stdout[:120])
r, _l, _d = _run("status", STANDALONE_ST)
guard("D1 status reads STANDALONE from the units (missing timers read not-found, once)",
      lambda: r.stdout.startswith("data capture: standalone")
      and "candle-logger.timer=not-found " in r.stdout and "absent" not in r.stdout,
      lambda: r.stdout[:200])
r, _l, _d = _run("status", {"s3-push.timer": "enabled", "optbot-retention-purge.timer": "enabled"})
guard("D1 a half-applied box reads MIXED, never a mode it is not in",
      lambda: r.stdout.startswith("data capture: MIXED"), lambda: r.stdout[:120])

r, log, dropin = _run("managed", STANDALONE_ST, instrument_env="SOFI")
guard("D2 managed: s3-push unmasked, then the three conductor units installed",
      lambda: r.returncode == 0 and "sudo systemctl unmask s3-push.service s3-push.timer" in log
      and all("installer %s" % i in log for i in ("install_s3_push_timer.sh",
                                                   "install_candle_logger_timer.sh",
                                                   "install_self_close.sh")),
      lambda: "rc=%s log=%s" % (r.returncode, log[-300:]))
guard("D2 managed: the push unit is told its OWN symbol (drop-in)",
      lambda: dropin == "[Service]\nEnvironment=OT_INSTRUMENT=SOFI\n", lambda: repr(dropin))
guard("D2 managed: this box's own 16:05 purge is DISABLED (the conductor owns it)",
      lambda: "sudo systemctl disable --now optbot-retention-purge.timer" in log)
guard("D2 managed: the unmask happens BEFORE the s3-push installer",
      lambda: 0 <= log.find("unmask s3-push") < log.find("installer install_s3_push_timer.sh"))
r2, log2, dropin2 = _run("managed", STANDALONE_ST, instrument_in_unit="AAL")
guard("D2 managed reads the instrument from the bot unit when not given",
      lambda: r2.returncode == 0 and "OT_INSTRUMENT=AAL" in dropin2, lambda: repr(dropin2))
r3, log3, dropin3 = _run("managed", STANDALONE_ST)
guard("D2b managed with no instrument anywhere REFUSES and installs nothing",
      lambda: r3.returncode != 0 and "installer" not in log3 and "unmask" not in log3
      and dropin3 == "", lambda: "rc=%s %s" % (r3.returncode, r3.stdout[-160:]))

r4, log4, drop4 = _run("managed", STANDALONE_ST, instrument_env="QQQ", instrument_in_unit="SOFI")
guard("D2c shell QQQ vs unit SOFI: REFUSED, nothing installed, no drop-in, conflict named",
      lambda: r4.returncode != 0 and "installer" not in log4 and "unmask" not in log4
      and drop4 == "" and "CONFLICT" in r4.stderr + r4.stdout,
      lambda: "rc=%s %s" % (r4.returncode, (r4.stderr or r4.stdout)[-160:]))
r5, log5, drop5 = _run("managed", STANDALONE_ST, instrument_env="SOFI", instrument_in_unit="SOFI")
guard("D2c shell and unit agree: proceeds, pushing as SOFI",
      lambda: r5.returncode == 0 and "OT_INSTRUMENT=SOFI" in drop5)

r, _l, _d = _run("status", {**STANDALONE_ST, "s3-push.service": "masked"})
guard("D1b status names the push guard: masked",
      lambda: "push guard: masked" in r.stdout and "🔴" not in r.stdout, lambda: r.stdout[-200:])
r, _l, _d = _run("status", STANDALONE_ST)
guard("D1b standalone with NO guard (no mask, no drop-in) is flagged red, not just 'standalone'",
      lambda: "push guard: NONE" in r.stdout and "🔴 standalone, but NOTHING stops" in r.stdout,
      lambda: r.stdout[-240:])
r, log, dro = _run("standalone", {**MANAGED_ST, "optbot-retention-purge.timer": "disabled",
                                  "s3-push.service": "enabled"})
guard("D3b standalone writes the never-push drop-in (OT_S3_PUSH=0)",
      lambda: dro == "[Service]\nEnvironment=OT_S3_PUSH=0\n" and "sudo tee " in log,
      lambda: repr(dro))
guard("D3b a mask that did NOT take is SAID (state named), and the drop-in is named as the guard",
      lambda: "could NOT be masked (state: enabled" in r.stdout and "never-push drop-in is the guard" in r.stdout
      and "push guard: never-push drop-in (OT_S3_PUSH=0)" in r.stdout, lambda: r.stdout[-400:])
r, log, dro = _run("standalone", {**MANAGED_ST, "optbot-retention-purge.timer": "disabled",
                                  "s3-push.service": "masked"})
guard("D3b a mask that took: no warning; the guard reads masked + drop-in",
      lambda: "could NOT be masked" not in r.stdout
      and "push guard: masked + never-push drop-in (OT_S3_PUSH=0)" in r.stdout, lambda: r.stdout[-300:])
r, log, dro = _run("managed", STANDALONE_ST, instrument_env="SOFI")
guard("D3c managed REMOVES the never-push drop-in before it unmasks and installs the pusher",
      lambda: 0 <= log.find("sudo rm -f ") < log.find("unmask s3-push") < log.find("installer install_s3_push_timer.sh"),
      lambda: log[-300:])
r, log, _d = _run("standalone", {**MANAGED_ST, "optbot-retention-purge.timer": "disabled"})
guard("D3 standalone: s3-push disabled and MASKED",
      lambda: "sudo systemctl disable --now s3-push.timer" in log
      and "sudo systemctl mask s3-push.service s3-push.timer" in log, lambda: log[-300:])
guard("D3 standalone: candle-logger and self-close off, this box's purge back on",
      lambda: "sudo systemctl disable --now candle-logger.timer optbot-self-close.timer" in log
      and ("sudo systemctl enable --now optbot-retention-purge.timer" in log
           or "installer install_retention_purge_timer.sh" in log), lambda: log[-300:])

# ── D4 configure.sh ──────────────────────────────────────────────────────────
_cfg = _read("configure.sh")
guard("D4 item 14 runs change_data_capture and does NOT mark the bot for restart",
      lambda: re.search(r"^\s*14\)\s*change_data_capture\s*;;", _cfg, re.M)
      and not re.search(r"^\s*14\)[^\n]*CHANGED=true", _cfg, re.M))
_cdc = (re.search(r"^change_data_capture\(\) \{\n.*?^\}", _cfg, re.M | re.S) or re.match("", "")).group(0)
guard("D4 change_data_capture calls the ONE script for both answers (scoped to its body - r139's item 1 also re-applies managed)",
      lambda: _cdc.count('bash "$BOT_DIR/deploy/data_capture.sh" managed') == 1
      and _cdc.count('bash "$BOT_DIR/deploy/data_capture.sh" standalone') == 1)
guard("D4 Done is 17, the prompt names 1-17, and the summary shows the mode",
      lambda: re.search(r"^\s*17\)\s*break", _cfg, re.M) and "Select [1-17]" in _cfg
      and "Data capture:   ${BOLD}$(data_capture_label)" in _cfg)

# ── D5 VIX family ────────────────────────────────────────────────────────────
def _d5(me):
    d = _mk("vix_")
    db = os.path.join(d, "feed.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER, open REAL,"
              " high REAL, low REAL, close REAL, volume REAL)")
    for s in ("SOFI", "SOFI_EXT", "VIX", "VIX_EXT", "VIXY", "QQQ", "QQQ_EXT"):
        c.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", (s, "1m", 1790000000000, 1, 1, 1, 1, 1))
    c.commit(); c.close()
    import warehouse.s3_push as sp
    keys = []
    real = sp.put_and_verify
    sp.put_and_verify = lambda s3, b, key, body, counters=None: keys.append(key) or True
    try:
        sp.push_candles(None, "fixture-bucket", db, {}, me)
    finally:
        sp.put_and_verify = real
    return sorted({re.search(r"sym=([^/]+)/", k).group(1) for k in keys})


try:
    _sofi, _spx = _d5("SOFI"), _d5("SPX")
except Exception as exc:                                        # noqa: BLE001
    _sofi = _spx = ["ERR %s" % exc]
guard("D5 a SOFI box uploads SOFI and SOFI_EXT only - never VIX/VIX_EXT",
      lambda: _sofi == ["SOFI", "SOFI_EXT"], lambda: str(_sofi))
guard("D5b ...and never a previous instrument's rows (QQQ, QQQ_EXT) or another root (VIXY)",
      lambda: not ({"QQQ", "QQQ_EXT", "VIXY"} & set(_sofi)), lambda: str(_sofi))
guard("D5 the SPX box still uploads the VIX family, and not QQQ",
      lambda: "VIX" in _spx and "VIX_EXT" in _spx and "QQQ" not in _spx, lambda: str(_spx))


def _d5c():
    import warehouse.s3_push as sp
    d = _mk("ohlc_")
    os.makedirs(os.path.join(d, "2026-09-24"))
    open(os.path.join(d, "2026-09-24", "QQQ.csv"), "w").write("x")
    real_root, real_env = sp.OHLC_ROOT, os.environ.get("OT_INSTRUMENT")
    try:
        sp.OHLC_ROOT = d
        os.environ["OT_INSTRUMENT"] = "SOFI"
        with_env = sp.own_symbol()
        os.environ.pop("OT_INSTRUMENT", None)
        import utils.instrument as _ui
        _real_unit = _ui._from_bot_unit
        try:
            _ui._from_bot_unit = lambda: ""            # r41: no bot unit, so the file is the fallback (CD.1 order)
            without_env = sp.own_symbol()
            _ui._from_bot_unit = lambda: "AMD"         # D5d: the unit's symbol wins over a stale file
            unit_wins = sp.own_symbol()
        finally:
            _ui._from_bot_unit = _real_unit
    finally:
        sp.OHLC_ROOT = real_root
        if real_env is None:
            os.environ.pop("OT_INSTRUMENT", None)
        else:
            os.environ["OT_INSTRUMENT"] = real_env
    return with_env == "SOFI" and without_env == "QQQ" and unit_wins == "AMD", (with_env, without_env, unit_wins)


guard("D5c own_symbol: OT_INSTRUMENT wins over a stale QQQ OHLC file, then the bot unit (D5d), then the file",
      lambda: _d5c()[0], lambda: str(_d5c()[1]))

# ── D6 purge clamp ───────────────────────────────────────────────────────────
_PROBE = r'''
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
import warehouse.retention_purge as rp
rp.NEVER_PUSH_DROPIN = os.path.join(os.environ["OT_WAREHOUSE_STATE"], "no-such-dropin.conf")
rp._unit_state = lambda unit: "enabled"      # a box that CAN push: the clamp applies
now = time.time(); DAY = 86400
age = now - 3 * DAY
out = {}
out["no_ledger"] = list(rp._safe_cutoff("quote_series", age, rp.SERIES_LEDGER, "series"))
json.dump({"series|quote_series": now - 7 * DAY}, open(rp.SERIES_LEDGER, "w"))
c, note = rp._safe_cutoff("quote_series", age, rp.SERIES_LEDGER, "series")
out["older_mark"] = [round((now - c) / DAY, 3), note[:20]]
json.dump({"dseries|indicator_series": now - 1 * DAY}, open(rp.DSERIES_LEDGER, "w"))
c, note = rp._safe_cutoff("indicator_series", age, rp.DSERIES_LEDGER, "dseries")
out["newer_mark"] = [round((now - c) / DAY, 3), note]
out["ledger_dir"] = os.path.dirname(rp.SERIES_LEDGER)
print(json.dumps(out))
'''


def _d6():
    st = _mk("state_")
    r = subprocess.run([sys.executable, "-c", _PROBE, _root], capture_output=True, text=True,
                       env={**os.environ, "OT_WAREHOUSE_STATE": st}, timeout=60)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1]), st
    except (ValueError, IndexError):
        return {"err": r.stderr[-300:]}, st


_D6, _st = _d6()
guard("D6 no push ledger (standalone): age cutoff unchanged and NO warning",
      lambda: _D6["no_ledger"][1] == "" and abs(_D6["no_ledger"][0] - (time.time() - 3 * 86400)) < 60,
      lambda: str(_D6)[:200])
guard("D6 a push mark OLDER than the age cutoff wins (7 days kept back, named)",
      lambda: _D6["older_mark"][0] == 7.0 and _D6["older_mark"][1].startswith("CLAMPED"),
      lambda: str(_D6.get("older_mark")))
guard("D6 a push mark NEWER than the age cutoff changes nothing",
      lambda: _D6["newer_mark"] == [3.0, ""], lambda: str(_D6.get("newer_mark")))
guard("D6 the ledger is read from OT_WAREHOUSE_STATE (the pusher's own state dir)",
      lambda: _D6["ledger_dir"] == _st)

_PROBE_C = r'''
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
import warehouse.retention_purge as rp
st = os.environ["OT_WAREHOUSE_STATE"]; now = time.time(); DAY = 86400; age = now - 3 * DAY
json.dump({"series|quote_series": now - 7 * DAY}, open(rp.SERIES_LEDGER, "w"))
out = {}
def case(name, unit, dropin):
    rp._NEVER = None
    rp._unit_state = unit
    rp.NEVER_PUSH_DROPIN = os.path.join(st, name + ".conf")
    if dropin is not None:
        open(rp.NEVER_PUSH_DROPIN, "w").write(dropin)
    c, note = rp._safe_cutoff("quote_series", age, rp.SERIES_LEDGER, "series")
    out[name] = [round((now - c) / DAY, 3), note]
case("masked", lambda u: "masked", None)
case("dropin", lambda u: "disabled", "[Service]\nEnvironment=OT_S3_PUSH=0\n")
case("dropin_on", lambda u: "disabled", "[Service]\nEnvironment=OT_S3_PUSH=1\n")
case("timer_off_only", lambda u: "disabled", None)
case("unreadable", lambda u: "", None)
print(json.dumps(out))
'''


def _d6c():
    st = _mk("state_c_")
    r = subprocess.run([sys.executable, "-c", _PROBE_C, _root], capture_output=True, text=True,
                       env={**os.environ, "OT_WAREHOUSE_STATE": st}, timeout=60)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"err": r.stderr[-300:]}


_D6C = _d6c()
guard("D6c s3-push MASKED: a frozen push mark is IGNORED (age cutoff) and named",
      lambda: _D6C["masked"][0] == 3.0 and "IGNORED" in _D6C["masked"][1] and "masked" in _D6C["masked"][1],
      lambda: str(_D6C)[:300])
guard("D6c the never-push drop-in (OT_S3_PUSH=0): the mark is IGNORED and named",
      lambda: _D6C["dropin"][0] == 3.0 and "OT_S3_PUSH=0" in _D6C["dropin"][1], lambda: str(_D6C)[:300])
guard("D6c a drop-in saying OT_S3_PUSH=1 still CLAMPS",
      lambda: _D6C["dropin_on"][0] == 7.0 and _D6C["dropin_on"][1].startswith("CLAMPED"), lambda: str(_D6C)[:300])
guard("D6c a merely DISABLED timer still CLAMPS (the conductor's quiesce is not 'never pushes')",
      lambda: _D6C["timer_off_only"][0] == 7.0, lambda: str(_D6C)[:300])
guard("D6c an unreadable unit state still CLAMPS (unknown keeps rows)",
      lambda: _D6C["unreadable"][0] == 7.0, lambda: str(_D6C)[:300])


def _d6b():
    tree = ast.parse(_read("warehouse/retention_purge.py"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "purge")
    src = ast.get_source_segment(_read("warehouse/retention_purge.py"), fn)
    a = src.find("for table, days in ARTIFACT_DAYS.items():")
    b = src.find("list(DERIVED_CDC_DAYS.items()):")
    ok = []
    for start, ledger in ((a, "SERIES_LEDGER"), (b, "DSERIES_LEDGER")):
        seg = src[start:start + 2500]   # r279: the dry-run COUNT block sits between clamp and delete
        clamp = seg.find("_safe_cutoff(table, cutoff, %s" % ledger)
        # r279: the DELETE moved into `_delete_batched` (mirror of otv4 r416); the call is the delete.
        delete = seg.find("_delete_batched(")
        ok.append(start >= 0 and 0 <= clamp < delete)
    return all(ok), ok


guard("D6b both purge loops clamp the cutoff before their DELETE", lambda: _d6b()[0],
      lambda: str(_d6b()[1]))

# ── D7 setup_ec2.sh ──────────────────────────────────────────────────────────
_setup = _read("setup_ec2.sh")
guard("D7 setup applies the mode through data_capture.sh; no hard-coded s3-push mask",
      lambda: 'ot_capture_install "$INSTALL_DIR" "$INSTRUMENT" "$DATA_CAPTURE"' in _setup
      and 'bash "$install_dir/deploy/data_capture.sh" standalone' in _read("deploy/install_services.sh")
      and not re.search(r"^sudo systemctl mask s3-push", _setup, re.M))
guard("D7 setup installs python3-boto3 and tzdata-legacy (the conductor's system python)",
      lambda: re.search(r"apt-get install[^\n]*python3-boto3[^\n]*tzdata-legacy", _setup))

# ── D0 ───────────────────────────────────────────────────────────────────────
for d in _TMP:
    shutil.rmtree(d, ignore_errors=True)
guard("D0 /etc/systemd/system is untouched",
      lambda: (sorted(os.listdir("/etc/systemd/system")) if os.path.isdir("/etc/systemd/system")
               else []) == _sysd_before)
guard("D0 no datacapcheck_ temp dirs left behind",
      lambda: not [n for n in os.listdir(tempfile.gettempdir()) if n.startswith("datacapcheck_")])

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
