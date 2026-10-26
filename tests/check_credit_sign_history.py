#!/usr/bin/env python3
"""
tests/check_credit_sign_history.py  v5.0
v5.0  2026-10-25  (MEAS.6 / RPT.26 / PRE.2) — THE CREDIT BOOK RE-READS WITH THE RIGHT SIGN, WITHOUT REWRITING A ROW
      (otv4 r344's gate, ported). No OTV5 entry path writes is_short_position (only broker_reconcile, for an
      adopted short), so every credit row carries 0 and r_ledger.position_dollars took its MFE off mfe_premium -
      the ADVERSE extreme for a credit - exchanging MFE and MAE for every credit trade.

  Drives the REAL tests/r_ledger.py (is_credit, position_dollars, two_population):
  H1  a credit row as the book holds it (flag 0, credit_received > 0) reads as SHORT
  H2  and its MFE/MAE come out the credit way round (MFE off mae_premium)
  H3  CONTROL: a debit row (no credit) is UNCHANGED - the long rule
  H4  the flag WINS when set: flag 1 + no credit still reads SHORT
  H5  CONTROL: a zero / absent / None / '' credit does not flip anything
  H6  the never-favourable VERDICT flips for a credit winner: two_population files it under WAS favourable
      (the old rule scored MFE $0 off the adverse leg and filed it NEVER)

Born red on ffe10bf at H1-H6 (r_ledger has no is_credit, so every check reports red). Mutant: is_credit reduced to
the old flag-only rule reds H1 H2 H6 alone (H3 H4 H5 are controls).
Run:  python3 tests/check_credit_sign_history.py   (exit 0 green, 1 red)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")
    if not ok:
        FAILED.append(name.split()[0])


def main():
    try:
        import r_ledger as RL
        is_credit, position_dollars = RL.is_credit, RL.position_dollars
    except Exception as exc:                                    # noqa: BLE001
        for n in ("H1", "H2", "H3", "H4", "H5", "H6"):
            check(n, False, f"r_ledger.is_credit missing: {type(exc).__name__}: {exc}")
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1

    # A credit spread as the BOOK HOLDS IT: flag 0, credit written.
    # Sold at 1.00; premium fell to 0.20 (the win) and rose to 1.30 (adverse).
    hist = dict(entry_premium=1.0, mfe_premium=1.30, mae_premium=0.20,
                contracts=1, is_short_position=0, credit_received=1.0)
    check("H1 flag 0 + credit 1.0 reads SHORT", is_credit(hist) is True, f"is_credit={is_credit(hist)!r}")

    mfe, mae = position_dollars(hist)
    check("H2 credit MFE $80 off mae_premium, MAE $30 off mfe_premium",
          mfe is not None and abs(mfe - 80.0) < 1e-6 and abs(mae - 30.0) < 1e-6, f"MFE={mfe!r} MAE={mae!r}")

    debit = dict(entry_premium=1.0, mfe_premium=1.30, mae_premium=0.20,
                 contracts=1, is_short_position=0, credit_received=0)
    dmfe, dmae = position_dollars(debit)
    check("H3 CONTROL: debit MFE $30 / MAE $80 (long rule intact)",
          abs(dmfe - 30.0) < 1e-6 and abs(dmae - 80.0) < 1e-6, f"MFE={dmfe!r} MAE={dmae!r}")

    flagged = dict(entry_premium=1.0, mfe_premium=1.30, mae_premium=0.20, contracts=1, is_short_position=1)
    check("H4 flag 1, no credit key -> SHORT", is_credit(flagged) is True)

    flipped = [v for v in (0, 0.0, None, "")
               if is_credit(dict(entry_premium=1.0, is_short_position=0, credit_received=v))]
    flipped += ["absent"] if is_credit(dict(entry_premium=1.0, is_short_position=0)) else []
    check("H5 CONTROL: 0 / 0.0 / None / '' / absent credit all stay long", not flipped, f"flipped={flipped!r}")

    # H6 — the verdict, not the column. Premium never rose above entry (mfe_premium == entry) and fell to 0.20:
    # a credit WINNER. The old long rule read MFE = $0 and filed it NEVER favourable.
    winner = dict(pnl_usd=60.0, entry_premium=1.0, mfe_premium=1.0, mae_premium=0.20, contracts=1,
                  is_short_position=0, credit_received=1.0, strategy="SweepCreditSpread",
                  option_side="put", exit_reason="hard_close", status="closed")
    d = RL.two_population([winner], RL.BASE_CUT)
    check("H6 a credit winner is filed WAS favourable, not NEVER",
          d["was"]["n"] == 1 and d["never"]["n"] == 0,
          f"never={d['never']['n']} was={d['was']['n']} fav_frac={RL.fav_frac(winner)!r}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — the credit book re-reads with the right sign")
    return 0


if __name__ == "__main__":
    sys.exit(main())
