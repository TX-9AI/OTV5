"""
strategy/liquidity_hunt.py  v1.14
v1.14 2026-10-24  OTV4TEST r316 (HUNT.13) — NO HUNT ON A SIDE AFTER A LOSING BREAKOUT ON THAT SIDE, FOR THE REST OF THE DAY.
      The operator, 2026-10-24 13:45 ET: "on a losing breakout trade, forbid a liquidity hunt on the same side for the
      day"; 13:56 ET: "if a breakout on one side fails, don't allow a hunt to fire on that side for the rest of the
      day" ... "effective Monday". breakout_failed_today() reads trades.db (DEC.1): a CLOSED Breakout row today on that
      side (option_side, call = long) with pnl_usd < 0; unreadable HOLDS. OT_HUNT_AFTER_BRK=trade|log|off (unset =
      trade); every hold and would-be hold is written to data/counterfactual/hunt_after_breakout.jsonl. Evidence
      (QQQ-TEST 09-09..10-23): 2 Hunts after a losing same-side Breakout, both lost (-489); SOFI none. Thin.
v1.13 2026-10-19  OTV4TEST r304 (HUNT.12) — release_break(direction, boundary): main.py hands a break BACK when its fire
      opened nothing (QQQ 10-19 10:13: the A2 long from 718.36 was BLOCKED by COMMIT.2, yet the fire had already put the
      break in FINISHED, so the plan held "this break already had its hunt" and only the late A1 at 720.49 - past its own
      720.40 target - was left, -$87.50). The operator, 2026-10-19 11:16 ET: "1. Yes". The fire still marks the break
      (one per break inside the tick is unchanged); only main.py's door, after execution, can release it.
v1.12 2026-10-18  OTV4TEST r297 (HUNT.11) — ONE HUNT PER BREAK SURVIVES A RESTART. FINISHED was an in-memory set and nothing
      read trades.db, so a restart with no Hunt open re-fired the same boundary (audit 2026-10-18 A6; the Runaway's twin
      has been DB-backed since r281). break_finished_in_book() keys today's Hunt rows by option_side + underlying_stop
      (the entry boundary); the plan asks it when the set does not already know, caches a True, and HOLDS named on an
      unreadable book. A LOG-ONLY (observed) fire still never touches the set or the book.
v1.11 2026-10-18  OTV4TEST r289 (RUN.9, mirror of otv4 r492) — the Hunt calls the same gamma_leverage_pick: it passes note=
      and DECLINEs with its reason when the chain's first OTM strike is not a candidate (no nearest-survivor fallback).
v1.10 2026-10-15  HUNT.9 (FORK-ONLY) — A2 RE-ARMED BY A RETURN TO THE RANGE IS RECORDED, NEVER TRADED. The operator,
      2026-10-14 10:28 ET: "It should be permitted if it goes back into the range"; 2026-10-15 10:16 ET: "Concur on
      all" (to "BRK.12 / HUNT.9: record-only"). After a boundary's A2 was taken, a 1m close on the far side again
      followed by a close back inside writes the A2 it would have fired (boundary, price, target, runway) to
      data/counterfactual/hunt_rearm.jsonl; FINISHED is untouched, so "one per break" still refuses it. A1 is
      unchanged; an observed (past-cutoff) pass records nothing. OT_HUNT_REARM=log|off (unset = log).
v1.9 2026-10-05  OTV4TEST r254 (OBS.1) — THE PLAN ALWAYS LOOKS, THE STRATEGY IS GATED ON THE HOUR: Breakout, Runaway and the Hunt are OBSERVED from their entry end to 15:40 - asked, recorded LOG-ONLY, never executed (the operator, 2026-10-05: "the plan always looks, but the strategies are gated on the hour of the day"; "Have those blocked TRADES just to Log only"). Here: past the cutoff the plan keeps looking only while observed; an observed fire never touches FINISHED.
v1.8  2026-10-03  OTV4TEST r229 (EM.2) — records em_platform (the tastytrade platform's expected move) beside the session number its above_em / below_em records are measured in. Nothing here ever gated on either.
v1.7  2026-10-03  OTV4TEST r220 (TIME.1) — its private HH:MM parser is utils.time_utils.parse_hm (eight plans carried the same copy), and an UNREADABLE clock is DORMANT - no trade - instead of skipping the window check.
v1.6  2026-10-03  OTV4TEST r193 (CFG.1) — its config dials are read as config.NAME with NO literal fallback; config v4.48 now defines them (they were getattr defaults on names config never had). Values unchanged.
v1.5  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged.
v1.4  2026-09-22  OTV4TEST r104 - THE RAILS NO LONGER OUTRANK A HELD
      EXTREME. `sorted(b["above"] + tines_up)` was one merged list and
      `na = above[0]` took whatever sat nearest, so a rail inside the nearest
      held extreme became THE level this plan hunts - and the hunt's whole
      thesis is the pool of resting stops beyond a held extreme, which a sloped
      rail does not have. Ordering (outward from the ORB edge) and the hi/lo
      rail filter are unchanged. Adds rails_in_play and the rail projection.
v1.3  2026-09-19  OTV4TEST r61 (ENT.1) — declares `underlying_stop_is_thesis`.
      This file writes `prep.boundary` into `underlying_stop` and its own
      comment says what that is: *"thesis-dead: a close back through it"*. The
      new entry-underwater guard refuses any trade opening beyond its stop, and
      a hunt opens beyond its boundary BY CONSTRUCTION, so it declares the
      column non-protective at the site that writes it.
v1.2  2026-09-17  OTV4TEST r33 — THE BOARD COMPOSITION MOVED OUT OF THIS FILE.
      `_board` held the eight lines that prefer the live LevelEngine and fall back
      to the bound store — correct, and the ONLY plan that had them. The sweep and
      the TCS did not, and r33's first cut gave them a registry-only read that
      returned zero levels under every fixture (five green checks went red). Those
      lines are now `derived.levels.board_for()`, called by all three. THIS PLAN'S
      QUESTION IS UNCHANGED: it still passes its ORB bounds, so the bias is still
      the nearest level BEYOND the opening range measured from the edge (r12).
      Only where the composition lives moved.
v1.1  2026-09-12  OTV4TEST r15 — the bias is read off the LEVEL BOARD (PLAN_SPEC §38):
      held levels beyond the range ordered outward plus the rails computed at this
      read, never a stale tine row; `board_state` is a check so silence is never
      clearance. The PDH/PDL ladder is now visible (levels v4.3).
v1.0  2026-09-10  OTV4TEST r12 — THE LIQUIDITY HUNT (PLAN_SPEC §37). Operator,
      2026-09-10, from the predecessor's own numbers: the ORB break-and-retest
      risks $71 to make $37; the momentum trade pays ~2:1 with the least
      give-back across ~300 trades. *"Under most circumstances price is going
      to go towards where the liquidity is."* So: from the five-minute opening
      range, price sweeps the nearest liquidity level; trade the BREAK TOWARD
      that level rather than wait for a retest, and on the rejection hand off
      to the sweep. Morning only. Runs in PARALLEL with the ORB — neither
      blocks the other — so the two are compared on the same range, the same
      levels, the same fills.

      BIAS — read at 09:35 from the level store: the nearest live named level
      (PDH/PDL, session extremes, pools, the 1h tines; nothing inside the range
      exists) measured from the RANGE EDGE, above vs below. The nearer side is
      the market's intent. *"Some of the earliest moves of the session are
      fake-outs and do not represent the intent."*

      ENTRIES — the liquidity picks the side; the break only times it.
        A1  a 1m close outside the range ON THE BIAS SIDE.
        A2  a far-side break that CLOSES BACK INSIDE the range — entered on
            that close, from the far boundary, direction = bias. *"Taking out
            a previous session high from the lower bound of the opening range
            boundary."* The whole range is runway.
        A far-side break that does NOT fail: not traded, recorded ("broke away
        from the liquidity"). One hunt per break key (direction, boundary).

      TARGET — the level itself. The runway is KNOWN at entry, so the strike is
      the gamma pick over that runway (runaway_continuation.gamma_leverage_pick
      with run = distance to the level), teenie gate bounding the cheap end.

      EXITS (exit_engine, the runaway's family routed by strategy name):
        · thesis dead — a 1m close back through the entry boundary
          (A1: the range edge it broke; A2: the far boundary it re-entered)
        · REJECTED at the level — the hunt exits and GRANTS THE HANDOFF to the
          sweep (execution/handoff.py) — the reversal is the sweep's trade
        · ACCEPTED at the level — over-delivered; hold on the runaway's exits
        · the fizzle read · 15:45. No premium stop.

      SLOT — exempt on entry and not counted as blocking (position_manager
      v4.9), exactly the butterfly's rule, so an open ORB and an open hunt can
      both be long the same break. That is the paired comparison.

      Every tick from 09:35 the row carries: the bias, both nearest levels and
      their distance in EM, the entry armed for, the runway, the strike. Every
      "not traded" names why.
"""
from __future__ import annotations

