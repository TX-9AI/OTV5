"""
utils/heartbeat.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-18  OTV4TEST r295 (LIVE.2) — ONE WRITER FOR data/BOT_HEARTBEAT, CALLABLE FROM A POLL LOOP.
      main._touch_heartbeat (r168) wrote the file once per main-loop pass and nothing else did, so a live close
      that polled the broker for its full LIVE_FILL_DEADLINE_SECONDS per position (30 s, serial, main.py's loop
      frozen meanwhile) could stand still for >= 180 s with five unfilled positions at 15:50 - and
      tools/emergency_watchdog.py (STALE_S = 180, two consecutive minutes) would SIGKILL the laddering bot at
      ~15:53. Audit 2026-10-18 C2. The two live poll loops (exit_engine._confirm_and_book_live_exit,
      order_confirm.confirm_order_fill) and flatten_all now touch this on every iteration.

      THE FILE'S FORMAT IS UNCHANGED: "<epoch> <note>" - main writes the tick number, the loops a short word.
      The watchdog reads only the mtime (emergency_watchdog.py:158). OT_HEARTBEAT_FILE moves it for ONE process
      (a checker that drives a live poll loop must not touch the live file); unset it is <repo>/data/BOT_HEARTBEAT,
      exactly main's path. NEVER RAISES: a heartbeat that could stop a close would be the hang it exists to catch;
      a failed write warns once per process.
"""
import logging
import os
import time

from utils.paths import _resolve

logger = logging.getLogger(__name__)
_warned = False


def path() -> str:
    return _resolve("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")


def touch(note: str = "", file_path: str = None) -> bool:
    """Write "<epoch> <note>" to the heartbeat file. True on success; False (warned once) on failure."""
    global _warned
    try:
        with open(file_path or path(), "w") as f:
            f.write(f"{time.time():.0f} {note}\n")
        return True
    except Exception as exc:                                    # noqa: BLE001
        if not _warned:
            _warned = True
            logger.warning("heartbeat write failed (%s) — the emergency watchdog will read this bot as stuck", exc)
        return False
