#!/usr/bin/env python3
"""
tests/gen_write_map.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.6  2026-10-13  OTV4TEST r279 - a call to a same-module SQL HELPER inside a constant
      loop resolves through the helper (see _loop_sql). The purge's DELETEs moved into
      `_delete_batched` (mirror of otv4 r416) and the map dropped them; W1/W1c caught it.

v4.5  2026-09-20  OTV4TEST r70 — §20 IN THIS REPO'S OWN COMMENTARY. `RE_DELETE`
      matched the English sentence "a checker that had to DELETE FROM THE live
      path" inside a `#` comment and invented a table called `the`, which
      over-attributed a reader and turned `check_map_accuracy` R1b RED on a
      delivery that changed no SQL. Comments and docstrings are now stripped
      before the regex scan (strings are NOT — every real statement is one).
      §20's corollary decides the direction: fix the pattern, never the prose.
Generates docs/WRITE_MAP.md — what every box writes, and who writes it.

v4.4  2026-09-20  OTV4TEST r67 (MAP.5) — THE SAME BLINDNESS AS v4.3, ONE
      PUNCTUATION MARK OVER, AND THIS TIME IN THE READ COLUMN. v4.3 taught
      this file to resolve `f"DELETE FROM {table}"` inside a loop over the
      module's own constants, because the purge deletes that way. It never
      learned the OTHER placeholder spelling: `warehouse/s3_push.py` reads
      TWENTY tables as `"SELECT * FROM %s" % table`, and every one was
      invisible. The map credited it with the two tables it names literally
      and its flag list reported SEVEN tables as having NO READER while
      s3_push was pushing all seven to the warehouse.
      🔑 THREE SHAPES WERE NEEDED AND ALL THREE ARE LOCAL EVIDENCE, never
      cross-module inference: (1) `_sql_template` matches the `%`-format
      substitution as well as the f-string; (2) `_iter_members` is an explicit
      recursion instead of a whitelist walk, so a CONDITIONAL iterable
      (`SERIES_TABLES if tables is None else tables`) contributes the branches
      that resolve; (3) `_param_consts` resolves a loop over a PARAMETER from
      this module's own call sites, which is how `tables=DERIVED_SERIES_TABLES`
      reaches the one generic pusher that serves two stores.
      ⚠️ CONSERVATISM IS UNCHANGED — an unresolvable branch, name or call
      contributes NOTHING rather than a guess, and attribution is still gated
      on tables some module CREATEs.
      ⚠️ MEASURED FALSE-POSITIVE SURFACE, because "it should be safe" is not
      a measurement: exactly THREE modules in the tree own module-level string
      collections naming real tables — `s3_push` (20), `retention_purge` (23)
      and `manifold_health` (1) — and the regenerated map's ONLY diff is
      s3_push entering the read column. The purge does not appear as a reader
      of what it counts before deleting, because `render()` already excludes a
      table's own writers from "read by".
      ⚠️ ONE RESIDUE, NAMED RATHER THAN LEFT TO BE REDISCOVERED:
      `push_table(..., "circuit_breaker_events", ...)` passes the table as a
      STRING LITERAL ARGUMENT to a parameterised pusher — a fourth shape this
      does not resolve. That table already has `query.py` as a reader, so no
      flag is affected; `check_map_accuracy` R1b pins the gap so it is a known
      exclusion rather than a silent one.

v4.3  2026-09-14  OTV4TEST r28 (MAP.3) — THE PURGE'S DELETES WERE INVISIBLE,
      ON THE ONE PATH THAT HAD JUST DELETED LIVE ROWS. `warehouse/retention_purge.py`
      deletes through `f"DELETE FROM {table} ..."` inside loops over its own
      policy dicts (`ARTIFACT_DAYS`, `DERIVED_ARTIFACT_DAYS`, `DERIVED_CDC_DAYS`),
      so the map credited it with `candles` only while it deletes from thirteen
      more tables. `--check` was green: the map was current and wrong (MAP.2).
      r18's constant resolution could not help — the placeholder is a LOOP
      VARIABLE, not a constant. `_loop_sql()` now reads the AST: a `for` whose
      target (or first unpacked name) is the placeholder, over an iterable built
      ONLY from this module's own literal dict/list/tuple/set constants of
      strings (plus `list`/`sorted`/`tuple`/`set` and `.items()`/`.keys()`), has
      each f-string SQL in its body matched once per member. ⚠️ CONSERVATIVE AS
      r18's: any other name in the iterable skips the loop, so an imported
      constant or a runtime value stays invisible (the old behaviour), and only
      tables some module CREATEs are attributed. `tests/check_map_accuracy.py`
      W1b pins that no NEVER_PURGE table picks up a delete.

v4.2  2026-09-13  OTV4TEST r18 — A TABLE NAMED THROUGH A CONSTANT WAS INVISIBLE,
      AND FOUR MORE WERE "(unattributed)" ONLY BECAUSE NOBODY ADDED THE LINE.
      `derived/base.py` writes `CREATE TABLE IF NOT EXISTS {STATUS_TABLE}`, so
      `derived_engine_status` — written by every derived engine every tick, read
      by `tools/manifold_health.py` — appeared NOWHERE, while the flag list
      reported "No writer (0): none" and the header reported 29 tables. The map
      that exists to make a table with no writer visible was itself blind to a
      writer with no literal. Module constants are now resolved into their own
      placeholders; the substitution is conservative and an unresolvable name
      simply stays invisible, which is the old behaviour rather than a wrong one.
      Plus `gate_disposition`/`plan_check`/`plan_tick` -> derived_store.db and
      `resting_orders` -> resting_orders.db, all four verified against the live
      files on the box — the last of which is a FOURTH database the map had
      never named.
v4.1  2026-08-26  r146 — THE MAP WAS ORDER-DEPENDENT AND FAILED THE GATE ON
      CONTROL WHILE PASSING IN THE SANDBOX. `scan()` recorded a READ only if
      the table's creator/writer had ALREADY been scanned, and `_files()`
      walked directories in FILESYSTEM order (os.walk, unsorted). So a reader
      that sat in a directory walked before its writer's directory was
      silently dropped — and which directory walks first differs between two
      machines. It surfaced the moment r146 moved plan_tick's creator from
      derived/ to strategy/. Fixed: directories are walked sorted, and reads
      are collected in a SECOND pass after every writer is known. The output
      is now a function of the tree alone.

v4.0  2026-08-25  Operator's ask: "a document that answers what does every box
write and who writes it — like a file map, but for journal writers."

WHY IT IS SEPARATE FROM FILE_MAP.md. That map answers "what calls what" from
the import graph. This answers a different question the import graph cannot:
**which module OWNS which table.** By r70 this repo had 22 tables across three
databases and NO SINGLE INDEX of who writes them — the ownership lived only in
scattered docstrings, which is the same shape as the sensor problem: a thing
that exists with no way to see it whole.

⚠️ GENERATED, NEVER HAND-MAINTAINED. A hand-kept write map drifts exactly the
way the version headers drifted across day_trader_pro — the changelogs advanced
while the title lines went stale for weeks. This is regenerated in the gate.

⚠️ IT REPORTS WHAT THE SOURCE SAYS, NOT WHAT A SCHEMA DUMP SAYS. A live
database shows tables that exist; this shows tables the CODE creates and
writes. The difference is the interesting part — a table in the db with no
writer in the tree is an orphan, and a writer whose table nobody reads is dead
weight. Both are visible here and in neither place alone.

Run:  python3 tests/gen_write_map.py           # regenerate
      python3 tests/gen_write_map.py --check   # fail if stale
"""

