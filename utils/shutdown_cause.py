#!/usr/bin/env python3
"""utils/shutdown_cause.py — v1.0

v1.0 (2026-09-20) — OTV4TEST r67 / BOX.9. WHY THE BOT WENT DOWN, NAMED.

🔴 THE DEFECT THIS EXISTS FOR. `main.py`'s SIGTERM handler hardcoded
`reason = "systemctl stop/restart"`, so EVERY route down produced the same
sentence on the emergency channel. The operator's own Telegram, 2026-09-19/20:

    09/19 21:31 ET  OptionsBot STOPPED | systemctl stop/restart   <- fleet stop
    09/19 22:49 ET  OptionsBot STOPPED | systemctl stop/restart   <- the r66 bake
    09/20 00:00 ET  OptionsBot STOPPED | systemctl stop/restart   <- MIDNIGHT HALT

Three different causes, one label. The only thing distinguishing the backstop
was the CLOCK, which means the operator INFERRED it rather than being told —
§0.5's class exactly: a real event rendering as something indistinguishable
from an unrelated one.

🔑 WHY A FILE AND NOT A MESSAGE FROM THE HALT ITSELF. `midnight_halt` runs from
a unit carrying NO `Environment=` lines, so it holds no Telegram token and
never could — r287's finding, that credentials reach a box through systemd's
environment and a bare `venv/bin/python` has none. And its own header forbids
the workaround: *"a backstop whose value is that it cannot fail in novel ways
must not acquire dependencies."* So the halt states its CAUSE locally and the
bot — which already has the token, the path and a working handler — does the
sending. Same sentinel idiom as `NO_MIDNIGHT_HALT`, `DRILL_DISK` and
`FEED_MAINTENANCE`.

⚠️ IT FAILS CLOSED ONTO TODAY'S WORDING. An absent, unreadable, malformed or
STALE stamp yields None and the alert says exactly what it says now. A
mislabelled shutdown would be worse than an unlabelled one, so every failure
path degrades to the generic sentence rather than to a guess.

⚠️ AND STALENESS IS THE ONE THAT MATTERS. The writer stamps and the process is
signalled seconds later; a file left behind by a halt that never completed must
NOT make next week's hand stop claim it was the backstop. `MAX_AGE_S` is the
whole guard, and `consume()` deletes on read so the ordinary path never leaves
one lying around at all.
"""
from __future__ import annotations

import os
import time

# The stamp is honoured only this many seconds after it is written. Both
# writers stamp IMMEDIATELY before signalling, so the real gap is < 5s; 120
# is generous enough to survive a slow box and far short of any later stop.
MAX_AGE_S = 120

_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "SHUTDOWN_CAUSE")


def path() -> str:
    """OT_SHUTDOWN_CAUSE overrides, so a checker never writes the real one."""
    return os.environ.get("OT_SHUTDOWN_CAUSE", _DEFAULT)


def record(cause: str) -> bool:
    """Stamp why the box is going down. Never raises — see the module docstring.

    ⚠️ THE FORMAT IS `<epoch>|<text>` AND `devtools.sh` WRITES IT TOO, in
    shell, from `bake()`. Two writers of one format is a coupling, so
    `tests/check_shutdown_cause.py` C5 drives the SHELL writer and reads it
    back through THIS parser rather than trusting that they agree.
    """
    try:
        p = path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("%d|%s\n" % (int(time.time()), cause.strip()))
        return True
    except Exception:                                           # noqa: BLE001
        return False


def consume(now: float | None = None) -> str | None:
    """The stamped cause if one was written in the last MAX_AGE_S, else None.

    Deletes the stamp on read: it describes ONE shutdown, and a stamp that
    outlives its own event is the stale-snapshot class this repo keeps paying
    for. A delete that fails is ignored — `MAX_AGE_S` is the real guard.
    """
    p = path()
    try:
        with open(p, encoding="utf-8") as fh:
            raw = fh.read().strip()
    except Exception:                                           # noqa: BLE001
        return None
    try:
        os.unlink(p)
    except Exception:                                           # noqa: BLE001
        pass
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


def label(default: str, now: float | None = None) -> str:
    """The stamped cause, or `default` when there is not a fresh one.

    🔑 THIS EXISTS AS ITS OWN FUNCTION SO THE DECISION CAN BE DRIVEN. The
    caller is a signal handler defined INSIDE `main()`, which a checker cannot
    reach without running the bot — and r43 already paid for inlining a
    behaviour into a 700-line dispatch: "a behaviour reachable only through a
    700-line dispatch is a behaviour that stops being tested." The choosing
    happens here, where `tests/check_shutdown_cause.py` C7/C7b/C7c drive it
    with a fresh, a stale and an absent stamp and assert the STRING RETURNED.
    """
    try:
        named = consume(now=now)
    except Exception:                                           # noqa: BLE001
        return default
    return named or default
