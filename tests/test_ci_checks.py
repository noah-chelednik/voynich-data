"""The repository's CI checks, run inside the suite.

The suite may run offline, in a read-only checkout. So every check here:

- uses the dev venv's own tools (the interpreter running this suite), never a tool from PATH;
- writes nothing into the tree or anywhere else (ruff ``--no-cache``, mypy ``--cache-dir=/dev/null``,
  black through its API so its user cache is never touched);
- needs no network. ``pip-audit`` needs the network and is therefore NOT here: it is run by hand
  (``pip-audit --strict -r requirements-lock.txt``) and its dated output recorded with the release.

``test_no_literal_counts`` enforces governing principle 2 (no hand-written expected counts or
thresholds in tests, validators or builders). ``test_no_skips_and_no_xfails`` keeps every real-file
test running: no skip and no xfail of any kind (the one xfail the plan allowed, the loss test, was
removed by item 1.1).
"""

from __future__ import annotations

import ast
import io
import json
import re
import subprocess
import sys
import tokenize
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PY, "-m", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _tracked_python_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return [ROOT / p for p in out.split("\0") if p]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------
# The checks of .github/workflows/ci.yml
# --------------------------------------------------------------------------------------------


def test_ruff() -> None:
    res = _run("ruff", "check", "--no-cache", ".")
    assert res.returncode == 0, res.stdout + res.stderr


def test_black() -> None:
    import black

    cfg = _pyproject()["tool"]["black"]
    mode = black.Mode(
        target_versions={black.TargetVersion[v.upper()] for v in cfg["target-version"]},
        line_length=cfg["line-length"],
    )
    exclude = re.compile(cfg["extend-exclude"], re.VERBOSE) if "extend-exclude" in cfg else None
    would_reformat = []
    for path in _tracked_python_files():
        rel = "/" + path.relative_to(ROOT).as_posix()
        if exclude is not None and exclude.search(rel):
            continue
        src = path.read_text(encoding="utf-8")
        try:
            black.format_file_contents(src, fast=False, mode=mode)
        except black.NothingChanged:
            continue
        would_reformat.append(rel)
    assert not would_reformat, f"black would reformat: {would_reformat}"


def test_mypy() -> None:
    res = _run("mypy", "--cache-dir=/dev/null", "vcat", "parsers", "builders", "validators", "hf")
    assert res.returncode == 0, res.stdout + res.stderr


