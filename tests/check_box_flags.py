#!/usr/bin/env python3
"""
tests/check_box_flags.py  v5.2
v5.2  2026-11-26  OTV5 r161 (LANE.1) — paper_only IS A LANE: F4 allows it for every real key (utils/box_flags.LANES);
      F7's real-schema case `park = paper_only` now reads paper_only with nothing refused and differs
      "park(paper_only, default on)" and the start line keeps its pinned shape (" · park=paper_only · "; the stand-in
      on/off key still refuses it, so a narrowed Key still works); F12's park row is (park, PARK, (on, off,
      paper_only), on). The operator, 2026-11-25: "I want park paperwalled until we enable it on the cash side".
v5.1  2026-11-24  OTV5 r155 (BOXF.2, M4) — THE `park` KEY. The operator, 2026-11-24: "Yes" (the design's M4). F7 gains the
      real schema's park cases (missing -> on; `park = off` -> off, nothing refused; `park = of`, a duplicate `park` and
      `park = paper_only` -> off, named; a stray `ogap = on` -> ignored, named, park untouched); NEW F8b (no module
      outside tests/ reads a REPLACED_ENV key - r155: OT_PARK - by os.environ.get / getenv / [] / "in"; every REPLACED_ENV
      key names a SCHEMA key); F10 gains the stale-env case (start_line names "OT_PARK in the unit is IGNORED (deploy/
      box_flags decides park)" in its REFUSED part; main._announce_box_flags with OT_PARK in the env logs ONE WARNING
      [flags] line and pages ONCE, code MSG, naming it); NEW F12 (SCHEMA["park"] = park / PARK / on, off / default on, and
      every schema key's setup is a strategy/plan_state TABLE row whose default is FLAG, so the default has no second
      copy). OT_PARK is popped from this checker's env so F10's INFO case never depends on the caller. Every other check
      unchanged.
v5.0  2026-11-22  OTV5 r148 (BOXF.1) — new. THE BOX FLAG FILES AND THEIR ONE LOADER. The operator, 2026-11-22: "Design it
      smartly. I don't want redundant gates blocking common use settings by having to track them in multiple places."
      So this gate validates the ONE file per box and the ONE loader, and NEVER compares a setting with another copy of
      it (no second copy exists: the schema in utils/box_flags.py is the roster, a file only overrides it).

  F1  every file in deploy/box_flags (README aside) is named for a listed symbol (config.STRIKE_INCREMENTS)
  F2  every line of every file parses (blank, "# comment" or "key = value  # reason")
  F3  every key is in utils/box_flags.SCHEMA
  F4  every value is allowed for its key (r161: on / off / paper_only, utils/box_flags.LANES)
  F5  no file sets a key twice
  F6  NO LINE RESTATES THE DEFAULT (so a default changed in SCHEMA reaches every box)
  F7  the loader, on fixtures with a stand-in schema: a missing file -> the defaults, source "none (defaults)"; a bad
      value, a duplicate and a malformed known key -> THAT setup off; an unknown key -> ignored; "paper_only" ->
      refused, off; an unreadable file (a directory in its place) -> EVERY setup off; each case named; never raises;
      effective() loads once and returns the same object (a later change on disk is not seen)
  F8  only utils/box_flags.py names the folder (deploy/box_flags) or its FLAGS_DIR in code: no other module opens it.
  F8b (r155) no module outside tests/ reads a utils/box_flags.REPLACED_ENV key (OT_PARK; OT_RUNAWAY joins with M3), and
      each REPLACED_ENV key names a SCHEMA key
  F9  nothing writes the folder: no installer, menu or deploy script (configure.sh, setup_ec2.sh, devtools.sh,
      bootstrap.example.sh, deploy/*, tools/*.sh) names it, and the show tool and the loader hold no write call; when
      ~/day_trader_pro is present, no dtp line names the folder AND writes (a fixture or a docstring that only names it
      is a read; control reads only the show tool's output)
  F10 the start line: start_line() has the pinned shape for a missing file, an ok file with differences and a refused
      line; main._announce_box_flags() logs exactly ONE [flags] line through main's logger, before _announce_plan_states
      on the start path, WARNING plus ONE page (code MSG) when a line is refused, INFO and no page otherwise
  F11 tools/box_flags_show.py (run as `python3 -I`) prints the same effective values as the loader, as JSON, reading
      no env key
  F12 (r155) SCHEMA["park"] is (park, PARK, (on, off), on); every SCHEMA key's setup is a strategy/plan_state TABLE row
      whose default is FLAG (the schema is the one copy of the default)
Born red on r146 (df51252): utils/box_flags.py, tools/box_flags_show.py and main._announce_box_flags do not exist
(F7-F11 red; F1-F6 green on an absent folder). 11 mutants red. v5.1 is red on r154 (b8f21c1) at F7, F8b, F10 and F12.
Run:  python3 tests/check_box_flags.py
"""
import ast
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ.pop("OT_PARK", None)                 # r155: F10's INFO case must not depend on the caller's env
_TD = tempfile.mkdtemp(prefix="check_box_flags_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ.setdefault(_k, os.path.join(_TD, _f))
FAILED = []
FOLDER = "deploy/box_flags"
LINE_RX = re.compile(r"^\[flags\] [A-Z0-9?]+ source=(none \(defaults\)|deploy/box_flags/[A-Z0-9]+|\S+) "
                     r"sha256=([0-9a-f]{12}|-) commit=(\S+) · (schema v\d+: no keys|([a-z0-9_]+=[a-z_]+)( [a-z0-9_]+=[a-z_]+)*)"
                     r" · differs: (none|.+?)( · REFUSED: .+)?$")


def check(name, ok, detail=""):
    print(f"  {name:<4} {'PASS' if ok else 'FAIL'}  {'' if ok else detail}")
    if not ok:
        FAILED.append(name)


def _code_files():
    out = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "venv", ".venv", "node_modules")]
        for f in fn:
            if f.endswith((".py", ".sh")) or f in ("configure.sh",):
                out.append(os.path.relpath(os.path.join(dp, f), ROOT))
    return sorted(out)


