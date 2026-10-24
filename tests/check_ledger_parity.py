#!/usr/bin/env python3
"""
tests/check_ledger_parity.py  v1.6
v1.6  2026-10-24  OTV5 r0 — A FRESH LEDGER HAS NO KNOWN HOLES. The two allow-lists (KNOWN_UNLANDED, KNOWN_ROWLESS_CITATIONS)
      named revision numbers of another ledger and would have excused real orphans at those numbers here; both are empty.
      Cross-repo citations (OTV4TEST rN, otv4 rN, mainline rN, dtp rN) are stripped before L3 looks for bare numbers.
      This closes the fork's HYG.3 (the gate read a frozen ledger): docs/GENESIS.md IS this tree's ledger.
v1.5  2026-09-08  r318 — r316 JOINS THE KNOWN-ROWLESS SET, AND THE LAND ORDER
      IS WHY NOBODY SAW IT. r316 was cut and never landed (it bundled r317's
      work with r315's; r315 landed first and made its BASE stale), so r317's
      own GENESIS row explains the spent number by name — and that citation
      made L3 red the instant it was appended. EXACTLY the r226 case, allowed
      for exactly the r226 reason: the citation is the RECORD of why the
      number is missing, not evidence of a lost row.
      🔴 THE LAND GATE COULD NOT HAVE CAUGHT IT. `land.sh` runs the CHECK
      lines, then regenerates the maps, then appends GENESIS — so every check
      runs against a ledger that does not yet contain the row being landed.
      A DESC that cites a rowless number therefore lands GREEN and the red
      appears on the next run, with nothing tying it to the delivery that
      caused it. r317 reported `check_ledger_parity PASS` and left origin red.
      Recorded as DOC.20; the ordering itself is the operator's call.
v1.4  2026-09-08  r317 — L7: NO ID CARRIES TWO BYTE-IDENTICAL ROWS. Four did
      (ORB.3 x3, ORB.4 x3, S3.1 x2, S3.6 x2) and every existing check passed
      over them, because L1/L5/L6 test for the CONTRADICTION case and
      identical copies contradict nothing. Scoped to VERBATIM copies only:
      differing rows per id are the ledger's own per-revision idiom.
v1.3  2026-09-08  r317 — 🔴 L3 READ day_trader_pro's REVISION NUMBERS AS THIS
      REPO'S, AND HAS SINCE THE TWO SEQUENCES OVERLAPPED. `\br305\b` matches
      the "dtp r305" in an otv4 row, so a CROSS-REPO citation counted as a
      same-repo one. otv4's GENESIS cites 31 distinct dtp revisions and 28 of
      them HAPPEN to collide with a real otv4 row number, so the check stayed
      quiet by luck; only 305, 309 and 316 fall outside otv4's range, and
      those three are the entire red. It now requires the citation to be
      un-prefixed.
      ⚠️ THE TEMPTING FIX WAS THE WRONG ONE. Adding 305/309/316 to
      `KNOWN_ROWLESS_CITATIONS` turns the board green and leaves the check
      measuring the wrong thing — it would go quiet until dtp's numbering next
      escapes otv4's range, and the allow-list is for holes this repo cannot
      explain, not for a pattern that never applied. Same class as the r230
      finding: a rule pointing at the wrong thing is worse than no rule.
      ⚠️ AND THE COLLISION IS NOT HYPOTHETICAL IN THE OTHER DIRECTION — with
      28 numbers shared, any genuine otv4 hole whose number a dtp citation
      happens to mention was equally invisible. Whether one is hiding under
      the fix is now answerable, and the run below says: none.
v1.2  2026-09-04  r245 — 🔴 THE OPEN LIST MATCHES THE STATE MARKER,
      NOT THE WORD. It asked whether "OPEN" appeared anywhere in the state
      cell, and the older rows carry a long `◐ PUSHED…` narrative there
      containing "OPENED" and "opening" — so CLOSED items read as open, TEN
      false positives out of 25. I recommended work on BFLY.2 as though it
      were live and then argued from a defect r197 had already fixed.
      ⚠️ THIRD INSTRUMENT TO MISLEAD IN ONE EVENING, after the stop-forensics
      count and its verdict line. All three read a proxy instead of the
      thing itself. L6 pins the five markers against a fixture.
v1.1  2026-09-04  r241 — r226 JOINS THE KNOWN-ROWLESS SET. r240's own
      GENESIS row cites it by name while explaining that it rebuilds it, so
      the citation became "cited but rowless" the moment r240 landed — caught
      by this checker the same day it was written. The citation IS the record
      of why the number is missing, not evidence of a lost row.
v1.0  2026-09-04  r240 — THE TWO LEDGERS MUST AGREE, AND THE BACKLOG MUST BE
      ABLE TO ANSWER "WHAT IS OPEN". Both had stopped being true.

🔴 MEASURED at 45988b6 (BACKLOG v1.57, GENESIS 226 rows, r1..r239):
  • 25 rows read `🔲 OPEN`, and FOUR of those ids — SWEEP.2, SWEEP.3, SWEEP.4,
    TCS.8 — also carry a later `✅ CLOSED` row. Entries are per-revision and
    append-only, so closing an item leaves its earlier OPEN row in place.
    SWEEP.2 appears on FOUR rows. Roughly a third of the open list was wrong.
  • r226 is CLAIMED BY A BACKLOG ENTRY and has NO GENESIS ROW. §35: a revision
    absent from the ledger did not happen.
  • GENESIS skips 13 numbers (r42, 49, 89, 97, 109, 110, 111, 117, 123, 141,
    151, 159, 226). Nine are absent everywhere — allocated and never used,
    which is fine. THREE are cited in GENESIS prose by other revisions
    (r110, r141, r159) but have no row of their own, which is not.

⚠️ THE POINT IS NOT TIDINESS. Every prioritisation starts by reading the open
list, and a list that is a third wrong sends the next session at work that is
already done. This checker makes that state a RED rather than a discovery.
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def _docs():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return (open(os.path.join(root, "docs", "GENESIS.md"), encoding="utf-8").read(),
            open(os.path.join(root, "docs", "BACKLOG.md"), encoding="utf-8").read())


def item_rows(bl):
    """(id, state) for every backlog table row that declares an item."""
    return [(m.group(1), m.group(3).strip()) for m in
            re.finditer(r'^\|\s*\*\*([A-Z]+\.\d+)\*\*\s*\|(.*?)\|\s*([^|]*?)\s*\|\s*$',
                        bl, re.M)]


def open_items(bl):
    """The ids that are ACTUALLY open, newest state per id.

    🔴 THE FILE IS NEWEST-FIRST. Entries are PREPENDED — v1.57 sits at the top
    and v1.0 at the bottom — so the FIRST row for an id is its most recent
    state, not the last. The first cut of this helper took the last and
    reported SWEEP.2/3/4 as open when they had been closed at r231/r234: the
    exact error it exists to catch, made while catching it.
    """
    """
    🔴 MATCHED ON THE STATE MARKER, NOT THE WORD. The first cut asked whether
    "OPEN" appeared anywhere in the state cell — and the older rows carry a
    long `◐ PUSHED…` narrative in that cell containing "OPENED" and "opening",
    so CLOSED items read as open. BFLY.2 was closed at r197 and I recommended
    work on it as though it were live, then argued from a defect r197 had
    already fixed. The marker is the state; the prose is commentary.
    """
    newest = {}
    for rid, state in item_rows(bl):
        if rid not in newest:          # first occurrence == newest entry
            newest[rid] = state
    return sorted(k for k, s in newest.items() if s.lstrip().startswith("\U0001f532"))


def main():
    gen, bl = _docs()

    # ══ L1 — NO ID IS BOTH OPEN AND CLOSED ════════════════════════════════
    seen = defaultdict(list)
    for rid, state in item_rows(bl):
        seen[rid].append(state.upper())
    contradictory = sorted(k for k, v in seen.items()
                           if any("CLOSED" in s for s in v)
                           and any("OPEN" in s and "CLOSED" not in s for s in v))
    check("L1 no item carries both an OPEN row and a CLOSED row",
          not contradictory, ", ".join(contradictory))

    # ══ L2 — EVERY BACKLOG ENTRY HAS A GENESIS ROW ════════════════════════
    # 🔴 §35: a revision absent from the ledger did not happen. The backlog is
    # not the ledger, so a revision it claims and GENESIS does not is a claim
    # with no record behind it.
    gen_rows = set(re.findall(r'^\| \*\*(r\d+)\*\*', gen, re.M))
    claimed = set(re.findall(r'^\*\*v[\d.]+ — [\d-]+ — (r\d+)', bl, re.M))
    # ⚠️ r226 IS A KNOWN, EXPLAINED HOLE AND IS ALLOWED BY NAME. It was cut on
    # 2026-09-03 and NEVER LANDED — no commit for it exists on any branch —
    # and its BACKLOG entry reached git only because `docs/BACKLOG.md` ships in
    # every archive, so r227 (the urgent "did you brick my ORB" fix) carried
    # the already-written entry along with its own. r240 rebuilds the change
    # and the v1.58 entry records the history. Allowed BY NAME, not by
    # loosening the rule: a second orphan still fails.
    KNOWN_UNLANDED = set()           # v1.6: a fresh ledger; add a number here only with its row-less story
    # ⚠️ THE NEWEST ENTRY IS EXEMPT, BY CONSTRUCTION. `land.sh` appends the
    # GENESIS row at LAND time, so the backlog entry for the revision being cut
    # always exists first. Demanding a row for it would fail on every single
    # delivery, and a check that is red by design is a check that gets ignored.
    # Scoped to ONE — the highest-numbered claim — so a second unlanded entry
    # still fails.
    # ⚠️ EVERYTHING PAST THE LEDGER'S END IS IN FLIGHT, not just one. The first
    # cut exempted only the highest-numbered claim, assuming one delivery at a
    # time — and went red the moment three were cut in an evening and none had
    # landed. A revision NUMBERED ABOVE the last GENESIS row cannot have a row
    # yet by definition; one numbered BELOW it and missing is a real orphan,
    # which is what r226 was.
    _last_landed = max((int(r[1:]) for r in gen_rows), default=0)
    _in_flight = {r for r in claimed if int(r[1:]) > _last_landed}
    orphan = sorted(claimed - gen_rows - KNOWN_UNLANDED - _in_flight,
                    key=lambda r: int(r[1:]))
    check("L2 every revision the BACKLOG claims has a GENESIS row",
          not orphan, ", ".join(orphan))

    # ══ L3 — NO REVISION IS CITED IN PROSE WITHOUT A ROW ══════════════════
    # ⚠️ A citation to a revision with no row is a reference to something the
    # ledger says never happened — either the row was lost or the citation is
    # wrong, and both are worth knowing. Scoped to the numbers actually MISSING
    # from the sequence, so an ordinary backward citation does not trip it.
    nums = sorted(int(r[1:]) for r in gen_rows)
    gaps = [n for n in range(nums[0], nums[-1] + 1) if f"r{n}" not in gen_rows]
    # ⚠️ r110, r141 AND r159 ARE CITED BY LATER REVISIONS AND HAVE NO ROW.
    # Either three rows were lost or three citations point at revisions that
    # never existed; the ledger cannot say which and it is not rewritten to
    # guess. Recorded as DOC.11, allowed by name, and a FOURTH such citation
    # fails — because that would be a new loss rather than an old one.
    # ⚠️ r226 JOINED THIS SET WHEN r240 LANDED, and the checker caught it the
    # same day it was written. r240's own GENESIS row explains that it rebuilds
    # r226 — so citing it by name is CORRECT, and the citation is the record of
    # why the number is missing rather than evidence of a lost row. L2 already
    # allows it as a known unlanded revision; L3 allows the citation for the
    # same reason and by the same name.
    # ⚠️ r316 JOINED THIS SET WHEN r317 LANDED, and it is the r226 case again:
    # r316 was cut, never landed, and re-cut as r317 after r315 made its BASE
    # stale. r317's row says so by name, so the citation is the record of why
    # the number is missing rather than evidence of a lost row. §26: the
    # number is spent and does not come back.
    KNOWN_ROWLESS_CITATIONS = set()  # v1.6: a fresh ledger
    # 🔴 r317 — A CROSS-REPO CITATION IS NOT A CITATION OF THIS LEDGER.
    # otv4 rows routinely say "DOCS ONLY - DEV.5 FILED FOR dtp r305", naming a
    # day_trader_pro revision. `\br305\b` matched it, so L3 demanded an otv4
    # row for a number that belongs to the other repo. 28 of the 31 dtp numbers
    # cited here happen to also be real otv4 rows, which is why this only ever
    # surfaced on the three that fall outside otv4's range.
    _DTP = re.compile(r'(?:dtp|day_trader_pro|OTV4TEST|otv4|mainline)[\s-]*r\d+', re.I)   # v1.6: every other ledger
    _own = _DTP.sub(" ", gen)          # strip cross-repo citations, then look
    cited = [n for n in gaps
             if re.search(rf'\br{n}\b', _own) and n not in KNOWN_ROWLESS_CITATIONS]
    check("L3 no missing revision number of THIS ledger is cited in GENESIS prose "
          "(cross-repo citations excluded)",
          not cited, f"cited but rowless: {cited}")

    # ══ L4 — THE SEQUENCE IS REPORTED, NOT ENFORCED ═══════════════════════
    # ⚠️ NOT A FAILURE. §26 says numbering is sequential and never resets, but
    # a number allocated and abandoned leaves a legitimate hole. This prints
    # the holes so they are visible; only a CITED hole (L3) or a CLAIMED hole
    # (L2) is a defect.
    print(f"        note: {len(gaps)} unused revision number(s): {gaps}")
    check("L4 the ledger is contiguous enough to trust its ordering",
          len(gaps) < 25, f"{len(gaps)} gaps in r{nums[0]}..r{nums[-1]}")

    # ══ L5 — THE OPEN LIST IS COMPUTABLE AND NON-EMPTY ════════════════════
    op = open_items(bl)
    check("L5 the open list resolves to one state per id",
          len(op) == len(set(op)) and op, f"{len(op)} open")
    print()
    print("  OPEN (latest state per id):")
    for rid in op:
        print(f"      {rid}")

    # ══ L6 — THE OPEN LIST MATCHES THE MARKER, NOT THE WORD ══════════════
    # 🔴 r245. The first cut asked whether "OPEN" appeared anywhere in the state
    # cell. The older rows carry a long `◐ PUSHED…` narrative there containing
    # "OPENED" and "opening", so CLOSED items read as OPEN — ten false
    # positives out of 25. I recommended work on BFLY.2 as though it were live
    # and then argued from a defect r197 had already fixed. The marker IS the
    # state; the prose beside it is commentary.
    _fixture = [("A.1", "🔲 OPEN"),
                ("A.2", "◐ **PUSHED.** r197 OPENED C.27 and C.28; the reopening"),
                ("A.3", "✅ **CLOSED r234**"),
                ("A.4", "⬛ superseded — see r231"),
                ("A.5", "📌 RECORDED")]
    _open = sorted(i for i, s in _fixture if s.lstrip().startswith("🔲"))
    check("L6 only the 🔲 row is open", _open == ["A.1"], str(_open))
    check("L6b a PUSHED narrative containing 'OPENED' is NOT open",
          "A.2" not in _open)
    check("L6c and the real list is non-empty and unique",
          op and len(op) == len(set(op)), f"{len(op)} open")

    # ══ L7 — NO ID CARRIES TWO BYTE-IDENTICAL ROWS ════════════════════════
    # 🔴 r317. FOUR IDS DID: ORB.3 and ORB.4 on THREE rows each, S3.1 and S3.6
    # on two — a run of rows present verbatim in both the S3-repoint section
    # and PART 2, in the same order, so a section insert duplicated a block
    # rather than moving it.
    # ⚠️ EVERY OTHER CHECK IN THIS FILE PASSED OVER THEM, AND THAT IS THE
    # POINT. L1/L5/L6 were built for the CONTRADICTION case — an id open in
    # one place and closed in another — and identical copies contradict
    # nothing, so the open list resolved to 19 with the strays sitting in it.
    # A checker cannot see a duplicate it was designed to tolerate.
    # ⚠️ IDENTICAL ONLY, DELIBERATELY. Multiple DIFFERING rows per id are this
    # ledger's own idiom: entries are prepended per revision and a superseded
    # row is struck in place rather than deleted, because rewriting them
    # rewrites history (r245). Flagging those would fire on the correct
    # pattern and train the reader to skip reds — the CV.1 failure. A verbatim
    # copy records nothing a single row does not.
    _rows = {}
    for _i, _l in enumerate(bl.splitlines(), 1):
        _m = re.match(r'\| \*\*([A-Z0-9.]+)\*\* \|', _l)
        if _m:
            _rows.setdefault(_m.group(1), []).append((_i, _l))
    _identical = {k: [i for i, _ in v] for k, v in _rows.items()
                  if len(v) > 1 and len({l for _, l in v}) == 1}
    check("L7 no backlog id carries two BYTE-IDENTICAL rows",
          not _identical, f"duplicated verbatim: {_identical}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 9 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
