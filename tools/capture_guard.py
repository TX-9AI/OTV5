#!/usr/bin/env python3
"""
tools/capture_guard.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-24  CD.1 — BEFORE A BOX PUSHES, ASK THE WAREHOUSE WHO ELSE ALREADY PUSHES THIS SYMBOL. A second pusher
      into raw/.../sym=<SYM>/ does not error: latest-wins by pushed_at_utc silently overwrites the first box's rows in
      every report that reads them (SPX-TEST 10-03: 36 objects into mainline's sym=SPX; the 09-25 SOFI box about to
      push as QQQ). configure.sh item 14 asks this before it turns MANAGED on.
      HOW: a LIVE read, not a list (a list drifts: retirements, stopped boxes, a box that pushes when nobody thought it
      did). For each of the last LOOKBACK_DAYS calendar days and each of raw/trades and raw/candles, the newest
      object under dt=<D>/sym=<SYM>/ is read and its envelope's src_host compared with THIS box's hostname. Every
      other host is named with the last date it pushed, so a box stopped for a week still shows ("ip-... last pushed
      2026-10-14, 10 days ago").
      FAILS CLOSED: a warehouse that cannot be listed or read is not a clean pass.
Exit:  0 no other host pushes <SYM>   1 another host does (named)   2 unreadable (fail closed)   3 bad usage
Usage: python3 tools/capture_guard.py SYM [--host HOSTNAME]
"""
from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import warehouse_source as ws                                   # noqa: E402  the ONE reader

LOOKBACK_DAYS = 14
DATATYPES = ("trades", "candles")


def scan(sym: str, host: str, s3=None, today=None) -> tuple:
    """-> (rc, lines). rc as the module docstring."""
    try:
        s3 = s3 or ws.client()
    except Exception as exc:                                    # noqa: BLE001
        return 2, [f"UNREADABLE: no warehouse client ({type(exc).__name__}) - failing closed"]
    today = today or datetime.now(timezone.utc).date()
    seen, read, lines = {}, 0, []
    for i in range(LOOKBACK_DAYS):
        d = (today - timedelta(days=i)).isoformat()
        for dt in DATATYPES:
            pre = f"{ws.PREFIX}/{dt}/dt={d}/sym={sym}/"
            try:
                keys = []
                for page in s3.get_paginator("list_objects_v2").paginate(Bucket=ws.BUCKET, Prefix=pre):
                    keys += [o["Key"] for o in page.get("Contents", []) or []]
                if not keys:
                    continue
                env = json.loads(s3.get_object(Bucket=ws.BUCKET, Key=sorted(keys)[-1])["Body"].read())
                read += 1
            except Exception as exc:                            # noqa: BLE001
                return 2, [f"UNREADABLE: {pre} ({type(exc).__name__}) - failing closed"]
            h = str(env.get("src_host") or "?")
            if h != host and (h not in seen or d > seen[h]):
                seen[h] = d
    if not seen:
        lines.append(f"clean: no host other than {host} pushed sym={sym} to raw/trades or raw/candles in the last "
                     f"{LOOKBACK_DAYS} days ({read} object(s) read)")
        return 0, lines
    for h, d in sorted(seen.items(), key=lambda x: x[1], reverse=True):
        ago = (today - datetime.strptime(d, "%Y-%m-%d").date()).days
        lines.append(f"ANOTHER PUSHER: {h} last pushed sym={sym} on {d} ({ago} day(s) ago)")
    return 1, lines


def main(argv) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__.strip().splitlines()[-1])
        return 3
    sym = args[0].strip().upper()
    host = socket.gethostname()
    if "--host" in argv:
        host = argv[argv.index("--host") + 1]
    rc, lines = scan(sym, host)
    for ln in lines:
        print(ln)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
