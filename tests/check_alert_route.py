#!/usr/bin/env python3
"""
tests/check_alert_route.py  v5.0
v5.0  2026-11-02  OTV5 r71 (PAGE.2) — new. A MANAGED BOX HANDS ITS ALERTS TO CONTROL'S ROUTER; CRITICAL ALERTS AND A
      STALE CONTROL STREAM STILL SEND FROM THE BOX. Born red on 2ee301d: notifications/alert_route.py does not exist
      (R0) and every check after it fails with it.

Driven, not grepped: a real AlertManager with a fake Telegram sender, a temp capture.choice through
OT_CAPTURE_CHOICE_FILE (the control ack file sits beside it), OT_LOG_FILE at scratch, and the records the pager logger
actually emits. The ack file is written here exactly as control's stream writes it (`HB <epoch> <src>:<n>,...`).

  R0  notifications.alert_route imports
  R1  managed + control healthy: a routine alert (ENT) writes ONE [alert] line via=control, the box does NOT send,
      _send returns True, and the [page] line and ALERT line are still written
  R2  managed + no ack file, and + an ack file older than CONTROL_STALE_S: the box sends (fallback), [alert] via=direct
  R3  critical with control healthy: HCF, a catastrophic-cap halt raw _send, a disk text and a BLIND with live open
      positions are each sent from the box AND written via=direct crit=true (control dedups the copy)
  R4  a routed alert control acks is never sent by the box; one it does not ack is sent at its deadline, once, with
      an `[alerted] <id>` line
  R5  the exit flush sends every still-unacked alert from the box
  R6  standalone: no [alert] line, the box sends, exactly as before
  R7  the [alert] line in bot.log's own format matches control's ALERT_RE and its JSON carries the UNESCAPED text, the
      symbol, the code, the ref, and the blind alert's cause and open count
  R8  a router fault (an unreadable ack directory, a raising writer) means "send from the box", never a lost alert
      and never an exception out of _send
  R9  no Telegram token in any [alert] / [alerted] line
"""
import json
import logging
import os
import re
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp(prefix="check_alert_route-")
CHOICE = os.path.join(_TMP, "capture.choice")
ACK = os.path.join(_TMP, "control_ack")
os.environ["OT_CAPTURE_CHOICE_FILE"] = CHOICE
os.environ["OT_LOG_FILE"] = os.path.join(_TMP, "bot.log")
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
TOKEN = "123456789:FAKE-token-for-check_alert_route"
os.environ["TELEGRAM_TOKEN"] = TOKEN
FAILED, RAN = [], []
TID = "abcd1234-5678-90ab-cdef-001122334455"
# control's match (day_trader_pro pager.py v0.2.0 ALERT_RE)
CONTROL_ALERT_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(?:,\d{3})? \[INFO\s*\] notifications\.pager: "
                              r"\[alert\] (\{.*\})\s*$")


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.recs = []

    def emit(self, record):
        self.recs.append((record.name, record.getMessage()))

    def alerts(self):
        out = []
        for n, m in self.recs:
            if n == "notifications.pager" and m.startswith("[alert] "):
                out.append(json.loads(m[len("[alert] "):]))
        return out

    def alerted(self):
        return [m.split()[1] for n, m in self.recs if n == "notifications.pager" and m.startswith("[alerted] ")]

    def pages(self):
        return [m for n, m in self.recs if n == "notifications.pager" and m.startswith("[page] ")]

    def raw(self):
        return [m for n, m in self.recs if n == "notifications.pager"]


class _TG:
    def __init__(self, ret=True):
        self.ret, self.sent = ret, []

    def send(self, msg):
        self.sent.append(msg)
        return self.ret


CAP = _Cap()
logging.getLogger().addHandler(CAP)
logging.getLogger().setLevel(logging.INFO)


def _choose(text):
    if text is None:
        if os.path.exists(CHOICE):
            os.unlink(CHOICE)
    else:
        with open(CHOICE, "w") as fh:
            fh.write(text + "\n")
    import notifications.pager as pg
    pg._state["managed"] = None


def _ack(ids=(), age_s=0.0):
    """Write the ack file as control's stream does, aged `age_s` by mtime. ids: full ids `<src>.<n>`."""
    by = {}
    for i in ids:
        src, _, n = i.rpartition(".")
        by.setdefault(src, []).append(n)
    line = "HB %.3f %s\n" % (time.time(), " ".join("%s:%s" % (s, ",".join(ns)) for s, ns in by.items()))
    with open(ACK + ".tmp", "w") as fh:
        fh.write(line)
    os.replace(ACK + ".tmp", ACK)
    t = time.time() - age_s
    os.utime(ACK, (t, t))


def _no_ack():
    if os.path.exists(ACK):
        os.unlink(ACK)


