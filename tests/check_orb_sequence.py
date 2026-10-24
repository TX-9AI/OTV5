#!/usr/bin/env python3
"""
tests/check_orb_sequence.py  v1.5
v1.5  2026-10-03  OTV4TEST r220 (TIME.1) — S4 PASSES A CLOCK (10:00). It called generate_signal with no now_hhmm and relied on the
      plan skipping its window check when the clock was unreadable; r220 makes an unreadable clock DORMANT. Production
      always passes one (main: _now_disp = now_et()). The assertion is unchanged.
v1.4  2026-10-02  OTV4TEST r187 (ROSTER.1) — RE-POINTED BY THE RULING, NOT LOOSENED:
      the strategy is OFF by default from r187; this checker tests its LOGIC,
      so it switches it on for its own run (OT_ORB_TRADE=1). check_trade_switches pins the default.
v1.3  2026-09-13  OTV4TEST r20 — the `liq_map=None` kwarg dropped from every
      `ORBStrategy.generate_signal` call; nothing else changed. The parameter is
      REMOVED rather than ignored, so a harness still passing it raises — which
      is how mainline r365 found a live call site that three source-shape gates
      had missed, because this kind of check DRIVES the function.
v1.2  2026-09-08  OTV4TEST r3 — S11b drives the acceptance (close + hold), since the
      runaway invalidation is no longer a wick to the 50 (orb_engine v4.13).
v1.1  2026-09-04  r235 — S4's fixtures set the SEQS, not the bare
      boolean. Setting only `order_placed` no longer refuses, so the check
      would fall through to the liquidity analysis and die on a None map — a
      red for the wrong reason, which is the CV.1 failure.
v1.0  2026-09-01  r207 — THE ORB FIRING SEQUENCE, PINNED BY EXECUTION.

Born red at f74818b (r206), where S1/S2/S3/S5/S6/S7/S8/S9/S10 all fail.

🔴 WHAT THIS EXISTS TO STOP, and it is not hypothetical. On 2026-09-01 QQQ
took TWO ORB shorts off ONE confirmed break+retest: 2 contracts at 1.56
stopped on the 25% floor, then 24 contracts at 1.15 — the exact premium the
first exited at — on the same tick, dead two minutes later on the structure
stop. Three separate defects had to line up:

  1. r195 removed `mark_triggered()` from the ORB dispatch and made
     `_orb_offer_working()` the duplicate suppressor. That reads a table
     PAPER NEVER WRITES, because `_place_single_leg` short-circuited to the
     paper filler above the standing-offer branch. Paper had no suppressor.
  2. `main.py` bound `orb = ctx["orb"]` at the top of the tick and dispatched
     on it at the bottom. `_rearm()` REPLACES ORBData, so after the exit the
     ctx reference was an orphan still reading OPEN_SHORT. r96's defect, at a
     different seam.
  3. The sizer measured the stop distance from the LIVE price, so the second
     fire — a few cents from its own invalidation — sized twelve times larger.

⚠️ EVERY CHECK BELOW THAT CAN EXECUTE, EXECUTES. WORKING_AGREEMENT 21: a test
that reads source text proves nothing about runtime, and 162 tests once passed
over a NameError that crash-looped the fleet. The three source-text checks
(S7/S8/S9) are pinned to CALL and BRANCH shapes via the AST, never to a string
that a comment could satisfy — WORKING_AGREEMENT 20.
"""

from __future__ import annotations
import os as _os_r187
_os_r187.environ["OT_ORB_TRADE"] = "1"   # r187: test the strategy's logic switched on

import ast
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def _frame(rows):
    """A 1m frame the engine can advance on. rows = [(o,h,l,c), ...].

    The engine reads `iloc[-2]`, so the caller supplies the bar to be consumed
    followed by one forming bar.
    """
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
        index=pd.date_range("2026-09-01 09:35", periods=len(rows), freq="1min"))


