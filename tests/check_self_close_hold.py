#!/usr/bin/env python3
"""tests/check_self_close_hold.py — v5.1
v5.1  2026-10-26  (TG.2) — THE FAKE ALERT MANAGER HAD A METHOD THE REAL ONE DOES NOT. drive() faked
      `SimpleNamespace(send=...)`, so H3-H5 counted alerts that, on a box, raised AttributeError (AlertManager has
      no `send`) and were swallowed. The fake now carries `_send`, the real method, and only that. H6 drives a held
      close through the REAL AlertManager with only its Telegram sender faked: the page reaches the sender. H6b
      every method self_close calls on the alert manager exists on the real class (AST). H7 the clean close pages
      nothing (a control, green on both). Born red on self_close v5.0 at H3 H4 H4b H5 H6 H6b.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
A FAILED DRAIN HOLDS THE BOX, WHATEVER ELSE THE VERIFIER PRINTS.

v1.0  2026-09-26 — OTV4TEST r147 (S3.15). `self_close` read `drift = "COUNTER DRIFT" in out`
      and let it override `not ok` whatever `failed=` said. A counter-drift line
      is printed whenever every remaining gap is <= 2, and an S3 delete that EMPTIES
      a prefix the box's counter still claims leaves a PERMANENT gap of 1 (a got=0
      prefix never heals). Measured 2026-09-26: SOFI carries six such prefixes and
      mainline 31 across 15 boxes, so on those boxes a drain with a failed PUT
      HALTED and ran the purge where it was built to HOLD and page. Operator,
      2026-09-26: "Concur" (proposal 2a). Shared with otv4 (WA §38.2).

  H1  failed=0, short=0, OK                        -> halts (the normal close)
  H2  failed=0, short>0, COUNTER DRIFT printed      -> halts (r171's ruling, unchanged)
  H3  failed=1, short=0                            -> HELD, alerted, no purge, no shutdown
  H4  failed=1, short>0, COUNTER DRIFT printed      -> HELD, alerted, no purge, no shutdown
                                                      (the defect: HEAD halts here)
  H4b as H4, with a stray " failed=0 " elsewhere in the output -> still HELD
      (failed= is read from the DRAIN line, which owns it; a mutant reading the
      whole output passed H1-H5 and is what this case exists to kill)
  H5  failed=0, short>0, no drift line (gap >= 3)   -> HELD (unchanged)

🔴 NOTHING REAL RUNS. `subprocess.run` is replaced by a recorder, so no
`systemctl`, no verifier and no `shutdown`; `retention_purge.main` is replaced
by a recorder (check_audit_20260823's r26 lesson: the real purge opens the live
feed store whatever the environment says); the alert manager is replaced so
nothing reaches Telegram. OT_INSTRUMENT is set so box_instrument() never reads
the unit.

Run:  cd ~/options-trader && python3 tests/check_self_close_hold.py
"""
from __future__ import annotations

import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "SYN"

PROBLEMS: list = []

DRIFT = ("  ⚠️ SMALL, CONSISTENT SHORTFALL ON 6 PREFIXES (max 1). That is the "
         "signature of COUNTER DRIFT, not data loss")


def drain(failed: int, short: int) -> str:
    verdict = "OK" if (not short and not failed) else "SHORT"
    return (f"DRAIN host=x sym=SYN drained=yes pushed=3 failed={failed} "
            f"prefixes=9 local=9 s3=9 short={short} {verdict}")


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def drive(verifier_out: str, am=None) -> dict:
    """Run self_close.main() against a canned verifier output. Records only."""
    import subprocess
    from warehouse import self_close as sc
    from warehouse import retention_purge as rp
    rec = {"cmds": [], "purge": [], "alerts": []}

    def fake_run(cmd, **kw):
        rec["cmds"].append(list(cmd) if isinstance(cmd, list) else cmd)
        if isinstance(cmd, list) and any("s3_push.py" in str(c) for c in cmd):
            return types.SimpleNamespace(stdout=verifier_out, stderr="")
        return types.SimpleNamespace(stdout="", stderr="")

    # A stand-in MODULE, not a patched attribute: self_close imports the alert
    # manager lazily, and the real one needs the bot venv (pytz) - importing it
    # here would make this check red on ENVIRONMENT, not content (WA §36).
    fake_am = types.SimpleNamespace(_send=lambda msg, *a, **k: rec["alerts"].append(msg))
    fake_mod = types.ModuleType("notifications.alert_manager")
    fake_mod.get_alert_manager = lambda: (am if am is not None else fake_am)
    saved = (subprocess.run, rp.main, sys.modules.get("notifications.alert_manager"))
    subprocess.run = fake_run
    rp.main = lambda argv=None: rec["purge"].append(list(argv or [])) or 0
    sys.modules["notifications.alert_manager"] = fake_mod
    try:
        rec["rc"] = sc.main(["self_close.py"])
    finally:
        subprocess.run, rp.main = saved[0], saved[1]
        if saved[2] is None:
            sys.modules.pop("notifications.alert_manager", None)
        else:
            sys.modules["notifications.alert_manager"] = saved[2]
    rec["shutdown"] = any(isinstance(c, list) and "shutdown" in c for c in rec["cmds"])
    return rec


