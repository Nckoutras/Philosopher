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

    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="persona")
    source_chunks: Mapped[list["SourceChunk"]] = relationship("SourceChunk", back_populates="persona")


# ── Conversations & Messages ──────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    persona_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("personas.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    ritual_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_saved_line_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("saved_lines.id", ondelete="SET NULL"), nullable=True)
    source_persona_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="conversations")
    persona: Mapped["Persona"] = relationship("Persona", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", order_by="Message.created_at")

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
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retrieval_ids: Mapped[list | None] = mapped_column(JSONB)
    safety_level: Mapped[str] = mapped_column(String(20), default="none")
    persona_override: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


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
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_daily_usage_lookup", "user_id", "usage_date"),
    )