@pytest.mark.parametrize(
    "schema_file", sorted((ROOT / "schemas").glob("*.json")), ids=lambda p: p.name
)
def test_schema_is_valid_json_schema(schema_file: Path) -> None:
    from jsonschema import Draft7Validator

    Draft7Validator.check_schema(json.loads(schema_file.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------------------------
# No literal counts (governing principle 2)
# --------------------------------------------------------------------------------------------

#: Directories under the rule. Reviewer proofs (tests/regressions, tests/regressions) are copied in
#: unchanged and are not under it.
LITERAL_COUNT_ROOTS = ("tests", "validators", "builders")
LITERAL_COUNT_EXCLUDED = ("tests/regressions/", "tests/test_ci_checks.py")

#: An integer this large in a comparison is a count or threshold about the data. A smaller one
#: (down to COUNT_LITERAL_MIN) is too, when the comparison names a count (`len(quires) > 10`).
LITERAL_MIN = 100
COUNT_LITERAL_MIN = 10

#: Names that mark a number as a count, when it is assigned or written next to one in prose.
COUNT_WORDS = re.compile(
    r"(?i)(expected|count|total|threshold|min_|max_|pages|lines|loci|locus|folios|quires|rows|"
    r"records|labels|words|pct|percent)"
)

#: A comparison involving one of these names compares an identity or a protocol constant, not a
#: count: folio numbers (f116) and HTTP status codes.
IDENTITY_NAMES = re.compile(r"(?i)\b(folio|folio_num|folio_number|status|status_code)\b")

#: Comparisons whose number is the test's OWN synthetic input, reviewed one by one. Each entry is
#: (path, the comparison as ast.unparse prints it), with the reason.
SYNTHETIC_ALLOWED = {
    # input is "fachys.ykal." * 1000, two words per repetition
    ("tests/test_eva_charset.py", "result.word_count == 2000"),
    # input is range(1000) rows built in the test
    ("tests/test_hf_export.py", "ds.num_rows == 1000"),
    # BuildReport(total_pages=10, total_lines=100) constructed in the test
    ("tests/test_builders.py", "d['total_pages'] == 10"),
    ("tests/test_builders.py", "d['total_lines'] == 100"),
    # LineRecord(..., char_count=10, ...) constructed in the test
    ("tests/test_builders.py", "record.char_count == 10"),
    # folio numbers (identities) in the set of missing folios, not counts
    ("tests/test_metadata.py", "12 in MISSING_FOLIOS"),
    ("tests/test_metadata.py", "74 in MISSING_FOLIOS"),
    # 116 is the last folio number of the manuscript (an identity), not a count of source data
    ("tests/test_metadata.py", "116 in covered"),
}


def _big_ints(node: ast.AST, minimum: int = LITERAL_MIN) -> list[int]:
    return [
        int(n.value)
        for n in ast.walk(node)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, (int, float))
        and not isinstance(n.value, bool)
        and abs(n.value) >= minimum
    ]


def _names(node: ast.AST) -> str:
    parts = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            parts.append(n.id)
        elif isinstance(n, ast.Attribute):
            parts.append(n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            parts.append(n.value)
    return " ".join(parts)


#: Names that read real data: the cached sources and the committed output (a synthetic input a test writes itself is
#: not real data, so its counts are the test's own).
# The repository's path constants and the source directory's name; a bare "output" or "cache" is a test's own
# temporary directory as often as not (tmp_path / "output"), so it does not count.
# The registry's and the extracts' readers are reads of real data too (B-121, AT9 F1): `cached_sources()` and
# `source_file("CD")` reach the cached files as surely as the path constants do.
REAL_DATA = re.compile(
    r"\b(ZL|ZL_PATH|zl_file|zl_path|zl_source_path|CACHE|CACHE_DIR|SOURCES|OUTPUT|OUTPUT_DIR|data_sources"
    r"|cached_sources|not_cached_sources|load_sources|license_statement|source_file|SOURCES_YAML|census_source"
    r"|nonconforming_lines"
    r"|CANVASES_JSON|load_canvases|LAYERS_YAML|load_layers)\b"
)


class _Defs:
    """The bindings of one scope, in source order by position, for the population rule (reviews cad4bcad finding 1,
    7ccc8927 finding 1): simple assignments (``x = ...``, ``x: T = ...``), parameters (as assignments at the function's
    line) and function definitions (``def f``, bound at its line; review 494bb9ab finding 2). A name read at a position
    has the value of its latest binding that ENDS before that position, the same line included; branches are not
    followed (straight-line reading)."""

    def __init__(self, nodes: list[ast.AST]):
        self.by_name: dict[str, list[tuple[tuple[int, int], tuple[int, int], ast.AST]]] = {}
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                position = (node.lineno, node.col_offset)
                self.by_name.setdefault(node.name, []).append((position, position, node))
                continue
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            end = (node.end_lineno or node.lineno, node.end_col_offset or 0)
            start = (node.lineno, node.col_offset)
            for target in targets:
                if isinstance(target, ast.Name):
                    self.by_name.setdefault(target.id, []).append((end, start, value))
        for defs in self.by_name.values():
            defs.sort(key=lambda d: d[0])

    def latest(self, name: str, at: tuple[int, int]) -> tuple[tuple[int, int], ast.AST] | None:
        """The start position and value of the latest binding of ``name`` that ends before ``at``."""
        found = None
        for end, start, value in self.by_name.get(name, []):
            if end <= at:
                found = (start, value)
        return found


#: The position after every statement of a scope: an enclosing scope's binding as it stands when a nested function runs.
_END = (10**9, 0)


class _Scope:
    """One lexical scope, the module or a function, for the population rule (review 494bb9ab finding 1). A name bound in
    the scope is read straight-line, at the position of the read; a free name is read from the nearest enclosing scope that
    binds it, as that binding stands at the end of that scope (a nested function runs after its enclosing code), then
    followed back there. A parameter or a ``def`` is a binding like an assignment, so it shadows."""

    def __init__(self, defs: _Defs, parent: _Scope | None, real_functions: set[int]):
        self.defs = defs
        self.parent = parent
        self.real_functions = (
            real_functions  # ids of the FunctionDef nodes whose return value reads real data
        )

    def resolve(
        self, name: str, at: tuple[int, int]
    ) -> tuple[_Scope, tuple[int, int], ast.AST] | None:
        if name in self.defs.by_name:
            found = self.defs.latest(name, at)
            return (self, found[0], found[1]) if found else None
        scope = self.parent
        while scope is not None:
            if name in scope.defs.by_name:
                found = scope.defs.latest(name, _END)
                return (scope, found[0], found[1]) if found else None
            scope = scope.parent
        return None

    def latest(self, name: str, at: tuple[int, int]) -> tuple[tuple[int, int], ast.AST] | None:
        """resolve(), shaped as _Defs.latest (the start position and the value)."""
        found = self.resolve(name, at)
        return (found[1], found[2]) if found else None


def _int_literal(node: ast.AST, defs: _Scope, at: tuple[int, int]) -> bool:
    """An integer literal of 2 or more, written in place or through a name whose binding is one, followed through any
    chain of names to its end (``expected = 9; required = expected``; reach 5d6306ba gap 2); a cycle stops it.
    """
    seen: set[tuple[int, str, tuple[int, int]]] = set()
    scope = defs
    while isinstance(node, ast.Name):
        found = scope.resolve(node.id, at)
        if not found:
            break
        where, position, value = found
        key = (id(where), node.id, position)
        if key in seen:
            break
        seen.add(key)
        node, scope, at = value, where, position
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
        and node.value >= 2
    )


def _reads_real_data(
    node: ast.AST,
    scope: _Scope,
    at: tuple[int, int],
    seen: frozenset[tuple[int, str, tuple[int, int]]] = frozenset(),
) -> bool:
    """Whether an expression read at position ``at`` in ``scope`` reads the cached sources or the output: directly, or
    through the binding of a name it uses, resolved lexically and followed back transitively (reviews cad4bcad finding 1,
    7ccc8927 finding 1, 494bb9ab findings 1 and 2); a name bound to a function whose return value reads real data reads
    real data (AD2 F1). A chain of bindings is followed to its end, however long; only a binding already on the chain stops
    it (a cycle; review dd656696 finding 1)."""
    names = _names(node)
    if REAL_DATA.search(names):
        return True
    for name in set(re.findall(r"\w+", names)):
        found = scope.resolve(name, at)
        if not found:
            continue
        where, position, value = found
        if isinstance(value, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if id(value) in scope.real_functions:
                return True
            continue
        key = (id(where), name, position)
        if key in seen:
            continue
        if _reads_real_data(value, where, position, seen | {key}):
            return True
    return False


def _len_call(
    node: ast.AST, scope: _Scope | None, at: tuple[int, int]
) -> tuple[ast.Call, _Scope | None, tuple[int, int]] | None:
    """The ``len(...)`` call an operand is, written in place or through a chain of names (``size = len(rows)``; reach
    3f9c87ec gap 2), with the scope and position it is read at; None when it is not one. A cycle stops the chain.
    """
    seen: set[tuple[int, str, tuple[int, int]]] = set()
    while isinstance(node, ast.Name) and scope is not None:
        found = scope.resolve(node.id, at)
        if not found:
            return None
        where, position, value = found
        key = (id(where), node.id, position)
        if key in seen:
            return None
        seen.add(key)
        node, scope, at = value, where, position
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
        return node, scope, at
    return None


def _source_population_equality(node: ast.Compare, defs: _Scope) -> bool:
    """Whether a comparison equates the ``len(...)`` of a population read from real data with an integer literal of 2
    or more, in place or through a name: ``rows = parse_file(ZL); assert len(rows) == 9``, or with
    ``expected_count = 9`` (reach cf1c8c6e gap 8)."""
    sides = [node.left, *node.comparators]
    at = (node.lineno, node.col_offset)
    for op, left, right in zip(node.ops, sides, sides[1:], strict=False):
        if not isinstance(op, (ast.Eq, ast.NotEq)):
            continue
        for size, number in ((left, right), (right, left)):
            call = _len_call(size, defs, at)
            if call is None or not call[0].args:
                continue
            where, read_at = call[1] or defs, call[2]
            if _reads_real_data(call[0].args[0], where, read_at) and _int_literal(number, defs, at):
                return True
    return False


def _population_threshold(node: ast.Compare, scope: _Scope | None = None) -> bool:
    """Whether a comparison thresholds a ``len(...)`` against an integer literal of 2 or more, in place or, given the
    comparison's scope, through a chain of names (``expected = 9; required = expected``; review a7ec7868 finding 1).
    """
    sides = [node.left, *node.comparators]
    thresholds = (ast.Gt, ast.GtE, ast.Lt, ast.LtE)
    at = (node.lineno, node.col_offset)
    for op, left, right in zip(node.ops, sides, sides[1:], strict=False):
        if not isinstance(op, thresholds):
            continue
        for size, number in ((left, right), (right, left)):
            if _len_call(size, scope, at) is None:
                continue
            if scope is not None and _int_literal(number, scope, at):
                return True
            if (
                isinstance(number, ast.Constant)
                and isinstance(number.value, int)
                and not isinstance(number.value, bool)
                and number.value >= 2
            ):
                return True
    return False


#: The assertion calls that compare their first two arguments, as the comparison each one makes (audit 20261021-tests
#: F2: `self.assertEqual(len(rows), 4072)` and `math.isclose(len(rows), 4072)` passed the guard)
ASSERTION_CALLS: dict[str, type[ast.cmpop]] = {
    "assertEqual": ast.Eq,
    "assertEquals": ast.Eq,
    "assertAlmostEqual": ast.Eq,
    "assertNotEqual": ast.NotEq,
    "assertGreater": ast.Gt,
    "assertGreaterEqual": ast.GtE,
    "assertLess": ast.Lt,
    "assertLessEqual": ast.LtE,
    "isclose": ast.Eq,
}


class _AssertionsAsComparisons(ast.NodeTransformer):
    """Each assertion call of ASSERTION_CALLS becomes the comparison it makes, and `pytest.approx(n)` becomes n, so
    every rule below reads them as it reads `assert a == b` (audit 20261021-tests F2)."""

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        func = node.func
        name = (
            func.attr
            if isinstance(func, ast.Attribute)
            else func.id if isinstance(func, ast.Name) else ""
        )
        if name == "approx" and node.args:
            return node.args[0]
        if name in ASSERTION_CALLS:
            # the two operands, positional or by keyword (`first`/`second` for unittest, `a`/`b` for isclose; reach
            # dec3e688 gap 3)
            keywords = {k.arg: k.value for k in node.keywords if k.arg}
            operands = list(node.args[:2])
            for key in ("first", "second", "a", "b"):
                if key in keywords and len(operands) < 2:
                    operands.append(keywords[key])
            if len(operands) == 2:
                compare = ast.Compare(
                    left=operands[0], ops=[ASSERTION_CALLS[name]()], comparators=[operands[1]]
                )
                return ast.copy_location(compare, node)
        return node


def _literal_count_hits(rel: str, src: str) -> list[str]:
    """Every hard-coded count in the Python source src, reported as living at rel."""
    tree = ast.fix_missing_locations(_AssertionsAsComparisons().visit(ast.parse(src)))
    hits = []

    # For the population rule: for each comparison, the simple assignments in its scope that come before it, in source
    # order. A function's scope is its own body without nested functions or classes, plus the module level; a later
    # assignment never colours an earlier comparison (review cad4bcad finding 1).
    def own_nodes(body: list[ast.stmt]) -> list[ast.AST]:
        out: list[ast.AST] = []
        stack: list[ast.AST] = list(reversed(body))
        while stack:
            node = stack.pop()
            out.append(node)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            stack.extend(reversed(list(ast.iter_child_nodes(node))))
        return out

    module_nodes = own_nodes(list(tree.body))
    real_functions: set[int] = set()
    module_scope = _Scope(_Defs(module_nodes), None, real_functions)
    scope_of: dict[int, _Scope] = {
        id(node): module_scope for node in module_nodes if isinstance(node, ast.Compare)
    }

    def parameters(function: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> list[ast.AST]:
        args = function.args
        names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
        names += [a.arg for a in (args.vararg, args.kwarg) if a is not None]
        out: list[ast.AST] = []
        for name in names:
            node = ast.Assign(targets=[ast.Name(id=name)], value=ast.Constant(value=None))
            node.lineno = node.end_lineno = function.lineno
            node.col_offset, node.end_col_offset = function.col_offset, function.col_offset + 1
            out.append(node)
        return out

    # Lexical scope (AT1 F3, AT2 F3, AD2 F1, B-061; review 494bb9ab): each function's scope holds its parameters and its
    # own bindings, and its parent is the scope it is defined in.
    function_scope: dict[int, _Scope] = {}
    function_own: dict[int, list[ast.AST]] = {}
    functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    def visit(body_nodes: list[ast.AST], scope: _Scope) -> None:
        for node in body_nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local = own_nodes(node.body)
                inner = _Scope(_Defs(parameters(node) + local), scope, real_functions)
                function_scope[id(node)], function_own[id(node)] = inner, local
                functions.append(node)
                for child in local:
                    if isinstance(child, ast.Compare):
                        scope_of[id(child)] = inner
                visit(local, inner)
            elif isinstance(node, ast.ClassDef):
                visit(own_nodes(node.body), scope)

    visit(module_nodes, module_scope)

    # The functions whose return value reads real data, to a fixed point (a function returning another's result)
    changed = True
    while changed:
        changed = False
        for function in functions:
            if id(function) in real_functions:
                continue
            for node in function_own[id(function)]:
                if (
                    isinstance(node, ast.Return)
                    and node.value is not None
                    and _reads_real_data(
                        node.value, function_scope[id(function)], (node.lineno, node.col_offset)
                    )
                ):
                    real_functions.add(id(function))
                    changed = True
                    break

    for node in ast.walk(tree):
        # (a) a threshold on a population size, whatever its value and whatever names it holds:
        #     `len(line_types) >= 2`. Only an emptiness check (`len(x) > 0`, `len(x) >= 1`) is not a
        #     count (reach 61cfe3b0 gap 3; checked first, so no identity exemption hides it, review
        #     6ca5c86f finding 2).
        if isinstance(node, ast.Compare) and (
            _population_threshold(node, scope_of.get(id(node), module_scope))
            or _source_population_equality(node, scope_of.get(id(node), module_scope))
        ):
            text = ast.unparse(node)
            if (rel, text) not in SYNTHETIC_ALLOWED:
                hits.append(f"{rel}:{node.lineno}: population threshold `{text[:100]}`")
        # (a2) a comparison against a large literal: `== 4072`, `> 4000`, `>= 220`
        elif isinstance(node, ast.Compare) and (
            _big_ints(node)
            or (_big_ints(node, COUNT_LITERAL_MIN) and COUNT_WORDS.search(_names(node)))
        ):
            text = ast.unparse(node)
            if IDENTITY_NAMES.search(_names(node)) or (rel, text) in SYNTHETIC_ALLOWED:
                continue
            hits.append(f"{rel}:{node.lineno}: comparison `{text[:100]}`")
        # (b) a large literal assigned to a count-like name: `expected_count = 4072` (a small one is caught where it
        #     is compared with a real population, rule (a))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if _big_ints(node.value) and COUNT_WORDS.search(" ".join(_names(t) for t in targets)):
                hits.append(f"{rel}:{node.lineno}: assignment `{ast.unparse(node)[:100]}`")

    # (c) a large number written as a count in a docstring or comment: a doctest output line
    #     (`4072`), or a number on the same line as a count word (`Pages: 226`, `# 206 - pages`)
    prose: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc and node.body:
                first = node.body[0].lineno
                prose.extend((first + i, line) for i, line in enumerate(doc.splitlines()))
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            prose.append((tok.start[0], tok.string))
    for lineno, line in prose:
        nums = [int(m) for m in re.findall(r"(?<![\w.:-])(\d{3,})(?![\w.:-])", line)]
        nums = [n for n in nums if n >= LITERAL_MIN and not 1900 <= n <= 2100]
        if not nums:
            continue
        if re.fullmatch(r"\s*\d+\s*", line) or COUNT_WORDS.search(line):
            hits.append(f"{rel}:{lineno}: prose `{line.strip()[:100]}`")
    return hits


def test_no_literal_counts() -> None:
    """No hand-written expected counts or thresholds in tests, validators or builders.

    Counts are derived from the upstream source files at test time (roadmap item 1.5).
    """
    hits = []
    for root in LITERAL_COUNT_ROOTS:
        for path in sorted((ROOT / root).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if any(rel.startswith(x) or rel == x for x in LITERAL_COUNT_EXCLUDED):
                continue
            hits.extend(_literal_count_hits(rel, path.read_text(encoding="utf-8")))
    assert not hits, f"{len(hits)} hard-coded counts or thresholds:\n" + "\n".join(hits)
    # the claims that name this test also say the suite has no skip or xfail (reach 1c53841b gap 6)
    test_no_skips_and_no_xfails()


@pytest.mark.parametrize(
    "snippet",
    [
        "assert len(records) == 4072\n",
        "assert report.total_lines > 4000\n",
        "assert len(pages) >= 220\n",
        "assert len(result.quires) > 10\n",
        "assert result.total_folios >= 100\n",
        "expected_count = 4072\n",
        '"""Pages: 226, Folios: 113"""\n',
        "def f():\n    '''\n    >>> len(records)\n    4072\n    '''\n",
        "x = 1  # 206 - pages that have loci\n",
        "ok = pct_with_chars >= 95\n",
        "assert len(line_types) >= 2\n",
        "rows = list(IVTFFParser().parse_file(ZL))\nassert len(rows) == 9\n",
        "rows = load(OUTPUT)\nexpected_count = 9\nassert len(rows) == expected_count\n",
        "assert 3 < len(rows)\n",
        "assert len(rows_by_status[status]) >= 10\n",
        "assert len(pages_by_folio[folio]) > 100\n",
        "items = cached_sources()\nassert len(items) == 9\n",
        'rows = list(IVTFFParser().parse_file(ROOT / source_file("CD")))\nassert len(rows) == 9\n',
        "extract = load_canvases()\nassert len(extract['canvases']) == 213\n",
        "rows = load(OUTPUT)\nself.assertEqual(len(rows), 4072)\n",
        "self.assertGreaterEqual(report.total_lines, 4000)\n",
        "rows = load(OUTPUT)\nassert math.isclose(len(rows), 4072)\n",
        "rows = load(OUTPUT)\nassert len(rows) == pytest.approx(4072)\n",
    ],
)
def test_no_literal_counts_detector_catches(snippet: str) -> None:
    """The detector itself: each shape of hard-coded count is caught."""
    assert _literal_count_hits("tests/probe.py", snippet), f"detector missed: {snippet!r}"


@pytest.mark.parametrize(
    "snippet",
    [
        "assert len(h) == 64\n",
        "assert resp.status_code == 200\n",
        "assert folio == 116\n",
        "assert len(records) == count_loci(source)\n",
        "x = 1  # built 2026-10-08\n",
        "assert len(rows) > 0\n",
        "assert len(rows) >= 1\n",
        "pages = list(parser.parse_string(content))\nassert len(pages) == 3\n",
    ],
)
def test_no_literal_counts_detector_allows(snippet: str) -> None:
    """The detector does not flag derived counts, short lengths, identities or dates."""
    assert not _literal_count_hits("tests/probe.py", snippet)


# --------------------------------------------------------------------------------------------
# Every real-file test runs (roadmap item 1.5)
# --------------------------------------------------------------------------------------------

#: No xfail is allowed: the one once allowed (the real-file loss test, before the phase 1 gate)
#: was removed by item 1.1 when the parser stopped dropping loci.
SKIP_NAMES = {"skip", "skipif", "importorskip", "skipIf", "skipUnless", "SkipTest", "skipTest"}
#: ``self.skipTest(...)`` (unittest) is a skip too (AT4 F1); the root conftest.py fails any skipped or xfailed outcome at
#: run time, however it was produced, so this guard is the static half of the policy.
#: The names that mark a test expected to fail, in pytest and in unittest (AT3 F1: ``unittest.expectedFailure``)
XFAIL_NAMES = {"xfail", "expectedFailure"}
TEST_TREES = ("tests", "tests/regressions")


def _skip_and_xfail_uses(rel: str, src: str) -> tuple[list[str], list[tuple[str, str, bool, str]]]:
    """(skip uses, xfail uses as (path, enclosing function, strict, reason)) in src."""
    tree = ast.parse(src)
    skips: list[str] = []
    xfails: list[tuple[str, str, bool, str]] = []
    owners: dict[int, str] = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in fn.decorator_list:
                for n in ast.walk(d):
                    owners[id(n)] = fn.name
    # A skip or xfail imported by name, under any alias, is a use, and so is each call of the local name (reach
    # b09d5b4b gap 11, AT1 F2, B-066): "from pytest import skip as skip_test", "from pytest import xfail".
    local_skips: set[str] = set()
    local_xfails: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in {
            "pytest",
            "unittest",
            "_pytest",
        }:
            for alias in node.names:
                if alias.name in SKIP_NAMES:
                    local_skips.add(alias.asname or alias.name)
                    skips.append(f"{rel}:{node.lineno}: import {alias.name}")
                elif alias.name in XFAIL_NAMES:
                    local_xfails.add(alias.asname or alias.name)
                    xfails.append((rel, "<import>", False, ""))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in local_skips - SKIP_NAMES:
                skips.append(f"{rel}:{node.lineno}: {node.func.id}()")
            elif node.func.id in local_xfails:
                xfails.append((rel, owners.get(id(node), "<not a decorator>"), False, ""))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in SKIP_NAMES:
            skips.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
        elif isinstance(node, ast.Name) and node.id in SKIP_NAMES:
            skips.append(f"{rel}:{node.lineno}: {node.id}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in XFAIL_NAMES:
                kw = {k.arg: k.value for k in node.keywords}
                strict = isinstance(kw.get("strict"), ast.Constant) and kw["strict"].value is True
                reason = kw.get("reason")
                text = reason.value if isinstance(reason, ast.Constant) else ""
                xfails.append((rel, owners.get(id(node), "<not a decorator>"), strict, str(text)))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr in XFAIL_NAMES
            and not any(id(node) == id(c.func) for c in ast.walk(tree) if isinstance(c, ast.Call))
        ):
            xfails.append((rel, owners.get(id(node), "<not a decorator>"), False, ""))
    return skips, xfails


def test_no_skips_and_no_xfails() -> None:
    """No skip and no xfail anywhere in the test trees."""
    skips: list[str] = []
    xfails: list[tuple[str, str, bool, str]] = []
    for root in TEST_TREES:
        for path in sorted((ROOT / root).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel == "tests/test_ci_checks.py":
                continue
            s, x = _skip_and_xfail_uses(rel, path.read_text(encoding="utf-8"))
            skips += s
            xfails += x
    assert not skips, "skips in the suite:\n" + "\n".join(skips)
    assert not xfails, xfails


@pytest.mark.parametrize(
    "snippet",
    [
        "import pytest\npytest.skip('x')\n",
        "import pytest\n@pytest.mark.skipif(True, reason='x')\ndef test_a(): pass\n",
        "import pytest\npytest.importorskip('x')\n",
        "import unittest\n@unittest.skip('x')\ndef test_a(): pass\n",
    ],
)
def test_skip_detector_catches(snippet: str) -> None:
    assert _skip_and_xfail_uses("tests/probe.py", snippet)[0], snippet


def test_xfail_detector_reads_strict_and_reason() -> None:
    src = (
        "import pytest\n"
        "@pytest.mark.xfail(strict=True, reason='item 1.1')\ndef test_a(): pass\n"
        "@pytest.mark.xfail\ndef test_b(): pass\n"
    )
    found = sorted(_skip_and_xfail_uses("tests/probe.py", src)[1])
    assert found == [
        ("tests/probe.py", "test_a", True, "item 1.1"),
        ("tests/probe.py", "test_b", False, ""),
    ]
