"""
strategy/management.py  v5.1
v5.1  2026-10-29  OTV5 r54 (BRK.16) — THE NEARER-STOP DEFERRAL CANNOT DEFER TO AN UNARMED BREAKOUT TRAIL. A Breakout's trail
      now arms only once the underlying reaches the range edge +/- 0.5W (the operator, 2026-10-29: "I want the trailing
      stop activation to occur at 1/2 W"; exit_engine v5.8). r98's structure-stop deferral asks the exit engine's
      trail_armed(record) first: an unarmed trail never governs, so the 5m structure stop exits. Every other strategy
      and every other rule here is unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v2.11 2026-10-18  OTV4TEST r288 (BRK.13) — BREAKOUT'S DELTA FLOOR. After the spec stops, par delta and the target/nickel
      rules, before no-progress and exhaustion: once BRK_DFLOOR_AFTER_S (600 s) have passed since entry, a readable
      |delta| <= BRK_DELTA_FLOOR (0.30) closes the Breakout (OT_BRK_DFLOOR=trade, the default) or is recorded only (log).
      None / 0.0 is UNREAD: hold. Every firing writes data/counterfactual/breakout_delta_floor.jsonl once per trade. The
      operator, 2026-10-17 19:12 ET: "A is fine" (trade it with a counterfactual). MEASURED /var/tmp/sat_1017/bdelta,
      added to today's stack: unseen QQQ 08-24..10-09 +1,363, 13 stocks +2,406 (7/13), top-3 days kept 100%.
v2.10 2026-10-10  OTV4TEST r265 (BRK.8) — BREAKOUT'S NO-PROGRESS EXIT. `breakout_no_progress()` walks the CLOSED 1m bars
      after the entry bar: once BRK_NOPROG_STALL_BARS (2) consecutive bars make no new favourable extreme, it decides
      ONCE - cut if the best progress since entry is under BRK_NOPROG_MIN_R (0.5 R, R = |underlying_entry -
      underlying_stop|). Stateless (recomputed from the frame each tick, so a restart decides the same). decide()
      applies it after the spec stops and par delta, before exhaustion: OT_BRK_NOPROG=trade CLOSES ("no_progress",
      priced by the exit engine's own rule - the mark ladder); log only RECORDS. Every decision that cuts is written once
      per trade to data/counterfactual/breakout_no_progress.jsonl (OT_COUNTERFACTUAL_DIR) with the mark - what the old
      stack held is replayed from the quote stream on Saturday. The operator, 2026-10-10 13:37 ET: "Yes, to all. Study,
      fit & apply"; "as long as this counter factual evidence is available for next Saturday." EVIDENCE: PREREG_MONDAY.md
      N3 - 13 unseen stocks +28,595 (losing days +35,786, 9/13 symbols); QQQ as-run +3,220; SPX-TEST 1 moved -910.
v2.9  2026-10-03  OTV4TEST r209 (EXIT.4) — THE EXIT'S PRICING POLICY IS DECLARED, NOT INFERRED; THE STRUCTURE STOP IS NAMED A
      TOUCH. (1) EXIT_PRICING maps each condition this plan closes on to how the close is priced - `floor` (at
      the mark) or `walk` (the exit ladder) - and Intent carries it; exit_engine reads it instead of matching
      substrings of the reason. The values are EXACTLY what the substrings produced (the operator, 2026-10-03:
      "why do you say mark? Clearly ladder is more advantageous" - credit and butterfly stops keep the ladder).
      (2) The structure stop reads the FORMING 1m bar and always has; its reason and its narration now say
      "touch" instead of "1m close". The operator, 2026-10-03: keep "whichever way was better from the numbers"
      (the touch exited better, n=12). No behaviour change in this file.
v2.8  2026-09-22  OTV4TEST r98 — THE NEARER OF THE TWO STOPS GOVERNS, EACH TICK.
      Operator: "use the nearest one... each tick one of the two will be
      closer. Default to the closer one", and what it is FOR: "kill losers
      quickly, and preserve winners out of the gate, even if it's modest".
      That intent IS max(structure, trail) - underwater the trail is unarmed
      or low so the STRUCTURE kills it fast; in profit the trail climbs above
      and PRESERVES the gain. The two live in DIFFERENT UNITS - a 1m close
      through underlying_stop versus a PREMIUM level - so `nearer_stop_defers`
      first asks whether r91's delta-linear bridge was actually built for the
      record, by checking stop_premium against entry - dist x |delta|.
      MEASURED: good to 0.003-0.013 on the Breakouts, 0.134 out on VOLT whose
      underlying_stop is a THESIS LINE at zero distance. Derived from columns,
      because underlying_stop_is_thesis is a SIGNAL field and not a trades
      column - a guard keyed on it would silently never fire (section 22).
v2.7  2026-09-21  OTV4TEST r82 — PAR DELTA REPLACES THE TARGET FOR THE
      BREAKOUT. Operator: *"the breakout needs the delta stop not the 100%
      stop."* Its target was never written for it — this file documents that
      rule as "a debit exit for the RUNAWAY only" and implemented it as
      `strategy not in BUTTERFLIES`, so every debit strategy inherited a
      guillotine. Measured: 8 target exits, all at delta 0.619-0.650.
      SCOPED, NOT DELETED — the runaway keeps the target (B3 pins it).
v2.6  2026-09-19  OTV4TEST r55 — THE DECLARED EXIT DESCRIBED AN EXIT THAT
      DOES NOT EXIST. `structure_stop` read "a 1m close back inside the opening
      range — the break failed", but BOTH evaluation paths read
      `underlying_stop` (this file's own outs loop, and exit_engine's
      `orb_structure_stop`), which for a Breakout IS the impulsive candle's
      extreme. 🔑 Operator: "If it comes back into the range but doesn't trigger
      a stop, make it HOLD." The code already did; the file did not say so — and
      this string is what the board NARRATES and what the next editor would have
      implemented against. Corrected to the ORB's wording verbatim.
v2.5  2026-09-18  OTV4TEST r51 (BRK.1) — THE BREAKOUT'S EXHAUSTION EXIT, and
      the first reader `_midline_atr` / `_momentum_divergence` have ever had.
      Both survived, fully written and documented, from an `_evaluate_continuation`
      path deleted with the strategy it served: MEASURED, ZERO CALL SITES.
      Operator: *"the liquidity hunt has an identified target and the breakout
      has to identify an EXHAUSTION SIGNAL to get out before it gives back."*
      Two tiers, order preserved from the original doctrine: EXTENSION tightens
      (a strong trend can stay extended), DIVERGENCE exits (continuing on fumes).
      ⚠️ MODE 2, NOT MODE 3 — the stricter both-signals form the operator asked
      for is deliberately NOT taken here: a first wiring and a behaviour change
      in one step cannot be told apart when the result arrives.
v2.4  2026-09-14  OTV4TEST r26 — THE ATP BUTTERFLY IS MANAGED EXACTLY AS THE PIN BUTTERFLY.
      Covered, with the same two declared exits (the 40% floor and the 15:45
      flatten, no target). Every "is this the butterfly" test reads one tuple,
      `BUTTERFLIES`, so a third butterfly cannot be half-managed by a name
      comparison someone forgot.
v2.3  2026-09-13  OTV4TEST r24 — THE DECLARATIONS MATCH THE ROWS AGAIN. The sweep's
      premium stop is the credit plus 15% OF THE RISK (PLAN_SPEC §31) — this
      line read "credit x (1 + max_loss_pct)", the inverted rule the stamp was
      still writing — and the butterfly's floor is 40% (operator's ruling).
      The plan still acts on each record's own `stop_premium`, so a position
      opened before r24 keeps the floor it was opened with.
v2.2  2026-08-27  r169: the butterfly declares exactly two exits — the 25%
      floor and the 15:45 flatten; the target no longer fires for it.
v2.1  2026-08-27  r168: the runaway declares NO structure stop — its floor is
      the 20% premium loss on the record; the breach check cannot fire for it
      because the signal carries no underlying_stop.
v2.0  2026-08-27  r167 — THE PLAN DECIDES; THE EXIT ENGINE CALCULATES AND
      EXECUTES. Operator, 2026-08-27: *"I'm ready for the managed exits
      build, if on the next tick is this, cut it loose, or roll, or whatever
      the management is."* With the rulings: *"Everything tied to the orb
      stays. Even the trailing stop armed at 50% and the tightening after
      100% on the peak. The other variables for the other strategies were
      all good except for the BOS"* and *"We still have the 15% floor & the
      'breach' stops."*
      NEW `decide(record, premium, df_1m, open_records)` -> Intent for the
      records this plan COVERS: RunawayContinuation, GEXPinButterfly, and a
      SweepCreditSpread / TrendCreditSpread vertical while it stands alone
      (a formed condor, a tent, ORB and ADOPTED are NOT covered — the ladder
      and ORB's own path decide those, untouched). Order, and it matters:
        1. THE DECLARED SPEC CONDITIONS, read straight off the record — the
           15% floor / hard stop (`stop_premium`), the BREACH stops (a 1m
           close through `underlying_stop`: the ORB boundary, the bound,
           the pool), the target, the nickel. These are never outranked.
        2. THE CALCULATORS — the exit engine's evaluate() for the 50% trail,
           the tightening after 100% on the peak, theta bleed, velocity
           stall. Its ExitDecision is adopted as the plan's own. BOS is gone
           (exit_engine v4.7).
      Every intent is a ROW before it is an act (CLOSE / TRAIL / HOLD with
      the condition that fired and the numbers). position_manager v4.6 asks
      this plan first and executes its intent through the same
      _execute_exit; the engine's evaluate() runs directly only for records
      the plan does not cover.
v1.0  2026-08-27  r166 — THE MANAGEMENT PLAN: ONE WATCHER PER OPEN POSITION.
      Operator, 2026-08-27, on where stops live: *"The plan seems like the
      right place for them … I like the thought of it watching & thinking if
      it does 'this' or 'this' we're out!"* And on the r66 vectors: *"if there
      is a way to incorporate those vectors back into the management (and
      stop functions) I think that is the logical next step."*

THE SAME SPLIT AS ENTRIES, ONE POSITION AT A TIME.
  · The STRATEGY declares its exit conditions as data (`EXIT_CONDITIONS`
    below, keyed by strategy name) — what "we're out" means for that spec.
  · The MANAGEMENT PLAN reads, every tick for every open record, the current
    value of each of those conditions off what the exit engine already
    tracks (premium now, stop premium, trail stop, target, underlying stop,
    MFE/MAE, ticks held) and writes ONE row: HOLD "if premium <= 0.66 -> out
    (hard stop); if touch < 101.00 -> out (structure); trail 1.12 armed;
    MFE +41%". It also records the r66 DERIVED VECTOR for that strategy
    (aggression at the level, tape, VRP, charm …) into strategy_note with
    phase "manage", so a stop can later be FITTED against what the tape was
    doing while the position lived, not just at entry.
  · The EXIT ENGINE executes, exactly as today. This file changes no exit.

⚠️ WRITTEN AFTER manage_open_position, deliberately: the exit engine has just
priced the record and updated trail/MFE. The row says what would take the
position out on the NEXT tick — anticipatory, like the entry plans.

⚠️ NEVER RAISES, NEVER GATES. A bookkeeping failure here cannot reach an exit.

⚠️ CONDITIONS ARE READ, NOT RE-DERIVED. Every threshold below is the record's
own field (set at entry from the strategy's spec) or the exit engine's own
state. When this file and the exit engine disagree, the exit engine is
right and this file has a bug — pinned by tests/check_management_plan.py.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from strategy.plan import Plan, _n

logger = logging.getLogger(__name__)

# ── WA §36 GATE CATEGORIES ──────────────────────────────────────────────
# This file OWNS NO THRESHOLD. Every number it writes is the record's own
# field (set at entry from the strategy's spec) or the exit engine's state;
# tests/check_management_plan.py M9 refuses a literal compared to a premium.
GATES = {}

# ── THE DECLARED EXIT CONDITIONS — the strategy's spec, as data ─────────────
# name -> what "true" means. Read from the record; nothing computed here.
EXIT_CONDITIONS: Dict[str, Dict[str, str]] = {
    "RunawayContinuation": {
        # r168 — NO price stop. Operator: a 20% premium loss, decay or adverse
        # move; "the runaway needs room to breathe. A few pullbacks in an
        # uptrend are ok." The ORB structure stop is ORB's alone.
        "hard_stop":      "premium <= stop_premium (the 20% floor set at entry)",
        "trail":          "premium <= trail_stop, once the trail has armed at +50%",
        "target":         "premium >= target_premium, then the tightening off the peak",
    },
    "ORBStrategy": {
        "hard_stop":      "premium <= stop_premium",
        "structure_stop": "a touch through underlying_stop (the impulsive-candle extreme; the forming 1m bar)",
        "trail":          "premium <= trail_stop, once the trail has armed",
        "target":         "premium >= target_premium",
    },
    "SweepCreditSpread": {
        "premium_stop":   "spread value >= stop_premium (credit + 15% of the risk, width - credit)",
        "acceptance":     "a touch through the swept pool (the level failed; the forming 1m bar)",
        "nickel":         "spread value <= the nickel — let it go",
    },
    "TrendCreditSpread": {
        "breach":         "a touch through the ORB bound (underlying_stop; the forming 1m bar) — no premium stop",
        "nickel":         "spread value <= the nickel",
    },
    "IronCondorStrategy": {
        "ladder":         "CondorManagement decides: ROLL / TENT / CLOSE (TRADES.md)",
        "premium_stop":   "spread value >= credit x (1 + 25%) while a lone vertical",
    },
    "GEXPinButterfly": {
        # r169 — operator: "1545 flatten or 25% loss. Whichever comes first."
        # No target, no max hold: a pin pays into the close.
        "stop":           "fly value <= entry x (1 - 40%)",          # r24: operator, was 25%
        "flatten":        "the 15:45 hard close",
    },
    # r51 (BRK.1) — THE BREAKOUT HAS NO TARGET, SO EXHAUSTION IS ITS EXIT.
    # Operator, 2026-09-18, distinguishing the three ORB-born trades: *"the
    # liquidity hunt has an identified target and the breakout has to identify
    # an EXHAUSTION SIGNAL to get out before it gives back."* The runaway exits
    # on THESIS (the 50 is lost); the hunt exits AT ITS TARGET; this one has
    # neither, so the exit is the whole trade.
    # ⚠️ AND r44's TRAIL STUDY IS WHY THE TRAIL CANNOT BE ITS PLAN: across 210
    # trail-exited fleet trades the trail returned a MEDIAN 42.9% of MFE. A
    # strategy with no target leaning on that is the worst pairing of the three.
    # The trail is a FLOOR under a Breakout, never its exit.
    # 🔑 TWO TIERS, AND THE ORDER MATTERS — this is the doctrine written for the
    # deleted continuation path, reused rather than reinvented: EXTENSION
    # tightens because *"a strong trend can stay extended"*, and only
    # DIVERGENCE — a new favourable extreme on WEAKER momentum, *"the move
    # continuing on fumes"* — actually exits.
    "Breakout": {
        "hard_stop":      "premium <= stop_premium",
        # 🔴 THIS SAID "a 1m close back inside the opening range — the break
        # failed" UNTIL r55, AND THE CODE NEVER DID THAT. `structure_stop` is
        # evaluated against `underlying_stop` (management.py's own outs loop,
        # and exit_engine's `orb_structure_stop` reads
        # `record["underlying_stop"]`), which for a Breakout IS the impulsive
        # candle's extreme. So the declared condition described an exit that
        # does not exist — and this string is what the board NARRATES and what
        # the next editor would have implemented against.
        # 🔑 OPERATOR, 2026-09-19: *"If it comes back into the range but doesn't
        # trigger a stop, make it HOLD."* That is what the code already does;
        # now it is what the file SAYS. The ORB's structure stop, verbatim —
        # this trade follows the ORB structurally, without the retest.
        "structure_stop": ("a touch through underlying_stop (the forming 1m bar; the impulsive-candle "
                           "extreme that registered the break) — a return INTO the "
                           "range with the stop intact is a HOLD, never an exit"),
        "extension":      ("price stretched from the BB midline -> TIGHTEN the trail, "
                           "never exit: a strong trend can stay extended"),
        "exhaustion":     ("a NEW run-favourable extreme on WEAKER 5m momentum -> out. "
                           "The move is continuing on fumes"),
    },
}
# OTV4TEST r26 — the ATP butterfly's exits are the pin butterfly's, by construction. — the ATP butterfly's exits are the pin butterfly's, by construction.
BUTTERFLIES = ("GEXPinButterfly", "ATPButterfly")
# r82 — strategies whose winner is ended by PAR DELTA rather than a premium
# target. VOLT is NOT here: it owns `_evaluate_volt` and carries its own rung.
DELTA_PAR_STRATEGIES = ("Breakout",)
from config import DELTA_PAR                                      # r82
import config as _cfg                                              # r265: BRK_NOPROG_* read at call time
import json as _json
import os as _os
import time as _time
from datetime import datetime as _dt


def _entry_epoch(record) -> Optional[float]:
    raw = record.get("entry_time")
    if not raw:
        return None
    try:
        return _dt.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def breakout_no_progress(record, df_1m, now_epoch: Optional[float] = None) -> Optional[dict]:
    """r265 (BRK.8) - the no-progress decision for one Breakout, or None while undecided /
    not applicable. Reads ONLY the record (entry_time, underlying_entry, underlying_stop,
    direction) and the CLOSED 1m bars after the entry bar (a bar is closed when its open +
    60 s <= now; the forming bar never counts). Returns {"cut": bool, "best_r": float,
    "bar_close": epoch, "bars": n} at the FIRST point BRK_NOPROG_STALL_BARS consecutive bars
    fail to make a new favourable extreme beyond the best since entry (starting from
    underlying_entry). Deterministic: the same frame gives the same answer every tick."""
    try:
        ue = float(record.get("underlying_entry") or 0.0)
        us = float(record.get("underlying_stop") or 0.0)
        R = abs(ue - us)
        t0 = _entry_epoch(record)
        if R <= 0 or ue <= 0 or t0 is None or df_1m is None or not len(df_1m):
            return None
        long_ = str(record.get("direction", "")) == "long" or str(record.get("option_side", "")) == "call"
        sg = 1.0 if long_ else -1.0
        now = _time.time() if now_epoch is None else float(now_epoch)
        e_open = (t0 // 60) * 60
        ext, cnt, best, n = ue, 0, 0.0, 0
        for ts, hi, lo in zip(df_1m.index, df_1m["high"], df_1m["low"]):
            b0 = ts.timestamp() if hasattr(ts, "timestamp") else float(ts)
            if b0 <= e_open or b0 + 60 > now:
                continue
            n += 1
            x = float(hi) if long_ else float(lo)
            best = max(best, (x - ue) * sg / R)
            if (x > ext) if long_ else (x < ext):
                ext, cnt = x, 0
            else:
                cnt += 1
            if cnt >= _cfg.BRK_NOPROG_STALL_BARS:
                return {"cut": best < _cfg.BRK_NOPROG_MIN_R, "best_r": best, "bar_close": b0 + 60, "bars": n}
        return None
    except Exception as exc:                                     # noqa: BLE001
        logger.debug("[manage] no-progress read failed: %s", exc)
        return None


_DFLOOR_SAID: set = set()


def breakout_delta_floor(record, now_epoch: Optional[float] = None) -> Optional[float]:
    """r288 (BRK.13) - |delta| when the floor is crossed (readable, <= BRK_DELTA_FLOOR, at least
    BRK_DFLOOR_AFTER_S after entry), else None. None / 0.0 / unparseable delta and an unreadable
    entry_time are UNREAD: None (hold). Never raises."""
    try:
        t0 = _entry_epoch(record)
        if t0 is None:
            return None
        now = _time.time() if now_epoch is None else float(now_epoch)
        if now - t0 < float(_cfg.BRK_DFLOOR_AFTER_S):
            return None
        raw = record.get("current_delta")
        d = abs(float(raw)) if raw not in (None, "") else 0.0
        return d if 0.0 < d <= float(_cfg.BRK_DELTA_FLOOR) else None
    except Exception:                                            # noqa: BLE001
        return None


def _record_delta_floor(record, delta: float, mode: str, prem, price) -> None:
    """Once per trade per process: data/counterfactual/breakout_delta_floor.jsonl - when, at what
    delta and mark the floor fired, so Saturday replays the old exits' road from the quote stream."""
    tid = str(record.get("trade_id", "") or "")
    if not tid or tid in _DFLOOR_SAID:
        return
    _DFLOOR_SAID.add(tid)
    acted = mode == "trade"
    logger.info("[manage] Breakout %s DELTA FLOOR %s: |delta| %.3f <= %.2f; mark %s (OT_BRK_DFLOOR=%s)",
                tid[:8], "CLOSE" if acted else "would close (LOG ONLY)", delta, _cfg.BRK_DELTA_FLOOR,
                _n(prem), mode)
    try:
        d = _os.environ.get("OT_COUNTERFACTUAL_DIR") or _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "counterfactual")
        _os.makedirs(d, exist_ok=True)
        row = {"ts_epoch": _time.time(), "trade_id": tid, "symbol": record.get("symbol"),
               "rule": "breakout_delta_floor", "mode": mode, "acted": acted, "delta": round(delta, 4),
               "floor": _cfg.BRK_DELTA_FLOOR, "mark": prem, "bid": record.get("_exit_bid"), "underlying": price,
               "entry_premium": record.get("entry_premium"), "option_symbol": record.get("option_symbol"),
               "contracts": record.get("contracts")}
        with open(_os.path.join(d, "breakout_delta_floor.jsonl"), "a") as fh:
            fh.write(_json.dumps(row) + "\n")
    except Exception as exc:                                     # noqa: BLE001
        logger.warning("[manage] delta-floor counterfactual row NOT written for %s: %s", tid[:8], exc)