import logging

import config
from strategy import relaxed
from strategy import observe as _observe   # r254 (OBS.1)
from strategy.base_strategy import OptionsSignal as Signal
from strategy.plan import Plan, _n
from strategy.runaway_continuation import gamma_leverage_pick, target_delta, ATR_FLOOR_PCT
from strategy.sweep_credit_spread import _symbol_of
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)

GATES = {
    "ATR_FLOOR_PCT":   "FEASIBILITY",     # the runaway's; can the tape reach a strike
    "WINDOW_OPEN_ET":  "FOUNDATIONAL",
    "CUTOFF_ET":       "FOUNDATIONAL",
}

WINDOW_OPEN_ET = config.ENTRY_OPEN_ET   # r148: no literal fallback
CUTOFF_ET      = config.HUNT_CUTOFF_ET          # r148: no literal fallback
MAX_LOSS_PCT   = float(config.HUNT_MAX_LOSS_PCT)

FINISHED: set = set()          # (direction, boundary) this process has hunted - a CACHE since r297; trades.db decides


def release_break(direction: str, boundary) -> bool:
    """r304 (HUNT.12) — forget that (direction, boundary) was hunted, because its fire opened NOTHING (main.py
    calls this only after execution left no Hunt position and no trades.db row for the break). True if it was
    held. Never raises."""
    try:
        key = (str(direction), round(float(boundary), 2))
        held = key in FINISHED
        FINISHED.discard(key)
        return held
    except Exception:                                           # noqa: BLE001
        return False


