#!/usr/bin/env python3
"""tests/check_telegram_queue.py — v5.0
v5.0  2026-10-26  (TG.1) — new. TELEGRAM NEVER BLOCKS THE CALLER, AND A FAILED ALERT IS RETRIED, NOT LOST.
      2026-10-26, first OTV5 paper session: 70 of 95 fleet alerts failed 09:15-10:00 ET (read timeout=10 and HTTP 429)
      and each failure stalled the trading loop 10 s; on SPX a Runaway hard stop was reached two stalls late and filled
      at -34% against a -20% stop. notifications/telegram_sender.py v5.1 queues to one daemon courier that retries.

🔑 IT DRIVES THE REAL TelegramSender AND ITS REAL COURIER. Only the network edge is faked: requests.post is replaced by
a scripted fake (per message text: sleep, 429 with retry_after, ReadTimeout, 400, 200), and the three credential
getters inside the module. NO NETWORK CALL IS MADE. The delivery constants are module globals the courier reads at
use time, so the 15-minute deadline and the backoff are shrunk here instead of slept through. A hard 90 s budget
(a timer that flushes and os._exit's) means a stuck worker cannot hang the sweep.

  T7  a disabled sender (no token/chat) returns False and starts no courier thread           (run first)
  T8  send_sync is ONE blocking POST: returns after the fake's 0.5 s, False on a 429, one call; True on a 200
  T1  send() returns within 50 ms while the fake POST sleeps 2 s, returns True, and the message is delivered
  T2  a 429 with parameters.retry_after=1 is retried after >= 1 s and then delivered
  T3  a ReadTimeout is retried and delivered
  T4  FIFO: A (two timeouts), B (a 429), C (clean) are delivered A, B, C
  T5  a 400 is dropped at ERROR after ONE attempt; T5b the next message is still delivered
  T6  a message that never succeeds is DROPPED at ERROR once the (shrunk) deadline passes; T6b the next still goes
  T10 on_result is called EXACTLY ONCE per accepted message with the honest verdict: delivered (True), dropped at the
      deadline, dropped as not retryable, dropped by a full queue (False each), and undelivered at exit (T9c, False)
  T11 an on_result that RAISES is logged at ERROR and the courier keeps delivering
  T12 a 400 "can't parse entities" is resent ONCE as plain text (no parse_mode, entities unescaped) and delivered;
      T12b if the plain resend fails too, the alert is dropped at ERROR after exactly two POSTs
  T9  at interpreter exit the queue is drained: a child process that queues one alert (POST takes 0.5 s) and exits
      normally still delivers it; T9b a child whose POST always times out still exits, within the 5 s drain + slack

Born red on v5.0 (5387033): T1 T2 T3 T4 T5 T6 T8 T9c T10 T11 T12 (send() posts synchronously, once; there is no send_sync).
Run:  python3 tests/check_telegram_queue.py
"""
import logging
import os
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BUDGET_S = 90

_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}", flush=True)
    if not ok:
        _fails.append(tag)


def _bail():
    print(f"  FAIL  BUDGET  the gate exceeded its {BUDGET_S}s budget — a worker is stuck", flush=True)
    sys.stdout.flush()
    os._exit(1)


_watchdog = threading.Timer(BUDGET_S, _bail)
_watchdog.daemon = True
_watchdog.start()

import requests                                                     # noqa: E402
import notifications.telegram_sender as TS                          # noqa: E402


# ── the network edge, scripted ──────────────────────────────────────────────
class _Resp:
    def __init__(self, code, body):
        self.status_code, self._body = code, body
        self.text = repr(body)

    def json(self):
        return self._body


SCRIPT = {}          # message text -> list of actions, consumed one per POST; empty -> 200
CALLS = []           # (t, text, action) for every POST
DELIVERED = []       # texts answered 200, in order
_lock = threading.Lock()


