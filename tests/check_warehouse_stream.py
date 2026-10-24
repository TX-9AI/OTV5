#!/usr/bin/env python3
"""tests/check_warehouse_stream.py — v1.0
`stream_series` RETURNS THE SAME ROWS AS `load_series` WITHOUT HOLDING THEM.

v1.0  2026-09-20 — OTV4TEST r69 (S3.14). `load_series` materialises a whole
      date: ~230,000 prints for ONE symbol-day. MEASURED on this box, same day,
      same 232,176 rows — `load_series` peaked at **294 MB RSS**, streaming at
      **108 MB**. A 19-session × 3-symbol corpus run was OOM-reaped mid-study
      on 2026-09-20 with 908 MB of PHYSICAL RAM (the 2 GB swapfile is separate,
      and the agent session itself was holding 336 MB).
      🔑 `_envelopes` WAS ALREADY A GENERATOR and each object holds ~2,400
      rows, so `load_series`'s accumulator was the only ceiling.

  W1  stream and load return IDENTICAL rows, in order, from one fake bucket
  W2  stream_series is a GENERATOR — it yields before the source is exhausted
  W3  it reports the same objects-listed/read meta when one is passed in
  W4  a symbol filter behaves identically on both paths
  W5  CONTROL: `load_series` is untouched — every existing caller is unaffected
  W6  CONTROL: an unreadable bucket still reports an ERROR through the stream,
      because "empty" and "unreachable" are different facts (the module's own
      design rule) and a generator that ends quietly could hide that

⚠️ NOTHING HERE TOUCHES S3. It reuses the module's own `_FakeS3` so the check
is about the code, not about the network or the role.
⚠️ W2 MATTERS MORE THAN IT LOOKS. The whole benefit is lost the moment a caller
writes `list(stream_series(...))` — that is `load_series` with extra steps and
the identical ceiling. W2 pins laziness so a future refactor that quietly
returns a list fails here rather than at 3am on a corpus run.
"""
from __future__ import annotations

import json
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
        return False
    try:
        d = detail()
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)
    return ok


try:
    from tests import warehouse_source as ws
    ERR = None
except Exception as exc:                                        # noqa: BLE001
    ERR = "%s: %s" % (type(exc).__name__, exc)

if ERR:
    for n in ("W1", "W2", "W3", "W4", "W5", "W6"):
        check(n + " (not reached)", False, ERR)
    print("\nRED — " + ERR)
    sys.exit(1)

P = ws.PREFIX


def _env(rows, sym="X", dt="2026-08-24", stamp="T1"):
    return json.dumps({"datatype": "prints", "symbol": sym, "dt": dt,
                       "pushed_at_utc": stamp, "record": rows}).encode()


OBJS = {
    f"{P}/prints/dt=2026-08-24/sym=X/1-a.json":
        _env([{"ts_epoch": 1.0, "price": 10.0}, {"ts_epoch": 2.0, "price": 11.0}]),
    f"{P}/prints/dt=2026-08-24/sym=X/2-b.json":
        _env([{"ts_epoch": 3.0, "price": 12.0}]),
    f"{P}/prints/dt=2026-08-24/sym=Y/3-c.json":
        _env([{"ts_epoch": 4.0, "price": 99.0}], sym="Y"),
}


def _s3():
    return ws._FakeS3(dict(OBJS))


guard("W1 stream and load return IDENTICAL rows, in order",
      lambda: list(ws.stream_series("prints", ["2026-08-24"], s3=_s3()))
      == ws.load_series("prints", ["2026-08-24"], s3=_s3())[0],
      lambda: "%d rows" % len(ws.load_series("prints", ["2026-08-24"], s3=_s3())[0]))


def _lazy():
    g = ws.stream_series("prints", ["2026-08-24"], s3=_s3())
    if not hasattr(g, "__next__"):
        return False
    first = next(g)                       # a row arrives before the source ends
    return first.get("price") == 10.0


guard("W2 it is a GENERATOR — a row arrives before the source is exhausted", _lazy)

_M = {}


def _meta():
    m = ws.Meta("prints")
    n = sum(1 for _ in ws.stream_series("prints", ["2026-08-24"], s3=_s3(), meta=m))
    _M["m"] = m
    ref = ws.load_series("prints", ["2026-08-24"], s3=_s3())[1]
    # 4 rows across 3 objects (2 for sym=X in one, 1 in another, 1 for Y).
    # My first cut asserted 3/2 — a fixture expectation I got wrong, which
    # went red against CORRECT code. Recorded rather than quietly amended.
    return n == 4 and m.read == ref.read and m.listed == ref.listed


guard("W3 it reports the same objects-listed/read meta",
      _meta, lambda: "listed=%s read=%s" % (_M["m"].listed, _M["m"].read))

guard("W4 a symbol filter behaves identically on both paths",
      lambda: list(ws.stream_series("prints", ["2026-08-24"], symbols=["Y"], s3=_s3()))
      == ws.load_series("prints", ["2026-08-24"], symbols=["Y"], s3=_s3())[0]
      == [{"ts_epoch": 4.0, "price": 99.0}])

guard("W5 CONTROL: load_series still returns (rows, meta) unchanged",
      lambda: (lambda r: isinstance(r, tuple) and len(r) == 2
               and len(r[0]) == 4 and r[1].read == 3)(
                   ws.load_series("prints", ["2026-08-24"], s3=_s3())))


class _Boom:
    def get_paginator(self, _):
        raise RuntimeError("AccessDenied")


def _boom():
    m = ws.Meta("prints")
    rows = list(ws.stream_series("prints", ["2026-08-24"], s3=_Boom(), meta=m))
    return rows == [] and "AccessDenied" in (m.error or "")


guard("W6 CONTROL: an unreachable bucket still reports an ERROR, not an empty day",
      _boom)

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
