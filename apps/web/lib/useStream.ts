import { useCallback } from 'react'
import { api, Message } from '@/lib/api'
import { useStore } from '@/lib/store'
import toast from 'react-hot-toast'

export function useStream() {
  const {
    activeConversationId,
    appendMessage,
    setStreaming,
    appendStreamingContent,
    resetStreaming,
    streamingContent,
    setSafetyActive,
  } = useStore()

  const send = useCallback(async (content: string) => {
    if (!activeConversationId) return

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
      const res = await api.streamMessage(activeConversationId, content)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''

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

          let event: { type: string; data?: string; level?: string; message_id?: string }
          try {
            event = JSON.parse(raw)
          } catch {
            continue
          }

          switch (event.type) {
            case 'chunk':
              fullContent += event.data ?? ''
              appendStreamingContent(event.data ?? '')
              break
            case 'safety':
            case 'safety_override':
              setSafetyActive(true)
              fullContent = ''
              useStore.getState().setStreamingContent('')
              break
            case 'done':
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
            case 'error':
              throw new Error('Stream error from server')
          }
        }
      }
    } catch (err) {
      resetStreaming()
      toast.error('Something went wrong. Please try again.')
      console.error(err)
    }
  }, [activeConversationId, appendMessage, setStreaming, appendStreamingContent, resetStreaming, setSafetyActive])

  return { send }
}
