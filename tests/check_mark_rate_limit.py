#!/usr/bin/env python3
"""tests/check_mark_rate_limit.py  v1.0
v1.0  2026-10-20  r496 / F4.2 — THE LIVE MARK FALLBACK SURVIVES THE BROKER'S RATE LIMIT.

  OTV4TEST r308's probe (16:05 ET) ran the REAL r468 fallback against the broker:
  QQQ priced 3 of 6, SPX 4 of 6, and every None with a cause was HTTP 429 (nginx
  HTML, raised by the SDK as TastytradeError "Couldn't parse response"). One REST
  call per leg per position per tick spent the bucket.

Drives the REAL PositionManager._fetch_current_premium in LIVE mode with no chain,
against a stub broker that answers BOTH SDK calls (get_market_data, the old per-leg
call, and get_market_data_by_type, the batch call) and 429s on a schedule. Sleeps
and heartbeat touches are recorded, not performed.

  R1  a butterfly against a broker that 429s every OTHER request -> priced
  R2  a credit vertical, same broker -> priced (short minus long)
  R3  a single leg whose first request 429s -> priced after one retry
  R4  a butterfly with a calm broker costs ONE request, not one per leg
  R5  a broker that always 429s -> None after exactly 4 requests, backoff 0.5/1/2 s
      (3.5 s in all), the heartbeat touched before every request
  R6  a non-429 failure is NOT retried: one request, None
  R7  the warning names "HTTP 429", not "Couldn't parse response"
  R8  _http_status reads nginx's page and an httpx-style .response.status_code
  (OTV4TEST critique MSG-QQQ-1020-25:)
  R9  the broker answers with DIFFERENT spacing ('SPXW261020C07545000' for
      'SPXW  261020C07545000') -> still priced
  R10 after one request spends its retries on 429, the next position in the same
      tick tries ONCE and sleeps nothing (one backoff per tick, any position count)

Run:  python3 tests/check_mark_rate_limit.py   (needs the venv's tastytrade)
"""
import logging
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "SYN")
PROBLEMS = []

NGINX_429 = ("Couldn't parse response: <html>\r\n<head><title>429 Too Many Requests</title>"
             "</head>\r\n<body>\r\n<center><h1>429 Too Many Requests</h1></center>\r\n"
             "<hr><center>nginx</center>\r\n</body>\r\n</html>\r\n")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name.split()[0])


class _MD:
    def __init__(self, symbol, bid, ask):
        self.symbol, self.bid, self.ask, self.mark, self.last = symbol, bid, ask, None, None


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.lines = []

    def emit(self, rec):
        self.lines.append(rec.getMessage())


