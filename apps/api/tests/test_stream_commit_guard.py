"""SAFETY-004 guard — no early `return` in a get_db stream may leave a write uncommitted.

WHY A STATIC TEST. With FastAPI 0.115.0 (measured, SAFETY-004), get_db's teardown —
commit, then close — runs BEFORE a StreamingResponse body. A stream that takes `db`
from get_db runs on a session that has already been committed, so a row it writes and
does not commit ITSELF is silently lost. The two crisis early-returns on Council and
You-vs-You did exactly that from #548 (2026-08-18) until SAFETY-004: every crisis
disclosure there was answered on screen and never recorded.

The live regression test (tests/db_live/test_safety_events_committed.py) measures each
path that exists today. This one keeps the NEXT early return from repeating the defect:
for every `return` in these streams, if a write happened on the way to it, a
`db.commit()` must sit between that write and the return.

WHAT COUNTS AS A WRITE: db.add / db.delete / db.flush, db.execute(insert|update|delete),
log_safety_event / _log_safety_event, output_is_unsafe (it logs), _save_message. Writes
inside a nested branch count (conservative); a commit counts only if it sits on the
return's own path.

Run: cd apps/api && pytest tests/test_stream_commit_guard.py -v
"""
import ast
from pathlib import Path

import pytest

SERVICES = Path(__file__).resolve().parents[1] / "services"

# Streams whose `db` is the request's get_db session (routers pass db=db). Chat `send`
# (stream_response) is not here: it opens its own sessions via session_factory.
GET_DB_STREAMS = [
    ("council_service.py", "stream_council"),
    ("self_comparison_service.py", "stream"),
    ("conversation_service.py", "stream_another_mind"),
    ("conversation_service.py", "stream_go_deeper"),
]

WRITE_CALLS = {"add", "delete", "flush", "log_safety_event", "_log_safety_event",
               "output_is_unsafe", "_save_message"}
WRITE_STATEMENTS = {"insert", "update", "delete", "pg_insert"}


def _call_name(call: ast.Call) -> str | None:
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def _is_write(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        name = _call_name(sub)
        if name in WRITE_CALLS:
            return True
        if name == "execute" and sub.args and isinstance(sub.args[0], ast.Call) \
                and _call_name(sub.args[0]) in WRITE_STATEMENTS:
            return True
    return False


def _is_commit(stmt: ast.stmt) -> bool:
    """A statement that is itself `await db.commit()` — on the path, not in a branch."""
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await)
            and isinstance(stmt.value.value, ast.Call) and _call_name(stmt.value.value) == "commit")


def _function(file: str, name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse((SERVICES / file).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{file}: {name} not found — update GET_DB_STREAMS")


def _statements_before(fn: ast.AsyncFunctionDef, target: ast.stmt) -> list[ast.stmt]:
    """The statements executed before `target` on its own path, in order: for each
    enclosing block from the function body inward, the siblings that precede it."""
    parents = {}
    for node in ast.walk(fn):
        for field in ("body", "orelse", "finalbody", "handlers"):
            block = getattr(node, field, None)
            if not isinstance(block, list):     # e.g. Lambda.body / IfExp.body is one node
                continue
            for child in block:
                parents[child] = (node, field)
    chain, node = [], target
    while node in parents:
        parent, field = parents[node]
        block = getattr(parent, field)
        chain.append(block[: block.index(node)])
        node = parent
    return [s for block in reversed(chain) for s in block]


def _own_returns(fn: ast.AsyncFunctionDef) -> list[ast.Return]:
    """The stream's own returns — not those of a helper defined inside it."""
    found, stack = [], list(ast.iter_child_nodes(fn))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Return):
            found.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return sorted(found, key=lambda r: r.lineno)


_BLOCK_FIELDS = ("body", "orelse", "finalbody", "handlers")


def _state(stmts: list[ast.stmt]) -> str | None:
    """Scan a sequence: 'dirty' if a write is left uncommitted at its end, 'clean' if
    the last write was committed, None if nothing was written. A compound statement is
    dirty if ANY of its branches ends dirty (conservative), clean if one commits."""
    state = None
    for st in stmts:
        if _is_commit(st):
            state = "clean"
            continue
        branches = [getattr(st, f) for f in _BLOCK_FIELDS if isinstance(getattr(st, f, None), list)]
        if branches and not isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ends = [_state(b if not isinstance(b[0], ast.ExceptHandler) else
                           [x for h in b for x in h.body]) for b in branches if b]
            if "dirty" in ends:
                state = "dirty"
            elif "clean" in ends:
                state = "clean"
            elif _is_write(getattr(st, "test", None) or ast.Pass()):
                state = "dirty"
        elif _is_write(st):
            state = "dirty"
    return state


def _unsafe_returns(file: str, name: str) -> list[int]:
    fn = _function(file, name)
    return [ret.lineno for ret in _own_returns(fn)
            if _state(_statements_before(fn, ret)) == "dirty"]


@pytest.mark.parametrize("file,name", GET_DB_STREAMS, ids=[f"{f}::{n}" for f, n in GET_DB_STREAMS])
def test_every_early_return_commits_what_it_wrote(file, name):
    bad = _unsafe_returns(file, name)
    assert bad == [], (
        f"{file}:{name} returns at line(s) {bad} after a write with no db.commit() in "
        f"between. This stream runs on a get_db session whose teardown has ALREADY "
        f"committed (FastAPI 0.115, SAFETY-004): the write would be silently lost."
    )


def test_the_guard_sees_a_real_violation():
    """The guard must be able to fail, and must not cry wolf:
    - a write, then a return, with no commit: flagged (line 5);
    - a write and a commit, then a return: clean;
    - a write and a commit inside an `if`, return after it: clean (the SAFETY-004 fix);
    - a write inside an `if` with no commit, return after it: flagged (line 15)."""
    src = chr(10).join([
        'async def s(db):',
        '    if a:',
        '        await log_safety_event(db, 1, 2, 3)',
        "        yield 'e'",
        '        return',
        '    if b:',
        '        await log_safety_event(db, 1, 2, 3)',
        '        await db.commit()',
        '        return',
        '    if c:',
        '        await log_safety_event(db, 1, 2, 3)',
        '        await db.commit()',
        '    if d:',
        '        db.add(x)',
        '    return',
    ]) + chr(10)
    fn = ast.parse(src).body[0]
    flagged = [r.lineno for r in _own_returns(fn) if _state(_statements_before(fn, r)) == "dirty"]
    assert flagged == [5, 15]
