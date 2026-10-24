#!/usr/bin/env python3
"""check_wing_search.py  v1.4
v1.4  2026-09-24  OTV4TEST r128 — RE-POINTED AT WHERE THE CODE LIVES. Fork r5
      moved the sweep's selection into strategy/sweep_plan.py and fork r9 moved
      TCS's into strategy/tcs_plan.py; strategy/sweep_credit_spread.py and
      strategy/trend_credit_spread.py kept the spec prose. Every property below
      is MOVED, NOT DROPPED (WORKING_AGREEMENT 38.4), except one key:
        W2b  cv.search_wing( in sweep_credit_spread.py -> SweepPlan._structure
             calls the shared searcher (AST) AND, executed, picks the wing
             search_wing picks (sweep_plan.py:342).
        W3   the searcher's floor argument is R_FLOOR, bound only by the import
             from strategy.criteria (sweep_plan.py:116, :342).
        W7   "relaxed does not"/"structure, not selection" was refusal TEXT fork
             r5 dropped; the RULE held. Now: the plan's R gate compares against
             R_FLOOR (sweep_plan.py:550) and nothing in the plan consults
             r_hurdle/r_verdict/relaxed_active, which return None/muted under
             relaxed (criteria.py:231).
        W8   sweep_max_age_bars RETIRED BY RULING, not moved — operator
             2026-09-04, "I do not give a rats ass how old the level is, its
             still a level" (criteria.py:299-303, fork r106). W8r pins that it
             stays out of CRITERIA; the docstring's "8->24" is gone.
        W9   sweep -> the search_wing call plus the R_FLOOR gate; TCS -> EXECUTED
             TCSPlan._structure: the WIDEST wing clearing TCS_R_FLOOR_EXPIRY is
             taken and a chain clearing none is refused (tcs_plan.py:118,
             :274-294, `r_expiry < TCS_R_FLOOR_EXPIRY` :286).
      🔴 HOLLOW GREENS FOUND AND FIXED: W3, W10 and W11 read the same spec-only
      files. Their comment filter dropped only '#' lines, so a DOCSTRING
      naming R_FLOOR satisfied "R_FLOOR in code", and "r_hurdle absent" /
      "no fixed-offset lookup" were true only because the code had left. They
      now read sweep_plan.py and tcs_plan.py through ast (comments AND
      docstrings stripped), and each goes red on a mutant of the live code.
      Also gains the r106 venv bootstrap for /usr/bin/python3.
v1.3  2026-09-04  r238 — W9 RE-DERIVED. TCS no longer calls
      `search_wing` — it needs the WIDEST qualifying wing, the opposite search.
v1.2  2026-09-03  r234 — W2 RE-DERIVED. It matched the SOURCE TEXT
      `r > best[0]`, which r234's NamedTuple refactor legitimately removed —
      §21: a check that reads source proves nothing about runtime and goes
      RED on a correct change. It now EXECUTES the search and asserts which
      wing won.
v1.1  2026-08-27  r160: W18 re-pinned — plan_second_leg deleted; authorize()/manage() build nothing. — v1.0

🔴 R IS A CONSTRUCTION TARGET, NOT A FILTER. THE WING IS SEARCHED.

Operator, 2026-08-27: *"strike selection must net r of 1 or better"* and
*"make the r-value a requirement outright... and relax something else to loosen
the entry"* and *"the integrity of the trade mechanics comes first."*

WHAT THIS REPLACES: a single wing at `WING_WIDTH = 5.0` — a FIXED DOLLAR
amount, one strike increment on SPX and SIX on CVX. R was then checked after
the fact and, under relaxed, MUTED. That is how a 6-wide spread collecting
$0.58 (R 0.13) looked normal to the code and got entered SEVENTEEN times.

THE SHORT STRIKE IS STRUCTURAL — it comes from the level and never moves. The
wing is the only free variable, and the tradeoff is monotonic: narrower wing ->
less credit, less risk, HIGHER R. So "the wing that best clears the floor" is
computable, and "no wing does" is a definite answer.

⚠️ MEASURED ON THE CHAIN THAT LOOPED (CVX short put 197.5, bid $0.80):
    wing 196.5 (1.0 wide)  credit 0.20  risk 0.80  R 0.250
    wing 195.5 (2.0 wide)  credit 0.37  risk 1.63  R 0.227
    wing 194.5 (3.0 wide)  credit 0.48  risk 2.52  R 0.190
    wing 192.5 (5.0 wide)  credit 0.58  risk 4.42  R 0.131  <- the old fixed wing
    wing 190.0 (7.5 wide)  credit 0.67  risk 6.83  R 0.098
**No wing clears 1.00.** The trade is refused by STRUCTURE. And the old fixed
$5 wing was the second-worst choice on the board.

⚠️ NOT MUTED BY RELAXED. Relaxed keeps widening the EVIDENCE dials it always
did (sweep_pierce_ceiling 0.25->0.75, level_hold_min 0.75->0.50; the age
dial is retired by the 2026-09-04 ruling); it no longer waives the economics. `R_FLOOR` is read directly,
NOT through `r_hurdle()`, which returns None under relaxed.

⚠️ EXPECTED CONSEQUENCE, STATED UP FRONT: relaxed now produces FEWER trades,
not more. Every setup must find a wing that pays for its own risk. That is the
cost of the trade being real, and the operator accepted it explicitly.
"""
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


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def _best_wing(short_bid, short_strike, wings, side="put"):
    """Mirror of the search, used only to state the arithmetic in the checks."""
    best = None
    for k, ask in wings:
        w = abs(short_strike - k)
        cr = max(0.0, short_bid - ask)
        rk = w - cr
        if cr <= 0 or rk <= 0:
            continue
        r = cr / rk
        if best is None or r > best[0]:
            best = (r, k, cr, w)
    return best