_NOPROG_SAID: set = set()


def _record_no_progress(record, verdict: dict, mode: str, prem, price) -> None:
    """Once per trade per process: the counterfactual row (WA: the old rule's road is
    replayed Saturday from the quote stream; this row says WHEN and AT WHAT the cut was)."""
    tid = str(record.get("trade_id", "") or "")
    if not tid or tid in _NOPROG_SAID:
        return
    _NOPROG_SAID.add(tid)
    acted = mode == "trade"
    logger.info("[manage] Breakout %s NO-PROGRESS %s: %d closed bars, best %.2f R < %.2f R; mark %s (%s)",
                tid[:8], "CUT" if acted else "would cut (LOG ONLY)", verdict["bars"], verdict["best_r"],
                _cfg.BRK_NOPROG_MIN_R, _n(prem), "OT_BRK_NOPROG=" + mode)
    try:
        d = _os.environ.get("OT_COUNTERFACTUAL_DIR") or _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "counterfactual")
        _os.makedirs(d, exist_ok=True)
        row = {"ts_epoch": _time.time(), "trade_id": tid, "symbol": record.get("symbol"),
               "rule": "breakout_no_progress", "mode": mode, "acted": acted,
               "decided_at_bar_close": verdict["bar_close"], "bars": verdict["bars"],
               "best_r": round(verdict["best_r"], 4), "min_r": _cfg.BRK_NOPROG_MIN_R,
               "mark": prem, "underlying": price, "entry_premium": record.get("entry_premium"),
               "option_symbol": record.get("option_symbol"), "contracts": record.get("contracts")}
        with open(_os.path.join(d, "breakout_no_progress.jsonl"), "a") as fh:
            fh.write(_json.dumps(row) + "\n")
    except Exception as exc:                                     # noqa: BLE001
        logger.warning("[manage] no-progress counterfactual row NOT written for %s: %s", tid[:8], exc)
