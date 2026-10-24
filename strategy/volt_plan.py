"""
strategy/volt_plan.py  v1.7
v1.7  2026-10-19  OTV4TEST r303 (PSTATE.1) — the switch is strategy/plan_state.py's: OT_VOLT=active|log|off ("1" still = active).
      DORMANT (the default) writes its row only if asked - main._safe_strategy no longer asks it; LOG evaluates
      exactly as active and the strategy records the fire LOG-ONLY (take()).
v1.6  2026-10-03  OTV4TEST r220 (TIME.1) — its private HH:MM parser is utils.time_utils.parse_hm (eight plans carried the same copy), and an UNREADABLE clock is DORMANT - no trade - instead of skipping the window check.
v1.5  2026-10-02  OTV4TEST r187 (ROSTER.1) — VOLT IS OFF BY DEFAULT. prepare() goes
      DORMANT at gate `enabled` unless os.environ OT_VOLT is the literal "1",
      read at CALL time. VOLT made -10,236 of QQQ's -15,784 week, lost on every
      symbol, crossed the daily cap 5 of 6 times, and its direction read drifts
      with the 60-candle df_1m (bars[0] is not the session open after ~1 h).
      The operator, 2026-10-02 21:05 ET: "1. CONCUR". OT_VOLT=1 restores it
      exactly. Pinned by tests/check_trade_switches.py.
v1.4  2026-10-02  OTV4TEST r186 (ZBID.1) — `select_contract` (VOLT) refuses a contract
      with no bid: data.options_chain.two_sided beside the QUOTE_FLOOR, whose
      FEASIBILITY reason - "a contract with no live quote cannot fill" - a
      no-bid contract met only because its mark IS its ask. The AAL chain
      of 2026-10-02 (P11.5 0.00/0.22) is pinned by check_zero_bid_refused Z6.
v1.3  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged.
v1.2  2026-09-24  OTV4TEST r131 — DOCSTRING ONLY. The operator, 2026-09-24:
      *"VOLT needs to adopt the breakout sizing model."* The ORDER is now sized
      by RiskManager's geometry/risk rule (main._geometry_inputs, fed
      `sizing_distance = risk_px` by volt_strategy). `provisional_size` below
      is unchanged and is now only the plan's FEASIBILITY bar (does one
      contract fit VOLT_BUDGET_USD), not the size that is placed.
v1.1  2026-09-21  OTV4TEST r74 — THE ENTRY FRAME DROPS TO ONE MINUTE AND THE
      WARM-UP TO THREE BARS. v1.0 gated on COMPLETED 5-MINUTE bars and demanded
      eight of them — 40 minutes — so a window opening at 09:35 could not fire
      before 10:15, measured at NEVER in the first 40 minutes across 18
      sessions. The operator: *"It should be able to fire immediately. I want
      to move on the first sense that volume is expanding and It needs to jump
      on."* Measured after: 24.2 trades/session against 2.0, first fire 09:37.
      ⚠️ THE EXIT FRAME IS UNCHANGED at five minutes — his stop ruling. Entry
      and exit frames are independent, and conflating them is what made the
      window unreachable.
v1.0  2026-09-20  OTV4TEST r72 — VOLT (VOLume Trade). THE CONTROL ARM.

🔑 WHY THIS EXISTS, AND IT IS NOT AN EDGE CLAIM.
The operator, 2026-09-20, after a full day of tape study returned almost
nothing: *"How hard would it be to construct 1 more trade strategy & plan… as
a control group. To study something… Nothing more complicated, since
absolutely ZERO indicators would help inform our trades, apparently."*

VOLT is the NULL HYPOTHESIS MADE TRADEABLE. It gates on TWO things — a
direction read and rising volume — and nothing else. No ADX, no regime, no
level map, no R floor, no freshness prior, no pin, no gamma. If VOLT performs
comparably to the gated strategies on the same tape in the same window, then
the gates are decoration and that is the single most valuable thing this fork
could learn. If VOLT is materially worse, the gates are earning their keep and
we can say so with a measurement instead of a belief.

⚠️ IT MUST NOT COMPETE. Registered blocking nothing and blocked by nothing,
same window as ORB/RUNAWAY/HUNT/BREAKOUT (09:35-11:30), so all five see the
same setups and the losing arm's outcome stays OBSERVABLE. That is r51's
ruling, in the operator's words: *"letting them all go at the same time is
gonna allow us to get the differentiation needed to rule on them later."*
Under a cascade the comparison is impossible.

THE TWO GATES, AND WHERE THEIR NUMBERS CAME FROM.
Both were MEASURED on 247 symbol-sessions of 15-second tape (13 names x 19
sessions, 2026-08-24..09-18) rather than chosen. The measurement asked one
question: from a signal bar, does price reach +0.5 ATR before -1.0 ATR within
30 minutes? That geometry breaks even at 66.7%.

  DIRECTION = close vs the SESSION OPEN. Four reads were tested at three
  volume thresholds (12 cells, all reported, none hidden):
      read              1.25x     1.5x     2.0x
      bar close>open    64.8%    62.8%    66.7%
      close vs EMA20    65.6%    63.1%    68.6%
      2 closes trend    63.3%    61.4%    65.8%
      vs SESSION OPEN   68.8%    66.7%    72.0%   <- best at EVERY threshold
  🔑 IT WINS AT ALL THREE, which is the argument — not the margin. And it is
  the SIMPLEST read available: one comparison, zero parameters, nothing to
  fit. For a control those are the same virtue.

  VOLUME = the 5m bar >= 1.25x the mean of the trailing five completed 1m bars.
  1.25x fires on ~9% of in-window bars (n=445 of the measured sample), which
  is what gives the control enough trades to be measurable at all. 2.0x reads
  higher (72.0%) on n=50 and 3.0x produced n=2 — too rare to study.

⚠️ THE HONEST LIMIT ON BOTH NUMBERS, STATED HERE SO IT IS NOT REDISCOVERED:
the winning cell was picked from 12, so +2.1pp over breakeven is INSIDE the
noise a 12-cell search generates. The cross-threshold consistency is the only
real evidence. And the study measured the UNDERLYING with an ATR target/stop
while VOLT trades an OPTION against a STRUCTURE stop, so it INDICATES the
direction read; it does not translate to VOLT's P&L. Both are DECLARED PRIORS
(WA §31), recorded on every row, and neither has been proven on a trade.

THE STOP IS THE ENTRY — the operator's ruling, 2026-09-21: *"Use a structural
stop. A close beyond where the trade opened is a dead thesis."* A 1m close back
through the entry price ends it. No lookback, no extreme, no fitted number, and
no way for the stop distance to degenerate toward zero (which is exactly what
killed the two designs that preceded it — see the ruling block below).

THE TRAIL ARMS ON DISTANCE, NOT PREMIUM — at 0.5R where R = |entry - stop|,
the operator's spec verbatim. Once armed the floor is
`entry + L x (peak - entry)`, r44's shape, because the OLD trail floor was a
fraction of PREMIUM and could sit BELOW ENTRY: at a +20% arm an 80% lock
floors at 0.96 of entry, so arming the trail could GUARANTEE a loss. The
`entry + L x (peak - entry)` form is >= entry by construction.
"""
from __future__ import annotations