from __future__ import annotations

import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "WRITE_MAP.md")

SKIP_DIRS = {".git", "__pycache__", "venv", "docs", "node_modules"}

RE_CREATE = re.compile(r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+)", re.I)
RE_INSERT = re.compile(r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+([a-z_]+)", re.I)
RE_UPDATE = re.compile(r"UPDATE\s+([a-z_]+)\s+SET", re.I)
RE_DELETE = re.compile(r"DELETE\s+FROM\s+([a-z_]+)", re.I)
RE_SELECT = re.compile(r"FROM\s+([a-z_]+)", re.I)
RE_DBFILE = re.compile(r"([a-z_]+)\.db")

# r18 — A TABLE NAMED THROUGH A CONSTANT WAS INVISIBLE, AND THE MAP SAID SO
# NOWHERE. Every pattern above requires a LITERAL table name, so
# `CREATE TABLE IF NOT EXISTS {STATUS_TABLE}` in `derived/base.py` matched
# nothing: `derived_engine_status` — written by every derived engine on every
# tick and read by `tools/manifold_health.py` — was absent from a document
# whose flag list reported "No writer (0): none".
# 🔑 THE FAILURE RENDERED AS A SMALLER, PLAUSIBLE COUNT rather than an error,
# which is this repo's most-repeated defect shape (WORKING_AGREEMENT §35).
# So module-level `NAME = "table_name"` constants are resolved and substituted
# into their own `{NAME}` placeholders before anything is matched.
# ⚠️ DELIBERATELY CONSERVATIVE: only a bare uppercase assignment to a single
# lowercase identifier, only inside a `{...}` placeholder, only in the file
# that declares it. An unresolvable name substitutes nothing and the table goes
# back to being invisible — which is the old behaviour, never a wrong answer.
RE_CONST = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*[\"']([a-z_][a-z0-9_]*)[\"']\s*$", re.M)


def _strip_prose(src: str) -> str:
    """Source with COMMENTS and DOCSTRINGS removed, for regex SQL scanning.

    🔴 r70 — §20, FOUND IN THIS REPO'S OWN COMMENTARY. `RE_DELETE` matched the
    ordinary English sentence *"a checker that had to DELETE FROM THE live
    path"* in a `#` comment and invented a table called `the`, which then
    over-attributed a reader and turned `check_map_accuracy` R1b red on a
    delivery that changed no SQL whatsoever.
    🔑 §20's COROLLARY DECIDES WHICH SIDE TO FIX: *"If you find yourself
    carefully NOT spelling a name so a grep stays green, stop — the canary is
    wrong, not the prose."* Rewording the comment would have degraded the
    record to protect the tool. r20 solved the identical collision by running
    its assertions on TOKENISED code; this does the same.
    ⚠️ STRINGS ARE NOT STRIPPED, AND THAT IS THE WHOLE CONSTRAINT — every real
    SQL statement in this tree IS a string literal. Only COMMENT tokens and
    DOCSTRINGS (a bare string EXPRESSION statement, which SQL never is) are
    removed, so no executable SQL can be lost.
    ⚠️ AND IT FAILS OPEN: if the source will not tokenise or parse, the
    original text is returned and the old behaviour stands rather than a file
    silently contributing nothing.
    """
    import io
    import tokenize
    try:
        drop = {}
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                drop.setdefault(tok.start[0], []).append(tok.start[1])
        lines = src.splitlines(keepends=True)
        for ln_no, cols in drop.items():
            i = ln_no - 1
            if 0 <= i < len(lines):
                nl = "\n" if lines[i].endswith("\n") else ""
                lines[i] = lines[i][:min(cols)] + nl
        txt = "".join(lines)
    except Exception:                                           # noqa: BLE001
        return src
    try:
        tree = ast.parse(txt)
    except SyntaxError:
        return txt
    spans = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)) or not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            spans.append((first.lineno, first.end_lineno))
    if not spans:
        return txt
    lines = txt.splitlines(keepends=True)
    for a, b in spans:
        for i in range(a - 1, min(b, len(lines))):
            lines[i] = "\n" if lines[i].endswith("\n") else ""
    return "".join(lines)


