'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { MessageCircle } from 'lucide-react'
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
  // Staged line-level reveal of the generated result:
  // 0 nothing · 1 portraits+names · 2 Musashi verdict · 3 Machiavelli verdict ·
  // 4 the anchor. prefers-reduced-motion jumps straight to 4 (everything shown).
  const [phase, setPhase] = useState(0)
  // Insight path (?insightId=) auto-generates; input path lets the user type a
  // belief and submit. Starts 'unresolved' until the load effect reads the URL —
  // so voluntary entry never flashes the generating copy before the form.
  const [mode, setMode] = useState<'unresolved' | 'insight' | 'input'>('unresolved')
  const [belief, setBelief] = useState('')

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }

    async function load() {
      try {
        // Suspense-safe (no useSearchParams): the effect is client-only.
        const insightId = new URLSearchParams(window.location.search).get('insightId')
        // No insight id → the voluntary input form (no fetch yet).
        if (!insightId) {
          setMode('input')
          return
        }
        setMode('insight')
        const cv = await api.counterviewFromInsight(insightId).catch(() => null)
        setCounterview(cv)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [token, router])

  const responses = counterview?.responses ?? []
  const generated = counterview?.status === 'generated' && responses.length > 0

  // Drive the staged reveal once a generated result is in. Pure setTimeout phases
  // (no rAF, no word-by-word). prefers-reduced-motion skips straight to the end.
  useEffect(() => {
    if (!generated) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setPhase(4)
      return
    }
    const timers = [
      setTimeout(() => setPhase(1), 150),
      setTimeout(() => setPhase(2), 800),
      setTimeout(() => setPhase(3), 1600),
      setTimeout(() => setPhase(4), 2300),
    ]
    return () => timers.forEach(clearTimeout)
  }, [counterview?.id, generated])

  async function handleSubmit() {
    const b = belief.trim()
    if (!b) return
    setLoading(true)
    const cv = await api.createCounterview(b).catch(() => null)
    setCounterview(cv)
    setLoading(false)
  }

  // ── Initial resolve (before we know insight vs input): a blank vellum beat,
  // never the generating copy — avoids flashing "Putting it to the test…" on
  // voluntary entry, where there is no fetch.
  if (loading && mode === 'unresolved') {
    return <main className="min-h-screen [min-height:100svh] bg-vellum" />
  }

  // ── Generating: a quiet wait while the POST runs (insight fetch or submit) ──
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

  // ── Voluntary input: the user types a belief to test ──
  if (mode === 'input' && !counterview) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum px-[24px] pb-[60px]">
        <SubPageNav fallbackHref="/app/rituals" />

        <div className="mt-[8px]">
          <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[6px]">
            The Wise Room
          </p>
          <h1 className="font-cormorant text-[34px] font-medium text-ink leading-tight">
            Counterview
          </h1>
        </div>

        <div className="mt-[28px]">
          <p className="font-cormorant text-[24px] text-ink leading-snug">
            What do you hold to be true?
          </p>
          <p className="font-lora text-[14px] text-sepia leading-[1.6] mt-[8px]">
            Write it plainly. The sharper the conviction, the better the test.
          </p>
        </div>

        <textarea
          value={belief}
          onChange={(e) => setBelief(e.target.value)}
          maxLength={1000}
          rows={5}
          placeholder="I believe&hellip;"
          className="mt-[20px] w-full bg-paper border-[0.5px] border-edge rounded-[16px] shadow-card px-[16px] py-[14px] font-lora text-[16px] text-ink leading-[1.6] resize-none focus:outline-none focus:border-bronze placeholder:text-sepia/60"
        />

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!belief.trim()}
          className="mt-[20px] w-full py-[14px] rounded-[14px] bg-bronze text-vellum font-cormorant text-[18px] font-medium disabled:opacity-40"
        >
          Make the case
        </button>
      </main>
    )
  }

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

  // Reveal helper: hidden (faint, nudged down) → settled. An element becomes
  // visible when its phase threshold is crossed.
  const reveal = (shown: boolean) =>
    `transition-all duration-700 ease-out ${shown ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-[8px]'}`

  // Two voices, in their authored order (position 0 left, 1 right). Round-0 only
  // for now — go-deeper round-1 stacking lands in a later slice.
  const ordered = responses
    .filter((r) => r.round === 0)
    .sort((a, b) => a.position - b.position)

  // Small ornamental rule (hairline · diamond · hairline). Reused in the header
  // and inside the portrait name overlay.
  const DiamondRule = ({ w = '40px' }: { w?: string }) => (
    <div className="flex items-center justify-center gap-[8px]">
      <span className="h-px bg-bronze/40" style={{ width: w }} />
      <span className="w-[6px] h-[6px] rotate-45 bg-bronze" />
      <span className="h-px bg-bronze/40" style={{ width: w }} />
    </div>
  )

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum px-[24px] pb-[60px]">
      <SubPageNav fallbackHref="/app/today" />

      {/* Centered, ornamented header */}
      <div className="text-center pt-[10px]">
        <p className="font-lora text-[12px] uppercase tracking-[0.28em] text-bronze-dark">
          The Wise Room
        </p>
        <div className="my-[10px]">
          <DiamondRule />
        </div>
        <h1 className="font-cormorant text-[44px] font-medium text-ink leading-tight">
          Counterview
        </h1>
        <div className="mt-[10px]">
          <DiamondRule />
        </div>
      </div>

      {/* The two verdicts — framed portrait card + verdict box per persona */}
      <div className="flex gap-[14px] mt-[26px]">
        {ordered.map((r, i) => (
          <div key={r.persona_slug} className="flex-1 flex flex-col">
            {/* Portrait card — framed, tall, name overlay + corner brackets */}
            <div className={`relative aspect-[3/5] rounded-[6px] overflow-hidden bg-linen ${reveal(phase >= 1)}`}>
              {r.persona_portrait_url ? (
                <Image
                  src={r.persona_portrait_url}
                  alt={r.persona_name}
                  fill
                  className="object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center font-cormorant text-[40px] text-charcoal">
                  {r.persona_name.charAt(0)}
                </div>
              )}
              <div className="absolute inset-x-0 bottom-0 h-[42%] bg-gradient-to-t from-black/60 to-transparent" />
              <div className="absolute inset-x-0 bottom-[12px] px-[6px] text-center">
                <p className="font-cormorant text-[20px] text-[#F5ECD8] leading-tight">
                  {r.persona_name}
                </p>
                <div className="mt-[5px]">
                  <DiamondRule w="18px" />
                </div>
              </div>
              {/* corner brackets */}
              <span className="absolute top-[6px] left-[6px] w-[13px] h-[13px] border-t border-l border-[#D9B98A]/80" />
              <span className="absolute top-[6px] right-[6px] w-[13px] h-[13px] border-t border-r border-[#D9B98A]/80" />
              <span className="absolute bottom-[6px] left-[6px] w-[13px] h-[13px] border-b border-l border-[#D9B98A]/80" />
              <span className="absolute bottom-[6px] right-[6px] w-[13px] h-[13px] border-b border-r border-[#D9B98A]/80" />
            </div>
            {/* Verdict box — inset double frame + speech bubble */}
            <div className={`mt-[12px] bg-paper rounded-[10px] border-[0.5px] border-edge shadow-card p-[5px] ${reveal(phase >= 2 + i)}`}>
              <div className="relative border-[0.5px] border-bronze/30 rounded-[7px] px-[14px] py-[14px]">
                <p className="font-cormorant text-[17px] text-ink leading-snug pr-[22px]">
                  {r.verdict}
                </p>
                <MessageCircle size={15} strokeWidth={1.5} className="absolute top-[12px] right-[12px] text-bronze" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* The anchor — the insight (or belief) this case was made against */}
      {counterview?.anchor_text && (
        <div className={`mt-[28px] ${reveal(phase >= 4)}`}>
          <div className="flex items-center gap-[7px] mb-[8px]">
            <span className="w-[5px] h-[5px] rotate-45 bg-bronze" />
            <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark">
              {counterview.source === 'insight' ? 'Your insight' : 'Your belief'}
            </p>
          </div>
          <div className="bg-paper/60 border-[0.5px] border-edge rounded-[10px] px-[16px] py-[14px]">
            <p className="font-cormorant text-[19px] text-charcoal leading-snug">
              {counterview.anchor_text}
            </p>
          </div>
        </div>
      )}
    </main>
  )
}
