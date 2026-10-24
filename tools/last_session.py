#!/usr/bin/env python3
"""
tools/last_session.py  v1.2 — WHAT THE OPERATOR SAID LAST TIME.
v1.2  2026-10-03  OTV4TEST r191 (AUD.2) — Eastern time comes from the tz database (zoneinfo), not a fixed
      UTC-4: from 2026-11-01 (DST ends) every time this digest printed would have been an hour late.

v1.1  2026-09-26  OTV4TEST r151 — THIS SESSION IS KNOWN BY ITS ID, NOT GUESSED BY ITS CLOCK.
      The default pick was "the most recent transcript NOT written in the last 90s", on
      the belief that a file touched that recently is THIS session. On a HANDOFF that is
      false: the new session starts seconds after the old one's last write, so the thread
      that JUST ENDED is inside the window, gets skipped as "this session", and the digest
      hands over the one BEFORE it — the exact misfire mainline's dtp transcript_text.py
      suffered on 2026-09-26 (1-REPORTER, dtp r446, which sent the mechanism). The harness
      exports CLAUDE_CODE_SESSION_ID, measured equal to this session's transcript id; it is
      now read first (then CLAUDE_SESSION_ID), and the 90s guess runs ONLY when no id is
      known. `--list` marks THIS SESSION the same way. Gate: tests/check_last_session.py.
      Operator: "Send it".

v1.0  2026-09-18  OTV4TEST r41. Operator: *"is it possible to include in our
      handoff script to have you read the last conversation so you're caught
      up?"*

WHY THIS IS A DIGEST AND NOT THE TRANSCRIPT. The conversations in
`~/.claude/projects/-home-ubuntu-options-trader/` total 50MB; the largest single
session is bigger than a context window. "Read the last conversation" taken
literally spends the whole budget before any work starts, and spends most of it
on MY OWN output — tool calls, file dumps, reasoning — which is the part least
worth re-reading.

🔑 THE OPERATOR'S OWN MESSAGES ARE THE SIGNAL. They are the rulings, the
corrections and the scope; everything else in the file is downstream of them.
118 user messages fit in a few pages. So this prints HIS words, in order, with
timestamps — plus the revisions that landed in that window, so a ruling can be
matched to what shipped.

⚠️ IT NAMES THE FILE IT CHOSE. A digest that silently picks the wrong session is
worse than no digest, so the header states the session id and span and the
selection rule, and `--list` shows every candidate.

Usage:
  python3 tools/last_session.py                 # the previous session
  python3 tools/last_session.py --list          # every session, newest first
  python3 tools/last_session.py --session 7f83  # one by id prefix
  python3 tools/last_session.py --full          # don't trim long messages
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys

DIR = os.path.expanduser("~/.claude/projects/-home-ubuntu-options-trader")
try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")        # r191: was a fixed UTC-4, an hour wrong from 11-01
except Exception:                                               # noqa: BLE001
    ET = dt.timezone(dt.timedelta(hours=-4))
LIVE_WINDOW_S = 90          # the FALLBACK only: a file touched this recently is THIS session


def _self_id() -> str:
    """r151 — this session's transcript id, from the harness, or '' when unknown."""
    return (os.environ.get("CLAUDE_CODE_SESSION_ID")
            or os.environ.get("CLAUDE_SESSION_ID") or "").strip()


def _is_self(path: str, now: float, sid: str) -> bool:
    """THIS session: by id when the harness gives one — never guessed then — else by
    the 90s write window (which misfires on a handoff; see v1.1)."""
    if sid:
        return os.path.basename(path).startswith(sid)
    return (now - os.path.getmtime(path)) < LIVE_WINDOW_S


