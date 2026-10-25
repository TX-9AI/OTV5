"""
derived/snapshot.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.7  2026-10-24  CD.2 — the VWAP slope is measured in MARKET time: the comparison row is the one whose bar_ts_ms is
      ~600 s before the current bar's, carrying the SAME session anchor. By write time, across a restart gap, the
      comparison row could be yesterday's or carry another day's anchor.
v4.6  2026-09-22  OTV4TEST r99 — THE VWAP CONTEXT REACHES THE SNAPSHOT AT LAST.
      `price_vs_vwap` was NULL on EVERY ROW EVER WRITTEN, back to 09-09:
      volatility_engine sets "ABOVE"/"BELOW"/"NONE", a CATEGORICAL, and the
      payload ran _f() on it - float("ABOVE") raises, _f swallows it, the
      column stores None. Computed every tick for weeks and discarded at
      this boundary. Now records the VWAP NUMBER from anchors.vwap_now()
      (session-anchored, fails closed), a SIGNED vwap_dist_pct, the
      categorical AS TEXT, and vwap_source naming WHICH of the two VWAPs in
      this tree answered - they differed by 4.86 points when measured.
      AND vwap_slope_pct, because DISTANCE CANNOT SEPARATE a real extension
      from a fake one. Operator: "We're OK with buying into the beginning of
      an extension and riding it for as long as it holds. What I'm not OK
      with is buying a fake extension... it's OK that it's extended as long
      as it's pulling everything up with it." A real extension DRAGS THE
      MEAN; a fake pokes out against a flat VWAP. RECORDED, NOT GATED.
v4.5  2026-09-18  OTV4TEST r51 — the three fields now actually READ, because
      `_flow_conn` gained a producer in the same revision. Without it
      `flow_imbalance`, `flow_tagged_frac` and `book_depth` would have written
      NULL on every row while looking correct.
v4.4  2026-09-18  OTV4TEST r51 — THE THREE A STOP RUN CANNOT MANUFACTURE:
      `flow_imbalance` / `flow_tagged_frac` / `flow_prints`, `gamma_regime`
      (the [-1,+1] pinning-trending score, NOT raw `gex` and NOT the
      `gex_environment` classification), and `book_depth`. These are BRK.1's
      surviving entry gates, and gating on them without recording them would be
      this module's own founding defect for the fourth time (r240/r243/r244).
      ⚠️ NONE OF THEM CAN BE BACKFILLED — prints purge in three days and the
      regime is a rolling baseline. The operator's head-to-head starts Monday;
      every session without these is a session whose "why" is unrecoverable.
      ⚠️ VOLUME EXPANSION IS DELIBERATELY ABSENT: measured over 736 fleet
      breaks it does not separate (best lift 1.08x), because a stop run
      manufactures it.
v4.3  2026-09-04  r244 — 🔑 ALL THREE PIN MEASURES, NOT ONE.
      `pin_concentration` (29% fail) and the GEX environment behind `pinning`
      (53% fail) GATE every butterfly fire and NEITHER has ever been tested
      against an outcome — both live in `plan_check` with no `trade_id`, so
      nothing can join them to a P&L. Operator, 2026-09-04, on whether any
      measure of pin strength has been validated: none has.
      🔴 INSTRUMENTING ONLY THE EM FRACTION WOULD HAVE BEEN WORSE THAN USELESS
      — a study could conclude "EM predicts nothing" while the real signal sat
      in a field nobody recorded, and that negative would be believed.
      ⚠️ RAW, NOT THRESHOLDED. The gate's pass/fail is already in `plan_check`;
      what is missing is the VALUE, and a study cannot fit a boundary it can
      only see one side of.
      ⚠️ SEPARATELY, NOT COMPOSITED — r224's lesson: a composite that separates
      tells you nothing about WHICH PART did the work.
      ⚠️ CONTEXT FOR THE NEXT READER: `screen_entry_vectors` scored SIXTEEN
      point-in-time vectors over 152 runaway trades and the best separation was
      AUC 0.54, against a noise floor of 0.19 in its own fixture. It never
      covered these three. Nothing here is evidence yet; it is the first time
      the question can be asked.
v4.2  2026-09-04  r243 — 🔴 THE PIN AND ITS EM FRACTION JOIN THE
      PAYLOAD. Operator, 2026-09-04, after the stop-removal and window cases
      both failed on evidence: *"that leaves the EM variable as our last hope
      of raising our win rate."* It was UNANSWERABLE — `pin_em_fraction` gates
      every butterfly fire, `plan_check` carries it on every tick with NO
      trade_id, and this payload is keyed BY trade_id and carried no pin and no
      EM. So whether the 7 winners sat lower in the 0.30-1.00 band than the 13
      losers could not be asked.
      🔑 SAME SHAPE AS r240: a field computed, used for a DECISION, and never
      written where the OUTCOME could be joined to it. The bridge existed; it
      did not carry the field.
      ⚠️ DERIVED FROM ctx, NOT PLUMBED — `pin_strike` and `atm_iv` are already
      there and `expected_move()` is the strategy's own function, so this is
      the fraction THE GATE USED rather than a second definition of it.
      ⚠️ EMITTED FOR EVERY STRATEGY, not just the butterfly: the runaway and
      the ORB fire near pins too, and a field present only where someone
      expected to need it is a field no study can ask a new question of.
      ⚠️ None WHEN UNMEASURABLE, 0.0 FOR A PIN AT THE MONEY — opposite facts,
      and this file's contract is that absent stays distinguishable.
      ⚠️ AND IT CANNOT RAISE: `capture()` runs on every fill, so a study field
      that throws would cost a trade its snapshot for a number nobody needs
      live. S4 drives four degenerate contexts.
      ⚠️ NOTHING ACCRUES RETROACTIVELY — the 20 butterflies already banked stay
      unmeasurable. This starts the collection.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Owns `fire_snapshot`. Everything derived at the instant a trade fired.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

🔴 THE OPERATOR'S PURPOSE, 2026-08-22: if shadow observers are rebuilt on this
repo it is to study **which derived indicators reveal any usable edge** — so
what is wanted is a snapshot of everything available at the moment of the fire.

That makes the study a JOIN:

    fire_snapshot JOIN trades ON trade_id

Derived indicators on one side, outcome and excursion on the other. "Did high
charm at fire predict a larger MFE?" becomes one query. Today it cannot be
asked at all.

⚠️ EXCURSION TELEMETRY IS UNAFFECTED AND LIVES ON A DIFFERENT AXIS.
`mfe_premium` / `mfe_bars` / `mae_premium` / `mae_bars` are properties of the
trade's LIFE and stay on `trades`. This is one frozen instant at entry.
Different clocks, different tables, no collision — and the join is what makes
excursion work BETTER than it does today.

recorded label plus conviction and dropped every term that actually decided the
entry — so the journal had a vocabulary of two for a decision made on twenty.
If the point is DISCOVERING which indicator reveals edge, pre-selecting the
columns defeats the exercise before it starts.

⚠️ ABSENCE IS RECORDED EXPLICITLY. A value that was unavailable at fire time is
written as null — NEVER omitted, NEVER zero. A missing indicator and an
indicator that measured zero are different facts, and the whole VW.1 saga was
that distinction going wrong across five layers.

⚠️ WHY A JSON PAYLOAD RATHER THAN COLUMNS. The indicator set will keep growing
— order of 60-100 fields — and every addition would otherwise be a migration on
a table that already carries 75 columns and an `entry_snapshot` JSON escape
hatch. `trades` stays about the trade; this stays about the world at that
moment. Promote a field to a real column when a study proves it earns one.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f



def _vwap_fields(ctx, price, vol, _sym: str = "QQQ") -> dict:
    """The VWAP context for a fire: the number, the signed distance, the label.

    🔑 ONE SOURCE, NAMED. `anchors.vwap_now()` is the session-anchored VWAP
    (r94: 09:30 open, not midnight; r96: deep-fetched on a cold start) and it
    FAILS CLOSED with a reason rather than returning a partial-window value.
    ⚠️ IT FALLS BACK TO THE VOLATILITY ENGINE'S OWN df_5m VWAP ONLY IF THE
    SESSION ONE IS UNAVAILABLE, and `vwap_source` then says so — a study that
    cannot tell the two apart is averaging two different quantities.
    ⚠️ `vwap_dist_pct` IS SIGNED: positive means price ABOVE the VWAP. The
    sign is the half that answers "were we buying an extension?".
    """
    vw, src = None, None
    try:
        from derived import anchors as _A
        vw, _why = _A.vwap_now()
        if vw is not None:
            src = "session"
    except Exception:                                           # noqa: BLE001
        vw = None
    if vw is None and vol is not None:
        try:
            _v = float(getattr(vol, "vwap", 0) or 0)
            if _v > 0:
                vw, src = _v, "frame_5m"
        except (TypeError, ValueError):
            vw = None
    # 🔴 r99 — THE SLOPE IS WHAT SEPARATES A REAL EXTENSION FROM A FAKE ONE,
    # AND DISTANCE ALONE CANNOT. Operator, 2026-09-22: *"We're OK with buying
    # into the beginning of an extension and riding the extension for as long
    # as it holds. What I'm not OK with is buying a FAKE extension."*
    # 🔑 AT THE MOMENT OF ENTRY THOSE TWO LOOK IDENTICAL on distance — both
    # are price away from VWAP. What differs is whether the move is DRAGGING
    # THE MEAN WITH IT: a real extension pulls VWAP along behind it; a fake
    # pokes out and snaps back through a VWAP that never moved.
    # ⚠️ RECORDED, NOT GATED. Nothing reads this yet, by §31 — it is the
    # measurement that would let the corpus answer the operator's question,
    # and a threshold set before that measurement is the thing
    # `PREREG_TRAIL.md` exists to prevent.
    slope = None
    try:
        from data.derived_store import get_derived_store as _gds
        _st = _gds()
        _rows = list(_st.conn.execute(
            "SELECT bar_ts_ms, vwap, vwap_anchor_ms FROM indicator_series WHERE symbol=? "
            "AND vwap IS NOT NULL AND bar_ts_ms IS NOT NULL ORDER BY bar_ts_ms DESC LIMIT 400", (_sym,)))
        if vw and _rows:
            _now_ms, _anchor = _rows[0][0], _rows[0][2]          # CD.2: market time, one session's anchor
            _past = [r for r in _rows if r[0] <= _now_ms - 600_000 and r[2] == _anchor]
            if _past and _past[0][1]:
                slope = (float(vw) - float(_past[0][1])) / float(vw) * 100.0
    except Exception:                                           # noqa: BLE001
        slope = None
    px = _f(price)
    dist = ((px - vw) / vw * 100.0) if (vw and px) else None
    lab = getattr(vol, "price_vs_vwap", None) if vol is not None else None
    return {
        "vwap": _f(vw),
        "vwap_dist_pct": _f(dist),
        "vwap_source": src,
        # signed % change in VWAP over ~10 minutes: is the mean being dragged?
        "vwap_slope_pct": _f(slope),
        # TEXT, not `_f()`. This is the categorical that has been silently
        # nulled on every row ever written.
        "price_vs_vwap": str(lab) if lab else None,
    }


class SnapshotEngine(DerivedEngine):
    name = "snapshot"
    table = "fire_snapshot"

    def __init__(self, store=None, symbol: str = "", levels=None):
        super().__init__(store)
        self.symbol = symbol
        self._levels = levels          # LevelEngine, for the provenance walk

    def build_payload(self, ctx: dict) -> dict:
        """Every derived value we can see right now. Keys ALWAYS present.

        ⚠️ EVERY KEY IS EMITTED EVEN WHEN NULL. A caller — or a study three
        months from now — can then tell "measured as absent" from "this field
        did not exist yet in that era", which an omitted key cannot express.
        """
        trend, vol = ctx.get("trend"), ctx.get("vol")
        price = _f(ctx.get("price"))
        # r243 — the pin and how far it sits, in expected moves. Both None when
        # unmeasurable; NEVER 0.0, because a pin at the money and a pin that
        # could not be read are opposite facts and this file's own contract is
        # that "measured as absent" must stay distinguishable.
        _gex = ctx.get("gex")
        _pin = _f(getattr(_gex, "pin_strike", None))
        # 🔴 r244 — THE OTHER TWO PIN MEASURES, for the same reason as the EM
        # fraction. `pin_concentration` and the GEX environment GATE every
        # butterfly fire (`pin_concentration` 29% fail, `pinning` 53%) and
        # NEITHER has ever been tested against an outcome — they live in
        # plan_check with no trade_id, so nothing can join them to a P&L.
        # Operator, 2026-09-04, on whether any measure of pin strength has been
        # validated: nothing has. `screen_entry_vectors` scored SIXTEEN vectors
        # over 152 runaway trades and the best separation was AUC 0.54 against
        # a noise floor of 0.19 in its own fixture — and it never covered these.
        # 🔑 THREE MEASURES OR ONE ANSWER. Instrumenting only the EM fraction
        # would let a study conclude "EM predicts nothing" while the real
        # signal sat in a field nobody recorded. r224's own lesson: a composite
        # that separates tells you nothing about WHICH PART did the work, so
        # each component is recorded separately.
        # ⚠️ RAW, NOT THRESHOLDED. The gate's answer (pass/fail against
        # PIN_CONC_MIN) is already in plan_check; what is missing is the VALUE,
        # because a study cannot fit a boundary it can only see one side of.
        _conc = _f(getattr(_gex, "pin_concentration", None))
        _gex_env = getattr(_gex, "gex_environment", None)
        _gex_env = str(_gex_env) if _gex_env else None
        _pin_frac = None
        try:
            from strategy.gex_pin_butterfly import expected_move as _em_fn
            _em = _em_fn(price, _f(ctx.get("atm_iv"))) if price else None
            if _pin and _em and _em > 0:
                _pin_frac = abs(_pin - price) / _em
        except Exception:                                       # noqa: BLE001
            _pin_frac = None

        payload = {
            "schema": 1,
            "ts": time.time(),
            "price": price,
            # ── tier 1: path-dependent
            "adx": _f(getattr(trend, "primary_adx", None)) if trend else None,
            "atr": _f(getattr(vol, "atr_current", None)) if vol else None,
            "atr_normalized": _f(getattr(vol, "atr_normalized", None)) if vol else None,
            "bb_width_pct": _f(getattr(vol, "bb_width_pct", None)) if vol else None,
            # 🔴 r99 — THE VWAP CONTEXT, AND IT WAS NULL ON EVERY ROW EVER
            # WRITTEN. Operator, 2026-09-22, asking why the runaway's fake-outs
            # could not be diagnosed: *"On the fake out question, do we have
            # any VWAP to reference? That's what I would wanna know."*
            # MEASURED: `price_vs_vwap` NULL on ALL 23 banked runaway
            # snapshots, back to 09-09 — before the r69 breakage existed.
            # 🔑 THREE FAULTS STACKED, AND NONE OF THEM ERRORED.
            # (1) TYPE: `volatility_engine:226` sets "ABOVE"/"BELOW"/"NONE", a
            #     CATEGORICAL, and this line ran `_f()` on it — `float("ABOVE")`
            #     raises, `_f` swallows it, the column stores None. Computed
            #     every tick for weeks and discarded at this boundary.
            # (2) GRANULARITY: even repaired it is a DIRECTION, not a DISTANCE,
            #     and cannot answer the question actually being asked — HOW
            #     EXTENDED was the entry. A continuation trade is definitionally
            #     a bet on extension, so distance is the whole point.
            # (3) SOURCE: `vol.vwap` is a SECOND VWAP, a df_5m cumsum
            #     (`volatility_engine:223`) anchored to whatever the frame
            #     spans — not the session-anchored one r94/r96 repaired. Two
            #     VWAPs, nothing forcing them to agree, and the snapshot was
            #     reading the unfixed one. Same shape as WIN.1's window table.
            # ✅ So the NUMBER comes from `anchors.vwap_now()` — session
            # anchored, deep-fetched on a cold start, and FAILS CLOSED with a
            # reason — and the categorical is stored AS TEXT.
            # ⚠️ `vwap_source` RECORDS WHICH ONE ANSWERED, because a study that
            # cannot tell a session VWAP from a frame VWAP is measuring two
            # different quantities and calling them one (§0.5).
            **_vwap_fields(ctx, price, vol, self.symbol),
            # ── tier 4: second-order + vol measures
            "charm": _f(ctx.get("charm")),
            "vanna": _f(ctx.get("vanna")),
            # ⚠️ ctx["gex"] is a GEXSnapshot OBJECT — _f() on it yields None,
            # which is why this column has been NULL on every row ever
            # written. The scalar is `net_gex`. See derived/surface.py r140.
            "gex": _f(getattr(ctx.get("gex"), "net_gex", None)),
            "atm_iv": _f(ctx.get("atm_iv")),
            "iv_slope": _f(ctx.get("iv_slope")),
            "realised_vol_cc": _f(ctx.get("realised_vol_cc")),
            "realised_vol_parkinson": _f(ctx.get("realised_vol_parkinson")),
            "variance_risk_premium": _f(ctx.get("variance_risk_premium")),
            "expected_move_iv": _f(ctx.get("expected_move_iv")),
            "expected_move_straddle": _f(ctx.get("expected_move_straddle")),
            "session_fraction_remaining": _f(ctx.get("session_fraction_remaining")),
            # ── context
            "trend_direction": getattr(trend, "overall_direction", None) if trend else None,
            # ── CONTEXT FOR THE JOINS THIS TABLE EXISTS TO ENABLE ───────────
            # ⚠️ CHARACTER AND GAP ARE CONDITIONERS, NOT SIGNALS. Neither is a
            # finding on its own; both qualify a finding about something else.
            # 🔴 THE ORB QUESTION THIS MAKES ASKABLE: in the v3 book ORB Long
            # ran 4 trades / +$332.50 while ORB Short ran 14 / -$3,812.30, and
            # that asymmetry has never been conditioned on anything. With
            # gap_class on the fire row the question becomes "were the shorts
            # losing ON GAP-UP DAYS — fading a gap that kept going — while the
            # longs happened to align with theirs?" Two columns, one join, and
            # it may reframe the flagship trade's one weak side.
            "character": ctx.get("character"),
            "character_held_s": _f(ctx.get("character_held_s")),
            "gap_pct": _f((ctx.get("gap") or {}).get("gap_pct")
                          if isinstance(ctx.get("gap"), dict)
                          else ctx.get("gap_pct")),
            # 🔴 r243 — THE PIN AND ITS EM FRACTION. Operator, 2026-09-04,
            # after the stop-removal and window cases both failed on evidence:
            # *"then that leaves the EM variable as our last hope of raising
            # our win rate."* And it was UNANSWERABLE — `pin_em_fraction` is
            # computed on every butterfly tick and gates every fire, but this
            # payload carried no pin and no EM, and `plan_check` has the value
            # with NO trade_id. So there is no way to ask whether the seven
            # winners sat lower in the 0.30-1.00 band than the thirteen losers,
            # which is the entire question.
            # 🔑 SAME SHAPE AS r240: a field computed, used for a DECISION, and
            # never written where the OUTCOME could be joined to it. This
            # payload is keyed by trade_id, so it is the bridge — it just did
            # not carry the field.
            # ⚠️ DERIVED HERE, NOT PLUMBED. `pin_strike` and `atm_iv` are
            # already in ctx and `expected_move()` is the strategy's own
            # function, so this reproduces the fraction the gate actually used
            # rather than inventing a second definition of it.
            # ⚠️ AND IT IS EMITTED FOR EVERY STRATEGY, not just the butterfly —
            # the runaway and the ORB fire near pins too, and a field present
            # only where someone expected to need it is a field no study can
            # ask a new question of.
            "pin_strike": _pin,
            "pin_em_fraction": _pin_frac,
            "pin_concentration": _conc,
            "gex_environment": _gex_env,
            "gap_class": ((ctx.get("gap") or {}).get("gap_class")
                          if isinstance(ctx.get("gap"), dict) else None),
        }

        # The level walk WITH PROVENANCE — nearest levels each way and their
        # touch scores. This is the operator's own framing of what price is
        # trading into, and it has never been recorded at fire time.
        walk = None
        try:
            if self._levels is not None and price:
                walk = self._levels.walk(price, limit=3)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("snapshot: level walk unavailable: %s", exc)
        payload["levels"] = walk           # null if unavailable, never {}

        # Fork state at fire, both frames — including WHY it was absent.
        fork = None
        try:
            fork = ctx.get("fork_state")
        except Exception:                                       # noqa: BLE001
            pass
        payload["fork"] = fork

        # ══ r51 — THE THREE A STOP RUN CANNOT MANUFACTURE ═════════════════════
        # BRK.1's surviving gates, recorded RAW at fire time. This module exists
        # because of exactly one failure, three times over (r240, r243, r244): a
        # field COMPUTED, used for a DECISION, and never RECORDED — so
        # `pin_concentration` and the GEX environment gated every butterfly fire
        # and neither could ever be tested against an outcome. Gating BRK.1 on
        # regime, aggression and depth without recording them would be the
        # fourth.
        # 🔑 AND THE OPERATOR'S HEAD-TO-HEAD IS WHY IT IS URGENT RATHER THAN
        # TIDY. 2026-09-18: *"when we see them trade head-to-head, we're gonna
        # uncover the why — why the liquidity hunt is better than the breakout
        # for conditions X Y & Z."* Outcomes alone answer "which won". Only the
        # CONDITIONS answer "when". None of these three can be backfilled:
        # prints purge in three days, and the regime is a rolling baseline that
        # cannot be reconstructed after the fact.
        # ⚠️ RAW, NOT THRESHOLDED, and NOT COMPOSITED — this file's own rule.
        # ⚠️ VOLUME EXPANSION IS DELIBERATELY NOT HERE: measured 2026-09-18 over
        # 736 fleet breaks, it does not separate a break that made 1R from one
        # that did not (best lift 1.08x). A stop run MANUFACTURES it, which is
        # the operator's own insight, so it describes that a break happened and
        # never whether it holds.
        _conn = ctx.get("_flow_conn")
        _agg = None
        try:
            if _conn is not None:
                from analysis.order_flow import aggression as _aggr
                _agg = _aggr(_conn, self.symbol)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("snapshot: aggression unavailable: %s", exc)
        payload["flow_imbalance"] = _f((_agg or {}).get("imbalance"))
        payload["flow_tagged_frac"] = _f((_agg or {}).get("tagged_frac"))
        payload["flow_prints"] = _f((_agg or {}).get("prints"))

        # the PINNING/TRENDING score in [-1,+1] — NOT `gex` (raw net gamma) and
        # NOT `gex_environment` (a classification). It fails closed on staleness
        # by its own design, so a null here means "could not be read now".
        _reg = None
        try:
            from derived.gamma_regime import regime as _regime
            _reg = _regime()
        except Exception as exc:                                # noqa: BLE001
            logger.debug("snapshot: gamma regime unavailable: %s", exc)
        payload["gamma_regime"] = _f(_reg)

        # depth at the touch and how it moved — the book's answer to the same
        # question the tape answers above, and independent of it.
        _dep = None
        try:
            if _conn is not None:
                from analysis.order_flow import depth as _depth
                _dep = _depth(_conn, self.symbol)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("snapshot: depth unavailable: %s", exc)
        payload["book_depth"] = _dep        # null when unreadable, never {}
        return payload

    def capture(self, trade_id: str, ctx: dict) -> int:
        """Write the snapshot for a fired trade. Returns rows written.

        ⚠️ CALLED FROM THE TRADE WRITE PATH so the snapshot and the trade row
        land together. A trade with no snapshot is a hole in the study; a
        snapshot with no trade is an orphan.
        ⚠️ NEVER RAISES — the base class wraps `run`, and this path is wrapped
        too, because a study artifact must never be able to fail a fill.
        """
        store = self._store
        if store is None or not trade_id:
            return 0
        try:
            payload = self.build_payload(ctx)
            return store.write_fire_snapshot(
                trade_id, self.symbol or ctx.get("symbol") or "",
                json.dumps(payload, default=str))
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[derived:snapshot] capture failed for %s: %s — the "
                           "trade is unaffected; this study row is absent",
                           trade_id, exc)
            return 0

    def derive(self, ctx: dict) -> int:
        """Nothing per-tick. This engine is event-driven — see `capture`."""
        return 0
