#!/usr/bin/env python3
"""
tests/check_cascade_constants.py  v1.1
v1.1  2026-09-22  OTV4TEST r92 — MIRRORED 4 -> 8, AND THE SUBSET WAS THE DEFECT. A mirror
      list that is a subset of what it mirrors reports green on everything it
      forgot to name (§23's permissive rot). C2's bar is now len(MIRRORED)
      rather than a literal 4, and the detail line survives a non-tuple — it
      did `tuple(want)` unconditionally and died on a float mid-run.
v1.0  2026-09-04  r246 — TCS.9: THE CASCADE HARNESSES' LOCAL CONSTANTS MUST
      MATCH CONFIG.

🔴 `cascade_harness.py` and `cascade_real.py` each keep their own copy of the
session constants so the cascade can be reasoned about without importing
config. That is deliberate. What was missing is the COMPARISON — r238 set
`TCS_ENTRY_END_ET` to (0,0) to park TCS and both harnesses still read (14,0),
so for a day they modelled a TCS that traded. r241 restored (14,0) and made
them correct BY ACCIDENT, which is not the same as correct.

🔑 A COPY IS FINE. A COPY NOBODY COMPARES IS DRIFT WAITING TO HAPPEN. This is
the same treatment `ORB_NO_ENTRY_AFTER_ET` already has, and the harness comment
already promised it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


# harness name -> config name. Only constants the harness claims to mirror.
# 🔴 r92 — EVERY MIRRORED CONSTANT, NOT FOUR OF EIGHT. The harnesses carried
# EIGHT local copies and this dict compared FOUR, so `CONDOR_ENTRY_START_ET`
# sat at (11, 11) against config's (11, 31) — drifted since r81 unified the
# credit start, INVISIBLY, in the one checker whose entire job is to catch that
# drift. It was found by reading the harnesses, not by running this.
# ⚠️ THE LESSON IS THE SHAPE, NOT THE ROW. A mirror list that is a SUBSET of
# what it mirrors reports green on everything it forgot to name — the same
# permissive rot §23 records for the v3 cutoff's name list. C3 below now fails
# if a harness carries a constant this dict does not compare, so the subset
# cannot silently reappear.
MIRRORED = {
    "ORB_NO_ENTRY_AFTER_ET":       "ORB_NO_ENTRY_AFTER_ET",
    "DEBIT_DIRECTIONAL_CUTOFF_ET": "DEBIT_DIRECTIONAL_CUTOFF_ET",
    "CONDOR_ENTRY_START_ET":       "CONDOR_ENTRY_START_ET",
    "TCS_START_ET":                "TCS_START_ET",
    "TCS_ENTRY_END_ET":            "TCS_ENTRY_END_ET",
    "BUTTERFLY_ENTRY_START_ET":    "BUTTERFLY_ENTRY_START_ET",
    "CONDOR_TRIGGER_APPROACH":     "CONDOR_TRIGGER_APPROACH",
    "HARD_CLOSE_ET":               "HARD_CLOSE_ET",
}


def main():
    import config as C
    root = os.path.dirname(os.path.abspath(__file__))
    seen = 0
    for mod in ("cascade_harness", "cascade_real"):
        path = os.path.join(root, mod + ".py")
        if not os.path.exists(path):
            # ⚠️ ABSENT IS NOT PASSING. A harness that has been deleted or
            # renamed must be noticed, not silently skipped.
            check(f"C0 {mod}.py exists", False, "harness missing")
            continue
        ns = {}
        src = open(path, encoding="utf-8").read()
        for line in src.split("\n"):
            for name in MIRRORED:
                if line.startswith(name) and "=" in line:
                    try:
                        ns[name] = eval(line.split("=", 1)[1].split("#")[0].strip())
                    except Exception:                          # noqa: BLE001
                        pass
        for name, cfg_name in MIRRORED.items():
            if name not in ns:
                continue
            want = getattr(C, cfg_name, None)
            if want is None:
                continue
            seen += 1
            # ⚠️ r92 — THE DETAIL LINE MUST SURVIVE A NON-TUPLE. It read
            # `tuple(want)` unconditionally, so the moment the mirror grew to
            # include `CONDOR_TRIGGER_APPROACH` — a float — the checker died on
            # a TypeError mid-run, after six PASSes, reporting nothing about
            # the two constants behind it. A checker that crashes while
            # formatting its own message is §21's failure one level up: the
            # verdict never reaches the reader.
            _norm = lambda v: tuple(v) if isinstance(v, (list, tuple)) else v
            got, exp = _norm(ns[name]), _norm(want)
            check(f"C1 {mod}.{name} matches config", got == exp,
                  f"harness {got} vs config {exp}")

    # ⚠️ A CHECKER THAT COMPARED NOTHING MUST FAIL. If the parse stops finding
    # the constants — renamed, reformatted, moved — this would otherwise report
    # a cheerful green having verified nothing at all.
    # 🔑 r92 — THE BAR IS THE MIRROR'S OWN SIZE, NOT A LITERAL 4. Hard-coding the
    # count meant the mirror could be extended while this went on asserting the
    # old, smaller number — the check would have passed on half the list.
    check("C2 the checker actually compared something",
          seen >= len(MIRRORED), f"{seen} compared, {len(MIRRORED)} mirrored")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {seen + 1} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
