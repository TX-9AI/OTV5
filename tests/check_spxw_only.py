#!/usr/bin/env python3
"""
tests/check_spxw_only.py  v1.1
v1.1  2026-10-04  otv4 r464 — W4 SKIPS where strategy.orcs_plan is absent (ORCS is
      fork-only), as check_zero_bid_refused's Z6 does; nothing else changed.
      OTV4TEST r241's v1.0 (sha 63499c5b) is the source.
NEVER TRADE THE MORNING EXPIRATION. A chain that lists an AM-settled series beside a PM one on the
same date yields ONLY the PM series to every selector.

v1.0  2026-10-04  (proposed by SPX-TEST for QQQ-TEST's delivery) - the operator, 2026-10-04 13:57 ET:
      "Never trade the morning expiration on SPX." tastytrade 13.2.3's own docstring for
      get_option_chain (instruments.py:901-904): "In the case that there are two expiries on the same
      day (e.g. SPXW and SPX AM options), both will be returned in the same list." data/options_chain
      fetch_chain took that list whole. Monthly expiries on SPX: 10-16, 11-20, 12-18 (third Fridays).
      Drives the REAL OptionsChainFetcher.fetch_chain with get_option_chain, the quote/greek read,
      OI and the aux-tenor publish stubbed - no network. The fixture Options are built through the SDK's
      own Option model (every required field validated), never a hand-rolled stand-in (WA 0.4).
      The fixture GIVES THE AM SERIES EVERY TIE (listed first, a hair more delta), so a chain that
      keeps it shows it in the selections - that is what makes W3/W4 able to fail.

  W1  today's chain (both series, same strikes) holds ONLY SPXW, and half the contracts
  W2  an AM-only requested date is skipped for the next PM date (lowercase 'am' is AM too)
  W3  select_orb_strike and select_sweep_strike return SPXW contracts
  W4  ORCS's real locate() picks an SPXW short AND an SPXW wing on both sides
  W5  a QQQ chain (all PM) is unchanged: same symbols, same counts
  W6  the drop is SAID: a log line names how many AM contracts were removed
  W7  the archival aux-tenor publish still receives the UNFILTERED structure (TERM.1 unchanged)

Run:  python3 tests/check_spxw_only.py
"""
import logging
import os
import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


from tastytrade.instruments import Option                       # noqa: E402

STRIKES = [7600 + 5 * i for i in range(41)]                     # 7600..7800 by 5
SPOT = 7700.0


def _occ(root, d, cp, k):
    return f"{root:<6}{d.strftime('%y%m%d')}{cp}{int(round(k * 1000)):08d}"


def _opt(root, settle, d, cp, k, und="SPX"):
    """One SDK Option, validated by the SDK's own model from an API-shaped payload."""
    return Option(**{
        "instrument-type": "Equity Option", "symbol": _occ(root, d, cp, k), "active": True,
        "strike-price": str(k), "root-symbol": root, "underlying-symbol": und,
        "expiration-date": d.isoformat(), "exercise-style": "European" if und == "SPX" else "American",
        "shares-per-contract": 100, "option-type": cp, "option-chain-type": "Standard",
        "expiration-type": "Regular" if settle.upper() == "AM" else "Weekly",
        "settlement-type": settle, "stops-trading-at": datetime(d.year, d.month, d.day, 20, 0,
                                                                   tzinfo=timezone.utc).isoformat(),
        "market-time-instrument-collection": "Cash Settled Equity Option",
        "days-to-expiration": 0, "is-closing-only": False,
        "streamer-symbol": f".{root}{d.strftime('%y%m%d')}{cp}{k:g}",
    })


def _series(root, settle, d, und="SPX", strikes=STRIKES):
    return [_opt(root, settle, d, cp, k, und) for k in strikes for cp in ("C", "P")]


def _market(opts, spot):
    """greeks/quotes keyed by streamer symbol. The AM series gets a hair MORE |delta| (every tie)."""
    g, q = {}, {}
    for o in opts:
        k, cp = float(o.strike_price), ("C" if o.option_type.value == "C" else "P")
        d = 0.5 - (k - spot) / 100.0 if cp == "C" else -(0.5 + (k - spot) / 100.0)
        d = max(-0.99, min(0.99, d))
        if o.root_symbol == "SPX":
            d += 0.001 if d > 0 else -0.001
        intrinsic = max(0.0, (spot - k) if cp == "C" else (k - spot))
        mid = round(max(0.30, intrinsic + 6.0 - abs(k - spot) * 0.05), 2)
        g[o.streamer_symbol] = SimpleNamespace(delta=d, gamma=0.01, theta=-1.0, vega=0.1, volatility=0.12)
        q[o.streamer_symbol] = SimpleNamespace(bid_price=mid - 0.05, ask_price=mid + 0.05)
    return g, q


