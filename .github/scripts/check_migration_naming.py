#!/usr/bin/env python3
"""Enforce CLAUDE.md C-04 on alembic migration files.

Two rules, checked independently:

  RULE 1  revision id <= 32 characters.
          alembic_version.version_num is VARCHAR(32). A longer id crashes the
          deploy at the version-write step. This is not hypothetical:
          035_deep_mode_and_go_deeper_count (33 chars) took production down on
          2026-06-26 and had to be renamed in #371. Postgres DDL is
          transactional so the upgrade rolled back cleanly, but the deploy
          still failed.

  RULE 2  filename (minus .py) == the in-file revision id.
          Keeps the chain greppable and stops a rename touching one but not
          the other.

Stdlib only, by design: no dependency of this script may break CI itself.

Usage:
    python .github/scripts/check_migration_naming.py
"""
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "apps" / "api" / "db" / "migrations" / "versions"

MAX_REVISION_ID_LEN = 32

# CLOSED allowlist — RULE 2 ONLY.
#
# Both files predate C-04 (codified 2026-06-26) and both revision ids are
# comfortably inside the 32-char limit (20 and 19 chars), so neither carries the
# deploy-crash risk that rule exists to prevent — only their filenames disagree
# with their revision ids. Renaming a migration file is prohibited, so they are
# grandfathered here rather than fixed.
#
# This list is CLOSED. Adding to it requires founder approval. If you are here
# because a new migration failed rule 2, rename the file to match its revision
# id — that is the fix, not an entry below.
RULE_2_ALLOWLIST = frozenset({
    "013_add_ondelete_conversation_fks.py",  # revision = 013_conv_fk_ondelete
    "014_user_oauth_columns.py",             # revision = 014_user_oauth_cols
})

_REVISION = re.compile(
    r"^revision\s*(?::\s*str\s*)?=\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)


def main():
    if not VERSIONS_DIR.is_dir():
        print(f"::error::migrations directory not found: {VERSIONS_DIR}")
        return 2

    files = sorted(p for p in VERSIONS_DIR.glob("*.py") if p.name != "__init__.py")
    if not files:
        # An empty scan must never be a silent pass.
        print("::error::no migration files found - check the path")
        return 2

    violations = []
    exempted = []

    for path in files:
        src = path.read_text(encoding="utf-8", errors="replace")
        m = _REVISION.search(src)
        if m is None:
            violations.append((path.name, "no `revision = ...` assignment found"))
            continue

        revision = m.group(1)

        if len(revision) > MAX_REVISION_ID_LEN:
            violations.append((
                path.name,
                f"RULE 1: revision id {revision!r} is {len(revision)} chars "
                f"(max {MAX_REVISION_ID_LEN}) - this crashes the deploy",
            ))

        if revision != path.stem:
            if path.name in RULE_2_ALLOWLIST:
                exempted.append((path.name, revision))
            else:
                violations.append((
                    path.name,
                    f"RULE 2: filename stem {path.stem!r} != revision id {revision!r} "
                    f"- rename the file to {revision}.py",
                ))

    print(f"migration files checked : {len(files)}")
    print(f"rule-2 exemptions used  : {len(exempted)}")
    for name, rev in exempted:
        print(f"    (grandfathered) {name} -> revision {rev}")
    print(f"violations              : {len(violations)}")

    if violations:
        print("")
        for name, msg in violations:
            print(f"  {name}: {msg}")
            print(f"::error file=apps/api/db/migrations/versions/{name}::{msg}")
        print("")
        print("See CLAUDE.md C-04. Fix by renaming the file and updating BOTH the")
        print("in-file `revision = ...` and the NEXT migration's `down_revision = ...`.")
        return 1

    print("")
    print("OK - all migration files satisfy C-04.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
