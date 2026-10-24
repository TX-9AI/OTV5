#!/usr/bin/env python3
"""
tests/check_fill_basis.py  v1.4
v1.4  2026-09-24  OTV4TEST r128 — F6 AND F6b MOVED, NOT DROPPED (WORKING_AGREEMENT
      38.4). Both grepped the WHOLE of main.py for r220's inline names
      (`_lr.price_for(_lkey`, `_lr.refuse(_lkey`, `_lr.clear(_lkey)`,
      `fill.quantity >= _req_contracts`); mainline r315 moved placement and
      pricing into the ONE shared placer `main._post_credit_vertical`, which
      the entry (`_execute_condor_leg`) and the remainder supervisor both call,
      so the names left and both went red on a correct change. The PROPERTY
      held. They now (a) read the helper's own FunctionDef by AST, docstring
      and comments stripped — the default pricer is `_lr.price_for`, the
      rung is priced as a "sell", `_lr.clear(lkey)` sits under
      `_filled >= contracts` and `_lr.refuse(lkey, ...)` in its else — and
      that `_execute_condor_leg` calls it WITHOUT a pricer override; and (b)
      EXECUTE it with an injected placer/confirmer and the REAL registry
      (tests/check_credit_remainder.py's harness): the posted limit is the
      ladder's rung, not the mark; a non-fill ratchets the walk to the next
      rung; a partial keeps it; a complete fill clears it. The old whole-file
      `'"sell"' in mainsrc` clause was hollow (any "sell" anywhere in main.py
      satisfied it). Also gains the r106 venv bootstrap: the lander runs
      CHECKs under /usr/bin/python3, which has no pandas/pytz.
v1.3  2026-09-03  r234 — RE-DERIVED. F0 asserted "five values" — the
      exact invariant r219 broke by adding a fifth and missing two guard
      returns, which this check could not see because it only drove the
      success path. It now pins the SHAPE, read by name, on the guard path
      too. And the 0.60-wide fixture r219 called "the shape the fleet trades"
      is now REFUSED by the narrow-side bracket, which is r219's own verdict
      ("born at its stop") enforced at selection; F1c pins that refusal and
      names the rung, F1/F1b move to a surviving shape.
v1.2  2026-09-02  r220 — F6/F7: every live entry walks a ladder EXCEPT ORB.
      Credit verticals posted a static limit at `net_credit` and never walked
      it — not exempt, just unwired. ORB's standing offer stays exempt by
      design and F7 guards that carve-out.
v1.1  2026-09-02  r220 — F5 WALKS EVERY STRATEGY'S FILL PATH. r219 fixed the
      prepare layer and TrendCreditSpread undid it at the signal layer:
      `_build_signal` had no credit in scope and recomputed bid/ask three
      hundred lines below the fix. A fix applied at one layer and reversed at
      another looks complete from either end.
v1.0  2026-09-02  r219 — THE ENTRY AND THE MARK WERE ON DIFFERENT SIDES OF THE
      QUOTE, AND THE DIFFERENCE WAS BOOKED AS A LOSS AT FILL.

🔴 `credit_vertical.search_wing` priced the credit as `short.BID - long.ASK`,
and that number became `sig.entry_premium` and therefore the position's entry
of record. `position_manager._fetch_current_premium` marks a credit vertical at
`short.MARK - long.MARK`. Two bases. The gap is BOTH HALF-SPREADS, present the
instant the position opens, with no market movement — and for a credit vertical
a higher mark is a LOSS.

🔑 MEASURED, NOT ARGUED. Sweep forensics over 2026-08-25..09-02: 38 of 41 trades
exited on the lone stop, which carries 60.5 cents of room, while price NEVER
reached the short strike on any of 22 measurable trades and closed only 0.63
points toward it. That move implies a spread delta of 0.96, which a 5-wide
cannot carry. The underlying never explained the loss.

⚠️ OPERATOR RULING, 2026-09-02: "I have a ladder for live offers, all paper
needs to fill at mark, period." So the MARK is booked. The bid/ask credit is
kept for the R hurdle — deciding on the conservative number and booking the
mark refuses trades that only clear R when priced optimistically, so the error
runs in the safe direction.

⚠️ AND THE OLD BEHAVIOUR HAD A PASSING TEST. check_plan_prepares S2 asserted
`net_credit == 1.30` — the bid/ask figure — so the suite certified the mismatch
for the life of the strategy. It is re-derived to 1.33, the mark.

Born red at fd84426 (r218), where F1 and F3 fail.
"""
from __future__ import annotations

import ast
import os
import sys

import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


