#!/usr/bin/env python3
"""check_retention_armed.py — v1.2 (landed r162; R5 re-derived r278)

v1.2  2026-09-14 — OTV4TEST r26 (HYG.9). R2/R3 NO LONGER TAKE THE BOX'S REAL PURGE LOCK.
      `rp.main()` acquires `LOCK_PATH` — `<repo>/data/retention_purge.lock` —
      before it calls the stubbed `purge`, so every run created that file in the
      real checkout and, on a box mid-purge, would have waited on (or held) the
      real lock. Found by running each check alone and watching for the file
      after check_purge_lock's own fix. `LOCK_PATH` now points at scratch for the
      two calls, and R0 asserts the real path is not created (when absent before).

v1.1  2026-09-05 — r278. 🔴 R5 ASSERTED "VACUUM is still not EXECUTED at
      shutdown" AND r255 MADE THAT FALSE ON PURPOSE. It has been red since that
      afternoon and nothing noticed, because these checks only run when a
      `land.spec` names them. THIRD INSTANCE OF THIS CLASS IN ONE DAY — the
      conductor's C7 and the `head -3` truncation were the same shape; this one
      was missed because it lives in the other repo.
      🔑 The property being protected has not changed: **a vacuum must never
      stall the halt.** r255 enforces it by REFUSING when free disk is under the
      live size, rather than by the vacuum being absent. R5/R5b/R5c now pin
      that: it exists, it is gated, and a failure is reported rather than
      raised.

🔴 THE NIGHTLY PURGE MUST ACTUALLY DELETE.

`warehouse/retention_purge.py` shipped DRY BY DEFAULT, armed only by
`OT_RETENTION_APPLY=1`, pending a review of the policy numbers that was never
scheduled. `self_close` called `main([])` — an EMPTY argv, with no environment
set — so **the purge ran dry every night for two months, printed what it WOULD
delete, and deleted nothing.**

⚠️ THE COST, 2026-08-27: `feed_store.db` reached 1.5–1.8 GB per box, the 6.7
GiB roots hit 100%, and the fleet went blind MID-SESSION during RTH. QQQ and MU
crash-looped; recovering them cost their swapfiles, a failed VACUUM that left
the database LARGER, and a 14-box volume rebuild.

⚠️ AND IT WAS INVISIBLE BY CONSTRUCTION. A dry run logs the same line every
night at INFO. **Sixty identical log lines are indistinguishable from a job
that works** — nobody reads an unchanging line. Same failure class as the
pytest chain that was decorative for weeks and the tooling check that printed
green on a broken environment: a green light nobody read.

WHAT THIS PINS:
  R1  `self_close` passes `--apply` — arming is EXPLICIT at the call site, not
      ambient in an environment nobody sets.
  R2  `main()` honours it.
  R3  a hand-run is still DRY (a human must ask before deleting).
  R4  a dry purge with rows pending is LOUD, so the next silence is visible.
"""
import ast
import contextlib
import io
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    sc = open(os.path.join(_root, "warehouse", "self_close.py"),
              encoding="utf-8").read()
    code = "\n".join(l for l in sc.split("\n")
                     if not l.strip().startswith("#"))

    # ── 🔴 R1 — THE SHUTDOWN PATH ARMS IT ────────────────────────────────
    # ⚠️ Match CODE, not the comment that explains the fix — that comment
    # quotes the old `main([])` call.
    check("R1 self_close calls the purge with --apply",
          'retention_purge.main(["--apply"])' in code)
    check("R1b the un-armed call is gone",
          "retention_purge.main([])" not in code)

    # ── R2/R3 — the flag works, and a hand-run does not delete ───────────
    os.environ.pop("OT_RETENTION_APPLY", None)
    from warehouse import retention_purge as rp
    _real = rp.purge
    rp.purge = lambda apply=False: {"quote_series": 1000, "prints": 500}
    import tempfile
    _real_lock = rp.LOCK_PATH
    _real_lock_existed = os.path.exists(_real_lock)
    rp.LOCK_PATH = os.path.join(tempfile.mkdtemp(), "retention_purge.lock")
    try:
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            rp.main(["--apply"])
        armed = b.getvalue()
        check("R2 --apply arms the purge",
              "removed 1,500" in armed and "WOULD" not in armed)

        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            rp.main([])
        dry = b.getvalue()
        # ⚠️ A HUMAN MUST ASK. Defaulting a hand-run to delete is how someone
        # purges a box they were only inspecting.
        check("R3 a hand-run with no flag is still DRY",
              "WOULD remove" in dry)
        # ── 🔴 R4 — AND IT IS LOUD ABOUT IT ──────────────────────────────
        check("R4 a dry purge with rows pending warns explicitly",
              "RETENTION IS DRY" in dry and "NOT removed" in dry)
    finally:
        rp.purge = _real
        rp.LOCK_PATH = _real_lock
    check("R0 the run did not create the box's real purge lock",
          _real_lock_existed or not os.path.exists(_real_lock), _real_lock)

    # ── 🔴 R5 RE-DERIVED (r278) — THE RULE CHANGED, SO THE CHECK MOVED ───
    # It asserted "VACUUM is still not EXECUTED at shutdown", and r255 made
    # that FALSE on purpose: a gated vacuum now runs inside `reclaim()`. The
    # gate went red the afternoon r255 landed and NOTHING NOTICED, because
    # nothing runs these checks unless a `land.spec` names them.
    # ⚠️ THIRD INSTANCE OF THIS CLASS IN ONE DAY. The conductor's C7 pinned the
    # same retired rule and was re-derived when the reclaim was built; `head
    # -3` was the same shape; this one was missed because it lives in the OTHER
    # repo. A check that goes on certifying a rule the system has stopped
    # following is worse than no check — it reports green for a property that
    # is no longer true.
    #
    # 🔑 WHAT THE ORIGINAL RULE WAS ACTUALLY PROTECTING, AND STILL IS: a vacuum
    # must never stall the halt. r162's cost is in this file's header — the
    # fleet went blind mid-session because the purge had run dry for two
    # months, and the recovery included a failed VACUUM that could not fit in
    # /tmp. So the property is not "no vacuum"; it is "no vacuum that cannot
    # complete", and r255 enforces it by REFUSING when free disk is under the
    # live size rather than by absence.
    import ast as _ast
    rp_src = open(os.path.join(_root, "warehouse", "retention_purge.py"),
                  encoding="utf-8").read()
    rp_tree = _ast.parse(rp_src)
    # ⚠️ PARSE, DO NOT GREP — kept from v1.0, and the reason is still good: the
    # module docstring recounts the failed VACUUM of 2026-08-27, so a text
    # search goes red on prose.
    _vac = [n for n in _ast.walk(rp_tree)
            if isinstance(n, _ast.Call)
            and any(isinstance(a, _ast.Constant)
                    and isinstance(a.value, str)
                    and "vacuum" in a.value.lower() for a in n.args)]
    check("R5 the vacuum exists and is GATED, not absent",
          bool(_vac), f"{len(_vac)} vacuum call(s)")
    # 🔴 R5b — THE GATE IS THE WHOLE PROPERTY. A vacuum writes a complete second
    # copy before replacing the original, so it needs free disk above the live
    # size. On 2026-09-05 the four boxes that needed it most had less; one that
    # died half-way at 16:10 on a 96%-full box would be worse than none.
    check("R5b ...refusing when free disk is under the live size",
          "_vacuum_min_free" in rp_src and "REFUSED" in rp_src)
    # ⚠️ R5c — AND IT STILL MUST NOT STALL THE HALT. r162's rule, unchanged:
    # a reclaim failure is reported and stepped over, never raised.
    check("R5c ...and never blocking the halt — a failure is reported, "
          "not raised",
          "vacuum FAILED" in rp_src and "SQLITE_TMPDIR" in rp_src)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_retention_armed: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
