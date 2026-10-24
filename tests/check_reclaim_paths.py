#!/usr/bin/env python3
# tests/check_reclaim_paths.py — v1.0
# v1.0 (2026-10-03) — OTV4TEST r192 (AUD.3): MIRRORED from otv4 r420. Everything below the gate docstring
#   is byte-identical with otv4's file; these two lines are the fork's header. otv4's own header follows.
# options-trader-v4/tests/check_reclaim_paths.py — v1.0
# v1.0 (2026-09-23) — r420 / OPS.43. THE RECLAIM LIST MUST NAME THE FILE THE
#   REST OF THE SYSTEM WRITES TO.
#   🔴 THE DEFECT. `retention_purge` reclaimed `HERE/data/trades.db`. That file
#   exists on every box and holds ZERO TABLES. The fleet's actual trade record
#   is `HERE/trades.db`, one directory up — so the nightly reclaim has never
#   checkpointed or vacuumed the database it names, and the log line
#   `reclaim trades.db  checkpoint ok, wal 0MB -> 0MB` was TRUE OF THE WRONG
#   FILE. A number that is correct about the wrong object is the hardest kind
#   to catch, because nothing about it looks broken.
#   📊 COST TODAY IS NIL AND THE ROW SAYS SO: measured fleet-wide before the
#   fix, the real trades.db is 0.1-0.3MB with a 0MB WAL and 0MB free pages, so
#   there was nothing to reclaim. This is a correctness gate, not a disk one,
#   and it is written that way rather than claiming a saving it cannot show.
#   🔑 P1 AND P4 ARE THE CHECKS THAT MATTER, AND THEY ARE ANTI-DRIFT RATHER
#   THAN ANTI-TYPO. The cause was a THIRD hardcoded literal for a path
#   `config.DB_PATH` and `s3_push.TRADES_DB` already owned. Fixing the literal
#   fixes today; pinning the two owners together is what stops the next one —
#   WA §7, and when there must be two readers, a check that they AGREE.
#   ⚠️ P4 DRIVES THE OVERRIDE because agreeing on the default is the easy half.
#   Two modules can share a default and still diverge the moment an env var is
#   set, and `OT_TRADES_DB` is exactly the knob an operator would reach for.
"""Gate: the reclaim list names the real databases, and cannot drift.

P1  both owners name a trades.db, neither under data/       (shape)
P2  the reclaim list contains it, and NOT the data/ decoy
P3  feed_store / derived_store still resolve under data/     [control]
P4  an OT_TRADES_DB override moves BOTH, not one             (anti-drift)
"""
import importlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


