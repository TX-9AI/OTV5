"""data/disk_watch.py — v1.3

v1.3 (2026-09-06) — r290 / DEV.12. 🔴 THE WAL MARKER WAS `<-- WAL`, AND
`TelegramSender` POSTS WITH parse_mode="HTML". Telegram answered 400: *"can't
parse entities: Unsupported start tag \"--\" at byte offset 120"*. `send()`
returns False on a non-200, which is INDISTINGUISHABLE from an unconfigured
token — so three rounds went to credentials for one character. `alert_manager`
never hit it because its own v1.10 note says "escape BEFORE sending". This guard
calls the sender directly and now does both: the marker is `(WAL)`, and the
message is `html.escape`d, because a FILE PATH is not ours to trust either.



v1.2 (2026-09-06) — r287 / DEV.9. 🔴 THE DRILL IS A SENTINEL FILE NOW, BECAUSE
TWO ATTEMPTS TO REHEARSE FROM OUTSIDE THE SERVICE FAILED THE SAME WAY. A test
invoked over SSH runs with NO credentials: `setup_ec2.sh` writes
`Environment=TELEGRAM_TOKEN=` into the systemd UNIT, so a plain
`venv/bin/python` never had a token and never could. The second attempt sourced
`.env` — a mechanism `optionsbot` does not use — and reported `CONFIGURED=False`.
🔑 `MAINT_FLAG` in `candle_feed` already solved this shape: a file the RUNNING
service checks each cycle, "no restart, and it survives a bake". Touch
`data/DRILL_DISK`; the service sends the marked message through the REAL sender
in the REAL process. **A rehearsal that takes a different path from the live
alert is not a rehearsal** — which is precisely why the last two proved nothing.
⚠️ It is therefore NOT INSTANT: it fires within OT_DISK_CHECK_S. The menu item
says so, and confirms the flag was CONSUMED rather than claiming a delivery it
cannot see.



v1.1 (2026-09-06) — r286 / DEV.8. 🔴 IT RETURNED SUCCESS WITHOUT DELIVERING.
v1.0 called `sender.send()` and returned True regardless of the result, so an
unconfigured or down Telegram would have logged a successful alert and paged
NOBODY. `TelegramSender.send` returns False SILENTLY when `telegram_configured()`
is false — which is exactly how the menu's own test printed the message, exited
0, reported "1/1 succeeded" and delivered nothing.
⚠️ AND A FAILED SEND NOW RE-ARMS. Leaving `over` set would mark the episode as
reported when the operator never heard it, and every later cycle would stay
silent — a disk alert that goes quiet because the FIRST attempt failed is worse
than one that never existed.


v1.0 (2026-09-06) — r285 / DEV.7. THE BOX SAYS IT IS FULL. NOBODY ASKS IT.

🔴 THE OPERATOR'S FRAMING, AND IT IS WHY THIS LIVES ON THE BOX: *"it should be
a statement, not the answer to a question that we're constantly asking."* A
control-side poller would ask fifteen boxes every few minutes, forever, almost
always to hear "no" — and would inherit S3.19's failure, where `ssh_run` gives
22 seconds, returns `rc=255 ssh timeout`, and **leaves the remote process
running**. A `find /` on a nearly-full box is exactly the walk that outlasts 22
seconds, so the poller would abandon scans that then compete for the disk it was
worried about.

🔑 THE EC2 API CANNOT ANSWER THIS AT ALL. It knows a volume's SIZE, never how
full it is, so no amount of IAM substitutes — something must run ON the box. The
feed already does: it is the process writing the candles, holding the WAL open,
and filling the disk. **The thing consuming the space notices.**

⚠️ TWO COSTS, DELIBERATELY SPLIT. Every cycle costs one `os.statvfs` — a
syscall, microseconds, no subprocess. The EXPENSIVE half — walking the tree for
the five largest files — runs ONLY on the crossing, once per episode, on a box
that has already earned the attention.

⚠️ ONCE PER EPISODE, RE-ARMED ON RECOVERY. Cross the threshold, page, go quiet,
and re-arm only when it drops back under. A box sitting at 93% that paged every
cycle would train the operator to skim exactly the alert that matters (§17).

⚠️ 92%, NOT 99%. On a 14G volume 99% is ~140MB, and SQLite needs room for the
WAL PLUS a checkpoint that writes a second copy before replacing the original —
so at 99% the nightly reclaim's gated vacuum REFUSES and the box cannot dig
itself out. This fleet has been there: roots at 100%, the fleet blind
mid-session, QQQ and MU crash-looping. 92% still leaves room for the vacuum to
fit and for a box to be stopped deliberately rather than die.
"""
from __future__ import annotations

import html
import logging
import os
import stat
import time

log = logging.getLogger(__name__)

