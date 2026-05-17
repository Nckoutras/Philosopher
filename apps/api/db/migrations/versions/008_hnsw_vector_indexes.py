"""HNSW vector indexes on source_chunks and memory_entries; adds chunk_index to source_chunks

Replaces IVFFlat indexes (created in 001_initial) with HNSW indexes, which offer
better recall and query speed for our corpus size without needing to pre-specify
a cluster count. Also adds chunk_index to source_chunks for idempotent ingestion.

Revision ID: 008_hnsw_vector_indexes
Revises: 007_block_c_schema
Create Date: 2026-05-17
"""
import sqlalchemy as sa
from alembic import op


revision = '008_hnsw_vector_indexes'
down_revision = '007_block_c_schema'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add chunk_index to source_chunks for positional dedup during ingestion
    op.add_column(
        'source_chunks',
        sa.Column('chunk_index', sa.Integer, nullable=True),
    )

    # 2. Partial unique index enables ON CONFLICT upsert in ingest_corpus.py.
    #    Partial (WHERE chunk_index IS NOT NULL) so existing null rows are unaffected.
    op.execute("""
        CREATE UNIQUE INDEX uq_source_chunks_persona_title_chunk
        ON source_chunks (persona_id, source_title, chunk_index)
        WHERE chunk_index IS NOT NULL
    """)

    # 3. Drop IVFFlat indexes from 001_initial — superseded by HNSW below.
    #    IVFFlat requires pre-specifying list count; HNSW does not and is
    #    strictly better for datasets under ~1M rows.
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS idx_memory_embedding")

    # 4. HNSW index on source_chunks.embedding (cosine distance matches retrieval query)
    op.execute("""
        CREATE INDEX ix_source_chunks_embedding_hnsw_cosine
        ON source_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # 5. HNSW index on memory_entries.embedding (same operator class)
    op.execute("""
        CREATE INDEX ix_memory_entries_embedding_hnsw_cosine
        ON memory_entries USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_memory_entries_embedding_hnsw_cosine")
    op.execute("DROP INDEX IF EXISTS ix_source_chunks_embedding_hnsw_cosine")

    # Re-create original IVFFlat indexes
    op.execute("""
        CREATE INDEX idx_chunks_embedding
        ON source_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    op.execute("""
        CREATE INDEX idx_memory_embedding
        ON memory_entries USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    op.execute("DROP INDEX IF EXISTS uq_source_chunks_persona_title_chunk")
    op.drop_column('source_chunks', 'chunk_index')
