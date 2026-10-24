"""
utils/instrument.py  v1.0
THE BOX'S INSTRUMENT, FOR A PROCESS THAT DOES NOT RUN INSIDE THE BOT'S UNIT.

v1.0  2026-09-26  OTV4TEST r146. The operator: "That default QQQ variable outside
      the environment has bit us multiple times ... defaulting the QQQ is not
      the answer." Every process that read OT_INSTRUMENT with a "QQQ" fallback
      was right on the QQQ box BY LUCK and wrong everywhere else: the boot
      sweep's checkers labelled fixture events QQQ on SOFI and AAL (r144), and
      self_close and the manifold board ran without the variable on those boxes.

      box_instrument() asks, in order:
        1. this process's OT_INSTRUMENT (a service unit, a harness, the operator)
        2. the BOT UNIT's own OT_INSTRUMENT - the truth for this box, read the way
           status.py's get_runtime_env reads it: the unit's Environment into
           memory, ONE key extracted, NOTHING printed (WORKING_AGREEMENT §18a -
           that block holds the broker and Telegram credentials)
        3. UNSET - never a guessed symbol. A caller that gets UNSET says so.
"""
from __future__ import annotations

import os
import re
import subprocess

UNSET = "UNSET"
_BOT_UNIT = os.environ.get("OT_BOT_UNIT", "optionsbot")


def _from_bot_unit(key: str = "OT_INSTRUMENT") -> str:
    """The bot unit's value for ONE variable, or "". Never prints the block."""
    try:
        out = subprocess.run(["systemctl", "show", _BOT_UNIT, "--property=Environment"],
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:                                           # noqa: BLE001
        return ""
    m = re.search(rf"(?:^|\s|=){re.escape(key)}=([^\s]+)", out)
    return m.group(1) if m else ""


def box_instrument() -> str:
    """OT_INSTRUMENT from this process, else from the bot unit, else UNSET."""
    return (os.environ.get("OT_INSTRUMENT") or "").strip() or _from_bot_unit() or UNSET