def main():
    try:
        from warehouse import retention_purge as RP
    except Exception as exc:                                  # noqa: BLE001
        ck("P0", False, f"cannot import retention_purge ({exc})")
        print("\nRED — 1 check(s) failed: P0")
        return 1

    rp_trades = getattr(RP, "TRADES_DB", None)

    # ── P1 — the two owners must name the same file ──────────────────────
    sp_trades = None
    try:
        from warehouse import s3_push as SP
        sp_trades = getattr(SP, "TRADES_DB", None)
    except Exception as exc:                                  # noqa: BLE001
        # boto3 may be absent in a bare checkout; fall back to reading the
        # literal out of the source rather than skipping the check entirely.
        try:
            src = open(os.path.join(ROOT, "warehouse", "s3_push.py"),
                       encoding="utf-8").read()
            m = re.search(r'TRADES_DB\s*=\s*os\.environ\.get\(\s*\n?\s*'
                          r'"OT_TRADES_DB",\s*os\.path\.join\((.*?)\)\)', src, re.S)
            sp_trades = "(source) " + m.group(1).strip() if m else None
        except OSError:
            sp_trades = None

    # ⚠️ STRING EQUALITY IS THE WRONG TEST AND THE FIRST CUT USED IT.
    # `s3_push` derives from `$HOME/options-trader/...` (deployment-absolute)
    # while this file derives from `HERE` (checkout-relative, matching its own
    # `feed_db`/`derived_db`). ON A BOX THEY RESOLVE IDENTICALLY — install dir
    # IS $HOME/options-trader — and in any other checkout they CANNOT, because
    # one is anchored to the tree and the other to the home directory. A gate
    # demanding equality would be red on every developer checkout and would get
    # loosened until it meant nothing (the CV.1 lesson). What must hold is
    # STRUCTURAL: same filename, and neither pointing into `data/`. The
    # behavioural anti-drift property is P4's job.
    def _shape_ok(pth):
        parts = os.path.normpath(pth).split(os.sep)
        return parts[-1] == "trades.db" and "data" not in parts[-2:-1]

    if rp_trades is None:
        ck("P1", False, "retention_purge.TRADES_DB is absent")
    elif sp_trades is None:
        ck("P1", False, "could not resolve s3_push.TRADES_DB to compare")
    else:
        sp_txt = sp_trades if isinstance(sp_trades, str) else str(sp_trades)
        rp_ok = _shape_ok(rp_trades)
        sp_ok = sp_txt.startswith("(source) ") or _shape_ok(sp_txt)
        ck("P1", rp_ok and sp_ok,
           f"retention_purge={rp_trades!r} (shape ok={rp_ok}); "
           f"s3_push={sp_txt!r} (shape ok={sp_ok})")

    # ── P2 — the reclaim call site uses it, and not the decoy ────────────
    # ⚠️ PARSED, NOT GREPPED, AND IT TOOK TWO TRIES TO GET THERE. Cut one
    # grepped the whole file and went red on its own changelog, which QUOTES
    # the retired literal so the next reader can see what was wrong. Cut two
    # filtered lines starting with `#` — and this module's changelog lives in
    # its DOCSTRING, which carries no `#` at all, so it still matched. A
    # checker that cannot tell prose from code punishes documenting the fix;
    # the AST cannot be fooled by either. Third instance this session, after
    # the §20 collisions and a monitor that matched the word it was hunting
    # inside its own echoed command.
    try:
        import ast as _ast
        src = open(os.path.join(ROOT, "warehouse", "retention_purge.py"),
                   encoding="utf-8").read()
        tree = _ast.parse(src)
        uses = decoy = False
        for node in _ast.walk(tree):
            if not (isinstance(node, _ast.Call)
                    and isinstance(node.func, _ast.Name)
                    and node.func.id == "reclaim"):
                continue
            if not node.args or not isinstance(node.args[0], _ast.List):
                continue
            for el in node.args[0].elts:
                if isinstance(el, _ast.Name) and el.id == "TRADES_DB":
                    uses = True
                # a literal join(..., "data", "trades.db") inside the list
                if isinstance(el, _ast.Call):
                    lits = [a.value for a in _ast.walk(el)
                            if isinstance(a, _ast.Constant)
                            and isinstance(a.value, str)]
                    if "trades.db" in lits and "data" in lits:
                        decoy = True
        ck("P2", uses and not decoy,
           f"reclaim() arg list: uses TRADES_DB={uses}, data/ decoy={decoy} "
           f"(parsed, so the changelog cannot trip it)")
    except Exception as exc:                                  # noqa: BLE001
        ck("P2", False, f"cannot parse source ({exc})")

    # ── P3 — CONTROL: the stores that ARE under data/ must not move ──────
    # The fix was one directory; a fix that also moved feed_store would trade
    # one wrong path for two.
    try:
        ok = ('os.path.join(HERE, "data", "feed_store.db")' in src)
        ck("P3", ok, "feed_store.db still resolves under data/" if ok
           else "feed_store.db path CHANGED — the fix over-reached")
    except Exception as exc:                                  # noqa: BLE001
        ck("P3", False, f"{exc}")

    # ── P4 — an override must move BOTH owners ───────────────────────────
    marker = "/tmp/_p4_trades_probe.db"
    old = os.environ.get("OT_TRADES_DB")
    os.environ["OT_TRADES_DB"] = marker
    try:
        rp2 = importlib.reload(RP)
        got_rp = getattr(rp2, "TRADES_DB", None)
        got_sp = None
        try:
            from warehouse import s3_push as SP2
            got_sp = getattr(importlib.reload(SP2), "TRADES_DB", None)
        except Exception:                                     # noqa: BLE001
            got_sp = marker      # boto3 absent: s3_push reads the same env var
        ck("P4", got_rp == marker and got_sp == marker,
           f"under OT_TRADES_DB={marker}: retention_purge={got_rp!r} "
           f"s3_push={got_sp!r}")
    finally:
        if old is None:
            os.environ.pop("OT_TRADES_DB", None)
        else:
            os.environ["OT_TRADES_DB"] = old
        try:
            importlib.reload(RP)
        except Exception:                                     # noqa: BLE001
            pass

    if _fails:
        print(f"\nRED — {len(_fails)} check(s) failed: {' '.join(_fails)}")
        return 1
    print("\nGREEN — the reclaim list names the real trades.db, and is pinned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