def break_finished_in_book(direction: str, boundary, session_date=None):
    """r297 (HUNT.11) — what trades.db says about THIS break today. NEVER raises.

      True          — a Hunt (open or closed) already traded this (direction, boundary) today
      False         — none has: it may trade
      "unreadable"  — the book could not be read; the caller FAILS CLOSED

    The in-memory FINISHED set died with every restart, so a restart with no Hunt open re-fired the
    same boundary (audit 2026-10-18 A6); the Runaway's twin has read trades.db since r281. A Hunt row
    keys its break by option_side (call = long, put = short) and underlying_stop, which the Hunt
    writes as its ENTRY BOUNDARY (ENT.1). ANY row counts - a win finishes the break as surely as a stop.
    """
    from datetime import datetime, timedelta
    try:
        from zoneinfo import ZoneInfo
        _et, _utc = ZoneInfo("America/New_York"), ZoneInfo("UTC")
        day = session_date or datetime.now(_et).date()
        bnd = round(float(boundary), 2)
        lo = (datetime.combine(day, datetime.min.time(), _et)
              - timedelta(hours=1)).astimezone(_utc).isoformat()
        from database.trade_logger import get_trade_logger
        conn = get_trade_logger()._connect()
        try:
            rows = conn.execute(
                "SELECT entry_time, option_side, underlying_stop FROM trades "
                "WHERE strategy='LiquidityHunt' AND entry_time >= ?", (lo,)).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[hunt] break status unreadable from trades.db (%s) — failing closed", exc)
        return "unreadable"
    for et_, side, ustop in rows:
        sd = str(side or "").lower()
        d = "long" if sd.startswith("c") else ("short" if sd.startswith("p") else "")
        if d != direction:
            continue
        try:
            if ustop is None or round(float(ustop), 2) != bnd:
                continue
            if datetime.fromisoformat(str(et_)).astimezone(_et).date() != day:
                continue
        except (TypeError, ValueError):
            continue
        return True
    return False


def breakout_failed_today(direction: str, session_date=None):
    """r316 (HUNT.13) - the LOSING Breakout that closes this side to the Hunt today. NEVER raises.

      (trade_id, pnl_usd) - a CLOSED Breakout on `direction` today with pnl_usd < 0 (the first such)
      None                - none has: the Hunt may trade
      "unreadable"        - the book could not be read; the caller HOLDS (fails closed)

    The side is option_side (call = long, put = short), direction the fallback, as side_entries_today; rows are
    the current mode's (paper or live) only.
    """
    from datetime import datetime, timedelta
    try:
        from zoneinfo import ZoneInfo
        _et, _utc = ZoneInfo("America/New_York"), ZoneInfo("UTC")
        day = session_date or datetime.now(_et).date()
        lo = (datetime.combine(day, datetime.min.time(), _et)
              - timedelta(hours=1)).astimezone(_utc).isoformat()
        from database.trade_logger import get_trade_logger
        tl = get_trade_logger()
        conn = tl._connect()
        try:
            rows = conn.execute(
                "SELECT trade_id, entry_time, option_side, direction, pnl_usd FROM trades "
                "WHERE strategy='Breakout' AND status='closed' AND entry_time >= ? "
                "AND COALESCE(paper_trade,1)=? ORDER BY exit_time",
                (lo, int(getattr(tl, "_mode_flag", 1)))).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[hunt] Breakout history unreadable from trades.db (%s) - holding", exc)
        return "unreadable"
    for tid, et_, side, dirn, pnl in rows:
        sd = str(side or "").lower()
        d = "long" if sd.startswith("c") else ("short" if sd.startswith("p") else str(dirn or "").lower())
        if d != direction:
            continue
        try:
            if datetime.fromisoformat(str(et_)).astimezone(_et).date() != day:
                continue
            if pnl is not None and float(pnl) < 0:
                return (str(tid), float(pnl))
        except (TypeError, ValueError):
            continue
    return None


