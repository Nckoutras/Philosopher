'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { WeeklyLetter, Persona } from '@/lib/api'
import AppHeader from '@/components/layout/AppHeader'
import SubPageNav from '@/components/layout/SubPageNav'
import SwipeableRow from '@/components/ui/SwipeableRow'
import DeleteConfirmModal from '@/components/ui/DeleteConfirmModal'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function formatWeekSpan(start: string, end: string): string {
  const s = new Date(start)
  const e = new Date(end)
  const sm = MONTHS[s.getUTCMonth()]
  const sd = s.getUTCDate()
  const em = MONTHS[e.getUTCMonth()]
  const ed = e.getUTCDate()
  const yr = e.getUTCFullYear()
  if (sm === em) return `${sm} ${sd}–${ed}, ${yr}`
  return `${sm} ${sd} – ${em} ${ed}, ${yr}`
}

// Monthly letters: "Month Year" (period_start is the 1st of the month, UTC).
function formatSeasonLabel(start: string): string {
  return new Date(start).toLocaleDateString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })
}

export default function LettersPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const subscription = useStore((s) => s.subscription)
  const isPro = subscription?.status === 'active' && subscription?.plan !== 'free'
  const [letters, setLetters] = useState<WeeklyLetter[] | null>(null)
  const [personas, setPersonas] = useState<Persona[]>([])
  const [query, setQuery] = useState('')
  const [revealedId, setRevealedId] = useState<string | null>(null)
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    if (!isPro) {
      router.replace('/app/upgrade')
      return
    }
    api.getWeeklyLetters()
      .then(setLetters)
      .catch(() => setLetters([]))
    // Personas drive the per-card thumbnail (slug → portrait_url, resolved live
    // so a future portrait change can't leave a stale URL on old letters). A
    // failed fetch must not break the list — fall back to initial/placeholder.
    api.getPersonas()
      .then(setPersonas)
      .catch(() => setPersonas([]))
  }, [token, isPro, router])

  const portraitBySlug = new Map(personas.map((p) => [p.slug, p.portrait_url]))

  const visible = letters?.filter((l) => l.status !== 'suppressed') ?? []
  const q = query.trim().toLowerCase()
  const searched = q
    ? visible.filter(
        (l) =>
          l.status === 'generated' &&
          ((l.payload?.title ?? '').toLowerCase().includes(q) ||
            (l.voice_persona_name ?? '').toLowerCase().includes(q) ||
            formatWeekSpan(l.period_start, l.period_end).toLowerCase().includes(q)),
      )
    : visible

  async function handleDeleteConfirm() {
    if (!pendingDeleteId) return
    setDeleteLoading(true)
    setDeleteError(null)
    try {
      await api.deleteWeeklyLetter(pendingDeleteId)
      setLetters((prev) => (prev ? prev.filter((l) => l.id !== pendingDeleteId) : prev))
      toast.success('Deleted')
      setPendingDeleteId(null)
    } catch {
      setDeleteError('Could not delete. Please try again.')
    } finally {
      setDeleteLoading(false)
    }
  }

  function handleDeleteClose() {
    if (deleteLoading) return
    setPendingDeleteId(null)
    setDeleteError(null)
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <AppHeader />

      <div className="px-[24px] pt-[22px] pb-[16px] flex items-center gap-[12px]">
        <SubPageNav fallbackHref="/app/rituals" />
        <div>
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">Rituals</p>
          <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">The Sunday Letter</h1>
        </div>
      </div>

      {letters !== null && visible.length > 0 && (
        <div className="px-[16px] pb-[12px]">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your letters"
            className="w-full bg-white border-[0.5px] border-edge rounded-[10px] px-[14px] py-[10px] font-lora text-[14px] text-ink placeholder:text-sepia/60 focus:outline-none focus:border-bronze/50"
          />
        </div>
      )}

      <div className="px-[16px] flex flex-col gap-[12px]">
        {letters === null ? (
          <>
            <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex flex-col gap-[8px]">
              <div className="h-[10px] w-[100px] bg-linen rounded animate-pulse" />
              <div className="h-[24px] w-[220px] bg-linen rounded animate-pulse" />
              <div className="h-[12px] w-[160px] bg-linen rounded animate-pulse" />
            </div>
            <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex flex-col gap-[8px]">
              <div className="h-[10px] w-[80px] bg-linen rounded animate-pulse" />
              <div className="h-[24px] w-[200px] bg-linen rounded animate-pulse" />
              <div className="h-[12px] w-[140px] bg-linen rounded animate-pulse" />
            </div>
          </>
        ) : visible.length === 0 ? (
          <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[24px] text-center">
            <p className="font-cormorant text-[19px] font-normal text-ink">Your first letter arrives Sunday.</p>
            <p className="font-lora text-[15px] text-charcoal mt-[6px] leading-[1.6]">
              After an active week, the mind you spent the most time with writes to you.
            </p>
          </div>
        ) : searched.length === 0 ? (
          <p className="px-[8px] py-[16px] font-lora text-[14px] text-sepia italic">
            No letters match &ldquo;{query.trim()}&rdquo;.
          </p>
        ) : (
          searched.map((l) => {
            if (l.status === 'generated') {
              const portrait = l.voice_persona_slug
                ? portraitBySlug.get(l.voice_persona_slug)
                : undefined
              return (
                <SwipeableRow
                  key={l.id}
                  isRevealed={revealedId === l.id}
                  onReveal={() => setRevealedId(l.id)}
                  onCollapse={() => setRevealedId(null)}
                  onDeleteRequest={() => { setRevealedId(null); setPendingDeleteId(l.id) }}
                >
                  <button
                    type="button"
                    onClick={() => router.push(`/app/letters/${l.id}`)}
                    className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px]"
                  >
                    <div className="flex items-start gap-[12px]">
                      {/* Persona thumbnail — portrait by slug, else initial, else neutral circle */}
                      <div className="w-[40px] h-[40px] rounded-full overflow-hidden flex-shrink-0 bg-linen border border-edge flex items-center justify-center">
                        {portrait ? (
                          <Image
                            src={portrait}
                            alt={l.voice_persona_name ?? ''}
                            width={40}
                            height={40}
                            className="object-cover w-full h-full"
                          />
                        ) : l.voice_persona_name ? (
                          <span className="font-cormorant text-[18px] font-medium text-charcoal">
                            {l.voice_persona_name.charAt(0)}
                          </span>
                        ) : null}
                      </div>
                      <div className="flex-1 min-w-0 flex items-start justify-between gap-[8px]">
                      <div className="flex-1 min-w-0">
                        {l.kind === 'monthly' ? (
                          <div className="flex items-center gap-[8px]">
                            <span className="font-lora text-[10px] uppercase tracking-[0.16em] text-bronze border border-[0.5px] border-bronze rounded-[3px] px-[6px] py-[1px]">
                              Season
                            </span>
                            <span className="font-lora text-[11px] uppercase tracking-[0.14em] text-sepia">
                              {formatSeasonLabel(l.period_start)}
                            </span>
                          </div>
                        ) : (
                          <p className="font-lora text-[11px] uppercase tracking-[0.14em] text-sepia">
                            {formatWeekSpan(l.period_start, l.period_end)}
                          </p>
                        )}
                        <p className="font-cormorant text-[19px] font-medium text-ink leading-tight mt-[4px]">
                          {l.payload?.title ?? 'A letter for you'}
                        </p>
                        {l.voice_persona_name && (
                          <p className="font-lora text-[13px] text-charcoal mt-[4px]">
                            in the voice of {l.voice_persona_name}
                          </p>
                        )}
                      </div>
                      {l.read_at === null && (
                        <div className="w-[8px] h-[8px] rounded-full bg-bronze flex-shrink-0 mt-[6px]" />
                      )}
                      </div>
                    </div>
                  </button>
                </SwipeableRow>
              )
            }
            return (
              <div key={l.id} className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] opacity-60">
                <p className="font-lora text-[11px] uppercase tracking-[0.14em] text-sepia">
                  {formatWeekSpan(l.period_start, l.period_end)}
                </p>
                <p className="font-cormorant text-[17px] text-charcoal mt-[4px]">
                  A quiet week — no letter this time.
                </p>
              </div>
            )
          })
        )}
      </div>

      <DeleteConfirmModal
        open={pendingDeleteId !== null}
        title="Delete this letter?"
        body="This can't be undone."
        loading={deleteLoading}
        error={deleteError}
        onConfirm={handleDeleteConfirm}
        onClose={handleDeleteClose}
      />
    </main>
  )
}
