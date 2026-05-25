'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { differenceInCalendarDays } from 'date-fns'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { SavedLineRead } from '@/lib/api'
import SavedLineCard from '@/components/reflections/SavedLineCard'
import DateGrouper from '@/components/reflections/DateGrouper'
import FilterPills, { type FilterOption } from '@/components/reflections/FilterPills'
import EmptyReflections from '@/components/reflections/EmptyReflections'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import AppHeader from '@/components/layout/AppHeader'
import SwipeableRow from '@/components/ui/SwipeableRow'
import DeleteConfirmModal from '@/components/ui/DeleteConfirmModal'

function groupLabel(savedAt: string): 'This week' | 'Earlier' {
  const days = differenceInCalendarDays(new Date(), new Date(savedAt))
  if (days <= 6) return 'This week'
  return 'Earlier'
}

function groupItems(items: SavedLineRead[]): Array<{ label: 'This week' | 'Earlier'; items: SavedLineRead[] }> {
  const groups: Record<'This week' | 'Earlier', SavedLineRead[]> = { 'This week': [], Earlier: [] }
  const order: Array<'This week' | 'Earlier'> = []
  for (const item of items) {
    const label = groupLabel(item.saved_at)
    if (!order.includes(label)) order.push(label)
    groups[label].push(item)
  }
  return order.map((label) => ({ label, items: groups[label] }))
}

export default function ReflectionsPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const savedLines = useStore((s) => s.savedLines)
  const loading = useStore((s) => s.savedLinesLoading)
  const error = useStore((s) => s.savedLinesError)
  const loadSavedLines = useStore((s) => s.loadSavedLines)

  const [activeFilter, setActiveFilter] = useState<FilterOption>('all')
  const [selectedPersonaSlug, setSelectedPersonaSlug] = useState<string | null>(null)
  const [portraitBySlug, setPortraitBySlug] = useState<Record<string, string>>({})
  const [pickerLine, setPickerLine] = useState<SavedLineRead | null>(null)
  const [revealedRowId, setRevealedRowId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<{ id: string; messageId: string } | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [isFirstReflectionsRender] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return !sessionStorage.getItem('swipe_hint_seen_reflections')
  })

  const load = useCallback(async () => {
    const [, personas] = await Promise.all([loadSavedLines(), api.getPersonas()])
    const map = personas.reduce<Record<string, string>>((acc, p) => {
      acc[p.slug] = p.portrait_url
      return acc
    }, {})
    setPortraitBySlug(map)
  }, [loadSavedLines])

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

  function handleDeleteRequest(id: string, messageId: string) {
    setRevealedRowId(null)
    setPendingDelete({ id, messageId })
  }

  async function handleDeleteConfirm() {
    if (!pendingDelete) return
    setDeleteLoading(true)
    setDeleteError(null)
    try {
      await api.deleteSavedLine(pendingDelete.id)
      useStore.getState().removeAfterDelete(pendingDelete.id, pendingDelete.messageId)
      toast.success('Deleted')
      setPendingDelete(null)
    } catch {
      setDeleteError('Could not delete. Please try again.')
    } finally {
      setDeleteLoading(false)
    }
  }

  function handleDeleteClose() {
    if (deleteLoading) return
    setPendingDelete(null)
    setDeleteError(null)
  }

  const visibleSavedLines = savedLines

  const uniquePersonas = Array.from(
    new Map(
      visibleSavedLines.map((l) => [
        l.persona_slug,
        { slug: l.persona_slug, display_name: l.persona_display_name },
      ]),
    ).values(),
  )

  const filtered =
    activeFilter === 'by-mind' && selectedPersonaSlug
      ? visibleSavedLines.filter((l) => l.persona_slug === selectedPersonaSlug)
      : visibleSavedLines

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
        <h1 className="font-cormorant text-[26px] font-normal text-ink leading-tight">
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
          {visibleSavedLines.length > 0 && (
            <FilterPills
              active={activeFilter}
              personas={uniquePersonas}
              selectedPersonaSlug={selectedPersonaSlug}
              onChange={handleFilterChange}
            />
          )}
          {visibleSavedLines.length === 0 ? (
            <EmptyReflections
              onStartConversation={() => router.push('/app/library')}
            />
          ) : (
            <div className="flex-1 overflow-y-auto px-[16px] pb-[80px]">
              {grouped.map(({ label, items }, groupIdx) => (
                <div key={label}>
                  <DateGrouper label={label} />
                  {items.map((item, itemIdx) => (
                    <div key={item.id} className="mb-[8px]">
                      <SwipeableRow
                        isRevealed={revealedRowId === item.id}
                        onReveal={() => setRevealedRowId(item.id)}
                        onCollapse={() => setRevealedRowId(null)}
                        onDeleteRequest={() => handleDeleteRequest(item.id, item.message_id)}
                        showHint={isFirstReflectionsRender && groupIdx === 0 && itemIdx === 0}
                      >
                        <SavedLineCard
                          item={item}
                          portraitUrl={portraitBySlug[item.persona_slug] ?? ''}
                          onClick={() =>
                            router.push(
                              `/app/chat/conv/${item.conversation_id}`,
                            )
                          }
                          onAskAnotherMind={() => setPickerLine(item)}
                        />
                      </SwipeableRow>
                    </div>
                  ))}
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
            setPickerLine(null)
            router.push(`/app/chat/conv/${id}`)
          }}
        />
      )}

      <DeleteConfirmModal
        open={pendingDelete !== null}
        title="Delete reflection?"
        body="This can't be undone."
        loading={deleteLoading}
        error={deleteError}
        onConfirm={handleDeleteConfirm}
        onClose={handleDeleteClose}
      />
    </main>
  )
}