_HAB_SAID: set = set()


def _record_hunt_after_breakout(row: dict) -> None:
    """r316 (HUNT.13) COUNTERFACTUAL: once per (symbol, direction, boundary, entry) per process, the Hunt a losing
    same-side Breakout held (or, in log mode, would have held), to data/counterfactual/hunt_after_breakout.jsonl.
    Never raises; a failed write is logged."""
    key = (row.get("symbol"), row.get("direction"), row.get("boundary"), row.get("entry"))
    if key in _HAB_SAID:
        return
    _HAB_SAID.add(key)
    try:
        import json, os, time
        d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "counterfactual")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "hunt_after_breakout.jsonl"), "a") as fh:
            fh.write(json.dumps({"ts_epoch": time.time(), "rule": "hunt_after_breakout",
                                 "mode": getattr(config, "HUNT_AFTER_BRK_MODE", "trade"), **row}) + "\n")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[hunt] after-breakout counterfactual row NOT written: %s", exc)


def _record_hunt_rearm(row: dict) -> None:
    """HUNT.9 COUNTERFACTUAL: the A2 a return to the range would have fired, NOT traded, to
    data/counterfactual/hunt_rearm.jsonl. Never raises; a failed write is logged, never fatal."""
    try:
        import json, os, time
        d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "counterfactual")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "hunt_rearm.jsonl"), "a") as fh:
            fh.write(json.dumps({"ts_epoch": time.time(), "rule": "hunt_rearm",
                                 "mode": getattr(config, "HUNT_REARM_MODE", "log"), **row}) + "\n")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[hunt] re-arm counterfactual row NOT written: %s", exc)


from utils.time_utils import parse_hm as _hm      # r220 (TIME.1): the one parser


class HuntPreparation:
    __slots__ = ("tick", "bias", "above", "below", "target", "target_name", "entry", "direction",
                 "side", "boundary", "runway", "em_frac", "contract", "premium", "floor_premium",
                 "leverage", "structural", "starved", "unmet", "ready", "note")

    def __init__(self, tick):
        self.tick = tick
        self.bias = ""
        self.above = self.below = None
        self.target = self.target_name = None
        self.entry = self.direction = self.side = ""
        self.boundary = self.runway = self.em_frac = None
        self.contract = self.premium = self.floor_premium = self.leverage = None
        self.structural, self.starved, self.unmet = [], [], []
        self.ready = False
        self.note = ""

    def trade_line(self):
        c = self.contract
        if c is None:
            return "no contract selected"
        return (f"buy {float(c.strike):g}{self.side[0].upper()} @ {_n(self.premium)}  "
                f"floor {_n(self.floor_premium)}  runway {_n(self.runway)} to "
                f"{self.target_name} {_n(self.target)} ({_n(self.em_frac)} EM)  "
                f"entry {self.entry} from {_n(self.boundary)}")


