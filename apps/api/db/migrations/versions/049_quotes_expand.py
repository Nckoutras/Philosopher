"""Expand quotes corpus — rewrite 88 contexts + add 110 quotes (88 → 198)

Revision ID: 049_quotes_expand
Revises: 048_saved_quotes
Create Date: 2026-07-12

Data-driven, self-contained (C-01): the payload is a frozen UTF-8 JSON snapshot in
db/migrations/data/quotes_049_data.json (loaded at run time by a path relative to
this file — no app-code import, no absolute path). Two operations:

  1. UPDATE the `context` of all 88 existing rows to their rewritten versions,
     matched by (persona_slug, text_en). Each update MUST touch exactly one row;
     a 0-row match means the live text_en drifted from the snapshot, so we RAISE
     (fail loud) rather than silently skip.
  2. INSERT 110 new rows. Only the authored columns are set; id / created_at /
     discuss_count / story_count / is_active are left to their table defaults, and
     `themes` is written as text[]. Net: quotes goes 88 → 198 (18 per persona).

downgrade() DELETEs the 110 inserted rows (matched by the natural key
persona_slug + source_locator + text_en from the snapshot), restoring the row
count to 88. It does NOT restore the pre-rewrite context text of the 88 rows —
the old contexts are not captured in the snapshot; this content change is
forward-only by design.
"""
import json
import os

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = '049_quotes_expand'
down_revision = '048_saved_quotes'
branch_labels = None
depends_on = None

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "quotes_049_data.json")

# Only the authored columns; the rest (id, created_at, discuss_count, story_count,
# is_active) fall back to their server defaults on insert.
_quotes = sa.table(
    "quotes",
    sa.column("persona_slug", sa.Text),
    sa.column("text_en", sa.Text),
    sa.column("text_original", sa.Text),
    sa.column("source_locator", sa.Text),
    sa.column("translation_note", sa.Text),
    sa.column("confidence", sa.Text),
    sa.column("context", sa.Text),
    sa.column("themes", postgresql.ARRAY(sa.Text)),
)


def _load():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def upgrade() -> None:
    data = _load()
    bind = op.get_bind()

    # 1. Rewrite the 88 existing contexts — each must match exactly one row.
    upd = sa.text(
        "UPDATE quotes SET context = :ctx "
        "WHERE persona_slug = :slug AND text_en = :text_en"
    )
    for u in data["updates"]:
        res = bind.execute(
            upd,
            {"ctx": u["new_context"], "slug": u["persona_slug"], "text_en": u["text_en"]},
        )
        if res.rowcount != 1:
            raise RuntimeError(
                f"049: context UPDATE matched {res.rowcount} rows for "
                f"{u['persona_slug']} / {u['text_en']!r} (expected exactly 1)"
            )

    # 2. Insert the 110 new rows (themes as text[]; defaults for the rest).
    op.bulk_insert(
        _quotes,
        [
            {
                "persona_slug": i["persona_slug"],
                "text_en": i["text_en"],
                "text_original": i["text_original"],
                "source_locator": i["source_locator"],
                "translation_note": i["translation_note"],
                "confidence": i["confidence"],
                "context": i["context"],
                "themes": i["themes"],
            }
            for i in data["inserts"]
        ],
    )


def downgrade() -> None:
    # Remove the 110 inserted rows by their natural key; row count returns to 88.
    # (The 88 rewritten contexts are NOT reverted — forward-only content.)
    data = _load()
    bind = op.get_bind()
    delq = sa.text(
        "DELETE FROM quotes "
        "WHERE persona_slug = :slug AND source_locator = :loc AND text_en = :text_en"
    )
    for i in data["inserts"]:
        bind.execute(
            delq,
            {"slug": i["persona_slug"], "loc": i["source_locator"], "text_en": i["text_en"]},
        )
