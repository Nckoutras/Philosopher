from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Literal, Union
from typing_extensions import Annotated
from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator

from text_utils import shorten_source


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"
    # True only when THIS request created the account. OTP sign-in creates a user
    # implicitly when the verified email has no row (auth.py:198), and the screens were
    # identical either way — so a mistyped address the user also owns produced a second,
    # empty account with no signal at all.
    #
    # Defaults False so the login / register / refresh mint sites need no edit: that the
    # diff does not touch them IS the guarantee they are unchanged.
    #
    # Set only AFTER successful verification. Reporting at request time whether an email
    # is known would let an unauthenticated caller enumerate accounts.
    is_new_account: bool = False


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_admin: bool
    onboarded_at: Optional[datetime]
    created_at: datetime
    needs_disclaimer: bool = False
    # Global free daily deep-mode allowance remaining today (0..5). -1 = unlimited
    # (pro/premium). Computed in the /me handler; not an ORM column.
    deep_remaining: int = -1

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


# ── Quotes ────────────────────────────────────────────────────────────────────

class QuoteOut(BaseModel):
    id: str
    persona_slug: str
    text_en: str
    text_original: Optional[str] = None
    source_locator: str
    translation_note: Optional[str] = None
    confidence: str
    context: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def source_short(self) -> str:
        # Compact, word-boundary source for the carousel card + share preview.
        # source_locator stays full (used by "The story").
        return shorten_source(self.source_locator)

    class Config:
        from_attributes = True


class SuggestedQuoteOut(QuoteOut):
    # matched_themes = the quote.themes ∩ user-candidate-themes intersection that
    # drove the match; the frontend uses it to render the "why this" reason.
    matched_themes: list[str] = []


# ── Conversation ──────────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    persona_slug: str
    ritual_id: Optional[str] = None
    skip_opening: bool = False
    # Γ-3. True ONLY from the bare persona-page open: hand back the last real
    # conversation with this persona when one is still within the resume window,
    # else create as before. Defaults False so every seeded door (letter discuss,
    # quotes, self-portrait, Today nudge, cross-persona, rituals) keeps creating
    # a fresh thread exactly as today — a seed belongs in a new conversation, not
    # appended to an old one.
    resume: bool = False


class ConversationOut(BaseModel):
    id: str
    # Γ-3. True when this open handed back an EXISTING thread rather than
    # creating one. The client needs it for two reasons: /app/chat/[slug] holds
    # no message history (the store clears `messages` on setActiveConversation),
    # so a resumed thread must be handed to /app/chat/conv/{id}, which loads it;
    # and the header's "Start fresh" escape hatch only appears on a resume.
    # Default False keeps every other creation response byte-compatible.
    resumed: bool = False
    persona: PersonaOut
    title: Optional[str]
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    source_persona_slug: Optional[str] = None
    source_context_content: Optional[str] = None
    last_message_snippet: Optional[str] = None
    # `persona` above is the coalesced ACTIVE mind (sticky guest when set, else
    # home). These two always point to the immutable home/origin persona so the
    # client can render "Return to [origin]" and detect stickiness
    # (persona.slug != origin_persona_slug).
    origin_persona_slug: Optional[str] = None
    origin_persona_name: Optional[str] = None
    # Pro sticky deep mode: when true (and the user is Pro), every reply is deep.
    deep_mode: bool = False

    class Config:
        from_attributes = True


class CrossPersonaRequest(BaseModel):
    saved_line_id: str
    target_persona_slug: str


class ReadingRevisitCreate(BaseModel):
    weekly_letter_id: str
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


class ActiveMindSet(BaseModel):
    """Set the conversation's sticky active mind (continue with a guest)."""
    target_persona_slug: str


