"""Standardize persona portraits to .webp (repoint the 6 non-webp rows)

Revision ID: 026_personas_portrait_webp
Revises: 025_create_mirror_saves
Create Date: 2026-06-16

Data-only. New oil-painting portraits replaced the 9 persona images and every
portrait is now served as .webp (WebP is the standardized format; the old
multi-MB sources were not committed). Six personas had non-webp extensions in
personas.portrait_url and are repointed here:

    socrates, marcus_aurelius           .jpg -> .webp
    carl_jung, lao_tzu, oscar_wilde     .png -> .webp
    niccolo_machiavelli  (file machiavelli.png -> machiavelli.webp)

The 3 personas already on .webp (sigmund_freud, epictetus, simone_de_beauvoir)
need NO DB change — their .webp files were overwritten in place.

NO schema change: no columns added/dropped, no tables touched other than these
6 personas rows. Fully reversible (DOWN restores the original extensions).
"""
from alembic import op

revision = '026_personas_portrait_webp'
down_revision = '025_create_mirror_saves'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE personas SET portrait_url='/personas/socrates.webp'        WHERE slug='socrates'")
    op.execute("UPDATE personas SET portrait_url='/personas/marcus_aurelius.webp' WHERE slug='marcus_aurelius'")
    op.execute("UPDATE personas SET portrait_url='/personas/carl_jung.webp'       WHERE slug='carl_jung'")
    op.execute("UPDATE personas SET portrait_url='/personas/lao_tzu.webp'         WHERE slug='lao_tzu'")
    op.execute("UPDATE personas SET portrait_url='/personas/oscar_wilde.webp'     WHERE slug='oscar_wilde'")
    op.execute("UPDATE personas SET portrait_url='/personas/machiavelli.webp'     WHERE slug='niccolo_machiavelli'")


def downgrade() -> None:
    op.execute("UPDATE personas SET portrait_url='/personas/socrates.jpg'         WHERE slug='socrates'")
    op.execute("UPDATE personas SET portrait_url='/personas/marcus_aurelius.jpg'  WHERE slug='marcus_aurelius'")
    op.execute("UPDATE personas SET portrait_url='/personas/carl_jung.png'        WHERE slug='carl_jung'")
    op.execute("UPDATE personas SET portrait_url='/personas/lao_tzu.png'          WHERE slug='lao_tzu'")
    op.execute("UPDATE personas SET portrait_url='/personas/oscar_wilde.png'      WHERE slug='oscar_wilde'")
    op.execute("UPDATE personas SET portrait_url='/personas/machiavelli.png'      WHERE slug='niccolo_machiavelli'")
