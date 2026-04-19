from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_admin: bool
    onboarded_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Subscription ──────────────────────────────────────────────────────────────

class SubscriptionOut(BaseModel):
    plan: str
    status: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool

    class Config:
        from_attributes = True


# ── Persona ───────────────────────────────────────────────────────────────────

class PersonaOut(BaseModel):
    id: str
    slug: str
    name: str
    era: Optional[str]
    tradition: Optional[str]
    tier: str
    tagline: Optional[str] = None
    avatar_emoji: Optional[str] = None
    opening_invocation: Optional[str] = None
    is_accessible: bool = True

    class Config:
        from_attributes = True


# ── Conversation ──────────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    persona_slug: str
    ritual_id: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    persona: PersonaOut
    title: Optional[str]
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    safety_level: str
    persona_override: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Memory ────────────────────────────────────────────────────────────────────

class MemoryEntryOut(BaseModel):
    id: str
    entry_type: str
    content: str
    confidence: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryEntryUpdate(BaseModel):
    content: Optional[str] = None
    is_active: Optional[bool] = None


# ── Insight ───────────────────────────────────────────────────────────────────

class InsightOut(BaseModel):
    id: str
    content: str
    insight_type: Optional[str]
    is_dismissed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Ritual ────────────────────────────────────────────────────────────────────

class RitualOut(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str]
    tier: str
    frequency: str
    is_accessible: bool = True

    class Config:
        from_attributes = True


# ── Billing ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str = Field(pattern="^(pro|premium)$")
    interval: str = Field(default="monthly", pattern="^(monthly|yearly)$")


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


# ── Streaming SSE ─────────────────────────────────────────────────────────────

class StreamEvent(BaseModel):
    type: str   # chunk | done | safety | error
    data: Any


# ── Admin ─────────────────────────────────────────────────────────────────────

class SafetyEventOut(BaseModel):
    id: str
    user_id: Optional[str]
    conversation_id: Optional[str]
    trigger_stage: str
    risk_level: str
    category: Optional[str]
    action_taken: str
    raw_flags: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True
