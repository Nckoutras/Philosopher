import uuid
from datetime import date, datetime
from sqlalchemy import (
    String, Text, Boolean, Integer, Float, DateTime, Date,
    ForeignKey, JSON, ARRAY, CheckConstraint, UniqueConstraint, func, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from db.session import Base


def gen_uuid():
    return str(uuid.uuid4())


# ── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    auth_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    oauth_provider_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    mirror_host_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    weekly_email_opt_out: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # A16 — token revocation counter. Tokens embed the version they were minted
    # with ("ver"); both validators reject a token whose claim differs. Incrementing
    # this kills every token on every device. A missing claim reads as 0, so pre-A16
    # tokens stay valid until the first increment.
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="user", uselist=False)
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="user")
    memory_entries: Mapped[list["MemoryEntry"]] = relationship("MemoryEntry", back_populates="user")


# ── Subscriptions ─────────────────────────────────────────────────────────────

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    plan: Mapped[str] = mapped_column(String(50), default="free")          # free | pro | premium
    status: Mapped[str] = mapped_column(String(50), default="active")      # active | trialing | past_due | canceled
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="subscription")


# ── Personas ─────────────────────────────────────────────────────────────────

class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    era: Mapped[str | None] = mapped_column(String(100))
    tradition: Mapped[str | None] = mapped_column(String(100))
    tier: Mapped[str] = mapped_column(String(50), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    portrait_url: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="persona", foreign_keys="Conversation.persona_id",
    )
    source_chunks: Mapped[list["SourceChunk"]] = relationship("SourceChunk", back_populates="persona")


# ── Quotes ───────────────────────────────────────────────────────────────────

class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    persona_slug: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    translation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    discuss_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    story_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    themes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('persona_slug', 'source_locator', 'text_en', name='uq_quotes_persona_locator_text'),
        Index('idx_quotes_persona_slug', 'persona_slug'),
    )


# ── Conversations & Messages ──────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    persona_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"), nullable=False)
    # Sticky guest mind: NULL ⇒ falls back to persona_id (the immutable origin/home
    # mind). When set, this overrides who-answers-next / header / thumbnails / quota.
    active_persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    # Pro-only sticky "deep mode": when true AND the sender is Pro/premium, every
    # normal reply is deep. SEPARATE from active_persona_id; inert for non-Pro.
    deep_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    title: Mapped[str | None] = mapped_column(String(500))
    ritual_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_saved_line_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("saved_lines.id", ondelete="SET NULL"), nullable=True)
    source_persona_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="conversations")
    # Two FKs to personas now exist (persona_id + active_persona_id); foreign_keys
    # disambiguates each relationship.
    persona: Mapped["Persona"] = relationship("Persona", back_populates="conversations", foreign_keys=[persona_id])
    active_persona: Mapped["Persona | None"] = relationship("Persona", foreign_keys=[active_persona_id])
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index('ix_conversations_user_active', 'user_id', postgresql_where=text('deleted_at IS NULL')),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    conversation_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    # Components of tokens_used (054). The four Anthropic usage buckets are
    # disjoint and price differently (input 1.0x, cache_creation 1.25x,
    # cache_read 0.1x), so the sum alone cannot express cost. output_tokens is
    # deliberately absent — it is tokens_used minus these three.
    # NULL = pre-054 row or usage read failed. 0 = genuinely zero, and the two
    # must stay distinguishable.
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    cache_creation_tokens: Mapped[int | None] = mapped_column(Integer)
    cache_read_tokens: Mapped[int | None] = mapped_column(Integer)
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retrieval_ids: Mapped[list | None] = mapped_column(JSONB)
    safety_level: Mapped[str] = mapped_column(String(20), default="none")
    persona_override: Mapped[bool] = mapped_column(Boolean, default=False)
    message_kind: Mapped[str] = mapped_column(String(20), nullable=False, default='standard')
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    persona: Mapped["Persona | None"] = relationship("Persona")


# ── Memory ────────────────────────────────────────────────────────────────────