DISK_PCT_ALERT = int(os.environ.get("OT_DISK_PCT", "92"))
CHECK_EVERY_S = float(os.environ.get("OT_DISK_CHECK_S", "300"))
TOP_N = 5
# ⚠️ THE WALK IS BOUNDED. An unbounded `os.walk("/")` on a sick box is the same
# mistake as the poller's `find` — it can run long enough to matter. One
# filesystem only (no /proc, no mounts), and a wall-clock ceiling.
WALK_BUDGET_S = float(os.environ.get("OT_DISK_WALK_S", "20"))

# 🔴 r287 — THE DRILL IS A SENTINEL FILE, BECAUSE A DRILL RUN OUTSIDE THE
# SERVICE IS NOT A DRILL. Two attempts failed the same way: a test invoked over
# SSH runs in a process with NO credentials — `setup_ec2.sh` writes
# `Environment=TELEGRAM_TOKEN=` into the systemd UNIT, so a plain
# `venv/bin/python` never had a token and never could. The second attempt
# sourced `.env`, a mechanism `optionsbot` does not use, and reported
# `CONFIGURED=False`.
# 🔑 THE HOUSE IDIOM ALREADY SOLVES IT. `MAINT_FLAG` in `candle_feed` is a file
# the RUNNING service checks each cycle — main.py's own note: "no restart, and
# it survives a bake". The operator touches a file; the SERVICE does the work,
# in its own environment, by the REAL code path.
DRILL_FLAG = os.environ.get(
    "OT_DISK_DRILL_FLAG",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "DRILL_DISK"))

_state = {"over": False, "last_check": 0.0}


def _drill_requested() -> bool:
    """True if a drill sentinel is present. Consumes it.

    ⚠️ CONSUMED BEFORE THE SEND. If the unlink failed afterwards the box would
    re-page every cycle until someone noticed — a rehearsal turning the alert
    channel into a loop. Mirrors `_maintenance_now`'s discipline, inverted:
    the safe default here is silence, not action.
    """
    try:
        if not os.path.exists(DRILL_FLAG):
            return False
        os.unlink(DRILL_FLAG)
        return True
    except Exception:                                       # noqa: BLE001
        log.warning("disk_watch: drill flag unreadable", exc_info=True)
        return False


def _pct_used(path: str = "/") -> float:
    st = os.statvfs(path)
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    return 0.0 if total <= 0 else (total - free) * 100.0 / total


def _human(n: int) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024.0
    return f"{n:.1f}TB"


def largest_files(root: str = "/", top: int = TOP_N, budget_s: float = None):
    """The `top` largest files under `root`, largest first. -> [(bytes, path)].

    ⚠️ ONE FILESYSTEM, ONE TIME BUDGET. `os.walk` with `topdown=True` lets us
    prune before descending: anything on another device is skipped, so /proc and
    mounted volumes never cost anything. The budget stops a pathological tree
    from turning a 5-minute check into a 5-minute stall.
    """
    budget = WALK_BUDGET_S if budget_s is None else budget_s
    deadline = time.time() + budget
    try:
        dev = os.stat(root).st_dev
    except OSError:
        return []
    best: list[tuple[int, str]] = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root, topdown=True,
                                                onerror=lambda e: None):
        if time.time() > deadline:
            truncated = True
            break
        keep = []
        for d in dirnames:
            try:
                if os.stat(os.path.join(dirpath, d)).st_dev == dev:
                    keep.append(d)
            except OSError:
                continue
        dirnames[:] = keep
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            # ⚠️ REGULAR FILES ONLY. `lstat` so a symlink is measured as the
            # link, not its target — otherwise a link into another filesystem
            # reintroduces exactly what the device check above excludes.
            # (A first cut wrote this guard as a garbled conditional that always
            # evaluated False and filtered nothing; it "worked" because
            # os.walk's filenames are already non-directories.)
            if not stat.S_ISREG(st.st_mode):
                continue
            best.append((st.st_size, p))
        if len(best) > 20000:
            best.sort(reverse=True)
            del best[top * 4:]
    best.sort(reverse=True)
    if truncated:
        log.warning("disk_watch: file walk hit its %.0fs budget — the list may "
                    "be incomplete", budget)
    return best[:top]


