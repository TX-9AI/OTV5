#!/usr/bin/env python3
"""
tests/check_reconnect_jitter.py  v5.0
v5.0  2026-10-25  (TTS.1) — new. THE STREAMER'S RECONNECT WAITS ARE JITTERED, SO THE FLEET DOES NOT RETRY IN LOCKSTEP.
      data/candle_feed.py slept a fixed 3 -> 60 s ladder; after one server-side DXLink break every box retried on the
      same schedule against the shared TastyTrade session ceiling (2026-09-29 09:30-09:37, one box blind). Born red on
      ffe10bf at J1-J5 (no reconnect_wait; run() sleeps the raw ladder value).

DRIVEN with seeded random.Random instances, so every verdict is reproducible:

  J1  every wait on every rung (3, 6, 12, 24, 48, 60) lies in [max(RECONNECT_MIN_S, 0.8 x rung), 1.2 x rung] and is never
      below RECONNECT_MIN_S (200 draws per rung)
  J2  the jitter is real: 200 draws on the 60 s rung spread over more than 10 s and are not all the rung itself
  J3  one seed gives one sequence (reproducible); two seeds give different sequences
  J4  fourteen boxes (fourteen seeds) on the same rung after one shared break get fourteen distinct waits
  J5  run() sleeps the value reconnect_wait() returned and never the raw `backoff` (parsed, not grepped)
"""
import ast
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def main():
    try:
        import data.candle_feed as cf
        rw = cf.reconnect_wait
        lo_s, why = float(cf.RECONNECT_MIN_S), ""
    except Exception as e:                                          # noqa: BLE001
        rw, lo_s, why = None, 3.0, "%s: %s" % (type(e).__name__, e)

    ladder = (3, 6, 12, 24, 48, 60)
    if rw is None:
        for n in ("J1", "J2", "J3", "J4"):
            check("%s (reconnect_wait unavailable)" % n, False, why)
    else:
        rng = random.Random(7)
        bad = []
        for b in ladder:
            for _ in range(200):
                w = rw(b, rng)
                if not (max(lo_s, 0.8 * b) - 1e-9 <= w <= 1.2 * b + 1e-9) or w < lo_s:
                    bad.append((b, round(w, 3)))
        check("J1 every wait lies in [max(MIN, 0.8 rung), 1.2 rung] and never below RECONNECT_MIN_S",
              not bad, "out of bounds: %s" % bad[:5])

        r2 = random.Random(11)
        ws = [rw(60, r2) for _ in range(200)]
        check("J2 the jitter is real: 200 draws on the 60 s rung spread > 10 s, not all 60",
              max(ws) - min(ws) > 10 and any(abs(w - 60) > 1e-6 for w in ws),
              "min %.2f max %.2f" % (min(ws), max(ws)))

        a = [rw(b, random.Random(42)) for b in ladder]
        b_ = [rw(b, random.Random(42)) for b in ladder]
        c = [rw(b, random.Random(43)) for b in ladder]
        check("J3 one seed -> one sequence; two seeds -> different sequences", a == b_ and a != c,
              "42=%s 42'=%s 43=%s" % (a[:2], b_[:2], c[:2]))

        fleet = [round(rw(60, random.Random(1000 + i)), 6) for i in range(14)]
        check("J4 fourteen boxes on one rung after one break get fourteen distinct waits",
              len(set(fleet)) == 14, "distinct=%d %s" % (len(set(fleet)), fleet[:4]))

    # J5 — the sleep in run() is the jittered value
    src = open(os.path.join(ROOT, "data", "candle_feed.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    runs = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "run"]
    jittered, raw = set(), []
    for fn in runs:
        for n in ast.walk(fn):
            if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                    and getattr(n.value.func, "id", getattr(n.value.func, "attr", "")) == "reconnect_wait"):
                jittered |= {t.id for t in n.targets if isinstance(t, ast.Name)}
        sleeps = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                  and getattr(n.func, "attr", "") == "sleep" and n.args]
        for s in sleeps:
            arg = s.args[0]
            if isinstance(arg, ast.Name) and arg.id == "backoff":
                raw.append(s.lineno)
    slept_jittered = any(
        isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "sleep" and n.args
        and isinstance(n.args[0], ast.Name) and n.args[0].id in jittered
        for fn in runs for n in ast.walk(fn))
    check("J5 run() sleeps reconnect_wait()'s value, never the raw backoff",
          len(runs) == 1 and slept_jittered and not raw,
          "run() defs=%d jittered names=%s raw backoff sleeps at %s" % (len(runs), sorted(jittered), raw))

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
