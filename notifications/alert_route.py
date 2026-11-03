"""
notifications/alert_route.py  v5.0
v5.0  2026-11-02  (PAGE.2) — new. A MANAGED BOX HANDS ITS ALERTS TO CONTROL; CONTROL SENDS ONE PACED, GROUPED TELEGRAM
      QUEUE FOR THE FLEET. 2026-11-02 09:30 and 14:19 ET a dxFeed node failure made 3, then 8+, boxes each send its own
      "BOT IS BLIND" inside a minute; the operator: "we need that message routing slash queue triage more than ever".
      On a managed box (notifications/pager.is_managed(): capture.choice reads "managed") every AlertManager alert is
      written as ONE full line in bot.log through the pager logger:
          `<stamp> [INFO ] notifications.pager: [alert] {"id": .., "code": .., "sym": .., "via": .., "crit": .., ...}`
      (JSON, ASCII only, the text NOT HTML-escaped), which control's pager stream (day_trader_pro pager.py v0.2.0)
      reads and day_trader_pro alert_router.py groups, prioritises and paces into Telegram.
      THE BOX DECIDES WHO SENDS, PER ALERT (route()):
        - not managed                     -> the box sends; no [alert] line (unchanged from v5.2 alert_manager)
        - critical (CRITICAL_CODES, CRITICAL_RE: emergency, halt / catastrophic cap, kill switch, disk, the broker
          codes, a BLIND with live open positions)   -> the box sends direct AND writes via=direct; control records it
          and never re-sends it (dedup by id)
        - control healthy                 -> via=control; the box does NOT send; control acks it
        - control unhealthy               -> the box sends direct, via=direct
      CONTROL IS HEALTHY iff its ack file (CONTROL_ACK beside the capture choice file, written only by control's
      alert-router stream: each line control writes on the ssh channel's stdin replaces it) was modified within
      CONTROL_STALE_S by the box's own clock. A routed alert not named in the ack file within ACK_DEADLINE_S is sent
      direct by the watcher thread and a `[alerted] <id>` line tells control it was (control drops its queued copy).
      At process exit every still-unacked alert gets ACK_EXIT_WAIT_S, then is sent direct.
      ⚠️ route() NEVER RAISES and never blocks on the network: any fault in this module answers "send direct", so a
      broken router costs a duplicate, never an alert.
      ⚠️ NO NEW KNOB. The switch is the existing managed capture choice; the ack file path follows
      OT_CAPTURE_CHOICE_FILE's directory (already read by notifications/pager.py). Gate tests/check_alert_route.py.
"""

import atexit
import json
import logging
import os
import re
import threading
import time

from notifications import pager as _pager

logger = logging.getLogger("notifications.pager")     # the SAME logger as [page]: control's grep reads one name
logger.setLevel(logging.INFO)
_log = logging.getLogger(__name__)

CONTROL_STALE_S = 45.0        # control's stream writes its ack file every ~10 s; 45 s without one = control is down
ACK_DEADLINE_S = 30.0         # a routed alert control has not acked in 30 s is sent by the box itself
ACK_EXIT_WAIT_S = 3.0         # at exit, unacked alerts get this long before the box sends them
WATCH_TICK_S = 1.0

# Codes that are always the box's own job to deliver (control dedups its copy).
#   HCF hard close incomplete · EXR shares in the account · SLC short leg closed by the broker · RCU broker reconcile
#   unavailable
CRITICAL_CODES = frozenset({"HCF", "EXR", "SLC", "RCU"})
# ...and any alert whose words name an emergency, a halt, the kill switch, the disk or the broker.
CRITICAL_RE = re.compile(r"EMERGENCY|CATASTROPHIC|HALT|KILL[ _-]?SWITCH|DISK|RECONCILE MISMATCH|could not be "
                         r"cancelled|LONE SHORT|GO TO TASTYTRADE NOW", re.IGNORECASE)

_state = {"src": None, "n": 0}
_lock = threading.Lock()
_pending = {}                 # id -> (deadline, text, sender, code)
_watch = {"thread": None, "atexit": False}


def ack_path() -> str:
    choice = _pager._choice_file()
    return os.path.join(os.path.dirname(choice) or ".", "control_ack")


def _src() -> str:
    """This process's id prefix: pid + start time, so a restarted bot's ids never collide with the old one's."""
    if _state["src"] is None:
        _state["src"] = "%x%04x" % (os.getpid(), int(time.time()) % 65536)
    return _state["src"]


def _next_id() -> str:
    with _lock:
        _state["n"] += 1
        return "%s.%d" % (_src(), _state["n"])


def is_critical(code: str, text: str) -> bool:
    try:
        return str(code or "").upper() in CRITICAL_CODES or bool(CRITICAL_RE.search(str(text or "")))
    except Exception:                                           # noqa: BLE001
        return True