def _fake_post(url, json=None, timeout=None, **_kw):
    text = (json or {}).get("text", "")
    with _lock:
        acts = SCRIPT.get(text) or []
        act = acts.pop(0) if acts else "ok"
        CALLS.append((time.time(), text, act, timeout, dict(json or {})))
    if act.startswith("sleep"):
        time.sleep(float(act[5:]))
        act = "ok"
    if act == "timeout":
        time.sleep(0.05)
        raise requests.exceptions.ReadTimeout(
            "HTTPSConnectionPool(host='api.telegram.org', port=443): Read timed out. (read timeout=10)")
    if act.startswith("429"):
        n = int(act.split(":")[1])
        return _Resp(429, {"ok": False, "error_code": 429, "description": f"Too Many Requests: retry after {n}",
                           "parameters": {"retry_after": n}})
    if act == "400":
        return _Resp(400, {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"})
    if act == "400p":
        return _Resp(400, {"ok": False, "error_code": 400,
                           "description": "Bad Request: can't parse entities: Unsupported start tag"})
    with _lock:
        DELIVERED.append(text)
    return _Resp(200, {"ok": True})


requests.post = _fake_post
TS.requests.post = _fake_post


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.rows = []

    def emit(self, rec):
        self.rows.append((rec.levelno, rec.getMessage()))


CAP = _Cap()
_lg = logging.getLogger("notifications.telegram_sender")
_lg.addHandler(CAP)
_lg.setLevel(logging.DEBUG)
_lg.propagate = False


def _creds(on):
    TS.telegram_configured = (lambda: True) if on else (lambda: False)
    TS.get_telegram_token = (lambda: "T0K") if on else (lambda: "")
    TS.get_telegram_chat_id = (lambda: "C1") if on else (lambda: "")


def _wait(pred, t):
    end = time.time() + t
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


def _courier_threads():
    return [t for t in threading.enumerate() if t.name == "telegram-courier"]


def _errors(sub):
    return [m for lv, m in CAP.rows if lv >= logging.ERROR and sub in m]


_CHILD = r"""
import sys, time
sys.path.insert(0, %r)
import requests, notifications.telegram_sender as TS
ACT = %r
class R:
    status_code = 200
    text = "ok"
def post(url, json=None, timeout=None, **k):
    if ACT == "timeout":
        time.sleep(0.2)
        raise requests.exceptions.ReadTimeout("Read timed out.")
    time.sleep(float(ACT[5:]))
    print("DELIVERED child", flush=True)
    return R()
TS.requests.post = post
TS.telegram_configured = lambda: True
TS.get_telegram_token = lambda: "T0K"
TS.get_telegram_chat_id = lambda: "C1"
TS.BACKOFF_START_S = 0.2
TS.BACKOFF_CAP_S = 0.4
snd = TS.TelegramSender()
try:
    snd.send("child shutdown alert", on_result=lambda d, why: print("RESULT", d, why, flush=True))
except TypeError:
    snd.send("child shutdown alert")
sys.exit(0)
"""


def main():
    TS.BACKOFF_START_S = 0.2                 # read at use time by v5.1; harmless on v5.0
    TS.BACKOFF_CAP_S = 0.4

    # ── T7 disabled ─────────────────────────────────────────────────────────
    _creds(False)
    s0 = TS.TelegramSender()
    r = s0.send("T7 disabled")
    time.sleep(0.1)
    ck("T7 disabled send() returns False, makes no POST, starts no courier thread",
       r is False and not CALLS and not _courier_threads(),
       f"returned={r!r} posts={len(CALLS)} threads={len(_courier_threads())}")

    _creds(True)
    s = TS.TelegramSender()

    # ── T8 send_sync ────────────────────────────────────────────────────────
    ss = getattr(s, "send_sync", None)
    if ss is None:
        ck("T8 send_sync exists and is ONE blocking POST", False, "TelegramSender has no send_sync")
    else:
        SCRIPT["T8 a"] = ["sleep0.5"]
        SCRIPT["T8 b"] = ["429:1", "ok"]
        n0 = len(CALLS)
        t0 = time.time(); ra = ss("T8 a", timeout=3); da = time.time() - t0
        t0 = time.time(); rb = ss("T8 b"); db = time.time() - t0
        n_b = len([c for c in CALLS[n0:] if c[1] == "T8 b"])
        time.sleep(1.3)                      # a hidden retry of "T8 b" would land here
        n_b2 = len([c for c in CALLS if c[1] == "T8 b"])
        to = [c[3] for c in CALLS[n0:] if c[1] == "T8 a"]
        ck("T8 send_sync blocks for the POST and returns True on a 200 (timeout passed through)",
           ra is True and da >= 0.45 and to == [3], f"returned={ra!r} took={da:.2f}s timeouts={to}")
        ck("T8 send_sync on a 429 returns False after ONE attempt, no retry, no queue",
           rb is False and n_b == 1 and n_b2 == 1 and db < 0.5, f"returned={rb!r} posts={n_b}->{n_b2} took={db:.2f}s")

    # ── T1 non-blocking ─────────────────────────────────────────────────────
    SCRIPT["T1 slow"] = ["sleep2"]
    t0 = time.time(); r = s.send("T1 slow"); dt = time.time() - t0
    ck("T1 send() returns within 50 ms while the POST sleeps 2 s, and returns True",
       dt < 0.05 and r is True, f"took={dt*1000:.0f}ms returned={r!r}")
    ok = _wait(lambda: "T1 slow" in DELIVERED, 4)
    ck("T1 ...and the message is then delivered", ok, f"delivered={DELIVERED}")

    # ── T2 429 retry_after ──────────────────────────────────────────────────
    SCRIPT["T2 rate"] = ["429:1"]
    s.send("T2 rate")
    ok = _wait(lambda: "T2 rate" in DELIVERED, 4)
    ts = [c[0] for c in CALLS if c[1] == "T2 rate"]
    gap = (ts[1] - ts[0]) if len(ts) >= 2 else 0.0
    ck("T2 a 429 retry_after=1 is retried after >= 1 s, then delivered",
       ok and len(ts) == 2 and gap >= 0.95, f"delivered={ok} posts={len(ts)} gap={gap:.2f}s")

    # ── T3 timeout retry ────────────────────────────────────────────────────
    SCRIPT["T3 timeout"] = ["timeout"]
    s.send("T3 timeout")
    ok = _wait(lambda: "T3 timeout" in DELIVERED, 4)
    n = len([c for c in CALLS if c[1] == "T3 timeout"])
    ck("T3 a ReadTimeout is retried and delivered", ok and n == 2, f"delivered={ok} posts={n}")

    # ── T4 FIFO across retries ──────────────────────────────────────────────
    SCRIPT["T4 A"] = ["timeout", "timeout"]
    SCRIPT["T4 B"] = ["429:1"]
    for m in ("T4 A", "T4 B", "T4 C"):
        s.send(m)
    ok = _wait(lambda: "T4 C" in DELIVERED, 6)
    order = [d for d in DELIVERED if d.startswith("T4")]
    ck("T4 FIFO is kept across retries: A, B, C", ok and order == ["T4 A", "T4 B", "T4 C"], f"order={order}")

    # ── T5 400 not retryable ────────────────────────────────────────────────
    SCRIPT["T5 bad"] = ["400", "ok"]
    s.send("T5 bad")
    s.send("T5 next")
    ok = _wait(lambda: "T5 next" in DELIVERED, 4)
    n = len([c for c in CALLS if c[1] == "T5 bad"])
    ck("T5 a 400 is dropped after ONE attempt with an ERROR log",
       n == 1 and "T5 bad" not in DELIVERED and bool(_errors("T5 bad")), f"posts={n} errors={_errors('T5 bad')}")
    ck("T5b the next message is still delivered", ok, f"delivered={DELIVERED[-3:]}")

    # ── T6 deadline ─────────────────────────────────────────────────────────
    saved = getattr(TS, "DELIVERY_DEADLINE_S", None)
    TS.DELIVERY_DEADLINE_S = 1.5
    SCRIPT["T6 never"] = ["timeout"] * 1000
    t0 = time.time()
    s.send("T6 never")
    s.send("T6 next")
    ok = _wait(lambda: "T6 next" in DELIVERED, 6)
    dt = time.time() - t0
    drops = [m for m in _errors("DROPPED after") if "T6 never" in m]
    n = len([c for c in CALLS if c[1] == "T6 never"])
    ck("T6 a message that never succeeds is retried, then DROPPED at ERROR at the deadline",
       len(drops) == 1 and n >= 2 and "T6 never" not in DELIVERED and dt >= 1.4, f"drops={drops} posts={n} t={dt:.2f}s")
    ck("T6b the next message is still delivered after the drop", ok, f"delivered={DELIVERED[-3:]}")
    if saved is not None:
        TS.DELIVERY_DEADLINE_S = saved

    # ── T10 on_result exactly once, honest verdicts ─────────────────────────
    R = []
    def rec(tag):
        return lambda d, why: R.append((tag, d, why))
    def send_cb(msg, tag):
        try:
            return s.send(msg, on_result=rec(tag))
        except TypeError:
            return s.send(msg)
    TS.DELIVERY_DEADLINE_S = 1.0
    SCRIPT["T10 dl"] = ["timeout"] * 1000
    SCRIPT["T10 bad"] = ["400"]
    send_cb("T10 ok", "ok")
    send_cb("T10 dl", "dl")
    send_cb("T10 bad", "bad")
    _wait(lambda: len(R) >= 3, 5)
    if saved is not None:
        TS.DELIVERY_DEADLINE_S = saved
    # overflow: hold the courier on a 1 s POST, then overfill a 2-slot queue
    saved_q = getattr(TS, "QUEUE_MAX", None)
    TS.QUEUE_MAX = 2
    SCRIPT["T10 hold"] = ["sleep1"]
    send_cb("T10 hold", "hold")
    time.sleep(0.2)
    send_cb("T10 q1", "q1"); send_cb("T10 q2", "q2"); send_cb("T10 q3", "q3")
    _wait(lambda: len(R) >= 7, 5)
    if saved_q is not None:
        TS.QUEUE_MAX = saved_q
    time.sleep(0.3)
    by = {}
    for tag, d, why in R:
        by.setdefault(tag, []).append((d, why))
    want = {"ok": True, "dl": False, "bad": False, "hold": True, "q1": False, "q2": True, "q3": True}
    once = all(len(by.get(k, [])) == 1 for k in want)
    right = once and all(by[k][0][0] is v for k, v in want.items())
    why_ok = once and "deadline" in by["dl"][0][1] and "not retryable" in by["bad"][0][1] \
        and "queue full" in by["q1"][0][1]
    ck("T10 on_result fires exactly once per message: delivered / deadline / not retryable / queue overflow",
       right and why_ok, f"{by}")

    # ── T11 a raising callback does not kill the courier ────────────────────
    def boom(d, why):
        raise ValueError("callback boom")
    try:
        s.send("T11 boom", on_result=boom)
    except TypeError:
        s.send("T11 boom")
    s.send("T11 after")
    ok = _wait(lambda: "T11 after" in DELIVERED, 4)
    ck("T11 an on_result that raises is logged at ERROR and the courier keeps going",
       ok and bool(_errors("callback raised")), f"delivered={ok} errors={_errors('callback raised')}")

    # ── T12 can't parse entities -> one plain-text resend ───────────────────
    SCRIPT["T12 a &lt;b&gt;"] = ["400p"]
    s.send("T12 a &lt;b&gt;")
    ok = _wait(lambda: "T12 a <b>" in DELIVERED, 4)
    posts = [c for c in CALLS if c[1] in ("T12 a &lt;b&gt;", "T12 a <b>")]
    ck("T12 a 400 can't parse entities is resent ONCE as plain text (no parse_mode, unescaped) and delivered",
       ok and len(posts) == 2 and posts[0][4].get("parse_mode") == "HTML" and "parse_mode" not in posts[1][4],
       f"delivered={ok} posts={[(c[1], c[4].get('parse_mode')) for c in posts]}")
    SCRIPT["T12 b &amp;"] = ["400p"]
    SCRIPT["T12 b &"] = ["400p"]
    s.send("T12 b &amp;")
    s.send("T12 next")
    ok = _wait(lambda: "T12 next" in DELIVERED, 4)
    posts = [c for c in CALLS if c[1] in ("T12 b &amp;", "T12 b &")]
    ck("T12b if the plain resend also fails, it is dropped at ERROR after exactly two POSTs",
       ok and len(posts) == 2 and bool(_errors("not retryable")) and "T12 b &" not in DELIVERED,
       f"posts={len(posts)}")

    # ── T9 atexit drain, bounded ────────────────────────────────────────────
    for tag, act, want in (("T9", "sleep0.5", True), ("T9b", "timeout", False)):
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, "-c", _CHILD % (ROOT, act)], capture_output=True, text=True,
                               timeout=15, env=dict(os.environ))
            out, rc = p.stdout, p.returncode
        except subprocess.TimeoutExpired:
            out, rc = "", "HUNG"
        dt = time.time() - t0
        got = "DELIVERED child" in out
        if not want:
            ck("T9c ...and its on_result is told, once: False, undelivered at exit",
               out.count("RESULT ") == 1 and "RESULT False undelivered at exit" in out, f"out={out.strip()[-120:]!r}")
        if want:
            ck("T9 a child that queues one alert and exits normally still delivers it (atexit drain)",
               got and rc == 0, f"delivered={got} rc={rc} t={dt:.1f}s")
        else:
            ck("T9b a child whose POST always times out still exits, bounded by the drain",
               not got and rc == 0 and dt < 12, f"rc={rc} t={dt:.1f}s")

    fl = getattr(TS, "flush", None)
    if fl:
        fl(2)
    print(f"\n{'RED' if _fails else 'GREEN'}: {len(_fails)} failed {_fails if _fails else ''}", flush=True)
    return 1 if _fails else 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:                                          # noqa: BLE001
        print(f"  FAIL  CRASH  {type(e).__name__}: {e}", flush=True)
        rc = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)