# ── r128 — CODE, NOT PROSE ───────────────────────────────────────────────
# Comments AND docstrings stripped through ast: a docstring naming R_FLOOR
# satisfied the old line filter, which is how W3/W10 stayed green on files the
# code had left.
_MUTED = ("r_hurdle", "r_verdict", "relaxed_active")


def _tree(rel):
    return ast.parse(open(os.path.join(_root, rel), encoding="utf-8").read())


def _code(tree):
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            b = n.body
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) \
                    and isinstance(b[0].value.value, str):
                n.body = b[1:] or [ast.Pass()]
    return ast.unparse(tree)


def _method(tree, cls, name):
    for c in tree.body:
        if isinstance(c, ast.ClassDef) and c.name == cls:
            for f in c.body:
                if isinstance(f, ast.FunctionDef) and f.name == name:
                    return f
    return None


def _idents(node):
    """Every identifier referenced: bare names, attributes and imported names."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.alias):
            out.add(n.name.split(".")[-1])
            if n.asname:
                out.add(n.asname)
    return out


def _floor_bound_by_criteria(tree, name):
    """`name` is imported from strategy.criteria and never re-bound."""
    imported = any(isinstance(n, ast.ImportFrom) and n.module == "strategy.criteria"
                   and any(a.name == name and a.asname is None for a in n.names)
                   for n in ast.walk(tree))
    rebound = any(isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Store)
                  for n in ast.walk(tree))
    return imported and not rebound


def _compares_to(node, name):
    return [n for n in ast.walk(node) if isinstance(n, ast.Compare)
            and any(isinstance(x, ast.Name) and x.id == name
                    for x in [n.left] + list(n.comparators))]


def _search_calls(node):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "search_wing"
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "cv"]


def _floor_arg(call):
    if len(call.args) >= 4:
        return call.args[3]
    return next((k.value for k in call.keywords if k.arg == "r_floor"), None)


def _fixed_offset_lookups(node):
    """find_contract_at_strike calls whose strike is anything but a bare name
    other than a long/wing name — i.e. a strike COMPUTED from an offset."""
    bad = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if fname.lstrip("_") != "find_contract_at_strike":
                continue
            arg = n.args[1] if len(n.args) >= 2 else None
            if not (isinstance(arg, ast.Name) and "long" not in arg.id.lower()
                    and "wing" not in arg.id.lower()):
                bad.append(ast.unparse(n))
    return bad


def main():
    from strategy.criteria import R_FLOOR
    _sp_tree = _tree("strategy/sweep_plan.py")
    _sp_code = _code(_tree("strategy/sweep_plan.py"))
    _sp_struct = _method(_sp_tree, "SweepPlan", "_structure")
    _tp_tree = _tree("strategy/tcs_plan.py")
    _tp_code = _code(_tree("strategy/tcs_plan.py"))
    _tp_struct = _method(_tp_tree, "TCSPlan", "_structure")
    src = open(os.path.join(_root, "strategy", "sweep_credit_spread.py"),
               encoding="utf-8").read()
    code = "\n".join(l for l in src.split("\n")
                     if not l.strip().startswith("#"))

    # ── 🔴 W1 — THE FIXED WING IS NO LONGER THE SELECTION ────────────────
    # ⚠️ Match CODE, not the comment explaining the removal.
    check("W1 the wing is not a single fixed-width lookup",
          "_long = cv.find_contract_at_strike(_contracts, _long_strike)"
          not in code)
    # ⚠️ r157 — the search lives in `credit_vertical.search_wing`, ONE
    # implementation shared by all four credit strategies. Four copies would
    # drift, and the drift would be silent.
    cvsrc = "\n".join(
        l for l in open(os.path.join(_root, "strategy", "credit_vertical.py"),
                        encoding="utf-8").read().split("\n")
        if not l.strip().startswith("#"))
    # 🔴 RE-DERIVED AT r234. This matched the SOURCE TEXT `r > best[0]`, which
    # r234's NamedTuple refactor legitimately removed — WORKING_AGREEMENT §21,
    # a check that reads source proves nothing about runtime and goes red on a
    # correct change. It now EXECUTES: every strike beyond the short is
    # considered, and the winner is the best of them on the gated basis.
    from strategy import credit_vertical as cv

    class _K:
        def __init__(self, k, b, a, m):
            self.strike, self.bid, self.ask, self.mark = k, b, a, m
    _sh = _K(100.0, 1.20, 1.24, 1.22)
    _wings = [_K(95.0, 0.20, 0.23, 0.215), _K(97.0, 0.50, 0.55, 0.525),
              _K(99.0, 0.95, 1.00, 0.975)]
    _res = cv.search_wing([_sh] + _wings, _sh, "put", 1.0)
    _best = max((c for c in _wings),
                key=lambda c: (1.20 - c.ask) / (abs(100.0 - c.strike) - (1.20 - c.ask)))
    check("W2 every strike beyond the short is considered, best wins",
          _res.long is not None and _res.long.strike == _best.strike,
          f"{_res.long and _res.long.strike} vs {_best.strike}")
    # 🔴 r128 — MOVED, NOT DROPPED: fork r5 put the sweep's selection in
    # SweepPlan._structure (sweep_plan.py:342). AST: the call is to the shared
    # `cv.search_wing`; EXECUTED: on W2's chain the plan takes exactly the wing
    # the shared searcher takes (97 — neither the narrowest nor the widest,
    # so a bespoke or fixed-width search picks differently).
    _w2b_exec, _w2b_why = None, ""
    try:
        from strategy import sweep_plan as _spm

        class _Ch:
            puts, calls = [_sh] + _wings, []
        _cand = _spm.Candidate(dict(level_id="W2b", price=100.0, kind="support",
                                    provenance="W2b"))
        _cand = _spm.SweepPlan._structure(_spm.SweepPlan.__new__(_spm.SweepPlan),
                                          _cand, _Ch())
        _w2b_exec = _cand.long is not None and _res.long is not None \
            and _cand.long.strike == _res.long.strike
        _w2b_why = f"plan {_cand.long and _cand.long.strike} vs search_wing {_res.long and _res.long.strike}"
    except Exception as exc:                                    # noqa: BLE001
        _w2b_why = f"{type(exc).__name__}: {exc}"
    check("W2b the sweep calls the SHARED searcher",
          _sp_struct is not None and bool(_search_calls(_sp_struct)) and _w2b_exec,
          _w2b_why)

    # ── 🔴 W3 — R IS READ DIRECTLY, NOT THROUGH THE MUTED HURDLE ─────────
    # `r_hurdle()` returns None under relaxed. If the search consulted it, the
    # floor would vanish in exactly the mode that produced the loop.
    # 🔴 r128 — was HOLLOW: "R_FLOOR" in sweep_credit_spread.py matched a
    # docstring and "r_hurdle" was absent because the code had left. Now the
    # floor the searcher is HANDED is R_FLOOR itself, imported from
    # strategy.criteria and never re-bound (sweep_plan.py:116, :342).
    _fa = [_floor_arg(c) for c in _search_calls(_sp_struct)] if _sp_struct else []
    check("W3 the search reads R_FLOOR, not r_hurdle()",
          bool(_fa) and all(isinstance(a, ast.Name) and a.id == "R_FLOOR" for a in _fa)
          and _floor_bound_by_criteria(_sp_tree, "R_FLOOR"),
          "floor arg: " + ", ".join(ast.unparse(a) if a is not None else "None" for a in _fa))

    # ── W4 — the CVX chain that looped is REFUSED ────────────────────────
    cvx = [(196.5, 0.60), (195.5, 0.43), (194.5, 0.32),
           (192.5, 0.22), (190.0, 0.13)]
    best = _best_wing(0.80, 197.5, cvx)
    check("W4 the CVX 2026-08-27 chain clears no wing",
          best is not None and best[0] < R_FLOOR,
          f"best R {best[0]:.3f} at wing {best[1]} ({best[3]:.1f} wide)")

    # ── W5 — and the OLD fixed wing was not even the best of a bad set ───
    old = [c for c in cvx if abs(197.5 - c[0] - 5.0) < 0.01]
    if old:
        w = abs(197.5 - old[0][0])
        cr = 0.80 - old[0][1]
        check("W5 the old fixed $5 wing was worse than the narrowest",
              cr / (w - cr) < best[0],
              f"fixed {cr/(w-cr):.3f} vs best {best[0]:.3f}")

    # ── W6 — a chain that DOES clear the floor is taken ──────────────────
    # ⚠️ The gate must not be unpassable. A near-the-money short with a tight
    # wing clears 1.00 and must be selected.
    rich = [(197.0, 0.55), (196.0, 0.30), (195.0, 0.15)]
    b2 = _best_wing(1.40, 198.0, rich)
    check("W6 a chain that clears the floor selects a wing",
          b2 is not None and b2[0] >= R_FLOOR,
          f"R {b2[0]:.3f} at wing {b2[1]} ({b2[3]:.1f} wide)")

    # ── W7 — the refusal explains that this is STRUCTURE ─────────────────
    # 🔴 r128 — MOVED, NOT DROPPED. The refusal TEXT went with fork r5; the
    # RULE is what matters: the plan's R gate compares against R_FLOOR
    # (sweep_plan.py:550) and nothing in the plan asks the muted hurdle —
    # `r_hurdle()` returns None under relaxed (criteria.py:231), `r_verdict`
    # rides on it, and `relaxed_active` is the switch itself.
    _rgate = [c for c in ast.walk(_sp_tree) if isinstance(c, ast.Call)
              and isinstance(c.func, ast.Attribute) and c.func.attr == "check"
              and c.args and isinstance(c.args[0], ast.Constant) and c.args[0].value == "r"]
    _rgate_ok = bool(_rgate) and all(
        len(c.args) >= 3 and _compares_to(c.args[2], "R_FLOOR")
        and not (_idents(c.args[2]) & set(_MUTED)) for c in _rgate)
    _muted_here = sorted(_idents(ast.parse(_sp_code)) & set(_MUTED))
    check("W7 the refusal says relaxed does not waive it",
          _rgate_ok and not _muted_here,
          f"r gate on R_FLOOR: {_rgate_ok}; muted hurdle consulted: {_muted_here or 'none'}")

    # ── 🔴 W8 — RELAXED STILL LOOSENS THE EVIDENCE DIALS ─────────────────
    # The trade was not "stop relaxing"; it was "relax evidence, never
    # economics". If CRITERIA ever loses these, relaxed stops doing anything.
    from strategy.criteria import CRITERIA
    # r128 — `sweep_max_age_bars` RETIRED BY RULING, not moved: operator
    # 2026-09-04, "I do not give a rats ass how old the level is, its still a
    # level" (criteria.py:299-303, fork r106). A relaxable pair for a gate
    # that does not exist would advertise a split nothing applies.
    for k in ("sweep_pierce_ceiling", "level_hold_min"):
        check(f"W8 {k} is still a relaxable evidence dial",
              k in CRITERIA and CRITERIA[k][0] != CRITERIA[k][1],
              f"{CRITERIA.get(k)}")
    check("W8r sweep_max_age_bars stays retired (2026-09-04 ruling)",
          "sweep_max_age_bars" not in CRITERIA)

    # ── 🔴 W9 — ALL FOUR CREDIT STRATEGIES, NOT JUST THE SWEEP ───────────
    # r156 shipped the sweep alone; the other three kept fixed dollar wings
    # (TCS_WING_WIDTH_*, CONDOR_WING_WIDTH_*) split only two ways — SPX vs QQQ
    # — so every other symbol took the QQQ number regardless of its price or
    # strike ladder.
    # ⚠️ r158 — `iron_condor_strategy.py` IS NOT IN THIS LIST ANY MORE, and its
    # absence is the point. Operator, 2026-08-27: *"The condor doesn't construct
    # anything."* It builds no spread, so it has no wing to search. W16 below
    # pins that it stays that way — a condor that starts searching wings has
    # started constructing again.
    # 🔴 r128 — RE-POINTED: the selection code lives in sweep_plan.py (fork r5)
    # and tcs_plan.py (fork r9); the two strategy files named here before keep
    # the spec prose, which is why W10/W11 were green without reading code.
    # 🔴 W9 RE-DERIVED AT r238. It asserted every credit strategy CALLS
    # `search_wing` — true until the operator's spec gave TCS the opposite
    # search: `search_wing` maximises R, which drives the wing NARROW, while
    # TCS wants the WIDEST wing still clearing 1:1. The invariant that
    # survives is that the wing is SOLVED for against a declared floor rather
    # than taken from a fixed width.
    _tcs_exec, _tcs_why = False, ""
    try:
        from strategy import tcs_plan as _tpm

        class _T:
            def __init__(self, k, b, a):
                self.strike, self.bid, self.ask = float(k), b, a
                self.mark, self.delta, self.symbol = (b + a) / 2.0, -0.3, f"P{k}"

        def _run(wings):
            class _Ch:
                puts, calls = [_T(100.0, 3.00, 3.01)] + wings, []
            c = _tpm.Candidate(dict(level_id="W9", price=100.0, kind="resistance",
                                    provenance="W9"))
            return _tpm.TCSPlan._structure(_tpm.TCSPlan.__new__(_tpm.TCSPlan), c, _Ch())
        # R at expiry on bid/ask: 99 -> 1.50, 98 -> 1.00, 97 -> 0.76. The
        # widest clearing 1:1 is 98; 97 is wider but below the floor.
        _ok = _run([_T(99.0, 2.35, 2.40), _T(98.0, 1.95, 2.00), _T(97.0, 1.65, 1.70)])
        # nothing clears 1:1 (best 0.67): refused, and named
        _no = _run([_T(99.0, 2.35, 2.60), _T(98.0, 1.95, 2.20), _T(97.0, 1.65, 1.90)])
        _tcs_exec = (_ok.long is not None and float(_ok.long.strike) == 98.0
                     and _ok.r >= _tpm.TCS_R_FLOOR_EXPIRY
                     and _no.long is None and _no.why_key == "wing_r_best")
        _tcs_why = (f"took {_ok.long and _ok.long.strike} R {_ok.r}; "
                    f"no-clear chain -> {_no.long}, {_no.why_key}")
    except Exception as exc:                                    # noqa: BLE001
        _tcs_why = f"{type(exc).__name__}: {exc}"
    _tcs_floor_decl = any(isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "TCS_R_FLOOR_EXPIRY" for t in n.targets)
        for n in _tp_tree.body)

    _plans = (
        ("sweep_plan.py", _sp_tree, _sp_code, _sp_struct, "R_FLOOR",
         _sp_struct is not None and bool(_search_calls(_sp_struct))
         and _rgate_ok, "search_wing + R gate on R_FLOOR"),
        ("tcs_plan.py", _tp_tree, _tp_code, _tp_struct, "TCS_R_FLOOR_EXPIRY",
         _tcs_floor_decl and _tp_struct is not None
         and bool(_compares_to(_tp_struct, "TCS_R_FLOOR_EXPIRY")) and _tcs_exec,
         _tcs_why),
    )
    for name, tree, code, struct, floor, solved, why in _plans:
        check(f"W9 {name} solves for a wing against a declared floor", solved, why)
        # W10 — the declared floor is READ BY THE SELECTION ITSELF (the
        # `_structure` that solves the wing; a record-only check elsewhere in
        # the file does not count), and the muted hurdle is consulted nowhere
        # in the file (docstrings and comments stripped).
        _reads = struct is not None and floor in _idents(struct)
        _muted = sorted(_idents(ast.parse(code)) & set(_MUTED))
        check(f"W10 {name} reads R_FLOOR, never the muted hurdle",
              _reads and not _muted,
              f"_structure reads {floor}: {_reads}; muted: {_muted or 'none'}")
        # ⚠️ THE FIXED WIDTH MUST NOT DRIVE THE EXECUTED SPREAD. What must
        # never come back is a long strike being LOOKED UP at a fixed offset
        # and traded. The only lookup allowed is the SHORT, at its level strike.
        _bad = _fixed_offset_lookups(tree)
        check(f"W11 {name} does not look up a wing at a fixed offset",
              not _bad, "; ".join(_bad))

    # ── 🔴 W16 — THE CONDOR CONSTRUCTS NOTHING ───────────────────────────
    # Operator, 2026-08-27: *"Condor leg one is not a trade. It's a
    # condition."* / *"nothing in the plan is executable. It's an information
    # layer to feed the strategy and the strategy will execute."*
    # ⚠️ 366 LINES DELETED — `decide()`, `check_leg_triggers()` and
    # `_build_leg_signal()` — plus the 54-line inline builder inside
    # `plan_second_leg`. If any of them return, the condor is a second
    # implementation of a credit vertical again, which is the exact thing
    # Fable was asked to remove and which had ALREADY drifted from the real
    # one (mark instead of bid/ask, fixed wing, no stop_survivable, an R gate
    # relaxed could waive).
    ic2 = open(os.path.join(_root, "strategy", "iron_condor_strategy.py"),
               encoding="utf-8").read()
    ictree = ast.parse(ic2)
    gone = {"decide", "check_leg_triggers", "_build_leg_signal"}
    have = {n.name for n in ast.walk(ictree)
            if isinstance(n, ast.FunctionDef)}
    check("W16 the condor's construction methods are gone",
          not (gone & have), f"still present: {sorted(gone & have) or 'none'}")
    check("W17 the condor never calls search_wing",
          "search_wing" not in ic2)
    # ⚠️ AND IT MUST NOT ASSEMBLE A SIGNAL. A permission carries a side and a
    # level; an OptionsSignal carries contracts. Building one here is how the
    # duplication comes back.
    # r160 — plan_second_leg is DELETED (the condor selects nothing). What
    # remains is authorize() (a side and a reason) and manage() (the ladder
    # row); neither may build a signal.
    _names = {n.name for n in ast.walk(ictree) if isinstance(n, ast.FunctionDef)}
    _mg = next((n for n in ast.walk(ictree) if isinstance(n, ast.FunctionDef)
                and n.name in ("authorize", "manage")), None)
    _bodies = "".join(ast.unparse(n) for n in ast.walk(ictree)
                      if isinstance(n, ast.FunctionDef) and n.name in ("authorize", "manage"))
    check("W18 plan_second_leg is gone; authorize()/manage() exist and build no signal",
          "plan_second_leg" not in _names and {"authorize", "manage"} <= _names
          and "OptionsSignal(" not in _bodies)

    # ── W19 — the permission carries nothing executable ──────────────────
    from strategy.plan import Permission
    _p = Permission(side="put", level=197.5)
    _fields = set(vars(_p))
    check("W19 a Permission carries no contracts, strikes or premium",
          not any(k for k in _fields
                  if "contract" in k or "strike" in k or "premium" in k),
          ", ".join(sorted(_fields)))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_wing_search: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
