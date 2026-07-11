'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Quote } from '@/lib/api'
import QuoteCard from '@/components/quotes/QuoteCard'

type PersonaMeta = { name: string; portrait_url: string | null }

// Fisher-Yates — pure, called exactly once per mount (post-fetch, in load()).
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
  const [personaMap, setPersonaMap] = useState<Record<string, PersonaMeta>>({})
  const [loading, setLoading] = useState(true)
  const [errored, setErrored] = useState(false)

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
        // Shuffle ONCE, post-fetch. load() runs a single time per mount, so the
        // order is stable across re-renders and only reshuffles on remount
        // (i.e. re-entering the tab).
        setQuotes(shuffle(quoteList))
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
    // h-full fills the (tabs) layout's padded content area, so the carousel sits
    // ABOVE the floating tab bar (the layout reserves its footprint).
    <main className="h-full min-h-0 bg-vellum">
      <div className="flex h-full snap-x snap-mandatory overflow-x-auto overflow-y-hidden overscroll-x-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {quotes.map((q) => {
          const meta = personaMap[q.persona_slug]
          return (
            <div key={q.id} className="h-full w-full shrink-0 snap-center">
              <QuoteCard
                quote={q}
                personaName={meta?.name ?? q.persona_slug}
                portraitUrl={meta?.portrait_url ?? null}
              />
            </div>
          )
        })}
      </div>
    </main>
  )
}