class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"))
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"))
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)  # belief | value | struggle | pattern | milestone
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Vector(1536))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_turn: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="memory_entries")


# ── Insights ─────────────────────────────────────────────────────────────────

class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"))
    persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    insight_type: Mapped[str | None] = mapped_column(String(50))  # pattern | shift | question | challenge
    source_count: Mapped[int | None] = mapped_column(Integer)  # distinct conversations a recurring theme was noticed across
    theme: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional life-theme slug (THEME_VALUES) captured at signal-write
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Mirrors ───────────────────────────────────────────────────────────────────

class Mirror(Base):
    __tablename__ = "mirrors"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    host_persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"), nullable=True)
    insight_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("insights.id", ondelete="SET NULL"), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="weekly")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ring_true: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ring_true_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ring_true_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("kind IN ('weekly', 'preview', 'insight')", name="ck_mirrors_kind"),
        CheckConstraint("status IN ('generated', 'empty', 'suppressed')", name="ck_mirrors_status"),
        CheckConstraint("ring_true IN ('yes', 'partly', 'no')", name="ck_mirrors_ring_true"),
        Index("ix_mirrors_user_created", "user_id", text("created_at DESC")),
        Index("uq_mirrors_user_period_kind", "user_id", "period_start", "kind", unique=True),
        Index("uq_mirrors_insight", "insight_id", unique=True, postgresql_where=text("insight_id IS NOT NULL")),
    )


# ── Weekly Letters ───────────────────────────────────────────────────────────

class WeeklyLetter(Base):
    __tablename__ = "weekly_letters"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    voice_persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'weekly'"))
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Reader write-back: the person's own short response to this letter. One per
    # letter (overwritten on re-submit), fed forward into the next letter via the
    # existing prior-letters fetch. Mirrors the mirrors.ring_true_note pattern.
    write_back_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    write_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('generated', 'empty', 'suppressed')", name="ck_weekly_letters_status"),
        CheckConstraint("kind IN ('weekly', 'monthly')", name="ck_weekly_letters_kind"),
        Index("uq_weekly_letters_user_period", "user_id", "period_start", "kind", unique=True),
        Index("ix_weekly_letters_user_id", "user_id"),
    )


# ── Self Comparisons ─────────────────────────────────────────────────────────

class SelfComparison(Base):
    __tablename__ = "self_comparisons"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    then_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    then_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    now_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    now_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    ring_true: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ring_true_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ring_true_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ── Rituals ───────────────────────────────────────────────────────────────────

class Ritual(Base):
    __tablename__ = "rituals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"))
    tier: Mapped[str] = mapped_column(String(50), default="free")
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[str] = mapped_column(String(50), default="daily")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserRitualCompletion(Base):
    __tablename__ = "user_ritual_completions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    ritual_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("rituals.id"), nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="SET NULL"))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Source Chunks (retrieval) ─────────────────────────────────────────────────

class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"))
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)  # primary_text | biography | commentary | letter
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Vector(1536))
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_ref: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    persona: Mapped["Persona"] = relationship("Persona", back_populates="source_chunks")


# ── Safety Events ─────────────────────────────────────────────────────────────

class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="SET NULL"))
    message_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("messages.id"))
    trigger_stage: Mapped[str] = mapped_column(String(50), nullable=False)   # pre_generation | post_generation
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)      # low | medium | high | critical
    category: Mapped[str | None] = mapped_column(String(100))
    action_taken: Mapped[str] = mapped_column(String(100), nullable=False)   # suppressed | redirected | logged
    raw_flags: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── User Preferences ──────────────────────────────────────────────────────────

class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    themes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    other_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    need_most: Mapped[str] = mapped_column(Text, nullable=False)
    # Onboarding profile pills (tappable, no free text). Nullable: NULL means no
    # profile set. e.g. {"values": ["honesty","freedom"], "disagreement_style": "probe_their_view"}
    profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Derived Self-Portrait payoff cache (server-generated, kept separate from the
    # user-authored `profile`). NULL until first generated. Shape:
    # {"text", "best_fit", "answer_count_watermark", "generated_at"}. Written in 5b.
    portrait_cache: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


# ── OTP Codes ─────────────────────────────────────────────────────────────────

class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    salt: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("ix_otp_codes_email_created", "email", text("created_at DESC")),
    )


