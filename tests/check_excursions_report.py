#!/usr/bin/env python3
"""
tests/check_excursions_report.py  v5.0
v5.0  2026-11-08  OTV5 r79 (RSUITE.1) — PORTED FROM THE FROZEN otv4 TREE with tests/excursions.py v5.0. Fixtures use
      live setup names; NEW C6: a credit row WITHOUT is_short_position but with credit_received > 0 maps as a SHORT
      (OTV5 MEAS.6 is_credit; asymmetric fixture, so the long mapping cannot pass it by coincidence).
      Every entry below this line is the predecessor's history (cited by its own prefix).
otv4 v1.0  2026-09-09  r327 / RPT.19 — the land gate for tests/excursions.py.
  C1  a LONG's MFE comes from mfe_premium; a SHORT's from mae_premium
  C2  an unmeasured row is counted apart and NEVER scored never-favourable
  C3  render() and render_rows() both draw, with the unmeasured line named
  C4  it shares r_ledger.position_dollars — no second sign rule
  C5  `_r_tool`'s four flags are all accepted by its argparse
  C6  (v5.0) a credit row with no is_short_position flag is still a SHORT

⚠️ C4 IS THE ONE THAT MATTERS LONGEST. The short-side mapping is the whole
reason that helper exists, and a copy of it here would drift silently from
the R ledger's capture and giveback — two rules for one number, the shape
behind the dedup pair and the counter/offset ledgers.
"""
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    try:
        import excursions as ex
        import r_ledger as rl
    except Exception as exc:                                     # noqa: BLE001
        print("  FAIL  tests/excursions.py did not import: {}".format(exc))
        return 1

    lng = dict(entry_premium=1.0, mfe_premium=1.80, mae_premium=0.85,
               contracts=1, is_short_position=0, pnl_usd=40.0,
               strategy="Breakout", option_side="call", symbol="NVDA")
    sht = dict(entry_premium=1.0, mfe_premium=1.40, mae_premium=0.60,
               contracts=1, is_short_position=1, pnl_usd=25.0,
               strategy="PARK", option_side="put", symbol="SPX")
    bare = dict(entry_premium=1.0, contracts=1, is_short_position=0,
                pnl_usd=-10.0, strategy="Breakout", option_side="call",
                symbol="AMD")

    m1, a1 = ex.position_dollars(lng)
    m2, a2 = ex.position_dollars(sht)
    check("C1", abs(m1 - 80.0) < 1e-6 and abs(a1 - 15.0) < 1e-6
          and abs(m2 - 40.0) < 1e-6 and abs(a2 - 40.0) < 1e-6,
          "long ({:.0f}/{:.0f}) short ({:.0f}/{:.0f})".format(m1, a1, m2, a2))

    b = ex.measure([lng, sht, bare], "strategy")
    un = sum(x["unmeasured"] for x in b.values())
    nf = sum(x["never_fav"] for x in b.values())
    check("C2", un == 1 and nf == 0,
          "unmeasured={} never_fav={}".format(un, nf))

    buf = io.StringIO()
    with redirect_stdout(buf):
        ex.render(b, "strategy")
        ex.render_rows([lng, sht, bare])
    out = buf.getvalue()
    check("C3", "UNMEASURED" in out and "Breakout" in out and "MFE$" in out,
          "{} line(s) drawn".format(len(out.splitlines())))

    check("C4", ex.position_dollars is rl.position_dollars,
          "same object" if ex.position_dollars is rl.position_dollars
          else "excursions defines its own sign rule")

    rc = 0
    for flags in (["--selftest"], ["--date", "2026-09-01", "--selftest"],
                  ["--from", "2026-09-01", "--to", "2026-09-02", "--selftest"],
                  ["--all-history", "--selftest"]):
        try:
            rc |= ex.main(flags)
        except SystemExit as e:                                  # argparse
            rc |= int(e.code or 0)
    check("C5", rc == 0, "_r_tool's flags all accepted")

    cr = dict(entry_premium=1.0, mfe_premium=1.50, mae_premium=0.80,
              contracts=1, credit_received=100.0, pnl_usd=25.0,
              strategy="PARK", option_side="put", symbol="SPX")
    m6, a6 = ex.position_dollars(cr)
    # asymmetric on purpose: SHORT -> (20, 50); the long mapping would give (50, 20)
    check("C6", m6 is not None and abs(m6 - 20.0) < 1e-6 and abs(a6 - 50.0) < 1e-6,
          "credit by credit_received: mfe={:.0f} mae={:.0f}".format(m6 or 0, a6 or 0))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