def _et(ts: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(ET)
    except Exception:                                           # noqa: BLE001
        return None


def _text(d: dict) -> str:
    """The human-readable text of one transcript entry, or ''."""
    m = d.get("message") or {}
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def scan(path: str) -> dict:
    """One pass: user messages, last assistant message, span."""
    users, last_asst, first, last = [], "", None, None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:                                   # noqa: BLE001
                continue
            t = _et(d.get("timestamp", ""))
            if t:
                first = first or t
                last = t
            kind = d.get("type")
            if kind not in ("user", "assistant"):
                continue
            txt = _text(d).strip()
            if not txt:
                continue
            if kind == "assistant":
                last_asst = txt
                continue
            # ⚠️ a "user" entry is also how TOOL RESULTS and system reminders
            # arrive. Neither is the operator speaking, and including them is
            # what would make this a transcript again.
            if txt.startswith("<") or txt.startswith("[Request interrupted"):
                continue
            users.append((t, txt))
    return {"path": path, "users": users, "last_asst": last_asst,
            "first": first, "last": last}


def sessions() -> list:
    out = []
    for f in glob.glob(os.path.join(DIR, "*.jsonl")):
        out.append((os.path.getmtime(f), f))
    return [f for _, f in sorted(out, reverse=True)]


def revisions(a: dt.datetime, b: dt.datetime) -> list:
    """Revisions committed inside the session's span — ruling -> what shipped."""
    try:
        r = subprocess.run(
            ["git", "-C", os.path.expanduser("~/options-trader"), "log",
             f"--since={a.isoformat()}", f"--until={b.isoformat()}",
             "--pretty=%h %s"], capture_output=True, text=True, timeout=30)
        return [l[:160] for l in r.stdout.splitlines() if l.strip()]
    except Exception:                                           # noqa: BLE001
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--session", default="")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--max-chars", type=int, default=900)
    a = ap.parse_args()

    files = sessions()
    if not files:
        print(f"no transcripts in {DIR}")
        return 1

    if a.list:
        now = dt.datetime.now().timestamp()
        sid = _self_id()
        print(f"{'session':10s} {'span (ET)':34s} {'msgs':>5s}  state")
        print("-" * 72)
        for f in files:
            s = scan(f)
            live = _is_self(f, now, sid)
            span = (f"{s['first']:%m-%d %H:%M} → {s['last']:%m-%d %H:%M}"
                    if s["first"] and s["last"] else "?")
            print(f"{os.path.basename(f)[:8]:10s} {span:34s} {len(s['users']):5d}  "
                  f"{'THIS SESSION (live)' if live else ''}")
        return 0

    if a.session:
        cand = [f for f in files if os.path.basename(f).startswith(a.session)]
        if not cand:
            print(f"no session starting '{a.session}' — try --list")
            return 1
        pick, rule = cand[0], f"--session {a.session}"
    else:
        now = dt.datetime.now().timestamp()
        sid = _self_id()
        older = [f for f in files if not _is_self(f, now, sid)]
        if not older:
            print("only the live session exists — nothing previous to read")
            return 1
        pick = older[0]
        rule = (f"most recent transcript that is not this session (id {sid[:8]}, "
                "from the harness)" if sid else
                f"most recent transcript not written in the last {LIVE_WINDOW_S}s "
                "(NO session id in the environment — a guess that misfires on a handoff)")

    s = scan(pick)
    print("=" * 78)
    print(f"PREVIOUS SESSION  {os.path.basename(pick)[:8]}")
    print(f"  span    : {s['first']:%Y-%m-%d %H:%M} → {s['last']:%Y-%m-%d %H:%M} ET"
          if s["first"] else "  span    : ?")
    print(f"  operator: {len(s['users'])} messages")
    print(f"  selected: {rule}")
    print("=" * 78)

    if s["first"] and s["last"]:
        revs = revisions(s["first"], s["last"])
        if revs:
            print("\nREVISIONS THAT LANDED IN THAT WINDOW")
            for r in revs:
                print(f"  {r}")

    print("\nWHAT THE OPERATOR SAID, IN ORDER")
    print("-" * 78)
    for i, (t, txt) in enumerate(s["users"], 1):
        body = txt if a.full else (
            txt if len(txt) <= a.max_chars else txt[:a.max_chars] + f" …[+{len(txt)-a.max_chars} chars]")
        stamp = f"{t:%m-%d %H:%M}" if t else "  ?  "
        print(f"\n[{i:3d}] {stamp}\n{body}")

    if s["last_asst"]:
        tail = s["last_asst"]
        if not a.full and len(tail) > 3000:
            tail = tail[-3000:]
        print("\n" + "-" * 78)
        print("HOW IT ENDED (final assistant message)")
        print("-" * 78)
        print(tail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
