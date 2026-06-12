'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { differenceInCalendarDays } from 'date-fns'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { ReflectionFeedItem } from '@/lib/api'
import SavedLineCard from '@/components/reflections/SavedLineCard'
import MirrorVerdictCard from '@/components/reflections/MirrorVerdictCard'
import CouncilVerdictCard from '@/components/reflections/CouncilVerdictCard'
import DateGrouper from '@/components/reflections/DateGrouper'
import FilterPills, { type FilterOption } from '@/components/reflections/FilterPills'
import EmptyReflections from '@/components/reflections/EmptyReflections'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import AppHeader from '@/components/layout/AppHeader'
import SwipeableRow from '@/components/ui/SwipeableRow'
import DeleteConfirmModal from '@/components/ui/DeleteConfirmModal'

// Pending-delete is generic over the three feed kinds so one confirm modal
// serves all of them. Lines hit DELETE /saved-lines; verdicts hit the existing
// DELETE /mirrors|council save endpoints.
type PendingDelete =
  | { kind: 'line'; id: string; messageId: string }
  | { kind: 'mirror_verdict'; mirrorId: string }
  | { kind: 'council_verdict'; sessionId: string }

function groupLabel(savedAt: string): 'This week' | 'Earlier' {
  const days = differenceInCalendarDays(new Date(), new Date(savedAt))
  if (days <= 6) return 'This week'
  return 'Earlier'
}

function groupItems(items: ReflectionFeedItem[]): Array<{ label: 'This week' | 'Earlier'; items: ReflectionFeedItem[] }> {
  const groups: Record<'This week' | 'Earlier', ReflectionFeedItem[]> = { 'This week': [], Earlier: [] }
  const order: Array<'This week' | 'Earlier'> = []
  for (const item of items) {
    const label = groupLabel(item.saved_at)
    if (!order.includes(label)) order.push(label)
    groups[label].push(item)
  }
  return order.map((label) => ({ label, items: groups[label] }))
}

function itemKey(item: ReflectionFeedItem): string {
  if (item.kind === 'line') return `line:${item.id}`
  if (item.kind === 'mirror_verdict') return `mirror:${item.save_id}`
  return `council:${item.save_id}`
}