class CouncilCreate(BaseModel):
    matter: str
    # Which door produced this council. SHAPE is validated here, not membership —
    # the same rule, and the same reason, as CheckoutRequest.source below: the
    # vocabulary lives where it is written (the web sets council_source in
    # sessionStorage from four places) and duplicating it here would give two
    # sources of truth that drift. This field is why that matters concretely: the
    # comment it replaces listed three values and the code had grown a fourth
    # ("nudge", from the insight card's Council door), so a membership check
    # written from the comment would have refused a real, shipped door.
    #
    # The bound is what was missing. This is client-supplied and reached
    # analytics unvalidated; the router normalises it to a four-value set before
    # use, and the pattern stops anything unbounded arriving in the first place.
    source: str = Field(default="direct", pattern="^[a-z_]{1,32}$")
    mirror_id: str | None = None
    # Γ-7-lite. The insight card that opened this council, for source='nudge'.
    # Validated as a UUID at the router, not here: an unparseable id must not 422
    # a council the person is trying to convene — the link is a record, and losing
    # it is strictly better than refusing the ritual over it.
    insight_id: str | None = None
    conversation_id: str | None = None   # chat source only; drives the essence brief
    matter_edited: bool = False          # chat source only; user edited the auto-filled matter → skip re-distill


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
    source_count: Optional[int]
    conversation_id: Optional[str]
    is_dismissed: bool
    # The reader's verdict (063), NULL until they answer. Returned so a card that
    # has already been answered renders its own state rather than an empty row —
    # the surfaces are stateless and the row is the only memory of the answer.
    ring_true: Optional[str] = None
    ring_true_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InsightRingTrueRequest(BaseModel):
    """PATCH /insights/{id}/ring-true.

    Literal, matching RingTrueRequest (mirrors) rather than a bare `str`: the
    vocabulary is closed, the DB has a CHECK that would otherwise reject the write
    as a 500, and this value reaches analytics — the Γ-1b rule that an enum
    property must be bound at the edge applies to a `verdict` exactly as it did
    to a `source`. No `note` in v1: migration 063 says why a third free-text
    column with no reader is debt rather than a feature.
    """
    ring_true: Literal["yes", "partly", "no"]


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
    # Single Pro tier. Rejecting "premium" here (422) rather than letting it reach
    # the router, where it now fails as a confusing 400 "Invalid plan/interval:
    # premium_monthly" — premium_monthly was removed from PLANS in #526.
    plan: str = Field(pattern="^pro$")
    interval: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    # Which paywall produced this checkout. SHAPE is validated here, not
    # membership: the enum lives in apps/web/lib/upgradeCopy.ts, which is where
    # it is read and rendered. Duplicating the list server-side would give two
    # sources of truth that drift, and a value this endpoint does not recognise
    # is a reporting gap, never a reason to refuse a payment.
    source: str | None = Field(default=None, pattern="^[a-z_]{1,32}$")


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

THEME_VALUES = ("separation", "anxiety", "fear", "grief", "acceptance", "work", "relationships", "purpose", "dilemma", "controversy", "doubt", "freedom")
NEED_MOST_VALUES = ("comfort", "challenge", "interpretation", "practical_steadiness")


class PreferenceUpsertRequest(BaseModel):
    themes: list[Literal["separation", "anxiety", "fear", "grief", "acceptance", "work", "relationships", "purpose", "dilemma", "controversy", "doubt", "freedom"]] = Field(default_factory=list, max_length=12)
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


class ProfileIn(BaseModel):
    """Onboarding profile pills. Bounded enums only — no free text in v1."""
    values: list[Literal["honesty", "freedom", "loyalty", "justice", "growth", "security", "connection", "achievement"]] = Field(default_factory=list, max_length=3)
    disagreement_style: Literal["stand_firm", "seek_the_middle", "avoid_conflict", "probe_their_view", "heat_then_reflect"] | None = None

    @field_validator("values")
    @classmethod
    def dedupe_values(cls, v: list[str]) -> list[str]:
        seen = set()
        result = []
        for val in v:
            if val not in seen:
                seen.add(val)
                result.append(val)
        return result