def _armed_engine(direction: str):
    """An engine with a real range that has just registered a real break.

    ⚠️ BUILT BY DRIVING `_check_for_break`, NOT BY SETTING FIELDS. A fixture
    that assigns the state directly encodes my belief about how a break is
    registered; driving the real method encodes the code's.
    """
    from analysis.orb_engine import ORBEngine
    eng = ORBEngine()
    d = eng._data
    d.orb_high, d.orb_low, d.orb_width = 707.70, 706.21, 1.49
    from analysis.orb_engine import ORBState
    d.state = ORBState.WAITING_FOR_BREAK
    if direction == "short":
        # opens inside, closes below, wick high 706.81 -> 0.60 above the low
        eng._check_for_break(_frame([(707.00, 706.81, 705.40, 705.60),
                                     (705.60, 705.70, 705.30, 705.50)]))
    else:
        # opens inside, closes above, wick low 707.10 -> 0.60 below the high
        eng._check_for_break(_frame([(706.90, 708.60, 707.10, 708.40),
                                     (708.40, 708.70, 708.30, 708.50)]))
    return eng


def _fn_source(path: str, name: str):
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def main() -> int:
    from analysis.orb_engine import ORBData, ORBState

    # ── S1 — the two fields exist on the dataclass ───────────────────────
    ann = getattr(ORBData, "__annotations__", {})
    check("S1 ORBData carries stop_distance_px and order_placed",
          "stop_distance_px" in ann and "order_placed" in ann,
          f"missing: {[k for k in ('stop_distance_px', 'order_placed') if k not in ann]}")

    # ── S2 — the break FREEZES |wick - boundary|, both directions ────────
    if "stop_distance_px" in ann:
        es = _armed_engine("short")
        ds = es._data
        el = _armed_engine("long")
        dl = el._data
        ok_s = (ds.state == ORBState.ARMED_SHORT
                and abs(ds.stop_distance_px - (ds.break_candle_high - ds.orb_low)) < 1e-9)
        ok_l = (dl.state == ORBState.ARMED_LONG
                and abs(dl.stop_distance_px - (dl.orb_high - dl.break_candle_low)) < 1e-9)
        check("S2 the break freezes the boundary-to-wick distance both ways",
              ok_s and ok_l,
              f"short={ds.stop_distance_px:.4f} (want {ds.break_candle_high - ds.orb_low:.4f}) "
              f"long={dl.stop_distance_px:.4f} (want {dl.orb_high - dl.break_candle_low:.4f})")

        # ⚠️ THE POINT OF FREEZING IT: the number must not move when price
        # does. This is the 2->24 resize made unrepresentable.
        before = ds.stop_distance_px
        es._check_for_retest(_frame([(705.50, 706.21, 705.40, 705.90),
                                     (705.90, 706.00, 705.80, 705.95)]))
        check("S2b the distance does not move when price walks to the stop",
              abs(es._data.stop_distance_px - before) < 1e-9,
              f"{before:.4f} -> {es._data.stop_distance_px:.4f}")
    else:
        check("S2 the break freezes the boundary-to-wick distance both ways",
              False, "stop_distance_px does not exist")
        check("S2b the distance does not move when price walks to the stop",
              False, "stop_distance_px does not exist")

    # ── S3 — a TOUCH of the boundary is a valid retest ───────────────────
    # Operator, 2026-09-01: "a touch is acceptable as a re-enter, we are just
    # making sure the level is respected before committing." The BODY test is
    # unchanged and still demands open AND close outside.
    e = _armed_engine("short")
    e._check_for_retest(_frame([(705.90, 706.21, 705.80, 706.00),
                                (706.00, 706.10, 705.90, 706.05)]))
    check("S3 a wick that TOUCHES the boundary confirms the retest",
          e._data.state == ORBState.OPEN_SHORT, f"state={e._data.state}")

    # ⚠️ AND THE BODY RULE IS NOT LOOSENED WITH IT. A candle whose body closes
    # back inside is a DISARM, not a near-miss.
    e2 = _armed_engine("short")
    e2._check_for_retest(_frame([(705.90, 706.50, 705.80, 706.40),
                                 (706.40, 706.50, 706.30, 706.45)]))
    check("S3b a body back inside the range invalidates, never confirms",
          e2._data.state == ORBState.INVALIDATED
          and e2._data.invalidation_reason == "close_inside",
          f"state={e2._data.state} reason={e2._data.invalidation_reason}")

    # ── S4 — a spent confirmation constructs nothing ─────────────────────
    # EXECUTED through the real generate_signal, not asserted from source.
    try:
        from strategy import plan as P
        from strategy.orb_strategy import ORBStrategy

        class _Store:
            def __init__(self):
                self.conn = sqlite3.connect(":memory:")
                self.conn.row_factory = sqlite3.Row

            def commit(self):
                self.conn.commit()

        st = _Store()
        P.ensure_tables(st)
        P.bind_store(st)
        strat = ORBStrategy()
        eng = _armed_engine("short")
        eng._check_for_retest(_frame([(705.90, 706.21, 705.80, 706.00),
                                      (706.00, 706.10, 705.90, 706.05)]))
        d = eng._data
        d.confirmation_seq = 1        # r235 — a retest happened
        d.order_placed = True
        d.order_placed_seq = 1        # …and it already fired
        P.begin_tick()
        sig = strat.generate_signal(orb=d, ms=None, vol_state=None,
                                    chain=None, macro=None,
                                    current_price=705.90, now_hhmm="10:00")   # r220: a plan with no clock is dormant
        P.close_tick(st, "TEST")
        # ⚠️ `sig is None` ALONE IS NOT THE PROOF, and at r206 it passes for an
        # unrelated reason (no chain, so the strike never resolves). The claim
        # is that it refused AT THIS GATE, so the plan row has to say so —
        # otherwise this check is green against the version it was written to
        # catch, which is WORKING_AGREEMENT 0.4 exactly.
        row = st.conn.execute(
            "SELECT verdict, reason FROM plan_tick ORDER BY ts_epoch DESC "
            "LIMIT 1").fetchone()
        why = (row["reason"] or "") if row else ""
        # ⚠️ r235 — the fixture must set the SEQS, not the bare boolean. Setting
        # only `order_placed` no longer refuses, and the check would then fall
        # through to the liquidity analysis and die on a None map — a red for
        # the wrong reason, which is the CV.1 failure.
        check("S4 a spent confirmation is refused AT THAT GATE, not incidentally",
              sig is None and why.startswith("order_already_placed"),
              f"signal={sig!r} verdict={row['verdict'] if row else None} why={why!r}")
    except Exception as exc:                                    # noqa: BLE001
        # ⚠️ A CHECK THAT CANNOT RUN IS A FAILURE, NOT A SKIP. r205's first
        # cut reported "could not execute" and gated nothing.
        check("S4 a confirmation that already placed an order returns no signal",
              False, f"could not execute: {exc}")

    # ── S5 — a re-arm clears the latch AND the geometry ──────────────────
    eng = _armed_engine("short")
    eng._data.confirmation_seq = 1        # r235
    eng._data.order_placed = True
    eng._data.order_placed_seq = 1        # r235
    eng._rearm()
    check("S5 _rearm clears the spent latch so the next attempt is clean",
          getattr(eng._data, "order_placed", None) is False
          and float(getattr(eng._data, "stop_distance_px", -1.0)) == 0.0,
          f"order_placed={getattr(eng._data, 'order_placed', 'ABSENT')} "
          f"stop_distance_px={getattr(eng._data, 'stop_distance_px', 'ABSENT')}")

    # ⚠️ AND IT KEEPS THE RANGE. A re-arm that forgot the range would make the
    # next attempt impossible rather than clean.
    check("S5b _rearm keeps the range and lands in AWAITING_RANGE_REENTRY",
          eng._data.orb_high == 707.70 and eng._data.orb_low == 706.21
          and eng._data.state == ORBState.AWAITING_RANGE_REENTRY,
          f"state={eng._data.state}")

    # ── S6 — both survive a restart ──────────────────────────────────────
    # r103 makes orb_state.json AUTHORITATIVE. A latch that does not persist
    # lets a bake mid-setup re-fire a trigger that already produced an order,
    # which is WORKING_AGREEMENT 37 broken by restart.
    import json
    import tempfile
    eng = _armed_engine("short")
    eng._check_for_retest(_frame([(705.90, 706.21, 705.80, 706.00),
                                  (706.00, 706.10, 705.90, 706.05)]))
    eng._data.confirmation_seq = 1        # r235
    eng._data.order_placed = True
    eng._data.order_placed_seq = 1        # r235
    snap = eng.state_snapshot(705.9)
    from analysis.orb_engine import ORBEngine
    with tempfile.TemporaryDirectory() as td:
        pth = os.path.join(td, "orb_state.json")
        with open(pth, "w") as f:
            json.dump(snap, f)
        fresh = ORBEngine()
        loaded = fresh.load_state_file(pth)
    check("S6 the spent latch and the frozen distance survive a restart",
          loaded and getattr(fresh._data, "order_placed", False) is True
          and abs(float(getattr(fresh._data, "stop_distance_px", 0.0))
                  - eng._data.stop_distance_px) < 1e-9,
          f"loaded={loaded} order_placed={getattr(fresh._data, 'order_placed', 'ABSENT')} "
          f"dist={getattr(fresh._data, 'stop_distance_px', 'ABSENT')}")

    # ── S7 — the dispatch asks the ENGINE, not the tick's copy ───────────
    mainsrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    tree = ast.parse(mainsrc, "main.py")
    binds_ctx = binds_engine = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "orb"):
            continue
        v = node.value
        # `orb = ctx["orb"]` — the stale binding
        if (isinstance(v, ast.Subscript) and isinstance(v.value, ast.Name)
                and v.value.id == "ctx"):
            binds_ctx = True
        # `orb = get_orb_engine().data` — the live one
        if isinstance(v, ast.Attribute) and v.attr == "data":
            f = v.value
            if (isinstance(f, ast.Call) and isinstance(f.func, ast.Name)
                    and f.func.id == "get_orb_engine"):
                binds_engine = True
    check("S7 the ORB dispatch binds the engine's data, never ctx['orb']",
          binds_engine and not binds_ctx,
          f"engine={binds_engine} ctx={binds_ctx}")

    # ── S8 — THE SIZER READS ENTRY-TO-STOP, AND NOTHING SIZES OFF THE
    #         RECORDED GEOMETRY ─────────────────────────────────────────────
    # 🔴 THIS CHECK ASSERTED THE OPPOSITE IN AN INTERMEDIATE CUT OF r207, and
    # the operator caught it before it landed: *"The true risk is based on
    # where we entered though, not the range boundary. That's arbitrary. The 2
    # factuals are the distance from entry to the stop."* The stop is a PRICE
    # LEVEL, so the risk is the gap between the FILL and it; the boundary is
    # where the candle started. `stop_distance_px` answers r119's separate
    # question and is RECORDED ONLY.
    # ⚠️ THE SECOND HALF IS THE ONE THAT HAS TO HOLD OVER TIME. r119 shipped
    # `stop_width_pct`/`planned_r` recorded-not-graded with a G4 that fails if
    # anything ever reads them, precisely because an observation wired into a
    # decision before the data has spoken looks reasonable in review. Same
    # shape here: this is the assertion that goes red when someone sizes off
    # the frozen field "since it already knows".
    sizes_from_entry = sizes_from_frozen = False
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "_orb_d"):
            continue
        names = {n.value for n in ast.walk(node) if isinstance(n, ast.Constant)
                 and isinstance(n.value, str)}
        if {"underlying_entry", "underlying_stop"} <= names:
            sizes_from_entry = True
        if "orb_stop_distance_px" in names:
            sizes_from_frozen = True
    check("S8 the ORB sizer measures entry-to-stop, never boundary-to-wick",
          sizes_from_entry and not sizes_from_frozen,
          f"entry_to_stop={sizes_from_entry} frozen={sizes_from_frozen}")

    # ⚠️ AND NOTHING ANYWHERE IN THE DECISION PATH READS IT. r119's G4 made
    # literal: the field may be written and read for the record, but a strategy
    # or the sizer reading it is the wiring-an-observation-into-a-decision
    # failure. `orb_strategy` records it through `t.check(...)`, which is the
    # plan table and not a decision, so that call is the one exemption.
    _readers = []
    for rel in ("main.py", os.path.join("risk", "risk_manager.py"),
                os.path.join("execution", "entry_engine.py")):
        src = open(os.path.join(_root, rel), encoding="utf-8").read()
        for node in ast.walk(ast.parse(src, rel)):
            if (isinstance(node, ast.Constant) and node.value == "orb_stop_distance_px"):
                _readers.append(rel)
    check("S8b nothing in the sizing or entry path reads the recorded geometry",
          not _readers, f"readers: {sorted(set(_readers)) or 'none'}")

    # ── S9 — ORB reaches the offer path in BOTH modes ────────────────────
    # The ORDER of the two guards is the whole defect, so the check is about
    # order and not presence: both tests existed at r206.
    ee = os.path.join(_root, "execution", "entry_engine.py")
    fn = _fn_source(ee, "_place_single_leg")
    order = []
    if fn is not None:
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            t = node.test
            if (isinstance(t, ast.Call) and isinstance(t.func, ast.Name)
                    and t.func.id == "_is_standing_offer"):
                order.append(("offer", node.lineno))
            if isinstance(t, ast.Attribute) and t.attr == "paper_trading":
                order.append(("paper", node.lineno))
    order.sort(key=lambda x: x[1])
    check("S9 _place_single_leg tests the standing offer BEFORE paper",
          [k for k, _ in order][:2] == ["offer", "paper"],
          f"order={[k for k, _ in order]}")

    # ── S10 — paper fills the whole offer, and reads no strike ───────────
    from execution import resting_orders as _ro
    row = {"offered_qty": 12, "direction": "short", "structure_stop": 706.81,
           "strike": 705.0, "last_seen_qty": 0}
    got_far = _ro._filled_qty("X", row, paper=True, price=650.0)
    got_near = _ro._filled_qty("X", row, paper=True, price=709.0)
    check("S10 paper fills the whole offer at any price",
          got_far == 12 and got_near == 12,
          f"far={got_far} near={got_near} (want 12/12)")

    # ── S11 — every break in the sequence constructs nothing ─────────────
    from analysis.orb_engine import ORBEngine as _E
    e = _E()
    e._data.orb_high, e._data.orb_low, e._data.orb_width = 707.70, 706.21, 1.49
    e._data.state = ORBState.WAITING_FOR_BREAK
    # a candle that OPENS OUTSIDE never broke out of the range
    e._check_for_break(_frame([(705.00, 705.20, 704.40, 704.60),
                               (704.60, 704.70, 704.30, 704.50)]))
    check("S11 a candle that opens outside the range does not arm",
          e._data.state == ORBState.WAITING_FOR_BREAK, f"state={e._data.state}")

    e = _armed_engine("short")
    # ran to the 50% TP with no retest — the runaway hands off, it never fires.
    # OTV4TEST r3 (orb_engine v4.13): a runaway is a CLOSE beyond the 50 that
    # HOLDS — two closed bars through update()'s order — never a wick.
    for rows in ([(705.40, 705.50, 705.00, 705.10), (705.10, 705.20, 705.00, 705.05)],
                 [(705.10, 705.20, 705.00, 705.05), (705.05, 705.15, 704.95, 705.00)]):
        e._track_fifty_acceptance(_frame(rows))
        e._check_for_retest(_frame(rows))
    check("S11b a runaway invalidates instead of confirming",
          e._data.state == ORBState.INVALIDATED
          and e._data.invalidation_reason == "runaway",
          f"state={e._data.state} reason={e._data.invalidation_reason}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_orb_sequence: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
