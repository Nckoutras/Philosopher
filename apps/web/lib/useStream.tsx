import { useCallback, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { api, Message, RateLimitError, SSEEvent, SSEEventStart } from '@/lib/api'
import { useStore } from '@/lib/store'
import { track } from '@/lib/analytics'
import { latencyBucket } from '@/lib/analyticsEvents'
import toast from 'react-hot-toast'
import { fairUseMessage } from '@/lib/fairUseCopy'

export function useStream() {
  const router = useRouter()
  const {
    activeConversationId,
    appendMessage,
    setStreaming,
    appendStreamingContent,
    resetStreaming,
    setSafetyActive,
    setStreamError,
    setShowPaywall,
    setCorrection,
    appendCorrectionContent,
    setStreamingBroughtIn,
  } = useStore()

  // Tracks the in-flight SSE stream so it can be aborted on unmount (navigate
  // away) or when a new send supersedes it. Aborting cancels the fetch + reader
  // and lets the server detect the disconnect, releasing its DB session (§5).
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  const send = useCallback(async (content: string, seededOpening: boolean = false) => {
    // Clock for first_reply_rendered, started at the send rather than at the
    // request: what the user experiences as latency begins when they tap.
    const _t0 = Date.now()
    if (!activeConversationId) return

    // Abort any prior in-flight stream before starting a new one.
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    // Clear prior safety and error states before starting
    setSafetyActive(false)
    setStreamError(null)

    // Optimistic user message
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      safety_level: 'none',
      persona_override: false,
      created_at: new Date().toISOString(),
    }
    appendMessage(userMsg)
    setStreaming(true)

    try {
      const currentPlan = useStore.getState().plan
      const res = await api.streamMessage(activeConversationId, content, currentPlan, seededOpening, controller.signal)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let isCorrecting = false
      let contentBeforeCorrection = ''
      // RF-01: capture error event data instead of discarding persona_voice
      let pendingStreamError: { error_code: string; persona_voice: string } | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event: SSEEvent
          try {
            event = JSON.parse(raw) as SSEEvent
          } catch {
            continue
          }

          switch (event.type) {
            case 'start': {
              // Deep-mode metering signal. deep_remaining is the free-tier
              // remaining after this reply; -1 is a filler for deep-off/pro and
              // must NOT overwrite the store's real remaining. Only a >= 0 value
              // is authoritative. deep_applied is unused here (reserved for A3).
              const ev = event as SSEEventStart
              if (typeof ev.deep_remaining === 'number' && ev.deep_remaining >= 0) {
                useStore.getState().setDeepRemaining(ev.deep_remaining)
              }
              break
            }
            case 'chunk':
              fullContent += event.data
              if (isCorrecting) {
                appendCorrectionContent(event.data)
              } else {
                appendStreamingContent(event.data)
              }
              break
            case 'correction':
              contentBeforeCorrection = fullContent
              fullContent = ''
              isCorrecting = true
              setCorrection()
              break
            case 'safety':
            case 'safety_override':
              setSafetyActive(true)
              fullContent = ''
              useStore.getState().setStreamingContent('')
              break
            case 'done': {
              // first_reply_rendered: the reply is on screen NOW. The server
              // knows when it finished streaming; only the browser knows when
              // the user could read it, which is the number that matters for
              // "is this too slow to wait through". A bucket, never raw ms.
              track('first_reply_rendered', {
                persona: useStore.getState().activePersonaSlug ?? 'unknown',
                latency_bucket: latencyBucket(Date.now() - _t0),
                origin: 'send',
              })
              // Skip appending an empty assistant message when safety fired;
              // SafetyBubble represents that response in the UI.
              if (!useStore.getState().safetyActive) {
                // When correction was triggered but no correction chunks arrived
                // (stream failed before first chunk), fall back to original content.
                const finalContent = fullContent || contentBeforeCorrection
                const assistantMsg: Message = {
                  id: event.message_id ?? crypto.randomUUID(),
                  role: 'assistant',
                  content: finalContent,
                  safety_level: 'none',
                  persona_override: false,
                  created_at: new Date().toISOString(),
                }
                appendMessage(assistantMsg)
              }
              resetStreaming()
              // safetyActive intentionally NOT cleared here — it stays true
              // until the user sends their next message (cleared at top of send).
              break
            }
            case 'error':
              // RF-01: capture persona_voice from error event; stream ends after this
              pendingStreamError = { error_code: event.error_code, persona_voice: event.persona_voice }
              break
          }
        }

        if (pendingStreamError) break
      }

      // RF-01: surface the error event to store for UI consumers
      if (pendingStreamError) {
        await reader.cancel().catch(() => {})
        setStreamError(pendingStreamError)
        resetStreaming()
      }
    } catch (err: unknown) {
      // Intentional abort (unmount / superseded by a newer send): the newer
      // flow owns the streaming state, so do not reset it or toast here.
      if (err instanceof DOMException && err.name === 'AbortError') return
      resetStreaming()
      if (err instanceof RateLimitError && err.errorCode === 'fair_use_limit') {
        // Pro fair-use cap. NEVER the paywall: this user is already a
        // subscriber and there is nothing to sell them. Plain notice only.
        toast(fairUseMessage(err.resetAt))
      } else if (err instanceof RateLimitError) {
        // RF-02: show paywall modal instead of toast
        setShowPaywall(true, {
          upgradeTarget: err.upgradeTarget,
          resetAt: err.resetAt,
          limit: err.limit,
          personaVoice: err.personaVoice,
        })
      } else {
        toast.error('Something went wrong. Please try again.')
      }
      console.error(err)
    }
  }, [activeConversationId, appendMessage, setStreaming, appendStreamingContent, resetStreaming, setSafetyActive, setStreamError, setShowPaywall, setCorrection, appendCorrectionContent])

  const sendAnotherMind = useCallback(async (personaSlug: string) => {
    // Clock for first_reply_rendered, started at the send rather than at the
    // request: what the user experiences as latency begins when they tap.
    const _t0 = Date.now()
    if (!activeConversationId) return

    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setSafetyActive(false)
    setStreamError(null)
    setStreaming(true)

    try {
      const currentPlan = useStore.getState().plan
      const res = await api.streamAnotherMind(activeConversationId, personaSlug, currentPlan, controller.signal)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let broughtInSlug: string | undefined
      let broughtInName: string | undefined
      let pendingStreamError: { error_code: string; persona_voice: string } | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event: SSEEvent
          try {
            event = JSON.parse(raw) as SSEEvent
          } catch {
            continue
          }

          switch (event.type) {
            case 'start': {
              const ev = event as SSEEventStart
              broughtInSlug = ev.persona_slug
              broughtInName = ev.persona_name
              setStreamingBroughtIn(ev.persona_name ?? null)
              break
            }
            case 'chunk':
              fullContent += event.data
              appendStreamingContent(event.data)
              break
            case 'done': {
              // first_reply_rendered: the reply is on screen NOW. The server
              // knows when it finished streaming; only the browser knows when
              // the user could read it, which is the number that matters for
              // "is this too slow to wait through". A bucket, never raw ms.
              track('first_reply_rendered', {
                persona: useStore.getState().activePersonaSlug ?? 'unknown',
                latency_bucket: latencyBucket(Date.now() - _t0),
                origin: 'another_mind',
              })
              const assistantMsg: Message = {
                id: event.message_id ?? crypto.randomUUID(),
                role: 'assistant',
                content: fullContent,
                safety_level: 'none',
                persona_override: false,
                created_at: new Date().toISOString(),
                persona_slug: broughtInSlug ?? null,
                persona_name: broughtInName ?? null,
              }
              appendMessage(assistantMsg)
              resetStreaming()
              break
            }
            case 'error':
              pendingStreamError = { error_code: event.error_code, persona_voice: event.persona_voice }
              break
          }
        }

        if (pendingStreamError) break
      }

      if (pendingStreamError) {
        await reader.cancel().catch(() => {})
        setStreamError(pendingStreamError)
        resetStreaming()
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      resetStreaming()
      if (err instanceof RateLimitError && err.errorCode === 'fair_use_limit') {
        // Pro fair-use cap. NEVER the paywall: this user is already a
        // subscriber and there is nothing to sell them. Plain notice only.
        toast(fairUseMessage(err.resetAt))
      } else if (err instanceof RateLimitError) {
        setShowPaywall(true, {
          upgradeTarget: err.upgradeTarget,
          resetAt: err.resetAt,
          limit: err.limit,
          personaVoice: err.personaVoice,
        })
      } else if (err instanceof Error && err.message === 'upgrade_required') {
        // Same condition as AnotherMindSheet's client-side guard: the backend's
        // is_persona_accessible check on /another-mind. One name for one thing.
        router.push(`/app/upgrade?source=persona_locked&persona=${encodeURIComponent(personaSlug)}`)
      } else {
        toast.error('Something went wrong. Please try again.')
      }
      console.error(err)
    }
  }, [activeConversationId, appendMessage, setStreaming, appendStreamingContent, resetStreaming, setSafetyActive, setStreamError, setShowPaywall, setStreamingBroughtIn, router])

  const sendGoDeeper = useCallback(async () => {
    // Clock for first_reply_rendered, started at the send rather than at the
    // request: what the user experiences as latency begins when they tap.
    const _t0 = Date.now()
    if (!activeConversationId) return

    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setSafetyActive(false)
    setStreamError(null)
    setStreaming(true)

    try {
      const currentPlan = useStore.getState().plan
      const res = await api.streamGoDeeper(activeConversationId, currentPlan, controller.signal)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let pendingStreamError: { error_code: string; persona_voice: string } | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event: SSEEvent
          try {
            event = JSON.parse(raw) as SSEEvent
          } catch {
            continue
          }

          switch (event.type) {
            case 'start': {
              break
            }
            case 'chunk':
              fullContent += event.data
              appendStreamingContent(event.data)
              break
            case 'done': {
              // first_reply_rendered: the reply is on screen NOW. The server
              // knows when it finished streaming; only the browser knows when
              // the user could read it, which is the number that matters for
              // "is this too slow to wait through". A bucket, never raw ms.
              track('first_reply_rendered', {
                persona: useStore.getState().activePersonaSlug ?? 'unknown',
                latency_bucket: latencyBucket(Date.now() - _t0),
                origin: 'go_deeper',
              })
              const assistantMsg: Message = {
                id: event.message_id ?? crypto.randomUUID(),
                role: 'assistant',
                content: fullContent,
                safety_level: 'none',
                persona_override: false,
                created_at: new Date().toISOString(),
                persona_slug: null,
                persona_name: null,
              }
              appendMessage(assistantMsg)
              resetStreaming()
              break
            }
            case 'limit': {
              if (event.scope === 'turn') {
                toast("You've drawn this reply as far as it goes — bring a new thought, or another mind.")
              } else if (event.tier === 'free') {
                setShowPaywall(true, { upgradeTarget: 'pro', reason: 'go_deeper_depth' })
              } else {
                toast("You've reached this conversation's depth. Start a fresh thread to keep going.")
              }
              resetStreaming()
              break
            }
            case 'error':
              pendingStreamError = { error_code: event.error_code, persona_voice: event.persona_voice }
              break
          }
        }

        if (pendingStreamError) break
      }

      if (pendingStreamError) {
        await reader.cancel().catch(() => {})
        setStreamError(pendingStreamError)
        resetStreaming()
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      resetStreaming()
      if (err instanceof RateLimitError && err.errorCode === 'fair_use_limit') {
        // Pro fair-use cap. NEVER the paywall: this user is already a
        // subscriber and there is nothing to sell them. Plain notice only.
        toast(fairUseMessage(err.resetAt))
      } else if (err instanceof RateLimitError) {
        setShowPaywall(true, {
          upgradeTarget: err.upgradeTarget,
          resetAt: err.resetAt,
          limit: err.limit,
          personaVoice: err.personaVoice,
        })
      } else if (err instanceof Error && err.message === 'upgrade_required') {
        // NOTE: /go-deeper never returns upgrade_required — its only error_code
        // is rate_limited (verified against routers/conversations.py). This branch
        // is therefore unreachable today. Tagged anyway so it is correct if the
        // guard is ever added; expect zero traffic on source=go_deeper until then.
        router.push('/app/upgrade?source=go_deeper')
      } else {
        toast.error('Something went wrong. Please try again.')
      }
      console.error(err)
    }
  }, [activeConversationId, appendMessage, setStreaming, appendStreamingContent, resetStreaming, setSafetyActive, setStreamError, setShowPaywall, router])

  return { send, sendAnotherMind, sendGoDeeper }
}
