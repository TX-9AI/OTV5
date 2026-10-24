#!/usr/bin/env python3
"""
tests/check_emergency_watchdog.py  v1.0 — the r168 emergency watchdog (EXP.1 item 3).

v1.0  2026-09-27  OTV4TEST r168 — born with WDOG.1: one message per event (the operator's ruling).

Drives the REAL tools/emergency_watchdog.run_once / emergency_close / health
against a recording fake world (clock, service, heartbeat, positions, pager,
stop/start, cancel, flatten), the REAL main._touch_heartbeat on a scratch path,
the REAL Real.load_env / open_positions / flatten_pass / status with their I/O
replaced, and the REAL installer with sudo stubbed. Nothing reaches systemd,
Telegram, the broker or a live store.

  W0  outside 09:30-16:05, or not a trading day: nothing is read or sent
  W1  healthy with a position: no page, no stop
  W2  unhealthy and FLAT: no page (ruled: positions only)
  W3  unhealthy with a position BEFORE 15:50: silent all morning, no stop (the bot's own alerts cover it)
  W4  recovery: silent, state cleared
  W5  15:50 paper: stop -> flatten until flat -> ONE page naming each close + P&L; no cancel, no restart
  W6  live: working orders cancelled AFTER the stop and BEFORE the first flatten; one page
  W7  the bot will not stop: NOTHING sent (no cancel, no flatten), ONE close-by-hand page
  W8  never flat: the loop ends at 16:00, ONE page saying what is still open
  W9  once a day: a second episode inside 15:50-16:00 neither closes nor pages
  W10 a HEALTHY bot at 15:52 with a position is never stopped
  W11 health: boot grace, stale/fresh heartbeat edges, a non-active service
  W12 main._touch_heartbeat writes tick + time, never raises, and main_loop calls it first
  W13 load_env parses systemd's Environment (quoted spaces), REMOVES the Telegram pair from this
      process (the bot's code here cannot page) and keeps it for the watchdog; --status prints no value
  W14 open_positions reads only this mode's open rows; outcomes reads each close's P&L
  W15 flatten_pass never reassigns the manager's open records (a live walk's order id rides there)
  W16 the installer renders a weekday per-minute oneshot as ubuntu; setup_ec2's suite installs it
  W17 the real page posts ONCE with the kept pair; the real stop is SIGKILL then stop (no SIGTERM page)
  W18 ONE EVENT, ONE MESSAGE: stuck from 09:30 with a position, minute by minute to 16:04 = exactly 1 page

Run:  python3 tests/check_emergency_watchdog.py
"""
import contextlib
import datetime as dt
import glob as _glob
import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import types
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    sys.path.insert(1, _sp)

ET = ZoneInfo("America/New_York")
FAILS = []


