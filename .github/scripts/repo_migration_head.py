#!/usr/bin/env python3
"""Print the single alembic head revision id recorded in this checkout.

Used by .github/workflows/db-backup.yml to answer one question before it dumps
anything: *is this the database this repository actually migrates?*

The backup workflow compares this value against `SELECT version_num FROM
alembic_version` on the target. A mismatch fails the job. That guard exists
because of a concrete near-miss on 2026-09-14: the Supabase project NAMED
"Philosopher" is not production. It is the pre-Oregon database, abandoned in
May 2026 at revision `015_add_fk_indexes`, and a backup pointed at it would
have been green every night and worthless. Nothing about the connection string
says which database is on the other end; the schema version does.

The check is deliberately two-sided. It catches a backup aimed at the wrong
project, AND it catches a migration applied to the wrong project - both present
as the same disagreement.

Parsing is done with `ast`, not regex: it reads module-level assignments the
way Python does, so `revision: str = "x"`, a tuple `down_revision`, and a
commented-out assignment all behave correctly.

Stdlib only, by design: no dependency of this script may break the backup.

Usage:
    python3 .github/scripts/repo_migration_head.py      # prints e.g. 061_trajectory_snapshots
"""
import ast
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "apps" / "api" / "db" / "migrations" / "versions"


def _assigned_strings(tree, target_name):
    """Every string literal assigned to `target_name` at module level.

    Returns a list because a merge migration's `down_revision` is a tuple of
    parent ids. `down_revision = None` yields an empty list, which is what the
    base revision should contribute to the "referenced" set.
    """
    found = []
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue

        if not any(isinstance(t, ast.Name) and t.id == target_name for t in targets):
            continue

        value = node.value
        if value is None:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            found.append(value.value)
        elif isinstance(value, (ast.Tuple, ast.List)):
            for el in value.elts:
                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                    found.append(el.value)
    return found


def main():
    if not VERSIONS_DIR.is_dir():
        print(f"migrations directory not found: {VERSIONS_DIR}", file=sys.stderr)
        return 2

    files = sorted(p for p in VERSIONS_DIR.glob("*.py") if p.name != "__init__.py")
    if not files:
        # An empty scan must never print a confident answer.
        print("no migration files found - check the path", file=sys.stderr)
        return 2

    revisions = set()
    referenced = set()

    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            print(f"{path.name}: cannot parse: {exc}", file=sys.stderr)
            return 2

        own = _assigned_strings(tree, "revision")
        if len(own) != 1:
            print(
                f"{path.name}: expected exactly 1 `revision = ...`, found {len(own)}",
                file=sys.stderr,
            )
            return 2
        revisions.add(own[0])
        referenced.update(_assigned_strings(tree, "down_revision"))

    heads = sorted(revisions - referenced)

    if len(heads) != 1:
        # backend-ci.yml already enforces a single head via `alembic heads`.
        # Repeating it here keeps this script honest on its own terms: it must
        # never print one id when the chain actually has two.
        print(
            f"expected exactly 1 head, found {len(heads)}: {heads}",
            file=sys.stderr,
        )
        return 1

    print(heads[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
