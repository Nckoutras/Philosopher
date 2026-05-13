"""Add bio and portrait_url columns to personas

Revision ID: 005_personas_bio_portrait
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = '005_personas_bio_portrait'
down_revision = '004_user_preferences'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('personas', sa.Column('bio', sa.Text(), nullable=False, server_default=''))
    op.add_column('personas', sa.Column('portrait_url', sa.Text(), nullable=False, server_default=''))

    op.execute("""
        UPDATE personas SET
            bio = 'Roman emperor, last of the Five Good Emperors. He wrote ''Meditations'' as private notes to himself — not philosophy for publication, but reminders to a man trying to govern an empire while staying human. Stoic, disciplined, oriented toward what''s in your control. He treats grief like weather: real, passing, not personal. If you came looking for someone who won''t flinch at hard things, he won''t.',
            portrait_url = '/personas/marcus_aurelius.jpg'
        WHERE slug = 'marcus_aurelius'
    """)

    op.execute("""
        UPDATE personas SET
            bio = 'Athenian gadfly, executed at 70 for asking too many questions. Wrote nothing — everything we know comes through Plato and Xenophon. His method: ask, listen, ask again, until your own answer reveals itself or collapses. He does not give you wisdom. He helps you find what you already half-knew. Expect to be questioned more than comforted.',
            portrait_url = '/personas/socrates.jpg'
        WHERE slug = 'socrates'
    """)

    op.execute("""
        UPDATE personas SET
            bio = 'French existentialist, philosopher, novelist, intellectual partner to Sartre but a thinker in her own right. Wrote ''The Second Sex'' and ''The Ethics of Ambiguity''. She believes you are made by your choices — that freedom is a burden, not a gift. She talks about love, work, aging, motherhood, and refusal. If you came tangled in relationships and identity, she''ll meet you there.',
            portrait_url = '/personas/simone_de_beauvoir.webp'
        WHERE slug = 'simone_de_beauvoir'
    """)

    op.execute("""
        UPDATE personas SET
            bio = 'Born a slave in Rome, became one of antiquity''s most quoted teachers. Lame, exiled, but free in the way that mattered. His teaching is brutally simple: separate what you control from what you don''t, and stop wasting yourself on the second. He does not coddle. He has no patience for self-pity but enormous patience for the work of becoming.',
            portrait_url = '/personas/epictetus.webp'
        WHERE slug = 'epictetus'
    """)

    op.execute("""
        UPDATE personas SET
            bio = 'Viennese physician who invented psychoanalysis. Mapped the unconscious — the parts of yourself you refuse to see, the wishes you keep hidden, the patterns you repeat. He does not believe you understand your own motives. He listens for what you do not say. Controversial, often wrong, but the language he gave us to discuss the mind is still ours. Bring your dreams.',
            portrait_url = '/personas/sigmund_freud.webp'
        WHERE slug = 'sigmund_freud'
    """)


def downgrade():
    op.drop_column('personas', 'portrait_url')
    op.drop_column('personas', 'bio')
