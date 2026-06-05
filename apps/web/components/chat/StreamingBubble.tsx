'use client'

import { useStore } from '@/lib/store'

export default function StreamingBubble() {
  const isStreaming = useStore((s) => s.isStreaming)
  const streamingContent = useStore((s) => s.streamingContent)
  const isCorrecting = useStore((s) => s.isCorrecting)
  const correctionContent = useStore((s) => s.correctionContent)
  const streamingBroughtInName = useStore((s) => s.streamingBroughtInName)
  const activePersonaName = useStore((s) => s.activePersonaName)

  if (!isStreaming) return null

  const broughtIn = !!streamingBroughtInName

  return (
    <div className="flex flex-col items-start">
      {broughtIn && (
        <>
          <p className="font-lora text-[10px] text-sepia uppercase tracking-[0.18em] text-center my-1 w-full">
            {activePersonaName} steps aside
          </p>
          <p className="font-lora text-[9px] text-sepia uppercase tracking-[0.18em] mb-1">
            {streamingBroughtInName} · brought in
          </p>
        </>
      )}
      <div className={`max-w-[80%] px-4 py-3 rounded-sm shadow-card font-lora text-[16px] text-safety leading-relaxed whitespace-pre-wrap animate-fade-in ${broughtIn ? 'bg-linen' : 'bg-white'}`}>
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
