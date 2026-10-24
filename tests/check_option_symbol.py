#!/usr/bin/env python3
"""
tests/check_option_symbol.py  v1.0
v1.0  2026-09-13  OTV4TEST r17 — PRE.1: EVERY ENTRY ROW NAMES ITS OPTION.
      `EntryEngine._record_kwargs` is the ONE LINEAGE factory both the immediate
      and the standing-offer paths build through; it wrote `symbol =
      INSTRUMENT` (the underlying) and nothing naming the contract, so a row
      joined to no quote_series and every premium-path study refused it (19 of
      21 rows on this box; mainline measured exit_replay refusing 301 of 337).

  O1  the factory writes option_symbol from the signal's contract
  O2  ...and still writes the underlying in `symbol` — both, not either
  O3  a signal with no contract yields "" and raises nothing (credit legs
      build their own rows and write option_symbol on their own path)
  O4  the factory is still the only construction site (ONE LINEAGE holds)

Born red at r16 on O1.
Run:  python3 tests/check_option_symbol.py
"""
import os
import sys
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    from execution.entry_engine import EntryEngine
    import config
    eng = EntryEngine.__new__(EntryEngine)
    occ = "QQQ   260913C00596000"
    sig = types.SimpleNamespace(
        strategy_name="LiquidityHunt", setup_type="liquidity_hunt_A2", direction="long",
        underlying_entry=596.1, underlying_stop=595.0, underlying_target=598.4,
        vix_at_signal=15.0, is_fed_day=False,
        contract=types.SimpleNamespace(symbol=occ, strike=596.0))
    kw = EntryEngine._record_kwargs(eng, sig)
    check("O1 the factory writes option_symbol from the signal's contract",
          kw.get("option_symbol") == occ, repr(kw.get("option_symbol")))
    check("O2 ...and still writes the UNDERLYING in `symbol` — both, not either",
          kw.get("symbol") == config.INSTRUMENT, repr(kw.get("symbol")))
    sig2 = types.SimpleNamespace(
        strategy_name="X", setup_type="x", direction="long", underlying_entry=1.0,
        underlying_stop=0.0, underlying_target=0.0, vix_at_signal=0.0, is_fed_day=False)
    kw2 = EntryEngine._record_kwargs(eng, sig2)
    check("O3 no contract -> \"\" and no exception", kw2.get("option_symbol") == "", repr(kw2.get("option_symbol")))
    src = open(os.path.join(_root, "execution", "entry_engine.py"), encoding="utf-8").read()
    check("O4 ONE LINEAGE holds: `symbol = INSTRUMENT,` appears once — one construction site",
          src.count("symbol            = INSTRUMENT,") == 1)
    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}"); return 1
    print("PASS — check_option_symbol"); return 0


if __name__ == "__main__":
    sys.exit(main())