def _resolve_consts(src: str) -> str:
    """Substitute this module's own `NAME = "table"` constants into `{NAME}`."""
    consts = dict(RE_CONST.findall(src))
    if not consts:
        return src
    for name, val in consts.items():
        src = src.replace("{" + name + "}", val)
    return src


# r28 (MAP.3) — the iterable may be dressed in these and nothing else.
_ITER_WRAPPERS = {"list", "sorted", "tuple", "set"}
_ITER_METHODS = {"items", "keys"}


def _string_members(node):
    """A literal dict's keys or a list/tuple/set's elements, if all are strings."""
    if isinstance(node, ast.Dict):
        elts = node.keys
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        elts = node.elts
    else:
        return None
    vals = [e.value for e in elts if isinstance(e, ast.Constant)]
    if len(vals) != len(elts) or not all(isinstance(v, str) for v in vals):
        return None
    return vals


def _iter_members(node, consts, params=None):
    """Members of a `for` iterable built only from this module's literal constants.
    -> list of strings, or None when anything in it is not resolvable.

    v4.4 — REWRITTEN FROM A WHITELIST WALK TO AN EXPLICIT RECURSION. The walk
    form collected every `ast.Name` under the node and refused any node type it
    did not recognise, which made the two forms below unreachable: a
    conditional iterable trips over `IfExp`/`Compare`/`Is`, and a parameter
    name is a `Name` that is simply not in `consts`. Recursing per node type
    keeps r28's rule — AN UNRESOLVABLE PIECE CONTRIBUTES NOTHING AND NEVER A
    GUESS — while letting the resolvable pieces through.

    `params` maps a parameter name to the module constants passed for it at
    this module's own call sites (see `_param_consts`). It is None when the
    loop is not inside a function.
    """
    # a literal collection written in place
    m = _string_members(node)
    if m is not None:
        return m or None

    if isinstance(node, ast.Name):
        if node.id in consts:
            return list(consts[node.id])
        # v4.4 — a PARAMETER, resolved from this module's own call sites.
        if params and node.id in params:
            return list(params[node.id]) or None
        return None

    # list(...) / sorted(...) / tuple(...) / set(...)
    if isinstance(node, ast.Call):
        if (isinstance(node.func, ast.Name) and node.func.id in _ITER_WRAPPERS
                and node.args):
            return _iter_members(node.args[0], consts, params)
        # <dict>.items() / <dict>.keys()
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr in _ITER_METHODS):
            return _iter_members(node.func.value, consts, params)
        return None

    # ⚠️ A CONDITIONAL ITERABLE CONTRIBUTES THE BRANCHES THAT RESOLVE.
    # `SERIES_TABLES if tables is None else tables` is the real shape in
    # `warehouse/s3_push.py`: one branch is a module constant, the other is a
    # caller-supplied parameter. Taking the union of whatever resolves is the
    # same conservatism as everywhere else in this file — a branch that cannot
    # be resolved adds nothing, so the answer is never wider than the evidence.
    if isinstance(node, ast.IfExp):
        out = []
        for side in (node.body, node.orelse):
            got = _iter_members(side, consts, params)
            if got:
                out.extend(got)
        return sorted(set(out)) or None

    # A + B, both of which must resolve.
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        lhs = _iter_members(node.left, consts, params)
        rhs = _iter_members(node.right, consts, params)
        if lhs is None or rhs is None:
            return None
        return lhs + rhs

    return None