def _mgr(am, ret=True):
    m = am.AlertManager.__new__(am.AlertManager)
    m._tg, m._enabled = _TG(ret), True
    return m


def main():
    try:
        import notifications.alert_route as ar
        import notifications.alert_manager as am
    except Exception as e:                                  # noqa: BLE001
        check("R0 notifications.alert_route imports", False, "%s: %s" % (type(e).__name__, e))
        for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"):
            check(r, False, "no alert_route")
        print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
        return 1
    check("R0 notifications.alert_route imports", True)
    am.public_ip = lambda *a, **k: ("1.2.3.4", None)
    ar._ensure_watch = lambda: None                         # the gate drives check_pending itself, by the clock it gives
    check("R0b the ack file sits beside the capture choice file", ar.ack_path() == ACK, ar.ack_path())

    # R1 — managed, control healthy
    _choose("managed")
    _ack()
    CAP.recs.clear()
    m = _mgr(am)
    r = m._send("entered <x> & y", code="ENT", ref=TID)
    al = CAP.alerts()
    alert_lines = [x for n, x in CAP.recs if n == "notifications.alert_manager" and x.startswith("ALERT: ")]
    check("R1 healthy control: via=control, the box does not send, True returned, [page] + ALERT kept",
          r is True and m._tg.sent == [] and len(al) == 1 and al[0]["via"] == "control" and not al[0]["crit"]
          and al[0]["code"] == "ENT" and CAP.pages() == ["[page] ENT abcd1234"] and len(alert_lines) == 1,
          "ret=%r sent=%r alerts=%r pages=%r" % (r, m._tg.sent, al, CAP.pages()))
    ar._pending.clear()

    # R2 — fallback: no ack file, stale ack file
    bad = []
    for label, setup in (("no ack file", _no_ack), ("stale ack file", lambda: _ack(age_s=ar.CONTROL_STALE_S + 30))):
        setup()
        CAP.recs.clear()
        m = _mgr(am)
        r = m._send("routine", code="EXT", ref=TID)
        al = CAP.alerts()
        if not (r is True and m._tg.sent == ["routine"] and len(al) == 1 and al[0]["via"] == "direct"
                and ar.pending() == 0):
            bad.append("%s: ret=%r sent=%r alerts=%r pending=%d" % (label, r, m._tg.sent, al, ar.pending()))
    # and the sender's own False is still what _send returns on the fallback path
    _no_ack()
    rf = _mgr(am, False)._send("routine")
    check("R2 control stream unhealthy: the box sends, via=direct (no ack file; stale ack file)",
          not bad and rf is False, "; ".join(bad) + " ret_false=%r" % rf)

    # R3 — critical: direct AND written, with control healthy
    _ack()
    bad = []
    cases = [
        ("HCF", lambda mm: mm.send_hard_close_failure_alert("QQQ", [TID])),
        ("cap", lambda mm: mm._send("\U0001F6D1 QQQ DAILY CATASTROPHIC LOSS CAP HIT — day realized $-900. New entries "
                                    "halted")),
        ("disk", lambda mm: mm._send("\U0001F6A8 QQQ DISK 96% full")),
        ("BLD live", lambda mm: mm.send_blind_alert("QQQ", {"cause": "BARS_STALE", "timeframe": "1m", "fields": {}},
                                                    open_positions=["PUT 737 x2"], paper=False, blind_for_s=40)),
        ("SLC", lambda mm: mm.send_short_leg_closed_alert("QQQ", "short 740C", "long 745C")),
    ]
    for label, call in cases:
        CAP.recs.clear()
        mm = _mgr(am)
        call(mm)
        al = CAP.alerts()
        if not (len(mm._tg.sent) == 1 and len(al) == 1 and al[0]["via"] == "direct" and al[0]["crit"] is True):
            bad.append("%s: sent=%d alerts=%r" % (label, len(mm._tg.sent), al))
    # a paper BLIND with no position is NOT critical: routed
    CAP.recs.clear()
    mm = _mgr(am)
    mm.send_blind_alert("QQQ", {"cause": "BARS_STALE", "timeframe": "1m", "fields": {}}, open_positions=[],
                        paper=True, blind_for_s=40)
    al = CAP.alerts()
    paper_ok = mm._tg.sent == [] and len(al) == 1 and al[0]["via"] == "control"
    check("R3 critical (HCF, catastrophic halt, disk, BLIND with live positions, broker SLC) go direct AND are written "
          "via=direct crit=true; a flat paper BLIND is routed", not bad and paper_ok,
          "; ".join(bad) + " paper=%r" % paper_ok)
    ar._pending.clear()

    # R4 — ack deadline
    _ack()
    CAP.recs.clear()
    m = _mgr(am)
    m._send("first", code="ENT", ref="t1")
    m._send("second", code="ENT", ref="t2")
    ids = [a["id"] for a in CAP.alerts()]
    _ack(ids=ids[:1])                                       # control acks the first only
    now = time.time()
    early = ar.check_pending(now=now)                       # before the deadline: nothing sent
    late = ar.check_pending(now=now + ar.ACK_DEADLINE_S + 1)
    again = ar.check_pending(now=now + ar.ACK_DEADLINE_S + 5)
    check("R4 an acked alert is never sent by the box; an unacked one is sent at its deadline, once, with [alerted]",
          early == [] and late == [ids[1]] and again == [] and m._tg.sent == ["second"] and CAP.alerted() == [ids[1]],
          "early=%r late=%r again=%r sent=%r alerted=%r ids=%r" % (early, late, again, m._tg.sent, CAP.alerted(), ids))

    # R5 — exit flush
    _ack()
    CAP.recs.clear()
    m = _mgr(am)
    m.send_shutdown_alert("QQQ", "maintenance")
    sent_exit = ar.flush_at_exit(wait_s=0.3)
    check("R5 at exit every unacked alert is sent from the box", len(sent_exit) == 1 and len(m._tg.sent) == 1
          and ar.pending() == 0, "sent=%r tg=%r" % (sent_exit, m._tg.sent))

    # R6 — standalone unchanged
    _choose("standalone")
    _ack()
    CAP.recs.clear()
    m = _mgr(am)
    r = m._send("routine", code="ENT", ref=TID)
    check("R6 standalone: no [alert] line, the box sends", r is True and m._tg.sent == ["routine"]
          and CAP.alerts() == [] and CAP.pages() == [], "sent=%r alerts=%r" % (m._tg.sent, CAP.alerts()))

    # R7 — the line in bot.log format is control's ALERT_RE, unescaped text and meta
    _choose("managed")
    _ack()
    log = os.path.join(_TMP, "fmt.log")
    fh = logging.FileHandler(log, encoding="utf-8")
    fh.setFormatter(logging.Formatter(fmt="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
                                      datefmt="%Y-%m-%d %H:%M:%S"))
    logging.getLogger("notifications.pager").addHandler(fh)
    m = _mgr(am)
    m.send_blind_alert("AMD", {"cause": "BARS_STALE", "timeframe": "1m", "fields": {"newest_bar": "<14:18>"}},
                       open_positions=["CALL 160 x1"], paper=True, blind_for_s=61)
    logging.getLogger("notifications.pager").removeHandler(fh)
    fh.close()
    lines = [ln.rstrip("\n") for ln in open(log, encoding="utf-8") if "[alert] " in ln]
    rec = None
    if len(lines) == 1:
        mm_ = CONTROL_ALERT_RE.match(lines[0])
        rec = json.loads(mm_.group(2)) if mm_ else None
    ok7 = (rec is not None and rec["code"] == "BLD" and rec["sym"] == os.environ["OT_INSTRUMENT"]
           and rec["cause"] == "BARS_STALE on 1m" and rec["open"] == 1 and rec["paper"] is True
           and "<14:18>" in rec["text"] and "&lt;" not in rec["text"] and "BOT IS BLIND" in rec["text"]
           and all(ord(c) < 128 for c in lines[0]))
    check("R7 the [alert] line matches control's ALERT_RE; JSON carries unescaped text, code, cause, open count",
          ok7, "lines=%r rec=%r" % (lines, rec))
    ar._pending.clear()

    # R8 — faults send from the box
    bad = []
    real_write = ar._write
    ar._write = lambda rec: (_ for _ in ()).throw(RuntimeError("disk gone"))
    _ack()
    m = _mgr(am)
    try:
        r = m._send("routine under a broken writer", code="ENT")
        if not (r is True and m._tg.sent == ["routine under a broken writer"]):
            bad.append("writer: ret=%r sent=%r" % (r, m._tg.sent))
    except Exception as e:                                  # noqa: BLE001
        bad.append("writer raised %s" % type(e).__name__)
    ar._write = real_write
    real_path = ar.ack_path
    ar.ack_path = lambda: (_ for _ in ()).throw(PermissionError("no"))
    m = _mgr(am)
    try:
        r = m._send("routine under an unreadable ack", code="ENT")
        if not (r is True and len(m._tg.sent) == 1):
            bad.append("ack: ret=%r sent=%r" % (r, m._tg.sent))
    except Exception as e:                                  # noqa: BLE001
        bad.append("ack raised %s" % type(e).__name__)
    ar.ack_path = real_path
    check("R8 a router fault sends from the box and never raises out of _send", not bad, "; ".join(bad))
    ar._pending.clear()

    # R9 — no token
    leaked = [x for x in CAP.raw() if TOKEN in x] + [ln for ln in open(log, encoding="utf-8") if TOKEN in ln]
    check("R9 no Telegram token in any [alert] / [alerted] line", not leaked, "%d lines" % len(leaked))

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
