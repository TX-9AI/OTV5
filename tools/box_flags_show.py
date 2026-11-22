#!/usr/bin/env python3
"""
tools/box_flags_show.py  v5.0
v5.0  2026-11-22  OTV5 r148 (BOXF.1) — new. THE BOX FLAGS, AS THIS TREE WOULD LOAD THEM, FOR EVERY BOX OR ONE. The same
      parser the bot runs (utils/box_flags.load), so control never keeps a copy of it (the design, §0 rule 3): control's
      daily recap runs it on ~/OTV5 HEAD and compares its answer with each box's [flags] start line (the EFFECTIVE value)
      to spot a PENDING change (a landed file the box has not started on yet). READ ONLY: it opens deploy/box_flags and
      nothing else, writes nothing, reads no env key and no credential, and makes no network or broker call.

Usage:  python3 -I ~/OTV5/tools/box_flags_show.py [--symbol SYM ...] [--json] [--root DIR]
        with no --symbol: every file in deploy/box_flags plus every symbol named on the command line; a symbol with no
        file is shown on the defaults. Exit 0 always when it ran; 2 when utils/box_flags cannot be imported.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def rows(symbols, root=""):
    from utils import box_flags as BF
    syms = sorted(set(s.upper() for s in symbols) | (set() if symbols else set(BF.files(root))))
    out = []
    for s in syms:
        f = BF.load(s, path=BF.path_for(s, root))
        out.append({"symbol": f.symbol, "source": f.source, "sha256": f.sha256, "status": f.status,
                    "values": dict(f.values), "differs": list(f.differs), "problems": list(f.problems)})
    return {"schema_version": BF.SCHEMA_VERSION,
            "schema": {k: {"setup": r.setup, "allowed": list(r.allowed), "default": r.default}
                       for k, r in sorted(BF.SCHEMA.items())},
            "boxes": out}


def main(argv=None):
    ap = argparse.ArgumentParser(description="show the box flags this tree would load")
    ap.add_argument("--symbol", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default="")
    a = ap.parse_args(argv)
    try:
        doc = rows(a.symbol, a.root)
    except ImportError as exc:
        print("box_flags_show: utils/box_flags not importable (%s)" % exc, file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(doc, indent=1, sort_keys=True))
        return 0
    keys = ", ".join("%s (%s, default %s)" % (k, "/".join(v["allowed"]), v["default"])
                     for k, v in doc["schema"].items()) or "no keys"
    print("schema v%d: %s" % (doc["schema_version"], keys))
    if not doc["boxes"]:
        print("no box files: every box runs on the defaults")
    for b in doc["boxes"]:
        print("%-6s %s sha256=%s · differs: %s%s" % (
            b["symbol"], b["source"], b["sha256"], ", ".join(b["differs"]) or "none",
            (" · REFUSED: " + "; ".join(b["problems"])) if b["problems"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