def _param_consts(tree, consts):
    """{function name: {parameter name: [table names]}} from THIS module's calls.

    🔑 v4.4 — WHY THIS EXISTS AND WHY IT IS NOT GENERAL DATAFLOW. `s3_push`
    has ONE generic pusher, `push_series(..., tables=None, ...)`, serving two
    stores: it is called once with the default and once with
    `tables=DERIVED_SERIES_TABLES`. The table names are module constants and
    the call site is in the SAME FILE, twelve lines from the loop — so the
    evidence is entirely local and no cross-module inference is involved.
    ⚠️ ONLY A BARE `Name` THAT IS A MODULE CONSTANT COUNTS. A computed value,
    an imported name or a call result resolves to nothing, which leaves the
    loop exactly as invisible as it was before v4.4 rather than guessed at.
    """
    funcs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            funcs[node.name] = [p.arg for p in (a.posonlyargs + a.args)]
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        fname = node.func.id
        if fname not in funcs:
            continue
        names = funcs[fname]
        slot = out.setdefault(fname, {})
        for i, arg in enumerate(node.args):
            if i < len(names) and isinstance(arg, ast.Name) and arg.id in consts:
                slot.setdefault(names[i], []).extend(consts[arg.id])
        for kw in node.keywords:
            if (kw.arg and isinstance(kw.value, ast.Name)
                    and kw.value.id in consts):
                slot.setdefault(kw.arg, []).extend(consts[kw.value.id])
    return out


