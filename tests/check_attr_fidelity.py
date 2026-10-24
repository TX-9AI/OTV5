#!/usr/bin/env python3
"""check_attr_fidelity.py — v1.2
v1.2  2026-10-03 — OTV4TEST r193 (CFG.1). A3/A4: THE SAME FAILURE, ON config ITSELF. The 10-03 audit
      found 29 names read as getattr(config, "NAME", literal) that config never defined - every
      "retune via config" took the module's literal, and a mistyped name could not fail. A3 resolves
      every getattr(<config alias>, "NAME"...) in the production tree against the REAL imported config
      module; the few names owned elsewhere are listed with their reason. A4 pins the 29 values config
      now defines to the literals their modules were using, so the move changed nothing.
v1.1  2026-09-23 — OTV4TEST r126. The `sweep` subject (analysis.liquidity_mapper
      .LiquiditySweep) and its A2 regression pin (bars_ago / bars_since_reclaim)
      are removed with the mapper, which is deleted. The other four stay.

🔴 THE GATE FOR THE FAILURE THAT COST FIVE SETUPS IN ONE WEEK.

Every one of these shipped, and every one is the same shape — a name read off
an object that does not have it:

    ctm.all()                        real: all_rails()
    getattr(c, "oi")                 real: open_interest
    _f(ctx.get("gex"))               real: a GEXSnapshot OBJECT, not a float
    getattr(sweep, "bars_since_reclaim")   real: bars_ago
    getattr(orb, "tp50")             real: target_50pct

⚠️ `getattr` WITH A DEFAULT CANNOT RAISE. No traceback, no log line, no red
test — the gate simply never applies. A DEAD gate and a gate that keeps passing
are indistinguishable from outside. `oi` blinded the butterfly for its entire
existence; `target_50pct` refused every runaway on eight boxes at 09:51 on a
breakout morning while printing "50% TP n/a".

⚠️ AND UNIT TESTS CANNOT CATCH IT WHEN ONE AUTHOR WRITES BOTH THE CALLER AND
THE FIXTURE — they are wrong the same way and the board goes green. This check
resolves against the REAL imported classes, never a stand-in.

HOW IT WORKS: for each (variable name -> class) binding declared in _SUBJECTS
below, every `getattr(var, "name")` and `var.name(...)` in the scanned tree is
resolved against that class's annotations, slots and dir(). Unknown names fail.

ADDING A SUBJECT: one line in _SUBJECTS. If a variable name is used for two
different types anywhere in the tree, do NOT add it — a false positive here
trains people to ignore the gate, which is worse than not having it.
"""
import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def _members(cls):
    """Every attribute name that resolves on this class."""
    names = set(dir(cls))
    names |= set(getattr(cls, "__annotations__", {}) or {})
    for base in getattr(cls, "__mro__", []):
        names |= set(getattr(base, "__annotations__", {}) or {})
        names |= set(getattr(base, "__slots__", []) or [])
    return names


def _load_subjects():
    """(variable name -> real class). Import failures are reported, not skipped
    silently — a subject that cannot be imported is an unchecked subject."""
    subjects, broken = {}, []
    wanted = [
        ("ctm",       "analysis.condor_trigger_map", "CondorTriggerMap"),
        # ⚠️ `t` IS DELIBERATELY ABSENT. It is the PlanTick variable throughout
        # strategy/, not a ForkTrigger — adding it produced 40+ false positives
        # on the first run. A noisy gate is worse than no gate: it teaches
        # people to ignore it. ForkTrigger fields are covered by the A2 pin and
        # by check_fixture_fidelity, which scopes to the file that owns them.
        ("orb",       "analysis.orb_engine",         "ORBData"),
        ("contract",  "data.options_chain",          "OptionContract"),
        ("chain",     "data.options_chain",          "OptionsChain"),
        ("gex",       "data.gex_data",               "GEXSnapshot"),
    ]
    for var, mod, cls in wanted:
        try:
            m = __import__(mod, fromlist=[cls])
            subjects[var] = (cls, _members(getattr(m, cls)))
        except Exception as exc:                                # noqa: BLE001
            broken.append(f"{mod}.{cls} ({type(exc).__name__})")
    return subjects, broken


def _scan(subjects, folders):
    """Every attribute read against a known subject, with its source location."""
    bad = []
    for folder in folders:
        d = os.path.join(_root, folder)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(d, fn)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except Exception:                                   # noqa: BLE001
                continue
            for n in ast.walk(tree):
                var = attr = None
                # getattr(obj, "name", ...)
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "getattr" and len(n.args) >= 2
                        and isinstance(n.args[0], ast.Name)
                        and isinstance(n.args[1], ast.Constant)
                        and isinstance(n.args[1].value, str)):
                    var, attr = n.args[0].id, n.args[1].value
                # obj.name  (attribute or method call)
                elif (isinstance(n, ast.Attribute)
                      and isinstance(n.value, ast.Name)):
                    var, attr = n.value.id, n.attr
                if var is None or var not in subjects:
                    continue
                cls, members = subjects[var]
                if attr.startswith("__") or attr in members:
                    continue
                bad.append(f"{folder}/{fn}:{n.lineno} {var}.{attr} "
                           f"(not on {cls})")
    return bad