export default function ReflectionsPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const feedItems = useStore((s) => s.feedItems)
  const loading = useStore((s) => s.feedLoading)
  const error = useStore((s) => s.feedError)
  const loadReflectionsFeed = useStore((s) => s.loadReflectionsFeed)

  const [activeFilter, setActiveFilter] = useState<FilterOption>('all')
  const [selectedPersonaSlug, setSelectedPersonaSlug] = useState<string | null>(null)
  const [portraitBySlug, setPortraitBySlug] = useState<Record<string, string>>({})
  const [pickerLine, setPickerLine] = useState<Extract<ReflectionFeedItem, { kind: 'line' }> | null>(null)
  const [revealedRowId, setRevealedRowId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [isFirstReflectionsRender] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return !sessionStorage.getItem('swipe_hint_seen_reflections')
  })

  const load = useCallback(async () => {
    const [, personas] = await Promise.all([loadReflectionsFeed(), api.getPersonas()])
    const map = personas.reduce<Record<string, string>>((acc, p) => {
      acc[p.slug] = p.portrait_url
      return acc
    }, {})
    setPortraitBySlug(map)
  }, [loadReflectionsFeed])

  useEffect(() => {
    if (isFirstReflectionsRender) {
      sessionStorage.setItem('swipe_hint_seen_reflections', '1')
    }
  }, [isFirstReflectionsRender])

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    load()
  }, [token, router, load])

  async function handleDeleteConfirm() {
    if (!pendingDelete) return
    setDeleteLoading(true)
    setDeleteError(null)
    try {
      if (pendingDelete.kind === 'line') {
        await api.deleteSavedLine(pendingDelete.id)
        useStore.getState().removeFeedLine(pendingDelete.id, pendingDelete.messageId)
      } else if (pendingDelete.kind === 'mirror_verdict') {
        await api.unsaveMirror(pendingDelete.mirrorId)
        useStore.getState().removeFeedMirror(pendingDelete.mirrorId)
      } else {
        await api.unsaveCouncil(pendingDelete.sessionId)
        useStore.getState().removeFeedCouncil(pendingDelete.sessionId)
      }
      toast.success(pendingDelete.kind === 'line' ? 'Deleted' : 'Removed')
      setPendingDelete(null)
    } catch {
      setDeleteError('Could not remove. Please try again.')
    } finally {
      setDeleteLoading(false)
    }
  }

  function handleDeleteClose() {
    if (deleteLoading) return
    setPendingDelete(null)
    setDeleteError(null)
  }

  // Persona pills derive from line items only — a verdict isn't a single mind.
  const uniquePersonas = Array.from(
    new Map(
      feedItems
        .filter((i): i is Extract<ReflectionFeedItem, { kind: 'line' }> => i.kind === 'line')
        .map((l) => [l.persona_slug, { slug: l.persona_slug, display_name: l.persona_display_name }]),
    ).values(),
  )

  // DECISION 1: with a persona filter active, verdict cards are hidden and only
  // that persona's lines remain. 'all' shows every kind.
  const filtered =
    activeFilter === 'by-mind' && selectedPersonaSlug
      ? feedItems.filter((i) => i.kind === 'line' && i.persona_slug === selectedPersonaSlug)
      : feedItems

  const grouped = groupItems(filtered)

  function handleFilterChange(filter: FilterOption, personaSlug?: string) {
    setActiveFilter(filter)
    if (filter === 'by-mind' && personaSlug) {
      setSelectedPersonaSlug(personaSlug)
    } else if (filter !== 'by-mind') {
      setSelectedPersonaSlug(null)
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] flex items-center justify-center bg-vellum">
        <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <AppHeader />
      <header className="px-[24px] pt-[22px] pb-[16px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-1">
          Reflections
        </p>
        <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
          Your saved lines.
        </h1>
      </header>

      {error ? (
        <div className="px-[16px]">
          <p className="font-lora text-[13px] text-sepia mb-3">Could not load reflections.</p>
          <button
            type="button"
            onClick={() => load()}
            className="font-lora text-[13px] text-sepia underline"
          >
            Try again
          </button>
        </div>
      ) : (
        <>
          {feedItems.length > 0 && (
            <FilterPills
              active={activeFilter}
              personas={uniquePersonas}
              selectedPersonaSlug={selectedPersonaSlug}
              onChange={handleFilterChange}
            />
          )}
          {feedItems.length === 0 ? (
            <EmptyReflections
              onStartConversation={() => router.push('/app/library')}
            />
          ) : (
            <div className="flex-1 overflow-y-auto px-[16px] pb-[80px]">
              {grouped.map(({ label, items }, groupIdx) => (
                <div key={label}>
                  <DateGrouper label={label} />
                  {items.map((item, itemIdx) => {
                    const key = itemKey(item)
                    return (
                      <div key={key} className="mb-[8px]">
                        <SwipeableRow
                          isRevealed={revealedRowId === key}
                          onReveal={() => setRevealedRowId(key)}
                          onCollapse={() => setRevealedRowId(null)}
                          onDeleteRequest={() => {
                            setRevealedRowId(null)
                            if (item.kind === 'line') {
                              setPendingDelete({ kind: 'line', id: item.id, messageId: item.message_id })
                            } else if (item.kind === 'mirror_verdict') {
                              setPendingDelete({ kind: 'mirror_verdict', mirrorId: item.mirror_id })
                            } else {
                              setPendingDelete({ kind: 'council_verdict', sessionId: item.session_id })
                            }
                          }}
                          showHint={isFirstReflectionsRender && groupIdx === 0 && itemIdx === 0}
                        >
                          {item.kind === 'line' ? (
                            <SavedLineCard
                              item={item}
                              portraitUrl={portraitBySlug[item.persona_slug] ?? ''}
                              onClick={() => router.push(`/app/chat/conv/${item.conversation_id}`)}
                              onAskAnotherMind={() => setPickerLine(item)}
                            />
                          ) : item.kind === 'mirror_verdict' ? (
                            <MirrorVerdictCard
                              item={item}
                              portraitUrl={item.host_persona_slug ? (portraitBySlug[item.host_persona_slug] ?? '') : ''}
                            />
                          ) : (
                            <CouncilVerdictCard item={item} portraitBySlug={portraitBySlug} />
                          )}
                        </SwipeableRow>
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {pickerLine && (
        <PersonaPickerSheet
          open={pickerLine !== null}
          excludeSlug={pickerLine.persona_slug}
          savedLineId={pickerLine.id}
          sourceContent={pickerLine.message_content}
          onClose={() => setPickerLine(null)}
          onCreated={(id) => {
            router.push(`/app/chat/conv/${id}`)
            setPickerLine(null)
          }}
        />
      )}

      <DeleteConfirmModal
        open={pendingDelete !== null}
        title={pendingDelete?.kind === 'line' ? 'Delete reflection?' : 'Remove from saved?'}
        body="This can't be undone."
        loading={deleteLoading}
        error={deleteError}
        onConfirm={handleDeleteConfirm}
        onClose={handleDeleteClose}
      />
    </main>
  )
}
