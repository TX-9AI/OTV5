"""
utils/box_flags.py  v5.3
v5.3  2026-11-24  OTV5 r155 (BOXF.2, M4) — THE `park` KEY: setup PARK, on / off, DEFAULT ON (so no box changes when this
      lands; a box differs only through its own file line `park = off`). The operator, 2026-11-24: "Yes" (the design's M4,
      ahead of the C5 equity boxes going live with Runaway only). strategy/plan_state reads PARK's state from it (on ->
      ACTIVE, anything else -> DORMANT: never asked, writes nothing; an open PARK row is still managed to its exit, exits
      read no flag). OT_PARK is no longer read anywhere (config.PARK_MODE / PARK_ENV_REFUSED are deleted): REPLACED_ENV
      names it, and stale_env() reports only that the key is PRESENT in the process environment (its value is never
      read), which start_line() names as IGNORED on the [flags] line and main pages once. Schema v1 keeps its number: a
      key added, none changed.
v5.2  2026-11-23  OTV5 r153 (TRIM.2) — THE `ogap` KEY GOES: OGAP is retired (strategy/plan_state: DORMANT, no switch). The
      operator, 2026-11-23: "The hunt & OGAP are trash. Retire them both after this session today." SCHEMA is empty
      again (schema v1: no keys, r148's shape), so a box file line `ogap = ...` is an UNKNOWN KEY: ignored, named on the
      [flags] start line as REFUSED (main pages it once), and it can turn nothing on; tests/check_box_flags F3 refuses
      such a line at land. The mechanism is unchanged and waits for its next key.
v5.1  2026-11-22  OTV5 r149 (OGAP.4, M1) — THE FIRST KEY: `ogap` (setup OGAP, on / off, DEFAULT ON). The operator,
      2026-11-22: "If we're studying that trade, I don't understand why we're only testing it on one box. I honestly want
      it paper Trading on all of them." So OGAP runs on every box with no file line (the design drafted default off with
      `ogap = on` for QQQ; the ruling made it on everywhere, so no box needs a line). strategy/plan_state reads it for
      OGAP's state (on -> ACTIVE, off -> DORMANT); OGAP also sits out on a LIVE box (plan_state; until delivery P's
      paper_only, which this schema still refuses). Schema v1 keeps its number: a key added, none changed.
v5.0  2026-11-22  OTV5 r148 (BOXF.1) — new. ONE SAVED SETTINGS FILE PER BOX, READ ONCE AT START, AND ONE SCHEMA THAT IS
      THE FLEET ROSTER. The operator, 2026-11-22: "each box should maintain a 'flag' file — essentially a configure file,
      but not user toggled ... saved settings, not user interactive"; "Design it smartly. I don't want redundant gates
      blocking common use settings by having to track them in multiple places." The design
      (~/reviews/design/BOX_FLAGS_20261122/DESIGN.md) is approved for building; its recommended answers are the rules
      (the operator, 2026-11-22): fail closed but start; a file holds only the lines where the box differs from the
      default; L1 (this mechanism) then M1 (OGAP) before 2026-12-04.

      THE FILE. deploy/box_flags/<SYM> (SYM = config.INSTRUMENT), plain text: blank lines, "# comment" lines and
      "key = value  # reason" lines, one key per line. It holds ONLY the lines where this box differs from the default
      (tests/check_box_flags.py F6 refuses a line that restates one), so a default changed in SCHEMA reaches every box.
      A missing file means the box runs on the defaults. It changes only through a land (git is the audit trail) and
      reaches the box with the normal fleet update. No menu item, no prompt, no env key.

      THE SCHEMA. SCHEMA below is the one place the keys, their setups, their allowed values and their defaults live.
      r148 ships it EMPTY (schema v1, no keys): with no key no file can say anything, so the start line never claims what
      the code does not do. A key joins it in its own land (M1: ogap; M2-M4: hunt, runaway, park). Until delivery P lands,
      the allowed values are "on" and "off" only; "paper_only" is refused like any other bad value.

      WHO READS IT. Only this module opens deploy/box_flags (check_box_flags F8). The bot calls load() in-process; control
      runs the same code as a command (tools/box_flags_show.py), so there is one parser and dtp keeps no copy of it.
      effective() is the process's one frozen load: the first call reads the file, every later call returns the same
      Flags, so a file changed on disk by a mid-session bake takes effect at the next process start.

      FAIL CLOSED, BUT THE BOT ALWAYS STARTS (a box that will not start cannot manage exits or record data):
        missing file                -> the defaults; source=none (defaults)
        unknown key                 -> ignored, named
        a known key, a bad value    -> THAT setup reads "off", named (a typo of "off" must never turn a setup on)
        a duplicate known key       -> that setup reads "off", named
        a malformed line            -> named; when its first word is a known key, that setup reads "off"
        exists but unreadable       -> EVERY schema setup reads "off", named
      Every problem is named on the one [flags] start line (main pages it once). The land gate makes each of them
      unlandable, so in practice only disk damage can produce one. NEVER RAISES from load() or effective().
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

GATES = {}      # WA §36: this file owns no gate constant

SCHEMA_VERSION = 1
ON, OFF = "on", "off"
VALUES = (ON, OFF)                         # until delivery P; "paper_only" is refused until then
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGS_REL = "deploy/box_flags"
FLAGS_DIR = os.path.join(ROOT, *FLAGS_REL.split("/"))
README = "README"                          # the format note in FLAGS_DIR; never a symbol file
_LINE = re.compile(r"^([A-Za-z0-9_]+)[ \t]*=[ \t]*([A-Za-z0-9_]+)[ \t]*(#.*)?$")


@dataclass(frozen=True)
class Key:
    """One schema row: the key a file may set, the plan_state name it decides, its allowed values, its default."""
    key: str
    setup: str
    allowed: Tuple[str, ...] = VALUES
    default: str = ON


# THE ROSTER. r148 (BOXF.1): empty; each key joins in its own land. r149 (OGAP.4): ogap, default on.
# r153 (TRIM.2): ogap removed with OGAP's retirement; empty again. r155 (BOXF.2, M4): park, default on.
SCHEMA: Dict[str, Key] = {
    "park": Key("park", "PARK", VALUES, ON),     # r155: on every box unless its file says off (the operator, 2026-11-24)
}

# r155 (M4) — the env keys a schema key replaced. NOT READ: only their presence in the process environment is reported
# (stale_env), so a stale unit line is named on the [flags] start line instead of being thought obeyed.
REPLACED_ENV: Dict[str, str] = {"OT_PARK": "park"}


@dataclass(frozen=True)
class Flags:
    """What one load found. `values` holds the effective value of EVERY schema key."""
    symbol: str
    source: str                            # "deploy/box_flags/QQQ" | "none (defaults)"
    sha256: str                            # the file's first 12 hex, "-" when there is no file
    status: str                            # "ok" | "missing" | "unreadable"
    values: Dict[str, str] = field(default_factory=dict)
    problems: Tuple[str, ...] = ()
    differs: Tuple[str, ...] = ()          # "key(value, default d)" for each key off its default

    def value(self, key: str) -> str:
        return self.values.get(key, "")


def path_for(symbol: str, root: str = "") -> str:
    return os.path.join(root or FLAGS_DIR, str(symbol or "").upper())


def files(root: str = "") -> Tuple[str, ...]:
    """The box files present (their names = symbols), README and dotfiles excluded. () when the folder is absent."""
    d = root or FLAGS_DIR
    try:
        return tuple(sorted(n for n in os.listdir(d)
                            if n != README and not n.startswith(".") and os.path.isfile(os.path.join(d, n))))
    except Exception:                                           # noqa: BLE001
        return ()


def parse(text: str, schema: Optional[Dict[str, Key]] = None):
    """(set_values, problems, lines). PURE. set_values = {key: value} for the keys this text sets (a bad, duplicate or
    malformed known key reads OFF); problems = what was refused, by line; lines = [(lineno, key, value)] of every
    well-formed key line, known or not (the gate's F5 / F6 read them)."""
    schema = SCHEMA if schema is None else schema
    out: Dict[str, str] = {}
    problems = []
    lines = []
    seen = set()
    for n, raw in enumerate(str(text).splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        m = _LINE.match(s)
        if not m:
            first = re.split(r"[\s=#]+", s, maxsplit=1)[0]
            if first in schema:
                out[first] = OFF
                problems.append("line %d malformed (%r): %s reads off" % (n, s[:60], first))
            else:
                problems.append("line %d malformed (%r): ignored" % (n, s[:60]))
            continue
        k, v = m.group(1), m.group(2)
        lines.append((n, k, v))
        if k not in schema:
            problems.append("line %d unknown key %r: ignored (schema v%d: %s)"
                            % (n, k, SCHEMA_VERSION, ", ".join(sorted(schema)) or "no keys"))
            continue
        if k in seen:
            out[k] = OFF
            problems.append("line %d duplicate key %r: %s reads off" % (n, k, k))
            continue
        seen.add(k)
        if v not in schema[k].allowed:
            out[k] = OFF
            problems.append("line %d %s = %r is not one of %s: %s reads off"
                            % (n, k, v, "/".join(schema[k].allowed), k))
            continue
        out[k] = v
    return out, problems, lines


def load(symbol: str = "", path: str = "", schema: Optional[Dict[str, Key]] = None) -> Flags:
    """Read one box's file. `symbol` defaults to config.INSTRUMENT; `path` overrides the file (tests, the show tool's
    --root). NEVER RAISES: anything unexpected reads as an unreadable file (every setup off), named."""
    schema = SCHEMA if schema is None else schema
    sym = str(symbol or "").upper()
    if not sym:
        try:
            import config as _c
            sym = str(getattr(_c, "INSTRUMENT", "") or "").upper()
        except Exception:                                       # noqa: BLE001
            sym = ""
    p = path or path_for(sym)
    rel = p[len(ROOT) + 1:] if p.startswith(ROOT + os.sep) else p
    defaults = {k: r.default for k, r in schema.items()}
    try:
        if not os.path.lexists(p):
            return Flags(sym, "none (defaults)", "-", "missing", dict(defaults))
        with open(p, "rb") as fh:
            blob = fh.read()
        text = blob.decode("utf-8")
    except Exception as exc:                                    # noqa: BLE001
        return Flags(sym, rel, "-", "unreadable", {k: OFF for k in schema},
                     ("%s UNREADABLE (%s: %s): every setup reads off" % (rel, type(exc).__name__, exc),))
    try:
        got, problems, _lines = parse(text, schema)
        vals = dict(defaults)
        vals.update(got)
        differs = tuple("%s(%s, default %s)" % (k, vals[k], defaults[k])
                        for k in sorted(schema) if vals[k] != defaults[k])
        return Flags(sym, rel, hashlib.sha256(blob).hexdigest()[:12], "ok", vals, tuple(problems), differs)
    except Exception as exc:                                    # noqa: BLE001
        return Flags(sym, rel, "-", "unreadable", {k: OFF for k in schema},
                     ("%s UNPARSEABLE (%s: %s): every setup reads off" % (rel, type(exc).__name__, exc),))


_EFFECTIVE: Dict[str, Flags] = {}


def effective() -> Flags:
    """THE process's flags: loaded on the first call, the same object on every later call (read once, at start)."""
    f = _EFFECTIVE.get("flags")
    if f is None:
        f = load()
        _EFFECTIVE["flags"] = f
    return f


def value(key: str) -> str:
    """The effective value of schema key `key` for this process ("" for a key not in the schema)."""
    return effective().value(key)


def commit() -> str:
    """The 10-character commit this tree is at, or "unknown". Read once per call by subprocess; the bot calls it once."""
    try:
        r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short=10", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        return (r.stdout or "").strip() or "unknown"
    except Exception:                                           # noqa: BLE001
        return "unknown"


def stale_env(environ=None) -> Tuple[str, ...]:
    """r155 — the REPLACED_ENV keys PRESENT in `environ` (default: this process's), sorted. Presence only: the value is
    never read, so no env key can decide anything a schema key decides. Never raises."""
    try:
        env = os.environ if environ is None else environ
        return tuple(k for k in sorted(REPLACED_ENV) if k in env)
    except Exception:                                           # noqa: BLE001
        return ()


def ignored_notes(names) -> Tuple[str, ...]:
    """r155 — the REFUSED text for each stale env key: "OT_PARK in the unit is IGNORED (deploy/box_flags decides park)"."""
    return tuple("%s in the unit is IGNORED (deploy/box_flags decides %s)" % (k, REPLACED_ENV.get(k, "?"))
                 for k in names)


def start_line(flags: Flags, commit_id: str, ignored=()) -> str:
    """The one [flags] start line (tests/check_box_flags.py F10 pins its shape). `ignored` (r155): stale env keys
    (stale_env()), named after the file's own problems in the REFUSED part."""
    head = "[flags] %s source=%s sha256=%s commit=%s" % (flags.symbol or "?", flags.source, flags.sha256,
                                                        commit_id or "unknown")
    keys = sorted(flags.values)
    vals = " ".join("%s=%s" % (k, flags.values[k]) for k in keys) if keys else "schema v%d: no keys" % SCHEMA_VERSION
    line = "%s · %s · differs: %s" % (head, vals, ", ".join(flags.differs) or "none")
    refused = tuple(flags.problems) + ignored_notes(ignored or ())
    if refused:
        line += " · REFUSED: " + "; ".join(refused)
    return line


def reset() -> None:
    """Tests only: forget the process's frozen load."""
    _EFFECTIVE.clear()
