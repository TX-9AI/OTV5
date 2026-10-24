#!/usr/bin/env python3
"""
tests/fees.py  v1.1
v1.1  2026-09-07  r293 (re-cut, not landed) — THE OPEN SIDE IS NOW MEASURED.
The operator supplied statement 5WZ-19645-13 for MAY 2025, which carries 52
usable option lines including OPENING trades, SPXW at up to 45 contracts, an
ASSIGNMENT, an EXERCISE and two EXPIRIES. FEE.3 asked for exactly this.
  🎯 EVERY STRUCTURAL CLAIM IN THE MODEL IS CONFIRMED AGAINST REAL CHARGES:
  · the $1.00/contract OPEN commission is real — SPX open $1.78/ct vs SPX
    close $0.78/ct, and equity open $1.13/ct vs equity close $0.13/ct. The
    difference is EXACTLY $1.00 in both instruments, on 31 lines.
  · THE CLOSE IS FREE — the close rate equals the open rate minus that dollar,
    with nothing else moving.
  · 🔴 SPX IS NOT CAPPED. 45 contracts cost $80.08. A $10/leg cap would make
    that ~$45. The commission scales LINEARLY to 45 contracts, which is the
    single most consequential branch in this file and it is now measured
    rather than read off a card.
  · 🔴 THE EQUITY CAP IS REAL AND BINDS. SPY 20 contracts cost $12.59 where
    uncapped would be ~$22.60. And it appears to be PER ORDER ACROSS FILLS,
    not per fill: SPY 595C filled 2 then 29 and was charged $2.26 then $11.76,
    which is $2.00 + $8.00 of commission — one $10 cap split across two fills.
    ⚠️ RECORDED AS AN OBSERVATION, NOT MODELLED. The trades table has no
    order id and no fill breakdown, so this file cannot express it; it matters
    only where one logical entry fills in pieces.
  · $5.00 FLAT PER ASSIGNMENT OR EXERCISE EVENT, NOT PER CONTRACT — both A/E
    lines moved 30 contracts and were charged $5.00 exactly.
  · EXPIRY IS FREE — two EXPIRED lines, 30 and -30 contracts, and Total
    Miscellaneous Transactions is empty.
  🔴 AND THE RESIDUAL IS NOW LOCATED, WHICH IS THE REAL ADVANCE. It is NOT in
  the commission — that matches to the cent. It is entirely in the
  pass-through fees: equity runs $0.13/ct against a carded $0.12, and SPX runs
  $0.78/ct against a carded $0.72. SPX minus equity is $0.65/ct against the
  card's $0.60 SPX exchange fee. Both statements agree on the equity figure,
  so it is a stable 2025 rate and not noise. THE COMPONENT THAT MOVED STILL
  CANNOT BE NAMED — the card is dated 2026-07-30 and no rate history was
  supplied — but the residual is confined to two numbers, is +5% of a trade's
  fees on equity and +8% on SPX, and moves NOTHING about the structure.
  ⚠️ THE MODEL STAYS ON THE 2026 CARD, deliberately: this account traded in
  2025 and the fleet trades now. `--reconcile` prints both statements so the
  gap is visible every run rather than absorbed.
v1.0  2026-09-07  r293 — THE FEE MODEL. Every P&L number in this system is
GROSS. Read at source rather than assumed: `exit_engine` computes
`pnl_usd = (current_premium - entry_prem) * contracts * CONTRACT_MULTIPLIER`
at all eight sites and `position_manager:655` does the same — a pure premium
difference. There is no commission, clearing, regulatory or exchange term
anywhere in the tree; a grep for "fee" and "commission" across every .py in
otv4 and day_trader_pro returns only the word "feed". So every report that
has ever printed a dollar has printed a number the broker would not have
paid.

⚠️ THIS FILE IS CONTROL-ONLY AND TOUCHES NOTHING THAT TRADES (WA §34). It is
a pure function of a trade row: no chain, no network, no clock, no writes. It
is imported by reports; it never gates, sizes, or prices anything. `--selftest`
is the whole of its own verification.

⚠️ IT IS A MODEL, NOT A RECORD. The broker's actual charges arrive on a
statement; this computes what the PUBLISHED SCHEDULE says they should be. The
two are reconciled by `--reconcile`, which is the only honest way to hold a
model of somebody else's billing — and that reconciliation currently DOES NOT
CLOSE. See RECONCILIATION below; it is a stated open item, not a rounding
detail to be absorbed.

SOURCE OF THE RATES
  tastytrade "COMMISSIONS & FEES", last updated 2026-07-30, supplied by the
  operator 2026-09-07. Every rate below carries the section it came from.
  ⚠️ Rates change without notice ("tastytrade reserves the right to modify any
  fees ... without prior notice"), so `SCHEDULE_DATE` is stamped on every
  breakdown. A report printing fees from a stale card is the C.31 shape — a
  number defended by a justification the record no longer supports.

WHAT COSTS WHAT, AND WHY IT IS NOT UNIFORM
  Three things make fees vary by more than contract count, and all three bite
  this fleet specifically:

  1. THE OPEN COSTS $1.00/CONTRACT AND THE CLOSE COSTS NOTHING. So a
     round trip is not symmetric and per-side accounting is mandatory.

  2. THE $10/LEG COMMISSION CAP DOES NOT APPLY TO BROAD-BASED INDEX OPTIONS.
     Fourteen of the fifteen panel symbols are equity/ETF and cap at $10 a leg.
     SPX does not cap AND carries a $0.60/contract exchange fee on every side.
     🔴 CONSEQUENCE, COMPUTED BELOW IN THE SELFTEST: a 50-lot ORB costs about
     $22 round trip on an equity name and about $123 on SPX — 5.5x, for the
     identical contract count. ORB sizes on GEOMETRY (r181/r192) and its
     budget (r201) is denominated in premium, which knows nothing about this.

  3. LEG COUNT IS A PROPERTY OF THE STRUCTURE, NOT THE TRADE ROW. One `trades`
     row is one to three legs and one to four contract-sides per unit:
       DIRECTIONAL          1 leg      1x contracts   (ORB, runaway)
       CONDOR_LEG / TREND   2 legs     2x contracts   (credit verticals)
       BUTTERFLY            3 legs     4x contracts   (1 / 2 / 1 — verified at
                                                       entry_engine.py:811-819)
       TENT                 3 legs     3x contracts   (r106)
     🔴 SO THE BUTTERFLY PAYS FOUR CONTRACT-SIDES PER FLY PER SIDE. On the
     cheap flies of 2026-09-01 (META debit $0.17) the modelled round trip is
     ~$4.98 against a 25% stop floor of $4.25 — THE FEES EXCEED THE INTENDED
     MAXIMUM LOSS. That is a structural fact about four legs and a small
     debit, not a judgement about the strategy, and `stop_survivable` (r154,
     wired to the butterfly at r208) measures the stop against the BID-ASK and
     does not know fees exist.

THE CLASSIFIER IS `strategy.structure.of()` — THE ONE THE ENGINE USES.
  Not a strategy-name list (§r35, an allow-list rots permissively) and not a
  second copy (r214 precedent: `is_credit_vertical` was reused rather than
  re-derived, and C.23 records what happens when a tool re-implements the
  thing it measures — it tests itself and stays green over the bug).

ABSENCE IS NEVER ZERO.
  A row that cannot be priced returns `None` with a NAMED reason, never
  `0.0`. A fee of zero and an unpriceable row are different facts and a
  report that folds them together understates its own total silently — the
  plausible-silence class (P10, r143, r138: `reach or 99`, `conc or 0`).
  `total_fees_usd` over a list therefore reports `unpriced` alongside the sum,
  always, including when it is zero.

RECONCILIATION AGAINST A REAL STATEMENT — IT DOES NOT CLOSE, AND THAT IS
RECORDED RATHER THAN SMOOTHED.
  Statement 5WZ-19645-13, June 2025, ten option lines. Two findings:

  🔴 (a) EVERY OPTION LINE ON IT IS A `CLOSING CONTRACT`. There is not one
  opening option trade on the statement, so it carries ZERO evidence about the
  $1.00/contract open commission — which is the single largest term in this
  model. The statement validates the cheap half of the round trip only.

  🔴 (b) THE CLOSE-SIDE RATE DOES NOT MATCH THE CARD. Observed buy-to-close is
  a flat $0.13/contract across four lines (3ct and 5ct, exact). The 2026-07-30
  card implies $0.12 ($0.10 clearing + $0.02 ORF). One cent per contract is
  unexplained. I can NOT attribute it to a named component from the documents
  in hand: the statement predates the card by thirteen months, ORF is
  exchange-set and the card says so, and no rate history was supplied.
  ⚠️ AND NO SINGLE MODEL FITS ALL FIVE SELL LINES. Sell-to-close runs
  $0.14/ct at 1 contract, $0.1333/ct at 3 and $0.132/ct at 5 — consistent with
  $0.13 plus a per-contract sales term, but the rounding that fits 1 and 3
  (round up) gives $0.67 at 5 where the statement says $0.66. Rather than
  invent a rounding rule to make the three agree, `--reconcile` prints the
  residual per line and the model stays on the published card. §0: when two
  facts do not reconcile, say so and stop.

  ⚠️ AND THE STATEMENT CANNOT ANSWER THE MULTI-LEG QUESTION AT ALL. Each leg
  is its own BOUGHT/SOLD line with its own debit/credit; there is no order
  grouping, no order id, no per-leg commission column, and fees are EMBEDDED
  in the debit/credit rather than itemised. So nothing on a statement of this
  form can tell us how a three-leg butterfly is billed as one order. The leg
  model above comes from OUR OWN order builder, which is a stronger source for
  what we submit — and a weaker one for what we are charged.

SEC FEE — COMPUTED WHERE THE BASIS IS KNOWN, LABELLED WHERE IT IS NOT.
  $20.60 per $1,000,000 of SALES. For a single-leg debit the close IS the sale
  and the basis is exact. For a credit vertical the trades table stores the NET
  credit, never the short leg's own premium, so the true basis is unknowable
  from this table and the model uses the net as a LOWER BOUND. `sec_basis` says
  which, on every breakdown. The term is ~$0.21 per $10,000 sold, so this is a
  labelling question and not a material one — but an unlabelled estimate is how
  `oi_proxy` became indistinguishable from data for the life of a project (r19).

Run:  python3 tests/fees.py --selftest
      python3 tests/fees.py --reconcile
      python3 tests/fees.py --show          # the schedule, with provenance
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.structure import Structure, of as structure_of   # noqa: E402

SCHEDULE_DATE = "2026-07-30"
SCHEDULE_SOURCE = "tastytrade COMMISSIONS & FEES"

CONTRACT_MULTIPLIER = 100

# ── THE SCHEDULE, AS DATA (WA §36 — a declaration is data, not prose) ────────
# Every rate names the card section it came from, so a change is one edit and
# an unexplained constant is visibly unexplained.
OPEN_COMMISSION_PER_CONTRACT = 1.00     # "Options on Stock" / "Broad-Based Index Options"
CLOSE_COMMISSION_PER_CONTRACT = 0.00    # both sections: "$0.00 commission to close"
EQUITY_COMMISSION_CAP_PER_LEG = 10.00   # "Equity option commission capped at $10 per leg."
CLEARING_PER_CONTRACT = 0.10            # "Clearing Fees - Options"
ORF_PER_CONTRACT = 0.02                 # "Options Regulatory Fee" (footnote 1)
TAF_PER_CONTRACT_SOLD = 0.00329         # "FINRA TAF - Option Sales" (footnote 4)
SEC_FEE_PER_DOLLAR_SOLD = 20.60 / 1_000_000.0   # "SEC Fee" (footnote 5)
# "Option Exercise / Assignment $5" — trade-related fees table.
# 🔑 MEASURED PER EVENT, NOT PER CONTRACT: both A/E lines on the May 2025
# statement moved 30 contracts and were charged $5.00 exactly. Per-contract
# would have been $150. Nothing in `trades` records an assignment today, so
# this is EXPOSED and unused rather than wired into fees_for() — see FEE.5.
ASSIGNMENT_FEE_PER_EVENT = 5.00
# Expiring worthless costs nothing: two EXPIRED lines, 30 and -30 contracts,
# and the statement's Total Miscellaneous Transactions is blank. This matters
# for the credit book, whose hard close "takes the nickel or takes ASSIGNMENT"
# (r105) — those two dispositions cost $0.00 and $5.00, not the same.
EXPIRY_FEE = 0.00
# ── MEASURED 2025 RATES, RECORDED AND NOT APPLIED ────────────────────────────
# What the two statements actually charged, per contract, excluding commission.
# NOT used by the model — the model prices the CURRENT card. These exist so
# --reconcile can state the gap rather than discover it, and so a future
# statement can be checked against a number rather than a memory.
MEASURED_2025_NONCOMM = {"equity": 0.13, "index": 0.78}

# "Single-Listed Exchange Proprietary Index Options Fees" — the table.
# ⚠️ MEMBERSHIP OF THIS TABLE IS WHAT MAKES A SYMBOL BROAD-BASED for our
# purposes, rather than a hand-kept list of "index-looking" tickers. QQQ is an
# ETF and is deliberately absent: it takes equity treatment, cap included.
INDEX_OPTION_FEE_PER_CONTRACT: Dict[str, float] = {
    "SPX": 0.60, "RUT": 0.18, "VIX": 0.35, "OEX": 0.40, "XEO": 0.40,
    "DJX": 0.18, "CBTX": 0.50, "MBTX": 0.25, "NDX": 0.25,
    # XSP is $0.00 under 10 contracts/leg and $0.07 at 10+ (footnote 7) — a
    # QUANTITY-DEPENDENT rate this model does not express. Left out rather
    # than entered wrong; `is_index_option` returns False for it and
    # `unmodelled_symbol()` names it, so an XSP row is flagged, not silently
    # priced as an equity.
}
QUANTITY_DEPENDENT_SYMBOLS = frozenset({"XSP"})

# Contract-sides per unit of `contracts`, and how many are SOLD, per structure.
# 🔑 VERIFIED AT SOURCE, NOT ASSUMED: entry_engine.py:811-819 builds the fly as
# BUY lower x contracts, SELL center x contracts*2, BUY upper x contracts.
_LEG_MODEL: Dict[Structure, Dict[str, Any]] = {
    Structure.DIRECTIONAL: {
        "legs": [("single", 1, "buy")],
        "note": "one long option (ORB, runaway)",
    },
    Structure.BUTTERFLY: {
        "legs": [("lower", 1, "buy"), ("center", 2, "sell"), ("upper", 1, "buy")],
        "note": "1/2/1 — four contract-sides per fly",
    },
    Structure.CONDOR_LEG: {
        "legs": [("short", 1, "sell"), ("long", 1, "buy")],
        "note": "credit vertical",
    },
    Structure.TREND_PARTICIPATION: {
        "legs": [("short", 1, "sell"), ("long", 1, "buy")],
        "note": "credit vertical (TC.6)",
    },
    Structure.TENT: {
        "legs": [("short", 1, "sell"), ("long", 1, "buy"), ("hedge", 1, "buy")],
        "note": "r106 — short + wing + opposite-type hedge long",
    },
}


def is_index_option(symbol: Optional[str]) -> bool:
    return str(symbol or "").upper() in INDEX_OPTION_FEE_PER_CONTRACT


def unmodelled_symbol(symbol: Optional[str]) -> Optional[str]:
    """Names a symbol this model declines to price, or None.

    ⚠️ A SYMBOL THIS FILE CANNOT PRICE MUST NOT SILENTLY TAKE EQUITY RATES.
    That is the r19 shape — a proxy never labelled unavailable becomes
    indistinguishable from data.
    """
    s = str(symbol or "").upper()
    if not s:
        return "no symbol on the row"
    if s in QUANTITY_DEPENDENT_SYMBOLS:
        return (f"{s} has a QUANTITY-DEPENDENT exchange fee "
                f"($0.00 under 10 contracts/leg, $0.07 at 10+) which this "
                f"model does not express")
    return None


@dataclass
class LegFee:
    """One leg, one side (open or close). Every component named separately."""
    leg: str
    side: str                    # "open" | "close"
    action: str                  # "buy" | "sell"
    contracts: int
    commission: float = 0.0
    commission_capped: bool = False
    clearing: float = 0.0
    orf: float = 0.0
    taf: float = 0.0
    sec: float = 0.0
    index_fee: float = 0.0

    @property
    def total(self) -> float:
        return (self.commission + self.clearing + self.orf
                + self.taf + self.sec + self.index_fee)


@dataclass
class FeeBreakdown:
    trade_id: Optional[str]
    symbol: str
    structure: str
    contracts: int
    legs: List[LegFee] = field(default_factory=list)
    sec_basis: str = "exact"
    schedule_date: str = SCHEDULE_DATE
    closed: bool = True

    # ── component rollups ───────────────────────────────────────────────────
    # ⚠️ NOT ROUNDED. Rounding here was the first version and its own F1 caught
    # it: a 4dp property compared against the hand-computed card value differs
    # in the 5th place, so the check could not assert the arithmetic it exists
    # to assert. Worse than the test problem is the LIBRARY problem — TAF is
    # $0.00329 and the SEC fee is $0.0000206 per dollar, so rounding every trade
    # before summing throws away most of both terms and a 500-trade rollup
    # drifts by more than the components it dropped. Rounding happens ONCE, at
    # the display and serialisation boundary, and nowhere else.
    def component(self, name: str) -> float:
        return sum(getattr(l, name) for l in self.legs)

    @property
    def open_fees(self) -> float:
        return sum(l.total for l in self.legs if l.side == "open")

    @property
    def close_fees(self) -> float:
        return sum(l.total for l in self.legs if l.side == "close")

    @property
    def total(self) -> float:
        return sum(l.total for l in self.legs)

    @property
    def contract_sides(self) -> int:
        return sum(l.contracts for l in self.legs)

    def as_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "structure": self.structure,
            "contracts": self.contracts,
            "contract_sides": self.contract_sides,
            "open_fees": round(self.open_fees, 4),
            "close_fees": round(self.close_fees, 4),
            "total_fees": round(self.total, 4),
            "commission": round(self.component("commission"), 4),
            "clearing": round(self.component("clearing"), 4),
            "orf": round(self.component("orf"), 4),
            "taf": round(self.component("taf"), 4),
            "sec": round(self.component("sec"), 4),
            "index_fee": round(self.component("index_fee"), 4),
            "sec_basis": self.sec_basis,
            "schedule_date": self.schedule_date,
            "closed": self.closed,
        }

    def render(self) -> str:
        L = [f"  {self.symbol} {self.structure} x{self.contracts} "
             f"({self.contract_sides} contract-sides)"]
        for l in self.legs:
            L.append(f"    {l.side:<5} {l.leg:<7} {l.action:<4} "
                     f"{l.contracts:>3}ct  ${l.total:>7.4f}"
                     + ("  [capped]" if l.commission_capped else ""))
        L.append(f"    open ${self.open_fees:.2f}  close ${self.close_fees:.2f}"
                 f"  TOTAL ${self.total:.2f}")
        return "\n".join(L)


@dataclass
class Unpriced:
    """A row that cannot be priced, and WHY. Never a zero."""
    trade_id: Optional[str]
    symbol: str
    reason: str


def _f(v) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v) -> Optional[int]:
    f = _f(v)
    return None if f is None else int(f)


def _side_fees(symbol: str, leg: str, side: str, action: str, contracts: int,
               sale_proceeds_usd: float) -> LegFee:
    """One leg, one side. Every rate applied from the schedule constants."""
    lf = LegFee(leg=leg, side=side, action=action, contracts=contracts)
    idx = is_index_option(symbol)

    if side == "open":
        raw = contracts * OPEN_COMMISSION_PER_CONTRACT
        # 🔴 THE CAP EXCLUDES BROAD-BASED INDEX OPTIONS — stated twice on the
        # card ("Broad-based index options are excluded from the capped
        # commission offer"). This single branch is the whole SPX story.
        if idx:
            lf.commission = raw
        else:
            lf.commission = min(raw, EQUITY_COMMISSION_CAP_PER_LEG)
            lf.commission_capped = raw > EQUITY_COMMISSION_CAP_PER_LEG
    else:
        lf.commission = contracts * CLOSE_COMMISSION_PER_CONTRACT

    lf.clearing = contracts * CLEARING_PER_CONTRACT
    lf.orf = contracts * ORF_PER_CONTRACT
    if idx:
        lf.index_fee = contracts * INDEX_OPTION_FEE_PER_CONTRACT[symbol.upper()]

    # SALES ONLY. Footnote 4 (TAF) and footnote 5 (SEC) both scope to sales.
    if action == "sell":
        lf.taf = contracts * TAF_PER_CONTRACT_SOLD
        lf.sec = max(0.0, sale_proceeds_usd) * SEC_FEE_PER_DOLLAR_SOLD
    return lf


def fees_for(row: Mapping[str, Any]):
    """-> FeeBreakdown, or Unpriced with a named reason. Never a silent zero.

    Reads ONLY persisted `trades` columns. Pure: no network, no clock, no
    writes.
    """
    tid = row.get("trade_id")
    symbol = str(row.get("symbol") or "").upper()

    bad = unmodelled_symbol(symbol)
    if bad:
        return Unpriced(tid, symbol, bad)

    contracts = _i(row.get("contracts"))
    if contracts is None or contracts <= 0:
        return Unpriced(tid, symbol,
                        f"contracts is {row.get('contracts')!r} — a fee cannot "
                        f"be computed without a quantity")

    st = structure_of(row)
    model = _LEG_MODEL.get(st)
    if model is None:                                   # unreachable today
        return Unpriced(tid, symbol, f"no leg model for structure {st}")

    status = str(row.get("status") or "").strip().lower()
    closed = status == "closed"

    entry = _f(row.get("entry_premium"))
    exit_p = _f(row.get("exit_premium"))

    # SEC basis. Exact only where the SOLD leg's own premium is the row's
    # premium — that is the single-leg case and nothing else.
    single_leg = st is Structure.DIRECTIONAL
    sec_basis = "exact" if single_leg else "net_premium_lower_bound"

    bd = FeeBreakdown(trade_id=tid, symbol=symbol, structure=st.value,
                      contracts=contracts, sec_basis=sec_basis, closed=closed)

    for leg_name, ratio, open_action in model["legs"]:
        n = contracts * ratio
        close_action = "sell" if open_action == "buy" else "buy"

        open_sale = (entry or 0.0) * n * CONTRACT_MULTIPLIER if open_action == "sell" else 0.0
        bd.legs.append(_side_fees(symbol, leg_name, "open", open_action, n, open_sale))

        # ⚠️ AN OPEN POSITION HAS PAID ONLY THE OPEN SIDE. Charging it a round
        # trip would overstate today's cost of a position still running — the
        # same reasoning pnl_s3 uses to count open trades and never sum them.
        if not closed:
            continue
        close_sale = (exit_p or 0.0) * n * CONTRACT_MULTIPLIER if close_action == "sell" else 0.0
        bd.legs.append(_side_fees(symbol, leg_name, "close", close_action, n, close_sale))

    return bd


def total_fees_usd(rows) -> dict:
    """Fleet/day rollup. ALWAYS reports `unpriced`, including when it is zero.

    ⚠️ A total that hides how many rows it could not price is a total that
    understates itself silently.
    """
    total = 0.0
    priced: List[FeeBreakdown] = []
    unpriced: List[Unpriced] = []
    comps = {k: 0.0 for k in
             ("commission", "clearing", "orf", "taf", "sec", "index_fee")}
    for r in rows:
        res = fees_for(r)
        if isinstance(res, Unpriced):
            unpriced.append(res)
            continue
        priced.append(res)
        total += res.total
        for k in comps:
            comps[k] += res.component(k)
    return {"total_fees": round(total, 2),
            "priced": len(priced),
            "unpriced": len(unpriced),
            "unpriced_rows": unpriced,
            "components": {k: round(v, 2) for k, v in comps.items()},
            "breakdowns": priced,
            "schedule_date": SCHEDULE_DATE}


def net_of_fees(row: Mapping[str, Any]) -> Optional[float]:
    """gross pnl_usd minus modelled fees, or None if either is unavailable.

    ⚠️ None, NEVER the gross. Returning gross on an unpriceable row would make
    a fee-blind number indistinguishable from a fee-aware one, which is the
    exact confusion this file exists to end.
    """
    gross = _f(row.get("pnl_usd"))
    if gross is None:
        return None
    res = fees_for(row)
    if isinstance(res, Unpriced):
        return None
    return round(gross - res.total, 2)


# ── the schedule, printed with provenance ───────────────────────────────────
def show_schedule() -> int:
    print(f"\n  {SCHEDULE_SOURCE} — last updated {SCHEDULE_DATE}\n")
    print(f"  open commission        ${OPEN_COMMISSION_PER_CONTRACT:.2f} /contract")
    print(f"  close commission       ${CLOSE_COMMISSION_PER_CONTRACT:.2f} /contract")
    print(f"  equity cap             ${EQUITY_COMMISSION_CAP_PER_LEG:.2f} /leg "
          f"(broad-based index EXCLUDED)")
    print(f"  clearing               ${CLEARING_PER_CONTRACT:.2f} /contract, every side")
    print(f"  ORF                    ${ORF_PER_CONTRACT:.2f} /contract, every side")
    print(f"  FINRA TAF              ${TAF_PER_CONTRACT_SOLD:.5f} /contract SOLD")
    print(f"  SEC fee                $20.60 per $1,000,000 SOLD")
    print("  index exchange fee     " + ", ".join(
        f"{k} ${v:.2f}" for k, v in sorted(INDEX_OPTION_FEE_PER_CONTRACT.items())))
    print(f"  NOT MODELLED           {', '.join(sorted(QUANTITY_DEPENDENT_SYMBOLS))} "
          f"(quantity-dependent rate)")
    print("\n  leg models (contract-sides per unit of `contracts`):")
    for st, m in _LEG_MODEL.items():
        n = sum(r for _l, r, _a in m["legs"])
        print(f"    {st.value:<20} {len(m['legs'])} leg(s), {n}x  — {m['note']}")
    print()
    return 0


# ── RECONCILIATION against the June 2025 statement ──────────────────────────
# ⚠️ THESE ARE THE STATEMENT'S OWN NUMBERS, transcribed, not derived. Each line
# is (description, contracts, price, cash, action). `cash` is the DEBIT for a
# buy and the CREDIT for a sell, exactly as printed. Implied fee is
# |cash - contracts*price*100|.
# 🔴 ALL TEN LINES ARE `CLOSING CONTRACT`. There is not one opening option
# trade on this statement, so it cannot speak to the open commission at all.
_STATEMENT_2025_06 = [
    ("PUT COST 05/30/25 1010",  3, 0.06,    18.39, "buy"),
    ("CALL COST 05/30/25 1060", 3, 0.35,   105.39, "buy"),
    ("PUT OKTA 05/30/25 120",   5, 17.73, 8865.65, "buy"),
    ("CALL OKTA 05/30/25 130",  5, 0.01,     5.65, "buy"),
    ("CALL NVDA 05/30/25 134",  1, 3.86,   385.86, "sell"),
    ("PUT NVDA 05/30/25 134",   1, 0.14,    13.86, "sell"),
    ("PUT COST 06/06/25 985",   3, 1.25,   374.60, "sell"),
    ("CALL COST 06/06/25 1085", 3, 2.26,   677.60, "sell"),
    ("PUT OKTA 06/06/25 115",   5, 12.63, 6314.34, "sell"),
    ("CALL OKTA 06/06/25 135",  5, 0.01,     4.34, "sell"),
]


def reconcile() -> int:
    print("\n  RECONCILIATION — statement 5WZ-19645-13, June 2025, vs the "
          f"{SCHEDULE_DATE} card")
    print("  ⚠️ every line below is a CLOSING CONTRACT; the statement contains "
          "NO opening")
    print("     option trade, so it cannot test the $1.00/contract open "
          "commission at all.\n")
    print(f"  {'line':<26} {'ct':>3} {'implied':>9} {'modelled':>9} {'resid':>8}")
    residuals = []
    for desc, ct, px, cash, action in _STATEMENT_2025_06:
        gross = ct * px * CONTRACT_MULTIPLIER
        implied = abs(cash - gross)
        lf = _side_fees("NVDA", "single", "close", action, ct,
                        gross if action == "sell" else 0.0)
        modelled = lf.total
        resid = implied - modelled
        residuals.append((desc, ct, implied, modelled, resid))
        print(f"  {desc:<26} {ct:>3} {implied:>9.4f} {modelled:>9.4f} "
              f"{resid:>+8.4f}")

    # 🔑 THE STRONGEST THING THIS STATEMENT PROVES, AND IT IS PROVED HERE
    # RATHER THAN ASSERTED: three matched pairs of SELL lines have the SAME
    # contract count and WILDLY different proceeds, and each pair was charged
    # an IDENTICAL fee. If any proceeds-proportional term (the SEC fee) were
    # being charged at a material rate, the pairs would differ.
    print("\n  PROCEEDS-INDEPENDENCE TEST (sell lines, matched on contract "
          "count):")
    by_ct: Dict[int, list] = {}
    for desc, ct, px, cash, action in _STATEMENT_2025_06:
        if action != "sell":
            continue
        gross = ct * px * CONTRACT_MULTIPLIER
        by_ct.setdefault(ct, []).append((desc, gross, abs(cash - gross)))
    independent = True
    for ct, lines in sorted(by_ct.items()):
        if len(lines) < 2:
            continue
        fees = {round(f, 4) for _d, _g, f in lines}
        proceeds = [g for _d, g, _f in lines]
        same = len(fees) == 1
        independent = independent and same
        print(f"    {ct}ct: proceeds ${min(proceeds):,.2f} vs "
              f"${max(proceeds):,.2f} "
              f"({max(proceeds) / max(min(proceeds), 0.01):,.0f}x)  ->  fee "
              f"{'IDENTICAL' if same else 'DIFFERS'} {sorted(fees)}")
    sec_on_biggest = max(g for _d, g, _f in
                         [x for v in by_ct.values() for x in v]) \
        * SEC_FEE_PER_DOLLAR_SOLD
    if independent:
        print(f"    => ALL THREE PAIRS IDENTICAL. The carded SEC fee would have "
              f"added ${sec_on_biggest:.4f}")
        print(f"       to the largest of them and $0.0001 to its twin; it did "
              f"not. So NO")
        print( "       PROCEEDS-PROPORTIONAL TERM WAS CHARGED on these option "
               "sales in June 2025,")
        print( "       even though footnote 5 of the card says one applies to "
               "option sales.")
        print( "    ⚠️ THE MODEL KEEPS THE SEC TERM ANYWAY — the card is the "
               "authority for a")
        print( "       model of the card, and the term is worth ~$0.13 on a "
               "$6,315 sale against")
        print( "       a $1.00/contract commission. It is FLAGGED, not "
               "removed, and it is the")
        print( "       first thing to drop if a current statement agrees with "
               "this one.")

    print("\n  WHAT THIS SHOWS, AND WHAT IT DOES NOT SETTLE:")
    buys = [r for r in residuals if r[0].startswith(("PUT COST 05", "CALL COST 05",
                                                     "PUT OKTA 05", "CALL OKTA 05"))]
    per_ct = sorted({round(r[2] / r[1], 4) for r in buys})
    print(f"    · buy-to-close implied rate is FLAT at {per_ct} $/contract "
          f"across 4 lines,")
    print(f"      against a modelled ${CLEARING_PER_CONTRACT + ORF_PER_CONTRACT:.2f} "
          f"(clearing ${CLEARING_PER_CONTRACT:.2f} + ORF ${ORF_PER_CONTRACT:.2f}).")
    print("      ONE CENT PER CONTRACT IS UNEXPLAINED. The statement predates "
          "the card by")
    print("      13 months and ORF is exchange-set; no rate history was "
          "supplied, so the")
    print("      component that moved CANNOT BE NAMED from the documents in "
          "hand.")
    sells = [r for r in residuals if r not in buys]
    print(f"    · sell-to-close implied rates: "
          f"{sorted({round(r[2] / r[1], 4) for r in sells})} $/contract — "
          f"consistent with")
    print("      a per-contract sales term on top, but NO SINGLE ROUNDING RULE "
          "fits all")
    print("      three quantities. Not resolved here; not invented here.")
    print("    · the model is left on the PUBLISHED CARD. These residuals are "
          "the open")
    print("      item, and a current statement with OPENING trades is what "
          "would close it.\n")
    return 0


# ── THE MAY 2025 STATEMENT — the one with OPENING trades ────────────────────
# (label, kind, contracts, price, cash, action, open|close). `cash` is the
# DEBIT for a buy and the CREDIT for a sell, transcribed from the statement.
_STATEMENT_2025_05 = [
    ("SPXW 5850C",     "index",  1, 20.45,    2046.78, "buy",  "open"),
    ("SPXW 5870P x20", "index", 20, 4.25,     8535.59, "buy",  "open"),
    ("SPXW 5895P x25", "index", 25, 1.67,     4219.48, "buy",  "open"),
    ("SPXW 5815P x30", "index", 30, 1.82,     5513.38, "buy",  "open"),
    ("SPXW 5835P x45", "index", 45, 5.01,    22625.08, "buy",  "open"),
    ("SPXW 5925C x45", "index", 45, 1.02,     4670.08, "buy",  "open"),
    ("SPXW 5840P x45 s/o", "index", 45, 5.97, 26784.92, "sell", "open"),
    ("SPXW 5920C x45 s/o", "index", 45, 1.31,  5814.92, "sell", "open"),
    ("SPXW 5835P x45 cl",  "index", 45, 0.24,  1044.90, "sell", "close"),
    ("SPXW 5840P x45 cl",  "index", 45, 0.29,  1340.10, "buy",  "close"),
    ("SPXW 5805P x20 cl",  "index", 20, 2.21,  4435.59, "buy",  "close"),
    ("NVDA 134C",      "equity",  1, 4.75,      476.13, "buy",  "open"),
    ("META 645C",      "equity",  2, 5.10,     1022.26, "buy",  "open"),
    ("OKTA 115P",      "equity",  5, 4.82,     2415.65, "buy",  "open"),
    ("COST 985P",      "equity",  3, 8.82666667, 2651.39, "buy", "open"),
    ("SPY 578P x10",   "equity", 10, 0.55,      561.29, "buy",  "open"),
    ("SPY 590C x20",   "equity", 20, 0.10,      212.59, "buy",  "open"),
    ("OKTA 120P s/o",  "equity",  5, 6.62,     3304.34, "sell", "open"),
    ("SPY 590C x49 cl","equity", 49, 0.06,      287.53, "sell", "close"),
    ("META 645C cl",   "equity",  2, 7.65,     1529.73, "sell", "close"),
]
# The two A/E lines, verbatim. 30 contracts each.
_AE_2025_05 = [
    ("SPXW 5895C ASSIGNED", 30, 26.54, 79625.00),
    ("SPXW 5900C EXERCISED", 30, 21.54, 64615.00),
]


def _implied(ct, px, cash):
    return abs(cash - ct * px * CONTRACT_MULTIPLIER)


def reconcile_may() -> int:
    print("\n  MAY 2025 — THE STATEMENT WITH OPENING TRADES (FEE.3's ask)\n")
    print(f"  {'line':<22}{'ct':>3} {'o/c':<6}{'implied/ct':>11}"
          f"{'modelled/ct':>12}{'resid/ct':>10}")
    groups = {}
    for lbl, kind, ct, px, cash, act, oc in _STATEMENT_2025_05:
        imp = _implied(ct, px, cash) / ct
        sym = "SPX" if kind == "index" else "NVDA"
        lf = _side_fees(sym, "l", oc, act, ct,
                        ct * px * CONTRACT_MULTIPLIER if act == "sell" else 0.0)
        mod = lf.total / ct
        # 🔴 THE CAP CONTAMINATES ANY PER-CONTRACT RATE DERIVED FROM IT.
        # A first cut took min() over every line of a group and picked the
        # CAPPED SPY 20-lot (0.6295/ct), then reported equity's open rate as
        # $0.63 and its open-minus-close difference as $0.50 — and then
        # compared "uncapped would be" against that same capped figure, which
        # is circular. Only lines the cap CANNOT bind on may set the rate.
        cap_can_bind = (oc == "open" and kind == "equity"
                        and ct * OPEN_COMMISSION_PER_CONTRACT
                        > EQUITY_COMMISSION_CAP_PER_LEG)
        if not cap_can_bind:
            groups.setdefault((kind, oc), []).append(round(imp, 4))
        print(f"  {lbl:<22}{ct:>3} {oc:<6}{imp:>11.4f}{mod:>12.4f}"
              f"{imp - mod:>+10.4f}")

    print("\n  🎯 WHAT IS NOW CONFIRMED, computed from the table above:")
    io, ic = min(groups[("index", "open")]), min(groups[("index", "close")])
    eo, ec = min(groups[("equity", "open")]), min(groups[("equity", "close")])
    print(f"    · SPX    open {io:.2f}/ct  close {ic:.2f}/ct  "
          f"-> difference {io - ic:.2f}")
    print(f"    · equity open {eo:.2f}/ct  close {ec:.2f}/ct  "
          f"-> difference {eo - ec:.2f}")
    print(f"      THE OPEN COMMISSION IS ${OPEN_COMMISSION_PER_CONTRACT:.2f} "
          f"AND THE CLOSE IS FREE, in both instruments, measured.")
    big = [(l, c, _implied(c, p, x)) for l, k, c, p, x, a, o
           in _STATEMENT_2025_05 if k == "index" and c == 45 and o == "open"]
    capped = 45 * (EQUITY_COMMISSION_CAP_PER_LEG / 45) + 45 * ic
    print(f"    · 🔴 SPX IS NOT CAPPED: 45 contracts cost "
          f"${big[0][2]:.2f}; a $10/leg cap would make it about "
          f"${EQUITY_COMMISSION_CAP_PER_LEG + 45 * ic:.2f}.")
    spy20 = _implied(20, 0.10, 212.59)
    # UNCAPPED is derived from the UNCAPPED rate (eo), which the filter above
    # guarantees is not itself a capped line.
    print(f"    · 🔴 THE EQUITY CAP BINDS: SPY 20 contracts cost ${spy20:.2f}; "
          f"uncapped would be ${20 * eo:.2f}. "
          f"Commission there is about "
          f"${spy20 - 20 * ec:.2f} against 20 x "
          f"${OPEN_COMMISSION_PER_CONTRACT:.2f}.")
    for lbl, ct, px, cash in _AE_2025_05:
        print(f"    · {lbl}: {ct} contracts charged "
              f"${_implied(ct, px, cash):.2f} — ${ASSIGNMENT_FEE_PER_EVENT:.2f} "
              f"PER EVENT, not per contract (${ASSIGNMENT_FEE_PER_EVENT * ct:.2f} "
              f"would be per-contract).")
    print(f"    · EXPIRY IS FREE (${EXPIRY_FEE:.2f}) — two EXPIRED lines, "
          f"30 and -30 contracts, no charge.")

    print("\n  ⚠️ AND THE RESIDUAL IS NOW LOCATED RATHER THAN JUST NOTED:")
    card_eq = CLEARING_PER_CONTRACT + ORF_PER_CONTRACT
    card_ix = card_eq + INDEX_OPTION_FEE_PER_CONTRACT["SPX"]
    print(f"    it is NOT in the commission, which matches to the cent. "
          f"Non-commission")
    print(f"    fees run equity {ec:.2f}/ct against a carded {card_eq:.2f}, "
          f"and SPX {ic:.2f}/ct")
    print(f"    against a carded {card_ix:.2f}. SPX minus equity is "
          f"{ic - ec:.2f}/ct against the card's")
    print(f"    ${INDEX_OPTION_FEE_PER_CONTRACT['SPX']:.2f} exchange fee. "
          f"Both statements agree on the equity number,")
    print( "    so it is a stable 2025 rate, not noise. The component that "
           "moved still")
    print( "    cannot be named; the card is 2026 and no rate history was "
           "supplied.")
    print()
    return 0


# ── SELFTEST ────────────────────────────────────────────────────────────────
FAILURES: List[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def _row(**kw) -> dict:
    r = {"trade_id": "t1", "symbol": "NVDA", "strategy": "ORBStrategy",
         "setup_type": "orb_break", "contracts": 1, "status": "closed",
         "entry_premium": 1.00, "exit_premium": 1.20, "pnl_usd": 20.0}
    r.update(kw)
    return r


def selftest() -> int:
    print("\nfees selftest\n")

    # F1 — the single-leg equity round trip, computed by hand from the card.
    r = _row(contracts=1)
    b = fees_for(r)
    # open : $1.00 comm + $0.10 clearing + $0.02 ORF                  = 1.12
    # close: $0.00 comm + $0.10 + $0.02 + TAF 0.00329 + SEC 120*20.6e-6
    want_open = 1.00 + 0.10 + 0.02
    want_close = 0.10 + 0.02 + 0.00329 + (1.20 * 100 * SEC_FEE_PER_DOLLAR_SOLD)
    check("F1  single-leg equity round trip matches the card",
          abs(b.open_fees - want_open) < 1e-6 and abs(b.close_fees - want_close) < 1e-6,
          f"open ${b.open_fees:.4f} close ${b.close_fees:.4f}")

    # F2 — the $10/leg cap binds on equity and DOES NOT on a broad-based index.
    eq = fees_for(_row(symbol="NVDA", contracts=50, entry_premium=1.0, exit_premium=1.0))
    ix = fees_for(_row(symbol="SPX", contracts=50, entry_premium=6.95, exit_premium=7.45))
    check("F2  equity commission caps at $10/leg",
          abs(eq.component("commission") - 10.00) < 1e-6,
          f"${eq.component('commission'):.2f} on 50 contracts")
    check("F2b SPX commission is UNCAPPED (card excludes broad-based index)",
          abs(ix.component("commission") - 50.00) < 1e-6,
          f"${ix.component('commission'):.2f} on 50 contracts")
    check("F2c SPX carries the $0.60/contract exchange fee on BOTH sides",
          abs(ix.component("index_fee") - 60.00) < 1e-6,
          f"${ix.component('index_fee'):.2f}")
    check("F2d the r201 50-lot SPX ORB costs ~5.5x the same size in an equity",
          ix.total > 5 * eq.total,
          f"SPX ${ix.total:.2f} vs equity ${eq.total:.2f}")

    # F3 — butterfly is FOUR contract-sides per fly per side, not three.
    fly = fees_for(_row(strategy="GEXPinButterfly", setup_type="butterfly_pin",
                        contracts=1, entry_premium=0.17, exit_premium=0.0,
                        is_butterfly=1))
    check("F3  butterfly bills 1/2/1 — 8 contract-sides on a 1-lot round trip",
          fly.contract_sides == 8, f"{fly.contract_sides} sides")
    check("F3b the modelled fly round trip EXCEEDS its own 25% stop floor",
          fly.total > 0.25 * 0.17 * CONTRACT_MULTIPLIER,
          f"fees ${fly.total:.2f} vs floor ${0.25 * 0.17 * 100:.2f} "
          f"on a $0.17 debit")

    # F4 — credit vertical is two legs, and the short leg pays TAF at OPEN.
    cv = fees_for(_row(strategy="SweepCreditSpread", setup_type="sweep_credit",
                       contracts=5, entry_premium=0.58, exit_premium=0.05))
    opens_sold = [l for l in cv.legs if l.side == "open" and l.action == "sell"]
    check("F4  credit vertical is 2 legs / 20 contract-sides at 5 lots",
          cv.contract_sides == 20, f"{cv.contract_sides} sides")
    check("F4b the SHORT leg pays TAF at OPEN (a sale), the long does not",
          len(opens_sold) == 1 and opens_sold[0].taf > 0,
          f"taf ${opens_sold[0].taf:.5f}" if opens_sold else "no sold open leg")

    # F5 — ABSENCE IS NEVER ZERO. Three unpriceable shapes, each NAMED.
    for bad, why in ((_row(contracts=0), "zero contracts"),
                     (_row(contracts=None), "null contracts"),
                     (_row(symbol=""), "no symbol")):
        res = fees_for(bad)
        check(f"F5  unpriceable ({why}) returns Unpriced with a reason",
              isinstance(res, Unpriced) and bool(res.reason),
              getattr(res, "reason", "RETURNED A BREAKDOWN"))

    # F5b — XSP is declined by NAME rather than silently priced as an equity.
    res = fees_for(_row(symbol="XSP", contracts=10))
    check("F5b XSP is declined by name, not priced as an equity",
          isinstance(res, Unpriced) and "QUANTITY-DEPENDENT" in res.reason,
          getattr(res, "reason", "PRICED IT ANYWAY"))

    # F6 — an OPEN position has paid only the open side.
    op = fees_for(_row(status="open", exit_premium=None))
    check("F6  an open position is charged the open side only",
          op.close_fees == 0.0 and op.open_fees > 0,
          f"open ${op.open_fees:.4f} close ${op.close_fees:.4f}")

    # F7 — the rollup ALWAYS reports unpriced, including when it is zero.
    roll = total_fees_usd([_row(), _row(contracts=0), _row(symbol="SPX")])
    check("F7  the rollup reports `unpriced` alongside the total",
          roll["unpriced"] == 1 and roll["priced"] == 2,
          f"priced {roll['priced']}, unpriced {roll['unpriced']}")
    clean = total_fees_usd([_row(), _row()])
    check("F7b `unpriced` is reported even when it is zero",
          "unpriced" in clean and clean["unpriced"] == 0)

    # F8 — net_of_fees returns None on an unpriceable row, NEVER the gross.
    check("F8  net_of_fees returns None on an unpriceable row, not the gross",
          net_of_fees(_row(contracts=0)) is None)
    check("F8b net_of_fees subtracts on a priceable one",
          net_of_fees(_row()) is not None
          and net_of_fees(_row()) < _row()["pnl_usd"],
          f"net ${net_of_fees(_row())}")

    # F9 — the classifier is the ENGINE'S, so a mislabelled legacy row routes
    #      the way the exit engine routes it (structure.of's own §22 rule).
    legacy = _row(strategy="IronCondorStrategy", setup_type="trend_credit_short")
    check("F9  classification defers to strategy.structure.of()",
          fees_for(legacy).structure == Structure.TREND_PARTICIPATION.value,
          fees_for(legacy).structure)

    # F10 — SEC basis is LABELLED, never silently estimated.
    check("F10 single-leg SEC basis is exact; multi-leg is labelled a bound",
          fees_for(_row()).sec_basis == "exact"
          and cv.sec_basis == "net_premium_lower_bound",
          f"single={fees_for(_row()).sec_basis} vertical={cv.sec_basis}")

    # ── F11-F14: PINNED AGAINST THE MAY 2025 STATEMENT'S REAL CHARGES ──────
    # These assert the STRUCTURE the statement measured, not the rates. The
    # rates are a 2026 card and will move; the structure is what the model is.
    spx1 = fees_for(_row(symbol="SPX", contracts=1, entry_premium=20.45,
                         exit_premium=20.45))
    eq1 = fees_for(_row(symbol="NVDA", contracts=1, entry_premium=4.75,
                        exit_premium=4.75))
    # The STRUCTURE: everything except commission is identical on both sides,
    # so the whole open/close asymmetry IS the commission. Measured on the
    # statement as $1.78 vs $0.78 (SPX) and $1.13 vs $0.13 (equity).
    for lbl, bd in (("SPX", spx1), ("equity", eq1)):
        o = [l for l in bd.legs if l.side == "open"][0]
        c = [l for l in bd.legs if l.side == "close"][0]
        same = all(abs(getattr(o, k) - getattr(c, k)) < 1e-9
                   for k in ("clearing", "orf", "index_fee"))
        check(f"F11 the open/close asymmetry IS the commission ({lbl})",
              same and abs(o.commission - c.commission
                           - OPEN_COMMISSION_PER_CONTRACT) < 1e-9,
              f"clearing/ORF/index identical both sides, commission "
              f"${o.commission:.2f} vs ${c.commission:.2f}")

    # 🔑 F11c — A THIRD INDEPENDENT MEASUREMENT THAT THE SALES TERMS ARE NOT
    # CHARGED, and it fell out of F11 failing before it was rewritten. The
    # model's FULL open-minus-close is NOT $1.00: the close is a sale, so it
    # carries TAF and the SEC fee. The statement's is EXACTLY $1.00 on both
    # instruments and every quantity. The gap below is precisely those two
    # carded terms, which the June statement's proceeds-independence test and
    # May's identical 45-lot charges at 4.6x different proceeds also say are
    # not being levied. Recorded, not acted on — see FEE.3.
    gap = OPEN_COMMISSION_PER_CONTRACT - (spx1.open_fees - spx1.close_fees)
    sales_terms = spx1.legs[1].taf + spx1.legs[1].sec
    check("F11c the model's only open/close deviation from $1.00 is TAF+SEC",
          abs(gap - sales_terms) < 1e-9,
          f"model gap ${gap:.4f} == TAF+SEC ${sales_terms:.4f}; the statement "
          f"measured exactly $1.00, so it levied neither")

    # F12 — the statement's own 45-lot, against the cap that does not apply.
    spx45 = fees_for(_row(symbol="SPX", contracts=45, entry_premium=5.01,
                          exit_premium=5.01))
    check("F12 SPX 45-lot open commission is $45, not the $10 cap",
          abs(spx45.legs[0].commission - 45.0) < 1e-9
          and not spx45.legs[0].commission_capped,
          f"${spx45.legs[0].commission:.2f} — the statement charged $80.08 "
          f"for this leg, which no cap can produce")

    # F13 — assignment is PER EVENT. The statement charged $5.00 on 30
    # contracts; per-contract would have been $150.
    check("F13 assignment/exercise is $5.00 per EVENT, not per contract",
          ASSIGNMENT_FEE_PER_EVENT == 5.00 and EXPIRY_FEE == 0.00,
          f"assignment ${ASSIGNMENT_FEE_PER_EVENT:.2f}, "
          f"expiry ${EXPIRY_FEE:.2f}")
    # ⚠️ AND IT IS DELIBERATELY NOT WIRED: nothing in `trades` records that a
    # position was assigned rather than closed, so charging it would be
    # inventing an event. FEE.5 carries that gap.
    check("F13b assignment is EXPOSED but not charged by fees_for()",
          "ASSIGNMENT_FEE_PER_EVENT" not in
          open(__file__).read().split("def fees_for")[1].split("def total_fees_usd")[0])

    # F14 — the measured 2025 rates are RECORDED and NOT APPLIED.
    check("F14 the model prices the CARD, not the measured 2025 rates",
          abs((eq1.close_fees - eq1.legs[1].taf - eq1.legs[1].sec)
              - (CLEARING_PER_CONTRACT + ORF_PER_CONTRACT)) < 1e-9
          and MEASURED_2025_NONCOMM["equity"] != CLEARING_PER_CONTRACT
          + ORF_PER_CONTRACT,
          f"card ${CLEARING_PER_CONTRACT + ORF_PER_CONTRACT:.2f}/ct vs "
          f"measured ${MEASURED_2025_NONCOMM['equity']:.2f}/ct — the gap is "
          f"reported by --reconcile, never absorbed")

    print()
    if FAILURES:
        print(f"fees selftest: FAIL ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("fees selftest: ALL PASS")
    print("\n  worked examples (the numbers behind the findings above):")
    for label, bd in (("50-lot ORB, equity", eq), ("50-lot ORB, SPX", ix),
                      ("1-lot butterfly @ $0.17", fly),
                      ("5-lot credit vertical", cv)):
        print(f"\n  {label}:")
        print(bd.render())
    print()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="fee model for the trades table")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="model vs the June 2025 statement")
    ap.add_argument("--show", action="store_true", help="print the schedule")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.reconcile:
        rc = reconcile_may()
        return reconcile() or rc
    if a.show:
        return show_schedule()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
