'use client'

import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Flame, Lock, Clock } from 'lucide-react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { UpgradeBanner } from '@/components/billing/UpgradeBanner'
import toast from 'react-hot-toast'

interface Ritual {
  id: string
  slug: string
  name: string
  description: string | null
  tier: string
  frequency: string
  is_accessible: boolean
}

export default function RitualsPage() {
  const router = useRouter()
  const { subscription } = useStore()
  const plan = subscription?.plan ?? 'free'

  const { data: rituals = [], isLoading } = useQuery<Ritual[]>({
    queryKey: ['rituals'],
    queryFn: () => api.request<Ritual[]>('/rituals'),
  })

  const { data: completions = [] } = useQuery({
    queryKey: ['ritual-completions'],
    queryFn: () => api.request<any[]>('/rituals/completions'),
  })

  const handleStart = async (ritual: Ritual) => {
    if (!ritual.is_accessible) {
      router.push('/upgrade')
      return
    }
    try {
      const conv = await api.request<{ id: string }>(`/rituals/${ritual.id}/start`, { method: 'POST' })
      router.push(`/app/persona/${conv.id}`)
    } catch {
      toast.error('Could not start ritual')
    }
  }

  // Compute streak per ritual
  const streakMap = computeStreaks(completions)

  const freeRituals = rituals.filter((r) => r.tier === 'free')
  const proRituals  = rituals.filter((r) => r.tier !== 'free')

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-12">

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10"
        >
          <h1
            className="text-2xl font-medium mb-2"
            style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
          >
            Daily practice
          </h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Rituals are structured prompts that anchor philosophical practice to daily life.
          </p>
        </motion.div>

        {plan === 'free' && <UpgradeBanner className="mb-8" message="Upgrade to unlock all rituals and weekly practices." />}

        {isLoading ? (
          <RitualSkeleton />
        ) : (
          <div className="space-y-8">
            <RitualGroup
              title="Daily"
              rituals={freeRituals.filter(r => r.frequency === 'daily')}
              streakMap={streakMap}
              onStart={handleStart}
            />
            <RitualGroup
              title="Weekly"
              rituals={[...freeRituals.filter(r => r.frequency === 'weekly'), ...proRituals]}
              streakMap={streakMap}
              onStart={handleStart}
            />
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function RitualGroup({ title, rituals, streakMap, onStart }: {
  title: string
  rituals: Ritual[]
  streakMap: Record<string, number>
  onStart: (r: Ritual) => void
}) {
  if (rituals.length === 0) return null

  return (
    <section>
      <h2
        className="text-xs uppercase tracking-widest mb-4 flex items-center gap-2"
        style={{ color: 'var(--text-muted)' }}
      >
        <Clock size={11} />
        {title}
      </h2>
      <div className="space-y-3">
        {rituals.map((ritual, i) => (
          <motion.div
            key={ritual.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <RitualCard
              ritual={ritual}
              streak={streakMap[ritual.id] ?? 0}
              onStart={onStart}
            />
          </motion.div>
        ))}
      </div>
    </section>
  )
}

function RitualCard({ ritual, streak, onStart }: {
  ritual: Ritual
  streak: number
  onStart: (r: Ritual) => void
}) {
  return (
    <div
      className="flex items-start justify-between gap-4 p-5 rounded-2xl"
      style={{
        background: 'var(--bg-surface)',
        border: `1px solid ${ritual.is_accessible ? 'var(--border)' : 'var(--border)'}`,
        opacity: ritual.is_accessible ? 1 : 0.7,
      }}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            {ritual.name}
          </h3>
          {ritual.tier !== 'free' && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-wider"
              style={{ background: 'rgba(201,169,110,0.12)', color: 'var(--gold)' }}
            >
              Pro
            </span>
          )}
        </div>
        {ritual.description && (
          <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {ritual.description}
          </p>
        )}
        {streak > 0 && (
          <div className="flex items-center gap-1 mt-2 text-xs" style={{ color: 'var(--gold)' }}>
            <Flame size={11} />
            {streak} day streak
          </div>
        )}
      </div>

      <button
        onClick={() => onStart(ritual)}
        className="flex-shrink-0 flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium transition-opacity hover:opacity-80"
        style={{
          background: ritual.is_accessible ? 'var(--gold)' : 'var(--bg-secondary)',
          color: ritual.is_accessible ? '#0f0e0d' : 'var(--text-muted)',
          border: ritual.is_accessible ? 'none' : '1px solid var(--border)',
        }}
      >
        {ritual.is_accessible ? 'Begin' : <><Lock size={11} /> Unlock</>}
      </button>
    </div>
  )
}

function RitualSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-24 rounded-2xl animate-pulse"
          style={{ background: 'var(--bg-surface)' }} />
      ))}
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function computeStreaks(completions: Array<{ ritual_id: string; completed_at: string }>): Record<string, number> {
  const byRitual: Record<string, Date[]> = {}
  for (const c of completions) {
    if (!byRitual[c.ritual_id]) byRitual[c.ritual_id] = []
    byRitual[c.ritual_id].push(new Date(c.completed_at))
  }
  const result: Record<string, number> = {}
  for (const [id, dates] of Object.entries(byRitual)) {
    dates.sort((a, b) => b.getTime() - a.getTime())
    let streak = 0
    let prev = new Date()
    prev.setHours(0, 0, 0, 0)
    for (const d of dates) {
      const day = new Date(d)
      day.setHours(0, 0, 0, 0)
      const diff = Math.round((prev.getTime() - day.getTime()) / 86400000)
      if (diff <= 1) { streak++; prev = day }
      else break
    }
    result[id] = streak
  }
  return result
}
