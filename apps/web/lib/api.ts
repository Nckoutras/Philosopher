const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://philosopher-api-z9l9.onrender.com/api/v1'

// ── SSE event types ───────────────────────────────────────────────────────────

export type SSEEventStart = { type: 'start'; brought_in?: boolean; persona_slug?: string; persona_name?: string }
export type SSEEventChunk = { type: 'chunk'; data: string }
// message_id is absent in pre-generation safety path (Pattern B)
export type SSEEventDone = { type: 'done'; message_id?: string; case_id?: string; session_id?: string }
export type SSEEventSafety = { type: 'safety'; level: string }
export type SSEEventSafetyOverride = { type: 'safety_override'; level: string }
export type SSEEventError = { type: 'error'; error_code: 'llm_unavailable'; persona_voice: string }
export type SSEEventCorrection = { type: 'correction' }
export type SSEEventLimit = { type: 'limit'; scope: 'turn' | 'thread'; tier: 'free' | 'pro' | 'premium' }

// ── Council SSE event types ───────────────────────────────────────────────────
export type SSEEventConvening = { type: 'convening' }
export type SSEEventMember = { type: 'member'; slug: string; name: string; position: number }
export type SSEEventSynthesisStart = { type: 'synthesis_start' }
export type SSEEventSynthesisError = { type: 'synthesis_error' }
// Structured council synthesis (decision instrument). real_question / tension /
// next_move may be null (grounded-or-null); verdict is always present when emitted.
export type SSEEventSynthesis = {
  type: 'synthesis'
  real_question: string | null
  tension: string | null
  verdict: string
  next_move: string | null
}

export type SSEEvent =
  | SSEEventStart
  | SSEEventChunk
  | SSEEventDone
  | SSEEventSafety
  | SSEEventSafetyOverride
  | SSEEventError
  | SSEEventCorrection
  | SSEEventLimit
  | SSEEventConvening
  | SSEEventMember
  | SSEEventSynthesisStart
  | SSEEventSynthesisError
  | SSEEventSynthesis

// ── 429 response body (LLMErrorResponse from backend) ────────────────────────

export interface LLMErrorResponse {
  error_code: string
  persona_voice: string
}

// ── RateLimitError ────────────────────────────────────────────────────────────

export class RateLimitError extends Error {
  resetAt: Date
  limit: number
  remaining: number
  errorCode: string
  personaVoice?: string
  upgradeTarget: 'pro' | 'premium'

  constructor(opts: {
    resetAt: Date
    limit: number
    remaining: number
    errorCode: string
    personaVoice?: string
    upgradeTarget: 'pro' | 'premium'
  }) {
    super('RATE_LIMIT')
    this.name = 'RateLimitError'
    this.resetAt = opts.resetAt
    this.limit = opts.limit
    this.remaining = opts.remaining
    this.errorCode = opts.errorCode
    this.personaVoice = opts.personaVoice
    this.upgradeTarget = opts.upgradeTarget
  }
}

// ── Saved-line error classes ──────────────────────────────────────────────────

export class SaveLimitError extends Error {
  limit: number
  currentCount: number
  constructor(opts: { limit: number; currentCount: number }) {
    super('SAVE_LIMIT')
    this.name = 'SaveLimitError'
    this.limit = opts.limit
    this.currentCount = opts.currentCount
  }
}

export class DuplicateSaveError extends Error {
  constructor() {
    super('DUPLICATE_SAVE')
    this.name = 'DuplicateSaveError'
  }
}

export class ShareLimitError extends Error {
  constructor() {
    super('SHARE_LIMIT')
    this.name = 'ShareLimitError'
  }
}