WRITE_RX = re.compile(r"open\([^)]*['\"][wax]b?\+?['\"]|\.write(_text)?\(|(^|[\s;|&])(>|>>|tee|cp|mv|install|rsync|"
                      r"sed\s+-i|truncate|rm)(\s|$)|shutil\.|os\.(replace|rename|remove|unlink)\(")


def dtp_writers(root):
    """F9's dtp half: a dtp line that names the folder AND writes (a write open, > / >>, tee, cp, mv, sed -i, rm,
    shutil, os.replace ...). A line that only NAMES it (a log fixture's source=deploy/box_flags/SPX, a docstring) is
    reading, and control reads only the show tool's output."""
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "venv", ".venv", "data", "logs", "reports")]
        for f in fn:
            if not f.endswith((".py", ".sh", ".prompt", ".service", ".timer")):
                continue
            pp = os.path.join(dp, f)
            try:
                for i, ln in enumerate(open(pp, encoding="utf-8", errors="replace"), 1):
                    if "box_flags/" in ln and WRITE_RX.search(ln):
                        out.append(f"dtp {os.path.relpath(pp, root)}:{i} writes the folder: {ln.strip()[:80]!r}")
            except OSError:
                pass
    return out


def main():
    print("check_box_flags")
    try:
        from utils import box_flags as BF
    except Exception as exc:                                    # noqa: BLE001
        BF = None
        print(f"  (utils/box_flags not importable: {type(exc).__name__}: {exc})")
    import config

    folder = os.path.join(ROOT, *FOLDER.split("/"))
    names = sorted(n for n in (os.listdir(folder) if os.path.isdir(folder) else [])
                   if n != "README" and not n.startswith("."))

    # ── F1-F6 the files ─────────────────────────────────────────────────────
    listed = set(getattr(config, "STRIKE_INCREMENTS", {}) or {})
    bad1 = [n for n in names if n not in listed or not os.path.isfile(os.path.join(folder, n))]
    check("F1", not bad1, f"not a listed symbol (or not a plain file): {bad1}")
    schema = getattr(BF, "SCHEMA", {}) if BF else {}
    bad2, bad3, bad4, bad5, bad6 = [], [], [], [], []
    for n in names:
        try:
            text = open(os.path.join(folder, n), encoding="utf-8").read()
        except Exception as exc:                                # noqa: BLE001
            bad2.append(f"{n}: unreadable ({exc})")
            continue
        seen = set()
        for i, raw in enumerate(text.splitlines(), 1):
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            m = re.match(r"^([a-z0-9_]+)[ \t]*=[ \t]*([a-z0-9_]+)[ \t]*(#.*)?$", s)
            if not m:
                bad2.append(f"{n}:{i} {s[:50]!r}")
                continue
            k, v = m.group(1), m.group(2)
            if k not in schema:
                bad3.append(f"{n}:{i} {k}")
                continue
            if v not in schema[k].allowed:
                bad4.append(f"{n}:{i} {k}={v} (allowed {'/'.join(schema[k].allowed)})")
            if k in seen:
                bad5.append(f"{n}:{i} {k}")
            seen.add(k)
            if v == schema[k].default:
                bad6.append(f"{n}:{i} {k} = {v} is the default")
    check("F2", not bad2, f"unparseable lines: {bad2}")
    check("F3", not bad3, f"keys not in SCHEMA (schema v{getattr(BF, 'SCHEMA_VERSION', '?')}: "
                          f"{', '.join(sorted(schema)) or 'no keys'}): {bad3}")
    check("F4", not bad4, f"values not allowed: {bad4}")
    check("F5", not bad5, f"duplicate keys: {bad5}")
    check("F6", not bad6, f"lines restating the default (delete them): {bad6}")

    # ── F7 the loader ───────────────────────────────────────────────────────
    ok7, d7 = False, "utils/box_flags missing"
    if BF is not None:
        try:
            S = {"alpha": BF.Key("alpha", "SetupA", ("on", "off"), "on"),
                 "beta": BF.Key("beta", "SetupB", ("on", "off"), "off")}
            td = tempfile.mkdtemp(prefix="bf_", dir=_TD)

            def put(name, text):
                p = os.path.join(td, name)
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(text)
                return p
            miss = BF.load("QQQ", path=os.path.join(td, "NOPE"), schema=S)
            good = BF.load("QQQ", path=put("G", "# c\n\nbeta = on   # why\n"), schema=S)
            badv = BF.load("QQQ", path=put("B", "alpha = maybe\nbeta = on\n"), schema=S)
            papo = BF.load("QQQ", path=put("P", "alpha = paper_only\n"), schema=S)
            dup = BF.load("QQQ", path=put("D", "beta = on\nbeta = on\n"), schema=S)
            malf = BF.load("QQQ", path=put("M", "alpha on\n"), schema=S)
            unk = BF.load("QQQ", path=put("U", "breakout = on\n"), schema=S)
            os.mkdir(os.path.join(td, "X"))
            unr = BF.load("QQQ", path=os.path.join(td, "X"), schema=S)
            nul = BF.load("QQQ", path=put("N", "alpha = off\n"), schema={})
            checks = {
                "missing": (miss.status == "missing" and miss.source == "none (defaults)" and miss.sha256 == "-"
                            and miss.values == {"alpha": "on", "beta": "off"} and not miss.problems),
                "ok": (good.status == "ok" and good.values == {"alpha": "on", "beta": "on"} and not good.problems
                       and good.differs == ("beta(on, default off)",) and re.fullmatch(r"[0-9a-f]{12}", good.sha256)),
                "bad value": (badv.values == {"alpha": "off", "beta": "on"} and len(badv.problems) == 1
                              and "alpha" in badv.problems[0] and "'maybe'" in badv.problems[0]),
                "paper_only": papo.values["alpha"] == "off" and "paper_only" in " ".join(papo.problems),
                "duplicate": dup.values["beta"] == "off" and "duplicate" in " ".join(dup.problems),
                "malformed": malf.values["alpha"] == "off" and "malformed" in " ".join(malf.problems),
                "unknown": (unk.values == {"alpha": "on", "beta": "off"} and "unknown key 'breakout'"
                            in " ".join(unk.problems)),
                "unreadable": (unr.status == "unreadable" and unr.values == {"alpha": "off", "beta": "off"}
                               and "UNREADABLE" in " ".join(unr.problems)),
                "empty schema": nul.values == {} and "unknown key 'alpha'" in " ".join(nul.problems),
            }
            # r155 (M4): the real schema's park key
            if "park" in BF.SCHEMA:
                r_miss = BF.load("QQQ", path=os.path.join(td, "NOPE"))
                r_off = BF.load("QQQ", path=put("RO", "park = off  # C5\n"))
                r_typo = BF.load("QQQ", path=put("RT", "park = of\n"))
                r_dup = BF.load("QQQ", path=put("RD", "park = off\npark = off\n"))
                r_pap = BF.load("QQQ", path=put("RP", "park = paper_only\n"))
                r_ogap = BF.load("QQQ", path=put("RG", "ogap = on\n"))
                checks.update({
                    "park missing": r_miss.values.get("park") == "on" and not r_miss.problems,
                    "park off": (r_off.values.get("park") == "off" and not r_off.problems
                                 and r_off.differs == ("park(off, default on)",)),
                    "park typo": r_typo.values.get("park") == "off" and "'of'" in " ".join(r_typo.problems),
                    "park duplicate": r_dup.values.get("park") == "off" and "duplicate" in " ".join(r_dup.problems),
                    "park paper_only": (r_pap.values.get("park") == "paper_only" and not r_pap.problems   # r161
                                        and r_pap.differs == ("park(paper_only, default on)",)
                                        and " · park=paper_only · " in BF.start_line(r_pap, "c")),
                    "stray ogap": (r_ogap.values.get("park") == "on"
                                   and "unknown key 'ogap'" in " ".join(r_ogap.problems)),
                })
            else:
                checks["park key"] = False
            BF.reset()
            e1 = BF.effective()
            e2 = BF.effective()
            checks["once"] = e1 is e2
            BF.reset()
            ok7 = all(checks.values())
            d7 = "failed: " + ", ".join(k for k, v in checks.items() if not v) + f" | badv={badv} unr={unr}"
            shutil.rmtree(td, ignore_errors=True)
        except Exception as exc:                                # noqa: BLE001
            d7 = f"{type(exc).__name__}: {exc}"
    check("F7", ok7, d7)

    # ── F8 one reader ───────────────────────────────────────────────────────
    allowed8 = {"utils/box_flags.py", "tests/check_box_flags.py"}
    bad8 = []
    for rel in _code_files():
        if rel in allowed8:
            continue
        try:
            src = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if rel.endswith(".py"):
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and "box_flags/" in node.value \
                        and "\n" not in node.value:             # a docstring may describe the folder
                    bad8.append(f"{rel}:{node.lineno} names {node.value[:40]!r}")
                if isinstance(node, ast.Attribute) and node.attr == "FLAGS_DIR":
                    bad8.append(f"{rel}:{node.lineno} reads FLAGS_DIR")
                if isinstance(node, ast.Name) and node.id == "FLAGS_DIR":
                    bad8.append(f"{rel}:{node.lineno} reads FLAGS_DIR")
        elif "box_flags/" in src:
            bad8.append(f"{rel} names the folder")
    check("F8", BF is not None and not bad8, f"other readers: {bad8}" if BF is not None else "no loader")

    # ── F8b no module reads a replaced env key (r155) ───────────────────────
    rep = dict(getattr(BF, "REPLACED_ENV", {}) or {}) if BF else {}
    bad8b = []
    if "OT_PARK" not in rep:
        bad8b.append(f"REPLACED_ENV lacks OT_PARK: {rep}")
    bad8b += [f"REPLACED_ENV {k} -> {v} is not a SCHEMA key" for k, v in rep.items() if v not in schema]
    for rel in _code_files():
        if not rel.endswith(".py") or rel.startswith("tests/"):
            continue
        try:
            tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read())
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Call) and node.args and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("get", "getenv", "pop", "setdefault"):
                key = node.args[0]
            elif isinstance(node, ast.Subscript):
                key = node.slice
            elif isinstance(node, ast.Compare):
                key = node.left
            if isinstance(key, ast.Constant) and key.value in rep:
                bad8b.append(f"{rel}:{node.lineno} reads {key.value}")
    check("F8b", BF is not None and not bad8b, f"{bad8b}")

    # ── F9 nothing writes it ────────────────────────────────────────────────
    bad9 = []
    for rel in _code_files():
        if not rel.endswith(".sh"):
            continue
        src = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
        if "box_flags" in src:
            bad9.append(f"{rel} names box_flags")
    for rel in ("utils/box_flags.py", "tools/box_flags_show.py"):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            bad9.append(f"{rel} missing")
            continue
        src = open(p, encoding="utf-8").read()
        for pat in (r"open\([^)]*['\"][wax]b?\+?['\"]", r"\.write\(", r"os\.(remove|unlink|rename|replace|makedirs|mkdir)\(",
                    r"shutil\."):
            if re.search(pat, src):
                bad9.append(f"{rel} holds a write call ({pat})")
    dtp = os.path.expanduser("~/day_trader_pro")
    dtp_note = "dtp not present: its half not checked here"
    if os.path.isdir(os.path.join(dtp, ".git")):
        dtp_note = "dtp checked"
        bad9 += dtp_writers(dtp)
    check("F9", not bad9, f"writers: {bad9}")
    print(f"       ({dtp_note})")

    # ── F10 the start line ──────────────────────────────────────────────────
    ok10, d10 = False, "no loader"
    if BF is not None:
        try:
            import main as MN
            l_miss = BF.start_line(BF.Flags("QQQ", "none (defaults)", "-", "missing", {}), "df51252070")
            l_ok = BF.start_line(BF.Flags("QQQ", "deploy/box_flags/QQQ", "0123456789ab", "ok",
                                          {"hunt": "off", "ogap": "on"}, (), ("hunt(off, default on)",)), "abc")
            l_bad = BF.start_line(BF.Flags("SPX", "deploy/box_flags/SPX", "0123456789ab", "ok", {"ogap": "off"},
                                           ("line 1 ogap = 'of' is not one of on/off: ogap reads off",),
                                           ("ogap(off, default on)",)), "abc")
            shapes = (l_miss == "[flags] QQQ source=none (defaults) sha256=- commit=df51252070 · schema v1: no keys"
                                " · differs: none"
                      and l_ok == ("[flags] QQQ source=deploy/box_flags/QQQ sha256=0123456789ab commit=abc · "
                                   "hunt=off ogap=on · differs: hunt(off, default on)")
                      and l_bad.endswith(" · REFUSED: line 1 ogap = 'of' is not one of on/off: ogap reads off")
                      and all(LINE_RX.match(x) for x in (l_miss, l_ok, l_bad)))

            class _Cap(logging.Handler):
                def __init__(self):
                    super().__init__(logging.DEBUG)
                    self.recs = []

                def emit(self, r):
                    self.recs.append(r)
            cap = _Cap()
            MN.logger.addHandler(cap)
            pages = []

            class _AM:
                def _send(self, msg, code="MSG", **k):
                    pages.append((code, msg))
                    return True
            s_am = MN.get_alert_manager
            MN.get_alert_manager = lambda: _AM()
            try:
                BF.reset()
                MN._announce_box_flags()
                r0 = [r for r in cap.recs if "[flags]" in r.getMessage()]
                p0 = list(pages)
                cap.recs.clear()
                BF._EFFECTIVE["flags"] = BF.Flags("QQQ", "deploy/box_flags/QQQ", "0123456789ab", "ok", {},
                                                  ("line 1 unknown key 'breakout': ignored (schema v1: no keys)",))
                MN._announce_box_flags()
                r1 = [r for r in cap.recs if "[flags]" in r.getMessage()]
                p1 = pages[len(p0):]
                # r155: a stale OT_PARK in the unit (presence only) is named and paged once
                BF.reset()
                cap.recs.clear()
                n_before = len(pages)
                os.environ["OT_PARK"] = "off"
                try:
                    MN._announce_box_flags()
                finally:
                    os.environ.pop("OT_PARK", None)
                r2 = [r for r in cap.recs if "[flags]" in r.getMessage()]
                p2 = pages[n_before:]
            finally:
                MN.get_alert_manager = s_am
                MN.logger.removeHandler(cap)
                BF.reset()
            want0 = BF.start_line(BF.load(), BF.commit())
            src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
            i_f, i_p = src.find("    _announce_box_flags()  "), src.find("    _announce_plan_states()  ")
            order = 0 < i_f < i_p and src.count("    _announce_box_flags()  ") == 1
            ign = "OT_PARK in the unit is IGNORED (deploy/box_flags decides park)"
            l_ign = BF.start_line(BF.Flags("UNH", "deploy/box_flags/UNH", "0123456789ab", "ok", {"park": "off"}, (),
                                           ("park(off, default on)",)), "abc", ("OT_PARK",))
            stale = (l_ign == ("[flags] UNH source=deploy/box_flags/UNH sha256=0123456789ab commit=abc · park=off · "
                               "differs: park(off, default on) · REFUSED: " + ign)
                     and LINE_RX.match(l_ign) is not None
                     and len(r2) == 1 and r2[0].levelno == logging.WARNING and r2[0].getMessage().endswith(ign)
                     and len(p2) == 1 and p2[0][0] == "MSG" and "OT_PARK" in p2[0][1])
            ok10 = (shapes and stale and len(r0) == 1 and r0[0].levelno == logging.INFO and r0[0].getMessage() == want0
                    and LINE_RX.match(want0) is not None and p0 == []
                    and len(r1) == 1 and r1[0].levelno == logging.WARNING and "REFUSED: line 1 unknown key" in
                    r1[0].getMessage() and len(p1) == 1 and p1[0][0] == "MSG" and "breakout" in p1[0][1] and order)
            d10 = (f"stale={stale} l_ign={l_ign!r} r2={[(r.levelno, r.getMessage()[-90:]) for r in r2]} p2={p2} "
                   f"shapes={shapes} r0={[r.getMessage() for r in r0]} want0={want0!r} p0={p0} "
                   f"r1={[(r.levelno, r.getMessage()[:80]) for r in r1]} p1={p1} order={order}")
        except Exception as exc:                                # noqa: BLE001
            d10 = f"{type(exc).__name__}: {exc}"
    check("F10", ok10, d10)

    # ── F11 the show tool ───────────────────────────────────────────────────
    ok11, d11 = False, "no tool"
    tool = os.path.join(ROOT, "tools", "box_flags_show.py")
    if BF is not None and os.path.exists(tool):
        try:
            env = {k: v for k, v in os.environ.items() if not k.startswith("OT_")}
            r = subprocess.run([sys.executable, "-I", tool, "--json", "--symbol", "QQQ", "--symbol", "SPX"],
                               capture_output=True, text=True, timeout=60, env=env, cwd=_TD)
            doc = json.loads(r.stdout)
            mine = {b["symbol"]: b["values"] for b in doc["boxes"]}
            want = {s: dict(BF.load(s).values) for s in ("QQQ", "SPX")}
            tsrc = open(tool, encoding="utf-8").read()
            ok11 = (r.returncode == 0 and mine == want and doc["schema_version"] == BF.SCHEMA_VERSION
                    and set(doc["schema"]) == set(BF.SCHEMA) and "environ" not in tsrc and "getenv" not in tsrc)
            d11 = f"rc={r.returncode} mine={mine} want={want} err={r.stderr[-200:]}"
        except Exception as exc:                                # noqa: BLE001
            d11 = f"{type(exc).__name__}: {exc}"
    check("F11", ok11, d11)

    # ── F12 the park row; the default has one copy (r155) ───────────────────
    ok12, d12 = False, "no loader"
    if BF is not None:
        try:
            from strategy import plan_state as PS
            pk = BF.SCHEMA.get("park")
            row_ok = pk is not None and (pk.key, pk.setup, tuple(pk.allowed), pk.default) == ("park", "PARK",
                                                                                             ("on", "off", "paper_only"), "on")
            flag = getattr(PS, "FLAG", "flag")
            bad12 = [f"{k} -> {r.setup}: TABLE {PS.TABLE.get(r.setup)}" for k, r in BF.SCHEMA.items()
                     if r.key != k or PS.TABLE.get(r.setup, ("", "", ""))[1] != flag]
            ok12 = row_ok and not bad12
            d12 = f"park={pk} not-flag rows={bad12}"
        except Exception as exc:                                # noqa: BLE001
            d12 = f"{type(exc).__name__}: {exc}"
    check("F12", ok12, d12)

    shutil.rmtree(_TD, ignore_errors=True)
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {' '.join(FAILED)}")
        return 1
    print("GREEN — the box flag files parse, restate no default, and one loader reads them (F1-F12)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
