import { useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { api, Message, RateLimitError, SSEEvent, SSEEventStart } from '@/lib/api'
import { useStore } from '@/lib/store'
import toast from 'react-hot-toast'

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
  } = useStore()

  const send = useCallback(async (content: string) => {
    if (!activeConversationId) return

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
      const res = await api.streamMessage(activeConversationId, content, currentPlan)
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
        setStreamError(pendingStreamError)
        resetStreaming()
      }
    } catch (err: unknown) {
      resetStreaming()
      if (err instanceof RateLimitError) {
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
    if (!activeConversationId) return

    setSafetyActive(false)
    setStreamError(null)
    setStreaming(true)

    try {
      const currentPlan = useStore.getState().plan
      const res = await api.streamAnotherMind(activeConversationId, personaSlug, currentPlan)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let broughtInSlug: string | undefined
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
            case 'start':
              broughtInSlug = (event as SSEEventStart).persona_slug
              break
            case 'chunk':
              fullContent += event.data
              appendStreamingContent(event.data)
              break
            case 'done': {
              const assistantMsg: Message = {
                id: event.message_id ?? crypto.randomUUID(),
                role: 'assistant',
                content: fullContent,
                safety_level: 'none',
                persona_override: false,
                created_at: new Date().toISOString(),
                persona_slug: broughtInSlug ?? null,
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
        setStreamError(pendingStreamError)
        resetStreaming()
      }
    } catch (err: unknown) {
      resetStreaming()
      if (err instanceof RateLimitError) {
        setShowPaywall(true, {
          upgradeTarget: err.upgradeTarget,
          resetAt: err.resetAt,
          limit: err.limit,
          personaVoice: err.personaVoice,
        })
      } else if (err instanceof Error && err.message === 'upgrade_required') {
        router.push('/app/upgrade')
      } else {
        toast.error('Something went wrong. Please try again.')
      }
      console.error(err)
    }
  }, [activeConversationId, appendMessage, setStreaming, appendStreamingContent, resetStreaming, setSafetyActive, setStreamError, setShowPaywall, router])

  return { send, sendAnotherMind }
}