def main():
    subjects, broken = _load_subjects()

    # ⚠️ A SUBJECT THAT WILL NOT IMPORT IS AN UNCHECKED SUBJECT — say so loudly
    # rather than quietly scanning less than advertised.
    check("A0 every subject class imports", not broken,
          "; ".join(broken) or f"{len(subjects)} subjects loaded")

    folders = ["strategy", "analysis", "derived", "data", "execution", "risk"]
    bad = _scan(subjects, folders)
    check("A1 every attribute read resolves on the REAL class",
          not bad,
          ("\n        " + "\n        ".join(bad)) if bad
          else f"{len(subjects)} subjects across {len(folders)} folders")

    # ⚠️ REGRESSION PINS — the five that actually shipped. If the scanner is
    # ever narrowed or a subject dropped, these say so directly instead of the
    # check quietly passing on a smaller surface.
    for var, real, ghost in (("ctm", "all_rails", "all"),
                             ("contract", "open_interest", "oi"),
                             ("orb", "target_50pct", "tp50"),
                             ("gex", "net_gex", "gex_value")):
        if var not in subjects:
            check(f"A2 {var} is still a scanned subject", False, "MISSING")
            continue
        _, members = subjects[var]
        check(f"A2 {var}: '{real}' exists and '{ghost}' does not",
              real in members and ghost not in members,
              f"real={real in members} ghost={ghost in members}")

    # ── A3 / A4 (r193, CFG.1) — getattr(config, "NAME", default) on a name config lacks ──
    try:
        import config as _cfg
        cfg_names = set(dir(_cfg))
    except Exception as exc:                                    # noqa: BLE001
        _cfg, cfg_names = None, set()
        check("A3 config imports", False, f"{type(exc).__name__}: {exc}")
    if _cfg is not None:
        # Names read through a default ON PURPOSE, each with its owner. Adding one here is a
        # statement that config must NOT define it; anything else unknown is the defect.
        OWNED_ELSEWHERE = {
            "LEVEL_SPIKE_REJECT": "derived/level_book.SPIKE_REJECT_USD owns the value",
            "QUOTE_FLOOR": "breakout_plan's dead 0.01 behind orb_plan's 0.05 - audit C9, ruling pending",
            "FEED_DB_PATH": "store paths - audit C4 centralization, not yet built",
            "FEED_STORE_PATH": "store paths - audit C4 centralization, not yet built",
            "DATA_DIR": "store paths - audit C4 centralization, not yet built",
        }
        ghost = []
        prod = ["strategy", "analysis", "derived", "data", "execution", "risk", "database",
                "notifications", "utils", "warehouse", "tools"]
        files = [os.path.join(_root, "main.py"), os.path.join(_root, "status.py"), os.path.join(_root, "query.py")]
        for folder in prod:
            d = os.path.join(_root, folder)
            if os.path.isdir(d):
                files += [os.path.join(d, fn) for fn in sorted(os.listdir(d)) if fn.endswith(".py")]
        for path in files:
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except Exception:                                   # noqa: BLE001
                continue
            for n in ast.walk(tree):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr"
                        and len(n.args) >= 2 and isinstance(n.args[0], ast.Name)
                        and n.args[0].id in ("config", "_cfg", "_config", "cfg")
                        and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str)):
                    name = n.args[1].value
                    if name not in cfg_names and name not in OWNED_ELSEWHERE:
                        ghost.append(f"{os.path.relpath(path, _root)}:{n.lineno} config.{name}")
        check("A3 every getattr(config, NAME, ...) names a key config DEFINES (or a listed owner)",
              not ghost, ("\n        " + "\n        ".join(ghost[:40])) if ghost else f"{len(files)} files scanned")
        PINS = {"BRK_FLOW_IMBALANCE_MIN": 0.10, "BRK_FLOW_TAGGED_MIN": 0.60, "BRK_REGIME_MAX": 0.0,
                "BRK_DEPTH_DEPLETION_MIN": 0.0, "BRK_ROOM_MIN_R": 1.0, "BRK_R_FLOOR": 1.0,
                "BRK_RANGE_MIN_PCT": 0.0023, "BRK_RANGE_MAX_PCT": 0.0350, "BRK_RANGE_CLEAN_MAX": 0.0,
                "GEX_BFLY_PIN_CONC_MIN": 0.25, "GEX_BFLY_EM_MIN_FRAC": 0.30, "GEX_BFLY_EM_MAX_FRAC": 1.00,
                "GEX_BFLY_SMOOTH_WINDOW": 12, "GEX_BFLY_PERSIST_TICKS": 8, "HANDOFF_TTL_TICKS": 8,
                "RUNAWAY_ATR_FLOOR_PCT": 0.08, "RUNAWAY_ATR_VETO_PCT": 0.05, "RUNAWAY_ATR_DEEP_PCT": 0.20,
                "RUNAWAY_DELTA_NEAR": 0.25, "RUNAWAY_DELTA_DEEP": 0.40, "RUNAWAY_STRENGTH_GRIND": 0.40,
                "RUNAWAY_STRENGTH_RIP": 0.70, "RUNAWAY_BAND_GRIND": 0.5, "RUNAWAY_BAND_RIP": 1.5,
                "SWEEP_CS_MIN_REJECTION_PCT": 0.0002, "SWEEP_CS_ATR_MAX_PCT": 0.20,
                "SWEEP_CS_LEVELS_EACH_SIDE": 3}
        off = {k: getattr(_cfg, k, "<absent>") for k, v in PINS.items() if getattr(_cfg, k, "<absent>") != v}
        hunt = getattr(_cfg, "HUNT_MAX_LOSS_PCT", "<absent>")
        adm = getattr(_cfg, "ADMISSION_RULES", "<absent>")
        if "OT_HUNT_MAX_LOSS_PCT" not in os.environ and hunt != getattr(_cfg, "RUNAWAY_MAX_LOSS_PCT", None):
            off["HUNT_MAX_LOSS_PCT"] = hunt
        if adm is not None:
            off["ADMISSION_RULES"] = adm
        check("A4 the 29 dials config now defines hold the values their modules were using",
              not off, str(off) if off else "27 literals + HUNT follows RUNAWAY_MAX_LOSS_PCT + ADMISSION_RULES None")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_attr_fidelity: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