import logging
import os

import config
from strategy.plan import Plan, _n
from data.options_chain import two_sided                       # ZBID.1 (r186)

logger = logging.getLogger(__name__)

# ── EVERY GATE, NAMED AND CATEGORISED (WA §36) ──────────────────────────────
# 🔑 THE SHORTNESS OF THIS DICT IS THE STRATEGY. VOLT has exactly two SELECTION
# gates; everything else here is FEASIBILITY (can this trade exist at all) and
# is not a view on the market. A third SELECTION gate destroys the measurement
# — put it in a NEW strategy.
GATES = {
    "VOL_MULT":           "SELECTION",     # gate 1 of 2 — rising volume
    "WINDOW_OPEN_ET":     "SELECTION",     # the slot, matched to the ORB's
    "WINDOW_CLOSE_ET":    "SELECTION",
    "VOL_LOOKBACK_BARS":  "SELECTION",     # what "rising" is measured against
    "MIN_BARS":           "FEASIBILITY",   # fewest bars before the gate can be read
    "TRAIL_ARM_R":        "SELECTION",     # exit geometry, the operator's spec
    "TRAIL_LOCK_FRAC":    "SELECTION",
    "QUOTE_FLOOR":        "FEASIBILITY",   # a contract with no quote cannot fill
    "BUDGET_USD":         "FEASIBILITY",   # zero contracts is not a trade
    "CONTRACT_MULT":      "FEASIBILITY",
    "DELTA_BIAS":         "FEASIBILITY",   # carried from the ORB selector — NOT RULED
}
# ⚠️ DIRECTION — gate 2 of 2 — is NOT a constant and so cannot appear above.
# It is `close vs the session open`, has no threshold, and nothing to tune.
# That is deliberate: a direction read with a knob is a read that gets fitted.

