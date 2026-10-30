"""
strategy/plan_state.py  v5.2
v5.2  2026-10-30  OTV5 r57 (TCS.LOG1) — TrendCreditSpread's DEFAULT IS LOG: OT_TCS_ACTIVE unset (or empty, or "log", or
      a value nobody recognises, which is named) -> log; "0" / "off" / "dormant" -> dormant; "1" (config.TREND_CREDIT_ACTIVE)
      -> active, unchanged. In LOG the TCS signal runs the real entry and books a SHADOW trade (execution/shadow_book.py),
      never an order. The operator, 2026-10-30: "Can you reactivate TCS Monday as 'log only'? But do not trade it." then
      "Make sure TCS logs everything an executable trade logs." Gate tests/check_tcs_shadow.py.
v5.1  2026-10-27  OTV5 r46 (PARC.1) — PARC joins the table: ("OT_PARC", ACTIVE, HOUR), its state read from
      config.PARC_MODE as PARK's is from PARK_MODE (trade -> active, log -> log, off -> dormant). The operator,
      2026-10-27: "Call it PARC"; "No shadow mode. We're paper. It trades tomorrow." Gate tests/check_parc.py.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
EVERY PLAN HAS ONE OF THREE STATES - ACTIVE, LOG ONLY, DORMANT - AND ONE GATING CATEGORY (PSTATE.1).

v1.0  2026-10-19  OTV4TEST r303 (PSTATE.1). The operator, 2026-10-19 08:34 ET: "Going forward, I want all the
      trades that are turned off to stop writing to the plan Log"; 08:43 ET: "The intent is dormant plans should
      not write to the ledger, unless we are studying them as 'log only' - I would like each plan to have 3
      states: active, dormant or log only, they can be further categorized as hour-gated or conditional gated";
      08:45 ET, on this design: "That looks right to me". ORCS is included ("1. Yes" - it reverses r249's
      "the plan keeps recording"), and CondorManagement / CreditRoll leave the [plans] line while no credit
      position is open ("2. Yes").

THE THREE STATES
  active   evaluated, written, trades - exactly as before.
  log      evaluated and written; anything it would fire is recorded LOG-ONLY and never executed (the r254
           observe mechanism: PlanTick.take() writes LOG-ONLY and opens no plan_ledger row; main.py's
           _log_only doors and the credit door in _execute_condor_leg refuse the signal).
  dormant  NOT evaluated (main._safe_strategy never calls it) and writes NOTHING: no plan_tick, plan_check,
           plan_ledger or plan_heartbeat row, and it is left off the per-minute [plans] line. One line at start
           (main.py) and data/plan_states.json name every plan's state, so the silence is explained (WA §0.5).

THE SWITCH. Each plan keeps the env key it already had; the values are active | log | off. The old spellings
keep their meaning: "1" (and "trade") = active; for a default-OFF trade anything but active/log stays dormant,
exactly as "only the literal 1" did; for a default-ON plan "0" / "off" = dormant. A value nobody recognises
leaves the plan at its DEFAULT state and is named (refused()), never silently obeyed. PARK keeps
config.PARK_MODE (trade -> active, log -> log, off -> dormant); PARC (OTV5 r46) reads config.PARC_MODE the same way. The config flags (ORCS_ENABLED,
SWEEP_CS_ENABLED, TREND_CREDIT_ACTIVE, ATP_BUTTERFLY_ENABLED, GEX_BUTTERFLY_ENABLED) still decide ACTIVE, so a
checker that flips one still flips the trade; "log" is read from the same key at call time.

THE CATEGORIES (declared, read by the startup line, the board and tests/check_plan_states.py)
  hour       asked only inside its clock window (config.ENTRY_WINDOWS).
  condition  asked only while its condition holds, whatever the hour: a management plan while a position of
             its own is open; CondorManagement / CreditRoll while a credit position is open; the condor, which
             has no entry of its own.

⚠️ NOTHING HERE DECIDES A TRADE. With every switch unset the states are today's roster, so no plan that traded
yesterday is stopped and none that was off is started. Never raises: an unreadable state reads as the plan's
DEFAULT (state()), which is the shipped behaviour.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

GATES = {}      # WA §36: this file owns no gate constant

ACTIVE, LOG, DORMANT = "active", "log", "dormant"
STATES = (ACTIVE, LOG, DORMANT)
HOUR, CONDITION = "hour", "condition"

# name -> (switch key shown to the operator, default state, category)
TABLE: Dict[str, Tuple[str, str, str]] = {
    "RunawayContinuation":      ("OT_RUNAWAY",        ACTIVE,  HOUR),
    "Breakout":                 ("OT_BREAKOUT",       ACTIVE,  HOUR),
    "LiquidityHunt":            ("OT_HUNT",           ACTIVE,  HOUR),
    "PARK":                     ("OT_PARK",           ACTIVE,  HOUR),
    "PARC":                     ("OT_PARC",           ACTIVE,  HOUR),     # OTV5 r46 (PARC.1)
    "GEXPinButterfly":          ("OT_GEX_BUTTERFLY",  ACTIVE,  HOUR),
    "ATPButterfly":             ("OT_ATP_BUTTERFLY",  DORMANT, HOUR),
    "VOLT":                     ("OT_VOLT",           DORMANT, HOUR),
    "ORBStrategy":              ("OT_ORB_TRADE",      DORMANT, HOUR),
    "OpeningRangeCreditSpread": ("OT_ORCS",           DORMANT, HOUR),
    "SweepCreditSpread":        ("OT_SWEEP_CS",       DORMANT, HOUR),
    "TrendCreditSpread":        ("OT_TCS_ACTIVE",     LOG,     HOUR),     # OTV5 r57 (TCS.LOG1): unset = log (shadow)
    "IronCondorStrategy":       ("",                  DORMANT, CONDITION),   # no entry of its own (r249)
    "CondorManagement":         ("",                  ACTIVE,  CONDITION),
    "CreditRoll":               ("",                  ACTIVE,  CONDITION),
}
# dispatch labels -> the plan they write under (strategy/plan.DISPATCH_ALIAS, kept in step)
ALIAS = {"ORB": "ORBStrategy", "SweepForLeg2": "SweepCreditSpread",
         "CondorPlan": "IronCondorStrategy", "CondorLeg": "IronCondorStrategy"}

_ON = ("1", "active", "trade", "on")
_OFF = ("0", "off", "dormant")

_REFUSED: Dict[str, str] = {}


def _raw(key: str) -> str:
    """The switch's value as set, read NOW. Each key is read by a literal call so tests/gen_env_doc.py
    documents it where it is read."""
    if key == "OT_RUNAWAY":
        v = os.environ.get("OT_RUNAWAY", "")
    elif key == "OT_BREAKOUT":
        v = os.environ.get("OT_BREAKOUT", "")
    elif key == "OT_HUNT":
        v = os.environ.get("OT_HUNT", "")
    elif key == "OT_VOLT":
        v = os.environ.get("OT_VOLT", "0")
    elif key == "OT_ORB_TRADE":
        v = os.environ.get("OT_ORB_TRADE", "0")
    elif key == "OT_ATP_BUTTERFLY":
        v = os.environ.get("OT_ATP_BUTTERFLY", "0")
    elif key == "OT_ORCS":
        v = os.environ.get("OT_ORCS", "0")
    elif key == "OT_SWEEP_CS":
        v = os.environ.get("OT_SWEEP_CS", "0")
    elif key == "OT_TCS_ACTIVE":
        v = os.environ.get("OT_TCS_ACTIVE", "")       # r57 (TCS.LOG1): unset = log, "0" = dormant
    elif key == "OT_GEX_BUTTERFLY":
        v = os.environ.get("OT_GEX_BUTTERFLY", "1")
    else:
        v = ""
    return str(v or "").strip().lower()


# the config flag that decides ACTIVE for a config-read switch (a checker flips the attribute)
_FLAG = {"OpeningRangeCreditSpread": "ORCS_ENABLED", "SweepCreditSpread": "SWEEP_CS_ENABLED",
         "TrendCreditSpread": "TREND_CREDIT_ACTIVE", "ATPButterfly": "ATP_BUTTERFLY_ENABLED",
         "GEXPinButterfly": "GEX_BUTTERFLY_ENABLED"}


def base(name: str) -> str:
    """'Breakout/manage' -> 'Breakout/manage' (a management plan is its own row); aliases resolve."""
    n = str(name or "")
    return ALIAS.get(n, n)


def known(name: str) -> bool:
    return base(name) in TABLE or base(name).endswith("/manage")


def category(name: str) -> str:
    n = base(name)
    if n.endswith("/manage"):
        return CONDITION
    return TABLE.get(n, ("", ACTIVE, HOUR))[2]


def default(name: str) -> str:
    n = base(name)
    return TABLE.get(n, ("", ACTIVE, HOUR))[1]


def switch(name: str) -> str:
    return TABLE.get(base(name), ("", ACTIVE, HOUR))[0]


def state(name: str) -> str:
    """active | log | dormant for `name`, read now. Unknown names and management plans are ACTIVE (they have
    no switch; a management plan is condition-gated, never switched). Never raises: an error reads DEFAULT."""
    n = base(name)
    try:
        if n.endswith("/manage") or n not in TABLE:
            return ACTIVE
        key, dflt, _cat = TABLE[n]
        if not key:
            return dflt
        if n == "PARK":
            import config as _c
            return {"trade": ACTIVE, "log": LOG, "off": DORMANT}.get(str(getattr(_c, "PARK_MODE", "trade")), ACTIVE)
        if n == "PARC":                                         # OTV5 r46 (PARC.1): config.PARC_MODE decides
            import config as _c
            return {"trade": ACTIVE, "log": LOG, "off": DORMANT}.get(str(getattr(_c, "PARC_MODE", "trade")), ACTIVE)
        raw = _raw(key)
        if n in _FLAG:
            import config as _c
            if bool(getattr(_c, _FLAG[n], dflt == ACTIVE)):
                return ACTIVE
            if raw == "log":
                return LOG
            if dflt == LOG:                                     # r57 (TCS.LOG1): a default-LOG trade
                if raw in _OFF:
                    return DORMANT
                if raw not in ("", "1"):                        # "1" with the flag off: a checker's flip
                    _note(n, key, raw)
                return LOG
            if dflt == ACTIVE and raw not in _OFF and raw not in _ON:
                _note(n, key, raw)
            return DORMANT
        if raw == "log":
            return LOG
        if raw in _ON or (dflt == ACTIVE and raw == ""):
            return ACTIVE
        if raw in _OFF or raw == "":
            return DORMANT
        _note(n, key, raw)
        return dflt
    except Exception:                                           # noqa: BLE001
        return default(n)


def _note(name: str, key: str, raw: str) -> None:
    if name not in _REFUSED:
        _REFUSED[name] = f"{key}={raw!r}"
        logger.warning("[plans] %s=%r is not active / log / off - %s stays %s (its default)",
                       key, raw, name, default(name))


def refused() -> Dict[str, str]:
    """Switch values that were not understood this process (name -> 'KEY=value')."""
    return dict(_REFUSED)


def is_dormant(name: str) -> bool:
    return state(name) == DORMANT


def is_log(name: str) -> bool:
    return state(name) == LOG


def summary(names=None) -> str:
    """One line for the log: every plan's state and category, grouped."""
    rows = sorted(set(TABLE) | set(names or ()))
    groups = {ACTIVE: [], LOG: [], DORMANT: []}
    for n in rows:
        groups[state(n)].append(f"{n}({category(n)})")
    out = " · ".join(f"{s}: {', '.join(groups[s]) or '-'}" for s in STATES)
    bad = refused()
    if bad:
        out += " · REFUSED: " + ", ".join(bad.values())
    return out


def write_states_file(path: str = "", names=None) -> bool:
    """data/plan_states.json - what the devtools plans panel reads (it cannot see the unit's environment).
    Never raises; False when it could not be written (and says so)."""
    try:
        if not path:
            path = os.environ.get("OT_PLAN_STATES_FILE", "") or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "plan_states.json")
        rows = sorted(set(TABLE) | set(names or ()))
        doc = {"written_epoch": time.time(), "pid": os.getpid(),
               "plans": {n: {"state": state(n), "category": category(n), "switch": switch(n)} for n in rows},
               "refused": refused()}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
        return True
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[plans] plan_states.json not written (%s: %s) - the plans panel will not know which "
                       "plans are dormant", type(exc).__name__, exc)
        return False


def read_states_file(path: str = "") -> dict:
    """The bot's last published states ({} when absent or unreadable)."""
    try:
        if not path:
            path = os.environ.get("OT_PLAN_STATES_FILE", "") or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "plan_states.json")
        with open(path) as fh:
            return json.load(fh)
    except Exception:                                           # noqa: BLE001
        return {}