# ── Disclaimer ────────────────────────────────────────────────────────────────

class DisclaimerVersion(Base):
    __tablename__ = "disclaimer_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_string: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    age_copy: Mapped[str] = mapped_column(Text, nullable=False)
    positioning_copy: Mapped[str] = mapped_column(Text, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    acceptances: Mapped[list["DisclaimerAcceptance"]] = relationship("DisclaimerAcceptance", back_populates="version")


class DisclaimerAcceptance(Base):
    __tablename__ = "disclaimer_acceptances"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("disclaimer_versions.id"), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    confirmed_age_18: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confirmed_non_therapy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped["DisclaimerVersion"] = relationship("DisclaimerVersion", back_populates="acceptances")

    __table_args__ = (
        UniqueConstraint("user_id", "version_id", name="uq_disclaimer_acceptances_user_version"),
        Index("ix_disclaimer_acceptances_user", "user_id"),
    )


# ── Saved Lines ───────────────────────────────────────────────────────────────

class SavedLine(Base):
    __tablename__ = "saved_lines"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    persona_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_save")
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("source_type IN ('manual_save', 'kept_insight')", name="ck_saved_lines_source_type"),
        Index(
            "ix_saved_lines_user_saved_at",
            "user_id",
            text("saved_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_saved_lines_user_message_active",
            "user_id", "message_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# ── Scheduled Emails ─────────────────────────────────────────────────────────

class ScheduledEmail(Base):
    __tablename__ = "scheduled_emails"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True,
                                     server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False),
                                          ForeignKey("users.id", ondelete="CASCADE"),
                                          nullable=False)
    saved_line_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False),
                                                        ForeignKey("saved_lines.id",
                                                                   ondelete="SET NULL"),
                                                        nullable=True)
    persona_id: Mapped[str] = mapped_column(UUID(as_uuid=False),
                                             ForeignKey("personas.id",
                                                        ondelete="RESTRICT"),
                                             nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Future-self loop (043): optional guess written at schedule time (never emailed),
    # and the reader's review on open (one per letter, overwrite-editable).
    prediction: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  server_default=func.now(),
                                                  onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','sent','failed','cancelled')",
            name="ck_scheduled_emails_status",
        ),
        Index(
            "ix_scheduled_emails_pending",
            "scheduled_for",
            postgresql_where=text("status = 'pending'"),
        ),
    )


# ── Daily Questions ───────────────────────────────────────────────────────────

class DailyQuestion(Base):
    __tablename__ = "daily_questions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ── Daily Usage ───────────────────────────────────────────────────────────────

class DailyUsage(Base):
    __tablename__ = "daily_usage"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    persona_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date(), nullable=False, primary_key=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Per-(user, persona, day) go-deeper count. Drives the free 3/day go-deeper
    # limit (Pro/premium unlimited). Mirrors message_count.
    go_deeper_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Per-(user, persona, day) count of FREE deep-mode replies. The free daily
    # allowance (5/day) is metered on the GLOBAL SUM across personas, not this row
    # alone (see rate_limit_service.check_deep_mode_limit). Pro/premium never bump it.
    deep_mode_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_daily_usage_lookup", "user_id", "usage_date"),
    )


# ── Council ───────────────────────────────────────────────────────────────────

class CouncilCase(Base):
    __tablename__ = "council_cases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="direct")
    mirror_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("mirrors.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    session_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CouncilSession(Base):
    __tablename__ = "council_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("council_cases.id", ondelete="CASCADE"), nullable=False)
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Flat synthesis prose — the verdict beat. Kept populated so the Reflections
    # feed + share card read it unchanged. Null only when synthesis fails.
    synthesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Structured decision instrument: {real_question, tension, verdict, next_move}.
    # Null on old sessions / synthesis failure → live screen falls back to `synthesis`.
    synthesis_structured: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")
    # True when a chat-sourced matter was user-edited before submit (so the members
    # deliberated the EDITED text, not a fresh re-distillation). Persisted for mining.
    matter_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("case_id", "session_number", name="uq_council_sessions_case_number"),
    )


