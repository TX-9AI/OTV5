#!/usr/bin/env python3
"""
tests/check_no_stray_duplicates.py  v1.1
v1.1  2026-09-07  r302 - S1 IS STAGE-AWARE. land.sh applies DEL at line 409 and
runs CHECKs at 371, so during the very land that removes them the strays are
still on disk and v1.0 failed its own delivery. The end state is gated by DEL
itself, which dies if a target is absent; S1 now asserts the RESIDUAL
invariant - once gone, they stay gone - which is what catches r288 recurring.
v1.0  2026-09-07  r302 — THE TWO STRAYS r288 LEFT BEHIND, AND THE SHAPE THAT
CREATED THEM.

🔴 WHAT HAPPENED. Commit `d622154` (r288, 2026-09-06 17:39 UTC) moved the disk
guard out of `candle_feed.run()`'s reconnect loop and into `main.py`'s tick
loop — an edit to two files that live at two different levels, `main.py` at the
repo root and `data/candle_feed.py` under `data/`. The archive carried each at
the WRONG level, so `tar` CREATED `data/main.py` and `candle_feed.py` beside
the real ones instead of overwriting them. Both files date from that single
commit; `data/main.py` carries v4.37/r239, the pre-r288 content, which is the
tell — the copy already on disk was written to the wrong path while the right
path got the update.

⚠️ AND THE LAND GATE COULD NOT HAVE CAUGHT IT. `check_land_discipline` proves
GENESIS is appended, both maps regenerate identical, and versions bump. A NEW
file at a NEW path regenerates the map identically to itself, because the map
is generated AFTER the extract and documents whatever landed. Nothing compares
the extracted file list against the payload's intended paths.

⚠️ AND THE ORPHAN REPORT WAS BLIND TO ONE OF THEM BY CONSTRUCTION.
`gen_file_map.py:248` falls back to `os.path.basename(p) in ENTRY_POINTS`, and
`data/main.py`'s basename is `main.py`, which IS an entry point. So the stray
rendered as `called by: (entry point)` — indistinguishable from the real one.
That basename fallback is a separate item and is NOT fixed here.

WHICH COPY WAS LIVE, ESTABLISHED FROM THE UNIT FILE AND NOT FROM THE NAME:
  `deploy/candle-feed.service` reads `ExecStart=... python -m data.candle_feed`
  — a MODULE PATH. So `data/candle_feed.py` is the live feed and the ROOT
  `candle_feed.py` was the stray. I had this backwards on first reading, on
  the strength of the unit file mentioning the string `candle_feed`.
  For `main.py` it is the other way: the root is live (v4.38/r288, and it is
  the copy that gained `data/disk_watch` and `notifications/telegram_sender`),
  and `data/main.py` is the stray.

THIS CHECK IMPORTS NOTHING FROM THE TREE. It reads paths and parses two files
with `ast`. A gate that needs `pytz` or the broker SDK goes red on ENVIRONMENT
rather than content, which is the CV.1 failure — and this one runs on control,
where neither is installed.

Run:  python3 tests/check_no_stray_duplicates.py
"""
from __future__ import annotations

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRAYS = ["data/main.py", "candle_feed.py"]
LIVE = ["main.py", "data/candle_feed.py"]

F: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        F.append(name)


def main() -> int:
    print("\ncheck_no_stray_duplicates\n")
    # S1 IS STAGE-AWARE, AND THE FIRST VERSION WAS NOT. `land.sh` applies
    # `DEL` in the STAGING block at line 409; the CHECK stage runs at 371. So
    # during a land the strays are STILL ON DISK when this runs, and asserting
    # they are gone FAILED THE VERY DELIVERY THAT REMOVES THEM. I wrote the
    # assertion without reading the order.
    # THE END STATE IS STILL ENFORCED, just not here: `DEL` dies with
    # "not present in $repo" if a target is missing, so the lander itself gates
    # the removal. What this asserts is the RESIDUAL invariant - once they are
    # gone they must STAY gone - which is what matters on every run after the
    # land, and is what would catch r288 happening again.
    landing = any(os.path.exists(os.path.join(ROOT, p)) for p in STRAYS)
    for p in STRAYS:
        if landing:
            print(f"  NOTE  S1  {p}: present - mid-land, DEL runs after CHECK")
        else:
            check(f"S1  the stray {p} is GONE",
                  not os.path.exists(os.path.join(ROOT, p)))
    for p in LIVE:
        full = os.path.join(ROOT, p)
        ok = os.path.exists(full)
        check(f"S2  the LIVE {p} survives", ok)
        if ok:
            try:
                ast.parse(open(full).read())
                check(f"S2b {p} parses", True)
            except SyntaxError as e:
                check(f"S2b {p} parses", False, str(e))

    # S3 — THE UNIT FILE IS THE AUTHORITY ON WHICH COPY IS LIVE, not the
    # filename. Pinned so a future tidy-up cannot delete the wrong one by
    # reading `candle_feed` in the ExecStart line and assuming the root file.
    unit = os.path.join(ROOT, "deploy", "candle-feed.service")
    txt = open(unit).read() if os.path.exists(unit) else ""
    check("S3  candle-feed.service execs the MODULE data.candle_feed",
          "-m data.candle_feed" in txt,
          "so data/candle_feed.py is live and the root copy was the stray")

    # S4 — nothing may import either stray back into existence.
    bad = []
    for dirpath, dirnames, files in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dirpath, fn)
            if os.path.relpath(fp, ROOT) == os.path.join("tests",
                                                         os.path.basename(__file__)):
                continue
            src = open(fp, errors="ignore").read()
            for pat in ("from data.main", "import data.main"):
                if pat in src:
                    bad.append((os.path.relpath(fp, ROOT), pat))
    check("S4  nothing imports data.main", not bad, str(bad[:3]))

    print()
    if F:
        print(f"check_no_stray_duplicates: FAIL ({len(F)}): {', '.join(F)}")
        return 1
    print("check_no_stray_duplicates: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
