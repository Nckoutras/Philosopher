import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, Boolean, Integer, Float, DateTime,
    ForeignKey, JSON, ARRAY, CheckConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="conversations")
    persona: Mapped["Persona"] = relationship("Persona", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    conversation_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
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
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id"))
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
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id"))
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
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id"))
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
    page_ref: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    persona: Mapped["Persona"] = relationship("Persona", back_populates="source_chunks")


# ── Safety Events ─────────────────────────────────────────────────────────────

class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id"))
    message_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("messages.id"))
    trigger_stage: Mapped[str] = mapped_column(String(50), nullable=False)   # pre_generation | post_generation
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)      # low | medium | high | critical
    category: Mapped[str | None] = mapped_column(String(100))
    action_taken: Mapped[str] = mapped_column(String(100), nullable=False)   # suppressed | redirected | logged
    raw_flags: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