EXIT_CONDITIONS["ATPButterfly"] = dict(EXIT_CONDITIONS["GEXPinButterfly"])

MGMT_CHECKS = ("premium", "entry_premium", "pnl_pct", "stop_premium", "trail_stop",
               "target_premium", "underlying_stop", "dist_to_stop", "mfe_pct",
               "mae_pct", "ticks_held", "fired", "extension_atr")

COVERED = ("RunawayContinuation", "GEXPinButterfly", "SweepCreditSpread",
           "TrendCreditSpread", "ATPButterfly", "Breakout")
NICKEL = 0.05



def nearer_stop_defers(record, prem, stop_p, entry) -> bool:
    """True when the TRAIL is the nearer stop, so the structure must stand aside.

    🔑 EXTRACTED SO THE CHECK DRIVES THE REAL DECISION. §21: a test that reads
    source text proves nothing about runtime, and a checker that reimplements
    the predicate is a closed loop that supplies its own answer (§0.4) — the
    shape that let a dead VWAP reader survive two days.

    🔑 THE RULE IS `max(structure, trail)`, and the operator's intent is what
    that produces: *"kill losers quickly, and preserve winners out of the gate,
    even if it's modest."* Underwater, the trail is unarmed or low and the
    STRUCTURE kills it fast; in profit, the trail climbs above and PRESERVES
    the gain.

    🔴 WHO IT REACHES IS AN EXPERIMENT CONSTRAINT, NOT A SIZING ONE, AND THE
    OPERATOR CORRECTED ME ON EXACTLY THIS. I first proposed scoping it by
    `sizes_on_structure()` — a SIZING set — and he ruled: *"You're painting it
    as a sizing rule... The breakout and the ORB should have comparable sizing
    AND EXIT MECHANISMS. The purpose of the breakout was to test whether
    chasing was better than waiting for a retest, all other things being the
    same. The VOLT does not necessarily share that same lineage."*
    So ORB and Breakout must move TOGETHER or the chase-versus-retest
    comparison measures the exit rule instead of the entry. MEASURED on today's
    book, the bridge test sorts precisely along that line without naming anyone:
    ORB VALID (0.800 vs 0.805) · Breakout VALID (1.094 vs 1.089) · Hunt, VOLT
    and Runaway all invalid.

    ⚠️ THE TWO STOPS ARE IN DIFFERENT UNITS — a touch through
    `underlying_stop` versus a PREMIUM level — and `stop_premium` bridges them
    only as a DELTA-LINEAR ESTIMATE. So this first asks whether that bridge was
    actually built for THIS record, by checking that `stop_premium` agrees with
    `entry - distance x |delta|`. Measured 2026-09-22: agreement within
    0.003-0.013 on the Breakouts, and 0.239 out on VOLT, whose
    `underlying_stop` is a thesis line at zero distance.
    ⚠️ DERIVED, NEVER READ: `underlying_stop_is_thesis` is a SIGNAL field and
    NOT a `trades` column, so a rehydrated record returns None, None reads as
    False, and a guard keyed on it would silently never fire (§22).
    """
    try:
        tr = float(record.get("trail_stop", 0.0) or 0.0)
        sp = float(stop_p or 0.0)
        e = float(entry or 0.0)
        dist = abs((_f(record.get("underlying_entry")) or 0.0)
                   - (_f(record.get("underlying_stop")) or 0.0))
        dl = abs(_f(record.get("entry_delta")) or 0.0)
        if not (dist > 0 and dl > 0 and e > 0 and sp > 0):
            return False                      # no usable bridge -> structure governs
        if abs(sp - (e - dist * dl)) > max(0.02, e * 0.05):
            return False                      # the bridge was not built for this record
        return tr > sp and prem is not None and prem > tr
    except Exception:                         # noqa: BLE001
        return False                          # fail to the structure stop, never past it