class LiquidityHunt:
    name = "LiquidityHunt"
    PLAN_CHECKS = ("entry_window", "price", "atr_pct", "orb_range", "board_state",
                   "rails_in_play",                                    # r104
                   "board_above",
                   "board_below", "fork_built", "nearest_above", "nearest_below",
                   "above_em", "below_em", "em_platform", "bias", "break_state", "fake_seen", "fake_failed",
                   "entry", "break_finished", "breakout_failed", "runway", "considered", "spread_rejected",
                   "contract", "leverage", "debit", "stop_premium")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS, record_only=True, self_ledgers=True)
        self._store = None
        self._fake: dict = {}         # break key -> {"seen": bar_ts, "failed": bool}
        self._last_bar_ts = ""
        self._bias_day = ""           # the bias is read once per session, at 09:35

    def _store_(self):
        if self._store is not None:
            return self._store
        try:
            from data.derived_store import get_derived_store
            return get_derived_store()
        except Exception:                                       # noqa: BLE001
            return None

    def _board(self, price_now, hi, lo) -> dict:
        """r33 — the shared entry point. This plan keeps its RANGE anchoring:
        the bias is the nearest level BEYOND the opening range, measured from
        the edge (r12), and that is untouched. Only the composition moved —
        the eight lines that lived here are now `derived.levels.board_for`,
        which the sweep and the TCS call too."""
        from derived.levels import board_for
        return board_for(self._store_(), _symbol_of(), price_now, hi, lo)

    # ── the plan ──────────────────────────────────────────────────────────
    def prepare(self, *, orb, price_now, now_et, atr_pct=None, chain=None, df_1m=None,
                atm_iv=None) -> HuntPreparation:
        t = self.planner.tick(price_now)
        prep = HuntPreparation(t)
        hm = _hm(now_et)
        if hm is None:                                           # r220: a window that cannot be checked is not open
            t.dormant("entry_window", "the clock could not be read — no trade")
            return prep
        # r254 (OBS.1) - observed past the end: the plan keeps looking, nothing it fires executes.
        _obs = bool(hm is not None and hm >= tuple(CUTOFF_ET) and _observe.is_active(self.name))
        if hm is not None and hm >= tuple(CUTOFF_ET) and not _obs:
            t.dormant("entry_window", f"past {CUTOFF_ET[0]:02d}:{CUTOFF_ET[1]:02d} ET — observing only")
            return prep
        if _obs:
            t.note(f"LOG-ONLY - past the {CUTOFF_ET[0]:02d}:{CUTOFF_ET[1]:02d} ET entry end: "
                   "observed, recorded, never executed (OBS.1)")
        if hm is not None and hm < tuple(WINDOW_OPEN_ET):
            t.dormant("entry_window", f"before {WINDOW_OPEN_ET[0]:02d}:{WINDOW_OPEN_ET[1]:02d} ET — the range is forming")
            return prep
        t.check("entry_window", None, True)
        price_now = safe_float(price_now)
        if not price_now or price_now <= 0:
            prep.starved.append("price_now"); t.starved("price_now"); return prep
        t.check("price", price_now, True)
        _atr = safe_float(atr_pct)
        reachable = target_delta(atr_pct) is not None
        t.check("atr_pct", _atr, reachable)

        hi = safe_float(getattr(orb, "orb_high", None)) or 0.0
        lo = safe_float(getattr(orb, "orb_low", None)) or 0.0
        if hi <= 0 or lo <= 0 or hi <= lo:
            prep.starved.append("opening_range"); t.starved("opening_range"); return prep
        t.check("orb_range", round(hi - lo, 4), True)
        # r15 — THE LEVEL BOARD (PLAN_SPEC §38): held levels beyond the range,
        # ordered outward, plus the fork's rails computed at this read. Four empty
        # answers stay distinct; nothing here is silence-as-clearance.
        b = self._board(price_now, hi, lo)
        t.check("board_state", {"ok": 1.0, "no_store": -1.0, "no_range": 0.0}.get(b.get("state"), None),
                b.get("state") == "ok")
        if b.get("state") != "ok":
            prep.starved.append(f"level_board:{b.get('state')}"); t.starved("level_board"); return prep
        tines_up = [dict(x) for x in b["tines"] if x["price"] > hi]
        tines_dn = [dict(x) for x in b["tines"] if x["price"] < lo]
        # 🔴 r104 — THE RAILS NO LONGER OUTRANK A HELD EXTREME. These were one
        # merged list and `na = above[0]` took whatever sat nearest — so a rail
        # inside the nearest held extreme became THE level this plan hunts.
        # 🔑 Operator, 2026-09-22: *"It's just SEPARATE from held levels with
        # testing orders. It's SOFTER than held levels."* The hunt's whole
        # thesis is the pool of resting stops beyond a held extreme; a sloped
        # rail has no pool to take.
        # ⚠️ ORDERING UNCHANGED — still outward from the ORB edge, and the rails
        # are still filtered against `hi`/`lo` rather than spot, which is this
        # plan's own anchoring (r12). Only the rank between the two kinds moves,
        # and nothing is withdrawn: an absent held extreme still leaves the rail
        # selectable, which is r33's "OR level, not an AND".
        from derived.levels import rails_after_held as _raf
        above = _raf(b["above"], tines_up, key=lambda l: float(l["price"]))
        below = _raf(b["below"], tines_dn, key=lambda l: -float(l["price"]))
        t.check("board_above", b["count"]["above"], None)
        t.check("board_below", b["count"]["below"], None)
        t.check("fork_built", 1.0 if b["fork"] == "built" else 0.0, None)
        # ⚠️ r104 — the rail count is its OWN number. `board_above`/`board_below`
        # already name the HELD set (they read b["count"]), so a combined total
        # would have hidden the rails entirely.
        t.check("rails_in_play", len(tines_up) + len(tines_dn), None)
        from derived import anchors as _Ar
        _Ar.stamp(t, **_Ar.rail_context(price_now))
        na = above[0] if above else None
        nb = below[0] if below else None
        prep.above, prep.below = na, nb
        em = None
        try:
            from strategy.gex_pin_butterfly import expected_move
            em = expected_move(price_now, atm_iv)
        except Exception:                                       # noqa: BLE001
            em = None
        da = (float(na["price"]) - hi) if na else None
        db = (lo - float(nb["price"])) if nb else None
        t.check("nearest_above", float(na["price"]) if na else None, None)
        t.check("nearest_below", float(nb["price"]) if nb else None, None)
        t.check("above_em", round(da / em, 3) if (da is not None and em) else None, None)
        t.check("below_em", round(db / em, 3) if (db is not None and em) else None, None)
        try:                                                    # r229: the platform's number, recorded
            from analysis.volatility_measures import expected_move_platform
            t.check("em_platform", expected_move_platform(chain, price_now)[0], None)
        except Exception:                                       # noqa: BLE001
            t.check("em_platform", None, None)
        if na is None and nb is None:
            t.hold(f"range {lo:.2f}-{hi:.2f}: NO live level outside the range on either side — nothing to hunt")
            return prep
        # the bias: the nearer liquidity, measured from the range edge
        if da is not None and (db is None or da <= db):
            bias, target, tname, dist = "long", float(na["price"]), na["provenance"], da
        else:
            bias, target, tname, dist = "short", float(nb["price"]), nb["provenance"], db
        prep.bias, prep.target, prep.target_name = bias, target, tname
        prep.em_frac = round(dist / em, 3) if em else None
        t.check("bias", 1.0 if bias == "long" else -1.0, True)
        head = (f"range {lo:.2f}-{hi:.2f}; nearest above {_n(na['price'] if na else None)} "
                f"({na['provenance'] if na else '-'}, {_n(da)}), nearest below "
                f"{_n(nb['price'] if nb else None)} ({nb['provenance'] if nb else '-'}, {_n(db)}) "
                f"→ bias {bias.upper()}, target {tname} {target:.2f} ({_n(prep.em_frac)} EM)")

        # the closed bar: where is price relative to the range, and did a fake fail?
        if df_1m is None or len(df_1m) < 2:
            prep.starved.append("df_1m"); t.starved("df_1m"); return prep
        bar = df_1m.iloc[-2]; bar_ts = str(df_1m.index[-2])
        close = float(bar["close"])
        new_bar = bar_ts != self._last_bar_ts
        self._last_bar_ts = bar_ts
        state = "inside" if lo <= close <= hi else ("above" if close > hi else "below")
        t.check("break_state", {"inside": 0.0, "above": 1.0, "below": -1.0}[state], None)
        bias_side = "above" if bias == "long" else "below"
        far_side = "below" if bias == "long" else "above"
        far_key = ("short" if bias == "long" else "long", lo if bias == "long" else hi)
        fk = self._fake.setdefault(far_key, {"seen": "", "failed": False})
        if new_bar and state == far_side:
            fk["seen"] = fk["seen"] or bar_ts
            fk["failed"] = False
            # HUNT.9 - RECORD-ONLY: the far-side break RE-ASSERTED after this boundary's A2 was taken. The
            # next close back inside is the A2 a re-arm would fire; it is RECORDED below, never traded (the
            # operator, 2026-10-14 10:28 ET: "It should be permitted if it goes back into the range";
            # 2026-10-15 10:16 ET: "Concur on all", to "record-only"). FINISHED is never touched here.
            if (not _obs and getattr(config, "HUNT_REARM_MODE", "log") == "log"
                    and (bias, round(lo if bias == "long" else hi, 2)) in FINISHED):
                fk["rearm"] = bar_ts
        if new_bar and fk["seen"] and state == "inside" and not fk["failed"]:
            fk["failed"] = True
            fk["failed_ts"] = bar_ts
        t.check("fake_seen", 1.0 if fk["seen"] else 0.0, None)
        t.check("fake_failed", 1.0 if fk["failed"] else 0.0, None)

        entry = ""
        if state == bias_side:
            entry, boundary = "A1", (hi if bias == "long" else lo)
        elif fk["failed"] and fk.get("failed_ts") == bar_ts and state == "inside":
            entry, boundary = "A2", (lo if bias == "long" else hi)
        elif state == far_side:
            t.hold(f"{head}. Broke AWAY from the liquidity ({far_side}) — a fake-out candidate; "
                   f"not traded; waiting on: the fake to fail (a close back inside)")
            return prep
        t.check("entry", {"": 0.0, "A1": 1.0, "A2": 2.0}[entry], bool(entry))
        if not entry:
            t.hold(f"{head}. Inside the range — waiting on: A1 (a close out {bias_side}) or A2 "
                   f"(a far-side break that closes back inside)")
            return prep
        prep.entry, prep.direction, prep.boundary = entry, bias, boundary
        prep.side = "call" if bias == "long" else "put"
        t.direction = bias
        key = (bias, round(boundary, 2))
        # r297 (HUNT.11): the book decides, the set only remembers. A restart emptied FINISHED and re-fired
        # the same boundary; now a Hunt row for this break today finishes it, and an unreadable book HOLDS.
        if key not in FINISHED and not _obs:
            _fin = break_finished_in_book(bias, boundary)
            if _fin == "unreadable":
                t.check("break_finished", 1.0, False)
                t.hold(f"{head}. {entry} {bias} at {_n(boundary)} — trades.db is UNREADABLE, so this break "
                       f"cannot be proven untraded today; failing closed (one per break)")
                return prep
            if _fin:
                FINISHED.add(key)
        t.check("break_finished", 1.0 if key in FINISHED else 0.0, key not in FINISHED)
        if key in FINISHED:
            if entry == "A2" and fk.get("rearm"):
                _rs = fk.pop("rearm")
                _record_hunt_rearm({"symbol": _symbol_of(), "direction": bias, "entry": entry,
                                    "boundary": round(boundary, 2), "reasserted_bar": _rs, "signal_bar": bar_ts,
                                    "price_now": price_now, "target": target,
                                    "runway": round(abs(target - price_now), 4)})
                t.hold(f"{head}. {entry} re-armed by a return to the range — RECORDED ONLY (HUNT.9); "
                       f"this break already had its hunt — one per break")
                return prep
            t.hold(f"{head}. {entry} armed but this break already had its hunt — one per break")
            return prep
        # 🔴 r316 (HUNT.13) — A LOSING BREAKOUT ON THIS SIDE CLOSES IT TO THE HUNT FOR THE DAY. The operator,
        # 2026-10-24 13:56 ET: "if a breakout on one side fails, don't allow a hunt to fire on that side for
        # the rest of the day". trades.db decides; an unreadable book HOLDS.
        _hab = getattr(config, "HUNT_AFTER_BRK_MODE", "trade")
        if _hab != "off":
            _bf = breakout_failed_today(bias)
            t.check("breakout_failed", None if _bf == "unreadable" else (1.0 if _bf else 0.0),
                    _bf is None or _hab == "log")
            if _bf == "unreadable":
                if _hab == "trade":
                    t.hold(f"{head}. {entry} {bias} at {_n(boundary)} — trades.db is UNREADABLE, so a losing "
                           f"{bias} Breakout today cannot be ruled out; holding (HUNT.13)")
                    return prep
            elif _bf:
                if not _obs:
                    _record_hunt_after_breakout({"symbol": _symbol_of(), "direction": bias, "entry": entry,
                                                 "boundary": round(boundary, 2), "signal_bar": bar_ts,
                                                 "price_now": price_now, "target": target,
                                                 "breakout_trade": _bf[0], "breakout_pnl": _bf[1],
                                                 "held": _hab == "trade"})
                if _hab == "trade":
                    t.hold(f"{head}. {entry} {bias} at {_n(boundary)} — the {bias} Breakout {_bf[0]} lost "
                           f"${_bf[1]:,.2f} today; no {bias} Hunt for the rest of the day (HUNT.13)")
                    return prep
        t.anchor(trigger=boundary, invalidation=boundary)
        runway = abs(target - price_now)
        prep.runway = runway
        t.check("runway", round(runway, 4), runway > 0)
        if runway <= 0:
            prep.structural.append(("runway", f"price {price_now:.2f} is already at/through the target {target:.2f}"))
        if not reachable:
            prep.unmet.append(("atr_pct", f"ATR {_n(_atr, '.3f')}% below the {ATR_FLOOR_PCT}% reachability floor"))
        if chain is None:
            prep.starved.append("chain")
        elif not prep.structural and not prep.unmet:
            contracts = chain.calls if prep.side == "call" else chain.puts
            why_none: list = []
            c, lev, n, spread_rej = gamma_leverage_pick(contracts, bias, price_now, runway, floor_pct=MAX_LOSS_PCT,
                                                        note=why_none)
            t.check("considered", n, n > 0)
            t.check("spread_rejected", spread_rej, None)
            if c is None and why_none:                     # r289 / RUN.9 (mirror of r492)
                prep.structural.append(("contract", f"{prep.side}: {why_none[0]}"))
            elif c is None:
                prep.structural.append(("contract", f"no {prep.side} whose {MAX_LOSS_PCT:.0%} floor clears its own "
                                                    f"spread over a {runway:.2f} runway ({spread_rej} rejected)"))
            else:
                prem = float(getattr(c, "ask", 0) or getattr(c, "mark", 0) or 0)
                prep.contract, prep.premium, prep.leverage = c, prem, lev
                prep.floor_premium = round(prem * (1 - MAX_LOSS_PCT), 4)
                t.check("contract", float(c.strike), True)
                t.check("leverage", lev, lev > 0)
                t.check("debit", prem, True)
                t.check("stop_premium", prep.floor_premium, None)
                t.debit = prem
        if prep.starved:
            t.starved(*prep.starved); return prep
        if prep.structural:
            g, w = prep.structural[0]; t.refuse(g, f"{head}. {entry}: {w}"); return prep
        if prep.unmet:
            g, w = prep.unmet[0]; t.refuse(g, f"{head}. {entry}: {w}"); return prep
        prep.ready = True
        t.note(f"{head}. {entry} FIRES — {prep.trade_line()}")
        return prep

    # ── the strategy: bars + fire ─────────────────────────────────────────
    def generate_signal(self, *, orb, price_now, now_et, atr_pct=None, chain=None, df_1m=None,
                        atm_iv=None, **_ignored):
        prep = self.prepare(orb=orb, price_now=price_now, now_et=now_et, atr_pct=atr_pct,
                            chain=chain, df_1m=df_1m, atm_iv=atm_iv)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        c = prep.contract
        sig = Signal(
            strategy_name=self.name,
            setup_type=f"liquidity_hunt_{prep.entry}",
            direction=prep.direction,
            option_side=prep.side,
            underlying_entry=float(price_now),
            underlying_stop=float(prep.boundary),       # thesis-dead: a close back through it
            underlying_target=float(prep.target),
            orb_range_high=float(getattr(orb, "orb_high", 0.0) or 0.0),
            orb_range_low=float(getattr(orb, "orb_low", 0.0) or 0.0),
            stop_loss_pct=MAX_LOSS_PCT,                  # recorded; the exit engine HOLDS
            strike=c.strike, expiry=getattr(c, "expiry", ""),
            entry_premium=c.mark, contract=c,
        )
        sig.hunt_entry = prep.entry
        sig.hunt_target_name = prep.target_name
        sig.hunt_em_frac = prep.em_frac
        sig.run_at_entry = prep.runway
        sig.gamma_leverage = prep.leverage
        sig.is_liquidity_hunt = True
        # 🔴 ENT.1 (r61) — THIS STRATEGY'S `underlying_stop` IS NOT A STOP.
        # It is `prep.boundary`, the ORB edge being faded, and the hunt enters
        # only AFTER price has taken that edge out — so entry on the far side
        # of it is the setup's DEFINING state, not a defect. Measured on the
        # banked book: 3 of 8 hunt rows sit that way and all three are correct.
        # The entry-underwater guard therefore skips this strategy, and it is
        # declared HERE, beside the line that writes the column, rather than as
        # a name in a list somewhere else that later rots (r55's finding).
        sig.underlying_stop_is_thesis = True
        sig.disarms_retest = False                       # the ORB is untouched
        relaxed.tag(sig)
        if _observe.is_active(self.name):
            # r254 (OBS.1) - a LOG-ONLY fire never touches the real one-per-break set.
            logger.debug("[hunt] LOG-ONLY %s %s — %s", prep.entry, prep.direction, prep.trade_line())
            return prep.tick.take(sig)
        FINISHED.add((prep.direction, round(prep.boundary, 2)))
        logger.info("[hunt] FIRE %s %s — %s", prep.entry, prep.direction, prep.trade_line())
        return prep.tick.take(sig)
