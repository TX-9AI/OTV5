#!/usr/bin/env python3
"""tests/check_disk_watch.py — v1.3
v1.3  2026-09-06 — r290 / DEV.12. D9 pins that no message contains a character
`parse_mode="HTML"` will choke on. The WAL marker was `<-- WAL`; Telegram
answered 400 "Unsupported start tag" and `send()` returned False, which reads
exactly like an unconfigured token.

v1.2  2026-09-06 — r287 / DEV.9. D8 pins the SENTINEL DRILL: it fires through
the live path, it is consumed so it cannot loop, and it bypasses the rate limit.

v1.1  2026-09-06 — r286 / DEV.8. D7 pins that a send which RETURNS FALSE is
reported as a failure and RE-ARMS. v1.0 returned True regardless of the result,
so an unconfigured Telegram would have logged a successful alert and paged
nobody — and left `over` set, so every later cycle stayed silent too.

v1.0  2026-09-06 — r285 / DEV.7.

🔴 THIS RUNS INSIDE `candle_feed`'s LOOP, ON FIFTEEN LIVE BOXES. A bug here does
not cost an alert — it costs the TAPE. So D5 asserts the one property that
matters more than any of the others: **`check()` never raises**, whatever the
filesystem or the sender does.

⚠️ AND THE ALERT MUST FIRE ONCE PER EPISODE, NOT ONCE PER CYCLE. A box sitting
at 93% that paged every five minutes would train the operator to skim exactly
the alert that matters (§17) — and an alert that fires once and never re-arms is
the opposite failure, silent on the next crossing. Both directions are pinned.
"""
import os
import sys
import tempfile
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


class _Sender:
    def __init__(self, boom=False):
        self.sent, self.boom = [], boom

    def send(self, msg):
        if self.boom:
            raise RuntimeError("telegram down")
        self.sent.append(msg)
        return True


def _arm(D, pct):
    """Force the next check() to see `pct` and to not be rate-limited."""
    D._state["last_check"] = 0.0
    D._pct_used = lambda path="/": pct


