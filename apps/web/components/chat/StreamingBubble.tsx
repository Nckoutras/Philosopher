'use client'

import { useStore } from '@/lib/store'

export default function StreamingBubble() {
  const isStreaming = useStore((s) => s.isStreaming)
  const streamingContent = useStore((s) => s.streamingContent)
  const isCorrecting = useStore((s) => s.isCorrecting)
  const correctionContent = useStore((s) => s.correctionContent)

  if (!isStreaming) return null

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] px-4 py-3 rounded-sm shadow-card bg-white font-lora text-[16px] text-safety leading-relaxed whitespace-pre-wrap">
        {isCorrecting ? (
          <>
            <span className="text-charcoal opacity-55 transition-opacity duration-300">
              {streamingContent}
            </span>
            <div className="my-2 border-t border-bronze opacity-60" />
            <p className="font-cormorant italic text-[13px] text-sepia mb-3">
              Let me put that again.
            </p>
            {correctionContent ? (
              <span className="animate-fade-in">{correctionContent}</span>
            ) : (
              <span className="text-sepia italic">Thinking…</span>
            )}
            <span className="streaming-cursor" aria-hidden="true" />
          </>
        ) : (
          <>
            {streamingContent || (
              <span className="text-sepia italic">Thinking…</span>
            )}
            <span className="streaming-cursor" aria-hidden="true" />
          </>
        )}
      </div>
    </div>
  )
}
