#!/usr/bin/env python3
"""
tests/check_box_flags.py  v5.0
v5.0  2026-11-22  OTV5 r148 (BOXF.1) — new. THE BOX FLAG FILES AND THEIR ONE LOADER. The operator, 2026-11-22: "Design it
      smartly. I don't want redundant gates blocking common use settings by having to track them in multiple places."
      So this gate validates the ONE file per box and the ONE loader, and NEVER compares a setting with another copy of
      it (no second copy exists: the schema in utils/box_flags.py is the roster, a file only overrides it).

  F1  every file in deploy/box_flags (README aside) is named for a listed symbol (config.STRIKE_INCREMENTS)
  F2  every line of every file parses (blank, "# comment" or "key = value  # reason")
  F3  every key is in utils/box_flags.SCHEMA
  F4  every value is allowed for its key (until delivery P: on / off; "paper_only" is refused)
  F5  no file sets a key twice
  F6  NO LINE RESTATES THE DEFAULT (so a default changed in SCHEMA reaches every box)
  F7  the loader, on fixtures with a stand-in schema: a missing file -> the defaults, source "none (defaults)"; a bad
      value, a duplicate and a malformed known key -> THAT setup off; an unknown key -> ignored; "paper_only" ->
      refused, off; an unreadable file (a directory in its place) -> EVERY setup off; each case named; never raises;
      effective() loads once and returns the same object (a later change on disk is not seen)
  F8  only utils/box_flags.py names the folder (deploy/box_flags) or its FLAGS_DIR in code: no other module opens it.
      (F8b, "no module reads OT_RUNAWAY / OT_HUNT / OT_PARK", arrives with M2-M4, which move those three keys here.)
  F9  nothing writes the folder: no installer, menu or deploy script (configure.sh, setup_ec2.sh, devtools.sh,
      bootstrap.example.sh, deploy/*, tools/*.sh) names it, and the show tool and the loader hold no write call; when
      ~/day_trader_pro is present, no dtp line names the folder AND writes (a fixture or a docstring that only names it
      is a read; control reads only the show tool's output)
  F10 the start line: start_line() has the pinned shape for a missing file, an ok file with differences and a refused
      line; main._announce_box_flags() logs exactly ONE [flags] line through main's logger, before _announce_plan_states
      on the start path, WARNING plus ONE page (code MSG) when a line is refused, INFO and no page otherwise
  F11 tools/box_flags_show.py (run as `python3 -I`) prints the same effective values as the loader, as JSON, reading
      no env key
Born red on r146 (df51252): utils/box_flags.py, tools/box_flags_show.py and main._announce_box_flags do not exist
(F7-F11 red; F1-F6 green on an absent folder). 11 mutants red.
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
            finally:
                MN.get_alert_manager = s_am
                MN.logger.removeHandler(cap)
                BF.reset()
            want0 = BF.start_line(BF.load(), BF.commit())
            src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
            i_f, i_p = src.find("    _announce_box_flags()  "), src.find("    _announce_plan_states()  ")
            order = 0 < i_f < i_p and src.count("    _announce_box_flags()  ") == 1
            ok10 = (shapes and len(r0) == 1 and r0[0].levelno == logging.INFO and r0[0].getMessage() == want0
                    and LINE_RX.match(want0) is not None and p0 == []
                    and len(r1) == 1 and r1[0].levelno == logging.WARNING and "REFUSED: line 1 unknown key" in
                    r1[0].getMessage() and len(p1) == 1 and p1[0][0] == "MSG" and "breakout" in p1[0][1] and order)
            d10 = (f"shapes={shapes} r0={[r.getMessage() for r in r0]} want0={want0!r} p0={p0} "
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

    shutil.rmtree(_TD, ignore_errors=True)
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {' '.join(FAILED)}")
        return 1
    print("GREEN — the box flag files parse, restate no default, and one loader reads them (F1-F11)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
