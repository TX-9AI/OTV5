#!/usr/bin/env python3
"""tests/check_live_mark_fallback.py  v1.1
F4 — THE LIVE MARK FALLBACK WORKS, AND PRICES THE WHOLE STRUCTURE.

v1.1  2026-10-20  r496 / F4.2 — the fallback now asks get_market_data_by_type(options=[...])
      once per structure (the 429 fix), so the stub answers that call from the same quote
      table; L8 asks that the call names the record's own symbol(s) as options. Every
      expected value is unchanged.

v1.0  2026-10-04  r468. Found by OTV4TEST's live-readiness audit. With no chain in
      hand, a LIVE box priced through PositionManager._get_option_mark, which
      called client.get(...) on the Session. The boxes' SDK (tastytrade 13.0.0,
      measured on UNH) has no Session.get, so every call raised and the bare
      except returned None. And a credit vertical's option_symbol is its SHORT
      leg, so repairing the transport alone would value a spread at its short
      leg's full mark.

Drives the REAL PositionManager._fetch_current_premium in LIVE mode with no chain.
The Session is a stand-in with NO .get, as on 13.0.0; get_market_data is replaced
by a coroutine stub that answers from a quote table and records every call. No
network, no database (the manager is built without __init__).

  L1  single leg, two-sided quote 1.00/1.20 -> 1.10
  L2  credit vertical: short 2.00/2.20, long 0.50/0.70 -> 1.50 (short minus long),
      never the short leg's 2.10
  L3  butterfly: lower + upper - 2 x center
  L4  tent -> None, and no quote is requested
  L5  credit vertical with no long_symbol -> None (one leg is not a price)
  L6  a finite-absurd mark (1e12) -> None (AUDIT F9's ceiling)
  L7  the SDK raising -> None, and a WARNING names the symbol (not silent)
  L8  the call asks for the record's symbol as options=[...] (v1.1: the batch call)
  L9  UNCHANGED RULE: a one-sided quote (bid 0, ask 0.22, mark 0.22) -> 0.22
  L10 UNCHANGED PATH: paper with no chain returns the last mark, asks nothing

Run:  python3 tests/check_live_mark_fallback.py   (needs the venv's tastytrade)
"""
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "SYN")
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Session:
    """As tastytrade 13.0.0's Session: there is no .get."""


class _MD:
    def __init__(self, bid, ask, mark=None, last=None):
        self.bid, self.ask, self.mark, self.last = bid, ask, mark, last


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.lines = []

    def emit(self, rec):
        self.lines.append(rec.getMessage())


def main():
    print("check_live_mark_fallback")
    try:
        import tastytrade.market_data as tmd
        from tastytrade.order import InstrumentType
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import execution.position_manager as PM

    quotes, calls = {}, []

    async def fake_by_type(session, options=None, **kw):
        options = list(options or [])
        calls.append(("options", tuple(options)))
        out = []
        for sym in options:
            q = quotes[sym]
            if isinstance(q, Exception):
                raise q
            q.symbol = sym
            out.append(q)
        return out

    tmd.get_market_data_by_type = fake_by_type
    PM.get_client = lambda: _Session()
    cap = _Capture()
    PM.logger.addHandler(cap)

    def live():
        m = PM.PositionManager.__new__(PM.PositionManager)
        m.paper_trading = False
        m._open_records = []
        m._mark_fail_warned = set()
        return m

    def price(rec, mgr=None):
        calls.clear()
        return (mgr or live())._fetch_current_premium(rec, chain=None)

    near = lambda a, b: a is not None and b is not None and abs(a - b) < 1e-9

    quotes.update({
        "SYN 1C100": _MD(1.00, 1.20),
        "SYN 1P90": _MD(2.00, 2.20), "SYN 1P85": _MD(0.50, 0.70),
        "SYN 1C95": _MD(5.00, 5.20), "SYN 1C100B": _MD(2.00, 2.20), "SYN 1C105": _MD(0.40, 0.60),
        "SYN ABSURD": _MD(0, 0, mark=1e12),
        "SYN BROKEN": RuntimeError("market data down"),
        "SYN ONESIDE": _MD(0, 0.22, mark=0.22),
    })

    v = price({"trade_id": "L1", "strategy": "ORBStrategy", "option_symbol": "SYN 1C100"})
    check("L1 single leg, two-sided -> the mid 1.10", near(v, 1.10), f"got {v!r}")
    check("L8 asks for the record's own symbol as an equity option",
          calls == [("options", ("SYN 1C100",))], f"calls={calls!r}")

    vert = {"trade_id": "L2", "strategy": "SweepCreditSpread", "is_condor_leg": 1,
            "option_symbol": "SYN 1P90", "short_symbol": "SYN 1P90", "long_symbol": "SYN 1P85"}
    v = price(vert)
    check("L2 credit vertical -> short minus long 1.50, never the short leg's 2.10",
          near(v, 1.50), f"got {v!r}")

    fly = {"trade_id": "L3", "strategy": "GEXPinButterfly", "is_butterfly": 1,
           "lower_symbol": "SYN 1C95", "center_symbol": "SYN 1C100B", "upper_symbol": "SYN 1C105"}
    v = price(fly)
    check("L3 butterfly -> lower + upper - 2 x center (5.10 + 0.50 - 4.20 = 1.40)",
          near(v, 1.40), f"got {v!r}")

    tent = dict(vert, trade_id="L4", setup_type="tent")
    v = price(tent)
    check("L4 tent -> None, and no quote requested", v is None and not calls,
          f"got {v!r} calls={calls!r}")

    v = price(dict(vert, trade_id="L5", long_symbol=""))
    check("L5 vertical with no long_symbol -> None", v is None, f"got {v!r}")

    v = price({"trade_id": "L6", "strategy": "ORBStrategy", "option_symbol": "SYN ABSURD"})
    check("L6 a 1e12 mark -> None", v is None, f"got {v!r}")

    cap.lines.clear()
    v = price({"trade_id": "L7", "strategy": "ORBStrategy", "option_symbol": "SYN BROKEN"})
    check("L7 SDK raises -> None and a WARNING names the symbol",
          v is None and any("SYN BROKEN" in ln for ln in cap.lines),
          f"got {v!r} warnings={cap.lines!r}")

    v = price({"trade_id": "L9", "strategy": "ORBStrategy", "option_symbol": "SYN ONESIDE"})
    check("L9 one-sided quote keeps the old rule: the mark 0.22", near(v, 0.22), f"got {v!r}")

    paper = live()
    paper.paper_trading = True
    v = price({"trade_id": "L10", "strategy": "ORBStrategy", "option_symbol": "SYN 1C100",
               "current_premium": 0.77, "entry_premium": 1.00}, mgr=paper)
    check("L10 paper, no chain -> last mark 0.77, nothing asked", near(v, 0.77) and not calls,
          f"got {v!r} calls={calls!r}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