class PreferenceOut(BaseModel):
    themes: list[str]
    other_text: str | None
    need_most: str
    profile: dict | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileReflectionOut(BaseModel):
    bullets: list[str]


class SelfPortraitAnswerIn(BaseModel):
    """One Self-Portrait quiz answer: a question id + the index of the chosen pill.
    Existence of the id and the pill_index range are validated against the question
    bank in the router (a bad value → 400), not here."""
    question_id: str = Field(min_length=1)
    pill_index: int = Field(ge=0)


class SelfPortraitQuestionOut(BaseModel):
    """One Self-Portrait question in its PUBLIC shape — the internal theme_tags are
    stripped server-side (see services.self_portrait.visible_questions)."""
    id: str
    category: str
    question: str
    pills: list[str]


class SelfPortraitOut(BaseModel):
    """GET /preferences/self-portrait payload: the questions this tier may see, the
    user's stored answers (filtered to the visible set), the tier flag, and how many
    questions remain locked behind Pro (0 for Pro)."""
    questions: list[SelfPortraitQuestionOut]
    answers: dict[str, int]
    is_pro: bool
    locked_count: int
    # Category coverage, for the breadth bar. answered_category_count is computed from
    # the UNFILTERED stored answers, not from `answers` above — a lapsed Pro→free user
    # answered categories whose questions this tier can no longer see, and those still
    # count. total_category_count is derived from the bank, never hardcoded.
    answered_category_count: int
    total_category_count: int


class BestFitOut(BaseModel):
    """One best-fit persona for the Self-Portrait payoff, emitted once the portrait
    is `ready` (live since #396). Chosen rule-based from the user's top themes
    (self_portrait_summary.themes_from_answers → compute_matches); `why` is the
    LLM-authored line, the selection never is."""
    slug: str
    name: str
    portrait_url: str | None = None
    bio: str | None = None
    why: str | None = None


class ThemeScoreOut(BaseModel):
    """One curated radar axis (Phase B). `score` is the per-user max-normalized 0–1
    leaning (1.0 = the user's strongest axis), so the polygon fills the frame. ONLY the
    normalized score crosses the wire — raw counts are never surfaced (no-count rule)."""
    key: str       # stable axis key, e.g. "identity" (frozen octagon order)
    label: str     # display label, e.g. "Identity"
    score: float   # normalized leaning in [0, 1]


class SelfPortraitPortraitOut(BaseModel):
    """GET /preferences/self-portrait/portrait payload — the present-tense portrait.

    Breadth-aware: `state` is 'forming' until the user's answers span enough life
    areas, then 'ready'. The payload NEVER carries a count/%/fraction — only the
    state plus the surfaced content. `preview` carries the forming observation lines.
    `summary` (the cached Sonnet summary) and `best_fit` (1-2 personas) are emitted
    when `ready` and a generated portrait exists (live since #396); null/empty
    otherwise. `theme_scores` (the curated radar axes) is present in every state."""
    state: str  # "forming" | "ready"
    preview: list[str] = []        # forming-style observation lines (always usable)
    summary: str | None = None     # cached LLM summary (ready only)
    best_fit: list[BestFitOut] = []  # top 1-2 personas (ready only)
    theme_scores: list[ThemeScoreOut] = []  # B1: curated radar axes, fixed octagon order


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
    prediction: Optional[str] = Field(None, max_length=200)
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