export class ConversationNotFoundError extends Error {
  constructor() {
    super('CONVERSATION_NOT_FOUND')
    this.name = 'ConversationNotFoundError'
  }
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  full_name: string | null
  avatar_url: string | null
  is_admin: boolean
  onboarded_at: string | null
  created_at: string
  needs_disclaimer?: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Persona {
  id: string
  slug: string
  name: string
  era: string | null
  tradition: string | null
  tier: 'free' | 'pro' | 'premium'
  tagline: string | null
  avatar_emoji: string | null
  opening_invocation: string | null
  bio: string
  portrait_url: string
  is_accessible: boolean
}

export interface Conversation {
  id: string
  // `persona` is the coalesced ACTIVE mind (sticky guest when set, else home).
  persona: Persona
  title: string | null
  message_count: number
  last_message_at: string | null
  created_at: string
  source_persona_slug: string | null
  source_context_content: string | null
  last_message_snippet: string | null
  // Always the immutable home/origin persona. Stickied iff persona.slug differs.
  origin_persona_slug: string | null
  origin_persona_name: string | null
  // Pro sticky deep mode: when true (and the user is Pro), every reply is deep.
  deep_mode: boolean
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  safety_level: string
  persona_override: boolean
  created_at: string
  persona_slug?: string | null
  persona_name?: string | null
}

export interface MemoryEntry {
  id: string
  entry_type: string
  content: string
  confidence: number
  is_active: boolean
  created_at: string
}

export interface Insight {
  id: string
  content: string
  insight_type: string | null
  source_count?: number | null
  conversation_id: string | null
  is_dismissed: boolean
  created_at: string
}

export interface Subscription {
  plan: string
  status: string
  current_period_end: string | null
  cancel_at_period_end: boolean
}

export interface DisclaimerCurrent {
  version_string: string
  age_copy: string
  positioning_copy: string
}

export interface DisclaimerAcceptRequest {
  confirmed_age_18: boolean
  confirmed_non_therapy: boolean
  locale?: string
}

export interface DisclaimerAcceptResponse {
  accepted_at: string
  version_string: string
}

export interface SavedLineOut {
  id: string
  user_id: string
  message_id: string
  persona_id: string
  source_type: string
  saved_at: string
}

export interface SavedLineRead {
  id: string
  message_id: string
  persona_id: string
  persona_slug: string
  persona_display_name: string
  message_content: string
  conversation_id: string
  saved_at: string
  source_type: string
}

export interface SavedLineListResponse {
  items: SavedLineRead[]
  total_count: number
  free_tier_limit: number | null
}

// ── Reflections feed (unified saved lines + mirror/council verdicts) ──────────

export interface ReflectionFeedLine extends SavedLineRead {
  kind: 'line'
}

export interface ReflectionFeedMirror {
  kind: 'mirror_verdict'
  save_id: string
  mirror_id: string
  thread: string
  host_persona_slug: string | null
  host_persona_name: string | null
  mirror_kind: string // 'weekly' | 'preview'
  saved_at: string
}

export interface ReflectionFeedCouncil {
  kind: 'council_verdict'
  save_id: string
  session_id: string
  synthesis: string
  persona_slugs: string[]
  created_at: string
  saved_at: string
}

export interface ReflectionFeedCounterviewVerdict {
  persona_slug: string
  persona_name: string
  verdict: string
  position: number
}

export interface ReflectionFeedCounterview {
  kind: 'counterview_verdict'
  save_id: string
  counterview_id: string
  source: string
  anchor_text: string | null
  verdicts: ReflectionFeedCounterviewVerdict[]
  saved_at: string
}

export interface ReflectionFeedYvYSentence {
  kind: 'yvy_sentence'
  save_id: string
  self_comparison_id: string
  sentence: string
  saved_at: string
}

export type ReflectionFeedItem =
  | ReflectionFeedLine
  | ReflectionFeedMirror
  | ReflectionFeedCouncil
  | ReflectionFeedCounterview
  | ReflectionFeedYvYSentence

export interface ReflectionsFeedResponse {
  items: ReflectionFeedItem[]
}

export interface DailyQuestion {
  id: string
  question_text: string
}

export interface LastConversation {
  conversation_id: string
  persona_id: string
  persona_slug: string
  persona_name: string
  persona_tagline: string | null
  persona_portrait_url: string
  last_message_snippet: string | null
  updated_at: string
}

export interface RecentSavedLine {
  saved_line_id: string
  content: string
  persona_id: string
  persona_slug: string
  persona_name: string
  persona_portrait_url: string
  conversation_id: string
  saved_at: string
}

export interface ScheduledEmailCreate {
  saved_line_id: string
  note?: string
  scheduled_for: string
}

export interface ScheduledEmailOut {
  id: string
  saved_line_id: string | null
  persona_id: string
  note: string | null
  recipient_email: string
  scheduled_for: string
  status: string
  sent_at: string | null
  created_at: string
}

export interface ScheduledEmailListItem {
  id: string
  persona_id: string
  persona_name: string
  persona_portrait_url: string | null
  scheduled_for: string
  status: string
  sent_at: string | null
  created_at: string
}

export interface MirrorMoment {
  said: string
  meant: string
}

export interface MirrorLineThatMoved {
  earlier: { label: string; quote: string }
  later: { label: string; quote: string }
  read: string
}

export interface MirrorPayload {
  thread: string | null
  moments: MirrorMoment[] | null
  line_that_moved: MirrorLineThatMoved | null
  question: string | null
}

export interface Mirror {
  id: string
  kind: string
  status: string
  period_start: string
  period_end: string
  host_persona_slug: string | null
  host_persona_name: string | null
  payload: MirrorPayload | null
  ring_true: 'yes' | 'partly' | 'no' | null
  ring_true_note: string | null
  created_at: string
}

export interface MirrorHost {
  slug: string
  name: string
  portrait_url: string | null
}

// ── Counterview ───────────────────────────────────────────────────────────────

export interface CounterviewResponse {
  persona_slug: string
  persona_name: string
  persona_portrait_url: string | null
  position: number
  round: number
  verdict: string
}

export interface CounterviewTurn {
  sequence: number
  persona_slug: string
  persona_name: string
  persona_portrait_url: string | null
  user_text: string
  persona_response: string | null
  status: 'generated' | 'empty' | 'suppressed'
}

export interface Counterview {
  id: string
  source: string
  anchor_text: string | null
  status: 'generated' | 'empty' | 'suppressed'
  still_stands: string | null
  responses: CounterviewResponse[]
  turns: CounterviewTurn[]
  rebuttals_remaining: number
  is_saved: boolean
}

export interface CounterviewListItem {
  id: string
  anchor_text: string | null
  created_at: string
}

export interface WeeklyLetterPayload {
  title: string | null
  opening: string | null
  references: string | null
  // "What went unspoken" — the occasional avoidance line. Weekly letters only,
  // grounded-or-null; absent on old letters and on the monthly season finale.
  avoidance?: string | null
  pull_quote: string | null
  forward_gesture: string | null
  practical_takeaway: string | null
  suggested_persona_slug: string | null
}

export interface WeeklyLetter {
  id: string
  period_start: string
  period_end: string
  status: 'generated' | 'empty' | 'suppressed'
  kind?: string
  payload: WeeklyLetterPayload | null
  read_at: string | null
  write_back_text: string | null
  write_back_at: string | null
  voice_persona_slug: string | null
  voice_persona_name: string | null
}

export interface SelfComparisonWindow {
  start: string
  end: string
  by_type: Record<string, string[]>
}

export interface SelfComparisonStatus {
  unlocked: boolean
  total_signals: number
  reason: string | null
  forming_preview: string[]
  then: SelfComparisonWindow | null
  now: SelfComparisonWindow | null
  weekly_remaining: number | null
  weekly_limit: number | null
  plan: string | null
}

// ── Client ────────────────────────────────────────────────────────────────────

class ApiClient {
  private token: string | null = null

