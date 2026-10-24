#!/usr/bin/env python3
"""
tests/check_clean_deploy.py  v1.0
v1.0  2026-10-24  CD.1 — AN INSTALL STARTS NOTHING AND PUSHES NOTHING; configure.sh's FIRST DONE STARTS EVERYTHING,
      IN ORDER; MANAGED IS GUARDED. Behaviour, not source text (WA §21): deploy/install_services.sh's functions and
      configure.sh's functions are RUN under a harness whose sudo / systemctl / python / data_capture are stubs that
      record every call (nothing touches systemd or the warehouse); setup_ec2.sh runs in --plan; capture_guard.scan
      runs against warehouse_source's _FakeS3.
  C1  install: daemon-reload, every service DISABLED, never enabled or started; one already active is STOPPED
  C2  install: data capture applied STANDALONE even when the bootstrap asked for managed; the request is RECORDED
  C3  setup_ec2.sh --plan: data_capture=standalone, data_capture_requested=<bootstrap>, a first_start line, and no
      start_bot line (OT_START_BOT is gone); a managed bootstrap plans standalone
  C4  first Done: enable+start candle-feed BEFORE the primer, the primer BEFORE enable+start of the bot, data capture
      MANAGED (chosen) only AFTER the bot is running; the marker is written
  C5  first Done with standalone chosen (or nothing chosen): data capture is never set managed
  C6  a later Done (marker present): no primer, no feed start - running + changed restarts the bot only
  C7  candle-feed fails to start: the first start STOPS - no primer, no bot, no capture, no marker
  C8  a box already running before CD.1: Done marks it and changes nothing (no primer, no capture call)
  C9  item 14 on a box before its first start: guard clean -> MANAGED recorded, NOT applied; another pusher and no
      OVERRIDE -> nothing recorded; unreadable warehouse + OVERRIDE -> recorded
  C10 capture_guard.scan: another host 9 days ago -> rc 1 naming host and date; only this host -> rc 0; a warehouse
      error -> rc 2 (fail closed)
  C11 item 1 after the first start runs the primer for the new symbol; before it, does not
  C12 the banner names the first start (PENDING before, done after)
  C14 item 1 on a MANAGED box drains the OLD symbol under its own label BEFORE the unit changes, wipes the paper db
      after, re-labels managed, guards the NEW symbol (clean -> not paused)
  C15 an OLD drain that is not OK refuses the switch: no unit change, no db wipe, named
  C16 another pusher of the NEW symbol and no OVERRIDE -> the push is PAUSED (flag file); OVERRIDE -> not paused
  C17 warehouse/s3_push.py: the pause flag stops every entrypoint (--verify prints DRAIN ... PAUSED, nothing pushed);
      own_symbol() falls back to the bot unit's instrument before any OHLC file
  C13 a primer that cannot prime (rc 2/3/4) REFUSES the first start: candle-feed up, the bot NOT started, no capture,
      no marker, the refusal named (the operator: "Don't allow this situation to happen in the 1st place. We have s3")
Run: python3 tests/check_clean_deploy.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
CONFIGURE = os.path.join(ROOT, "configure.sh")
SERVICES = os.path.join(ROOT, "deploy", "install_services.sh")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  [{detail}]"))
    RAN.append(name)
    if not ok:
        FAILED.append(name.split()[0])


def _functions_only(src: str) -> str:
    out, keep = [], False
    for line in src.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\(\)\s*\{", line):
            keep = True
        if keep:
            out.append(line)
        if keep and line == "}":
            keep = False
    return "\n".join(out)


def _stub(path, body):
    open(path, "w").write("#!/bin/bash\n" + body)
    os.chmod(path, 0o755)


def _world(tmp, active=(), primer_rc=0, guard_rc=0, feed_starts=True, capture="standalone", drain="OK"):
    """A stub world: sudo/systemctl/python/data_capture record to `log`; systemctl is-active reads `state/`."""
    log, st = os.path.join(tmp, "log"), os.path.join(tmp, "state")
    os.makedirs(st, exist_ok=True)
    for a in active:
        open(os.path.join(st, a), "w").write("1")
    bot = os.path.join(tmp, "bot")
    os.makedirs(os.path.join(bot, "deploy"), exist_ok=True)
    os.makedirs(os.path.join(bot, "tools"), exist_ok=True)
    bindir = os.path.join(tmp, "bin")
    os.makedirs(bindir, exist_ok=True)
    _stub(os.path.join(bindir, "systemctl"), f'''
echo "systemctl $*" >> "{log}"
case "$1" in
  is-active) [ "$2" = "--quiet" ] && u="$3" || u="$2"; [ -f "{st}/$u" ] && {{ echo active; exit 0; }}; echo inactive; exit 3;;
  start|restart) [ "$2" = candle-feed ] && [ "{int(feed_starts)}" = 0 ] && exit 1; echo 1 > "{st}/$2";;
  stop) rm -f "{st}/$2";;
esac
exit 0
''')
    _stub(os.path.join(bindir, "sudo"), f'echo "sudo $*" >> "{log}"\n"$@"\n')
    _stub(os.path.join(bindir, "botpy"), f'''
echo "python $*" >> "{log}"
case "$1" in
  tools/prime_ramp.py) exit {primer_rc};;
  tools/capture_guard.py) echo "guard says rc {guard_rc}"; exit {guard_rc};;
esac
exit 0
''')
    _stub(os.path.join(bot, "deploy", "data_capture.sh"), f'''
echo "data_capture $*" >> "{log}"
[ "$1" = status ] && echo "data capture: {capture}"
exit 0
''')
    _stub(os.path.join(bindir, "pushpy"), f'''
echo "push OT_INSTRUMENT=$OT_INSTRUMENT $*" >> "{log}"
echo "DRAIN host=x sym=$OT_INSTRUMENT drained=yes pushed=0 failed=0 prefixes=1 local=1 s3=1 short=0 {drain}"
exit 0
''')
    return log, bot, bindir


def _run_configure(tmp, script, bot, bindir, marker=None, choice=None, stdin=""):
    funcs = os.path.join(tmp, "funcs.sh")
    open(funcs, "w").write(_functions_only(open(CONFIGURE).read()))
    fsf = os.path.join(tmp, "first_start_done")
    if marker:
        open(fsf, "w").write(marker)
    ccf = os.path.join(tmp, "capture.choice")
    if choice:
        open(ccf, "w").write(choice + "\n")
    harness = f'''
RESET=""; BOLD=""; GREEN=""; YELLOW=""; CYAN=""; RED=""
SERVICE_NAME=optionsbot; FEED_SERVICE=candle-feed; BOT_DIR="{bot}"
FIRST_START_FILE="{fsf}"; CAPTURE_CHOICE_FILE="{ccf}"; CAPTURE_REQUESTED_FILE="{tmp}/capture.requested"
BOT_PY="{bindir}/botpy"; PUSH_PY="{bindir}/pushpy"; PUSH_PAUSE_FILE="{tmp}/push_paused"
export PATH="{bindir}:$PATH"
source "{funcs}"
sleep() {{ :; }}
show_config() {{ :; }}
get_env() {{ case "$1" in OT_INSTRUMENT) echo AMD;; OT_PAPER_TRADING) echo True;; *) echo "";; esac; }}
bot_is_running() {{ systemctl is-active --quiet optionsbot; }}
{script}
'''
    r = subprocess.run(["bash", "-c", harness], input=stdin, capture_output=True, text=True, timeout=60)
    return r, fsf, ccf


def _calls(log):
    return open(log).read().splitlines() if os.path.exists(log) else []


def _idx(calls, pat):
    for i, c in enumerate(calls):
        if re.search(pat, c):
            return i
    return -1


def main() -> int:
    # ── C1 / C2: deploy/install_services.sh ──────────────────────────────────────────────────────────
    if not os.path.isfile(SERVICES):
        check("C1 deploy/install_services.sh exists", False, "missing")
        check("C2 deploy/install_services.sh exists", False, "missing")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            log, bot, bindir = _world(tmp, active=("optionsbot",))
            req = os.path.join(tmp, "requested")
            r = subprocess.run(["bash", "-c", f'export PATH="{bindir}:$PATH"; OT_CAPTURE_REQUESTED_FILE="{req}"; '
                                f'. "{SERVICES}"; ot_services_installed_stopped candle-feed optionsbot; '
                                f'ot_capture_install "{bot}" AMD managed'],
                               capture_output=True, text=True, timeout=60)
            c = _calls(log)
            sysc = [x for x in c if x.startswith("systemctl") and "is-active" not in x]
            ok1 = (any("daemon-reload" in x for x in sysc)
                   and any(re.search(r"disable candle-feed", x) for x in sysc)
                   and any(re.search(r"disable optionsbot", x) for x in sysc)
                   and not any(re.search(r"\b(enable|start|restart)\b", x) for x in sysc)
                   and any(re.search(r"stop optionsbot", x) for x in sysc)
                   and not any(re.search(r"stop candle-feed", x) for x in sysc))
            check("C1 install: daemon-reload, both DISABLED, none enabled/started, the active one STOPPED",
                  ok1, f"{sysc}")
            dc = [x for x in c if x.startswith("data_capture")]
            check("C2 install: capture STANDALONE although managed was asked; the request RECORDED",
                  dc == ["data_capture standalone"] and open(req).read().strip() == "managed",
                  f"{dc} / {open(req).read() if os.path.exists(req) else None}")

    # ── C3: setup_ec2.sh --plan ──────────────────────────────────────────────────────────────────────
    def plan(extra):
        with tempfile.TemporaryDirectory() as home:
            env = {"PATH": "/usr/bin:/bin", "HOME": home, "TT_CLIENT_SECRET": "x", "TT_REFRESH_TOKEN": "x",
                   "TT_ACCOUNT_NUMBER": "x", "TELEGRAM_TOKEN": "x", "TELEGRAM_CHAT_ID": "x", **extra}
            r = subprocess.run(["setsid", "-w", "bash", os.path.join(ROOT, "setup_ec2.sh"), "--plan"],
                               stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, timeout=60)
            return {m.group(1): m.group(2) for m in re.finditer(r"^PLAN (\w+)=(.*)$", r.stdout, re.M)}, r
    p0, r0 = plan({})
    p1, r1 = plan({"OT_DATA_CAPTURE": "managed", "OT_START_BOT": "1"})
    check("C3 --plan: capture standalone (requested recorded), a first_start line, no start_bot",
          p0.get("data_capture") == "standalone" and p0.get("data_capture_requested") == "standalone"
          and "first_start" in p0 and "start_bot" not in p0
          and p1.get("data_capture") == "standalone" and p1.get("data_capture_requested") == "managed"
          and "start_bot" not in p1,
          f"{p0} | {p1} | rc {r0.returncode}/{r1.returncode} {r0.stdout[-200:]}")

    # ── C4-C8: configure.sh finish_session ───────────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        log, bot, bindir = _world(tmp)
        r, fsf, _ = _run_configure(tmp, "CHANGED=false; finish_session", bot, bindir, choice="managed")
        c = _calls(log)
        i_fe, i_fs = _idx(c, r"sudo systemctl enable candle-feed"), _idx(c, r"sudo systemctl start candle-feed")
        i_pr = _idx(c, r"python tools/prime_ramp.py --apply")
        i_be, i_bs = _idx(c, r"sudo systemctl enable optionsbot"), _idx(c, r"sudo systemctl start optionsbot")
        i_dc = _idx(c, r"data_capture managed")
        check("C4 first Done: feed enable+start < primer < bot enable+start < capture MANAGED; marker written",
              -1 < i_fe < i_fs < i_pr < i_be < i_bs < i_dc and os.path.exists(fsf),
              f"order fe {i_fe} fs {i_fs} pr {i_pr} be {i_be} bs {i_bs} dc {i_dc}; marker {os.path.exists(fsf)}\n{c}")
    for ch in ("standalone", None):
        with tempfile.TemporaryDirectory() as tmp:
            log, bot, bindir = _world(tmp)
            r, fsf, _ = _run_configure(tmp, "CHANGED=false; finish_session", bot, bindir, choice=ch)
            c = _calls(log)
            check(f"C5 first Done, choice {ch}: never managed; bot started; marker written",
                  not any("data_capture managed" in x for x in c) and _idx(c, r"start optionsbot") > -1
                  and os.path.exists(fsf), f"{c}")
    with tempfile.TemporaryDirectory() as tmp:
        log, bot, bindir = _world(tmp, active=("optionsbot", "candle-feed"))
        r, _, _ = _run_configure(tmp, "CHANGED=true; finish_session", bot, bindir, marker="2026-10-24T20:00:00Z")
        c = _calls(log)
        check("C6 later Done (marker present, running, changed): restart the bot only - no primer, no feed start",
              _idx(c, r"restart optionsbot") > -1 and _idx(c, r"prime_ramp") == -1
              and _idx(c, r"start candle-feed") == -1, f"{c}")
    with tempfile.TemporaryDirectory() as tmp:
        log, bot, bindir = _world(tmp, feed_starts=False)
        r, fsf, _ = _run_configure(tmp, "CHANGED=false; finish_session", bot, bindir, choice="managed")
        c = _calls(log)
        check("C7 the feed fails: STOP - no primer, no bot start, no capture, no marker",
              _idx(c, r"prime_ramp") == -1 and _idx(c, r"start optionsbot") == -1
              and not any(x.startswith("data_capture managed") for x in c) and not os.path.exists(fsf), f"{c}")
    for prc in (4, 3, 2):
        with tempfile.TemporaryDirectory() as tmp:
            log, bot, bindir = _world(tmp, primer_rc=prc)
            r, fsf, _ = _run_configure(tmp, "CHANGED=false; finish_session", bot, bindir, choice="managed")
            c = _calls(log)
            check(f"C13 the primer cannot prime (rc {prc}): first start REFUSED - no bot, no capture, no marker, named",
                  _idx(c, r"start optionsbot") == -1 and not any(x.startswith("data_capture managed") for x in c)
                  and not os.path.exists(fsf) and "FIRST START REFUSED" in r.stdout
                  and _idx(c, r"start candle-feed") > -1, f"{c}\n{r.stdout[-300:]}")
    with tempfile.TemporaryDirectory() as tmp:
        log, bot, bindir = _world(tmp, active=("optionsbot", "candle-feed"))
        r, fsf, _ = _run_configure(tmp, "CHANGED=false; finish_session", bot, bindir, choice="managed")
        c = _calls(log)
        check("C8 already running before CD.1: marked, nothing changed (no primer, no capture, no start)",
              os.path.exists(fsf) and _idx(c, r"prime_ramp") == -1 and not any(x.startswith("data_capture") for x in c)
              and _idx(c, r"sudo systemctl (start|restart|enable)") == -1, f"{c}")

    # ── C9: item 14 ──────────────────────────────────────────────────────────────────────────────────
    def item14(guard_rc, answers):
        with tempfile.TemporaryDirectory() as tmp:
            log, bot, bindir = _world(tmp, guard_rc=guard_rc)
            r, _, ccf = _run_configure(tmp, "ask_yn() { return 0; }; change_data_capture", bot, bindir,
                                       stdin=answers)
            c = _calls(log)
            return (open(ccf).read().strip() if os.path.exists(ccf) else None), c, r
    a, ca, _ = item14(0, "")
    b, cb, _ = item14(1, "no\n")
    d, cd, _ = item14(2, "OVERRIDE\n")
    check("C9 item 14 before the first start: clean -> recorded not applied; pusher + no OVERRIDE -> nothing; "
          "unreadable + OVERRIDE -> recorded",
          a == "managed" and not any(x == "data_capture managed" for x in ca)
          and b is None and not any(x == "data_capture managed" for x in cb)
          and d == "managed" and any("capture_guard.py AMD" in x for x in cd),
          f"{a} {b} {d} | {ca} | {cb}")

    # ── C10: capture_guard.scan ──────────────────────────────────────────────────────────────────────
    try:
        import warehouse_source as ws
        import capture_guard as cg

        def env(host):
            return json.dumps({"symbol": "AMD", "src_host": host, "record": {}}).encode()
        objs = {f"{ws.PREFIX}/trades/dt=2026-10-15/sym=AMD/1-a.json": env("ip-other"),
                f"{ws.PREFIX}/candles/dt=2026-10-23/sym=AMD/interval=1m/2-b.json": env("ip-me")}
        rc1, l1 = cg.scan("AMD", "ip-me", s3=ws._FakeS3(objs), today=date(2026, 10, 24))
        rc0, l0 = cg.scan("AMD", "ip-me", s3=ws._FakeS3({k: v for k, v in objs.items() if "2-b" in k}),
                          today=date(2026, 10, 24))

        class Boom:
            def get_paginator(self, _):
                raise RuntimeError("denied")
        rc2, l2 = cg.scan("AMD", "ip-me", s3=Boom(), today=date(2026, 10, 24))
        check("C10 guard: another host -> rc 1 naming host + date; only this host -> rc 0; error -> rc 2",
              rc1 == 1 and "ip-other" in l1[0] and "2026-10-15" in l1[0] and "9 day(s) ago" in l1[0]
              and rc0 == 0 and rc2 == 2, f"{rc1} {l1} | {rc0} {l0} | {rc2} {l2}")
    except Exception as exc:                                    # noqa: BLE001
        check("C10 guard importable and behaves", False, f"{type(exc).__name__}: {exc}")

    # ── C11: item 1 runs the primer only after the first start ───────────────────────────────────────
    def item1(marker):
        with tempfile.TemporaryDirectory() as tmp:
            log, bot, bindir = _world(tmp)
            open(os.path.join(tmp, "feed.unit"), "w").write("Environment=OT_INSTRUMENT=AMD\n")
            script = (f'FEED_UNIT_FILE="{tmp}/feed.unit"; set_env() {{ :; }}; reload_daemon() {{ :; }}; '
                      'python3() { echo "AMD NVDA"; }; change_instrument')
            _run_configure(tmp, script, bot, bindir, marker=marker, stdin="NVDA\n")
            return _calls(log)
    after, before = item1("2026-10-24T20:00:00Z"), item1(None)
    check("C11 item 1: the primer runs after the first start, not before it",
          _idx(after, r"prime_ramp.py --apply") > -1 and _idx(before, r"prime_ramp") == -1, f"{after} | {before}")

    # ── C14-C16: the safe switch on a MANAGED box (ruling 7) ─────────────────────────────────────────
    def switch(drain="OK", guard_rc=0, answer=""):
        with tempfile.TemporaryDirectory() as tmp:
            log, bot, bindir = _world(tmp, capture="managed", drain=drain, guard_rc=guard_rc)
            open(os.path.join(tmp, "feed.unit"), "w").write("Environment=OT_INSTRUMENT=AMD\n")
            open(os.path.join(bot, "trades.db"), "w").write("x")
            script = (f'FEED_UNIT_FILE="{tmp}/feed.unit"; set_env() {{ echo "set_env $*" >> "{log}"; }}; '
                      'reload_daemon() { :; }; python3() { echo "AMD NVDA"; }; change_instrument')
            r, _, _ = _run_configure(tmp, script, bot, bindir, marker="2026-10-24T20:00:00Z", stdin="NVDA\n" + answer)
            return (_calls(log), os.path.exists(os.path.join(tmp, "push_paused")),
                    os.path.exists(os.path.join(bot, "trades.db")), r)
    c, paused, db, r = switch()
    i_dr, i_set = _idx(c, r"push OT_INSTRUMENT=AMD .*--verify"), _idx(c, r"set_env OT_INSTRUMENT NVDA")
    check("C14 managed switch: drain as the OLD symbol BEFORE the unit changes; guard clean -> not paused; db wiped after",
          -1 < i_dr < i_set and not paused and not db and _idx(c, r"capture_guard.py") > i_set
          and _idx(c, r"data_capture managed") > i_set, f"{c} paused {paused} db {db}")
    c, paused, db, r = switch(drain="SHORT")
    check("C15 the OLD drain is not OK: switch REFUSED - no unit change, no db wipe, named",
          _idx(c, r"set_env") == -1 and db and "SWITCH REFUSED" in r.stdout, f"{c}\n{r.stdout[-200:]}")
    c1, p1, _, _ = switch(guard_rc=1, answer="no\n")
    c2, p2, _, _ = switch(guard_rc=2, answer="OVERRIDE\n")
    check("C16 another pusher of the NEW symbol, no OVERRIDE -> push PAUSED (flag written); OVERRIDE -> not paused",
          p1 and not p2 and _idx(c1, r"data_capture managed") > -1, f"{p1} {p2} {c1}")

    # ── C17: s3_push honours the pause flag from every entrypoint; own_symbol falls back to the bot unit ──────
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("s3p", os.path.join(ROOT, "warehouse", "s3_push.py"))
        s3p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(s3p)
        import contextlib, io
        with tempfile.TemporaryDirectory() as tmp:
            flag = os.path.join(tmp, "push_paused")
            open(flag, "w").write("sym=NVDA: test")
            s3p.PAUSE_FLAG, s3p.ENABLED = flag, True
            touched = []
            s3p.discover = lambda *a, **k: touched.append("discover") or []
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = s3p.main(["--verify"])
            out = buf.getvalue()
            import utils.instrument as ui
            saved_env, saved_fn = os.environ.pop("OT_INSTRUMENT", None), ui._from_bot_unit
            ui._from_bot_unit = lambda: "NVDA"
            try:
                sym = s3p.own_symbol()
            finally:
                ui._from_bot_unit = saved_fn
                if saved_env is not None:
                    os.environ["OT_INSTRUMENT"] = saved_env
        check("C17 s3_push: a paused box pushes nothing (--verify prints DRAIN ... PAUSED); own_symbol = the bot unit's",
              rc == 0 and not touched and "PAUSED" in out and re.search(r"^DRAIN .* PAUSED$", out, re.M) and sym == "NVDA",
              f"rc {rc} touched {touched} sym {sym}\n{out}")
    except Exception as exc:                                    # noqa: BLE001
        check("C17 s3_push pause flag + own_symbol", False, f"{type(exc).__name__}: {exc}")

    # ── C12: banner ──────────────────────────────────────────────────────────────────────────────────
    outs = []
    for mk in (None, "2026-10-24T20:00:00Z"):
        with tempfile.TemporaryDirectory() as tmp:
            log, bot, bindir = _world(tmp)
            r, _, _ = _run_configure(tmp, "print_banner", bot, bindir, marker=mk)
            outs.append(r.stdout)
    check("C12 the banner names the first start: PENDING before, done after",
          "First start: PENDING" in outs[0] and "First start: done 2026-10-24T20:00:00Z" in outs[1], f"{outs}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(sorted(set(FAILED))))
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
