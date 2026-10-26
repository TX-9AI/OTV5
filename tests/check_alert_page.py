#!/usr/bin/env python3
"""
tests/check_alert_page.py  v5.0
v5.0  2026-10-26  (PAGE.1) — new. THE BOT PAGES CONTROL WITH ONE SHORT LINE IN bot.log. Every alert also writes
      `[page] <CODE> [ref]` (logger notifications.pager) on a managed box, and control's pager follows bot.log for
      exactly those lines. Born red on 5387033: notifications/pager.py does not exist and _send takes no code.

Driven, not grepped: a real AlertManager with a fake Telegram sender, a temp capture.choice through
OT_CAPTURE_CHOICE_FILE, OT_LOG_FILE pointed at scratch, and the records the pager logger actually emits.

  P1  notifications.alert_manager.PAGE_CODES is the fixed sixteen-code table
  P2  managed: each send_* writes exactly ONE page line with its own code (and the trade id's first 8 chars for
      ENT, EXT, HCF)
  P3  ...and _send is otherwise unchanged: the ALERT line is still written, BEFORE the page, and _send returns what
      the sender returned (True and False both)
  P4  standalone (capture.choice reads "standalone"): no page line from any send_*
  P5  no capture.choice at all: standalone, no page line
  P6  an unknown code is written as MSG; a raw _send (no code) pages MSG; a long ref is cut to 8 chars
  P7  a page writer that raises does not break _send: it returns the sender's answer and raises nothing
  P8  a page line written through bot.log's own format is what control's pager matches
  P9  data/disk_watch's direct sends page MSG (the real alert and the DRILL), managed only
"""
import logging
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp(prefix="check_alert_page-")
CHOICE = os.path.join(_TMP, "capture.choice")
os.environ["OT_CAPTURE_CHOICE_FILE"] = CHOICE
os.environ["OT_LOG_FILE"] = os.path.join(_TMP, "bot.log")
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_DISK_DRILL_FLAG"] = os.path.join(_TMP, "DRILL_DISK")
FAILED, RAN = [], []
CODES = {"UP", "DN", "ENT", "EXT", "SUM", "HCF", "BLD", "SEE", "RCU", "EXR", "SLC", "ADP", "ORF", "PHN", "RCV", "MSG"}
TID = "abcd1234-5678-90ab-cdef-001122334455"
# control's match (day_trader_pro pager.py): bot.log stamp, then the pager logger's line
CONTROL_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(?:,\d{3})? \[INFO\s*\] notifications\.pager: "
                        r"\[page\] ([A-Z]{2,4})(?: (\S+))?$")


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

    def pages(self):
        return [m for n, m in self.recs if n == "notifications.pager" and m.startswith("[page] ")]


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
    try:
        import notifications.pager as pg
        pg._state["managed"] = None                         # the cache is read once per process; reset per case
    except Exception:                                       # noqa: BLE001
        pass


def _mgr(am, ret=True):
    m = am.AlertManager.__new__(am.AlertManager)
    m._tg, m._enabled = _TG(ret), True
    return m


