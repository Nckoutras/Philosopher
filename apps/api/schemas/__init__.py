from datetime import datetime
from typing import Optional, Any, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


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
    needs_disclaimer: bool = False

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


# ── OTP ───────────────────────────────────────────────────────────────────────

class OtpRequest(BaseModel):
    email: EmailStr


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


# ── Disclaimer ────────────────────────────────────────────────────────────────

class DisclaimerAcceptRequest(BaseModel):
    confirmed_age_18: bool
    confirmed_non_therapy: bool
    locale: Optional[str] = "en"


class DisclaimerAcceptOut(BaseModel):
    accepted_at: datetime
    version_string: str


class DisclaimerCurrentOut(BaseModel):
    version_string: str
    age_copy: str
    positioning_copy: str


# ── Preferences ───────────────────────────────────────────────────────────────

THEME_VALUES = ("separation", "anxiety", "fear", "grief", "acceptance", "work", "relationships", "purpose")
NEED_MOST_VALUES = ("comfort", "challenge", "interpretation", "practical_steadiness")


class PreferenceUpsertRequest(BaseModel):
    themes: list[Literal["separation", "anxiety", "fear", "grief", "acceptance", "work", "relationships", "purpose"]] = Field(default_factory=list, max_length=8)
    other_text: str | None = Field(default=None, max_length=500)
    need_most: Literal["comfort", "challenge", "interpretation", "practical_steadiness"]

    @field_validator("themes")
    @classmethod
    def dedupe_themes(cls, v: list[str]) -> list[str]:
        # Silently deduplicate; preserve first-seen order
        seen = set()
        result = []
        for theme in v:
            if theme not in seen:
                seen.add(theme)
                result.append(theme)
        return result

    @field_validator("other_text")
    @classmethod
    def normalize_other_text(cls, v: str | None) -> str | None:
        # Treat whitespace-only as None
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None

    @model_validator(mode="after")
    def at_least_one_signal(self) -> "PreferenceUpsertRequest":
        # Mirrors the DB CHECK constraint ck_user_preferences_some_input.
        # Validate at the app layer so the user gets a clean 422, not an opaque 500.
        if not self.themes and not self.other_text:
            raise ValueError("Provide at least one theme or fill the other field.")
        return self


class PreferenceOut(BaseModel):
    themes: list[str]
    other_text: str | None
    need_most: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Matches ───────────────────────────────────────────────────────────────────

class MatchOut(BaseModel):
    """Single persona match in the GET /preferences/matches response."""

    slug: str
    score: int
    reason: str

    class Config:
        from_attributes = True