class CouncilResponse(Base):
    __tablename__ = "council_responses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("council_sessions.id", ondelete="CASCADE"), nullable=False)
    persona_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[str] = mapped_column(Text, nullable=False)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CouncilSave(Base):
    __tablename__ = "council_saves"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("council_sessions.id", ondelete="CASCADE"), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_council_saves_user_session"),
        Index("ix_council_saves_user", "user_id"),
    )


class Counterview(Base):
    __tablename__ = "counterviews"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="direct")  # direct | insight
    insight_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("insights.id", ondelete="SET NULL"), nullable=True)
    anchor_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # generated | empty | suppressed
    # "What still stands" closing line — one neutral sentence naming what of the
    # belief survives the challenge. Null on old rows / empty / suppressed / ungrounded.
    still_stands: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Terrain-of-the-belief title (2-4 words) — rendered on the SHARED share card in
    # place of the raw anchor_text. Null on old rows / empty / suppressed / over-length.
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("source IN ('direct', 'insight')", name="ck_counterviews_source"),
        CheckConstraint("status IN ('generated', 'empty', 'suppressed')", name="ck_counterviews_status"),
        Index("ix_counterviews_user_created", "user_id", text("created_at DESC")),
        Index("uq_counterviews_insight", "insight_id", unique=True, postgresql_where=text("insight_id IS NOT NULL")),
    )


class CounterviewResponse(Base):
    __tablename__ = "counterview_responses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    counterview_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("counterviews.id", ondelete="CASCADE"), nullable=False)
    persona_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_counterview_responses_cv", "counterview_id"),
        UniqueConstraint("counterview_id", "persona_slug", "round", name="uq_counterview_response"),
    )


class CounterviewSave(Base):
    __tablename__ = "counterview_saves"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    counterview_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("counterviews.id", ondelete="CASCADE"), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "counterview_id", name="uq_counterview_saves_user_cv"),
        Index("ix_counterview_saves_user", "user_id"),
    )


class SavedQuote(Base):
    __tablename__ = "saved_quotes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quote_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "quote_id", name="uq_saved_quotes_user_quote"),
        # Matches migration 048 exactly (partial, newest-first) so the feed query is
        # index-served and a future autogenerate won't clobber it.
        Index(
            "ix_saved_quotes_user_saved_at",
            "user_id",
            text("saved_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class SelfComparisonSave(Base):
    __tablename__ = "self_comparison_saves"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    self_comparison_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("self_comparisons.id", ondelete="CASCADE"), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "self_comparison_id", name="uq_self_comparison_saves_user_sc"),
        Index("ix_self_comparison_saves_user", "user_id"),
    )


class CounterviewTurn(Base):
    """A bounded user rebuttal + the current speaker's reply, on its own axis
    (`sequence`) so the verdict/go-deeper round model is untouched. `persona_slug`
    is the persona the rebuttal targets (= who answers). `persona_response` is NULL
    unless `status == 'generated'`. The free 3-rebuttal cap counts status='generated'
    rows only (enforced in the service)."""
    __tablename__ = "counterview_turns"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    counterview_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("counterviews.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    persona_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    user_text: Mapped[str] = mapped_column(Text, nullable=False)
    persona_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # generated | empty | suppressed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('generated', 'empty', 'suppressed')", name="ck_counterview_turns_status"),
        UniqueConstraint("counterview_id", "sequence", name="uq_counterview_turn_seq"),
        Index("ix_counterview_turns_cv", "counterview_id"),
    )


class MirrorSave(Base):
    __tablename__ = "mirror_saves"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mirror_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("mirrors.id", ondelete="CASCADE"), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "mirror_id", name="uq_mirror_saves_user_mirror"),
        Index("ix_mirror_saves_user", "user_id"),
    )