def run():
    print("check_spxw_only")
    from data import options_chain as OC
    import data.open_interest as OI
    import analysis.tenor_publish as TP

    log_lines = []

    class _H(logging.Handler):
        def emit(self, rec):
            log_lines.append(rec.getMessage())

    logging.getLogger(OC.__name__).addHandler(_H())
    logging.getLogger(OC.__name__).setLevel(logging.DEBUG)

    aux_seen = []
    OC.get_session = lambda: None
    OI.fetch_open_interest = lambda session, occ: {}
    TP.publish_aux_tenors = lambda db, chain_map, spot, target: aux_seen.append(chain_map) or {}

    def fetcher(chain_map, spot=SPOT):
        f = OC.OptionsChainFetcher()
        allopts = [o for v in chain_map.values() for o in v]
        g, q = _market(allopts, spot)
        f._get_chain_structure = lambda session, symbol: chain_map
        f._fetch_greeks_and_quotes = lambda session, syms, expiry=None: (g, q)
        return f

    MON = date(2026, 10, 16)
    both = _series("SPX", "AM", MON) + _series("SPXW", "PM", MON)        # AM listed FIRST: it wins ties
    cmap = {MON: both}
    f = fetcher(cmap)
    log_lines.clear()
    ch = f.fetch_chain("SPX", expiry=MON.isoformat())
    syms = [c.symbol for c in (ch.calls + ch.puts)] if ch else []
    am = [s for s in syms if s.startswith("SPX ")]
    check("W1 today's chain holds ONLY SPXW, half the contracts (41C/41P, not 82/82)",
          ch is not None and not am and len(ch.calls) == 41 and len(ch.puts) == 41,
          f"chain={'None' if ch is None else f'{len(ch.calls)}C/{len(ch.puts)}P'}, AM symbols kept={len(am)}"
          + (f" e.g. {am[0]!r}" if am else ""))
    check("W6 the drop is SAID: a log line names how many AM contracts were removed",
          any("AM" in m and "82" in m for m in log_lines),
          f"no log line names the 82 AM contracts; lines={[m for m in log_lines if 'AM' in m][:3]}")
    check("W7 the archival aux-tenor publish still receives the UNFILTERED structure",
          bool(aux_seen) and sum(len(v) for v in aux_seen[-1].values()) == len(both),
          f"aux saw {sum(len(v) for v in aux_seen[-1].values()) if aux_seen else 'nothing'} of {len(both)}")

    if ch is not None:
        orb = f.select_orb_strike(ch, "long", 7700.0, delta_bias="higher")
        swp = f.select_sweep_strike(ch, "short", 0.30)
        check("W3 select_orb_strike and select_sweep_strike return SPXW contracts",
              orb is not None and swp is not None
              and orb.symbol.startswith("SPXW") and swp.symbol.startswith("SPXW"),
              f"orb={getattr(orb, 'symbol', None)!r} sweep={getattr(swp, 'symbol', None)!r}")
        try:                                   # ORCS is FORK-ONLY: SKIP where absent (as Z6)
            from strategy import orcs_plan as OP
        except ImportError:
            OP = None
            print("  SKIP  W4 strategy.orcs_plan is not in this tree")
        if OP is not None:
            res = {s: OP.locate(s, ch, SPOT, 10.0) for s in ("put", "call")}
            bad = {s: (getattr(l.short, "symbol", None), getattr(l.long, "symbol", None), l.why)
                   for s, l in res.items()
                   if not (l.short is not None and l.long is not None
                           and l.short.symbol.startswith("SPXW") and l.long.symbol.startswith("SPXW"))}
            check("W4 ORCS's real locate() picks an SPXW short AND an SPXW wing on both sides", not bad,
                  f"{bad}")
    else:
        check("W3 select_orb_strike and select_sweep_strike return SPXW contracts", False, "no chain")
        check("W4 ORCS's real locate() picks an SPXW short AND an SPXW wing on both sides", False, "no chain")

    D1, D2 = date(2026, 11, 19), date(2026, 11, 20)
    amonly = _series("SPX", "am", D1)                                     # lowercase: still AM
    f2 = fetcher({D1: amonly, D2: _series("SPXW", "PM", D2)})
    ch2 = f2.fetch_chain("SPX", expiry=D1.isoformat())
    s2 = [c.symbol for c in (ch2.calls + ch2.puts)] if ch2 else []
    check("W2 an AM-only requested date is skipped for the next PM date (lowercase 'am' is AM too)",
          ch2 is not None and ch2.expiry == D2.isoformat() and s2 and all(s.startswith("SPXW") for s in s2),
          f"expiry={getattr(ch2, 'expiry', None)} AM kept={sum(not s.startswith('SPXW') for s in s2)}")

    Q = date(2026, 10, 16)
    qstrikes = [590 + i for i in range(21)]
    qq = _series("QQQ", "PM", Q, und="QQQ", strikes=qstrikes)
    f3 = fetcher({Q: qq}, spot=600.0)
    ch3 = f3.fetch_chain("QQQ", expiry=Q.isoformat())
    s3 = sorted(c.symbol for c in (ch3.calls + ch3.puts)) if ch3 else []
    check("W5 a QQQ chain (all PM) is unchanged: same symbols, same counts",
          s3 == sorted(o.symbol for o in qq), f"{len(s3)} of {len(qq)}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(run())