# ── DECLARED PRIORS — every one is recorded on the row and none is proven ────
VOL_MULT           = float(getattr(config, "VOLT_VOL_MULT", 1.25))
VOL_LOOKBACK_BARS  = int(getattr(config, "VOLT_VOL_LOOKBACK_BARS", 5))
MIN_BARS           = int(getattr(config, "VOLT_MIN_BARS", 3))
TRAIL_ARM_R        = float(getattr(config, "VOLT_TRAIL_ARM_R", 0.50))
TRAIL_LOCK_FRAC    = float(getattr(config, "VOLT_TRAIL_LOCK_FRAC", 0.50))
WINDOW_OPEN_ET     = tuple(config.VOLT_WINDOW_OPEN_ET)     # r148: no literal fallback
WINDOW_CLOSE_ET    = tuple(config.VOLT_WINDOW_CLOSE_ET)    # r148: no literal fallback

QUOTE_FLOOR   = 0.05
DELTA_BIAS    = getattr(config, "ORB_STRIKE_DELTA_BIAS", "lower")
BUDGET_USD    = float(getattr(config, "VOLT_BUDGET_USD",
                              getattr(config, "ORB_BUDGET_USD", 0.0)) or 0.0)
CONTRACT_MULT = int(getattr(config, "CONTRACT_MULTIPLIER", 100))


from utils.time_utils import parse_hm as _hhmm    # r220 (TIME.1): the one parser


def select_contract(chain, direction: str, target_strike: float, otm_from=None):
    """Nearest listed strike to the target with a live quote, restricted to
    OUT OF THE MONEY when `otm_from` (spot) is supplied.

    🔑 OTM IS THE OPERATOR'S RULING, 2026-09-21: *"Select the nearest OTM
    strike."* Long -> the nearest strike ABOVE spot; short -> nearest BELOW.
    ⚠️ A DELIBERATE DIVERGENCE FROM `orb_plan.select_contract`, which takes the
    nearest strike on EITHER side. The earlier rationale — keep the selector
    identical so the comparison isolates the GATES — is SUPERSEDED and struck
    rather than deleted (r240): it was true, and the ruling overrides it. An
    OTM debit is cheaper, so at a fixed $1,050 budget VOLT buys MORE contracts
    carrying MORE gamma and no intrinsic, which is a genuinely different risk
    profile and not merely a different strike.
    ⚠️ FAILS CLOSED. If nothing OTM is quoted this returns None and the plan
    records a STARVED contract. A quiet fall-back to ATM would leave some VOLT
    trades ATM and some OTM with nothing recording which, so the row would not
    describe the trade (§0.5).
    """
    if chain is None or target_strike is None:
        return None
    contracts = chain.calls if direction == "long" else chain.puts
    cands = [c for c in (contracts or []) if float(getattr(c, "mark", 0) or 0) > QUOTE_FLOOR
             and two_sided(c)]                                  # ZBID.1 (r186)
    if otm_from is not None:
        spot = float(otm_from)
        cands = [c for c in cands
                 if (float(c.strike) > spot if direction == "long"
                     else float(c.strike) < spot)]
    if not cands:
        return None
    dist = min(abs(float(c.strike) - float(target_strike)) for c in cands)
    nearest = [c for c in cands if abs(float(c.strike) - float(target_strike)) <= dist + 1e-6]
    if len(nearest) == 1:
        return nearest[0]
    key = lambda c: abs(float(getattr(c, "delta", 0) or 0))          # noqa: E731
    return min(nearest, key=key) if DELTA_BIAS == "lower" else max(nearest, key=key)


