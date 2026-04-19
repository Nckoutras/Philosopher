'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Trash2, X, Lightbulb } from 'lucide-react'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  belief:    { label: 'Belief',    color: '#8b6f47' },
  value:     { label: 'Value',     color: '#6b8b6b' },
  struggle:  { label: 'Struggle',  color: '#8b6b6b' },
  pattern:   { label: 'Pattern',   color: '#6b6b8b' },
  milestone: { label: 'Milestone', color: '#8b7f47' },
}

export default function MemoryPage() {
  const qc = useQueryClient()
  const [activeFilter, setActiveFilter] = useState<string | null>(null)

  const { data: memories = [], isLoading: memLoading } = useQuery({
    queryKey: ['memory'],
    queryFn: () => api.getMemory(),
  })

  const { data: insights = [] } = useQuery({
    queryKey: ['insights'],
    queryFn: () => api.getInsights(),
  })

  const deleteMemory = useMutation({
    mutationFn: (id: string) => api.deleteMemory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memory'] })
      toast.success('Memory removed')
    },
  })

  const dismissInsight = useMutation({
    mutationFn: (id: string) => api.dismissInsight(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['insights'] }),
  })

  const filtered = activeFilter
    ? memories.filter((m) => m.entry_type === activeFilter)
    : memories

  const types = [...new Set(memories.map((m) => m.entry_type))]

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-12">

        <div className="mb-10">
          <h1
            className="text-2xl font-medium mb-2"
            style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
          >
            Your memory
          </h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            What your companion has learned about you across conversations.
            You can delete anything here.
          </p>
        </div>

        {/* Insights */}
        <AnimatePresence>
          {insights.map((insight) => (
            <motion.div
              key={insight.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-4 px-5 py-4 rounded-2xl relative"
              style={{
                background: 'rgba(201,169,110,0.06)',
                border: '1px solid rgba(201,169,110,0.2)',
              }}
            >
              <div className="flex items-start gap-3">
                <Lightbulb size={15} className="mt-0.5 flex-shrink-0" style={{ color: 'var(--gold)' }} />
                <div className="flex-1">
                  <p className="text-xs font-medium mb-1" style={{ color: 'var(--gold)' }}>
                    {insight.insight_type ?? 'Insight'}
                  </p>
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    {insight.content}
                  </p>
                </div>
                <button
                  onClick={() => dismissInsight.mutate(insight.id)}
                  className="p-1 rounded hover:opacity-70 flex-shrink-0"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <X size={13} />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Type filters */}
        {types.length > 0 && (
          <div className="flex gap-2 flex-wrap mb-6">
            <button
              onClick={() => setActiveFilter(null)}
              className="px-3 py-1 rounded-full text-xs transition-colors"
              style={{
                background: !activeFilter ? 'var(--gold)' : 'var(--bg-surface)',
                color: !activeFilter ? '#0f0e0d' : 'var(--text-secondary)',
                border: '1px solid var(--border)',
              }}
            >
              All ({memories.length})
            </button>
            {types.map((type) => {
              const meta = TYPE_LABELS[type]
              return (
                <button
                  key={type}
                  onClick={() => setActiveFilter(type === activeFilter ? null : type)}
                  className="px-3 py-1 rounded-full text-xs transition-colors"
                  style={{
                    background: activeFilter === type ? meta?.color + '22' : 'var(--bg-surface)',
                    color: activeFilter === type ? meta?.color : 'var(--text-secondary)',
                    border: `1px solid ${activeFilter === type ? meta?.color + '44' : 'var(--border)'}`,
                  }}
                >
                  {meta?.label ?? type} ({memories.filter((m) => m.entry_type === type).length})
                </button>
              )
            })}
          </div>
        )}

        {/* Memory list */}
        {memLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-xl animate-pulse"
                style={{ background: 'var(--bg-surface)' }} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {memories.length === 0
                ? 'Your memory is empty. Start a conversation.'
                : 'No entries of this type.'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence>
              {filtered.map((entry) => {
                const meta = TYPE_LABELS[entry.entry_type]
                return (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, height: 0 }}
                    className="group flex items-start gap-3 px-4 py-3.5 rounded-xl"
                    style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
                  >
                    <span
                      className="mt-0.5 px-2 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0"
                      style={{
                        background: (meta?.color ?? '#888') + '1a',
                        color: meta?.color ?? 'var(--text-muted)',
                      }}
                    >
                      {meta?.label ?? entry.entry_type}
                    </span>
                    <p className="flex-1 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      {entry.content}
                    </p>
                    <button
                      onClick={() => deleteMemory.mutate(entry.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded transition-all hover:opacity-70 flex-shrink-0"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
