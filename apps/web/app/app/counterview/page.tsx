'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Counterview } from '@/lib/api'
import SubPageNav from '@/components/layout/SubPageNav'

// The Counterview reader (DS v5). Reached from an insight card's "Doubt this":
// the insight id rides in the query string (?insightId=…). Insight-path only for
// now — voluntary (typed-belief) input is a later slice. No reveal animation, no
// save/share/go-deeper yet.
export default function CounterviewPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [loading, setLoading] = useState(true)
  const [counterview, setCounterview] = useState<Counterview | null>(null)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }

    async function load() {
      try {
        // Suspense-safe (no useSearchParams): the effect is client-only.
        const insightId = new URLSearchParams(window.location.search).get('insightId')
        // No insight id → straight to the gentle fallback (voluntary input is later).
        if (!insightId) return
        const cv = await api.counterviewFromInsight(insightId).catch(() => null)
        setCounterview(cv)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [token, router])

  // ── Generating: a quiet wait while the POST runs ──
  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-[24px] text-center">
        <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[10px]">
          The Wise Room
        </p>
        <p className="font-cormorant italic text-[20px] text-sepia">
          Putting it to the test&hellip;
        </p>
      </main>
    )
  }

  const responses = counterview?.responses ?? []
  const generated = counterview?.status === 'generated' && responses.length > 0

  // ── Nothing to show (empty/suppressed/no responses) ──
  // A gentle, neutral fallback — the same copy for empty and suppressed, never
  // exposing safety detection.
  if (!generated) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum px-[24px] pb-[60px]">
        <SubPageNav fallbackHref="/app/today" />
        <div className="flex-1 flex flex-col items-center justify-center text-center gap-[14px]">
          <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark">
            The Wise Room
          </p>
          <p className="font-cormorant text-[24px] text-ink leading-snug max-w-[300px]">
            There wasn&rsquo;t a clear case to make against this just yet.
          </p>
        </div>
      </main>
    )
  }

  // Two voices, in their authored order (position 0 left, 1 right).
  const ordered = [...responses].sort((a, b) => a.position - b.position)

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum px-[24px] pb-[60px]">
      <SubPageNav fallbackHref="/app/today" />

      <div className="mt-[8px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[6px]">
          The Wise Room
        </p>
        <h1 className="font-cormorant text-[34px] font-medium text-ink leading-tight">
          Counterview
        </h1>
      </div>

      {/* The two verdicts, side by side */}
      <div className="flex gap-[14px] mt-[28px]">
        {ordered.map((r) => (
          <div key={r.persona_slug} className="flex-1 flex flex-col items-center text-center gap-[12px]">
            <div className="w-[64px] h-[64px] rounded-full overflow-hidden flex-shrink-0 bg-linen border border-bronze flex items-center justify-center">
              {r.persona_portrait_url ? (
                <Image
                  src={r.persona_portrait_url}
                  alt={r.persona_name}
                  width={64}
                  height={64}
                  className="object-cover w-full h-full"
                />
              ) : (
                <span className="font-cormorant text-[26px] font-medium text-charcoal">
                  {r.persona_name.charAt(0)}
                </span>
              )}
            </div>
            <p className="font-cormorant text-[22px] font-medium text-ink leading-tight">
              {r.persona_name}
            </p>
            <div className="w-full bg-paper border-[0.5px] border-edge rounded-[16px] shadow-card px-[16px] py-[18px]">
              <p className="font-cormorant text-[19px] text-ink leading-snug">
                {r.verdict}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* The anchor — the insight this case was made against */}
      {counterview?.anchor_text && (
        <div className="mt-[36px]">
          <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[8px]">
            Your insight
          </p>
          <p className="font-cormorant text-[20px] text-sepia leading-snug">
            {counterview.anchor_text}
          </p>
        </div>
      )}
    </main>
  )
}