def provisional_size(premium: float, budget_usd: float = BUDGET_USD) -> int:
    """Budget / cost — the plan's FEASIBILITY bar and its recorded
    `size_provisional`. ⚠️ r131: this is NO LONGER THE PLACED SIZE. By the
    operator's 2026-09-24 ruling (*"VOLT needs to adopt the breakout sizing
    model"*) the order is sized by RiskManager._size_geometry on the signal
    range (`sizing_distance`); the r72 note that VOLT does not size off
    geometry is superseded by that ruling."""
    cost = float(premium or 0.0) * CONTRACT_MULT
    if cost <= 0:
        return 0
    if budget_usd <= 0:
        return 1
    return max(0, int(budget_usd // cost))


def _median_range(bars):
    """Median high-low of the given 5m bars — the session's own noise scale.
    Median, not mean, so one wide bar cannot inflate the floor."""
    rs = sorted((b[1] - b[2]) for b in bars if b[1] >= b[2])
    if not rs:
        return 0.0
    n = len(rs)
    return rs[n // 2] if n % 2 else (rs[n // 2 - 1] + rs[n // 2]) / 2.0


def _bars_1m(df_1m):
    """Completed 1-minute bars as (open, high, low, close, volume), oldest
    first. Returns [] on anything unexpected — a control that guesses when its
    input is malformed is not a control.

    🔑 ONE MINUTE, NOT FIVE, AND THAT IS THE WHOLE POINT (r74). r72 aggregated
    to 5m here and then demanded eight completed bars, which is 40 minutes of
    session — so VOLT could not fire before 10:15 in a window that opens at
    09:35. Measured over 18 sessions: it NEVER fired in the first 40 minutes.
    The operator's spec: *"It should be able to fire immediately. I want to
    move on the first sense that volume is expanding and It needs to jump on."*
    ⚠️ THE EXIT FRAME IS STILL FIVE MINUTES — `exit_engine._evaluate_volt`
    reads `df_5m`, by his earlier ruling. Entry and exit frames are
    independent; conflating them is what made the window unreachable."""
    if df_1m is None or getattr(df_1m, "empty", True):
        return []
    out, cur, cur_key = [], None, None
    try:
        for ts, row in df_1m.iterrows():
            key = (ts.hour, ts.minute)
            h, l = float(row.get("high")), float(row.get("low"))
            o, c = float(row.get("open")), float(row.get("close"))
            v = float(row.get("volume") or 0.0)
            if key != cur_key:
                if cur is not None:
                    out.append(cur)
                cur, cur_key = [o, h, l, c, v], key
            else:
                cur[1] = max(cur[1], h); cur[2] = min(cur[2], l)
                cur[3] = c; cur[4] += v
        if cur is not None:
            out.append(cur)                 # the FORMING bar, last
    except (AttributeError, TypeError, ValueError) as exc:
        logger.debug("volt: 1m frame read skipped: %s", exc)
        return []
    return out


class VoltPreparation:
    """What the plan hands the strategy each tick — never executable alone."""
    __slots__ = ("tick", "state", "direction", "side", "session_open", "price",
                 "bar_volume", "vol_baseline", "vol_ratio", "stop", "risk_px",
                 "trail_arm_px", "target_strike", "contract", "premium",
                 "size_provisional", "waiting_on", "starved", "ready")

    def __init__(self, tick):
        self.tick = tick
        self.state = ""
        self.direction = self.side = ""
        self.session_open = self.price = None
        self.bar_volume = self.vol_baseline = self.vol_ratio = None
        self.stop = self.risk_px = self.trail_arm_px = None
        self.target_strike = None
        self.contract = None
        self.premium = None
        self.size_provisional = 0
        self.waiting_on = ""
        self.starved = []
        self.ready = False

    def trade_line(self) -> str:
        c = self.contract
        if c is None:
            return "no trade prepared"
        return (f"buy {float(c.strike):g}{self.side[0].upper()} @ {_n(self.premium)}  "
                f"stop {_n(self.stop)} (a close back through the entry)  "
                f"R {_n(self.risk_px)}  trail arms {_n(self.trail_arm_px)} "
                f"({TRAIL_ARM_R:g}R)  size {self.size_provisional} provisional  "
                f"[vol {_n(self.vol_ratio)}x >= {VOL_MULT:g}x]")


class VoltPlan:
    """Owns the chain search and the row. TWO GATES AND NOTHING ELSE."""
    name = "VOLT"

    PLAN_CHECKS = ("entry_window", "session_open", "price_now", "direction",
                   "bar_volume", "vol_baseline", "vol_ratio", "vol_gate",
                   "stop_level", "risk_px", "signal_range", "trail_arm_px",
                   "target_strike", "contract", "premium", "size_provisional")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS,
                            record_only=True, self_ledgers=True)

    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, *, chain, price_now, df_1m=None, now_hhmm: str = "",
                already_open: bool = False) -> VoltPreparation:
        t = self.planner.tick(price_now)
        prep = VoltPreparation(t)
        prep.price = price_now
        # r187 (ROSTER.1): OFF by default; r303 (PSTATE.1): the state is plan_state's, read now - LOG evaluates
        from strategy import plan_state as _ps
        if _ps.is_dormant("VOLT"):
            t.dormant("enabled", "VOLT is OFF by the operator's ruling 2026-10-02 "
                                 "(OT_VOLT=active restores it, OT_VOLT=log records it)")
            return prep

        bars = _bars_1m(df_1m)
        # completed bars only — the forming bar's volume is a partial count and
        # gating on it would fire early on a bar that ends up ordinary.
        completed = bars[:-1] if len(bars) >= 1 else []

        # ── the window: OUTSIDE IT THE PLAN OBSERVES AND DOES NOT WRITE ────
        hm = _hhmm(now_hhmm)
        if hm is None:                                           # r220: a window that cannot be checked is not open
            t.dormant("entry_window", "the clock could not be read — no trade")
            return prep
        if hm is not None and not (tuple(WINDOW_OPEN_ET) <= hm < tuple(WINDOW_CLOSE_ET)):
            t.dormant("entry_window",
                      f"outside the VOLT slot {WINDOW_OPEN_ET[0]:02d}:{WINDOW_OPEN_ET[1]:02d}"
                      f"-{WINDOW_CLOSE_ET[0]:02d}:{WINDOW_CLOSE_ET[1]:02d} — observing only")
            return prep
        t.check("entry_window", 1.0, ok=True)
        t.check("price_now", price_now)

        # ⚠️ THREE, NOT VOL_LOOKBACK_BARS+2. r72 demanded eight COMPLETED bars
        # while the study that produced the 1.25x threshold required only
        # three and tolerated a short baseline — the number was justified by
        # one rule and enforced by a stricter one, and the difference was a
        # third of the trading window.
        if len(completed) < MIN_BARS + 1:
            # ⚠️ starved() CLOSES the tick and writes the row. A hold() after
            # it writes a SECOND row for one decision — 'could not evaluate'
            # would then appear twice with different wording.
            prep.starved.append("bars_5m")
            return t.starved("bars_5m") or prep

        # ── GATE 1 — DIRECTION: close vs the SESSION OPEN. That is the whole
        #    read. Measured best of four at every volume threshold, and the
        #    only one with no parameter to fit.
        session_open = float(bars[0][0])
        prep.session_open = session_open
        t.check("session_open", session_open)
        last_close = float(completed[-1][3])
        direction = "long" if last_close > session_open else "short"
        prep.direction = direction
        prep.side = "call" if direction == "long" else "put"
        t.check("direction", 1.0 if direction == "long" else -1.0)

        # ── GATE 2 — RISING VOLUME on the last COMPLETED 5m bar ───────────
        window = completed[-(VOL_LOOKBACK_BARS + 1):-1]
        baseline = sum(b[4] for b in window) / float(len(window)) if window else 0.0
        bar_vol = float(completed[-1][4])
        prep.bar_volume, prep.vol_baseline = bar_vol, baseline
        t.check("bar_volume", bar_vol)
        t.check("vol_baseline", baseline)
        if baseline <= 0:
            prep.starved.append("vol_baseline")
            return t.starved("vol_baseline") or prep
        ratio = bar_vol / baseline
        prep.vol_ratio = ratio
        t.check("vol_ratio", ratio)
        if ratio < VOL_MULT:
            t.check("vol_gate", ratio, ok=False)
            t.refuse("vol_gate",
                     f"volume {ratio:.2f}x baseline, below the {VOL_MULT:g}x prior")
            return prep
        t.check("vol_gate", ratio, ok=True)

        # ── THE STRUCTURAL STOP — THE OPERATOR'S RULING, 2026-09-21:
        #    *"Use a structural stop. A close beyond where the trade opened is
        #    a dead thesis."*
        # 🔑 THE STOP IS THE ENTRY. VOLT's thesis is "volume arrived and price
        # is on this side of the session open". A close back through the price
        # that thesis was acted on is the thesis being wrong — there is nothing
        # left to hold. No lookback, no extreme, no fitted level.
        # 🔴 IT REPLACED TWO WORSE DESIGNS AND THE REPLAY IS WHY, measured over
        # 19 sessions x 4 symbols with the REAL plan before this landed:
        #     3-bar structural extreme   meanR -1.430   WORST  -120R
        #     signal bar's own extreme   meanR -5.832   WORST  -749R
        #     THE RULING (close beyond entry)  meanR +0.008   worst  -1.49R
        # Both of mine share one defect: a tight structure puts the stop AT the
        # entry, risk -> 0, and R explodes. The ruling removes the failure mode
        # by construction rather than by flooring it.
        # ⚠️ SO `underlying_stop` EQUALS `underlying_entry` BY DESIGN, and that
        # is why the spec sets `underlying_stop_is_thesis = True`: r61's
        # entry-underwater guard is STRICT ("at or beyond the stop is through")
        # and would otherwise refuse every VOLT trade. The opt-out is declared
        # at the site that writes the column, as r61 requires.
        prep.stop = float(price_now)
        t.check("stop_level", prep.stop)
        # R IS THE SIGNAL BAR'S RANGE — the trail needs a distance and the stop
        # no longer supplies one. The bar whose volume triggered the entry is
        # the move's own scale, which is the honest denominator.
        sig = completed[-1]
        risk = float(sig[1] - sig[2])
        t.check("signal_range", risk)
        prep.risk_px = risk
        t.check("risk_px", risk)
        if risk <= 0:
            prep.starved.append("risk_px")
            return t.starved("risk_px") or prep
        # the trail arms on DISTANCE, the operator's spec: 0.5R from entry.
        prep.trail_arm_px = (float(price_now) + TRAIL_ARM_R * risk if direction == "long"
                             else float(price_now) - TRAIL_ARM_R * risk)
        t.check("trail_arm_px", prep.trail_arm_px)

        # ── the contract: NEAREST OTM (operator's ruling; see select_contract)
        # target = spot; the OTM restriction then yields the first strike
        # BEYOND it in the trade's direction — "the nearest OTM strike".
        prep.target_strike = float(price_now)
        t.check("target_strike", prep.target_strike)
        contract = select_contract(chain, direction, prep.target_strike,
                                   otm_from=float(price_now))
        if contract is None:
            prep.starved.append("contract")
            return t.starved("contract") or prep
        prep.contract = contract
        prep.premium = float(getattr(contract, "mark", 0) or 0)
        t.check("contract", float(contract.strike))
        t.check("premium", prep.premium)
        prep.size_provisional = provisional_size(prep.premium)
        t.check("size_provisional", float(prep.size_provisional))
        if prep.size_provisional < 1:
            t.refuse("size_provisional", "budget buys zero contracts")
            return prep

        if already_open:
            t.already()
            return prep

        t.debit_directional(prep.premium,
                            float(getattr(contract, "delta", 0) or 0),
                            float(getattr(contract, "gamma", 0) or 0),
                            risk,
                            invalidation=prep.stop)
        prep.ready = True
        return prep
