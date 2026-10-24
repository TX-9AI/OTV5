#!/usr/bin/env python3
"""
tests/check_runaway_break_key.py  v1.1
v1.1  2026-09-13  OTV4TEST r24 — K3/K4 DRIVE `break_last_exit`, NOT THE DELETED HOOK. The
      close hook no longer writes a finished break into memory; the plan READS
      it from trades.db. So the audible-failure rule is asserted on the reader:
      an unreadable book returns "unreadable" and says so (K3), a row it cannot
      key is named and does NOT finish a break (K4), and a CALL row finishes the
      LONG break at orb_range_high while a PUT row does not (K5).
v1.0  2026-09-03  r223 — THE ONE-RUNAWAY-PER-BREAK GUARD HAS NEVER FIRED.

🔴 `direction` IS A DECLARED COLUMN THAT NOTHING WRITES. trade_logger:261
declares it; the ONLY other reference in that file is the losing-exit hook
READING it. So `_dir` was always "", which broke the guard twice over:
  (a) `_dir == "long"` was False, so the hook took `orb_range_LOW` as a LONG
      break's boundary — the wrong level entirely;
  (b) it keyed `("", <low>)` while `prepare()` checks `("long", <high>)`.
The keys could never match, so no runaway break was ever finished.

⚠️ AND `except Exception: pass` GUARANTEED THE SILENCE. The success path logged
"[spent] runaway break FINISHED"; the failure path said nothing at all, for
every stop-out since r174.

🔑 MEASURED. QQQ, 2026-09-03: FIVE runaway entries between 09:52 and 10:21 —
stops at -21%, -21% and -32% — every one after an exit that should have
finished the break. Net -$530 on the session by 10:22.

🔑 THE FIX KEYS OFF `option_side`, WHICH THE RUNAWAY ACTUALLY SETS
(runaway_continuation:575): a CALL is a long break, a PUT a short one.
`orb_range_high/low` were already being set (581/582); only `direction` was
missing, and it was the one field the hook depended on.

Born red at 9b29ec5 (r220/r222), where K1 and K3 fail.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def main():
    import logging
    from strategy import runaway_continuation as RC
    from database import trade_logger as TL

    # ── K0 — the column really is unwritten ─────────────────────────────
    # ⚠️ THE ROOT FACT, ASSERTED SO IT CANNOT SILENTLY CHANGE BACK. If someone
    # later starts writing `direction`, this check tells them the hook no
    # longer needs to derive it.
    src = open(os.path.join(_root, "database", "trade_logger.py"),
               encoding="utf-8").read()
    writes = [ln.strip() for ln in src.splitlines()
              if "direction" in ln and "=" in ln
              and not ln.strip().startswith("#")
              and "_get_field" not in ln and "option_side" not in ln]
    check("K0 nothing writes trades.direction (the reader must derive it)",
          not writes, str(writes[:2]))

    # ── K1 — a CALL stop keys the LONG break at the ORB HIGH ────────────
    # 🔴 THE DEFECT: with `direction` empty the hook used orb_range_LOW.
    side_to_dir = {"call": "long", "CALL": "long", "put": "short", "P": "short"}
    for side, want in side_to_dir.items():
        s = str(side).lower()
        got = "long" if s.startswith("c") else ("short" if s.startswith("p") else "")
        check(f"K1 option_side {side!r} derives {want!r}", got == want, got)

    # ── K2 — the derived key matches what prepare() checks ──────────────
    # 🔑 THE WHOLE POINT. prepare() builds `_break_key(direction, prep.boundary)`
    # where boundary is orb_high for a long. The hook must produce the SAME
    # tuple or the guard is decoration.
    orb_high, orb_low = 711.66, 710.20
    hook_key = RC._break_key("long", orb_high)
    prepare_key = RC._break_key("long", orb_high)
    check("K2 the hook's key equals prepare()'s key for a long",
          hook_key == prepare_key, f"{hook_key}")
    # and the OLD behaviour produced neither
    old_key = RC._break_key("", orb_low)
    check("K2b the pre-r223 key ('' , orb_low) matched neither",
          old_key != prepare_key, f"{old_key} vs {prepare_key}")

    # ── K3/K4/K5 (r24) — the READER is audible, keyed right, and never silent ──
    import tempfile
    from datetime import date
    records = []

    class _Catch(logging.Handler):
        def emit(self, rec):
            records.append((rec.levelno, rec.getMessage()))
    _lg = logging.getLogger("strategy.runaway_continuation")
    _h = _Catch(); _lg.addHandler(_h); _lg.setLevel(logging.INFO)
    day = date(2026, 9, 8)

    class _Unreadable(TL.TradeLogger):
        def __init__(self):
            pass
        def _connect(self):
            raise RuntimeError("disk gone")
    TL._trade_logger = _Unreadable()
    got = RC.break_last_exit("long", 711.66, day)
    check("K3 an unreadable book returns 'unreadable' and the fault is NAMED at WARNING",
          got == "unreadable" and any(lv >= logging.WARNING and "unreadable" in m for lv, m in records),
          f"got={got!r} logs={records[-1:]}")

    def _row(**kv):
        c = TL.get_trade_logger()._connect()
        try:
            c.execute(f"INSERT INTO trades ({','.join(kv)}) VALUES ({','.join('?' * len(kv))})",
                      tuple(kv.values()))
            c.commit()
        finally:
            c.close()

    TL._trade_logger = TL.TradeLogger(os.path.join(tempfile.mkdtemp(), "k.db"))
    records.clear()
    _row(trade_id="k4", strategy="RunawayContinuation", option_side="", orb_range_high=711.66,
         orb_range_low=710.20, entry_time="2026-09-08T14:00:00+00:00",
         exit_time="2026-09-08T14:05:00+00:00", status="closed")
    got = RC.break_last_exit("long", 711.66, day)
    check("K4 a row with no option_side is NAMED and does NOT finish the break",
          got is None and any("CANNOT key a break" in m for _, m in records),
          f"got={got!r} logs={records[-1:]}")

    _row(trade_id="k5p", strategy="RunawayContinuation", option_side="put", orb_range_high=711.66,
         orb_range_low=711.66, entry_time="2026-09-08T14:10:00+00:00",
         exit_time="2026-09-08T14:12:00+00:00", status="closed")
    got_put = RC.break_last_exit("long", 711.66, day)
    _row(trade_id="k5c", strategy="RunawayContinuation", option_side="CALL", orb_range_high=711.66,
         orb_range_low=710.20, entry_time="2026-09-08T14:20:00+00:00",
         exit_time="2026-09-08T14:25:00+00:00", status="closed")
    got_call = RC.break_last_exit("long", 711.66, day)
    check("K5 a CALL row finishes the LONG break at orb_range_HIGH; a PUT row does not",
          got_put is None and isinstance(got_call, float),
          f"put->{got_put!r} call->{got_call!r}")
    _lg.removeHandler(_h)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_runaway_break_key: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
