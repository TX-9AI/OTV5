"""
analysis/gap_class.py  v1.0
v1.0  2026-10-24  CD.3 (DISC.4) — THE GAP CLASSIFIER, ON THE SHIPPED SURFACE. analysis/gap_measure.py has imported
      `classify` from tests.gap_backfill since the OTV4 split; that module has never existed in this tree's history
      (mainline DISC.4; verified on OTV4TEST c825449), so `_classify` was None and gap_class was never emitted - a
      column that read as measured-and-null. The operator, 2026-10-24: "Let's fix DISC.4 really soon".

      THE VOCABULARY (the only one this tree ever named: main.py's "UNDIRECTED" and its comment "yesterday's trend at the
      open, which is precisely what CONT/REV means"):
        FLAT          |gap| < flat_pct (0.15% by gap_backfill's default, kept)
        UNDIRECTED    a gap with no prior direction to judge it against (prior_dir 0)
        CONTINUATION  the gap is in the prior session's direction
        REVERSAL      the gap is against it
      Plus the operator's own vocabulary from the 2026-10-24 gap studies, recorded beside it:
        bucket()         "<0.25" | "0.25-0.75" | ">0.75" of |gap| in percent of the prior close
        range_gap_pct()  the open BEYOND the prior session's RTH range: (open - prior_high) / prior_close when the open is
                         above the high, (open - prior_low) / prior_close when below the low, else 0.0 (inside)
      All of it is RECORD-ONLY: nothing gates on a gap class (the 10-24 gap-gate study failed its frozen terms).
      One lineage: a study that classifies the warehouse's daily bars imports THIS module.
"""
from typing import Optional

FLAT_PCT = 0.15                      # percent of the prior close
BUCKETS = ((0.25, "<0.25"), (0.75, "0.25-0.75"), (float("inf"), ">0.75"))


def classify(gap_pct: float, prior_dir: int = 0, flat_pct: float = FLAT_PCT) -> str:
    """FLAT / UNDIRECTED / CONTINUATION / REVERSAL. gap_pct in PERCENT (close to open); prior_dir +1 / -1 / 0."""
    g = float(gap_pct)
    if abs(g) < float(flat_pct):
        return "FLAT"
    d = int(prior_dir or 0)
    if d == 0:
        return "UNDIRECTED"
    return "CONTINUATION" if (g > 0) == (d > 0) else "REVERSAL"


def bucket(gap_abs_pct: float) -> str:
    """The operator's size buckets, |gap| in percent of the prior close."""
    a = abs(float(gap_abs_pct))
    for hi, name in BUCKETS:
        if a < hi or (hi == 0.75 and a <= hi):
            return name
    return BUCKETS[-1][1]


def range_gap_pct(today_open: float, prior_high: float, prior_low: float, prior_close: float) -> Optional[float]:
    """The open beyond the prior session's RTH range, in percent of the prior close; 0.0 when the open is inside;
    None when a price is missing or the prior close is not positive."""
    try:
        o, h, l, c = float(today_open), float(prior_high), float(prior_low), float(prior_close)
    except (TypeError, ValueError):
        return None
    if c <= 0:
        return None
    if o > h:
        return round(100.0 * (o - h) / c, 4)
    if o < l:
        return round(100.0 * (o - l) / c, 4)
    return 0.0