  setToken(token: string | null) {
    this.token = token
    if (typeof window !== 'undefined') {
      token ? localStorage.setItem('ph_token', token) : localStorage.removeItem('ph_token')
      // Also set cookie for middleware route protection
      if (token) {
        document.cookie = `ph_token=${token}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`
      } else {
        document.cookie = 'ph_token=; path=/; max-age=0'
      }
    }
  }

  loadToken() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('ph_token')
    }
  }

  async request<T>(
    path: string,
    options: RequestInit = {},
    rawBody = false,
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...(rawBody ? {} : { 'Content-Type': 'application/json' }),
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      ...(options.headers as Record<string, string> ?? {}),
    }

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }))
      let message: string
      if (Array.isArray(error.detail)) {
        message = error.detail
          .map((e: { loc?: (string | number)[]; msg?: string }) => {
            const field = Array.isArray(e.loc) && e.loc.length > 1
              ? e.loc.slice(1).join('.')
              : ''
            return field ? `${field}: ${e.msg}` : (e.msg ?? 'Invalid input')
          })
          .join('; ')
      } else if (typeof error.detail === 'string') {
        message = error.detail
      } else {
        message = 'Request failed'
      }
      throw new Error(message)
    }
    if (res.status === 204) return null as T
    return res.json()
  }

  // ── Auth ──────────────────────────────────────────────────────────────────

  async register(email: string, password: string, full_name?: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    })
    this.setToken(data.access_token)
    return data
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    this.setToken(data.access_token)
    return data
  }

  async me(): Promise<User> {
    return this.request<User>('/auth/me')
  }

  async updateMe(fullName: string): Promise<User> {
    return this.request<User>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify({ full_name: fullName }),
    })
  }

  async requestOtp(email: string): Promise<void> {
    await this.request<void>('/auth/otp/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
  }

  async verifyOtp(email: string, code: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/otp/verify', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    })
    this.setToken(data.access_token)
    return data
  }

  // ── Disclaimer ────────────────────────────────────────────────────────────

  async getDisclaimerCurrent(): Promise<DisclaimerCurrent> {
    return this.request<DisclaimerCurrent>('/disclaimer/current')
  }

  async acceptDisclaimer(body: DisclaimerAcceptRequest): Promise<DisclaimerAcceptResponse> {
    return this.request<DisclaimerAcceptResponse>('/disclaimer/accept', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }

  // ── Preferences ────────────────────────────────────────────────────────────

  async upsertPreferences(payload: PreferenceUpsertRequest): Promise<PreferenceOut> {
    return this.request<PreferenceOut>('/preferences', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async getMatches(): Promise<Match[]> {
    return this.request<Match[]>('/preferences/matches', {
      method: 'GET',
    })
  }

  async getPreferences(): Promise<PreferenceOut> {
    return this.request<PreferenceOut>('/preferences', { method: 'GET' })
  }

  async saveProfile(payload: ProfilePayload): Promise<PreferenceOut> {
    return this.request<PreferenceOut>('/preferences/profile', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  }

  async getProfileReflection(): Promise<ProfileReflectionOut> {
    return this.request<ProfileReflectionOut>('/preferences/profile/reflection', {
      method: 'POST',
    })
  }

  // ── Self-Portrait ───────────────────────────────────────────────────────────

  async getSelfPortrait(): Promise<SelfPortraitData> {
    return this.request<SelfPortraitData>('/preferences/self-portrait', { method: 'GET' })
  }

  async getSelfPortraitPortrait(): Promise<SelfPortraitPortrait> {
    return this.request<SelfPortraitPortrait>('/preferences/self-portrait/portrait', { method: 'GET' })
  }

  async updateSelfPortrait(questionId: string, pillIndex: number): Promise<PreferenceOut> {
    return this.request<PreferenceOut>('/preferences/self-portrait', {
      method: 'PATCH',
      body: JSON.stringify({ question_id: questionId, pill_index: pillIndex }),
    })
  }

  async getSelfComparisonStatus(): Promise<SelfComparisonStatus> {
    return this.request<SelfComparisonStatus>('/self-comparison/status')
  }

  async setSelfComparisonRingTrue(comparisonId: string, ringTrue: string, note?: string): Promise<void> {
    return this.request(`/self-comparison/${comparisonId}/ring-true`, {
      method: 'PATCH',
      body: JSON.stringify({ ring_true: ringTrue, ...(note ? { note } : {}) }),
    })
  }

  // ── Personas ──────────────────────────────────────────────────────────────

  async getPersonas(): Promise<Persona[]> {
    return this.request<Persona[]>('/personas')
  }

  // ── Conversations ─────────────────────────────────────────────────────────

  async getConversations(): Promise<Conversation[]> {
    return this.request<Conversation[]>('/conversations')
  }

  async getConversation(id: string): Promise<Conversation> {
    // Bespoke fetch (not request()) so a deleted/missing conversation surfaces as
    // a typed 404 the chat route can handle gracefully, rather than a generic Error.
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
    })
    if (res.status === 404) throw new ConversationNotFoundError()
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(typeof error.detail === 'string' ? error.detail : 'Request failed')
    }
    return res.json()
  }

  // Sticky guest mind: make `personaSlug` the active mind for subsequent turns.
  async setActiveMind(conversationId: string, personaSlug: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${conversationId}/active-mind`, {
      method: 'POST',
      body: JSON.stringify({ target_persona_slug: personaSlug }),
    })
  }

  // Return to origin: clear the sticky active mind back to the home persona.
  async clearActiveMind(conversationId: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${conversationId}/active-mind`, {
      method: 'DELETE',
    })
  }

  // Pro sticky deep mode: turn ON (Pro/premium only; 403 for free) / OFF.
  async setDeepMode(conversationId: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${conversationId}/deep-mode`, {
      method: 'POST',
    })
  }

  async clearDeepMode(conversationId: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${conversationId}/deep-mode`, {
      method: 'DELETE',
    })
  }

  async createConversation(persona_slug: string, ritual_id?: string, skip_opening?: boolean): Promise<Conversation> {
    return this.request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ persona_slug, ritual_id, skip_opening }),
    })
  }

  async getMessages(conversationId: string): Promise<Message[]> {
    return this.request<Message[]>(`/conversations/${conversationId}/messages`)
  }

  async deleteConversation(id: string): Promise<void> {
    return this.request(`/conversations/${id}`, { method: 'DELETE' })
  }

  async createCrossPersonaConversation(savedLineId: string, targetPersonaSlug: string): Promise<Conversation> {
    return this.request<Conversation>('/conversations/cross-persona', {
      method: 'POST',
      body: JSON.stringify({ saved_line_id: savedLineId, target_persona_slug: targetPersonaSlug }),
    })
  }

  async createReadingRevisit(letterId: string, targetPersonaSlug: string): Promise<Conversation> {
    return this.request<Conversation>('/conversations/reading-revisit', {
      method: 'POST',
      body: JSON.stringify({ weekly_letter_id: letterId, target_persona_slug: targetPersonaSlug }),
    })
  }

  async createShareScreenshot(savedLineId: string, annotation?: string): Promise<Blob> {
    const body: Record<string, string> = { saved_line_id: savedLineId }
    if (annotation) body.annotation = annotation

    const res = await fetch(`${API_BASE}/share/screenshot`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      if (res.status === 429) throw new ShareLimitError()
      throw new Error(`Screenshot failed: ${res.status}`)
    }
    return res.blob()
  }

  // SSE stream — returns the raw Response for manual reading.
  // userPlan is used to determine upgradeTarget on 429 ('free' → 'pro', 'pro' → 'premium').
  async streamMessage(conversationId: string, content: string, userPlan: string = 'free', seededOpening: boolean = false, signal?: AbortSignal): Promise<Response> {
    const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ content, seeded_opening: seededOpening }),
      signal,
    })
    if (!res.ok) {
      if (res.status === 429) {
        const body = await res.json().catch(() => ({} as LLMErrorResponse))
        const limit = parseInt(res.headers.get('X-RateLimit-Limit') ?? '0', 10)
        const remaining = parseInt(res.headers.get('X-RateLimit-Remaining') ?? '0', 10)
        const resetHeader = res.headers.get('X-RateLimit-Reset') ?? new Date().toISOString()
        throw new RateLimitError({
          resetAt: new Date(resetHeader),
          limit,
          remaining,
          errorCode: body.error_code ?? 'rate_limited',
          personaVoice: body.persona_voice,
          upgradeTarget: userPlan === 'pro' ? 'premium' : 'pro',
        })
      }
      throw new Error('Stream failed')
    }
    return res
  }

  async streamAnotherMind(conversationId: string, personaSlug: string, userPlan: string = 'free', signal?: AbortSignal): Promise<Response> {
    const res = await fetch(`${API_BASE}/conversations/${conversationId}/another-mind`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ target_persona_slug: personaSlug }),
      signal,
    })
    if (!res.ok) {
      if (res.status === 403) {
        throw new Error('upgrade_required')
      }
      if (res.status === 429) {
        const body = await res.json().catch(() => ({} as LLMErrorResponse))
        const limit = parseInt(res.headers.get('X-RateLimit-Limit') ?? '0', 10)
        const remaining = parseInt(res.headers.get('X-RateLimit-Remaining') ?? '0', 10)
        const resetHeader = res.headers.get('X-RateLimit-Reset') ?? new Date().toISOString()
        throw new RateLimitError({
          resetAt: new Date(resetHeader),
          limit,
          remaining,
          errorCode: body.error_code ?? 'rate_limited',
          personaVoice: body.persona_voice,
          upgradeTarget: userPlan === 'pro' ? 'premium' : 'pro',
        })
      }
      throw new Error('Stream failed')
    }
    return res
  }

  async streamGoDeeper(conversationId: string, userPlan: string = 'free', signal?: AbortSignal): Promise<Response> {
    const res = await fetch(`${API_BASE}/conversations/${conversationId}/go-deeper`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({}),
      signal,
    })
    if (!res.ok) {
      if (res.status === 403) {
        throw new Error('upgrade_required')
      }
      if (res.status === 429) {
        const body = await res.json().catch(() => ({} as LLMErrorResponse))
        const limit = parseInt(res.headers.get('X-RateLimit-Limit') ?? '0', 10)
        const remaining = parseInt(res.headers.get('X-RateLimit-Remaining') ?? '0', 10)
        const resetHeader = res.headers.get('X-RateLimit-Reset') ?? new Date().toISOString()
        throw new RateLimitError({
          resetAt: new Date(resetHeader),
          limit,
          remaining,
          errorCode: body.error_code ?? 'rate_limited',
          personaVoice: body.persona_voice,
          upgradeTarget: userPlan === 'pro' ? 'premium' : 'pro',
        })
      }
      throw new Error('Stream failed')
    }
    return res
  }

  async streamCouncil(body: { matter: string; source?: string; mirror_id?: string | null; conversation_id?: string | null }): Promise<Response> {
    const res = await fetch(`${API_BASE}/council`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      if (res.status === 429) {
        const b = await res.json().catch(() => ({} as LLMErrorResponse))
        const limit = parseInt(res.headers.get('X-RateLimit-Limit') ?? '0', 10)
        const remaining = parseInt(res.headers.get('X-RateLimit-Remaining') ?? '0', 10)
        const resetHeader = res.headers.get('X-RateLimit-Reset') ?? new Date().toISOString()
        throw new RateLimitError({
          resetAt: new Date(resetHeader),
          limit,
          remaining,
          errorCode: b.error_code ?? 'rate_limited',
          personaVoice: b.persona_voice,
          upgradeTarget: 'pro',
        })
      }
      throw new Error('Council stream failed')
    }
    return res
  }

  async streamSelfComparison(body: { prompt: string }): Promise<Response> {
    const res = await fetch(`${API_BASE}/self-comparison`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      if (res.status === 429) {
        const b = await res.json().catch(() => ({} as LLMErrorResponse))
        const limit = parseInt(res.headers.get('X-RateLimit-Limit') ?? '0', 10)
        const remaining = parseInt(res.headers.get('X-RateLimit-Remaining') ?? '0', 10)
        const resetHeader = res.headers.get('X-RateLimit-Reset') ?? new Date().toISOString()
        throw new RateLimitError({
          resetAt: new Date(resetHeader), limit, remaining,
          errorCode: b.error_code ?? 'rate_limited', personaVoice: b.persona_voice, upgradeTarget: 'pro',
        })
      }
      throw new Error('Self-comparison stream failed')
    }
    return res
  }

  async saveCouncil(sessionId: string): Promise<void> {
    return this.request(`/council/${sessionId}/save`, { method: 'POST' })
  }

  async unsaveCouncil(sessionId: string): Promise<void> {
    return this.request(`/council/${sessionId}/save`, { method: 'DELETE' })
  }

  async saveCounterview(id: string): Promise<void> {
    return this.request(`/counterview/${id}/save`, { method: 'POST' })
  }

  async unsaveCounterview(id: string): Promise<void> {
    return this.request(`/counterview/${id}/save`, { method: 'DELETE' })
  }

  async saveSelfComparison(id: string): Promise<void> {
    return this.request(`/self-comparison/${id}/save`, { method: 'POST' })
  }

  async unsaveSelfComparison(id: string): Promise<void> {
    return this.request(`/self-comparison/${id}/save`, { method: 'DELETE' })
  }

  async saveMirror(mirrorId: string): Promise<void> {
    return this.request(`/mirrors/${mirrorId}/save`, { method: 'POST' })
  }

  async unsaveMirror(mirrorId: string): Promise<void> {
    return this.request(`/mirrors/${mirrorId}/save`, { method: 'DELETE' })
  }

  async shareCouncil(sessionId: string, annotation?: string): Promise<Blob> {
    const body: Record<string, string> = {}
    if (annotation) body.annotation = annotation

    const res = await fetch(`${API_BASE}/council/${sessionId}/share`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      if (res.status === 429) throw new ShareLimitError()
      throw new Error(`Council share failed: ${res.status}`)
    }
    return res.blob()
  }

  async shareCounterview(id: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/share/counterview`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ counterview_id: id }),
    })
    if (!res.ok) {
      if (res.status === 429) throw new ShareLimitError()
      throw new Error(`Counterview share failed: ${res.status}`)
    }
    return res.blob()
  }

  async shareMirror(mirrorId: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/mirrors/${mirrorId}/share`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({}),
    })
    if (!res.ok) {
      if (res.status === 429) throw new ShareLimitError()
      throw new Error(`Mirror share failed: ${res.status}`)
    }
    return res.blob()
  }

  async shareWeeklyLetter(letterId: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/weekly-letters/${letterId}/share`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({}),
    })
    if (!res.ok) {
      if (res.status === 429) throw new ShareLimitError()
      throw new Error(`Letter share failed: ${res.status}`)
    }
    return res.blob()
  }

  // ── Memory ────────────────────────────────────────────────────────────────

  async getMemory(): Promise<MemoryEntry[]> {
    return this.request<MemoryEntry[]>('/memory')
  }

  async deleteMemory(id: string): Promise<void> {
    return this.request(`/memory/${id}`, { method: 'DELETE' })
  }

  // ── Insights ──────────────────────────────────────────────────────────────

  async getInsights(conversationId?: string): Promise<Insight[]> {
    const qs = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : ''
    return this.request<Insight[]>(`/insights${qs}`)
  }

  async dismissInsight(id: string): Promise<void> {
    return this.request(`/insights/${id}/dismiss`, { method: 'PATCH' })
  }

  // Generate (or return the existing) insight-seeded mirror for this insight.
  // Synchronous on the server — the POST takes a few seconds. status may be
  // 'empty'/'suppressed' (null payload), which the reader handles gracefully.
  async reflectInsight(id: string): Promise<Mirror> {
    return this.request<Mirror>(`/insights/${id}/reflect`, { method: 'POST' })
  }

  // ── Counterview ─────────────────────────────────────────────────────────────

  // Generate (or return the existing) insight-seeded counterview for this insight.
  // Synchronous on the server — the POST takes a few seconds. status may be
  // 'empty'/'suppressed' (no responses), which the reader handles gracefully.
  async counterviewFromInsight(id: string): Promise<Counterview> {
    return this.request<Counterview>(`/insights/${id}/counterview`, { method: 'POST' })
  }

  async getCounterview(id: string): Promise<Counterview> {
    return this.request<Counterview>(`/counterview/${id}`)
  }

  // Slim, most-recent-first list of the user's generated counterviews (revisit list).
  async listCounterviews(): Promise<CounterviewListItem[]> {
    return this.request<CounterviewListItem[]>('/counterview')
  }

  // Voluntary path: generate a counterview against a belief the user types.
  // Synchronous on the server — status may be 'empty'/'suppressed' (no responses).
  async createCounterview(belief: string): Promise<Counterview> {
    return this.request<Counterview>('/counterview', {
      method: 'POST',
      body: JSON.stringify({ belief }),
    })
  }

  // Press one layer deeper for a single persona. Returns the full counterview,
  // now carrying that persona's round-1 response (a no-op — cap reached, nothing
  // to add, safety trip — returns it unchanged with a clean 200).
  async deeperCounterview(counterviewId: string, personaSlug: string): Promise<Counterview> {
    return this.request<Counterview>(`/counterview/${counterviewId}/deeper`, {
      method: 'POST',
      body: JSON.stringify({ persona_slug: personaSlug }),
    })
  }

  // Send a rebuttal directed at the current speaker; that persona replies in one
  // tight line. Returns the full counterview with the new turn in `turns[]` and the
  // updated `rebuttals_remaining`. Throws on 409 once the rebuttal cap is reached.
  async respondCounterview(
    counterviewId: string,
    personaSlug: string,
    text: string,
  ): Promise<Counterview> {
    return this.request<Counterview>(`/counterview/${counterviewId}/respond`, {
      method: 'POST',
      body: JSON.stringify({ persona_slug: personaSlug, text }),
    })
  }

  // ── Billing ───────────────────────────────────────────────────────────────

  async getSubscription(): Promise<Subscription> {
    return this.request<Subscription>('/billing/subscription')
  }

  async createCheckout(plan: string, interval: 'monthly' | 'yearly' = 'monthly'): Promise<{ checkout_url: string }> {
    return this.request('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan, interval }),
    })
  }

  async getPortalUrl(): Promise<{ portal_url: string }> {
    return this.request('/billing/portal', { method: 'POST' })
  }

  // ── Saved lines ───────────────────────────────────────────────────────────

  async createSavedLine(messageId: string): Promise<SavedLineOut> {
    const res = await fetch(`${API_BASE}/saved-lines`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ message_id: messageId }),
    })
    if (res.status === 409) throw new DuplicateSaveError()
    if (res.status === 402) {
      const body = await res.json().catch(() => ({ limit: 3, current_count: 3 }))
      throw new SaveLimitError({ limit: body.limit, currentCount: body.current_count })
    }
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(error.detail ?? 'Request failed')
    }
    return res.json()
  }

  async listSavedLines(): Promise<SavedLineListResponse> {
    return this.request<SavedLineListResponse>('/saved-lines')
  }

  async getReflectionsFeed(): Promise<ReflectionsFeedResponse> {
    return this.request<ReflectionsFeedResponse>('/reflections/feed')
  }

  async deleteSavedLine(savedLineId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/saved-lines/${savedLineId}`, {
      method: 'DELETE',
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
    })
    if (res.status === 404) return
    if (!res.ok) throw new Error('Delete failed')
  }

  // ── Scheduled emails ─────────────────────────────────────────────────────────

  async createScheduledEmail(body: ScheduledEmailCreate): Promise<ScheduledEmailOut> {
    return this.request<ScheduledEmailOut>('/scheduled-emails', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }

  async listScheduledEmails(status?: string): Promise<ScheduledEmailListItem[]> {
    const qs = status ? `?status=${encodeURIComponent(status)}` : ''
    return this.request<ScheduledEmailListItem[]>(`/scheduled-emails${qs}`)
  }

  async cancelScheduledEmail(emailId: string): Promise<void> {
    return this.request(`/scheduled-emails/${emailId}`, { method: 'DELETE' })
  }

  // ── Home / Today ─────────────────────────────────────────────────────────────

  async getTodayQuestion(): Promise<DailyQuestion> {
    return this.request<DailyQuestion>('/today/question')
  }

  async getLastConversation(): Promise<LastConversation | null> {
    return this.request<LastConversation | null>('/me/last-conversation')
  }

  async getRecentSavedLine(): Promise<RecentSavedLine | null> {
    return this.request<RecentSavedLine | null>('/me/recent-saved-line')
  }

  // ── Mirrors ───────────────────────────────────────────────────────────────

  async getLatestMirror(): Promise<Mirror | null> {
    return this.request<Mirror | null>('/mirrors/latest')
  }

  async setRingTrue(id: string, ringTrue: 'yes' | 'partly' | 'no', note?: string): Promise<Mirror> {
    return this.request<Mirror>(`/mirrors/${id}/ring-true`, {
      method: 'POST',
      body: JSON.stringify({ ring_true: ringTrue, note: note ?? null }),
    })
  }

  async getMirrorHosts(): Promise<{ hosts: MirrorHost[]; selected: string | null; default: string }> {
    return this.request('/mirrors/hosts')
  }

  async setMirrorHost(host_slug: string): Promise<{ host_slug: string }> {
    return this.request('/mirrors/host', {
      method: 'POST',
      body: JSON.stringify({ host_slug }),
    })
  }

  // ── Weekly Letters ─────────────────────────────────────────────────────────

  async getWeeklyLetters(): Promise<WeeklyLetter[]> {
    return this.request<WeeklyLetter[]>('/weekly-letters')
  }

  async getWeeklyLetter(id: string): Promise<WeeklyLetter> {
    return this.request<WeeklyLetter>(`/weekly-letters/${id}`)
  }

  async deleteWeeklyLetter(id: string): Promise<void> {
    await this.request(`/weekly-letters/${id}`, { method: 'DELETE' })
  }

  async writeBackToLetter(id: string, text: string): Promise<WeeklyLetter> {
    return this.request<WeeklyLetter>(`/weekly-letters/${id}/write-back`, {
      method: 'PATCH',
      body: JSON.stringify({ text }),
    })
  }
}

