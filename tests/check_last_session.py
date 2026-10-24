#!/usr/bin/env python3
"""tests/check_last_session.py — v1.0
THE PREVIOUS SESSION IS THE PREVIOUS SESSION, EVEN SECONDS AFTER A HANDOFF.

v1.0  2026-09-26 — OTV4TEST r151. tools/last_session.py picked "the most recent
      transcript not written in the last 90s", so on a handoff — the new session
      starting seconds after the old one's last write — it skipped the thread that
      just ended and digested the one before. It now knows THIS session by
      CLAUDE_CODE_SESSION_ID. Mechanism from mainline (dtp r446). Operator: "Send it".

  L1  a handoff: THIS session (id in the env) written now, the PREVIOUS written 10s
      ago, an OLDER one written an hour ago -> the digest names the PREVIOUS
      (HEAD named the older one)
  L2  CLAUDE_SESSION_ID alone is honoured the same way
  L3  --list marks exactly THIS session live, by id — not the just-ended one
  L4  no id in the environment -> the 90s fallback still runs, and SAYS it is a guess

Nothing real is read: the transcript directory is a scratch directory with three
synthetic files. Run:  python3 tests/check_last_session.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS: list = []
THIS, PREV, OLD = "aaaa1111-this", "bbbb2222-prev", "cccc3333-old"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if detail and not ok else ""))
    if not ok:
        PROBLEMS.append(name.split()[0])


def fixture() -> str:
    d = tempfile.mkdtemp(prefix="check_last_session.")
    now = time.time()
    for sid, age, words in ((THIS, 1, "this session"), (PREV, 10, "the thread that just ended"),
                            (OLD, 3600, "an older thread")):
        p = os.path.join(d, sid + ".jsonl")
        with open(p, "w") as fh:
            fh.write(json.dumps({"type": "user", "timestamp": "2026-09-26T20:00:00Z",
                                 "message": {"content": words}}) + "\n")
        os.utime(p, (now - age, now - age))
    return d


def run(d: str, argv: list, env: dict) -> str:
    spec = importlib.util.spec_from_file_location("last_session_uut", os.path.join(ROOT, "tools", "last_session.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.DIR = d
    m.revisions = lambda a, b: []                       # never read the live repo's log
    saved = {k: os.environ.get(k) for k in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")}
    old_argv = sys.argv
    buf = io.StringIO()
    try:
        for k in saved:
            os.environ.pop(k, None)
        os.environ.update(env)
        sys.argv = ["last_session.py"] + argv
        with contextlib.redirect_stdout(buf):
            m.main()
    finally:
        sys.argv = old_argv
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return buf.getvalue()


def main() -> int:
    print("last_session: the previous session, by id")
    d = fixture()
    for name, fn in (
        ("L1", lambda: (lambda out: check("L1 handoff: CLAUDE_CODE_SESSION_ID -> the thread that just ended, not the one before",
                                          "PREVIOUS SESSION  bbbb2222" in out and "just ended" in out,
                                          out.splitlines()[1] if len(out.splitlines()) > 1 else out))(
            run(d, [], {"CLAUDE_CODE_SESSION_ID": THIS}))),
        ("L2", lambda: (lambda out: check("L2 CLAUDE_SESSION_ID alone is honoured",
                                          "PREVIOUS SESSION  bbbb2222" in out, out.splitlines()[1] if len(out.splitlines()) > 1 else out))(
            run(d, [], {"CLAUDE_SESSION_ID": THIS}))),
        ("L3", lambda: (lambda out: check("L3 --list marks THIS session live by id, and only it",
                                          [l[:8] for l in out.splitlines() if "THIS SESSION" in l] == ["aaaa1111"], out))(
            run(d, ["--list"], {"CLAUDE_CODE_SESSION_ID": THIS}))),
        ("L4", lambda: (lambda out: check("L4 no id -> the 90s fallback runs and says it is a guess",
                                          "PREVIOUS SESSION  cccc3333" in out and "NO session id" in out, out.splitlines()[1] if len(out.splitlines()) > 1 else out))(
            run(d, [], {}))),
    ):
        try:
            fn()
        except Exception as exc:                        # noqa: BLE001
            check(f"{name} (did not run)", False, f"raised {type(exc).__name__}: {exc}")
    print("GREEN" if not PROBLEMS else f"RED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
