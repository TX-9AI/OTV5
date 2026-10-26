#!/usr/bin/env python3
"""
tests/check_land_reissue.py  v5.0
v5.0  2026-10-25  (LAND.1) — new. A GENUINE RE-ISSUE PASSES THE LAND GATE. §26 suffixes a re-issue of a revision that
      already shipped (r18_r2); tools/check_land_discipline.py found ledger rows with `r\\d+[a-z]?`, which cannot match
      one, so the lander appended the row and the checker then refused it: "no row for r18_r2". Born red on ffe10bf at
      R1 and R2.

DRIVEN: the target tree's own tools/check_land_discipline.py check() runs against throwaway git repos built with its own
_mkrepo() fixture (one versioned module, docs/GENESIS.md), each delivery a correctly bumped module plus a ledger append.

  R1  a delivery whose revision is r2_r2, its row LAST in the ledger, has NO problems
  R2  an r2_r2 row that is not the last row is refused for THAT reason ("is not the last row"), not as absent
  R3  CONTROL: a ledger holding only r2_r2 does not satisfy rev r2 (the suffix is not read as the base id)
  R4  CONTROL: a plain r2 delivery still passes
"""
import importlib.util
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


_sp = importlib.util.spec_from_file_location("_cld_reissue", os.path.join(ROOT, "tools", "check_land_discipline.py"))
cld = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(cld)

BUMPED = ("#!/usr/bin/env python3\n# mod.py — v1.1\n"
          "# v1.1 (2026-02-01) — the change.\n# v1.0 (2026-01-01) — born.\nX = 2\n")


def deliver(rows, rev):
    """A correct module bump plus `rows` appended to the ledger; -> problems for `rev`."""
    with tempfile.TemporaryDirectory() as d:
        cld._mkrepo(d)
        open(os.path.join(d, "mod.py"), "w").write(BUMPED)
        with open(os.path.join(d, "docs", "GENESIS.md"), "a") as fh:
            for r in rows:
                fh.write("| **%s** | x |\n" % r)
        probs, notes = [], []
        cld.check(d, rev, "HEAD", probs, notes)
        return probs


def main():
    p1 = deliver(["r2_r2"], "r2_r2")
    check("R1 a re-issue r2_r2 with its row last has no problems", not p1, " | ".join(p1)[:200])

    p2 = deliver(["r2_r2", "r3"], "r2_r2")
    check("R2 an r2_r2 row not last is refused as 'not the last row', not as absent",
          any("is not the last row" in p for p in p2) and not any("no row for" in p for p in p2),
          " | ".join(p2)[:200])

    p3 = deliver(["r2_r2"], "r2")
    check("R3 CONTROL: a ledger holding only r2_r2 does not satisfy rev r2",
          any("no row for r2" in p for p in p3), " | ".join(p3)[:200])

    p4 = deliver(["r2"], "r2")
    check("R4 CONTROL: a plain r2 delivery still passes", not p4, " | ".join(p4)[:200])

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
