'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { MessageCircle, Loader2, Bookmark, BookmarkCheck, Share2 } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Counterview, CounterviewListItem } from '@/lib/api'
import SubPageNav from '@/components/layout/SubPageNav'
import SharePreviewModal from '@/components/share/SharePreviewModal'

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
  // Go-deeper: which persona is mid-request (one at a time), and which personas
  // have nothing more to add (so we stop offering the tap).
  const [deepeningSlug, setDeepeningSlug] = useState<string | null>(null)
  const [exhausted, setExhausted] = useState<Set<string>>(new Set())
  // Save toggle — initial state hydrates from the loaded counterview's is_saved.
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  // Which of the two voices the shared verdict frame is showing (0 = baseRows[0],
  // 1 = baseRows[1]). Tapping a portrait or the toggle sets it; no new fetch — both
  // verdicts are already loaded in counterview.responses.
  const [activeSpeaker, setActiveSpeaker] = useState(0)
  // Revisit list — the user's recent generated counterviews, shown under the input
  // form. Loaded only on the voluntary (no-insightId) path; reopen pulls full via id.
  const [past, setPast] = useState<CounterviewListItem[]>([])

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }

    async function load() {
      try {
        // Suspense-safe (no useSearchParams): the effect is client-only.
        const insightId = new URLSearchParams(window.location.search).get('insightId')
        // No insight id → the voluntary input form (no fetch yet). Pull the revisit
        // list in the background — failure is non-fatal, the form still shows.
        if (!insightId) {
          setMode('input')
          api.listCounterviews().then(setPast).catch(() => {})
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

  // Reopen a past counterview: pull the full set by id and show its result. mode
  // stays 'input', but a now-truthy counterview falls through to the generated view.
  async function openPast(id: string) {
    setLoading(true)
    const cv = await api.getCounterview(id).catch(() => null)
    if (cv) {
      setCounterview(cv)
      setActiveSpeaker(0)
    }
    setLoading(false)
  }

  // Press one persona one layer deeper. Backend caps at a single round-1 per
  // persona; the returned counterview carries the new line (or is unchanged on a
  // no-op). Either way we stop offering the tap once it can add nothing more.
  const handleDeeper = async (slug: string) => {
    if (!counterview || deepeningSlug) return
    setDeepeningSlug(slug)
    try {
      const updated = await api.deeperCounterview(counterview.id, slug)
      setCounterview(updated)
      // No round-1 came back for this slug (empty/safety no-op) → don't re-offer.
      const gotDeeper = updated.responses.some((r) => r.persona_slug === slug && r.round === 1)
      if (!gotDeeper) setExhausted((prev) => new Set(prev).add(slug))
    } catch {
      setExhausted((prev) => new Set(prev).add(slug)) // 400/404 → don't loop the tap
    } finally {
      setDeepeningSlug(null)
    }
  }

  // Start over — wipe the result back to the voluntary input form. No endpoint:
  // it just re-shows the existing form (mode 'input', no counterview), which then
  // runs the existing createCounterview on submit.
  const handleStartOver = () => {
    setCounterview(null)
    setMode('input')
    setBelief('')
    setActiveSpeaker(0)
    setPhase(0)
    setSaved(false)
    setExhausted(new Set())
    setDeepeningSlug(null)
  }

  // Hydrate the Save toggle from the loaded counterview (correct state on reload).
  useEffect(() => {
    if (counterview) setSaved(counterview.is_saved)
  }, [counterview])

  // Optimistic save/unsave — revert the toggle if the request fails.
  const handleSave = async () => {
    if (!counterview || saving) return
    const next = !saved
    setSaving(true)
    setSaved(next)
    try {
      next ? await api.saveCounterview(counterview.id) : await api.unsaveCounterview(counterview.id)
    } catch {
      setSaved(!next)
    } finally {
      setSaving(false)
    }
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

        {past.length > 0 && (
          <section className="mt-[28px]">
            <p className="font-lora text-[11px] uppercase tracking-[0.22em] text-bronze-dark mb-[10px]">Past counterviews</p>
            <ul className="space-y-[8px]">
              {past.map((p) => (
                <li key={p.id}>
                  <button
                    onClick={() => openPast(p.id)}
                    className="w-full text-left bg-paper/60 border-[0.5px] border-edge rounded-[8px] px-[12px] py-[9px] active:scale-[0.99] transition-transform"
                  >
                    <span className="font-cormorant text-[15px] text-ink leading-snug line-clamp-2">{p.anchor_text || 'Untitled'}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
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

  // Two voices, in their authored order (position 0 left, 1 right). Round-0 drives
  // the columns; the deeper (round-1) line is looked up and stacked underneath.
  const baseRows = responses
    .filter((r) => r.round === 0)
    .sort((a, b) => a.position - b.position)
  const deeperFor = (slug: string) =>
    responses.find((r) => r.persona_slug === slug && r.round === 1)

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
    <>
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum px-[24px] pb-[60px]">
      <SubPageNav fallbackHref="/app/today" />

      {/* Compact, ornamented header */}
      <div className="text-center pt-[2px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark">
          The Wise Room
        </p>
        <h1 className="font-cormorant text-[22px] font-medium text-ink leading-tight mt-[2px]">
          Counterview
        </h1>
        <div className="mt-[6px]">
          <DiamondRule />
        </div>
      </div>

      {/* The two voices — large portraits side by side, tap to choose the speaker */}
      <div className="flex gap-[10px] mt-[14px]">
        {baseRows.map((r, i) => {
          const isActive = i === activeSpeaker
          return (
            <button
              key={r.persona_slug}
              type="button"
              onClick={() => setActiveSpeaker(i)}
              aria-pressed={isActive}
              className={`relative flex-1 h-[290px] rounded-[6px] overflow-hidden bg-linen transition-all duration-300 ${reveal(phase >= 1)} ${isActive ? 'opacity-100 shadow-[inset_0_0_0_2px_#B89968]' : 'opacity-50'}`}
            >
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
              {/* Speaking pill — only on the active voice */}
              {isActive && (
                <span className="absolute top-[8px] left-[8px] bg-bronze text-vellum font-lora text-[8px] uppercase tracking-[0.18em] px-[7px] py-[3px] rounded-full">
                  Speaking
                </span>
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
            </button>
          )
        })}
      </div>

      {/* The anchor — the insight (or belief) this case was made against */}
      {counterview?.anchor_text && (
        <div className={`mt-[16px] ${reveal(phase >= 4)}`}>
          <div className="flex items-center gap-[7px] mb-[6px]">
            <span className="w-[5px] h-[5px] rotate-45 bg-bronze" />
            <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark">
              {counterview.source === 'insight' ? 'Your insight' : 'Your belief'}
            </p>
          </div>
          <div className="bg-paper/60 border-[0.5px] border-edge rounded-[10px] px-[14px] py-[10px]">
            <p className="font-cormorant text-[17px] text-charcoal leading-snug">
              {counterview.anchor_text}
            </p>
          </div>
        </div>
      )}

      {/* One shared verdict frame — the speaker toggle switches the voice in place */}
      <div className={`mt-[16px] bg-paper rounded-[10px] border-[0.5px] border-edge shadow-card p-3 ${reveal(phase >= 2)}`}>
        {/* Speaker toggle — two halves, mirrors / is mirrored by the portrait tap */}
        <div className="flex rounded-[8px] border-[0.5px] border-bronze/30 overflow-hidden mb-[12px]">
          {baseRows.map((r, i) => {
            const isActive = i === activeSpeaker
            return (
              <button
                key={r.persona_slug}
                type="button"
                onClick={() => setActiveSpeaker(i)}
                aria-pressed={isActive}
                className={`flex-1 py-[8px] font-cormorant text-[15px] leading-none transition-colors ${isActive ? 'bg-bronze text-vellum' : 'bg-transparent text-charcoal'}`}
              >
                {r.persona_name}
              </button>
            )
          })}
        </div>

        {(() => {
          const active = baseRows[activeSpeaker] ?? baseRows[0]
          if (!active) return null
          const deeper = deeperFor(active.persona_slug)
          const isLoading = deepeningSlug === active.persona_slug
          const canDeepen = !deeper && !exhausted.has(active.persona_slug)
          return (
            <div className="relative px-[2px]">
              <p className="font-cormorant italic text-[17px] text-ink leading-snug pr-[22px]">
                {active.verdict}
              </p>
              {canDeepen && (
                <button
                  onClick={() => handleDeeper(active.persona_slug)}
                  disabled={deepeningSlug !== null}
                  aria-label="Go deeper"
                  className="absolute top-[2px] right-[2px] p-[2px] disabled:opacity-40"
                >
                  {isLoading ? (
                    <Loader2 size={15} strokeWidth={1.5} className="text-bronze animate-spin" />
                  ) : (
                    <MessageCircle size={15} strokeWidth={1.5} className="text-bronze" />
                  )}
                </button>
              )}
              {/* The second cut — stacked under the first when it exists */}
              {deeper && (
                <div className="mt-[12px] pt-[12px] border-t border-bronze/20">
                  <p className="font-cormorant text-[16px] italic text-charcoal leading-snug">
                    {deeper.verdict}
                  </p>
                </div>
              )}
            </div>
          )
        })()}
      </div>

      {/* Save · Start over · Share */}
      <div className={`mt-[20px] flex gap-[10px] ${reveal(phase >= 4)}`}>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 min-h-[44px] flex items-center justify-center gap-[7px] border-[0.5px] border-charcoal rounded-[6px] font-cormorant text-[15px] text-charcoal disabled:opacity-50"
        >
          {saved ? <BookmarkCheck size={16} strokeWidth={1.5} /> : <Bookmark size={16} strokeWidth={1.5} />}
          {saved ? 'Saved' : 'Save'}
        </button>
        <button
          onClick={handleStartOver}
          className="flex-[1.5] min-h-[48px] flex items-center justify-center border border-bronze-dark rounded-[6px] bg-bronze text-vellum font-cormorant text-[16px] font-medium"
        >
          Start over
        </button>
        <button
          onClick={() => setShareOpen(true)}
          className="flex-1 min-h-[44px] flex items-center justify-center gap-[7px] border-[0.5px] border-charcoal rounded-[6px] font-cormorant text-[15px] text-charcoal"
        >
          <Share2 size={16} strokeWidth={1.5} /> Share
        </button>
      </div>
    </main>

    {counterview && (
      <SharePreviewModal
        isOpen={shareOpen}
        onClose={() => setShareOpen(false)}
        kind="counterview"
        counterviewId={counterview.id}
        counterviewPortraits={baseRows.map((r) => r.persona_portrait_url).filter(Boolean) as string[]}
        quote={counterview.anchor_text ?? 'the case against this'}
      />
    )}
    </>
  )
}
