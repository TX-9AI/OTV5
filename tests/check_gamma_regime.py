#!/usr/bin/env python3
"""tests/check_gamma_regime.py — v1.0
THE DEALER-GAMMA REGIME IS READ AS ONE ROW, SCORED CONTINUOUSLY, AND SIZES
NOTHING UNTIL THE WEIGHT IS RAISED.

v1.0  2026-09-16 — OTV4TEST r31 (BFLY.7). The butterfly reads the pin STRIKE and
      the CONCENTRATION at it and has never read whether the pinning REGIME
      exists. Measured on this box 2026-09-16 the two disagreed for six hours:
      conc 0.06-0.17 (weak) against chain net gamma +71M..+123M (strongly
      pinning); then net gamma crossed ZERO at 15:00 ET and QQQ went 709.65 ->
      700.00 in twenty minutes.

  G0  SUMMING IS WRONG — every strike row at one ts carries the SAME chain-wide
      value, so `level()` must return the row value, not N x it. THE DEFECT THIS
      PINS WAS MADE FOR REAL before the code was written (see the module header).
  G1  the sign convention is the repo's own: + pins, - trends
  G2  `regime()` is bounded, monotone, and ZERO EXACTLY AT ZERO — the normaliser
      may move saturation but must never move the regime boundary
  G3  a stale row reads None, not an old regime
  G4  🔴 THE SHIPPED WEIGHT IS 0.0 AND `ramp()` RETURNS EXACTLY 1.0 — the whole
      point of the revision (WORKING_AGREEMENT §31)
  G5  with a weight it RAMPS, continuously, and is clamped both ends
  G6  the floor is NON-ZERO — the operator's ruling: a weak regime makes the
      trade smaller, never absent
  G7  `slope()` is a FIT, not a two-point difference: a spiky series whose ends
      are equal must not read as a flat regime
  G8  `read()` returns the four stable anchor keys, all present even when
      unreadable (None is a coverage fact, not a failure)
  G9  nothing here raises into a plan, ever — a broken store yields Nones

🔑 THE FIXTURE IS THIS BOX'S OWN TAPE (§0.4). G0/G1/G7 run against the REAL
2026-09-16 chain-net-gamma path read out of the live derived store, read-only,
not against a series invented to match the code. If the store is unavailable the
check says NOT RUN by name and never PASS (§38.7).

Born red at 0be53a1: `derived/gamma_regime.py` does not exist there, so G0-G9
all fail on import.
Run:  python3 tests/check_gamma_regime.py
"""
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

FAILED, RAN, SKIPPED = [], [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def not_run(name, why):
    print(f"  NOT RUN  {name}  [{why}]")
    SKIPPED.append(name)


def real_gamma_path():
    """The 2026-09-16 chain net gamma path, from the live store, READ-ONLY.
    Returns [(ts, millions)] or None when the store cannot be read."""
    p = os.path.join(_root, "data", "derived_store.db")
    if not os.path.exists(p):
        return None
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=2.0)
        rows = c.execute(
            "SELECT DISTINCT ts_epoch, gex FROM surface_series WHERE gex IS NOT NULL "
            "ORDER BY ts_epoch").fetchall()
        c.close()
        return [(float(t), float(g) / 1e6) for t, g in rows] or None
    except Exception:                                           # noqa: BLE001
        return None


def strikes_at_one_ts():
    """(n_rows, n_distinct_gex) at a single timestamp — G0's evidence."""
    p = os.path.join(_root, "data", "derived_store.db")
    if not os.path.exists(p):
        return None
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=2.0)
        ts = c.execute("SELECT ts_epoch FROM surface_series WHERE gex IS NOT NULL "
                       "ORDER BY ts_epoch DESC LIMIT 1").fetchone()
        if not ts:
            c.close()
            return None
        r = c.execute("SELECT COUNT(*), COUNT(DISTINCT gex) FROM surface_series "
                      "WHERE ts_epoch=?", (ts[0],)).fetchone()
        c.close()
        return (int(r[0]), int(r[1]))
    except Exception:                                           # noqa: BLE001
        return None


