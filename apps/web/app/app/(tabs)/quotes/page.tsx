'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Quote } from '@/lib/api'
import QuoteCard from '@/components/quotes/QuoteCard'
import BottomSheet from '@/components/ui/BottomSheet'
import PaywallModal from '@/components/chat/PaywallModal'
import { openingFor } from '@/lib/quotePrefill'

type PersonaMeta = { name: string; portrait_url: string | null }

// Fisher-Yates — pure. Used to build each no-repeat rotation cycle.
function shuffle<T>(input: T[]): T[] {
  const a = [...input]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export default function QuotesPage() {
  const token = useStore((s) => s.token)
  const router = useRouter()

  const [quotes, setQuotes] = useState<Quote[]>([])
  const [feed, setFeed] = useState<Quote[]>([])
  const [personaMap, setPersonaMap] = useState<Record<string, PersonaMeta>>({})
  const [loading, setLoading] = useState(true)
  const [errored, setErrored] = useState(false)

  // The full pool (one occurrence of each quote), read by appendCycle from a ref so
  // the interval/scroll closures never see a stale copy.
  const poolRef = useRef<Quote[]>([])

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    let active = true
    async function load() {
      try {
        const [quoteList, personas] = await Promise.all([api.getQuotes(), api.getPersonas()])
        if (!active) return
        const map: Record<string, PersonaMeta> = {}
        for (const p of personas) {
          map[p.slug] = { name: p.name, portrait_url: p.portrait_url || null }
        }
        setPersonaMap(map)
        setQuotes(quoteList)
        // Rotation queue: the pool is one occurrence of each quote; the first cycle is
        // a shuffle of it. appendCycle() extends the feed with further seam-avoided
        // shuffles so every quote is seen before any repeats. load() runs once per
        // mount, so re-entering the tab (remount) starts a fresh rotation.
        poolRef.current = quoteList
        setFeed(shuffle(quoteList))
      } catch {
        if (active) setErrored(true)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [token, router])

  // ── Peek-carousel: no-repeat rotation + gentle auto-advance ──────────────────

  const scrollerRef = useRef<HTMLDivElement | null>(null)
  const pausedRef = useRef(false) // auto-advance stops permanently on first interaction
  const programmaticRef = useRef(false) // true while WE are scrolling (not the user)
  const currentIndexRef = useRef(0)
  const intervalRef = useRef<number | null>(null)
  const appendGuardRef = useRef(false) // one appendCycle per committed feed

  const ready = !loading && !errored && feed.length > 0

  // Extend the feed by one more full permutation, avoiding a seam repeat (the new
  // cycle must not open with the quote the feed currently ends on).
  const appendCycle = useCallback(() => {
    const pool = poolRef.current
    if (pool.length === 0) return
    setFeed((prev) => {
      let cyc = shuffle(pool)
      const lastId = prev[prev.length - 1]?.id
      if (cyc.length > 1 && cyc[0].id === lastId) {
        cyc = [cyc[1], cyc[0], ...cyc.slice(2)]
      }
      return [...prev, ...cyc]
    })
  }, [])

  // Stop the drift for good. Called on any first-touch / manual scroll.
  const pauseAuto = useCallback(() => {
    if (pausedRef.current) return
    pausedRef.current = true
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  // Smoothly centre the next card. Reads live geometry so it survives reflow.
  const advance = useCallback(() => {
    const el = scrollerRef.current
    if (!el) return
    const total = el.children.length
    const target = Math.min(currentIndexRef.current + 1, total - 1)
    const card = el.children[target] as HTMLElement | undefined
    if (!card) return
    programmaticRef.current = true
    const left = card.offsetLeft - (el.clientWidth - card.clientWidth) / 2
    el.scrollTo({ left, behavior: 'smooth' })
    window.setTimeout(() => {
      programmaticRef.current = false
    }, 700)
  }, [])

  // Track the centred card; a MANUAL scroll pauses the drift; nearing the end tops
  // up the rotation so a swipe never runs out of (or repeats) quotes.
  const onScroll = useCallback(() => {
    const el = scrollerRef.current
    if (!el) return
    const total = el.children.length
    if (total === 0) return
    const c0 = el.children[0] as HTMLElement
    const c1 = el.children[1] as HTMLElement | undefined
    const stride = c1 ? c1.offsetLeft - c0.offsetLeft : c0.clientWidth || 1
    const idx = Math.max(0, Math.min(total - 1, Math.round(el.scrollLeft / stride)))
    currentIndexRef.current = idx
    if (!programmaticRef.current) pauseAuto()
    if (idx >= total - 3 && !appendGuardRef.current) {
      appendGuardRef.current = true
      appendCycle()
    }
  }, [pauseAuto, appendCycle])

  // Re-arm the append guard once the appended cards have committed.
  useEffect(() => {
    appendGuardRef.current = false
  }, [feed.length])

  // Gentle auto-advance: one card every 6s, until the first interaction. Skipped
  // entirely under prefers-reduced-motion. Never resumes without a remount.
  useEffect(() => {
    if (!ready) return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    if (pausedRef.current) return
    const id = window.setInterval(() => {
      if (pausedRef.current) return
      const el = scrollerRef.current
      if (!el) return
      if (currentIndexRef.current >= el.children.length - 3) appendCycle()
      advance()
    }, 6000)
    intervalRef.current = id
    return () => window.clearInterval(id)
  }, [ready, advance, appendCycle])

  // ── Discuss / detail sheet (handleDiscuss reused verbatim) ────────────────────

  const [detailQuote, setDetailQuote] = useState<Quote | null>(null)
  const [startingDiscussId, setStartingDiscussId] = useState<string | null>(null)

  const showPaywall = useStore((s) => s.showPaywall)
  const paywallDetails = useStore((s) => s.paywallDetails)
  const clearPaywall = useStore((s) => s.clearPaywall)

  async function handleDiscuss(quote: Quote) {
    void api.incrementDiscuss(quote.id).catch(() => {}) // fire-and-forget demand signal
    if (startingDiscussId) return
    setStartingDiscussId(quote.id)
    try {
      const conv = await api.createConversation(quote.persona_slug)
      // Seed the composer only (read-and-cleared on chat mount) — never auto-sent.
      sessionStorage.setItem(`chat_prefill_${conv.id}`, openingFor(quote).slice(0, 600))
      router.push(`/app/chat/conv/${conv.id}`)
      // Guard intentionally stays set on the navigating path (component unmounts),
      // preventing a double-start race; it resets only on the paths below.
    } catch (err) {
      if (err instanceof Error && err.message.includes('requires plan upgrade')) {
        // Pro mind gated for a free user → the persona_locked paywall variant.
        // personaVoice carries the display name (no store.activePersonaName here).
        useStore.getState().setShowPaywall(true, {
          upgradeTarget: 'pro',
          reason: 'persona_locked',
          personaVoice: personaMap[quote.persona_slug]?.name,
        })
      } else {
        toast('Could not start the conversation. Try again in a moment.')
      }
      setStartingDiscussId(null)
    }
  }

  function handleOpen(quote: Quote) {
    void api.incrementStory(quote.id).catch(() => {}) // fire-and-forget demand signal
    setDetailQuote(quote)
  }

  // Quiet loading — a bare vellum field, no spinner (a cached GET resolves fast).
  if (loading) {
    return <main className="h-full min-h-0 bg-vellum" />
  }

  // Calm fallback for both error and the (unexpected) empty corpus — never a raw error.
  if (errored || quotes.length === 0) {
    return (
      <main className="flex h-full min-h-0 items-center justify-center bg-vellum px-[32px]">
        <p className="font-lora text-sepia text-[14px] leading-relaxed text-center">
          {errored ? 'The quotes are resting. Try again in a moment.' : 'No quotes yet.'}
        </p>
      </main>
    )
  }

  return (
    <>
      {/* h-full fills the (tabs) layout's padded content area, so the carousel sits
          ABOVE the floating tab bar (the layout reserves its footprint). Peek geometry:
          each card is 80vw (snap-center) inside 10vw side padding, so the centre card
          dominates and its neighbours peek ~10vw on each side. */}
      <main className="h-full min-h-0 bg-vellum">
        <div
          ref={scrollerRef}
          onScroll={onScroll}
          onPointerDown={pauseAuto}
          onTouchStart={pauseAuto}
          className="flex h-full snap-x snap-mandatory items-stretch gap-[8px] overflow-x-auto overflow-y-hidden overscroll-x-contain px-[10vw] py-[10px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {feed.map((q, i) => {
            const meta = personaMap[q.persona_slug]
            return (
              <div key={`${q.id}-${i}`} className="h-full w-[80vw] shrink-0 snap-center">
                <QuoteCard
                  quote={q}
                  personaName={meta?.name ?? q.persona_slug}
                  portraitUrl={meta?.portrait_url ?? null}
                  onOpen={() => handleOpen(q)}
                />
              </div>
            )
          })}
        </div>
      </main>

      {/* Detail sheet: the full quote, its (real) original, attribution, then the story
          narrative (already on the Quote — no new fetch) and a single Discuss action.
          maxHeight 85svh so long stories fit; the scroll content clears the floating
          tab bar's iOS backdrop-blur overpaint (calc(4rem+28px); the panel already
          insets safe-area, so it is NOT re-added here). */}
      <BottomSheet open={!!detailQuote} onClose={() => setDetailQuote(null)} maxHeight="85svh">
        {detailQuote && (
          <div className="overflow-y-auto px-[24px] pt-[24px] pb-[calc(4rem+28px)]">
            <p className="font-cormorant text-ink text-[24px] font-medium leading-[1.3]">
              {detailQuote.text_en}
            </p>

            {!!detailQuote.text_original && detailQuote.text_original !== detailQuote.text_en && (
              <p className="font-lora italic text-charcoal text-[15px] leading-snug mt-[10px]">
                {detailQuote.text_original}
              </p>
            )}

            <p className="font-lora text-bronze text-[11px] uppercase tracking-[0.16em] mt-[14px]">
              {personaMap[detailQuote.persona_slug]?.name ?? detailQuote.persona_slug} · {detailQuote.source_locator}
            </p>

            <div className="mt-[22px] border-t border-[0.5px] border-edge pt-[18px]">
              <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze mb-[12px]">
                The story
              </p>
              <p className="font-lora text-charcoal text-[14px] leading-relaxed whitespace-pre-line">
                {detailQuote.context}
              </p>
            </div>

            <button
              type="button"
              onClick={() => handleDiscuss(detailQuote)}
              disabled={startingDiscussId === detailQuote.id}
              className="mt-[24px] w-full h-[48px] rounded-full bg-ink text-vellum font-cormorant text-[17px] font-medium transition active:scale-[0.98] disabled:opacity-60 [touch-action:manipulation]"
            >
              Discuss this
            </button>
          </div>
        )}
      </BottomSheet>

      {/* PaywallModal is not in the (tabs) layout — render it here, wired to the same
          store selectors (no duplicated paywall logic). */}
      <PaywallModal open={showPaywall} details={paywallDetails} onClose={clearPaywall} />
    </>
  )
}
