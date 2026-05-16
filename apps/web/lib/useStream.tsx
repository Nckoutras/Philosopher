import { useCallback } from 'react'
import { api, Message, RateLimitError, SSEEvent } from '@/lib/api'
import { useStore } from '@/lib/store'
import toast from 'react-hot-toast'

export function useStream() {
  const {
    activeConversationId,
    appendMessage,
    setStreaming,
    appendStreamingContent,
    resetStreaming,
    setSafetyActive,
    setStreamError,
  } = useStore()

  const send = useCallback(async (content: string) => {
    if (!activeConversationId) return

    // Clear any previous stream error state before starting
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
              appendStreamingContent(event.data)
              break
            case 'safety':
            case 'safety_override':
              setSafetyActive(true)
              fullContent = ''
              useStore.getState().setStreamingContent('')
              break
            case 'done': {
              const assistantMsg: Message = {
                id: event.message_id ?? crypto.randomUUID(),
                role: 'assistant',
                content: fullContent,
                safety_level: useStore.getState().safetyActive ? 'high' : 'none',
                persona_override: useStore.getState().safetyActive,
                created_at: new Date().toISOString(),
              }
              appendMessage(assistantMsg)
              resetStreaming()
              setSafetyActive(false)
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
        // RF-02: upgradeTarget is now correctly computed from userPlan in streamMessage
        const upgradeLabel = err.upgradeTarget === 'premium' ? 'Premium' : 'Pro'
        toast.error(
          (t: { id: string }) => (
            <span>
              Daily limit reached.{' '}
              <a
                href="/app/billing"
                onClick={() => toast.dismiss(t.id)}
                style={{ textDecoration: 'underline', fontWeight: 600 }}
              >
                Upgrade to {upgradeLabel} →
              </a>
            </span>
          ),
          { duration: 6000 },
        )
      } else {
        toast.error('Something went wrong. Please try again.')
      }
      console.error(err)
    }
  }, [activeConversationId, appendMessage, setStreaming, appendStreamingContent, resetStreaming, setSafetyActive, setStreamError])

  return { send }
}
