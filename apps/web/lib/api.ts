const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://philosopher-api-z9l9.onrender.com/api/v1'
// ── Types ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  full_name: string | null
  avatar_url: string | null
  is_admin: boolean
  onboarded_at: string | null
  created_at: string
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
  is_accessible: boolean
}

export interface Conversation {
  id: string
  persona: Persona
  title: string | null
  message_count: number
  last_message_at: string | null
  created_at: string
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
      throw new Error(error.detail ?? 'Request failed')
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

  // ── Personas ──────────────────────────────────────────────────────────────

  async getPersonas(): Promise<Persona[]> {
    return this.request<Persona[]>('/personas')
  }

  // ── Conversations ─────────────────────────────────────────────────────────

  async getConversations(): Promise<Conversation[]> {
    return this.request<Conversation[]>('/conversations')
  }

  async createConversation(persona_slug: string, ritual_id?: string): Promise<Conversation> {
    return this.request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ persona_slug, ritual_id }),
    })
  }

  async getMessages(conversationId: string): Promise<Message[]> {
    return this.request<Message[]>(`/conversations/${conversationId}/messages`)
  }

  async deleteConversation(id: string): Promise<void> {
    return this.request(`/conversations/${id}`, { method: 'DELETE' })
  }

  // SSE stream — returns the raw Response for manual reading
  async streamMessage(conversationId: string, content: string): Promise<Response> {
    const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ content }),
    })
    if (!res.ok) throw new Error('Stream failed')
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
}

export const api = new ApiClient()

// Load token from localStorage on module init (client-side only)
if (typeof window !== 'undefined') {
  api.loadToken()
}
