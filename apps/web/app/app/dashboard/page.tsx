'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { PersonaSelector } from '@/components/persona/PersonaSelector'
import { UpgradeBanner } from '@/components/billing/UpgradeBanner'

export default function DashboardPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { user } = useStore()
  const plan = useStore((s) => s.subscription?.plan ?? 'free')

  const { data: personas = [], isLoading } = useQuery({
    queryKey: ['personas'],
    queryFn: () => api.getPersonas(),
  })

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => api.getConversations(),
  })

  const handleSelectPersona = async (persona: typeof personas[number]) => {
    try {
      const conv = await api.createConversation(persona.slug)
      await queryClient.invalidateQueries({ queryKey: ['conversations'] })
      router.push(`/app/persona/${conv.id}`)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-12">

        {/* Greeting */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-10"
        >
          <h1
            className="text-2xl font-medium mb-2"
            style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
          >
            Good{getTimeOfDay()},{' '}
            <span style={{ color: 'var(--gold)' }}>
              {user?.full_name?.split(' ')[0] ?? 'friend'}
            </span>
            .
          </h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Who do you want to think with today?
          </p>
        </motion.div>

        {/* Upgrade banner for free users */}
        {plan === 'free' && <UpgradeBanner className="mb-8" />}

        {/* Persona selection */}
        {isLoading ? (
          <PersonaSkeleton />
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            <PersonaSelector
              personas={personas}
              onSelect={handleSelectPersona}
              onUpgrade={() => router.push('/upgrade')}
            />
          </motion.div>
        )}

        {/* Recent conversations */}
        {conversations.length > 0 && (
          <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="mt-12"
          >
            <h2
              className="text-xs uppercase tracking-widest mb-4"
              style={{ color: 'var(--text-muted)' }}
            >
              Recent
            </h2>
            <div className="space-y-1">
              {conversations.slice(0, 5).map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => router.push(`/app/persona/${conv.id}`)}
                  className="w-full text-left px-4 py-3 rounded-xl text-sm transition-colors hover:bg-[var(--bg-surface)]"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  <span className="mr-2">{conv.persona.avatar_emoji}</span>
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    {conv.persona.name}
                  </span>
                  <span className="ml-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                    {conv.message_count} turns ·{' '}
                    {conv.last_message_at
                      ? new Date(conv.last_message_at).toLocaleDateString()
                      : ''}
                  </span>
                </button>
              ))}
            </div>
          </motion.section>
        )}
      </div>
    </div>
  )
}

function getTimeOfDay() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}

function PersonaSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2].map((i) => (
        <div
          key={i}
          className="h-28 rounded-2xl animate-pulse"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
        />
      ))}
    </div>
  )
}