def _loop_sql(src: str):
    """-> [(sql text with the loop variable substituted), ...] for every f-string
    inside a `for` over this module's own literal constants (see v4.3)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    consts = {}
    for st in tree.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)):
            m = _string_members(st.value)
            if m is not None:
                consts[st.targets[0].id] = m
    if not consts:
        return []
    # v4.4 — which function each `for` sits in, so a loop over a PARAMETER can
    # be resolved from this module's own call sites.
    params_of = _param_consts(tree, consts)
    fn_of = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(fn):
                fn_of[id(sub)] = fn.name
    # v4.6 (r279) — A HELPER THAT TAKES THE TABLE AS A PARAMETER. Since the
    # mirror of otv4 r416 the purge no longer writes `f"DELETE FROM {table}"`
    # inside its policy loops; it calls `_delete_batched(conn, table, ...)`,
    # and the SQL lives in the helper with `table` as a PARAMETER. Without this
    # the map silently dropped the purge as the deleter of 13 tables (caught by
    # check_map_accuracy W1/W1c on the r279 build). DERIVED, NOT LISTED: any
    # function in this module whose SQL substitutes one of its own parameters
    # is a helper, and a call inside a constant loop that passes the loop
    # variable in that position resolves to that SQL for every member.
    helpers = {}
    for fn in tree.body:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        pnames = [a.arg for a in (fn.args.posonlyargs + fn.args.args)]
        for idx, pn in enumerate(pnames):
            for sub in ast.walk(fn):
                tmpl = _sql_template(sub, pn)
                if tmpl is not None:
                    helpers.setdefault(fn.name, []).append((idx, pn, tmpl))
    out = []
    # ... and a helper called with a LITERAL table (`_delete_batched(fc,
    # "candles", ...)`) resolves to that table, loop or no loop.
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in helpers):
            for idx, pn, htmpl in helpers[node.func.id]:
                arg = node.args[idx] if idx < len(node.args) else next(
                    (k.value for k in node.keywords if k.arg == pn), None)
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    out.append(htmpl.replace("\0", arg.value))
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        tgt = node.target
        if isinstance(tgt, ast.Tuple) and tgt.elts:
            tgt = tgt.elts[0]
        if not isinstance(tgt, ast.Name):
            continue
        members = _iter_members(node.iter, consts,
                                params_of.get(fn_of.get(id(node), ""), {}))
        if not members:
            continue
        for sub in (n for st in node.body for n in ast.walk(st)):
            tmpl = _sql_template(sub, tgt.id)
            if tmpl is not None:
                out.extend(tmpl.replace("\0", m) for m in members)
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id in helpers):
                for idx, pn, htmpl in helpers[sub.func.id]:
                    arg = sub.args[idx] if idx < len(sub.args) else next(
                        (k.value for k in sub.keywords if k.arg == pn), None)
                    if isinstance(arg, ast.Name) and arg.id == tgt.id:
                        out.extend(htmpl.replace("\0", m) for m in members)
    return out


def _sql_template(sub, var):
    """SQL text with the loop variable replaced by \0, or None.

    🔴 v4.4 — THIS USED TO MATCH `ast.JoinedStr` AND NOTHING ELSE, so it saw
    ONE of the two ways Python writes a placeholder. r28 taught this file the
    f-string form because `warehouse/retention_purge.py` deletes that way;
    `warehouse/s3_push.py` reads twenty tables ONE OPERATOR OVER, as
    `"SELECT * FROM %s" % table`, and every one of them was invisible. The map
    therefore credited it with the two tables it names literally and reported
    SEVEN tables as having no reader at all while it was pushing them to the
    warehouse the whole fleet reports from.
    ⚠️ SAME DEFECT, SAME FILE, ONE PUNCTUATION MARK APART — which is the
    argument for matching on the SHAPE OF THE SUBSTITUTION rather than on one
    spelling of it, and for the gate below that checks the ANSWER instead of
    the mechanism (`check_map_accuracy` R1/R1b).
    """
    # f"... {var} ..."
    if isinstance(sub, ast.JoinedStr):
        parts, uses = [], False
        for v in sub.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            elif isinstance(v.value, ast.Name) and v.value.id == var:
                parts.append("\0")
                uses = True
            else:
                parts.append("?")
        return "".join(parts) if uses else None

    # "... %s ..." % var   —   ONLY a bare Name on the right. A tuple means
    # several substitutions and the table's position stops being knowable, so
    # it resolves to nothing rather than to a guess.
    if (isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Mod)
            and isinstance(sub.left, ast.Constant)
            and isinstance(sub.left.value, str)
            and isinstance(sub.right, ast.Name) and sub.right.id == var):
        text = sub.left.value
        if text.count("%s") != 1:
            return None
        return text.replace("%s", "\0")

    return None

# Which database each table lives in. Derived from the module that CREATEs it,
# so a table moving file moves here automatically.
DB_OF_DIR = {
    "data/candle_feed.py": "feed_store.db",
    "data/derived_store.py": "derived_store.db",
    "database/trade_logger.py": "trades.db",
}

# ⚠️ MODULES THAT CREATE THEIR OWN TABLE INSIDE ANOTHER STORE'S FILE.
# `derived/` engines call `self._store.conn.execute("CREATE TABLE ...")` so the
# table lives in derived_store.db while the DDL lives in the engine. That is
# deliberate — one engine per store, each owning its own schema — but it means
# the file that CREATEs is not the file that names the database, and the first
# run of this generator listed four tables as "(unattributed)". Reporting them
# as homeless would be wrong; guessing silently would be worse. This is the
# explicit mapping, and it is the ONE hand-maintained thing here.
# r18 — THE FOUR "(unattributed)" TABLES WERE ALL RESOLVABLE, AND ONE OF THEM
# NAMED A FOURTH DATABASE THE MAP NEVER MENTIONED. Verified by reading the live
# files on the box, not inferred: `gate_disposition`, `plan_check` and
# `plan_tick` are in `derived_store.db`; `resting_orders` is in its own
# `data/resting_orders.db`. An "(unattributed)" heading reads as "nobody knows",
# when in fact nobody had added the line.
DB_OF_PREFIX = {
    "derived/": "derived_store.db",
    "analysis/tenor_publish.py": "feed_store.db",
    "analysis/gate_report.py": "derived_store.db",
    "strategy/plan.py": "derived_store.db",
    "execution/resting_orders.py": "resting_orders.db",
}


def _files():
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)   # v4.1: deterministic
        for f in sorted(fn):
            if f.endswith(".py"):
                yield os.path.relpath(os.path.join(dp, f), ROOT)


def scan():
    creates, writes, reads, dbs = {}, {}, {}, {}
    sources = {}
    looped = {}                         # r28: rel -> loop-resolved SQL texts
    for rel in _files():
        try:
            raw = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        except Exception:                                       # noqa: BLE001
            continue
        sources[rel] = _resolve_consts(_strip_prose(raw))
        looped[rel] = _loop_sql(raw)
    for rel, src in sources.items():
        for t in RE_CREATE.findall(src):
            creates.setdefault(t, set()).add(rel)
            if rel in DB_OF_DIR:
                dbs[t] = DB_OF_DIR[rel]
            else:
                for pref, db in DB_OF_PREFIX.items():
                    if rel.startswith(pref):
                        dbs[t] = db
                        break
        for rx, kind in ((RE_INSERT, "insert"), (RE_UPDATE, "update"),
                         (RE_DELETE, "delete")):
            for t in rx.findall(src):
                writes.setdefault(t, {}).setdefault(rel, set()).add(kind)
    # r28 (MAP.3) — loop-resolved SQL, attributed only to tables the tree
    # CREATEs, so a policy key that is not a table can never invent one.
    for rel, texts in looped.items():
        for text in texts:
            for rx, kind in ((RE_INSERT, "insert"), (RE_UPDATE, "update"),
                             (RE_DELETE, "delete")):
                for t in rx.findall(text):
                    if t in creates:
                        writes.setdefault(t, {}).setdefault(rel, set()).add(kind)
            for t in RE_SELECT.findall(text):
                if t in creates:
                    reads.setdefault(t, set()).add(rel)
    # v4.1 — SECOND PASS, after every writer is known. A read is only a read
    # of a table this tree writes; deciding that mid-walk made the answer
    # depend on directory order.
    for rel, src in sources.items():
        for t in RE_SELECT.findall(src):
            # a module that only writes also names the table in its INSERT;
            # reads are recorded separately so "who consumes this" is answerable
            if t in creates or t in writes:
                reads.setdefault(t, set()).add(rel)
    return creates, writes, reads, dbs


def render() -> str:
    creates, writes, reads, dbs = scan()
    tables = sorted(set(creates) | set(writes))
    L = []
    L.append("# WRITE_MAP.md — what every box writes, and who writes it")
    L.append("")
    L.append("**GENERATED by `tests/gen_write_map.py` — do not edit by hand.**")
    L.append("Regenerated in the land gate; a stale map fails `--check`.")
    L.append("")
    L.append("`FILE_MAP.md` answers *what calls what*. This answers *who owns "
             "which table* — a question the import graph cannot.")
    L.append("")
    L.append("⚠️ **A table with no writer is an orphan. A table nobody reads "
             "is dead weight.** Both are visible here and in neither the "
             "schema nor the call graph alone.")
    L.append("")
    L.append(f"**{len(tables)} tables.**")
    L.append("")

    by_db = {}
    for t in tables:
        by_db.setdefault(dbs.get(t, "(unattributed)"), []).append(t)

    for db in sorted(by_db):
        L.append(f"## {db}")
        L.append("")
        L.append("| table | created by | written by | read by |")
        L.append("|---|---|---|---|")
        for t in sorted(by_db[db]):
            c = ", ".join(f"`{x}`" for x in sorted(creates.get(t, []))) or "—"
            w = writes.get(t, {})
            wparts = []
            for mod in sorted(w):
                kinds = "/".join(sorted(w[mod]))
                wparts.append(f"`{mod}` ({kinds})")
            wtxt = ", ".join(wparts) or "**— NO WRITER**"
            r = sorted(x for x in reads.get(t, set())
                       if x not in w and x not in creates.get(t, set()))
            rtxt = ", ".join(f"`{x}`" for x in r) or "—"
            L.append(f"| `{t}` | {c} | {wtxt} | {rtxt} |")
        L.append("")

    orphan_w = [t for t in tables if not writes.get(t)]
    orphan_r = [t for t in tables
                if not [x for x in reads.get(t, set())
                        if x not in writes.get(t, {})]]
    L.append("## Flags")
    L.append("")
    L.append(f"- **No writer** ({len(orphan_w)}): "
             + (", ".join(f"`{t}`" for t in orphan_w) or "none"))
    L.append(f"- **No external reader** ({len(orphan_r)}): "
             + (", ".join(f"`{t}`" for t in orphan_r) or "none"))
    L.append("")
    L.append("⚠️ *No external reader* is not automatically a defect — a table "
             "written today for a study run in a month is exactly the point of "
             "the derived layer. It IS a defect when nobody ever intends to "
             "read it, and this list is where that question gets asked.")
    L.append("")
    return "\n".join(L)


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        try:
            cur = open(OUT, encoding="utf-8").read()
        except FileNotFoundError:
            print("  WRITE_MAP.md missing — run gen_write_map.py")
            return 1
        if cur.strip() != text.strip():
            print("  WRITE_MAP.md is STALE — regenerate it")
            return 1
        print("  write map is current")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