class ScheduledEmailDetail(BaseModel):
    """A single DELIVERED future-self letter, for the in-app arrived-letter screen.
    Only ever built for status='sent' rows (the endpoint 404s otherwise), so the
    note is never exposed before delivery. `created_at` is the written date;
    `sent_at` is the arrived date. `prediction` (written at schedule time) and
    `review_text`/`review_at` (written on open) close the loop (043)."""
    id: str
    persona_id: str
    persona_name: str
    persona_portrait_url: str
    note: Optional[str]
    prediction: Optional[str]
    review_text: Optional[str]
    review_at: Optional[datetime]
    scheduled_for: datetime
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledEmailReviewIn(BaseModel):
    text: str = Field(..., max_length=2000)


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
    # Set only on the ring-true safety path (A18c). The mirror itself is returned
    # unchanged — pre-note state, because the note was rejected and never written
    # — so the client still receives a well-formed MirrorOut and these two fields
    # are what tell it the note did not land. Defaults keep every other response
    # and every other endpoint returning MirrorOut byte-compatible.
    safety_triggered: bool = False
    safety_message: str | None = None

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


# ── Counterview ───────────────────────────────────────────────────────────────

class CounterviewCreate(BaseModel):
    belief: str


class CounterviewDeeperRequest(BaseModel):
    persona_slug: str


class CounterviewRespondRequest(BaseModel):
    # A user rebuttal directed at the current speaker (persona_slug), who replies.
    persona_slug: str
    text: str


class CounterviewResponseOut(BaseModel):
    persona_slug: str
    persona_name: str
    persona_portrait_url: str | None = None
    position: int
    round: int
    verdict: str


class CounterviewTurnOut(BaseModel):
    # One rebuttal exchange. `persona_response` is null when status != 'generated'.
    sequence: int
    persona_slug: str
    persona_name: str
    persona_portrait_url: str | None = None
    user_text: str
    persona_response: str | None = None
    status: str


class CounterviewOut(BaseModel):
    id: str
    source: str
    anchor_text: str | None = None
    status: str
    still_stands: str | None = None
    # Terrain title (2-4 words) — the share card's heading, in place of anchor_text.
    title: str | None = None
    responses: list[CounterviewResponseOut]
    turns: list[CounterviewTurnOut] = []
    rebuttals_remaining: int = 0
    is_saved: bool = False


class CounterviewListItem(BaseModel):
    # Slim row for the revisit list — no responses; reopen pulls full via GET /{id}.
    id: str
    anchor_text: str | None = None
    created_at: datetime


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
    kind: str = "weekly"
    payload: dict | None = None
    read_at: datetime | None = None
    write_back_text: str | None = None
    write_back_at: datetime | None = None
    voice_persona_slug: str | None = None
    voice_persona_name: str | None = None

    class Config:
        from_attributes = True


class WriteBackIn(BaseModel):
    """A reader's short response to a letter. Overwrites any prior write-back."""
    text: str = Field(min_length=1, max_length=2000)


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


class SelfComparisonListItem(BaseModel):
    """One row of the revisit list (Γ-8). Slim on purpose, exactly as
    CounterviewListItem is: the list renders the question the person typed and a
    date, and reopening pulls the rest via GET /{id}. `prompt` is their own text,
    already bounded at 600 chars by SelfComparisonCreate."""
    id: str
    prompt: str
    created_at: datetime


class SelfComparisonQuoteOut(BaseModel):
    """An evidence quote from the stored closing. `date` stays a STRING and is not
    re-parsed to a datetime: the service wrote it with .isoformat() and the reader
    only formats it for display, so parsing here would add a failure mode
    (a legacy or malformed value) to a purely presentational field."""
    text: str
    date: str


class SelfComparisonSideOut(BaseModel):
    """One of the two selves as it was GENERATED. `start`/`end` come from the
    stored payload, never recomputed — the 'now' window moves with every new
    memory row, so recomputing would silently rewrite what the person was shown."""
    answer: str = ""
    start: Optional[str] = None
    end: Optional[str] = None