def _calls(m):
    """(expected code, expected ref, call) for every send_*."""
    return [
        ("UP", "", lambda: m.send_startup_alert(paper=True, instrument="QQQ", risk_usd=1000.0, restart_type="fresh boot")),
        ("DN", "", lambda: m.send_shutdown_alert("QQQ", "maintenance")),
        ("ENT", TID[:8], lambda: m.send_entry_alert({"trade_id": TID, "paper_trade": True, "option_side": "put",
                                                      "strike": 737.0, "contracts": 2, "entry_premium": 1.7,
                                                      "total_cost": 340.0})),
        ("ENT", TID[:8], lambda: m.send_entry_alert({"trade_id": TID, "paper_trade": True, "is_butterfly": True,
                                                      "option_side": "call", "lower_strike": 735, "center_strike": 737,
                                                      "upper_strike": 739, "contracts": 1, "net_debit": 0.8,
                                                      "total_cost": 80.0})),
        ("EXT", TID[:8], lambda: m.send_exit_alert(TID, "breakout_short", 1.2, 1.7, -100.0, 2, "hard_stop")),
        ("SUM", "", lambda: m.send_daily_summary({"instrument": "QQQ", "paper": True, "n_trades": 1})),
        ("HCF", TID[:8], lambda: m.send_hard_close_failure_alert("QQQ", [TID, "other"])),
        ("BLD", "", lambda: m.send_blind_alert("QQQ", {"cause": "BARS_STALE", "timeframe": "1m", "fields": {}},
                                               open_positions=[], blind_for_s=40.0)),
        ("SEE", "", lambda: m.send_sight_restored_alert("QQQ", 40.0, "BARS_STALE")),
        ("RCU", "", lambda: m.send_reconcile_unavailable_alert("QQQ", "timeout")),
        ("EXR", "", lambda: m.send_exercise_footprint_alert("QQQ", [{"symbol": "QQQ", "quantity": 100}], 1.0)),
        ("SLC", "", lambda: m.send_short_leg_closed_alert("QQQ", "short 740C", "long 745C")),
        ("ADP", "", lambda: m.send_adopted_alert("QQQ", "PUT 737", 2, 1.1)),
        ("ADP", "", lambda: m.send_adopted_alert("QQQ", "PUT 737", 2, 1.1, is_short=True, anomaly=True)),
        ("ORF", "", lambda: m.send_orphan_cleared_alert("QQQ", ["PUT 737"])),
        ("PHN", "", lambda: m.send_phantom_closed_alert("QQQ", ["t1"])),
        ("RCV", "", lambda: m.send_recovery_alert("QQQ", "PUT 737", 2, 1.7, 340.0, "Breakout", "service restart")),
    ]


def _want(code, ref):
    return "[page] %s %s" % (code, ref) if ref else "[page] %s" % code