# r209 (EXIT.4) — HOW EACH CLOSE THIS PLAN DECIDES IS PRICED. `floor` = at the mark, now
# (a stop the thesis no longer survives); `walk` = the exit ladder. These are the values
# exit_engine's substring match produced before r209, written down: a long option's
# hard stop and a structure stop floor; a CREDIT premium stop and a BUTTERFLY stop walk
# (operator, 2026-10-03: "Clearly ladder is more advantageous"), as do the profit exits.
EXIT_PRICING = {
    "hard_stop":      "floor",
    "structure_stop": "floor",
    "premium_stop":   "walk",
    "stop":           "walk",      # the butterflies' stop
    "breach":         "walk",      # TCS: "breach: ..." never matched `tcs_breach`
    "acceptance":     "walk",
    "delta_par":      "walk",
    "target":         "walk",
    "nickel":         "walk",
}


class Intent:
    """What the plan decided for the NEXT tick. Executed by position_manager."""
    __slots__ = ("action", "reason", "condition", "trail", "pnl_pct", "pricing")

    def __init__(self, action: str, reason: str = "", condition: str = "",
                 trail: Optional[float] = None, pnl_pct: float = 0.0):
        self.action = action            # HOLD / CLOSE / TRAIL
        self.reason = reason
        self.condition = condition
        self.trail = trail
        self.pnl_pct = pnl_pct
        # r209 — how THIS close is priced, declared by condition. None = a condition
        # this table does not name (the engine's own exits): exit_engine decides.
        self.pricing = EXIT_PRICING.get(condition) if action == "CLOSE" else None

    def to_exit_decision(self):
        from execution.exit_engine import ExitDecision
        d = ExitDecision()
        d.should_exit = self.action == "CLOSE"
        d.exit_reason = self.reason if d.should_exit else ""
        d.new_trail_stop = self.trail
        d.current_pnl_pct = self.pnl_pct
        return d