def main():
    print("check_mark_rate_limit")
    try:
        import tastytrade.market_data as tmd
        from tastytrade.utils import TastytradeError
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import execution.position_manager as PM
    import utils.heartbeat as HB

    Q = {"SYN 1C95": (5.00, 5.20), "SYN 1C100": (2.00, 2.20), "SYN 1C105": (0.40, 0.60),
         "SYN 1P90": (2.00, 2.20), "SYN 1P85": (0.50, 0.70)}
    broker = {"n": 0, "fail": lambda n: False, "exc": None}

    def _answer():
        broker["n"] += 1
        if broker["fail"](broker["n"]):
            raise broker["exc"] or TastytradeError(NGINX_429)

    async def fake_one(session, symbol, instrument_type):
        _answer()
        return _MD(symbol, *Q[symbol])

    async def fake_by_type(session, options=None, **kw):
        _answer()
        return [_MD(s, *Q[s]) for s in (options or [])]

    tmd.get_market_data = fake_one
    respace = {"on": False}

    async def fake_by_type_r(session, options=None, **kw):
        rows = await fake_by_type(session, options=options)
        if respace["on"]:
            for r in rows:
                r.symbol = "".join(r.symbol.split())
        return rows

    tmd.get_market_data_by_type = fake_by_type_r
    PM.get_client = lambda: object()
    sleeps, touches = [], []
    PM.time = types.SimpleNamespace(sleep=sleeps.append, time=__import__("time").time)
    HB.touch = lambda note="", file_path=None: touches.append(note) or True
    cap = _Capture()
    PM.logger.addHandler(cap)

    def price(rec, fail=lambda n: False, exc=None, cool=0.0):
        broker.update(n=0, fail=fail, exc=exc)
        sleeps.clear(); touches.clear(); cap.lines.clear()
        m = PM.PositionManager.__new__(PM.PositionManager)
        m.paper_trading = False
        m._open_records = []
        m._mark_fail_warned = set()
        if cool is not None:
            PM.PositionManager._mark_cool_until = cool
        return m._fetch_current_premium(rec, chain=None)

    near = lambda a, b: a is not None and abs(a - b) < 1e-9              # noqa: E731
    fly = {"trade_id": "F", "strategy": "GEXPinButterfly", "is_butterfly": 1,
           "lower_symbol": "SYN 1C95", "center_symbol": "SYN 1C100", "upper_symbol": "SYN 1C105"}
    vert = {"trade_id": "V", "strategy": "SweepCreditSpread", "is_condor_leg": 1,
            "option_symbol": "SYN 1P90", "short_symbol": "SYN 1P90", "long_symbol": "SYN 1P85"}
    single = {"trade_id": "S", "strategy": "RunawayContinuation", "option_symbol": "SYN 1C100"}
    every_other = lambda n: n % 2 == 0                                  # noqa: E731

    v = price(fly, every_other)
    check("R1 butterfly, a broker that 429s every other request -> priced 1.40",
          near(v, 1.40), f"got {v!r} requests={broker['n']}")
    v = price(vert, every_other)
    check("R2 credit vertical, same broker -> priced 1.50", near(v, 1.50),
          f"got {v!r} requests={broker['n']}")
    v = price(single, lambda n: n == 1)
    check("R3 single leg, first request 429s -> priced 2.10 after one retry",
          near(v, 2.10) and broker["n"] == 2, f"got {v!r} requests={broker['n']}")
    v = price(fly)
    check("R4 a calm broker: a butterfly costs ONE request", near(v, 1.40) and broker["n"] == 1,
          f"got {v!r} requests={broker['n']}")
    v = price(fly, lambda n: True)
    check("R5 always 429: None after 4 requests, backoff 0.5/1/2 s, heartbeat before each",
          v is None and broker["n"] == 4 and sleeps == [0.5, 1.0, 2.0] and len(touches) == 4,
          f"got {v!r} requests={broker['n']} sleeps={sleeps} touches={len(touches)}")
    check("R7 the warning names HTTP 429, not \"Couldn't parse\"",
          any("HTTP 429" in ln for ln in cap.lines)
          and not any("Couldn't parse" in ln for ln in cap.lines), f"warnings={cap.lines!r}")
    v = price(single, lambda n: True, exc=TastytradeError("invalid_symbol: Symbol not found"))
    check("R6 a non-429 failure is not retried: one request, None",
          v is None and broker["n"] == 1 and sleeps == [], f"got {v!r} requests={broker['n']}")

    Q["SPXW  261020C07545000"] = (3.00, 3.20)
    respace["on"] = True
    v = price({"trade_id": "X", "strategy": "RunawayContinuation",
               "option_symbol": "SPXW  261020C07545000"})
    respace["on"] = False
    check("R9 a respaced answer ('SPXW261020C07545000') still prices 3.10", near(v, 3.10),
          f"got {v!r}")

    price(fly, lambda n: True)                     # spends the retries: cooldown starts
    v = price(vert, lambda n: True, cool=None)     # the next position, same tick
    check("R10 after a spent retry, the next position tries ONCE and sleeps nothing",
          v is None and broker["n"] == 1 and sleeps == [], f"requests={broker['n']} sleeps={sleeps}")
    PM.PositionManager._mark_cool_until = 0.0

    hs = getattr(PM.PositionManager, "_http_status", None)
    resp = types.SimpleNamespace(response=types.SimpleNamespace(status_code=503))
    check("R8 _http_status: nginx's 429 page and .response.status_code",
          hs is not None and hs(TastytradeError(NGINX_429)) == 429 and hs(resp) == 503
          and hs(TastytradeError("invalid_symbol: x")) is None,
          "missing" if hs is None else f"{hs(TastytradeError(NGINX_429))}, {hs(resp)}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