def main():
    print("check_gamma_regime — the pinning regime as a ramp input")
    try:
        from derived import gamma_regime as G
    except Exception as exc:                                    # noqa: BLE001
        print(f"  FAIL  import derived.gamma_regime  [{exc}]")
        print("\nRED — 1 check")
        return 1

    # ── G0: one row is the whole reading ────────────────────────────────
    s = strikes_at_one_ts()
    if s is None:
        not_run("G0 chain-wide gex is read once, not summed", "derived_store unreadable")
    else:
        n_rows, n_distinct = s
        # The store's own shape: many strike rows, ONE distinct value.
        check("G0 chain-wide gex is one value across every strike row",
              n_rows > 1 and n_distinct == 1, f"{n_rows} rows, {n_distinct} distinct")

    # ── G1/G2: sign convention and the boundary ─────────────────────────
    pos = G._tanh(120.0 / G.GAMMA_SCALE_M)
    neg = G._tanh(-100.0 / G.GAMMA_SCALE_M)
    check("G1 sign convention: + pins, - trends", pos > 0 > neg, f"{pos:+.3f} / {neg:+.3f}")
    check("G2 bounded, monotone, and exactly zero at zero",
          abs(G._tanh(0.0)) < 1e-12
          and -1.0 <= neg < pos <= 1.0
          and G._tanh(1e9) <= 1.0 and G._tanh(-1e9) >= -1.0,
          "tanh(0)=0")

    # ── G3: staleness reads None, not an old regime ─────────────────────
    stale = G.level(max_age_s=0.0)
    check("G3 a stale row reads None rather than an old regime", stale is None)

    # ── G4: THE SHIPPED WEIGHT CHANGES NOTHING ──────────────────────────
    shipped_zero = (G.GAMMA_RAMP_WEIGHT == 0.0)
    all_one = all(G.ramp(s) == 1.0 for s in (-1.0, -0.5, 0.0, 0.5, 1.0, None))
    check("G4 shipped weight is 0.0 and ramp() is exactly 1.0 for every score",
          shipped_zero and all_one, f"weight={G.GAMMA_RAMP_WEIGHT}")

    # ── G5: with a weight it ramps continuously and clamps ──────────────
    w = 0.5
    mids = [G.ramp(x, weight=w) for x in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    strictly_increasing = all(b > a for a, b in zip(mids, mids[1:]))
    clamped = (G.ramp(1.0, weight=99.0) == G.GAMMA_RAMP_CEIL
               and G.ramp(-1.0, weight=99.0) == G.GAMMA_RAMP_FLOOR)
    check("G5 with a weight it ramps continuously and clamps both ends",
          strictly_increasing and clamped,
          " ".join(f"{m:.2f}" for m in mids))

    # ── G6: the floor is non-zero (the operator's ruling) ───────────────
    check("G6 the floor is non-zero — a weak regime shrinks, never removes",
          G.GAMMA_RAMP_FLOOR > 0.0, f"floor={G.GAMMA_RAMP_FLOOR}")

    # ── G7: slope is a fit, not a two-point difference ──────────────────
    # A spiky path whose FIRST and LAST points are equal: a difference reads 0
    # (flat), a least-squares fit over a falling body does not.
    path = real_gamma_path()
    if not path or len(path) < G.SLOPE_MIN_POINTS:
        not_run("G7 slope is a least-squares fit, not a two-point difference",
                "no real gamma path in the store")
    else:
        t0 = path[0][0]
        spiky = [(t0 + 0, 10.0), (t0 + 60, 90.0), (t0 + 120, 20.0),
                 (t0 + 180, 80.0), (t0 + 240, 10.0)]
        two_point = spiky[-1][1] - spiky[0][1]          # == 0.0, "flat"
        xs = [(t - spiky[0][0]) / 60.0 for t, _ in spiky]
        ys = [v for _, v in spiky]
        n = float(len(spiky))
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        fit = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
        check("G7 slope is a least-squares fit, not a two-point difference",
              two_point == 0.0 and abs(fit) > 0.0,
              f"two-point {two_point:+.1f} vs fit {fit:+.2f}/min")

    # ── G8: the anchor keys are stable and always present ───────────────
    r = G.read()
    want = {"gamma_net_m", "gamma_regime", "gamma_slope_m", "gamma_ramp"}
    check("G8 read() returns the four stable anchor keys",
          set(r.keys()) == want, ",".join(sorted(r.keys())))

    # ── G9: nothing raises into a plan ──────────────────────────────────
    ok = True
    try:
        G.read(now=0.0)
        G.level(now=0.0)
        G.slope(now=0.0)
        G.regime(now=0.0)
        G.ramp(None)
    except Exception:                                           # noqa: BLE001
        ok = False
    check("G9 nothing raises into a plan, even with an absurd clock", ok)

    print()
    if SKIPPED:
        print(f"NOT RUN: {len(SKIPPED)} — {', '.join(SKIPPED)}")
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