def covers(record, open_records=None) -> bool:
    """Which records THIS plan decides for. ORB, ADOPTED, tents and formed
    condors are decided elsewhere and are only narrated here."""
    strategy = str(record.get("strategy", "") or "")
    if strategy not in COVERED:
        return False
    if record.get("is_tent") or record.get("is_broken_wing"):
        return False
    if record.get("is_condor_leg") or record.get("is_credit_vertical"):
        legs = [r for r in (open_records or []) if r.get("is_condor_leg")
                and not r.get("is_tent")]
        if len(legs) >= 2:
            return False                # formed: the ladder decides
    return True


def _f(v) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


class ManagementPlan:
    """One `Plan` per strategy, rows written under "<Strategy>/manage"."""

    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._writer = None          # the r66 NoteWriter, resolved lazily

    def _plan(self, strategy: str) -> Plan:
        key = f"{strategy}/manage"
        if key not in self._plans:
            self._plans[key] = Plan(key, MGMT_CHECKS, self_ledgers=True)
        return self._plans[key]

    def _notes(self, ctx: dict):
        if self._writer is not None:
            return self._writer
        try:
            for e in (ctx.get("derived_engines") or []):
                if getattr(e, "name", "") == "notes":
                    self._writer = e.writer
                    break
        except Exception:                                      # noqa: BLE001
            self._writer = None
        return self._writer

    # ══════════════════════════════════════════════════════════════════════
    # THE DECISION — for the records this plan covers
    # ══════════════════════════════════════════════════════════════════════
    def decide(self, record, current_premium: float, df_1m=None, open_records=None,
               current_price: Optional[float] = None, ctx: Optional[dict] = None,
               exit_engine=None, now_minutes_held: Optional[float] = None
               ) -> Optional[Intent]:
        """The intent for the NEXT tick, or None if this plan does not cover
        the record (caller falls back to the engine's own evaluate()).
        Writes the row. Never raises — a raise here returns None, and the
        engine decides as it always did."""
        try:
            if not covers(record, open_records):
                return None
            strategy = str(record.get("strategy", "") or "")
            prem = _f(current_premium)
            entry = _f(record.get("entry_premium")) or 0.0
            credit = bool(record.get("is_credit_vertical")) or strategy in (
                "SweepCreditSpread", "TrendCreditSpread")
            pnl = 0.0
            if prem is not None and entry > 0:
                pnl = (entry - prem) / entry if credit else (prem - entry) / entry
            stop_p = _f(record.get("stop_premium"))
            target = _f(record.get("target_premium"))
            ustop = _f(record.get("underlying_stop"))
            price = _f(current_price) if current_price is not None else _f(record.get("current_price"))
            last_close = None
            try:
                if df_1m is not None and len(df_1m):
                    last_close = float(df_1m["close"].iloc[-1])
            except Exception:                                  # noqa: BLE001
                last_close = None
            if price is None:
                price = last_close
            plan = self._plan(strategy)
            t = plan.tick(price, str(record.get("option_side", "") or ""))
            self._readings(t, record, price)

            # ── 1. THE DECLARED SPEC CONDITIONS — never outranked ──────────
            intent = None
            if prem is not None and stop_p and strategy != "TrendCreditSpread":
                hit = (prem >= stop_p) if credit else (prem <= stop_p)
                if hit:
                    name = "premium_stop" if credit else ("stop" if strategy in BUTTERFLIES else "hard_stop")
                    floor_pct = (abs(stop_p - entry) / entry) if entry else 0.0
                    intent = Intent("CLOSE", f"{name}_{floor_pct:.0%} pnl={pnl:.1%}", name, pnl_pct=pnl)
            if intent is None and ustop and last_close is not None:
                side = str(record.get("option_side", "") or "")
                if not credit and record.get("direction") in ("long", "short"):
                    breached = last_close < ustop if record.get("direction") == "long" else last_close > ustop
                else:
                    breached = last_close < ustop if side == "put" else last_close > ustop
                # ── r98 — THE NEARER STOP GOVERNS, EACH TICK ──────────────
                # 🔑 THE OPERATOR'S RULING, 2026-09-22: *"use the nearest one.
                # Each tick one of the two will be closer. Default to the
                # closer one."* And what it is FOR, in his words: *"what I'm
                # attempting to do is kill losers quickly, and preserve winners
                # out of the gate, even if it's modest."*
                # 🔑 THAT INTENT IS EXACTLY `max(structure, trail)`:
                #   · UNDERWATER — the trail is unarmed or below the structure,
                #     so the STRUCTURE governs and the loser dies fast.
                #   · IN PROFIT — the trail climbs above the structure, so the
                #     TRAIL governs and a modest gain is not handed back.
                # 🔴 THE TWO STOPS ARE IN DIFFERENT UNITS AND THE OPERATOR
                # CAUGHT ME GLOSSING IT. The structure stop is a 1m CLOSE
                # through `underlying_stop`; the trail is a PREMIUM level.
                # `stop_premium` bridges them since r91 — but only as a
                # DELTA-LINEAR ESTIMATE of the premium at that underlying
                # level, not an identity.
                # 📊 MEASURED on today's four structure exits: the bridge is
                # good to 0.003-0.013 on the Breakouts, whose structure stops
                # sit 0.01-0.23 points away, where delta-linear is essentially
                # exact. On VOLT it was off by 0.134 — because VOLT's
                # `underlying_stop` is a THESIS LINE, not a protective stop
                # (`und_dist` 0.000), and the bridge was never applied to it.
                # 🔑 SO THE GUARD ASKS WHETHER THE BRIDGE WAS ACTUALLY BUILT,
                # rather than naming strategies: does `stop_premium` agree with
                # `entry - distance x |delta|`? A name list rots and rots
                # PERMISSIVELY (§23); this reads what the record says about
                # itself. ⚠️ AND IT MUST BE DERIVED, NOT READ: the signal's
                # `underlying_stop_is_thesis` IS NOT A `trades` COLUMN, so a
                # rehydrated record returns None, None reads as False, and a
                # guard keyed on it would silently never fire (§22).
                # ⚠️ IT ONLY EVER DEFERS TO A NEARER STOP. `max()` is at or
                # above the structure alone, so this cannot hold a position
                # past both — it exits the moment price reaches the closer one.
                # r54 (BRK.16): an UNARMED Breakout trail (below edge +/- 0.5W) is no stop at all, so it
                # cannot be the nearer one - the structure governs until the trail arms.
                _trail_live = True
                if strategy == "Breakout" and exit_engine is not None and hasattr(exit_engine, "trail_armed"):
                    _trail_live = bool(exit_engine.trail_armed(record))
                if breached and not credit and _trail_live and nearer_stop_defers(
                        record, prem, stop_p, entry):
                    breached = False          # the trail is nearer; it governs
                if breached:
                    name = ("structure_stop" if not credit else
                            ("breach" if strategy == "TrendCreditSpread" else "acceptance"))
                    # r209: a TOUCH - `last_close` is the FORMING 1m bar's last price
                    intent = Intent("CLOSE", f"{name}: touch {last_close:.2f} through "
                                             f"{ustop:.2f} pnl={pnl:.1%}", name, pnl_pct=pnl)
            # ── r82 — PAR DELTA REPLACES THE TARGET FOR THE BREAKOUT ─────
            # Operator, 2026-09-21: *"the breakout needs the delta stop not the
            # 100% stop."* 🔑 AT PAR DELTA THE POSITION IS STOCK CARRYING AN
            # EXPIRY — convexity, the cheap tail and defined risk are all spent
            # — so the give-back is dollar-for-dollar with the underlying.
            # MEASURED on 2026-09-21: the 8 `target_hit` exits fired at delta
            # 0.619-0.650, capping every winner while real optionality
            # remained, and the +100% guillotine is WHY no Breakout has ever
            # reached par — 1 of 45 book-wide, and that one was VOLT.
            # ⚠️ NO DELTA MEANS HOLD, NOT GUESS. `current_delta` is stashed by
            # position_manager for single-leg longs; without it the structure
            # stop and the premium floor still cover the trade. r82 measured
            # extrinsic-from-mid as a proxy and killed it — it reaches zero at
            # delta 0.82, two hours early.
            if intent is None and strategy in DELTA_PAR_STRATEGIES and not credit:
                _dl = abs(float(record.get("current_delta", 0.0) or 0.0))
                if _dl >= DELTA_PAR:
                    intent = Intent("CLOSE", f"delta_par: delta {_dl:.3f} >= "
                                             f"par {DELTA_PAR:.2f} pnl={pnl:.1%}",
                                    "delta_par", pnl_pct=pnl)
            # the target: a debit exit for the RUNAWAY only — the butterfly rides
            # to the close (r169)
            # 🔴 r82 — AND THE COMMENT ABOVE WAS ALREADY TRUE OF THE INTENT AND
            # FALSE OF THE CODE. It says "the RUNAWAY only"; the predicate said
            # `not in BUTTERFLIES`, which is every debit strategy in the tree.
            # Breakout inherited a +100% guillotine nobody wrote for it. The
            # predicate now matches the sentence for the strategies that have
            # been ruled on, rather than the sentence being quietly wrong.
            if (intent is None and prem is not None and target and not credit
                    and strategy not in BUTTERFLIES
                    and strategy not in DELTA_PAR_STRATEGIES and prem >= target):
                intent = Intent("CLOSE", f"target_hit pnl={pnl:.1%}", "target", pnl_pct=pnl)
            if intent is None and credit and prem is not None and prem <= NICKEL:
                intent = Intent("CLOSE", f"nickel_close pnl={pnl:.1%}", "nickel", pnl_pct=pnl)

            # ── 1a0. r288 (BRK.13) — THE BREAKOUT'S DELTA FLOOR ─────────────
            # After the spec stops, par delta and target/nickel; before no-progress and
            # exhaustion. `trade` closes; `log` records and holds; `off` skips.
            if (intent is None and strategy == "Breakout" and not credit
                    and _cfg.BRK_DFLOOR_MODE in ("log", "trade")):
                _df = breakout_delta_floor(record)
                if _df is not None:
                    _record_delta_floor(record, _df, _cfg.BRK_DFLOOR_MODE, prem, price)
                    if _cfg.BRK_DFLOOR_MODE == "trade":
                        intent = Intent("CLOSE", f"delta_floor: |delta| {_df:.3f} <= "
                                                 f"{_cfg.BRK_DELTA_FLOOR:.2f} pnl={pnl:.1%}",
                                        "delta_floor", pnl_pct=pnl)

            # ── 1a. r265 (BRK.8) — THE BREAKOUT'S NO-PROGRESS EXIT ───────────
            # After the spec stops and par delta (they always outrank it), before
            # exhaustion. `trade` cuts; `log` records the cut and holds; `off` skips.
            if (intent is None and strategy == "Breakout" and not credit
                    and _cfg.BRK_NOPROG_MODE in ("log", "trade")):
                _np = breakout_no_progress(record, df_1m)
                if _np is not None and _np["cut"]:
                    _record_no_progress(record, _np, _cfg.BRK_NOPROG_MODE, prem, price)
                    if _cfg.BRK_NOPROG_MODE == "trade":
                        intent = Intent("CLOSE", f"no_progress: {_cfg.BRK_NOPROG_STALL_BARS} closed bars without "
                                                 f"a new extreme, best {_np['best_r']:.2f}R < "
                                                 f"{_cfg.BRK_NOPROG_MIN_R:.2f}R pnl={pnl:.1%}",
                                        "no_progress", pnl_pct=pnl)

            # ── 1b. r51 (BRK.1) — THE BREAKOUT'S EXHAUSTION EXIT ─────────────
            # 🔴 THE MACHINERY WAS ALREADY WRITTEN AND ORPHANED. `_midline_atr`
            # and `_momentum_divergence` survived, fully documented, from an
            # `_evaluate_continuation` path deleted with the strategy it served:
            # MEASURED 2026-09-18, ZERO CALL SITES. This is their first reader.
            # 🔑 TWO TIERS AND THE ORDER IS THE DOCTRINE, quoted from the block
            # above them: EXTENSION-FROM-MIDLINE *"tightens the trail hard
            # (protect the stretched gain) but does NOT exit — a strong trend
            # can stay extended"*; MOMENTUM DIVERGENCE — a new run-favourable
            # extreme on weaker momentum, *"the move is continuing on fumes"* —
            # is the CONFIRMATION that exits.
            # ⚠️ MODE 2, NOT MODE 3, AND THAT IS DELIBERATE FOR NOW. Their own
            # note-to-future-self records that a stricter form requiring BOTH
            # signals *"maps closer to how the operator actually trades — you
            # don't bail on divergence alone if the move isn't also stretched"*,
            # left as a code change by his request. BRK.1 is the first trade
            # with a reason to make it; it is NOT made here, because a
            # behaviour change and a first wiring in one step cannot be told
            # apart when the result comes in.
            if (intent is None and strategy == "Breakout" and exit_engine is not None
                    and prem is not None):
                try:
                    _c = ctx or {}
                    _tid = str(record.get("trade_id", "") or "")
                    _dir = "long" if str(record.get("option_side", "")) == "call" else "short"
                    if exit_engine._momentum_divergence(_tid, record, price, _dir,
                                                        _c.get("trend"), _c.get("df_5m")):
                        intent = Intent("CLOSE",
                                        f"exhaustion: new {_dir} extreme on weaker momentum "
                                        f"— continuing on fumes pnl={pnl:.1%}",
                                        "exhaustion", pnl_pct=pnl)
                    else:
                        _mid, _atr = exit_engine._midline_atr(_c.get("vol"), _c.get("df_5m"))
                        if _mid and _atr and price and abs(price - _mid) >= 2.0 * _atr:
                            t.check("extension_atr", abs(price - _mid) / _atr, None)
                except Exception as exc:                        # noqa: BLE001
                    logger.warning("[manage] exhaustion read failed for %s: %s — "
                                   "the mechanical stops are untouched",
                                   str(record.get("trade_id", ""))[:8], exc)

            # ── 2. THE CALCULATORS — the engine's trail / tightening / theta /
            # velocity, adopted as the plan's own decision ────────────────────
            if intent is None and exit_engine is not None and prem is not None:
                try:
                    d = exit_engine.evaluate(record, prem, df_1m=df_1m,
                                             df_5m=(ctx or {}).get("df_5m"),
                                             vol_state=(ctx or {}).get("vol"),
                                             trend=(ctx or {}).get("trend"))
                    if d.should_exit:
                        cond = str(d.exit_reason or "").split(" ")[0].split(":")[0]
                        intent = Intent("CLOSE", d.exit_reason, cond, pnl_pct=pnl)
                    elif d.new_trail_stop is not None:
                        intent = Intent("TRAIL", f"trail -> {d.new_trail_stop:.2f}", "trail",
                                        trail=d.new_trail_stop, pnl_pct=pnl)
                except Exception as exc:                        # noqa: BLE001
                    logger.warning("[manage] calculator raised for %s: %s — holding this tick",
                                   str(record.get("trade_id", ""))[:8], exc)
            if intent is None:
                intent = Intent("HOLD", "", "", pnl_pct=pnl)

            # ── the row: what fired, or what would fire next tick ──────────
            head = (f"{strategy} {record.get('option_side', '')} "
                    f"{'credit ' if credit else ''}{_n(entry)} -> now {_n(prem)} ({pnl:+.0%})")
            t.check("fired", 1.0 if intent.action == "CLOSE" else 0.0, None)
            if intent.action == "CLOSE":
                t.hold(f"{head}: CUT — {intent.reason}", verdict="CLOSE")
            elif intent.action == "TRAIL":
                t.hold(f"{head}: {intent.reason}; " + self._next_tick_line(record, credit, stop_p, ustop,
                                                                          intent.trail, target),
                       verdict="TRAIL")
            else:
                t.hold(f"{head}: holding — " + self._next_tick_line(
                    record, credit, stop_p, ustop, _f(record.get("trail_stop")), target))
            if ctx is not None:
                self._vector(ctx, strategy, record)
            return intent
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[manage] decide() raised for %s: %s — the engine decides",
                           str(record.get("trade_id", ""))[:8], exc)
            return None

    @staticmethod
    def _next_tick_line(record, credit, stop_p, ustop, trail, target) -> str:
        outs = []
        if stop_p and str(record.get("strategy", "")) != "TrendCreditSpread":
            outs.append(f"premium {'>=' if credit else '<='} {stop_p:.2f} -> out (floor)")
        if ustop:
            side = str(record.get("option_side", "") or "")
            if not credit and record.get("direction") in ("long", "short"):
                thru = "<" if record.get("direction") == "long" else ">"
            else:
                thru = "<" if side == "put" else ">"
            outs.append(f"touch {thru} {ustop:.2f} -> out (breach)")
        if trail:
            outs.append(f"premium <= {trail:.2f} -> out (trail)")
        if target and not credit and str(record.get("strategy", "")) not in BUTTERFLIES:
            outs.append(f"premium >= {target:.2f} -> out (target)")
        if str(record.get("strategy", "")) in BUTTERFLIES:
            outs.append("15:45 -> flatten (rides to the close)")
        if credit:
            outs.append("value <= nickel -> out")
        return "; ".join(outs) if outs else "no exit condition readable"

    def _readings(self, t, rec, price) -> None:
        entry = _f(rec.get("entry_premium")) or 0.0
        prem = _f(rec.get("current_premium"))
        t.check("premium", prem, None)
        t.check("entry_premium", entry or None, None)
        t.check("stop_premium", _f(rec.get("stop_premium")), None)
        t.check("trail_stop", _f(rec.get("trail_stop")), None)
        t.check("target_premium", _f(rec.get("target_premium")), None)
        ustop = _f(rec.get("underlying_stop"))
        t.check("underlying_stop", ustop, None)
        t.check("ticks_held", int(rec.get("excursion_ticks") or 0), None)
        if ustop and price:
            t.check("dist_to_stop", round(float(price) - ustop, 4), None)
            t.anchor(invalidation=ustop)
        mfe, mae = _f(rec.get("mfe_premium")), _f(rec.get("mae_premium"))
        if mfe is not None and entry > 0:
            t.check("mfe_pct", (mfe - entry) / entry, None)
        if mae is not None and entry > 0:
            t.check("mae_pct", (mae - entry) / entry, None)

    # ══════════════════════════════════════════════════════════════════════
    def tick(self, ctx: dict, records, current_price: float) -> int:
        """One row per open record. Returns rows written. Never raises."""
        n = 0
        for rec in (records or []):
            try:
                if self._one(ctx, rec, current_price):
                    n += 1
            except Exception as exc:                            # noqa: BLE001
                logger.debug("[manage] row skipped for %s: %s",
                             str(rec.get("trade_id", ""))[:8], exc)
        return n

    def _one(self, ctx: dict, rec, price: float) -> bool:
        strategy = str(rec.get("strategy", "") or "")
        if not strategy or strategy == "ADOPTED":
            return False
        if covers(rec, ctx.get("_open_records")):
            return False                # decide() wrote this record's row
        conds = EXIT_CONDITIONS.get(strategy)
        plan = self._plan(strategy)
        t = plan.tick(price, str(rec.get("option_side", "") or ""))

        # ── the readings — the record's own fields, the exit engine's state ─
        entry = _f(rec.get("entry_premium")) or 0.0
        prem = _f(rec.get("current_premium"))
        stop_p = _f(rec.get("stop_premium"))
        trail = _f(rec.get("trail_stop"))
        target = _f(rec.get("target_premium"))
        ustop = _f(rec.get("underlying_stop"))
        mfe = _f(rec.get("mfe_premium"))
        mae = _f(rec.get("mae_premium"))
        ticks = int(rec.get("excursion_ticks") or 0)
        credit = bool(rec.get("is_credit_vertical")) or strategy in (
            "SweepCreditSpread", "TrendCreditSpread", "IronCondorStrategy")
        pnl = None
        if prem is not None and entry > 0:
            pnl = (entry - prem) / entry if credit else (prem - entry) / entry
        t.check("premium", prem, None)
        t.check("entry_premium", entry or None, None)
        t.check("pnl_pct", pnl, None)
        t.check("stop_premium", stop_p, None)
        t.check("trail_stop", trail, None)
        t.check("target_premium", target, None)
        t.check("underlying_stop", ustop, None)
        t.check("ticks_held", ticks, None)
        if ustop and price:
            t.check("dist_to_stop", round(float(price) - ustop, 4), None)
            t.anchor(invalidation=ustop)
        if mfe is not None and entry > 0:
            t.check("mfe_pct", (mfe - entry) / entry if not credit else (entry - mfe) / entry, None)
        if mae is not None and entry > 0:
            t.check("mae_pct", (mae - entry) / entry if not credit else (entry - mae) / entry, None)

        if conds is None:
            t.hold(f"{strategy}: no declared exit conditions — the exit engine's "
                   f"default route applies; premium {_n(prem)} vs entry {_n(entry)}")
            self._vector(ctx, strategy, rec)
            return True

        # ── "if this or this -> out", from the declared conditions ─────────
        outs = []
        for name in conds:
            if name in ("hard_stop", "premium_stop", "stop") and stop_p:
                outs.append(f"premium {'>=' if credit else '<='} {stop_p:.2f} -> out ({name})")
            elif name in ("structure_stop", "breach", "acceptance") and ustop:
                # the side price must CLOSE ON to hurt this structure: a long
                # debit or a put credit spread is hurt below the level; a
                # short debit or a call credit spread above it
                side = str(rec.get("option_side", "") or "")
                if not credit and rec.get("direction") in ("long", "short"):
                    thru = "<" if rec.get("direction") == "long" else ">"
                else:
                    thru = "<" if side == "put" else ">"
                outs.append(f"touch {thru} {ustop:.2f} -> out ({name})")
            elif name == "trail":
                outs.append(f"premium <= {trail:.2f} -> out (trail armed)" if trail
                            else "trail not armed yet")
            elif name == "target" and target:
                outs.append(f"premium >= {target:.2f} -> out (target)")
            elif name == "nickel":
                outs.append("value at the nickel -> out (nickel)")
            elif name == "ladder":
                outs.append("see CondorManagement (roll / tent / close)")
        head = (f"{strategy} {rec.get('option_side', '')} "
                f"{'credit ' if credit else ''}{_n(entry)} -> now {_n(prem)}"
                + (f" ({pnl:+.0%})" if pnl is not None else "")
                + (f", MFE {_n(mfe)}" if mfe is not None else "")
                + f", {ticks} ticks")
        t.hold(f"{head}: " + "; ".join(outs) if outs else f"{head}: holding")
        self._vector(ctx, strategy, rec)
        return True

    def _vector(self, ctx: dict, strategy: str, rec) -> None:
        """The r66 derived vector, recorded for the OPEN position — phase
        'manage' in strategy_note's outcome column, trade_id attached."""
        w = self._notes(ctx)
        if w is None:
            return
        try:
            w.write(strategy, ctx, fired=False, outcome="manage",
                    trade_id=str(rec.get("trade_id", "") or ""))
        except Exception:                                      # noqa: BLE001
            pass


_PLAN: Optional[ManagementPlan] = None


def get_management_plan() -> ManagementPlan:
    global _PLAN
    if _PLAN is None:
        _PLAN = ManagementPlan()
    return _PLAN
