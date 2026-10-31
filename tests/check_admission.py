#!/usr/bin/env python3
"""
tests/check_admission.py  v5.2
v5.2  2026-10-31  OTV5 r67 (PARC.4) — PARC LEAVES SPEC AND `ALL` (WA section 38.4): PARC is removed.
      The operator, 2026-10-31: "On PARC, no. It was an idea. It failed. It's done." and "Yes" to removing its code. Every other row unchanged.
v5.1  2026-10-27  OTV5 r46 (PARC.1) — PARC JOINS SPEC AND `ALL`: 11:01-11:03, cap 1, ONE try per session, by ruling (the
      operator, 2026-10-27: "Call it PARC"; "No shadow mode. We're paper. It trades tomorrow."). Restated from the ruling.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.13 2026-10-18  OTV4TEST r292 (GATE.1) — PARK JOINS `ALL`. v1.12 put it in SPEC but not in the list the B-section iterates -
      the r78 defect this header already records - so the B checks and B8 never asked about it (audit 10-18 B2).
v1.12 2026-10-18  OTV4TEST r288 (PARK.1) — PARK JOINS THE TABLE: 11:01-11:03, cap 1, ONE try per session, by ruling (the
      operator, 2026-10-17 18:21 ET: "Trade it ... Call it PARK"). Restated in SPEC from the ruling, not from rules().
v1.11 2026-10-12  OTV4TEST r273 (BFLY.10) — both fly rows RE-POINTED 12:00 -> 13:00, and A8 asserts the ATP fly OUT at 12:59
        and IN at 13:00. r273 (BFLY.10), by ruling - the operator, 2026-10-12: "reduce the fly window to 1300".
THE ADMISSION TABLE, DRIVEN EXHAUSTIVELY (OTV4TEST r35).

v1.10 2026-10-03  OTV4TEST r204 (PREM.2) — ORCS JOINS THE TABLE: 09:45-10:30, cap 2 (one put spread, one call spread).
      The operator, 2026-10-03: "I want to paper trade it Monday." A0, the window edges and the cap loop
      cover it; B8 now names the TWO strategies that carry 2 (the sweep and ORCS).
v1.9  2026-10-02  OTV4TEST r187 (ROSTER.1) — RUNAWAY, HUNT, BREAKOUT and VOLT RE-POINTED 15:40 -> 10:30, by
        ruling: "let's impose a 1029 debit cutoff rule, but exempts the GEX pin fly" (2026-10-02). The ORB row,
        both flies, SWEEP and TCS are unchanged. A8 now asserts those four are IN at 10:29 and OUT at 10:30, the
        ORB still IN at 11:30, and at 15:40 every directional and credit entry OUT (unchanged).

v1.8  2026-09-30  OTV4TEST r179 (BFLY.9) — the ATP fly's window RE-POINTED 11:30 -> 12:00, by ruling. The table said 11:30 while the
        plan itself stayed dormant until 12:00 (measured 2026-09-30); the operator: "12:00 is fine". The SPEC row moves and A8 now
        asserts the ATP fly is OUT at 11:30 and IN at 12:00.
v1.7  2026-09-26  OTV4TEST r149 (EOD.1) — the SPEC and A8 RE-POINTED to the operator's ruling, restated from
        his words: "I wanna extend the debit window to all day" and "1. Stop entries at 1540". ORB, RUNAWAY,
        HUNT, BREAKOUT and VOLT now run 09:35-15:40 (VOLT keeps the ORB's window, as r72 requires). A8's 11:30
        handover no longer exists: at 11:30 the directional five are IN, the TCS is OUT until 11:31, and the ATP
        fly is IN; at 15:40 every directional and credit entry is OUT.

v1.6  2026-09-26  OTV4TEST r148 (WIN.1) — A and A8 RE-POINTED, not loosened. The TCS row is 11:31 because its PLAN has
        refused 11:30 all along ("before TCS_START_ET 11:31 — dormant"): the admitted-but-dormant minute made A8's
        'no gap' untrue in effect while the table said otherwise. A8 now pins the handover as it really runs: the
        morning three and the TCS are all OUT at 11:30 (the ATP fly is IN), and the TCS is IN at 11:31.
v1.5  2026-09-21  OTV4TEST r78 — the caps come BACK: the restated SPEC returns
      ORB/RUNAWAY/HUNT/BREAKOUT/VOLT to 1 and B8 is RE-POINTED A SECOND TIME,
      never loosened, to the operator's own sentence — every strategy capped,
      SWEEP alone at 2. 🔴 BREAKOUT JOINS `ALL`: it sat in SPEC but not in the
      list the B-section iterates, so the one strategy that actually stacked —
      19 positions off one opening range — was the one this checker never
      asked about, silently, since r51. B8b is NEW and keeps r76's None
      sentinel exercised on a SYNTHETIC rule through the real `decide()`,
      because restoring the values is not a reason to let the type rot.
v1.4  2026-09-21  OTV4TEST r76 — the restated SPEC uncaps six strategies and
      B8 is RE-POINTED: it asserted "sweep 2, every other type 1", which r76
      supersedes. UNCAPPED IS TESTED, NOT SKIPPED — B drives real admission
      with 1, 3 and 25 already open.
v1.3  2026-09-21  OTV4TEST r72 — A's restated SPEC gains VOLT at 09:35-11:30,
      from the operator's request rather than from `rules()`. 🔑 THIS CHECK
      WENT RED ON r72 AND THAT IS IT WORKING: it restates the table INSIDE the
      checker by design (r35, §0.4) so a fixture cannot agree with the belief
      under test, which means a NEW STRATEGY MUST make it red. Re-pointed at
      the new contract, never loosened (r33/r43/r64).
v1.2  2026-09-20  OTV4TEST r71 — A's restated SPEC moves SWEEP and TCS to
      15:40, from the operator's 2026-09-20 ruling rather than from `rules()`.
      🔑 THIS CHECK WENT RED ON r71 AND THAT IS IT WORKING. It restates the
      window table INSIDE the checker by design (r35, §0.4) so a fixture cannot
      agree with the belief under test — so a superseded ruling MUST turn it
      red. RE-POINTED AT THE NEW CONTRACT, NOT LOOSENED (r33/r43/r64).
v1.1  2026-09-18  OTV4TEST r51 — A0's restated SPEC gains Breakout, from the
      operator's 2026-09-18 ruling rather than from `rules()`.
v1.0  2026-09-17  OTV4TEST r35 — born red at r34 (5ef833e): `risk/admission.py`
      does not exist there, and neither does any single place that can be asked
      "may this plan hand trigger params to this strategy?". Admission was seven
      mechanisms in four files and nothing enumerated them.

WHAT IS PINNED, and it is the OPERATOR'S TABLE, not a paraphrase of it:
  A1-A7    every strategy's window, at BOTH edges, to the minute
  B1-B7    every strategy's concurrency cap, at cap-1, at cap, and above it
  C1-C2    tries-per-session on the two butterflies; unlimited on the rest
  D1-D6    the INTENT: conflicting theses run together, deliberately
  E1-E4    the universals, each refusing on its own name
  F1-F4    the blocking matrix, BOTH directions, via a config override
  G1-G3    the override path itself — partial overrides cannot blank a rule
  H1-H3    purity: same facts, same verdict; inputs never mutated
  X1-X3    the negatives — no VIX gate, unknown strategies fail CLOSED, and
           EVERY gate in gates() is reachable (a gate nothing can trigger is a
           gate nobody knows works — §17, §20's corollary for canaries)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FAILED = []
RAN = []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    from execution.position_manager import decide, Facts, rules, gates, AdmissionRule
    from execution.position_manager import ORB, RUNAWAY, HUNT, BREAKOUT, SWEEP, TCS, GEXFLY, ATPFLY, VOLT, ORCS

    T = rules()
    # ⚠️ r78 — BREAKOUT WAS IN SPEC BUT NOT IN `ALL`, so every B-section cap
    #    check and B8 itself SKIPPED IT. The one strategy that actually
    #    stacked — 19 positions off one opening range — was the one this
    #    checker never asked about. Added; it is not a new belief, it is the
    #    belief SPEC already held going unexercised since r51.
    ALL = [ORB, RUNAWAY, HUNT, BREAKOUT, SWEEP, TCS, GEXFLY, ATPFLY, VOLT, ORCS, "PARK"]   # r292: PARK was in SPEC, not here (the r78 defect again)

    def ok(strategy, hhmm, **kw):
        return decide(Facts(strategy=strategy, now_et=hhmm, orb_established=True, **kw))

    # ── the operator's table, restated HERE so the checker is not reading the
    #    same dict the code reads. §0.4: a fixture built from the belief under
    #    test cannot fail. These numbers come from his message, not from rules().
    SPEC = {
        ORB:     (((9, 35), (15, 40)), 1, None),   # r149 EOD.1: all day, entries stop 15:40
        RUNAWAY: (((9, 35), (10, 30)), 1, None),   # r187 ROSTER.1: directional debits stop at 10:29
        HUNT:    (((9, 35), (10, 30)), 1, None),   # r187 ROSTER.1: directional debits stop at 10:29
        # r51 (BRK.1) — the operator's 2026-09-18 ruling, restated from his own
        # words: *"I want the orb, hunt, breakout & sweep all able to fire &
        # non-competing"*, same opening range, nothing blocking anything.
        BREAKOUT: (((9, 35), (10, 30)), 1, None),   # r187 ROSTER.1: directional debits stop at 10:29
        # r71 (LATE.1) — the operator's 2026-09-20 ruling, restated from his own
        # words: *"let's just widen the credit trade window to 1540 for entries
        # & make the credit window flatten at 1550"*, because the late
        # institutional moves he is after are placed AFTER the hour at which
        # 0DTE day traders stop opening. These two are the CREDIT strategies and
        # they are the only ones that move; the debit windows below still close
        # at 15:00 because a debit is flattened by the 15:40 ladder and an entry
        # inside its own flatten window is an entry with no hold time at all.
        # r72 — VOLT, THE CONTROL ARM. Restated from the operator's request
        # (2026-09-20: *"construct 1 more trade strategy & plan… as a control
        # group… a window of 0935 to 1130"*), NOT read from rules().
        # ⚠️ ITS WINDOW MUST EQUAL THE ORB'S — a control measured over a
        # different period measures the period. check_volt_plan V1b pins that
        # equality from the other side.
        VOLT:    (((9, 35), (10, 30)), 1, None),   # r187 ROSTER.1: directional debits stop at 10:29
        SWEEP:   (((9, 35), (15, 40)), 2, None),
        TCS:     (((11, 31), (15, 40)), 1, None),   # r148: the minute its plan opens (AFD.1)
        GEXFLY:  (((13, 0), (15, 0)), 1, 1),     # r273: was 12:00
        ATPFLY:  (((13, 0), (15, 0)), 1, 1),     # r273: was 12:00 (r179: was 11:30)
        ORCS:    (((9, 45), (10, 30)), 2, None),  # r204
        "PARK":  (((11, 1), (11, 3)), 1, 1),      # r288 (PARK.1): the ask 11:01-11:02, one per session
    }
    # ⚠️ r76 — CAPS RESTATED FROM THE OPERATOR'S RULING, 2026-09-21: *"With
    # rare exception, there are no blocking TRADES and no maximum number of
    # positions."* None = unlimited. The TWO exceptions carry a number and only
    # those two: VERTICALS (a condor IS two verticals — sweep 2, TCS 1 because
    # it pairs only with a sweep) and the BUTTERFLIES (one per SESSION, r178's
    # 2026-08-28 stack of five in ninety seconds).
    check("A0 the table holds exactly the strategies the box runs",
          set(T) == set(SPEC), f"symmetric difference: {sorted(set(T) ^ set(SPEC))}")

    # ── A — windows, at BOTH edges, to the minute ───────────────────────────
    def minus(hhmm):
        t = hhmm[0] * 60 + hhmm[1] - 1
        return (t // 60, t % 60)

    for s in ALL:
        (start, end), _cap, _tries = SPEC[s]
        before, at_start, before_end, at_end = minus(start), start, minus(end), end
        good = (not ok(s, before) and ok(s, at_start)
                and ok(s, before_end) and not ok(s, at_end))
        check(f"A {s} window {start[0]:02d}:{start[1]:02d}-{end[0]:02d}:{end[1]:02d}, "
              f"half-open at both edges",
              good,
              f"{before}={bool(ok(s,before))} {at_start}={bool(ok(s,at_start))} "
              f"{before_end}={bool(ok(s,before_end))} {at_end}={bool(ok(s,at_end))}")

    check("A8 r149/r187: the ORB IN at 11:30, Runaway/Hunt/Breakout/VOLT IN at 10:29 and OUT at 10:30, the TCS OUT until 11:31, the ATP fly OUT until 13:00 (r273); at 15:40 every directional and credit entry is OUT",
          bool(ok(ORB, (11, 30)))
          and all(bool(ok(x, (10, 29))) and not ok(x, (10, 30)) for x in (RUNAWAY, HUNT, BREAKOUT, VOLT))
          and not ok(TCS, (11, 30)) and bool(ok(TCS, (11, 31))) and not ok(ATPFLY, (12, 59)) and bool(ok(ATPFLY, (13, 0)))
          and not any(ok(x, (15, 40)) for x in (ORB, RUNAWAY, HUNT, BREAKOUT, VOLT, SWEEP, TCS)),
          "directional debits stop at 10:29 (operator 2026-10-02); the TCS's one-minute gap is its plan's own (AFD.1)")

    check("A9 the GEX fly runs to 15:00 (its 14:00 cutoff was raised by ruling)",
          bool(ok(GEXFLY, (14, 30))) and bool(ok(GEXFLY, (14, 59))) and not ok(GEXFLY, (15, 0)),
          "14:30 and 14:59 in, 15:00 out")

    # ── B — concurrency caps. r76: None means UNLIMITED and MOST strategies
    #    are now None, so this tests BOTH contracts rather than assuming a cap.
    for s in ALL:
        (win, cap, _t) = SPEC[s]
        mid = (win[0][0], win[0][1] + 1)
        if cap is None:
            # 🔑 UNCAPPED IS A CONTRACT AND IT IS TESTED, NOT SKIPPED. The
            # operator, 2026-09-21: *"there are no blocking TRADES and no
            # maximum number of positions."* Six strategies carried a silent
            # cap of 1 that refused trades live; proving they now admit deep
            # is the whole point of the ruling.
            deep = [ok(s, mid, open_by_strategy={s: n}) for n in (1, 3, 25)]
            check(f"B {s} UNCAPPED: admits with 1, 3 and 25 already open",
                  all(bool(d) for d in deep),
                  f"1->{bool(deep[0])} 3->{bool(deep[1])} 25->{bool(deep[2])}")
            continue
        below = ok(s, mid, open_by_strategy={s: cap - 1}) if cap > 0 else None
        at = ok(s, mid, open_by_strategy={s: cap})
        over = ok(s, mid, open_by_strategy={s: cap + 3})
        check(f"B {s} cap={cap}: admits at {cap-1} open, refuses at {cap} and beyond",
              bool(below) and not at and not over
              and at.gate == "max_open_of_type" == over.gate,
              f"{cap-1}->{bool(below)} {cap}->{at.gate} {cap+3}->{over.gate}")

    # ⚠️ RE-POINTED TWICE, NEVER LOOSENED (r33/r43/r64). B8 asserted "sweep 2,
    # every other type 1"; r76 superseded that with "only two kinds carry a
    # number"; r78 supersedes THAT, because r76 misread the ruling and 19
    # Breakouts / $78,954 landed off ONE opening range in five minutes. The
    # contract is now the operator's sentence: ONE OF EACH, SWEEP ALONE AT TWO.
    _uncapped = {s for s in ALL if SPEC[s][1] is None}
    check("B8 EVERY strategy is capped, and ONLY the sweep and ORCS carry 2",
          not _uncapped
          and SPEC[SWEEP][1] == 2 and SPEC[ORCS][1] == 2      # r204: ORCS is a put spread and a call spread
          and {SPEC[s][1] for s in ALL if s not in (SWEEP, ORCS)} == {1},
          f"uncapped={sorted(_uncapped)}; "
          f"caps={ {s: SPEC[s][1] for s in ALL} }")

    # 🔑 r76's Optional[int]/None MACHINERY IS KEPT AND STILL TESTED even though
    # no live strategy uses it. r78 restored the VALUES, not the type — deleting
    # the sentinel's only test would let it rot until the next ruling needs it,
    # and `max_tries_per_session` in the same dataclass means None the same way.
    # Driven through REAL admission on a SYNTHETIC rule, per §21: text proves
    # nothing about runtime.
    _unl = dict(T); _unl[ORB] = AdmissionRule(((9, 35), (11, 30)), None)
    _deep = [decide(Facts(strategy=ORB, now_et=(9, 36), orb_established=True,
                          open_by_strategy={ORB: n}), table=_unl)
             for n in (1, 3, 25)]
    check("B8b the None sentinel STILL means unlimited: 1, 3 and 25 all admit",
          all(bool(d) for d in _deep),
          f"1->{bool(_deep[0])} 3->{bool(_deep[1])} 25->{bool(_deep[2])}")

    check("B9 TCS+TCS is impossible, which is the condor rule with no special case",
          ok(TCS, (13, 0), open_by_strategy={TCS: 1}).gate == "max_open_of_type"
          and bool(ok(TCS, (13, 0), open_by_strategy={SWEEP: 1})),
          "TCS+TCS refused, TCS+SWEEP admitted")

    # ── C — tries per session ───────────────────────────────────────────────
    for s in (GEXFLY, ATPFLY):
        mid = (13, 0)
        check(f"C {s} one attempt per session: 0 used admits, 1 used refuses",
              bool(ok(s, mid, tries_used=0))
              and ok(s, mid, tries_used=1).gate == "tries_per_session",
              f"{ok(s, mid, tries_used=1).gate}")
    check("C3 every other strategy is UNLIMITED attempts (r2: ORB uncapped; r3: runaway per break)",
          all(T[s].max_tries_per_session is None for s in (ORB, RUNAWAY, HUNT, SWEEP, TCS))
          and bool(ok(ORB, (10, 0), tries_used=99)),
          "99 attempts still admits")

    # ── D — THE INTENT: conflicting theses run together ─────────────────────
    intent = [
        ("D1 sweep admits with a runaway open", SWEEP, (10, 0), {RUNAWAY: 1}),
        ("D2 ATP admits with a GEX fly open", ATPFLY, (13, 0), {GEXFLY: 1}),
        ("D3 TCS admits with a sweep open", TCS, (13, 0), {SWEEP: 1}),
        ("D4 hunt admits with an ORB open (the paired comparison)", HUNT, (10, 0), {ORB: 1}),
        ("D5 runaway admits with an ORB and a hunt open", RUNAWAY, (10, 0), {ORB: 1, HUNT: 1}),
    ]
    for name, s, hhmm, openmap in intent:
        check(name, bool(ok(s, hhmm, open_by_strategy=openmap)), str(openmap))

    check("D6 NOTHING caps the TOTAL number of open positions",
          bool(ok(SWEEP, (13, 0),
                  open_by_strategy={ORB: 1, RUNAWAY: 1, HUNT: 1, TCS: 1,
                                    GEXFLY: 1, ATPFLY: 1, SWEEP: 1})),
          "seven open, an eighth still admits")

    # ── E — the universals, each refusing on its own name ───────────────────
    check("E1 not a trading day", decide(Facts(ORB, (10, 0), trading_day=False)).gate == "trading_day")
    check("E2 opening range not established",
          decide(Facts(ORB, (10, 0), orb_established=False)).gate == "orb_range")
    check("E3 catastrophic cap",
          decide(Facts(ORB, (10, 0), orb_established=True, cap_intact=False)).gate == "catastrophic_cap")
    check("E4 past the hard close",
          decide(Facts(ORB, (10, 0), orb_established=True, past_hard_close=True)).gate == "hard_close")
    check("E5 the universals are asked of EVERY strategy, not just some",
          all(decide(Facts(s, (13, 0), orb_established=False)).gate == "orb_range" for s in ALL),
          "all seven refuse on orb_range")

    # ── F — the blocking matrix, BOTH directions, through an override ───────
    blocked = dict(T)
    blocked[SWEEP] = AdmissionRule(T[SWEEP].window, T[SWEEP].max_open_of_type,
                          T[SWEEP].max_tries_per_session,
                          blocks=frozenset(), blocked_by=frozenset({RUNAWAY}))
    check("F1 blocked_by: a named strategy being open refuses this one",
          decide(Facts(SWEEP, (10, 0), orb_established=True,
                       open_by_strategy={RUNAWAY: 1}), blocked).gate == "blocked_by")
    check("F2 ...and only the NAMED one — an unnamed open strategy does not block",
          bool(decide(Facts(SWEEP, (10, 0), orb_established=True,
                            open_by_strategy={ORB: 1}), blocked)),
          "ORB open, sweep still admits")

    blocks = dict(T)
    blocks[RUNAWAY] = AdmissionRule(T[RUNAWAY].window, T[RUNAWAY].max_open_of_type,
                           T[RUNAWAY].max_tries_per_session,
                           blocks=frozenset({SWEEP}), blocked_by=frozenset())
    check("F3 blocks: expressed from the OTHER end, it refuses just the same",
          decide(Facts(SWEEP, (10, 0), orb_established=True,
                       open_by_strategy={RUNAWAY: 1}), blocks).gate == "blocks",
          "a half-configured matrix cannot silently do nothing")
    check("F4 the shipped table blocks NOTHING — that is the ruling, not an oversight",
          all(not T[s].blocks and not T[s].blocked_by for s in ALL),
          "every blocks/blocked_by empty")

    # ── G — the override path ───────────────────────────────────────────────
    import config as _cfg
    _had = hasattr(_cfg, "ADMISSION_RULES")
    _old = getattr(_cfg, "ADMISSION_RULES", None)
    try:
        _cfg.ADMISSION_RULES = {GEXFLY: {"max_open_of_type": 3}}
        T2 = rules()
        check("G1 an override changes the named field",
              T2[GEXFLY].max_open_of_type == 3, f"{T2[GEXFLY].max_open_of_type}")
        check("G2 ...and leaves every UNNAMED field of that rule intact",
              T2[GEXFLY].window == T[GEXFLY].window
              and T2[GEXFLY].max_tries_per_session == T[GEXFLY].max_tries_per_session,
              "a partial override cannot blank a rule by omission")
        check("G3 ...and does not touch any other strategy",
              all(T2[s] == T[s] for s in ALL if s != GEXFLY))
    finally:
        if _had:
            _cfg.ADMISSION_RULES = _old
        else:
            delattr(_cfg, "ADMISSION_RULES")

    # ── H — purity ──────────────────────────────────────────────────────────
    f = Facts(SWEEP, (10, 0), orb_established=True, open_by_strategy={RUNAWAY: 1})
    v1, v2 = decide(f), decide(f)
    check("H1 same facts, same verdict — no hidden state", v1 == v2, f"{v1} / {v2}")
    check("H2 the caller's facts are not mutated",
          f.open_by_strategy == {RUNAWAY: 1} and f.strategy == SWEEP)
    # ── H3 — decide() REACHES NOTHING OUTSIDE THE ADMISSION BLOCK ──────────
    # ⚠️ TWO EARLIER CUTS OF THIS CHECK ARE RECORDED RATHER THAN REPLACED.
    # (1) The first read `for m in {}.get(...) and []` — iterating an EMPTY LIST,
    #     so `not any(...)` was true whatever the module imported. §21's failure
    #     inside a checker written to enforce §21.
    # (2) The second imported the module in a clean interpreter and asserted that
    #     NOTHING from strategy/ or execution/ was loaded. That was true while
    #     admission lived in its own file and is FALSE now that it lives in its
    #     right home: `position_manager` has imported `strategy.structure` and
    #     `execution.exit_engine` since long before this (a pre-existing
    #     execution -> strategy edge, position_manager.py:137). Purity-by-module
    #     did not survive the move, and deleting the check to hide that would be
    #     worse than losing it.
    # WHAT STILL MATTERS AND IS STILL TRUE: `decide()` calls nothing outside the
    # admission block. That is what keeps it testable without a tick loop or a
    # store, and what stops the position manager DRIVING the plans — it answers.
    import ast as _ast
    _src = open(os.path.join(ROOT, "execution", "position_manager.py"), encoding="utf-8").read()
    _tree = _ast.parse(_src)
    _decide = next(n for n in _tree.body
                   if isinstance(n, _ast.FunctionDef) and n.name == "decide")
    _allowed = {"rules", "Facts", "Verdict", "_within", "int", "set", "sorted",
                "dict", "frozenset", "len", "str", "float", "bool", "tuple", "getattr"}
    _called = {n.func.id for n in _ast.walk(_decide)
               if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)}
    _attrs = {n.func.attr for n in _ast.walk(_decide)
              if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)}
    check("H3 decide() calls nothing outside the admission block — it answers, it never drives",
          not (_called - _allowed) and not (_attrs - {"get", "items", "keys"}),
          f"calls={sorted(_called - _allowed)} attrs={sorted(_attrs - {'get','items','keys'})}")

    check("H4 eligible_now() exists and never reaches into strategy/ (the one-way flow)",
          "def eligible_now" in _src
          and "import strategy" not in _src.split("def eligible_now")[1].split("def why_not")[0],
          "position manager feeds the plans; it does not call them")

    # ── X — the negatives ───────────────────────────────────────────────────
    src = open(os.path.join(ROOT, "execution", "position_manager.py"), encoding="utf-8").read()
    check("X1 the VIX crisis gate is GONE — a ruling, not an omission",
          "vix" not in [g.lower() for g in gates()]
          and "vix_entries_allowed" not in src.split('"""')[-1],
          f"gates={list(gates())}")
    check("X2 an unknown strategy fails CLOSED — a new trade joins the table or it does not trade",
          decide(Facts("SomethingNew", (10, 0), orb_established=True)).gate == "unknown_strategy")

    # every gate reachable: a gate nothing can trigger is one nobody knows works
    seen = set()
    for s in ALL:
        for kw in ({"trading_day": False}, {"orb_established": False},
                   {"orb_established": True, "cap_intact": False},
                   {"orb_established": True, "past_hard_close": True},
                   {"orb_established": True},
                   {"orb_established": True, "open_by_strategy": {s: 9}},
                   {"orb_established": True, "tries_used": 99}):
            for hhmm in ((3, 0), (10, 0), (13, 0)):
                seen.add(decide(Facts(s, hhmm, **kw)).gate)
    seen |= {decide(Facts("Nope", (10, 0), orb_established=True)).gate}
    seen |= {decide(Facts(SWEEP, (10, 0), orb_established=True,
                          open_by_strategy={RUNAWAY: 1}), blocked).gate,
             decide(Facts(SWEEP, (10, 0), orb_established=True,
                          open_by_strategy={RUNAWAY: 1}), blocks).gate}
    missing = set(gates()) - seen
    check("X3 EVERY gate in gates() is reachable — none is decorative",
          not missing, f"unreached: {sorted(missing)}" if missing else f"{len(gates())} gates")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
