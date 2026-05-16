'use client'

import { useStore } from '@/lib/store'

export default function StreamingBubble() {
  const isStreaming = useStore((s) => s.isStreaming)
  const streamingContent = useStore((s) => s.streamingContent)

  if (!isStreaming) return null

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] px-4 py-3 rounded-sm shadow-card bg-white font-lora text-[14px] text-safety leading-relaxed whitespace-pre-wrap">
        {streamingContent || (
          <span className="text-sepia italic">Thinking…</span>
        )}
        <span className="streaming-cursor" aria-hidden="true" />
      </div>
    </div>
  )
}
