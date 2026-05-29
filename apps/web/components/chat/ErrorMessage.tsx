'use client'

import { useStore } from '@/lib/store'

interface Props {
  send: (content: string) => void
}

export default function ErrorMessage({ send }: Props) {
  const streamError = useStore((s) => s.streamError)
  const messages = useStore((s) => s.messages)
  const setStreamError = useStore((s) => s.setStreamError)

  if (!streamError) return null

  const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user')

  const handleRetry = () => {
    setStreamError(null)
    if (lastUserMsg) {
      send(lastUserMsg.content)
    }
  }

  return (
    <div className="px-1 py-2">
      <p
        className="font-lora text-[16px] italic leading-relaxed"
        style={{ color: 'rgba(184, 153, 104, 0.6)' }}
      >
        {streamError.persona_voice}
      </p>
      <button
        onClick={handleRetry}
        className="mt-1 font-lora text-[12px] text-sepia underline underline-offset-2"
      >
        Try again
      </button>
    </div>
  )
}