export const api = new ApiClient()

// Load token from localStorage on module init (client-side only)
if (typeof window !== 'undefined') {
  api.loadToken()
}

// ── Preferences ───────────────────────────────────────────────────────────────

export interface PreferenceUpsertRequest {
  themes: string[]
  other_text: string | null
  need_most: 'comfort' | 'challenge' | 'interpretation' | 'practical_steadiness'
}

export type ProfileValue =
  | 'honesty' | 'freedom' | 'loyalty' | 'justice'
  | 'growth' | 'security' | 'connection' | 'achievement'

export type DisagreementStyle =
  | 'stand_firm' | 'seek_the_middle' | 'avoid_conflict'
  | 'probe_their_view' | 'heat_then_reflect'

export interface ProfilePayload {
  values: ProfileValue[]
  disagreement_style: DisagreementStyle | null
}

export interface PreferenceOut {
  user_id: string
  themes: string[]
  other_text: string | null
  need_most: string
  profile: ProfilePayload | null
  created_at: string
  updated_at: string
}

export interface ProfileReflectionOut {
  bullets: string[]
}

export interface SelfPortraitQuestion {
  id: string
  category: string
  question: string
  pills: string[]
}

export interface SelfPortraitData {
  questions: SelfPortraitQuestion[]
  answers: Record<string, number>
  is_pro: boolean
  locked_count: number
}

