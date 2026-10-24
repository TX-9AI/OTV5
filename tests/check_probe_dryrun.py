#!/usr/bin/env python3
"""
tests/check_probe_dryrun.py  v1.0
v1.0  2026-10-04  OTV4TEST r239 (PRB.2) — THE ORDER PROBE CAN ONLY EVER DRY-RUN.

  The operator, 2026-10-04: "Yes, to the dry run if you can do it without actually spending money."
  tools/probe_order_dryrun.py calls the broker's place_order. This gate proves, by reading its AST, that it
  cannot place a real order:
  D1  exactly one place_order call exists, inside _dry(), with the keyword dry_run set to the literal True
  D2  no `dry_run=False`, no `dry_run=` bound to anything but the constant True, anywhere in the file
  D3  every NewOrder the probe builds reaches the broker only through _dry() (no other attribute call on
      `account` that could submit: place_order / replace_order / place_complex_order)
  D4  the probe is on run_with_bot_env's PROBES list (so it runs only committed and unedited)
  D5  it prints no account number and no balance field (current_buying_power / new_buying_power / net_liq)
No network. Run: python3 tests/check_probe_dryrun.py
"""
import ast, os, sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    p = os.path.join(_root, "tools", "probe_order_dryrun.py")
    try:
        src = open(p).read()
        tree = ast.parse(src)
    except Exception as exc:  # noqa: BLE001
        check("D0 the probe exists and parses", False, f"{type(exc).__name__}: {exc}")
        print("\nRED"); return 1
    calls, owners = [], {}
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
                owners.setdefault(id(c), fn.name)
    for c in ast.walk(tree):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in (
                "place_order", "replace_order", "place_complex_order"):
            calls.append(c)
    def _dry_true(c):
        kw = [k for k in c.keywords if k.arg == "dry_run"]
        return len(kw) == 1 and isinstance(kw[0].value, ast.Constant) and kw[0].value.value is True
    check("D1 exactly one place_order call, inside _dry(), with dry_run=True (literal)",
          len(calls) == 1 and calls[0].func.attr == "place_order" and owners.get(id(calls[0])) == "_dry"
          and _dry_true(calls[0]), [(c.func.attr, owners.get(id(c)), _dry_true(c)) for c in calls])
    bad_kw = [k for c in ast.walk(tree) if isinstance(c, ast.Call) for k in c.keywords
              if k.arg == "dry_run" and not (isinstance(k.value, ast.Constant) and k.value.value is True)]
    check("D2 no dry_run bound to anything but the constant True", not bad_kw and "dry_run=False" not in src,
          len(bad_kw))
    check("D3 no other submitting call (replace_order / place_complex_order)",
          all(c.func.attr == "place_order" for c in calls))
    w = open(os.path.join(_root, "tools", "run_with_bot_env.py")).read()
    check("D4 the probe is on run_with_bot_env's PROBES list",
          '"probe_order_dryrun.py": "tools/probe_order_dryrun.py"' in w)
    prints = [ast.get_source_segment(src, c) or "" for c in ast.walk(tree)
              if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "print"]
    leak = [s for s in prints if any(k in s for k in ("current_buying_power", "new_buying_power",
                                                       "net_liq", "account_number", "get_tt_account_number"))]
    check("D5 prints no account number and no balance", not leak, leak[:2])
    if FAILED:
        print(f"\nRED — {sorted(set(FAILED))}"); return 1
    print("\nGREEN — the order probe can only ever dry-run"); return 0


if __name__ == "__main__":
    sys.exit(main())