class SelfComparisonClosingOut(BaseModel):
    """The app-voice closing, read back verbatim from the payload.

    Every field is defaulted because this schema describes a HISTORICAL RECORD,
    not a fresh generation: rows written before the R1a beats existed carry no
    `hidden_continuity`/`sentence_owed` keys at all, and a strict model would 500
    on them. Same reasoning trajectory_snapshot states for its own payload — read
    it as data, not as an invariant.
    """
    observation: str = ""
    question: str = ""
    then_quote: Optional[SelfComparisonQuoteOut] = None
    now_quote: Optional[SelfComparisonQuoteOut] = None
    hidden_continuity: Optional[str] = None
    sentence_owed: Optional[str] = None


class SelfComparisonDetailOut(BaseModel):
    """GET /self-comparison/{id} — a past run, reopened (Γ-8).

    The payload has been written since 021 and read by nothing: Reflections pulls
    only `closing.sentence_owed`, and only for saved runs. This schema is the read
    path for the rest of it.

    `ring_true` is returned for the reason InsightOut returns its own: the
    surfaces are stateless and the row is the only memory of the answer, so a run
    already judged must render that instead of an empty row. `ring_true_note` is
    NOT returned — no surface collects or displays a note on this ritual, and a
    field with no reader is debt rather than a feature.

    `saved` reflects a live (non-soft-deleted) self_comparison_saves row, so the
    Save affordance on a reopened run shows its real state.
    """
    id: str
    prompt: str
    created_at: datetime
    then: SelfComparisonSideOut
    now: SelfComparisonSideOut
    closing: SelfComparisonClosingOut
    ring_true: Optional[str] = None
    ring_true_at: Optional[datetime] = None
    saved: bool = False


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


class ReflectionFeedCounterviewVerdict(BaseModel):
    """One persona's round-0 line within a saved Counterview."""
    persona_slug: str
    persona_name: str
    verdict: str
    position: int


class ReflectionFeedCounterview(BaseModel):
    """A saved Counterview — the anchor plus each persona's round-0 verdict."""
    kind: Literal["counterview_verdict"] = "counterview_verdict"
    save_id: str
    counterview_id: str
    source: str
    anchor_text: Optional[str] = None
    # Terrain title (2-4 words) — the share card's heading; None on old rows.
    title: Optional[str] = None
    verdicts: list[ReflectionFeedCounterviewVerdict]
    saved_at: datetime


class ReflectionFeedYvYSentence(BaseModel):
    """A saved You-vs-You "sentence you owe yourself" line, pulled from the run's
    payload["closing"]["sentence_owed"]."""
    kind: Literal["yvy_sentence"] = "yvy_sentence"
    save_id: str
    self_comparison_id: str
    sentence: str
    saved_at: datetime


class ReflectionFeedQuote(BaseModel):
    """A saved corpus quote — the quote text + its persona and citation. `source_short`
    is the compact card/share form; `source_locator` is the full citation. portrait may
    be empty ("") for a persona without one, so it's Optional to match the frontend."""
    kind: Literal["quote"] = "quote"
    saved_quote_id: str
    quote_id: str
    text_en: str
    persona_slug: str
    persona_name: str
    persona_portrait_url: Optional[str] = None
    source_short: str
    source_locator: str
    saved_at: datetime


class ReflectionFeedFutureSelfReview(BaseModel):
    """A reviewed future-self letter (043): the reader's "what happened" answer on a
    delivered letter, with the original prediction for card context. 1:1 with the
    scheduled_emails row (no saves table); `saved_at` is the review timestamp."""
    kind: Literal["future_self_review"] = "future_self_review"
    scheduled_email_id: str
    persona_id: str
    persona_name: str
    persona_portrait_url: Optional[str] = None
    prediction: Optional[str] = None
    review_text: str
    saved_at: datetime


ReflectionFeedItem = Annotated[
    Union[
        ReflectionFeedLine,
        ReflectionFeedMirror,
        ReflectionFeedCouncil,
        ReflectionFeedCounterview,
        ReflectionFeedYvYSentence,
        ReflectionFeedQuote,
        ReflectionFeedFutureSelfReview,
    ],
    Field(discriminator="kind"),
]


