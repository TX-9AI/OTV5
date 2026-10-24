#!/usr/bin/env python3
# options-trader-v4/tests/check_vacuum_headroom.py — v1.0
# v1.0 (2026-09-23) — r419 / OPS.42. A VACUUM THAT CANNOT FIT MUST BE REFUSED
#   BEFORE IT STARTS, NOT DISCOVERED HALF-WAY.
#   🔴 THE MEASUREMENT THIS FILE EXISTS FOR, TAKEN ON PLTR 2026-09-22 DURING A
#   97%-DISK INCIDENT: `VACUUM` failed with `database or disk is full` at
#   530MB free AND AGAIN at 656MB free, on a database whose LIVE size was
#   401.9MB (page_count - freelist_count, times page_size). `VACUUM` builds a
#   complete second copy before replacing the original, and in WAL mode writes
#   that copy through the WAL, so it needs roughly TWICE the live size.
#   🔑 V3 IS THE CHECK THAT MATTERS BECAUSE IT IS THE INCIDENT ITSELF. At the
#   old headroom of 1.15 the gate computed need = 462MB and would have STARTED
#   the vacuum at 656MB free — the exact run that died. V3 drives the shipped
#   constant against the measured live size and demands the gate now refuse it.
#   ⚠️ A HALF-FINISHED VACUUM ON A NEARLY-FULL VOLUME AT 16:10 is strictly
#   worse than no vacuum: the file this purge was trying to shrink is the one
#   it can corrupt, and r418/OPS.41 records what a bad swap does to a live box.
#   ⚠️ THE FIX ONLY EVER MAKES THE GATE MORE CONSERVATIVE, so there is no
#   "does it still vacuum when it should" risk to trade against — V2 keeps the
#   refusal legible so a deferred vacuum is a volume decision, not a silence.
"""Gate: the VACUUM space gate reflects what VACUUM actually costs.

V1  VACUUM_HEADROOM is at least 2.0
V2  the refusal prints the arithmetic, not a bare "skipped"   [control]
V3  PLTR's measured 401.9MB live is REFUSED at 656MB free (the real failure)
"""
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
        ck("V0", False, f"cannot import warehouse.retention_purge ({exc})")
        print("\nRED — 1 check(s) failed: V0")
        return 1

    head = getattr(RP, "VACUUM_HEADROOM", None)

    # ── V1 — the constant itself ─────────────────────────────────────────
    if head is None:
        ck("V1", False, "VACUUM_HEADROOM is absent")
    else:
        ck("V1", head >= 2.0,
           f"VACUUM_HEADROOM={head} (want >= 2.0; VACUUM writes a full second "
           f"copy before replacing the original)")

    # ── V2 — CONTROL: the refusal is legible ─────────────────────────────
    # Source-anchored and SAID SO: the refusal is composed inside `reclaim()`
    # around a live statvfs and a real database, so asserting the STRING is
    # what a gate can honestly do here. The behavioural proof is the fleet log,
    # which prints this line whenever a box is too full.
    try:
        src = open(os.path.join(ROOT, "warehouse", "retention_purge.py"),
                   encoding="utf-8").read()
        ok = ("vacuum REFUSED: needs %s free, disk has %s" in src)
        ck("V2", ok, "refusal names need AND available" if ok
           else "the refusal no longer prints the arithmetic")
    except OSError as exc:
        ck("V2", False, f"cannot read source ({exc})")

    # ── V3 — THE MEASURED INCIDENT ───────────────────────────────────────
    # PLTR, 2026-09-22: live 401.9MB, VACUUM died at 530MB AND at 656MB free.
    if head is None:
        ck("V3", False, "VACUUM_HEADROOM is absent")
    else:
        live = int(401.9 * 1024 * 1024)
        need = int(live * head)
        free_at_failure = 656 * 1024 * 1024
        refused = need > free_at_failure
        ck("V3", refused,
           f"need={need / 1048576:.0f}MB vs the 656MB free at which VACUUM "
           f"ACTUALLY FAILED — {'refused (correct)' if refused else 'WOULD HAVE STARTED THE RUN THAT DIED'}")

    if _fails:
        print(f"\nRED — {len(_fails)} check(s) failed: {' '.join(_fails)}")
        return 1
    print("\nGREEN — the vacuum gate refuses what VACUUM cannot fit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
