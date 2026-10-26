"""
notifications/pager.py  v5.0
v5.0  2026-10-26  (PAGE.1) — new. THE BOT PAGES CONTROL WITH ONE SHORT LINE IN bot.log. The operator's design: every
      bot alert also writes ONE INFO line, `[page] <CODE>` or `[page] <CODE> <ref>`, and its timestamp is the reference;
      control (day_trader_pro pager.py) follows bot.log over ssh and passes on only the page lines. Written by
      AlertManager._send after its ALERT line and by data/disk_watch.py, which calls the Telegram sender directly.
      Only a MANAGED box pages: the capture choice file (configure.sh's CAPTURE_CHOICE_FILE,
      ${OT_CAPTURE_CHOICE_FILE:-$HOME/.optbot/capture.choice}) reads "managed"; read once, cached; unreadable is
      standalone. Gate tests/check_alert_page.py P1-P9.

⚠️ page() NEVER RAISES. It runs after a send that has already happened; a page that could fail would let control's
copy cost the operator's alert its return value, which callers (the blind drill) read.
⚠️ THE CODE SET IS FIXED. Control drops a code it does not know, so a code outside PAGE_CODES is written as MSG
rather than invented here and silently lost there.
"""

import logging
import os
import re

# The fixed code table — control's pager.py holds the same set and drops anything else.
PAGE_CODES = {
    "UP":  "startup",
    "DN":  "shutdown",
    "ENT": "entry",
    "EXT": "exit",
    "SUM": "daily summary",
    "HCF": "hard close failure",
    "BLD": "blind",
    "SEE": "sight restored",
    "RCU": "reconcile unavailable",
    "EXR": "exercise footprint",
    "SLC": "short leg closed",
    "ADP": "adopted",
    "ORF": "orphan cleared",
    "PHN": "phantom closed",
    "RCV": "recovery",
    "MSG": "anything else",
}

logger = logging.getLogger("notifications.pager")
# 🔑 THE PAGE IS WRITTEN AT INFO WHATEVER config.LOG_LEVEL SAYS. Records propagate to the root's handlers without
# the root's own level being consulted, so a box set to WARNING still pages; DEBUG changes nothing here.
logger.setLevel(logging.INFO)

_REF_OK = re.compile(r"[^A-Za-z0-9_-]")
_state = {"managed": None}


def _choice_file() -> str:
    return os.environ.get("OT_CAPTURE_CHOICE_FILE") or os.path.join(
        os.path.expanduser("~"), ".optbot", "capture.choice")


def is_managed() -> bool:
    """True iff the capture choice reads "managed" (configure.sh capture_choice). Read once and cached."""
    if _state["managed"] is None:
        try:
            with open(_choice_file(), encoding="utf-8") as fh:
                _state["managed"] = fh.read().strip() == "managed"
        except Exception:                                       # noqa: BLE001
            _state["managed"] = False                           # unreadable = standalone, as configure.sh reads it
    return _state["managed"]


def page(code: str = "MSG", ref: str = "") -> None:
    """Write `[page] CODE [ref]` on a managed box. NEVER raises; returns nothing."""
    try:
        if not is_managed():
            return
        code = str(code or "MSG").upper()
        if code not in PAGE_CODES:
            code = "MSG"
        ref = _REF_OK.sub("", str(ref or "")[:8])       # the first 8 chars, then anything not one token dropped
        logger.info("[page] %s %s" % (code, ref) if ref else "[page] %s" % code)
    except Exception:                                           # noqa: BLE001
        pass
