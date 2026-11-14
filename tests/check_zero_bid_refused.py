"""
tests/check_zero_bid_refused.py  v5.1
v5.1  2026-11-14  OTV5 r117 (HYG §5.3) — Z6 RUNS EVERY TIME. It was wrapped in find_spec("strategy.volt_plan"), a module
      r76 deleted, so it printed SKIP on every run and took Z6b (strategy/orb_plan.select_contract, Breakout's selector,
      still in the tree) down with it. The VOLT half goes; Z6 now drives the AAL chain through orb_plan.select_contract
      unconditionally (Z6) and adds Z6c: runaway_continuation.gamma_leverage_pick, the selector Runaway and the Hunt
      share, refuses a zero-bid contract and takes the same strike once it has a bid. A missing selector is a FAIL,
      never a SKIP. PARK (check_park K7) and OGAP (check_ogap O7b) refuse a one-sided quote in their own gates.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-02  OTV4TEST r186 (ZBID.1) — SHARED GATE, byte-identical in
      OTV4TEST and otv4 but for this header. A CONTRACT WITH NO BID IS NOT A
      LIVE QUOTE, WHATEVER ITS ASK SAYS. data/options_chain.py sets
      mark = ask when bid == 0, so a no-bid contract carried its whole ask as
      its mark and cleared every `mark > 0.05` "live quote" floor. AAL
      2026-10-02: three VOLT shorts bought P11.5 at delta -0.0009 with spot
      13.20, bid 0.00 / ask 0.22, filled at the ask, and lost 3,128 as the
      mark decayed toward the contract's real value (otv4's agent, read from
      the AAL box; mainline exposure to date measured ZERO on 15 boxes). The
      house rule already existed in runaway_continuation.gamma_leverage_pick
      (`bid <= 0` refused); the single-contract debit selectors lacked it.
      The operator, 2026-10-02: "Absolutely that's a real problem."

      INTERPRETERS, PER TREE: OTV4TEST - /usr/bin/python3 (with the r106 venv
      bootstrap) and venv/bin/python. otv4 - the dtp venv on control (CHK.11).

WHAT IT DRIVES (the REAL selectors, never source text):
  Z1  data.options_chain.two_sided(c): bid > 0 AND ask > 0.
  Z2  select_orb_strike skips a zero-bid contract NEAREST the target and
      takes the nearest two-sided one.
  Z3  select_orb_strike returns None when only zero-bid contracts clear the
      floor - it never falls back to one.
  Z4  select_sweep_strike skips a zero-bid contract nearest the target delta.
  Z5  UNCHANGED: on a chain where every contract is two-sided, both shared
      selectors pick exactly what the mark floor alone picked.
  Z6  this tree's Breakout selector on the AAL chain itself - spot 13.20, puts
      13.0 (0.04/0.06), 12.5 (0.02/0.04), 11.5 (0.00/0.22): orb_plan.select_contract
      refuses 11.5 (nothing else clears the 0.05 floor) - and, on the same chain
      with 11.5 at 0.18/0.22, picks it (so the refusal is the bid, not the strike).
  Z6c runaway_continuation.gamma_leverage_pick (Runaway and the Hunt): puts
      99 (0.00/0.60) and 98 (0.45/0.50), spot 99.5, run 2.0 -> 99P is refused
      and 98P taken; the same chain with 99P at 0.55/0.60 -> 99P (the best
      leverage) is picked. Always run; a missing selector
      is a FAIL, never a SKIP.

Run:  python3 tests/check_zero_bid_refused.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def _oc(k, bid, ask, delta, side):
    from data.options_chain import OptionContract
    mark = (bid + ask) / 2 if bid > 0 and ask > 0 else (bid or ask)   # options_chain's rule
    return OptionContract(symbol=f"{side}{k}", strike=float(k), mark=mark, bid=bid, ask=ask,
                          delta=delta, gamma=0.03, expiry="2026-10-02", option_type=side)


def _chain(calls=(), puts=(), spot=100.0):
    from data.options_chain import OptionsChain
    ch = OptionsChain(underlying="TEST", expiry="2026-10-02", spot_price=spot)
    ch.calls, ch.puts = list(calls), list(puts)
    return ch


def main():
    import data.options_chain as OC
    fetcher = OC.OptionsChainFetcher.__new__(OC.OptionsChainFetcher)

    # ── Z1 the predicate ─────────────────────────────────────────────────
    ts = getattr(OC, "two_sided", None)
    if ts is None:
        check("Z1 data.options_chain.two_sided exists", False, "absent")
    else:
        z = _oc(11.5, 0.00, 0.22, -0.0009, "P")
        ok = _oc(13.0, 0.04, 0.06, -0.38, "P")
        nb = _oc(13.0, 0.37, 0.00, -0.38, "P")
        check("Z1 two_sided: 0.00/0.22 False, 0.04/0.06 True, 0.37/0.00 False",
              ts(z) is False and ts(ok) is True and ts(nb) is False,
              f"{ts(z)} {ts(ok)} {ts(nb)}")

    # ── Z2/Z3 select_orb_strike ──────────────────────────────────────────
    ch2 = _chain(calls=[_oc(101, 0.00, 0.40, 0.30, "C"), _oc(102, 0.20, 0.24, 0.20, "C")])
    k2 = fetcher.select_orb_strike(ch2, "long", 101.0)
    check("Z2 select_orb_strike skips the zero-bid 101C nearest the target, takes 102C",
          k2 is not None and float(k2.strike) == 102.0, f"picked {getattr(k2, 'strike', None)}")
    ch3 = _chain(calls=[_oc(101, 0.00, 0.40, 0.30, "C"), _oc(102, 0.00, 0.24, 0.20, "C")])
    k3 = fetcher.select_orb_strike(ch3, "long", 101.0)
    check("Z3 only zero-bid contracts -> select_orb_strike returns None",
          k3 is None, f"picked {getattr(k3, 'strike', None)}")

    # ── Z4 select_sweep_strike ───────────────────────────────────────────
    ch4 = _chain(puts=[_oc(98, 0.00, 0.30, -0.30, "P"), _oc(97, 0.15, 0.19, -0.22, "P")])
    k4 = fetcher.select_sweep_strike(ch4, "short", 0.30, 0.05)
    check("Z4 select_sweep_strike skips the zero-bid 98P at the target delta, takes 97P",
          k4 is not None and float(k4.strike) == 97.0, f"picked {getattr(k4, 'strike', None)}")

    # ── Z5 unchanged when every contract is two-sided ────────────────────
    ch5 = _chain(calls=[_oc(k, 0.30 - 0.05 * i, 0.34 - 0.05 * i, 0.40 - 0.08 * i, "C")
                        for i, k in enumerate((101, 102, 103))],
                 puts=[_oc(k, 0.30 - 0.05 * i, 0.34 - 0.05 * i, -0.40 + 0.08 * i, "P")
                       for i, k in enumerate((99, 98, 97))])
    a = fetcher.select_orb_strike(ch5, "long", 102.2)
    b = fetcher.select_sweep_strike(ch5, "short", 0.32, 0.05)
    check("Z5 UNCHANGED: a fully two-sided chain gives 102C (orb) and 98P (sweep)",
          a is not None and b is not None and float(a.strike) == 102.0
          and float(b.strike) == 98.0,
          f"orb {getattr(a, 'strike', None)} sweep {getattr(b, 'strike', None)}")

    # ── Z6 this tree's own selectors, on the AAL chain (always run) ──────
    try:
        import strategy.orb_plan as OP
    except Exception as e:                                   # a missing selector is RED, never a SKIP
        OP = None
        check("Z6 strategy.orb_plan imports", False, repr(e))
    if OP is not None:
        aal = _chain(puts=[_oc(13.0, 0.04, 0.06, -0.38, "P"), _oc(12.5, 0.02, 0.04, -0.10, "P"),
                           _oc(11.5, 0.00, 0.22, -0.0009, "P")], spot=13.20)
        o = OP.select_contract(aal, "short", 11.5)
        live = _chain(puts=[_oc(13.0, 0.04, 0.06, -0.38, "P"), _oc(12.5, 0.02, 0.04, -0.10, "P"),
                            _oc(11.5, 0.18, 0.22, -0.0009, "P")], spot=13.20)
        o2 = OP.select_contract(live, "short", 11.5)
        check("Z6 Breakout's selector (orb_plan) refuses the AAL zero-bid P11.5; with a bid it takes it",
              o is None and o2 is not None and float(o2.strike) == 11.5,
              f"zero-bid picked {getattr(o, 'strike', None)}, two-sided picked {getattr(o2, 'strike', None)}")

    # ── Z6c the Runaway / Hunt selector ──────────────────────────────────
    try:
        from strategy.runaway_continuation import gamma_leverage_pick
    except Exception as e:
        gamma_leverage_pick = None
        check("Z6c strategy.runaway_continuation.gamma_leverage_pick imports", False, repr(e))
    if gamma_leverage_pick is not None:
        def _puts(bid99):
            return [_oc(99.0, bid99, 0.60, -0.45, "P"), _oc(98.0, 0.45, 0.50, -0.30, "P")]
        g0, _, _, rej0 = gamma_leverage_pick(_puts(0.00), "short", 99.5, 2.0)
        g1, _, _, _ = gamma_leverage_pick(_puts(0.55), "short", 99.5, 2.0)
        check("Z6c Runaway/Hunt gamma_leverage_pick: the zero-bid 99P (best leverage) is refused and 98P taken; "
              "with a bid on 99P it takes 99P",
              g0 is not None and float(g0.strike) == 98.0 and rej0 >= 1
              and g1 is not None and float(g1.strike) == 99.0,
              f"zero-bid picked {getattr(g0, 'strike', None)} (spread_rejected {rej0}), "
              f"two-sided picked {getattr(g1, 'strike', None)}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — no selector buys a contract with no bid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
