#!/usr/bin/env python3
"""utils/agent_status.py — v1.0

v1.0 (2026-09-20) — OTV4TEST r68 / BOX.11. IS AN AGENT SESSION AVAILABLE?

The operator's ask, 2026-09-20: *"Can we have a tmux session Claude --continue
added to the boot sequence on this box so that an agent is available from the
moment the box auto wakes?"* and, on the boot Telegram that already carries the
IP, *"Can I get added to that 'Claude is up' ... and 'Agent not available' if
it fails."*

🔑 WHY A FILE, AND WHY NOT A SECOND TELEGRAM SENDER. `tools/claude_boot.py`
raises the session; the BOT sends the alert. Giving the raiser its own token
would put a second copy of the credentials in a second unit, and §18a's finding
is that EVERY unit on this box is already a credential store — there is no
reason to add one. Same division as r67's `shutdown_cause`: the thing that
KNOWS writes a stamp, the thing that can already SEND reads it.

⚠️ THIS IS DELIBERATELY *NOT* `shutdown_cause`, AND THE DIFFERENCE IS THE
LIFETIME. A shutdown cause describes ONE event and is consumed on read, because
a stamp that outlives its event starts speaking for the next one. An agent
status describes a STANDING CONDITION: the bot may restart repeatedly while one
tmux session keeps running, and each restart must be able to read it again. So
this one is READ, never consumed. Two files, two lifetimes, stated here so
nobody later "tidies" them into one.

⚠️ AND IT FAILS TO *UNKNOWN*, NEVER TO A CLAIM. Absent, unreadable, malformed
or stale all yield None and the alert says so by name. §29 is the reason this
matters: the bot must never wait on the agent — nothing on this box may be
load-bearing for trading — so the alert reports whatever is true at the moment
it sends and blocks on nothing.
"""
from __future__ import annotations

import os
import time

# Generous: the raiser runs at boot and the bot's startup alert follows about
# eleven seconds later (measured 2026-09-20: boot 12:00:10 UTC, alert 12:00:21).
# Anything older than this window is from a PREVIOUS boot and must not be
# reported as today's state.
MAX_AGE_S = 900

_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "AGENT_STATUS")


def path() -> str:
    """OT_AGENT_STATUS overrides, so a checker never writes the real one."""
    return os.environ.get("OT_AGENT_STATUS", _DEFAULT)


def record(text: str) -> bool:
    """Stamp the agent's availability. Never raises."""
    try:
        p = path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("%d|%s\n" % (int(time.time()), text.strip()))
        return True
    except Exception:                                           # noqa: BLE001
        return False


def read(now: float | None = None) -> str | None:
    """The stamped status if it is fresh, else None. NOT consumed — see above."""
    try:
        with open(path(), encoding="utf-8") as fh:
            raw = fh.read().strip()
    except Exception:                                           # noqa: BLE001
        return None
    stamp, _, text = raw.partition("|")
    text = text.strip()
    if not text:
        return None
    try:
        age = (time.time() if now is None else now) - float(stamp)
    except Exception:                                           # noqa: BLE001
        return None
    if age < 0 or age > MAX_AGE_S:
        return None
    return text
