'use client'

import { useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api, type Persona } from '@/lib/api'
import ConversationList from '@/components/library/ConversationList'

export default function LibraryPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const conversations = useStore((s) => s.conversations)
  const loading = useStore((s) => s.conversationsLoading)
  const error = useStore((s) => s.conversationsError)
  const setConversations = useStore((s) => s.setConversations)
  const setLoading = useStore((s) => s.setConversationsLoading)
  const setError = useStore((s) => s.setConversationsError)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [convs, personas] = await Promise.all([
        api.getConversations(),
        api.getPersonas(),
      ])
      const bySlug = personas.reduce<Record<string, Persona>>((m, p) => { m[p.slug] = p; return m }, {})
      // Merge portrait_url from full persona data
      const enriched = convs.map((c) => ({
        ...c,
        persona: { ...c.persona, portrait_url: bySlug[c.persona.slug]?.portrait_url ?? '' },
      }))
      setConversations(enriched)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Could not load conversations'))
    } finally {
      setLoading(false)
    }
  }, [setConversations, setLoading, setError])

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }
    load()
  }, [token, router, load])

  // Build portrait map from enriched conversations
  const enrichedPortraitMap = conversations.reduce<Record<string, string>>((acc, c) => {
    if (c.persona.portrait_url) acc[c.persona.slug] = c.persona.portrait_url
    return acc
  }, {})

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      {/* Header */}
      <header className="px-6 pt-6 pb-2">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-1">
          Library
        </p>
        <h1 className="font-cormorant text-[26px] font-normal text-ink leading-tight">
          Past conversations.
        </h1>
      </header>

      <div className="flex-1">
        <ConversationList
          conversations={conversations}
          portraitUrlsBySlug={enrichedPortraitMap}
          loading={loading}
          error={error}
          onRetry={load}
        />
      </div>
    </main>
  )
}