class _C:
    def __init__(self, k, bid, ask, mark=None):
        self.strike, self.bid, self.ask = float(k), bid, ask
        self.mark = (bid + ask) / 2.0 if mark is None else mark


def main():
    from strategy.credit_vertical import search_wing

    # ⚠️ r234 — THE LEGS NARROW FROM 0.60 TO 0.10, AND THAT IS A FINDING, NOT
    # A CONVENIENCE. r219's original fixture was "the shape the fleet trades":
    # a 0.60-wide short and a 0.60-wide long. Under r234's narrow-side bracket
    # that shape is now REFUSED — stop room 0.69 against a 0.60 short spread
    # needs 1.20 to clear `stop_survivable`'s 2x — which is the correct answer
    # and exactly r219's own conclusion ("the position was born at its stop"),
    # now enforced at selection instead of discovered at the exit. F1/F1b are
    # about the CREDIT BASIS, so they use a shape that survives; F1c pins that
    # the wide one is refused, and names which rung did it.
    short = _C(100.0, 1.20, 1.30)
    long_ = _C(105.0, 0.23, 0.33)
    out = search_wing([short, long_], short, "call", 1.0, r_floor_stop=0.0)

    # 🔴 RE-DERIVED AT r234. "Five values" was the invariant precisely because
    # r219 added a fifth and MISSED two guard returns that still returned four
    # — and this check could not see it, because it only ever drove the
    # success path. A NamedTuple makes arity unrepresentable as a bug: F0 now
    # pins that EVERY return path, including the guards, yields the same type
    # read BY NAME.
    check("F0 search_wing returns a WingResult read by name",
          hasattr(out, "credit") and hasattr(out, "fill")
          and hasattr(out, "r_stop"), type(out).__name__)
    _bad = type(short)(0.0, short.ask, getattr(short, "mark", 0.0), short.strike) \
        if False else None
    class _NoBid:
        strike, bid, ask, mark = 100.0, 0.0, 1.10, 1.05
    _g = search_wing([_NoBid(), long_], _NoBid(), "call", 1.0, r_floor_stop=0.0)
    check("F0b the no-bid GUARD returns the same shape, not a short tuple",
          type(_g) is type(out) and _g.long is None and _g.why,
          f"{type(_g).__name__}: {_g.why}")
    if not hasattr(out, "fill"):
        print()
        print("FAILED 1: pre-r219 shape — the fill credit does not exist")
        return 1
    r, wing, judged = out.r, out.long, out.credit
    width, fill = out.width, out.fill
    # F1c — the wide-spread shape r219 measured is now refused AT SELECTION,
    # by the rung that owns the decision rather than by a later gate.
    _ws, _wl = _C(100.0, 1.20, 1.80), _C(105.0, 0.23, 0.83)
    _wide = search_wing([_ws, _wl], _ws, "call", 1.0, r_floor_stop=0.0)
    check("F1c a stop that cannot clear 2x the short spread is refused",
          _wide.long is None and _wide.why_key == "stop_vs_spread",
          f"{_wide.why_key}: {_wide.why}")

    # ── F1 — THE TWO CREDITS ARE DIFFERENT AND BOTH ARE RETURNED ────────
    check("F1 the booked (mark) credit differs from the judged (bid/ask) one",
          # r234 — the narrower fixture: judged 1.20-0.33 = 0.87 (bid/ask),
          # booked 1.25-0.28 = 0.97 (mark). The GAP is unchanged in meaning,
          # only in size: still exactly the two half-spreads.
          fill is not None and abs(fill - 0.97) < 1e-9
          and abs(judged - 0.87) < 1e-9,
          f"judged {judged} / booked {fill}")

    # 🔑 THE GAP IS EXACTLY BOTH HALF-SPREADS. That is the quantity that was
    # being charged as a loss at fill, and it is the same order as the stop's
    # 60.5 cents of room — the position was born at its stop.
    gap = (fill or 0) - judged
    half = ((short.ask - short.bid) + (long_.ask - long_.bid)) / 2.0
    check("F1b and the gap is exactly the sum of the two half-spreads",
          abs(gap - half) < 1e-9, f"gap {gap:.2f} vs half-spreads {half:.2f}")

    # ── F2 — R IS STILL JUDGED ON BID/ASK ───────────────────────────────
    # ⚠️ IF R MOVED TO THE MARK the hurdle would pass trades that only clear
    # it when priced optimistically. The conservative test is the point.
    # ⚠️ TOLERANCE MATCHED TO THE RETURN, WHICH IS ROUNDED TO 4dp. The first
    # draft used 1e-6 and failed on a 1.4e-5 rounding residual — a check that
    # fails for arithmetic reasons rather than behavioural ones teaches nobody
    # anything and gets suppressed next time it goes red.
    r_judged = judged / (width - judged)
    r_booked = (fill or 0) / (width - (fill or 0))
    check("F2 R is computed from the judged credit, not the booked one",
          abs(r - r_judged) < 5e-5 and abs(r - r_booked) > 1e-3,
          f"R {r:.4f}; judged-basis {r_judged:.4f}, booked-basis {r_booked:.4f}")

    # ── F3 — A LEG WITH NO MARK YIELDS NO FILL PRICE ────────────────────
    # 🔴 SUBSTITUTING THE BID/ASK NUMBER HERE IS THE ORIGINAL DEFECT. Unknown
    # and "use the other basis" are different facts; the callers refuse.
    nm = _C(105.0, 0.23, 0.83)
    nm.mark = None
    # r234 — by NAME, so a future field can never break this line again.
    fill2 = search_wing([short, nm], short, "call", 1.0, r_floor_stop=0.0).fill
    check("F3 a leg without a usable mark returns NO fill credit",
          fill2 is None, str(fill2))

    # ── F4 — NaN IS NOT A MARK ──────────────────────────────────────────
    # ⚠️ safe_float, not float(): every comparison against NaN is False, so a
    # bare conversion would let it through and book a NaN entry premium.
    nan = _C(105.0, 0.23, 0.83)
    nan.mark = float("nan")
    fill3 = search_wing([short, nan], short, "call", 1.0, r_floor_stop=0.0).fill
    check("F4 a NaN mark is not booked as a price", fill3 is None, str(fill3))

    # ── F5 — EVERY FILL PATH BOOKS THE MARK ─────────────────────────────
    # 🔴 r219 FIXED THE PREPARE LAYER AND TCS UNDID IT AT THE SIGNAL LAYER.
    # `_build_signal` had no credit in scope, so it recomputed
    # `short.bid - long.ask` three hundred lines below the fix — and
    # `main.py:2220` hands that to `paper_fill_credit`, whose parameter is
    # named `mark`. A fix applied at one layer and reversed at another looks
    # complete from either end; only walking EVERY strategy's fill path finds
    # it. This check is that walk, kept.
    # ⚠️ SOURCE-LEVEL ON PURPOSE. Constructing six live signals needs six sets
    # of chain, trend and market-state fixtures; the claim here is narrow —
    # no strategy computes its booked price from bid/ask — and that is exactly
    # what the source shows.
    # ⚠️ LINE BY LINE, NO REGEX WITH ESCAPES. Two attempts at this check died
    # on a backslash-n collapsing a level inside a generator — the same trap
    # that broke a shell command earlier today. Iterating lines needs no
    # escapes at all, so there is nothing to get wrong.
    paths = ("orb_strategy.py", "runaway_continuation.py",
             "gex_pin_butterfly.py", "sweep_credit_spread.py",
             "trend_credit_spread.py")
    bad = []
    for fn in paths:
        src = open(os.path.join(_root, "strategy", fn), encoding="utf-8")
        for ln in src.read().splitlines():
            t = ln.strip()
            if t.startswith("#"):
                continue
            if ("net_credit" in t or "entry_premium" in t) and "=" in t \
                    and ".bid" in t and ".ask" in t:
                bad.append(f"{fn}: {t[:56]}")
    check("F5 no strategy books its entry from bid/ask", not bad, "; ".join(bad))

    # ⚠️ AND THE HURDLE MUST STILL USE IT — if bid/ask vanished from
    # credit_vertical entirely, the conservative R test would have gone with it.
    cvsrc = open(os.path.join(_root, "strategy", "credit_vertical.py"),
                 encoding="utf-8").read()
    check("F5b the R hurdle still prices on bid/ask",
          "credit = max(0.0, bid - ask)" in cvsrc)

    # ── F6 — EVERY LIVE ENTRY WALKS A LADDER, EXCEPT ORB ────────────────
    # 🔴 CREDIT VERTICALS POSTED A STATIC LIMIT AND NEVER WALKED IT. Both
    # entry_engine paths price through `_walk_price` -> `ladder_registry`, and
    # ORB is exempt BY DESIGN — `_place_standing_offer`: "ORB only: ONE limit
    # at the mark, posted once, left to rest." The credit verticals were not
    # exempt, just unwired, so a spread that did not fill at `net_credit` sat
    # there instead of conceding.
    # ⚠️ OPERATOR, 2026-09-02: "everything but ORB using ladder entries", and
    # the walk for a credit spread runs FROM THE TOP — best credit first,
    # conceding toward mark, which is where the ladder's own "never posts worse
    # than mark" rule stops it.
    mainsrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    # 🔴 r128 — MOVED, NOT DROPPED. mainline r315 took r220's inline pricing
    # out of `_execute_condor_leg` into ONE shared placer,
    # `_post_credit_vertical`, called by the entry AND the remainder
    # supervisor. The old whole-file greps for `_lr.price_for(_lkey` went red
    # on that correct move, and `'"sell"' in mainsrc` was hollow: ANY "sell"
    # anywhere in main.py satisfied it. Scoped to the helper's own AST now,
    # docstring and comments gone, so prose cannot satisfy it.
    _mtree = ast.parse(mainsrc)
    _fns = {n.name: n for n in ast.walk(_mtree) if isinstance(n, ast.FunctionDef)}
    _pcv = _fns.get("_post_credit_vertical")
    _ecl = _fns.get("_execute_condor_leg")

    def _calls(fn):
        return [n for n in ast.walk(fn) if isinstance(n, ast.Call)] if fn else []

    def _is(call, obj, attr):
        f = call.func
        return (isinstance(f, ast.Attribute) and f.attr == attr
                and isinstance(f.value, ast.Name) and f.value.id == obj)

    _pc = _calls(_pcv)
    _ladder_default = any(_is(c, "_lr", "price_for") for c in _pc)
    _priced_sell = any(isinstance(c.func, ast.Name) and c.func.id == "pricer"
                       and len(c.args) >= 2 and isinstance(c.args[1], ast.Constant)
                       and c.args[1].value == "sell" for c in _pc)
    _entry_calls = [c for c in _calls(_ecl)
                    if isinstance(c.func, ast.Name) and c.func.id == "_post_credit_vertical"]
    _entry_uses_ladder = bool(_entry_calls) and not any(
        k.arg == "pricer" for c in _entry_calls for k in c.keywords)

    # EXECUTED, the way tests/check_credit_remainder.py C2 does it: injected
    # placer/confirmer (no broker), NO pricer — so the default under test is
    # the one the live entry gets — and the REAL ladder registry.
    os.environ.setdefault("OT_PAPER_TRADING", "1")
    _ex = {}
    try:
        import main as _main
        from config import INSTRUMENT as _SYM
        from execution import ladder_registry as _lreg
        from execution.entry_ladder import LadderState as _LS

        class _Q:
            def __init__(self, sym, k, b, a):
                self.symbol, self.strike, self.bid, self.ask = sym, float(k), b, a
                self.mark = (b + a) / 2.0

        class _Fl:
            def __init__(self, filled, qty=0, net=None):
                self.filled, self.quantity, self.net_price = filled, qty, net
                self.order_id, self.detail, self.working_order_id = "F6", "", None

        class _Rsp:
            errors = None
            order = "PLACED"

        _qs, _ql = _Q("SYN P99", 99, 1.00, 1.20), _Q("SYN P94", 94, 0.30, 0.40)
        _stb, _sta = 1.00 - 0.40, 1.20 - 0.30          # structure 0.60 / 0.90
        _box = {}

        def _placer(legs, limit):
            _box["posted"] = limit
            return _Rsp()

        def _confirmer(placed, basis, deadline_s):
            return _box["fill"]

        def _post(q):
            return _main._post_credit_vertical(_qs, _ql, q, _k, "S",
                                               placer=_placer, confirmer=_confirmer,
                                               mark_fallback=0.75)
        _k = "cv:F6:check_fill_basis:put"
        _lreg.reset_all()
        _ref = _LS("sell", _SYM)
        _r1, _ = _ref.next_price(_stb, _sta, structure="S")
        _ref.refuse(_r1)
        _r2, _ = _ref.next_price(_stb, _sta, structure="S")
        _box["fill"] = _Fl(False)
        _ex["l1"] = _post(4)[1]
        _ex["held1"] = _lreg.active() == 1 and _lreg.get(_k, "sell", _SYM).best_refused == _ex["l1"]
        _box["fill"] = _Fl(True, 2, 0.80)               # a PARTIAL: 2 of 4
        _ex["l2"] = _post(4)[1]
        _ex["held2"] = _lreg.active() == 1 and _lreg.get(_k, "sell", _SYM).best_refused == _ex["l2"]
        _box["fill"] = _Fl(True, 2, 0.75)               # the whole of 2
        _post(2)
        _ex["cleared"] = _lreg.active() == 0
        _ex["r1"], _ex["r2"], _ex["mark"] = _r1, _r2, (_stb + _sta) / 2.0
        _lreg.reset_all()
    except Exception as _exc:                                   # noqa: BLE001
        _ex["err"] = f"{type(_exc).__name__}: {_exc}"

    _l1 = _ex.get("l1")
    check("F6 the credit-vertical live order prices through the ladder",
          _pcv is not None and _ladder_default and _priced_sell and _entry_uses_ladder
          and "err" not in _ex and _l1 is not None
          and abs(_l1 - _ex["r1"]) < 1e-9 and abs(_l1 - _ex["mark"]) > 1e-9
          and abs(_l1 - 0.75) > 1e-9,
          _ex.get("err") or f"helper={_pcv is not None} default=_lr.price_for:{_ladder_default} "
          f"sell:{_priced_sell} entry-no-override:{_entry_uses_ladder} "
          f"posted {_l1} vs ladder rung {_ex.get('r1')} / mark {_ex.get('mark')}")

    # 🔑 A LADDER THAT NEVER ADVANCES IS THE STATIC LIMIT WITH A NEW NAME.
    # `refuse` on a non-fill, `clear` on a complete fill — and NOT on a
    # partial, because the remainder is still an open intent.
    _clear_on_full = _refuse_else = False
    for _n in (ast.walk(_pcv) if _pcv else ()):
        if not isinstance(_n, ast.If):
            continue
        _t = _n.test
        if (isinstance(_t, ast.Compare) and isinstance(_t.left, ast.Name)
                and _t.left.id == "_filled" and len(_t.ops) == 1
                and isinstance(_t.ops[0], ast.GtE)
                and isinstance(_t.comparators[0], ast.Name)
                and _t.comparators[0].id == "contracts"):
            _body = [c for s in _n.body for c in ast.walk(s) if isinstance(c, ast.Call)]
            _else = [c for s in _n.orelse for c in ast.walk(s) if isinstance(c, ast.Call)]
            _clear_on_full = any(_is(c, "_lr", "clear") for c in _body) \
                and not any(_is(c, "_lr", "refuse") for c in _body)
            _refuse_else = any(_is(c, "_lr", "refuse") for c in _else) \
                and not any(_is(c, "_lr", "clear") for c in _else)
    _l2 = _ex.get("l2")
    check("F6b a non-fill advances the walk and a full fill ends it",
          _clear_on_full and _refuse_else and "err" not in _ex
          and _ex.get("held1") and _l2 is not None and abs(_l2 - _ex["r2"]) < 1e-9
          and _l2 < _l1 and _ex.get("held2") and _ex.get("cleared"),
          _ex.get("err") or f"clear-under-_filled>=contracts:{_clear_on_full} "
          f"refuse-in-else:{_refuse_else} non-fill kept+ratcheted:{_ex.get('held1')} "
          f"next {_l2} (want {_ex.get('r2')}) partial kept:{_ex.get('held2')} "
          f"full cleared:{_ex.get('cleared')}")

    # ⚠️ AND THE STRUCTURE QUOTE IS BUILT PER LEG. `short.ask - long.bid` is
    # the best credit and `short.bid - long.ask` the worst; their midpoint is
    # `short.mid - long.mid`, exactly what paper books — so live and paper
    # share a floor. Building it from the combined mark plus a shade is
    # limit_ladder v1.1's recorded mistake.
    check("F6c the structure quote is built from the four leg quotes",
          "_sa - _lb" in mainsrc and "_sb - _la" in mainsrc)

    # ── F7 — ORB STAYS EXEMPT ───────────────────────────────────────────
    # ⚠️ THE CARVE-OUT IS DELIBERATE AND MUST SURVIVE. A standing offer that
    # walks is not a standing offer.
    eesrc = open(os.path.join(_root, "execution", "entry_engine.py"),
                 encoding="utf-8").read()
    offer = eesrc[eesrc.index("def _place_standing_offer"):]
    offer = offer[:offer.index("def _place_butterfly")]
    # ⚠️ CODE LINES ONLY. The first draft matched the COMMENT that documents
    # the carve-out — "NO `_walk_price`, NO `ladder_registry`" — and went red
    # on the very prose asserting the property it was checking. Same class as
    # the §20 canaries that keep matching changelog text.
    _code = [l for l in offer.splitlines()
             if l.strip() and not l.strip().startswith(("#", '"', "⚠", "🔑", "🔴"))]
    _code = "\n".join(_code)
    check("F7 ORB's standing offer still does NOT walk",
          "self._walk_price(" not in _code and "_lr.price_for(" not in _code,
          "the carve-out is deliberate: a standing offer that walks is not one")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_fill_basis: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