// One best-fit persona for the portrait payoff. Populated in 5b; the fields are
// reserved here so the type is stable.
export interface SelfPortraitBestFit {
  slug: string
  name: string
  portrait_url: string | null
  bio: string | null
  why: string | null
}

// One curated radar axis (Phase B). `score` is the per-user max-normalized 0–1
// leaning (1.0 = the user's strongest axis). Only the normalized score crosses the
// wire — never a raw count. Axes arrive in a fixed octagon order.
export interface SelfPortraitThemeScore {
  key: string
  label: string
  score: number
}

// GET /preferences/self-portrait/portrait. Breadth-aware: `state` flips to "ready"
// once answers span enough life areas. NEVER carries a count/%/fraction. In 5a only
// `state` + `preview` are populated; `summary`/`best_fit` arrive in 5b; `theme_scores`
// (the curated radar axes) arrives in B1 and is `[]` for backward-compat.
export interface SelfPortraitPortrait {
  state: 'forming' | 'ready'
  preview: string[]
  summary: string | null
  best_fit: SelfPortraitBestFit[]
  // Optional: genuinely absent during the backend-before-frontend deploy window.
  // Both call sites guard with `?? []`.
  theme_scores?: SelfPortraitThemeScore[]
}

export interface Match {
  slug: string
  score: number
  reason: string
}