def main():
    try:
        import notifications.alert_manager as am
    except Exception as e:                                  # noqa: BLE001
        check("P0 notifications.alert_manager imports", False, "%s: %s" % (type(e).__name__, e))
        print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
        return 1
    am.public_ip = lambda *a, **k: ("1.2.3.4", None)       # no network from a checker

    table = getattr(am, "PAGE_CODES", None)
    check("P1 PAGE_CODES is the fixed sixteen-code table", isinstance(table, dict) and set(table) == CODES,
          "got %r" % (sorted(table) if isinstance(table, dict) else table))

    # P2 / P3 — managed
    _choose("managed")
    m = _mgr(am)
    bad = []
    for code, ref, call in _calls(m):
        CAP.recs.clear()
        try:
            call()
        except Exception as e:                              # noqa: BLE001
            bad.append("%s raised %s: %s" % (code, type(e).__name__, e))
            continue
        got = CAP.pages()
        if got != [_want(code, ref)]:
            bad.append("%s -> %r" % (code, got))
    check("P2 managed: each send_* writes exactly one page line with its own code (%d calls)" % len(_calls(m)),
          not bad, "; ".join(bad[:6]))

    CAP.recs.clear()
    try:
        r_true = _mgr(am, True)._send("hello <x>", code="ENT", ref=TID)
        order = [n for n, msg in CAP.recs if (n == "notifications.alert_manager" and msg.startswith("ALERT: "))
                 or (n == "notifications.pager" and msg.startswith("[page] "))]
        r_false = _mgr(am, False)._send("hello")
    except Exception as e:                                  # noqa: BLE001
        r_true = r_false = "raised %s: %s" % (type(e).__name__, e)
        order = []
    check("P3 _send keeps its ALERT line (before the page) and returns the sender's answer",
          order == ["notifications.alert_manager", "notifications.pager"] and r_true is True and r_false is False,
          "order=%r true=%r false=%r" % (order, r_true, r_false))

    # P4 / P5 — standalone
    for label, text in (("P4 standalone (capture.choice reads \"standalone\")", "standalone"),
                        ("P5 no capture.choice at all reads standalone", None)):
        _choose(text)
        CAP.recs.clear()
        m = _mgr(am)
        errs = []
        for code, ref, call in _calls(m):
            try:
                call()
            except Exception as e:                          # noqa: BLE001
                errs.append("%s raised %s" % (code, type(e).__name__))
        alerts = [x for n, x in CAP.recs if x.startswith("ALERT: ")]
        check("%s: no page line from any send_*" % label, not CAP.pages() and not errs and len(alerts) >= 17,
              "pages=%r errs=%r alerts=%d" % (CAP.pages()[:3], errs[:3], len(alerts)))

    # P6 — unknown code, raw caller, long ref
    _choose("managed")
    CAP.recs.clear()
    m = _mgr(am)
    try:
        m._send("x", code="ZZZ")
        m._send("raw caller")
        m._send("x", code="EXT", ref="0123456789abcdef")
    except Exception as e:                                  # noqa: BLE001
        CAP.recs.append(("raised", "[page] %s" % type(e).__name__))
    check("P6 unknown code -> MSG; a raw _send pages MSG; a long ref is cut to 8 chars",
          CAP.pages() == ["[page] MSG", "[page] MSG", "[page] EXT 01234567"], "got %r" % CAP.pages())

    # P7 — a page writer that raises
    ok7, why7 = True, ""
    real_page = getattr(am, "_page", None)
    try:
        def _boom(*a, **k):
            raise RuntimeError("pager down")
        if real_page is None:
            ok7, why7 = False, "alert_manager has no page writer (_page)"
        else:
            am._page = _boom
            if _mgr(am, True)._send("a", code="UP") is not True or _mgr(am, False)._send("b") is not False:
                ok7, why7 = False, "return value changed"
        import notifications.pager as pg
        real_info = pg.logger.info
        pg.logger.info = _boom
        try:
            pg.page("UP", "x")                              # must not raise either
        finally:
            pg.logger.info = real_info
    except Exception as e:                                  # noqa: BLE001
        ok7, why7 = False, "raised %s: %s" % (type(e).__name__, e)
    finally:
        if real_page is not None:
            am._page = real_page
    check("P7 a page writer that raises does not break _send (return unchanged, nothing raised)", ok7, why7)

    # P8 — the line as bot.log writes it is the line control matches
    logpath = os.environ["OT_LOG_FILE"]
    fh = logging.FileHandler(logpath)
    fh.setFormatter(logging.Formatter(fmt="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
                                      datefmt="%Y-%m-%d %H:%M:%S"))      # main._setup_logging's format
    logging.getLogger().addHandler(fh)
    try:
        _mgr(am).send_exit_alert(TID, "breakout_short", 1.2, 1.7, 5.0, 1, "target")
        _mgr(am).send_shutdown_alert("QQQ")
    except Exception:                                       # noqa: BLE001
        pass                                                # judged by the file below
    finally:
        logging.getLogger().removeHandler(fh)
        fh.close()
    try:
        lines = [ln.rstrip("\n") for ln in open(logpath, encoding="utf-8") if "[page] " in ln]
    except OSError:
        lines = []
    ms = [CONTROL_RE.match(ln) for ln in lines]
    check("P8 the page lines in a bot.log-format file are what control's pager matches",
          len(ms) == 2 and all(ms) and [(x.group(2), x.group(3)) for x in ms] == [("EXT", TID[:8]), ("DN", None)],
          "lines=%r" % lines)

    # P9 — disk_watch
    ok9, why9 = True, ""
    try:
        import data.disk_watch as D
        D.largest_files = lambda *a, **k: []
        D._pct_used = lambda path="/": 99.0
        res = []
        for choice in ("managed", "standalone"):
            _choose(choice)
            CAP.recs.clear()
            D._state.update(over=False, last_check=0.0)
            s = _TG(True)
            D.check(sender=s, instrument="QQQ")                         # the real alert
            open(D.DRILL_FLAG, "w").close()
            D.check(sender=s, instrument="QQQ")                         # the drill
            res.append((choice, len(s.sent), CAP.pages()))
        want = [("managed", 2, ["[page] MSG", "[page] MSG"]), ("standalone", 2, [])]
        if res != want:
            ok9, why9 = False, "got %r" % res
    except Exception as e:                                  # noqa: BLE001
        ok9, why9 = False, "raised %s: %s" % (type(e).__name__, e)
    check("P9 disk_watch's direct sends page MSG (alert and drill), managed only", ok9, why9)

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        import shutil
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(rc)