def held(r: dict) -> bool:
    return r["rc"] == 1 and not r["shutdown"] and not r["purge"] and bool(r["alerts"])


def halted(r: dict) -> bool:
    return r["rc"] == 0 and r["shutdown"] and r["purge"] == [["--apply"]]


def main() -> int:
    print("self_close: a failed drain holds the box")
    r = drive(drain(0, 0))
    check("H1 clean drain, OK -> halts", halted(r), f"rc={r['rc']} shutdown={r['shutdown']}")
    r = drive(drain(0, 6) + "\n" + DRIFT)
    check("H2 clean drain + COUNTER DRIFT -> halts (r171 unchanged)", halted(r),
          f"rc={r['rc']} shutdown={r['shutdown']}")
    r = drive(drain(1, 0))
    check("H3 failed drain, nothing short -> HELD", held(r),
          f"rc={r['rc']} shutdown={r['shutdown']} purge={r['purge']}")
    r = drive(drain(1, 6) + "\n" + DRIFT)
    check("H4 failed drain + COUNTER DRIFT -> HELD, not halted", held(r),
          f"rc={r['rc']} shutdown={r['shutdown']} purge={r['purge']}")
    r = drive(drain(1, 6) + "\n" + DRIFT + "\n  retry stage: pushed=0 failed=0 (noise)")
    check("H4b failed drain + drift + stray failed=0 elsewhere -> still HELD", held(r),
          f"rc={r['rc']} shutdown={r['shutdown']} purge={r['purge']}")
    r = drive(drain(0, 1) + "\n  ⚠️ SHORTFALL VARIES (max 3) — that is NOT the counter-drift signature.")
    check("H5 clean drain, gap >= 3 -> HELD (unchanged)", held(r),
          f"rc={r['rc']} shutdown={r['shutdown']}")
    # ── H6 / H6b / H7 — TG.2: the page reaches the REAL alert manager's sender ──
    try:
        from notifications.alert_manager import AlertManager
        real = AlertManager.__new__(AlertManager)       # no constructor: no real TelegramSender
        sent = []
        real._tg = types.SimpleNamespace(send=lambda msg, *a, **k: sent.append(msg) or True)
        real._enabled = True
        r = drive(drain(1, 0), am=real)
        check("H6 a held close pages through the REAL AlertManager to its sender",
              r["rc"] == 1 and len(sent) == 1 and "self-close held" in sent[0],
              f"rc={r['rc']} sent={sent}")
        n0 = len(sent)
        r = drive(drain(0, 0), am=real)
        check("H7 a clean close pages nothing (control)", r["rc"] == 0 and len(sent) == n0,
              f"sent {n0}->{len(sent)}")
    except Exception as e:                                          # noqa: BLE001
        check("H6 a held close pages through the REAL AlertManager to its sender", False,
              f"{type(e).__name__}: {e}")
    try:
        import ast
        from notifications.alert_manager import AlertManager
        src = open(os.path.join(ROOT, "warehouse", "self_close.py"), encoding="utf-8").read()
        called = sorted({n.func.attr for n in ast.walk(ast.parse(src))
                         if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and isinstance(n.func.value, ast.Name) and n.func.value.id == "am"})
        missing = [m for m in called if not callable(getattr(AlertManager, m, None))]
        check("H6b every method self_close calls on the alert manager exists on AlertManager",
              bool(called) and not missing, f"called={called} missing={missing}")
    except Exception as e:                                          # noqa: BLE001
        check("H6b every method self_close calls on the alert manager exists on AlertManager", False,
              f"{type(e).__name__}: {e}")
    print("GREEN" if not PROBLEMS else f"RED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
