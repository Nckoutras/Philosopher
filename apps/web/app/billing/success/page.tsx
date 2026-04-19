'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

export default function BillingSuccessPage() {
  const router = useRouter()
  const { setSubscription } = useStore()

  // Refresh subscription after redirect from Stripe
  const { data: sub, isLoading } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => api.getSubscription(),
    refetchInterval: 2000,   // poll until Stripe webhook lands
    refetchIntervalInBackground: true,
  })

  useEffect(() => {
    if (sub && sub.status === 'active' && sub.plan !== 'free') {
      setSubscription(sub)
    }
  }, [sub, setSubscription])

  return (
    <div
      className="min-h-dvh flex items-center justify-center px-4"
      style={{ background: 'var(--bg-primary)' }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="text-center max-w-sm"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.15, type: 'spring', stiffness: 200 }}
          className="text-5xl mb-6"
        >
          ⚗️
        </motion.div>

        <h1
          className="text-2xl font-medium mb-3"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
        >
          Welcome to Pro.
        </h1>

        <p className="text-sm mb-8" style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          All philosophers, long-term memory, and daily rituals are now yours.
          Your practice begins now.
        </p>

        {/* Plan badge */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-8"
          style={{
            background: 'rgba(201,169,110,0.1)',
            border: '1px solid rgba(201,169,110,0.3)',
            color: 'var(--gold)',
          }}
        >
          <span className="text-sm font-medium capitalize">{sub?.plan ?? 'Pro'}</span>
          {isLoading && (
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--gold)] animate-pulse" />
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <button
            onClick={() => router.push('/app/dashboard')}
            className="px-6 py-2.5 rounded-xl text-sm font-medium transition-opacity hover:opacity-80"
            style={{ background: 'var(--gold)', color: '#0f0e0d' }}
          >
            Begin thinking
          </button>
        </motion.div>
      </motion.div>
    </div>
  )
}
