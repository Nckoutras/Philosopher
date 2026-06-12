from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Literal, Union
from typing_extensions import Annotated
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


class UpdateMeRequest(BaseModel):
    full_name: str

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('full_name cannot be empty')
        if len(v) > 100:
            raise ValueError('full_name must be 100 characters or fewer')
        return v


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
    bio: str = ""
    portrait_url: str = ""
    is_accessible: bool = True

    class Config:
        from_attributes = True


# ── Conversation ──────────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    persona_slug: str
    ritual_id: Optional[str] = None
    skip_opening: bool = False


class ConversationOut(BaseModel):
    id: str
    persona: PersonaOut
    title: Optional[str]
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    source_persona_slug: Optional[str] = None
    source_context_content: Optional[str] = None
    last_message_snippet: Optional[str] = None

    class Config:
        from_attributes = True


class CrossPersonaRequest(BaseModel):
    saved_line_id: str
    target_persona_slug: str


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    seeded_opening: bool = False


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    safety_level: str
    persona_override: bool
    persona_slug: str | None = None
    # 'standard' | 'go_deeper' | 'conclusion'. Lets the client feature the
    # gravity-gated conclusion as the headline savable unit.
    message_kind: str = 'standard'
    created_at: datetime

    class Config:
        from_attributes = True


class AnotherMindCreate(BaseModel):
    target_persona_slug: str


class CouncilCreate(BaseModel):
    matter: str
    source: str = "direct"          # "direct" | "mirror"
    mirror_id: str | None = None


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


class LLMErrorResponse(BaseModel):
    error_code: str
    persona_voice: str


# ── Saved Lines ───────────────────────────────────────────────────────────────

class SavedLineCreate(BaseModel):
    message_id: str


class SavedLineOut(BaseModel):
    id: str
    user_id: str
    message_id: str
    persona_id: str
    source_type: str
    saved_at: datetime

    class Config:
        from_attributes = True


class SavedLineRead(BaseModel):
    id: str
    message_id: str
    persona_id: str
    persona_slug: str
    persona_display_name: str
    message_content: str
    conversation_id: str
    saved_at: datetime
    source_type: str

    class Config:
        from_attributes = True


class SavedLineListResponse(BaseModel):
    items: list[SavedLineRead]
    total_count: int
    free_tier_limit: Optional[int]


class SavedLineLimitError(BaseModel):
    detail: str
    code: str
    limit: int
    current_count: int


class SavedLineBadRoleError(BaseModel):
    detail: str


# ── Scheduled Emails ─────────────────────────────────────────────────────────

class ScheduledEmailCreate(BaseModel):
    saved_line_id: str
    note: Optional[str] = Field(None, max_length=2000)
    scheduled_for: datetime
    recipient_email: Optional[EmailStr] = None

    @field_validator("scheduled_for")
    @classmethod
    def validate_scheduled_for(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if v < now + timedelta(hours=1):
            raise ValueError("scheduled_for must be at least 1 hour in the future")
        if v > now + timedelta(days=1825):
            raise ValueError("scheduled_for must be within 5 years from now")
        return v


class ScheduledEmailOut(BaseModel):
    id: str
    saved_line_id: Optional[str]
    persona_id: str
    note: Optional[str]
    recipient_email: str
    scheduled_for: datetime
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledEmailListItem(BaseModel):
    id: str
    persona_id: str
    persona_name: str
    persona_portrait_url: str
    scheduled_for: datetime
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Mirror ────────────────────────────────────────────────────────────────────

class MirrorOut(BaseModel):
    id: str
    kind: str
    status: str
    period_start: datetime
    period_end: datetime
    host_persona_slug: str | None = None
    host_persona_name: str | None = None
    payload: dict | None = None
    ring_true: str | None = None
    ring_true_note: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class RingTrueRequest(BaseModel):
    ring_true: Literal["yes", "partly", "no"]
    note: str | None = None


class MirrorHostOut(BaseModel):
    slug: str
    name: str
    portrait_url: str | None = None

    class Config:
        from_attributes = True


class MirrorHostsResponse(BaseModel):
    hosts: list[MirrorHostOut]
    selected: str | None = None
    default: str = "carl_jung"


class SetMirrorHostRequest(BaseModel):
    host_slug: str


# ── Home / Today ───────────────────────────────────────────────────────────────

class DailyQuestionOut(BaseModel):
    id: str
    question_text: str


class LastConversationOut(BaseModel):
    conversation_id: str
    persona_id: str
    persona_slug: str
    persona_name: str
    persona_tagline: Optional[str]
    persona_portrait_url: str
    last_message_snippet: Optional[str]
    updated_at: datetime


class RecentSavedLineOut(BaseModel):
    saved_line_id: str
    content: str
    persona_id: str
    persona_slug: str
    persona_name: str
    persona_portrait_url: str
    conversation_id: str
    saved_at: datetime


# ── Weekly Letter ────────────────────────────────────────────────────────────

class WeeklyLetterOut(BaseModel):
    id: str
    period_start: datetime
    period_end: datetime
    status: str
    payload: dict | None = None
    read_at: datetime | None = None
    voice_persona_slug: str | None = None
    voice_persona_name: str | None = None

    class Config:
        from_attributes = True


# ── Self Comparison ───────────────────────────────────────────────────────────

class SelfModelWindowOut(BaseModel):
    start: datetime
    end: datetime
    by_type: dict[str, list[str]]


class SelfModelStatusOut(BaseModel):
    unlocked: bool
    total_signals: int
    reason: Optional[str] = None
    forming_preview: list[str] = []
    then: Optional[SelfModelWindowOut] = None
    now: Optional[SelfModelWindowOut] = None
    weekly_remaining: Optional[int] = None
    weekly_limit: Optional[int] = None
    plan: Optional[str] = None


# ── Reflections feed (unified saved lines + mirror/council verdicts) ──────────

class ReflectionFeedLine(BaseModel):
    """A saved line — identical shape to SavedLineRead, tagged with a kind."""
    kind: Literal["line"] = "line"
    id: str
    message_id: str
    persona_id: str
    persona_slug: str
    persona_display_name: str
    message_content: str
    conversation_id: str
    saved_at: datetime
    source_type: str


class ReflectionFeedMirror(BaseModel):
    """A saved Mirror verdict — the closing-line `thread` plus its host persona."""
    kind: Literal["mirror_verdict"] = "mirror_verdict"
    save_id: str
    mirror_id: str
    thread: str
    host_persona_slug: Optional[str] = None
    host_persona_name: Optional[str] = None
    mirror_kind: str  # 'weekly' | 'preview'
    saved_at: datetime


class ReflectionFeedCouncil(BaseModel):
    """A saved Council verdict — the synthesis plus the participating persona slugs."""
    kind: Literal["council_verdict"] = "council_verdict"
    save_id: str
    session_id: str
    synthesis: str
    persona_slugs: list[str]
    created_at: datetime
    saved_at: datetime


ReflectionFeedItem = Annotated[
    Union[ReflectionFeedLine, ReflectionFeedMirror, ReflectionFeedCouncil],
    Field(discriminator="kind"),
]


class ReflectionsFeedResponse(BaseModel):
    items: list[ReflectionFeedItem]