class ReflectionsFeedResponse(BaseModel):
    items: list[ReflectionFeedItem]


# ── Share snapshot (migration 067) ────────────────────────────────────────────

# The six artifact kinds a share can carry. Mirrors the CHECK on shares.artifact_type;
# a value here that the constraint rejects would fail at INSERT rather than at the
# edge, which is the wrong end to find it.
ShareArtifactType = Literal["line", "quote", "council", "mirror", "letter", "counterview"]


class ShareVoice(BaseModel):
    """One speaker in a multi-voice snapshot (council, counterview).

    Denormalised on purpose: persona_name is stored rather than resolved from
    persona_slug at read time, because the landing page must not query anything
    the share does not carry. A persona renamed or retired after the share was
    created still renders as it did when the person chose to share it.
    """
    persona_slug: str
    persona_name: str
    text: str


class ShareSnapshot(BaseModel):
    """The text of a shared artifact, frozen at share-creation time.

    WHY THIS IS A MODEL AND NOT A BARE DICT. The landing page reads this and
    nothing else — no artifact row, no persona row, no message row. A JSONB blob
    with no schema is exactly the thing that rots, and this one has to stay
    readable for as long as a link lives, which is indefinitely. Validated on
    write AND on read so a shape that drifts fails at the boundary rather than
    rendering as a blank card.

    `v` earns its place for the same reason. A v2 is then an explicit branch
    instead of a silent widening, and old rows keep rendering.

    FIVE OF THE SIX KINDS ARE ONE TEXT BLOCK PLUS ATTRIBUTION; council and
    counterview are multi-voice. So `headline` is always present and `voices` is
    present only where there is more than one speaker — rather than six shapes,
    or one shape with five nulls in it.
    """
    v: Literal[1] = 1
    artifact_type: ShareArtifactType
    # The primary text a reader sees. For multi-voice kinds this is the framing
    # line (the belief, the question put to the council), not a verdict.
    headline: str
    # Rendered above the artifact on the landing page. NOT the card's wording:
    # the card is first-person ("Marcus Aurelius told me") because the sharer is
    # the reader; here the reader is a stranger.
    attribution: str
    # Present for single-voice kinds. None for council/counterview, where the
    # speakers are in `voices` and the attribution is a fixed label.
    persona_slug: Optional[str] = None
    persona_name: Optional[str] = None
    # The ARTIFACT's own timestamp, not the share's. When a person saved the
    # line, not when they later decided to pass it on.
    occurred_at: Optional[datetime] = None
    voices: list[ShareVoice] = Field(default_factory=list)


class SharePublicResponse(BaseModel):
    """What GET /s/{public_id} returns. Unauthenticated.

    `snapshot` is None exactly when `revoked` is True — revocation withdraws the
    content, not merely the styling of the page. Returning the text alongside a
    `revoked: true` flag would leave the content one devtools tab away from
    anyone the sharer had just withdrawn it from.
    """
    artifact_type: ShareArtifactType
    revoked: bool
    snapshot: Optional[ShareSnapshot] = None


class ShareCreatedResponse(BaseModel):
    """Returned alongside the PNG's share link by the six creation endpoints."""
    share_id: str
    public_id: str
    url: str


class ShareListItem(BaseModel):
    """One row of "Your links".

    NO VIEW COUNT, AND THE ABSENCE IS A RULING RATHER THAN AN OVERSIGHT. v1
    shows the sharer nothing about who opened a link. The list exists so that
    revocation is reachable — without it "Turn off this link" has nowhere to
    live and the withdrawn page is a screen no one can cause.

    `revoked` rather than `revoked_at`: the row is shown muted and actionless,
    and the exact second someone withdrew a link is not a thing this screen has
    a use for.
    """
    public_id: str
    url: str
    artifact_type: ShareArtifactType
    created_at: datetime
    revoked: bool


class ShareListResponse(BaseModel):
    items: list[ShareListItem]