def control_healthy(now: float = None) -> bool:
    """True iff control's ack file was refreshed within CONTROL_STALE_S (the box's own clock)."""
    try:
        age = (time.time() if now is None else now) - os.stat(ack_path()).st_mtime
        return -5.0 <= age <= float(CONTROL_STALE_S)
    except Exception:                                           # noqa: BLE001
        return False


def acked_ids() -> set:
    """The ids control's last ack line names. Format: `HB <epoch> <src>:<n>,<n>,... <src>:<n>...`."""
    try:
        with open(ack_path(), encoding="ascii", errors="replace") as fh:
            parts = fh.read(16384).split()
    except Exception:                                           # noqa: BLE001
        return set()
    out = set()
    if not parts or parts[0] != "HB":
        return out
    for tok in parts[2:]:
        src, _, ns = tok.partition(":")
        for n in ns.split(","):
            if n.isdigit():
                out.add("%s.%s" % (src, n))
    return out


def _instrument() -> str:
    try:
        from config import INSTRUMENT
        return os.environ.get("OT_INSTRUMENT") or INSTRUMENT
    except Exception:                                           # noqa: BLE001
        return os.environ.get("OT_INSTRUMENT", "?")


def _write(rec: dict) -> None:
    logger.info("[alert] " + json.dumps(rec, ensure_ascii=True, separators=(",", ":"), default=str))


def route(code: str, ref: str, text: str, send_direct, meta: dict = None):
    """Decide who delivers one alert. -> (sent_direct, accepted)

    `text` is the alert as the operator reads it (unescaped); `send_direct()` is the box's own Telegram send and
    returns its bool. accepted is True when control took it (via=control) or the direct send was accepted.
    NEVER raises: any fault here sends direct."""
    try:
        if not _pager.is_managed():
            return True, bool(send_direct())
        code = str(code or "MSG").upper()
        crit = is_critical(code, text)
        healthy = control_healthy()
        via = "direct" if (crit or not healthy) else "control"
        aid = _next_id()
        rec = {"id": aid, "code": code, "ref": str(ref or "")[:8], "sym": _instrument(), "via": via,
               "crit": bool(crit), "ts": round(time.time(), 3), "text": str(text)[:3800]}
        for k, v in (meta or {}).items():
            if k not in rec and v is not None:
                rec[k] = v
        if via == "direct":
            ok = bool(send_direct())
            _write(rec)
            return True, ok
        with _lock:
            _pending[aid] = (time.time() + float(ACK_DEADLINE_S), text, send_direct, code)
        _write(rec)
        _ensure_watch()
        return False, True
    except Exception as e:                                      # noqa: BLE001
        _log.error("alert route failed (%s); sending direct", type(e).__name__)
        try:
            return True, bool(send_direct())
        except Exception:                                       # noqa: BLE001
            return True, False


def check_pending(now: float = None, force: bool = False) -> list:
    """Send direct every routed alert past its deadline (or all unacked, `force`). -> the ids sent. Never raises."""
    sent = []
    try:
        now = time.time() if now is None else now
        with _lock:
            if not _pending:
                return sent
            items = list(_pending.items())
        acked = acked_ids()
        for aid, (deadline, _text, send_direct, _code) in items:
            if aid in acked:
                with _lock:
                    _pending.pop(aid, None)
                continue
            if force or now >= deadline:
                with _lock:
                    if _pending.pop(aid, None) is None:
                        continue
                try:
                    send_direct()
                except Exception:                               # noqa: BLE001
                    pass
                logger.info("[alerted] %s" % aid)
                _log.warning("alert %s not acked by control in %.0fs; sent direct", aid, ACK_DEADLINE_S)
                sent.append(aid)
    except Exception:                                           # noqa: BLE001
        pass
    return sent


def pending() -> int:
    with _lock:
        return len(_pending)


def flush_at_exit(wait_s: float = None) -> list:
    """Give control ACK_EXIT_WAIT_S to ack what is pending, then send the rest direct."""
    end = time.time() + (ACK_EXIT_WAIT_S if wait_s is None else wait_s)
    while pending() and time.time() < end:
        check_pending()
        time.sleep(0.2)
    sent = check_pending(force=True)
    if sent:
        try:                       # the courier may have started only now, after its own atexit slot
            from notifications import telegram_sender
            telegram_sender.flush()
        except Exception:                                       # noqa: BLE001
            pass
    return sent


def _watch_loop():
    while True:
        time.sleep(WATCH_TICK_S)
        check_pending()


def _ensure_watch():
    with _lock:
        th = _watch["thread"]
        if th is None or not th.is_alive():
            th = threading.Thread(target=_watch_loop, name="alert-route-watch", daemon=True)
            _watch["thread"] = th
            th.start()
        if not _watch["atexit"]:
            # registered after the Telegram courier's own atexit drain, so it runs BEFORE it (LIFO) and the direct
            # sends it makes are drained by the courier
            atexit.register(flush_at_exit)
            _watch["atexit"] = True
