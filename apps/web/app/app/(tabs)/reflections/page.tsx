'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
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
  const [pendingDeletes, setPendingDeletes] = useState<Set<string>>(new Set())
  const deleteTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
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
    const timers = deleteTimersRef.current
    return () => {
      timers.forEach((t) => clearTimeout(t))
      timers.clear()
    }
  }, [])

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }
    load()
  }, [token, router, load])

  function handleDelete(savedLineId: string, messageId: string) {
    setPendingDeletes((prev) => new Set(prev).add(savedLineId))

    const timer = setTimeout(async () => {
      try {
        await api.deleteSavedLine(savedLineId)
        useStore.getState().removeAfterDelete(savedLineId, messageId)
      } catch {
        setPendingDeletes((prev) => {
          const next = new Set(prev)
          next.delete(savedLineId)
          return next
        })
        toast.error('Could not delete. Try again.')
      } finally {
        deleteTimersRef.current.delete(savedLineId)
      }
    }, 5000)
    deleteTimersRef.current.set(savedLineId, timer)

    toast.custom(
      (t) => (
        <div className="bg-ink text-vellum font-lora text-[13px] rounded-sm px-[16px] py-[12px] flex items-center gap-[16px]">
          <span>Deleted reflection</span>
          <button
            type="button"
            onClick={() => {
              const pending = deleteTimersRef.current.get(savedLineId)
              if (pending) {
                clearTimeout(pending)
                deleteTimersRef.current.delete(savedLineId)
              }
              setPendingDeletes((prev) => {
                const next = new Set(prev)
                next.delete(savedLineId)
                return next
              })
              toast.dismiss(t.id)
            }}
            className="font-cormorant text-[15px] font-medium underline underline-offset-2 decoration-[0.5px]"
          >
            Undo
          </button>
        </div>
      ),
      { duration: 5000 },
    )
  }

  const visibleSavedLines = savedLines.filter((sl) => !pendingDeletes.has(sl.id))

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
                        onDelete={() => handleDelete(item.id, item.message_id)}
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
    </main>
  )
}