def ck(name, ok, det=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {det}" if det else ""))
    if not ok:
        FAILS.append(name)


try:
    import tools.emergency_watchdog as W
except Exception as exc:                                          # noqa: BLE001
    print(f"  FAIL  W*  tools/emergency_watchdog.py does not import: {type(exc).__name__}: {exc}")
    sys.exit(1)


class Fake:
    def __init__(self, hm=(10, 0), svc="active", hb=10.0, age=5000.0, opened=("Breakout aaaa1111",),
                 paper=True, trading=True, stop_ok=True, flat_after=1, day=dt.date(2026, 9, 28)):
        self.t = dt.datetime.combine(day, dt.time(*hm), tzinfo=ET)
        self.svc, self.hb, self.age = svc, hb, age
        self.opened, self._paper, self.trading = list(opened), paper, trading
        self.stop_ok, self.flat_after = stop_ok, flat_after
        self.calls, self.pages, self.st, self.passes, self.closed = [], [], {}, 0, set()

    def now(self): return self.t
    def advance(self, s): self.t += dt.timedelta(seconds=s)
    def trading_day(self, d): return self.trading
    def load_env(self): self.calls.append("env"); return {}
    def service_state(self): return self.svc
    def process_age_s(self): return self.age
    def heartbeat_age_s(self): return self.hb
    def paper(self): return self._paper
    def open_positions(self): self.calls.append("read"); return list(self.opened)
    def outcomes(self, opened):
        return [f"{o} -120" if o.split()[-1] in self.closed else f"{o} STILL OPEN" for o in opened]
    def page(self, m): self.calls.append("page"); self.pages.append(m); return True
    def stop_bot(self):
        self.calls.append("stop")
        if self.stop_ok:
            self.svc = "inactive"
        return self.stop_ok
    def cancel_working(self): self.calls.append("cancel"); return 2
    def flatten_pass(self):
        self.calls.append("flatten"); self.passes += 1
        if self.flat_after is not None and self.passes >= self.flat_after:
            self.closed |= {o.split()[-1] for o in self.opened}
            self.opened = []
        return [o.split()[-1] for o in self.opened]
    def sleep(self, s): self.calls.append("sleep"); self.advance(s)
    def load_state(self): return dict(self.st)
    def save_state(self, st): self.st = dict(st)


def two_runs(f):
    a = W.run_once(f); f.advance(60); b = W.run_once(f)
    return a, b


print("check_emergency_watchdog — r168")

# W0
f = Fake(hm=(9, 29), svc="failed"); v = W.run_once(f)
g = Fake(hm=(10, 0), svc="failed", trading=False); v2 = W.run_once(g)
h = Fake(hm=(16, 5), svc="failed"); v3 = W.run_once(h)
ck("W0  outside the window / not a trading day: idle, nothing read or sent",
   (v, v2, v3) == ("idle",) * 3 and not (f.calls or g.calls or h.calls), f"{v} {v2} {v3} {f.calls + g.calls + h.calls}")

# W1
f = Fake(); a, b = two_runs(f)
ck("W1  healthy with a position: no page, no stop", (a, b) == ("ok", "ok") and "page" not in f.calls and "stop" not in f.calls,
   f"{a} {b} {f.calls}")

# W2
f = Fake(svc="failed", opened=()); a, b = two_runs(f)
ck("W2  unhealthy and FLAT: no page (positions only)", (a, b) == ("flat", "flat") and not f.pages, f"{a} {b} {f.pages}")

# W3
f = Fake(hm=(10, 0), svc="failed"); vs = []
for _ in range(30):
    vs.append(W.run_once(f)); f.advance(60)
ck("W3  unhealthy with a position before 15:50: silent, no stop",
   not f.pages and "stop" not in f.calls and vs[0] == "watching" and set(vs[1:]) == {"unhealthy"}, f"pages={len(f.pages)} {set(vs)}")

# W4
f.svc = "active"; d = W.run_once(f)
ck("W4  recovery: silent, state cleared", d == "ok" and not f.pages and "unhealthy_since" not in f.st, f"{d} {f.st}")

# W5
f = Fake(hm=(15, 49), svc="failed", flat_after=3); a = W.run_once(f); f.advance(60); b = W.run_once(f)
seq = [c for c in f.calls if c in ("stop", "cancel", "flatten", "page")]
ok = (a == "watching" and b == "closed" and seq == ["stop", "flatten", "flatten", "flatten", "page"]
      and len(f.pages) == 1 and "Breakout aaaa1111 -120" in f.pages[0] and "FLAT" in f.pages[0]
      and "stays stopped" in f.pages[0])
ck("W5  15:50 paper: stop, flatten until flat, ONE page with each close; no cancel, no restart", ok,
   f"{a} {b} {seq} {f.pages[-1][:160] if f.pages else ''}")

# W6
f = Fake(hm=(15, 50), svc="active", hb=900, paper=False); a, b = two_runs(f)
seq = [c for c in f.calls if c in ("stop", "cancel", "flatten", "page")]
ck("W6  live: stop, cancel, flatten, ONE page",
   b == "closed" and seq == ["stop", "cancel", "flatten", "page"] and "LIVE" in f.pages[0], f"{b} {seq}")

# W7
f = Fake(hm=(15, 50), svc="failed", paper=False, stop_ok=False); a, b = two_runs(f)
ck("W7  bot will not stop: nothing sent, ONE close-by-hand page",
   b == "stop_failed" and "cancel" not in f.calls and "flatten" not in f.calls and len(f.pages) == 1
   and "WOULD NOT STOP" in f.pages[0] and "BY HAND" in f.pages[0], f"{b} {f.calls}")

# W8
f = Fake(hm=(15, 57), svc="failed", flat_after=None); a, b = two_runs(f)
ck("W8  never flat: ends at 16:00, ONE page naming what is still open",
   b == "incomplete" and f.t.time() >= dt.time(16, 0) and len(f.pages) == 1
   and "STILL OPEN" in f.pages[0] and "BY HAND" in f.pages[0], f"{b} {f.t.time()} pages={len(f.pages)}")

# W9
f = Fake(hm=(15, 49), svc="failed", flat_after=1); a, b = two_runs(f)          # closes by 15:50
f.advance(60); f.svc = "active"; W.run_once(f)                                   # the operator brings it back
f.svc = "failed"; f.opened = ["VOLT bbbb2222"]; f.passes = 0
f.advance(60); c = W.run_once(f); f.advance(60); d = W.run_once(f)               # a new episode, 15:52-15:53
ck("W9  once a day: a second episode inside 15:50-16:00 neither closes nor pages",
   b == "closed" and f.t.time() < dt.time(16, 0) and f.calls.count("stop") == 1 and len(f.pages) == 1
   and d == "unhealthy", f"{b} {c} {d} at {f.t.time()} stops={f.calls.count('stop')} pages={len(f.pages)}")

# W10
f = Fake(hm=(15, 52), svc="active", hb=12); a, b = two_runs(f); f.advance(60); c = W.run_once(f)
ck("W10 a healthy bot at 15:52 with a position is never stopped", "stop" not in f.calls and not f.pages, f"{f.calls}")

# W11
cases = [
    (dict(svc="active", age=60.0, hb=None), True, "boot grace"),
    (dict(svc="active", age=5000.0, hb=None), False, "no heartbeat"),
    (dict(svc="active", age=5000.0, hb=W.STALE_S + 1), False, "stale"),
    (dict(svc="active", age=5000.0, hb=W.STALE_S - 1), True, "fresh"),
    (dict(svc="activating", age=10.0, hb=5.0), False, "not active"),
    (dict(svc="active", age=None, hb=30.0), True, "age unknown, fresh"),
]
bad = [lbl for kw, want, lbl in cases if W.health(Fake(**kw))[0] != want]
ck("W11 health edges (boot grace, 180s, service state)", not bad, f"wrong: {bad}")

# W12
try:
    import main as M
    with tempfile.TemporaryDirectory() as td:
        M._HEARTBEAT = os.path.join(td, "BOT_HEARTBEAT")
        M._touch_heartbeat(41)
        body = open(M._HEARTBEAT).read().split()
        M._HEARTBEAT = os.path.join(td, "no", "such", "dir", "HB")
        raised = False
        try:
            M._touch_heartbeat(42); M._touch_heartbeat(43)
        except Exception:                                         # noqa: BLE001
            raised = True
    import inspect
    src = inspect.getsource(M.main_loop)
    first = src.index("_touch_heartbeat(") < src.index("try:")
    ck("W12 heartbeat: writes, never raises, first thing in the loop",
       body[1] == "41" and abs(float(body[0]) - __import__("time").time()) < 5 and not raised and first,
       f"body={body} raised={raised} first={first}")
except Exception as exc:                                          # noqa: BLE001
    ck("W12 heartbeat: writes, never raises, first thing in the loop", False, f"{type(exc).__name__}: {exc}")

# W13
r = W.Real()
raw = 'OT_INSTRUMENT=QQQ "OT_BOT_NAME=Options Trader QQQ" OT_PAPER_TRADING=True TELEGRAM_TOKEN=SEKRET123 TELEGRAM_CHAT_ID=987654'
saved = {k: os.environ.get(k) for k in ("OT_INSTRUMENT", "OT_BOT_NAME", "OT_PAPER_TRADING", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID")}
r._sysctl = lambda *a: raw if a[:1] == ("show",) and "Environment" in a else ("active" if a[:1] == ("is-active",) else "0")
r.heartbeat_age_s = lambda: 5.0
r.open_positions = lambda: []
r.load_state = lambda: {}
os.environ["TELEGRAM_TOKEN"] = "INHERITED"; os.environ["TELEGRAM_CHAT_ID"] = "INHERITED"   # already in this process
env = r.load_env()
tg_gone = "TELEGRAM_TOKEN" not in os.environ and "TELEGRAM_CHAT_ID" not in os.environ
try:
    import config as _cfg
    bot_can_page = bool(_cfg.telegram_configured())
except Exception as exc:                                          # noqa: BLE001
    bot_can_page = f"config unreadable: {type(exc).__name__}"
kept = r._tg == {"TELEGRAM_TOKEN": "SEKRET123", "TELEGRAM_CHAT_ID": "987654"}
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    W.status(r)
out = buf.getvalue()
for k, v in saved.items():
    if v is None:
        os.environ.pop(k, None)
    else:
        os.environ[k] = v
ck("W13 env parsed; the Telegram pair leaves this process and stays with the watchdog; --status prints no value",
   env.get("OT_BOT_NAME") == "Options Trader QQQ" and tg_gone and bot_can_page is False and kept
   and "SEKRET123" not in out and "987654" not in out and "telegram set" in out,
   f"gone={tg_gone} bot_can_page={bot_can_page} kept={kept} | " + out.replace("\n", " | ")[:160])

# W14
with tempfile.TemporaryDirectory() as td:
    db = os.path.join(td, "t.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE trades (trade_id TEXT, strategy TEXT, status TEXT, paper_trade INTEGER, pnl_usd REAL)")
    con.executemany("INSERT INTO trades VALUES (?,?,?,?,?)", [
        ("p-open-1", "Breakout", "open", 1, None), ("p-closed-9", "VOLT", "closed", 1, -412.5),
        ("l-open-1", "ORBStrategy", "open", 0, None)])
    con.commit(); con.close()
    old_db, old_pt = os.environ.get("OT_TRADES_DB"), os.environ.get("OT_PAPER_TRADING")
    os.environ["OT_TRADES_DB"] = db
    os.environ["OT_PAPER_TRADING"] = "True"; pap = W.Real().open_positions()
    os.environ["OT_PAPER_TRADING"] = "False"; liv = W.Real().open_positions()
    outs = W.Real().outcomes(["VOLT p-closed", "Breakout p-open-1"])
    for k, v in (("OT_TRADES_DB", old_db), ("OT_PAPER_TRADING", old_pt)):
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
ck("W14 open_positions reads only this mode's open rows; outcomes reads each close's P&L",
   pap == ["Breakout p-open-1"] and liv == ["ORBStrategy l-open-1"]
   and outs == ["VOLT p-closed -412", "Breakout p-open-1 STILL OPEN"], f"paper={pap} live={liv} outs={outs}")

# W15
class _TL:
    def get_open_trades(self): return [{"trade_id": "still-open-xyz"}]
class _PM:
    def __init__(self):
        self._trade_logger = _TL(); self.rec = {"trade_id": "still-open-xyz", "_live_exit_order_id": 77}
        self._open_records = [self.rec]; self.flat_calls = 0
    def has_open_position(self): return True
    def flatten_all(self, reason="", chain=None, spot=None): self.flat_calls += 1; return []
pm = _PM()
saved_mods = {k: sys.modules.get(k) for k in ("execution.position_manager", "data.options_chain")}
sys.modules["execution.position_manager"] = types.SimpleNamespace(get_position_manager=lambda paper: pm)
sys.modules["data.options_chain"] = types.SimpleNamespace(get_chain_fetcher=lambda: (_ for _ in ()).throw(RuntimeError("no feed")))
try:
    with contextlib.redirect_stdout(io.StringIO()):
        left = W.Real().flatten_pass()
finally:
    for k, v in saved_mods.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v
ck("W15 flatten_pass keeps the manager's records (a live walk's order id survives)",
   pm.flat_calls == 1 and pm._open_records[0] is pm.rec and pm.rec.get("_live_exit_order_id") == 77
   and left == ["still-op"], f"calls={pm.flat_calls} left={left}")

# W16
with tempfile.TemporaryDirectory() as td:
    stub = os.path.join(td, "bin"); os.makedirs(stub); out_dir = os.path.join(td, "units"); os.makedirs(out_dir)
    with open(os.path.join(stub, "sudo"), "w") as fh:
        fh.write('#!/bin/bash\nif [ "$1" = tee ]; then cat > "%s/$(basename "$2")"; else echo "sudo $*" >> "%s/cmds"; fi\n' % (out_dir, out_dir))
    with open(os.path.join(stub, "systemctl"), "w") as fh:
        fh.write("#!/bin/bash\nexit 0\n")
    os.chmod(os.path.join(stub, "sudo"), 0o755); os.chmod(os.path.join(stub, "systemctl"), 0o755)
    envx = dict(os.environ, PATH=stub + ":" + os.environ.get("PATH", ""))
    rc = subprocess.run(["bash", os.path.join(ROOT, "deploy", "install_emergency_watchdog.sh")],
                        env=envx, capture_output=True, text=True).returncode
    try:
        svc = open(os.path.join(out_dir, "optbot-emergency-watchdog.service")).read()
        tmr = open(os.path.join(out_dir, "optbot-emergency-watchdog.timer")).read()
        cmds = open(os.path.join(out_dir, "cmds")).read()
    except OSError as exc:
        svc = tmr = cmds = f"missing: {exc}"
exe = [l.split("=", 1)[1] for l in svc.splitlines() if l.startswith("ExecStart=")]
tos = [int(l.split("=", 1)[1]) for l in svc.splitlines() if l.startswith("TimeoutStartSec=")]
suite = [l for l in open(os.path.join(ROOT, "setup_ec2.sh")).read().splitlines() if l.startswith("SUITE=")]
ok = (rc == 0 and "Type=oneshot" in svc and "User=ubuntu" in svc and exe
      and os.path.isfile(exe[0].split()[1]) and exe[0].split()[1].endswith("tools/emergency_watchdog.py")
      and tos and tos[0] >= 900 and "OnCalendar=Mon..Fri *-*-* 09..16:*:00 America/New_York" in tmr
      and "enable --now optbot-emergency-watchdog.timer" in cmds
      and suite and "deploy/install_emergency_watchdog.sh" in suite[0])
ck("W16 installer renders a weekday per-minute oneshot as ubuntu; the suite installs it", ok,
   f"rc={rc} exec={exe} timeout={tos} suite={'yes' if suite and 'emergency' in suite[0] else 'no'}")

# W17
r = W.Real(); r._tg = {"TELEGRAM_TOKEN": "T0K", "TELEGRAM_CHAT_ID": "C1"}
posts, runs = [], []
class _Resp:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False
_orig_open, _orig_run, _orig_sleep = W.urllib.request.urlopen, W.subprocess.run, W.time.sleep
W.urllib.request.urlopen = lambda req, timeout=10: (posts.append(req.full_url), _Resp())[1]
W.subprocess.run = lambda cmd, **kw: (runs.append(" ".join(cmd)), types.SimpleNamespace(stdout="inactive", returncode=0))[1]
W.time.sleep = lambda s: None
try:
    with contextlib.redirect_stdout(io.StringIO()):
        sent = r.page("one message")
        stopped = r.stop_bot()
finally:
    W.urllib.request.urlopen, W.subprocess.run, W.time.sleep = _orig_open, _orig_run, _orig_sleep
sysd = [c for c in runs if "systemctl" in c and ("kill" in c or " stop " in c + " ")]
ck("W17 the real page posts once with the kept pair; the real stop is SIGKILL then stop",
   sent is True and len(posts) == 1 and "/botT0K/" in posts[0] and stopped
   and len(sysd) == 2 and "kill --signal=KILL" in sysd[0] and sysd[1].endswith("stop " + W.SERVICE),
   f"posts={len(posts)} runs={sysd}")

# W18
f = Fake(hm=(9, 30), svc="active", hb=900, flat_after=2)
while f.t.time() < dt.time(16, 5):
    W.run_once(f); f.advance(60)
ck("W18 ONE EVENT, ONE MESSAGE: stuck all day with a position = exactly 1 page, 1 stop",
   len(f.pages) == 1 and f.calls.count("stop") == 1 and "FLAT" in f.pages[0], f"pages={len(f.pages)} stops={f.calls.count('stop')}")

print()
print("FAIL: " + " ".join(FAILS) if FAILS else "PASS")
sys.exit(1 if FAILS else 0)