def main():
    try:
        import data.disk_watch as D
    except Exception as exc:                                # noqa: BLE001
        check("D0 data.disk_watch imports", False, str(exc))
        print("\nRED — 1 failed: D0")
        return 1
    check("D0 data.disk_watch imports", True)
    real_pct = D._pct_used

    # ══ 🔴 D1 — CROSSING PAGES, AND THE MESSAGE IS ACTIONABLE ═════════════
    D._state.update(over=False, last_check=0.0)
    _arm(D, 93.0)
    s = _Sender()
    sent = D.check(sender=s, instrument="QQQ")
    check("D1 crossing the threshold pages", sent and len(s.sent) == 1,
          f"sent={len(s.sent)}")
    check("D1b ...and the message names the box and the percentage",
          s.sent and "QQQ" in s.sent[0] and "93%" in s.sent[0],
          (s.sent[0].splitlines()[0][:56] if s.sent else ""))

    # ══ 🔴 D2 — ONCE PER EPISODE, NOT ONCE PER CYCLE ══════════════════════
    _arm(D, 94.0)
    D.check(sender=s, instrument="QQQ")
    _arm(D, 95.0)
    D.check(sender=s, instrument="QQQ")
    check("D2 staying over the threshold does NOT page again",
          len(s.sent) == 1, f"sent={len(s.sent)}")

    # ══ 🔴 D3 — AND IT RE-ARMS ON RECOVERY ════════════════════════════════
    # An alert that fires once and never re-arms is silent on the next
    # crossing — the opposite failure, and the harder one to notice.
    _arm(D, 40.0)
    D.check(sender=s, instrument="QQQ")
    check("D3 dropping back under re-arms it", D._state["over"] is False)
    _arm(D, 93.0)
    D.check(sender=s, instrument="QQQ")
    check("D3b ...so the NEXT crossing pages again", len(s.sent) == 2,
          f"sent={len(s.sent)}")

    # ══ ⚠️ D4 — THE CHEAP CHECK IS RATE-LIMITED ═══════════════════════════
    # The loop runs far more often than every CHECK_EVERY_S; without the gate
    # the walk could be triggered on consecutive cycles.
    D._state.update(over=False)
    D._state["last_check"] = 0.0
    D._pct_used = lambda path="/": 93.0
    D.check(sender=s, instrument="QQQ")
    before = len(s.sent)
    D._state["over"] = False          # pretend recovery WITHOUT clearing the clock
    fired = D.check(sender=s, instrument="QQQ")
    check("D4 a second call inside the interval does no work",
          not fired and len(s.sent) == before, f"sent={len(s.sent)}")

    # ══ 🔴 D5 — IT NEVER RAISES INTO THE FEED ═════════════════════════════
    # This is the property that outranks the rest: the caller is the candle
    # feed's loop on fifteen live boxes.
    D._state.update(over=False, last_check=0.0)
    D._pct_used = lambda path="/": (_ for _ in ()).throw(OSError("no statvfs"))
    try:
        r = D.check(sender=s, instrument="QQQ")
        check("D5 a failing statvfs is swallowed, not raised", r is False)
    except Exception as exc:                                # noqa: BLE001
        check("D5 a failing statvfs is swallowed, not raised", False,
              f"{type(exc).__name__}")
    D._state.update(over=False, last_check=0.0)
    _arm(D, 93.0)
    try:
        r = D.check(sender=_Sender(boom=True), instrument="QQQ")
        check("D5b a sender that throws is swallowed, not raised", r is False)
    except Exception as exc:                                # noqa: BLE001
        check("D5b a sender that throws is swallowed, not raised", False,
              f"{type(exc).__name__}")
    D._state.update(over=False, last_check=0.0)
    _arm(D, 93.0)
    try:
        D.check(sender=None, instrument="QQQ")
        check("D5c a missing sender is swallowed, not raised", True)
    except Exception as exc:                                # noqa: BLE001
        check("D5c a missing sender is swallowed, not raised", False,
              f"{type(exc).__name__}")

    # ══ D6 — THE WALK RANKS FILES AND EXCLUDES WHAT IT SHOULD ═════════════
    D._pct_used = real_pct
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "feed_store.db"), "wb").write(b"x" * 3_000_000)
        open(os.path.join(tmp, "feed_store.db-wal"), "wb").write(b"x" * 2_000_000)
        open(os.path.join(tmp, "tiny"), "wb").write(b"x")
        os.symlink("/etc/hostname", os.path.join(tmp, "link"))
        got = D.largest_files(tmp, top=3)
        check("D6 largest-first ordering",
              [os.path.basename(p) for _, p in got][:2]
              == ["feed_store.db", "feed_store.db-wal"],
              str([os.path.basename(p) for _, p in got]))
        # ⚠️ lstat, so a symlink is measured as the LINK — otherwise a link into
        # another filesystem reintroduces what the device check excludes.
        check("D6b symlinks are not counted as files",
              not any(p.endswith("/link") for _, p in D.largest_files(tmp, top=9)))

    # ══ 🔴 D7 — A SEND THAT RETURNS FALSE IS A FAILURE, AND RE-ARMS ═══════
    # `TelegramSender.send` returns False silently when Telegram is
    # unconfigured. v1.0 ignored the result: it logged success and paged
    # nobody, and left the episode marked as reported so every later cycle
    # stayed quiet as well.
    class _Quiet:
        def send(self, msg):
            return False

    D._state.update(over=False, last_check=0.0)
    _arm(D, 93.0)
    sent = D.check(sender=_Quiet(), instrument="QQQ")
    check("D7 a send that returns False is reported as NOT delivered",
          sent is False, f"returned {sent}")
    check("D7b ...and re-arms, so the next cycle can try again",
          D._state["over"] is False)
    D._state["last_check"] = 0.0
    s2 = _Sender()
    D._pct_used = lambda path="/": 93.0
    check("D7c ...and it does try again", D.check(sender=s2, instrument="QQQ")
          and len(s2.sent) == 1, f"sent={len(s2.sent)}")

    # ══ 🔴 D8 — THE SENTINEL DRILL GOES THROUGH THE LIVE PATH ════════════
    # A drill invoked over SSH runs in a process with no credentials — that is
    # how two earlier versions reported success and delivered nothing.
    D._pct_used = real_pct
    with tempfile.TemporaryDirectory() as tmp:
        flag = os.path.join(tmp, "DRILL_DISK")
        D.DRILL_FLAG = flag
        open(flag, "w").close()
        s3 = _Sender()
        D._state.update(over=False, last_check=time.time())   # rate limit ARMED
        got = D.check(sender=s3, instrument="QQQ")
        check("D8 a drill flag sends through the live sender, bypassing the "
              "rate limit", got and len(s3.sent) == 1, f"sent={len(s3.sent)}")
        # 🔴 CONSUMED. A surviving flag would re-page every cycle until someone
        # noticed — a rehearsal turning the alert channel into a loop.
        check("D8b ...and the flag is consumed, so it cannot loop",
              not os.path.exists(flag))
        D.check(sender=s3, instrument="QQQ")
        check("D8c ...so the next cycle is silent", len(s3.sent) == 1,
              f"sent={len(s3.sent)}")
        check("D8d ...and the message is marked TEST",
              s3.sent and s3.sent[0].startswith("TEST - NOT REAL"),
              (s3.sent[0][:20] if s3.sent else ""))

    # ══ 🔴 D9 — NOTHING WE SEND CAN BREAK THE HTML PARSER ════════════════
    # `TelegramSender.send()` posts parse_mode="HTML" and returns False on a
    # non-200 — the SAME return as an unconfigured token, which is why one
    # character cost three rounds of credential hunting.
    check("D9 the drill message contains no raw `<`",
          "<" not in D.test_message("QQQ"))
    D._state.update(over=False, last_check=0.0)
    _arm(D, 93.0)
    s9 = _Sender()
    D.check(sender=s9, instrument="QQQ")
    check("D9b ...and neither does a real alert, whose lines carry FILE PATHS",
          s9.sent and "<" not in s9.sent[0],
          ("has <" if s9.sent and "<" in s9.sent[0] else "clean"))

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 20 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
