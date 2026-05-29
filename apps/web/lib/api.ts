const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://philosopher-api-z9l9.onrender.com/api/v1'

// ── SSE event types ───────────────────────────────────────────────────────────

export type SSEEventStart = { type: 'start' }
export type SSEEventChunk = { type: 'chunk'; data: string }
// message_id is absent in pre-generation safety path (Pattern B)
export type SSEEventDone = { type: 'done'; message_id?: string }
export type SSEEventSafety = { type: 'safety'; level: string }
export type SSEEventSafetyOverride = { type: 'safety_override'; level: string }
export type SSEEventError = { type: 'error'; error_code: 'llm_unavailable'; persona_voice: string }
export type SSEEventCorrection = { type: 'correction' }

export type SSEEvent =
  | SSEEventStart
  | SSEEventChunk
  | SSEEventDone
  | SSEEventSafety
  | SSEEventSafetyOverride
  | SSEEventError
  | SSEEventCorrection

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
  persona: Persona
  title: string | null
  message_count: number
  last_message_at: string | null
  created_at: string
  source_persona_slug: string | null
  source_context_content: string | null
  last_message_snippet: string | null
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  safety_level: string
  persona_override: boolean
  created_at: string
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

  // ── Personas ──────────────────────────────────────────────────────────────

  async getPersonas(): Promise<Persona[]> {
    return this.request<Persona[]>('/personas')
  }

  // ── Conversations ─────────────────────────────────────────────────────────

  async getConversations(): Promise<Conversation[]> {
    return this.request<Conversation[]>('/conversations')
  }

  async getConversation(id: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${id}`)
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
  async streamMessage(conversationId: string, content: string, userPlan: string = 'free'): Promise<Response> {
    const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ content }),
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

  // ── Memory ────────────────────────────────────────────────────────────────

  async getMemory(): Promise<MemoryEntry[]> {
    return this.request<MemoryEntry[]>('/memory')
  }

  async deleteMemory(id: string): Promise<void> {
    return this.request(`/memory/${id}`, { method: 'DELETE' })
  }

  // ── Insights ──────────────────────────────────────────────────────────────

  async getInsights(): Promise<Insight[]> {
    return this.request<Insight[]>('/insights')
  }

  async dismissInsight(id: string): Promise<void> {
    return this.request(`/insights/${id}/dismiss`, { method: 'PATCH' })
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

export interface PreferenceOut {
  user_id: string
  themes: string[]
  other_text: string | null
  need_most: string
  created_at: string
  updated_at: string
}

export interface Match {
  slug: string
  score: number
  reason: string
}