def check(sender=None, instrument: str = "?") -> bool:
    """One cycle. Returns True if an alert was sent. NEVER raises.

    🔑 THE CHEAP CHECK IS THE ONLY THING THAT RUNS NORMALLY. `_pct_used` is a
    statvfs; the walk happens after the threshold is crossed and not before.
    """
    # ⚠️ CHECKED BEFORE THE RATE LIMIT. A rehearsal the operator just asked for
    # must not wait out an interval that exists to keep the STEADY STATE cheap.
    if _drill_requested():
        msg = test_message(instrument)
        log.warning("disk_watch: DRILL requested — sending via the live path")
        if sender is None:
            log.error("disk_watch: DRILL not delivered — no sender")
            return False
        try:
            ok = bool(sender.send(msg))
            log.warning("disk_watch: DRILL delivered=%s", ok)
            return ok
        except Exception as exc:                            # noqa: BLE001
            log.error("disk_watch: DRILL send failed (%s)", exc)
            return False

    now = time.time()
    if now - _state["last_check"] < CHECK_EVERY_S:
        return False
    _state["last_check"] = now
    try:
        pct = _pct_used("/")
    except Exception as exc:                                # noqa: BLE001
        log.warning("disk_watch: statvfs failed (%s)", exc)
        return False

    if pct < DISK_PCT_ALERT:
        if _state["over"]:
            # ⚠️ RE-ARM. Without this the next crossing is silent, which is the
            # failure mode of every once-only alert ever written.
            log.info("disk_watch: %s back under %d%% (%.1f%%) — re-armed",
                     instrument, DISK_PCT_ALERT, pct)
            _state["over"] = False
        return False

    if _state["over"]:
        return False                                        # already paged
    _state["over"] = True

    files = largest_files()
    # ⚠️ THE LOG GETS THE FULL PATHS, TELEGRAM GETS THE BASENAMES. This is
    # `send_blind_alert`'s own doctrine: "a phone alert that needs scrolling is
    # one that gets skimmed during exactly the minutes it matters."
    log.error("disk_watch: %s at %.1f%% — largest files: %s", instrument, pct,
              "; ".join(f"{_human(s)} {p}" for s, p in files))

    lines = [f"🔴 DISK {pct:.0f}% on {instrument} — act before the close."]
    for size, path in files:
        mark = "  (WAL)" if path.endswith("-wal") else ""
        lines.append(f"  {_human(size):>8}  {os.path.basename(path)}{mark}")
    if any(p.endswith("-wal") for _, p in files):
        # 🔑 SAID ONLY WHEN IT APPLIES. A -wal among the largest files means
        # checkpoints are not landing — one cannot complete while a connection
        # holds a read, which is why the nightly reclaim stops services first.
        lines.append("  a WAL that large means checkpoints are not landing.")
    # 🔴 r290 — ESCAPED, AND THE MARKER NO LONGER CONTAINS `<`.
    # `TelegramSender.send()` posts with parse_mode="HTML". The marker was
    # "<-- WAL", so Telegram answered: 400 Bad Request, "can't parse entities:
    # Unsupported start tag \"--\"" — and `send()` returns False on a non-200,
    # which read exactly like an unconfigured token. Three rounds were spent on
    # credentials for one character.
    # ⚠️ `alert_manager` NEVER HIT THIS because its v1.10 note says "escape
    # BEFORE sending — TelegramSender uses parse_mode=HTML". This guard calls
    # the sender directly and so must do the same: a FILE PATH is not ours to
    # trust either.
    msg = html.escape("\n".join(lines))

    if sender is None:
        log.error("disk_watch: no sender — alert NOT delivered:\n%s", msg)
        return False
    try:
        # 🔴 r286 — THE RETURN VALUE IS HONOURED. v1.0 called `send()` and
        # returned True regardless, so an unconfigured or down Telegram would
        # have logged a successful alert and paged NOBODY. `TelegramSender.send`
        # returns False silently when `telegram_configured()` is false — which
        # is exactly how the 2026-09-06 menu test printed the message, exited 0,
        # reported "1/1 succeeded" and delivered nothing.
        # ⚠️ AND A FAILED SEND RE-ARMS. Leaving `over` set would mark the
        # episode as reported when the operator never heard it, and the next
        # cycle would stay silent — a disk alert that is silent because the
        # FIRST attempt failed is the worst of both designs.
        ok = bool(sender.send(msg))
        if not ok:
            _state["over"] = False
            log.error("disk_watch: NOT DELIVERED (sender returned false — "
                      "Telegram unconfigured or down); alert text:\n%s", msg)
        return ok
    except Exception as exc:                                # noqa: BLE001
        _state["over"] = False
        log.error("disk_watch: send failed (%s); alert text:\n%s", exc, msg)
        return False


def test_message(instrument: str = "QQQ") -> str:
    """The alert as it would read, for the menu's test prompt. Sends nothing."""
    # ⚠️ ESCAPED FOR THE SAME REASON — the drill must travel the same bytes as
    # the real alert, or it is not a rehearsal.
    return html.escape("TEST - NOT REAL\n"
            f"🔴 DISK 93% on {instrument} — act before the close.\n"
            "     1.4GB  feed_store.db\n"
            "   820.0MB  feed_store.db-wal  (WAL)\n"
            "   210.0MB  trades.db\n"
            "  a WAL that large means checkpoints are not landing.")
