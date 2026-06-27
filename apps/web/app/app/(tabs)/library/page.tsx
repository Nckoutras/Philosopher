'use client'

import { Suspense, useEffect, useCallback, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Image from 'next/image'
import { ChevronRight } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api, type Persona, type LastConversation } from '@/lib/api'
import PastConversationsView from '@/components/library/PastConversationsView'
import BrowseMindsView from '@/components/library/BrowseMindsView'
import AppHeader from '@/components/layout/AppHeader'

function LibraryContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = (searchParams.get('mode') ?? 'past') as 'past' | 'browse'

  const token = useStore((s) => s.token)
  const conversations = useStore((s) => s.conversations)
  const loading = useStore((s) => s.conversationsLoading)
  const error = useStore((s) => s.conversationsError)
  const setConversations = useStore((s) => s.setConversations)
  const setLoading = useStore((s) => s.setConversationsLoading)
  const setError = useStore((s) => s.setConversationsError)

  const [personas, setPersonas] = useState<Persona[] | null>(null)
  const [lastConv, setLastConv] = useState<LastConversation | null>(null)

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
      // Non-critical: the "Continuing." card just won't render if this fails.
      try {
        setLastConv(await api.getLastConversation())
      } catch {
        setLastConv(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Could not load'))
    } finally {
      setLoading(false)
    }
  }, [setConversations, setLoading, setError])

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    load()
  }, [token, router, load])

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
        <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
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

      {/* ── Continuing. card (returning user) — relocated from Home ── */}
      {mode === 'past' && lastConv && (
        <div className="px-[16px] pb-[12px]">
          <button
            type="button"
            onClick={() => router.push(`/app/chat/conv/${lastConv.conversation_id}`)}
            className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px] flex items-start gap-[12px]"
          >
            <div className="flex-shrink-0">
              {lastConv.persona_portrait_url ? (
                <Image
                  src={lastConv.persona_portrait_url}
                  alt={lastConv.persona_name}
                  width={64}
                  height={64}
                  className="rounded-[2px] object-cover"
                />
              ) : (
                <div className="w-[64px] h-[64px] bg-linen rounded-[2px] flex items-center justify-center">
                  <span className="font-cormorant text-[24px] font-medium text-charcoal">
                    {lastConv.persona_name.charAt(0)}
                  </span>
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal mb-[4px]">
                Continuing.
              </p>
              <p className="font-cormorant text-[20px] font-medium text-ink leading-tight">
                {lastConv.persona_name}
              </p>
              {lastConv.last_message_snippet && (
                <p className="font-lora text-[13px] text-charcoal leading-snug mt-[6px] line-clamp-2">
                  &ldquo;{lastConv.last_message_snippet}&rdquo;
                </p>
              )}
            </div>
            <ChevronRight size={16} strokeWidth={1.5} className="text-sepia flex-shrink-0 self-center" />
          </button>
        </div>
      )}

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
