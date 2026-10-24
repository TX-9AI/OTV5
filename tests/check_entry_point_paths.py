#!/usr/bin/env python3
"""
tests/check_entry_point_paths.py  v1.0
v1.0  2026-09-07  r312 / DEP.10 — A DECLARED ENTRY POINT IS A PATH, AND AN
AMBIGUOUS BASENAME IS NOT EVIDENCE.

The r288 stray `data/main.py` sat on fifteen boxes for a day rendering as
`called by: (entry point)` — because `gen_file_map.py` fell back to
`os.path.basename(p) in ENTRY_POINTS`, and its basename is `main.py`.

🔴 AND REMOVING THAT FALLBACK ALONE DID NOTHING VISIBLE, which is the finding
this check exists to lock down. `_mentions` matches basename AND stem, so the
stray simply moved to `referenced in check_versions.sh, configure.sh +21` —
none of which name it. Two layers, one defect.

⚠️ THIS RUNS THE GENERATOR AGAINST A SYNTHETIC TREE, not against the repo. A
check that asserted something about the live tree would pass today and say
nothing about the case that matters, because the stray is not there any more.
E3 PLANTS one and reads how it is classified.

⚠️ AND IT IS A REAL GATE, NOT A BARE INVOCATION. `CHECK tests/gen_file_map.py`
would exit 0 whatever the code did — the G5 failure from `tests/fees.py`, where
running the module with no arguments tested nothing and reported success.

Run:  python3 tests/check_entry_point_paths.py
"""
from __future__ import annotations

import io
import os
import sys
import tokenize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "tests", "gen_file_map.py")
F: list = []


def check(n, ok, det=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  — {det}" if det else ""))
    if not ok:
        F.append(n)


def _code_only(path: str) -> str:
    """Source with comments and strings stripped.

    ⚠️ WA §20. The changelog entry §5 requires necessarily NAMES the expression
    that was removed, so a raw-text search finds it and goes red on the
    documentation of its own fix. Six such collisions in one session.
    """
    out = []
    with open(path) as fh:
        for tok in tokenize.generate_tokens(fh.readline):
            if tok.type not in (tokenize.COMMENT, tokenize.STRING):
                out.append(tok.string)
    return " ".join(out)


def main() -> int:
    print("\ncheck_entry_point_paths\n")
    code = _code_only(GEN)

    check("E1  ENTRY_POINTS is matched on PATH only — no basename fallback",
          "basename ( p ) in ENTRY_POINTS" not in code,
          "checked with comments and strings stripped (§20)")
    check("E2  the ambiguity guard exists in code",
          "_ambiguous" in code and "_by_base" in code)

    # E3 — PLANT A STRAY AND READ THE CLASSIFICATION. The whole point.
    import tempfile
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        pkg = os.path.join(td, "data")
        os.makedirs(os.path.join(td, "tests"))
        os.makedirs(pkg)
        open(os.path.join(td, "main.py"), "w").write("import data.market_data\n")
        open(os.path.join(pkg, "__init__.py"), "w").write("")
        open(os.path.join(pkg, "market_data.py"), "w").write("x = 1\n")
        # the stray: same basename, different level, imported by nobody
        open(os.path.join(pkg, "main.py"), "w").write("import data.market_data\n")
        # a doc that names the REAL one only, the way check_versions.sh does
        os.makedirs(os.path.join(td, "docs"))
        open(os.path.join(td, "docs", "X.md"), "w").write("we run main.py daily\n")
        import shutil
        shutil.copy(GEN, os.path.join(td, "tests", "gen_file_map.py"))
        subprocess.run([sys.executable, "tests/gen_file_map.py"], cwd=td,
                       capture_output=True)
        mp = os.path.join(td, "docs", "FILE_MAP.md")
        txt = open(mp).read() if os.path.exists(mp) else ""
        # ⚠️ BOUND THE WINDOW AT THE NEXT SECTION. A fixed 400-character slice
        # ran into the REAL `main.py` entry, which legitimately says
        # "(entry point)" — so the check went red on the correct behaviour of
        # the file next door. A matcher whose window is wider than its subject
        # reports on whatever happens to follow.
        seg = ""
        if "### `data/main.py`" in txt:
            i = txt.index("### `data/main.py`")
            j = txt.find("\n### ", i + 1)
            seg = txt[i:j if j != -1 else len(txt)]
        check("E3  a planted stray does NOT claim to be a declared entry point",
              "(entry point)" not in seg, seg.split("\n")[2][:74] if seg else "no entry rendered")
        check("E3b and it does NOT inherit the real main.py's mention",
              "docs/X.md" not in seg,
              "a bare basename is evidence for neither when two files share it")

    print()
    if F:
        print(f"check_entry_point_paths: FAIL ({len(F)}): {', '.join(F)}")
        return 1
    print("check_entry_point_paths: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
