'use client'

import { Suspense, useEffect, useCallback, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api, type Persona } from '@/lib/api'
import PastConversationsView from '@/components/library/PastConversationsView'
import BrowseMindsView from '@/components/library/BrowseMindsView'
import AppHeader from '@/components/layout/AppHeader'

function LibraryContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = (searchParams.get('mode') ?? 'past') as 'past' | 'browse'

  const token = useStore((s) => s.token)
  const _hasHydrated = useStore((s) => s._hasHydrated)
  const conversations = useStore((s) => s.conversations)
  const loading = useStore((s) => s.conversationsLoading)
  const error = useStore((s) => s.conversationsError)
  const setConversations = useStore((s) => s.setConversations)
  const setLoading = useStore((s) => s.setConversationsLoading)
  const setError = useStore((s) => s.setConversationsError)

  const [personas, setPersonas] = useState<Persona[] | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [convs, allPersonas] = await Promise.all([
        api.getConversations(),
        api.getPersonas(),
      ])
      setPersonas(allPersonas)
      const bySlug = allPersonas.reduce<Record<string, Persona>>((m, p) => {
        m[p.slug] = p
        return m
      }, {})
      const enriched = convs.map((c) => ({
        ...c,
        persona: { ...c.persona, portrait_url: bySlug[c.persona.slug]?.portrait_url ?? '' },
      }))
      setConversations(enriched)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Could not load'))
    } finally {
      setLoading(false)
    }
  }, [setConversations, setLoading, setError])

  useEffect(() => {
    if (!_hasHydrated) return
    if (token === null) {
      router.replace('/auth')
      return
    }
    load()
  }, [_hasHydrated, token, router, load])

  const portraitUrlsBySlug = conversations.reduce<Record<string, string>>((acc, c) => {
    if (c.persona.portrait_url) acc[c.persona.slug] = c.persona.portrait_url
    return acc
  }, {})

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <AppHeader />
      {/* Header */}
      <header className="px-6 pt-6 pb-2">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-1">
          Library
        </p>
        <h1 className="font-cormorant text-[26px] font-normal text-ink leading-tight">
          {mode === 'browse' ? 'Explore minds.' : 'Past conversations.'}
        </h1>
      </header>

      {/* Mode toggle */}
      <div className="flex gap-2 px-4 pb-3">
        <button
          type="button"
          onClick={() => router.push('/app/library')}
          className={
            mode === 'past'
              ? 'px-3 py-[5px] bg-ink text-vellum rounded-[4px] font-lora text-[12px]'
              : 'px-3 py-[5px] text-sepia font-lora text-[12px]'
          }
        >
          Past Conversations
        </button>
        <button
          type="button"
          onClick={() => router.push('/app/library?mode=browse')}
          className={
            mode === 'browse'
              ? 'px-3 py-[5px] bg-ink text-vellum rounded-[4px] font-lora text-[12px]'
              : 'px-3 py-[5px] text-sepia font-lora text-[12px]'
          }
        >
          Browse Minds
        </button>
      </div>

      <div className="flex-1">
        {mode === 'browse' ? (
          <BrowseMindsView personas={personas} loading={loading} />
        ) : (
          <PastConversationsView
            conversations={conversations}
            portraitUrlsBySlug={portraitUrlsBySlug}
            loading={loading}
            error={error}
            onRetry={load}
          />
        )}
      </div>
    </main>
  )
}

export default function LibraryPage() {
  return (
    <Suspense fallback={<main className="min-h-screen [min-height:100svh] bg-vellum" />}>
      <LibraryContent />
    </Suspense>
  )
}
