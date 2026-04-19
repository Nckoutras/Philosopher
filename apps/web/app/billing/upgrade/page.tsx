'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Check, ArrowLeft } from 'lucide-react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import toast from 'react-hot-toast'

const FEATURES = {
  free: [
    'Marcus Aurelius (Stoicism)',
    '1 additional free persona',
    '3 daily rituals',
    'Basic conversation',
  ],
  pro: [
    'All 6+ personas',
    'Long-term memory across sessions',
    'Pattern insights & analysis',
    'Unlimited rituals',
    'Email ritual reminders',
    'Priority response speed',
  ],
}

export default function UpgradePage() {
  const router = useRouter()
  const { subscription } = useStore()
  const [interval, setInterval] = useState<'monthly' | 'yearly'>('yearly')
  const [loading, setLoading] = useState(false)

  const currentPlan = subscription?.plan ?? 'free'

  const handleUpgrade = async (plan: string) => {
    setLoading(true)
    try {
      const { checkout_url } = await api.createCheckout(plan, interval)
      window.location.href = checkout_url
    } catch (e) {
      toast.error('Could not start checkout. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-dvh" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-3xl mx-auto px-6 py-16">

        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-sm mb-12 transition-opacity hover:opacity-70"
          style={{ color: 'var(--text-muted)' }}
        >
          <ArrowLeft size={14} />
          Back
        </button>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1
            className="text-3xl font-medium mb-3"
            style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
          >
            Think deeper
          </h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Access all philosophers, long-term memory, and daily rituals.
          </p>

          {/* Interval toggle */}
          <div
            className="inline-flex items-center gap-1 mt-6 p-1 rounded-xl"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
          >
            {(['monthly', 'yearly'] as const).map((opt) => (
              <button
                key={opt}
                onClick={() => setInterval(opt)}
                className="px-4 py-1.5 rounded-lg text-sm transition-all"
                style={{
                  background: interval === opt ? 'var(--gold)' : 'transparent',
                  color: interval === opt ? '#0f0e0d' : 'var(--text-secondary)',
                  fontWeight: interval === opt ? 500 : 400,
                }}
              >
                {opt === 'monthly' ? 'Monthly' : 'Yearly'}
                {opt === 'yearly' && (
                  <span className="ml-1.5 text-[10px] opacity-80">–2 months free</span>
                )}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Plan cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* Free */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="rounded-2xl p-6"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
          >
            <div className="mb-6">
              <p className="text-xs uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>Free</p>
              <p className="text-3xl font-medium" style={{ color: 'var(--text-primary)' }}>$0</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>forever</p>
            </div>
            <ul className="space-y-2.5 mb-8">
              {FEATURES.free.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
                  <Check size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                  {f}
                </li>
              ))}
            </ul>
            <div
              className="w-full py-2.5 rounded-xl text-sm text-center"
              style={{ color: 'var(--text-muted)', border: '1px solid var(--border)' }}
            >
              {currentPlan === 'free' ? 'Current plan' : 'Downgrade'}
            </div>
          </motion.div>

          {/* Pro */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="rounded-2xl p-6 relative overflow-hidden"
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--gold)',
              boxShadow: '0 0 0 1px rgba(201,169,110,0.15)',
            }}
          >
            {/* Glow */}
            <div
              className="absolute inset-0 opacity-5 pointer-events-none"
              style={{ background: 'radial-gradient(ellipse at top, var(--gold), transparent 70%)' }}
            />

            <div className="mb-6">
              <p className="text-xs uppercase tracking-widest mb-1" style={{ color: 'var(--gold)' }}>Pro</p>
              <p className="text-3xl font-medium" style={{ color: 'var(--text-primary)' }}>
                {interval === 'monthly' ? '$12' : '$99'}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                {interval === 'monthly' ? 'per month' : 'per year · $8.25/mo'}
              </p>
              <p className="text-xs mt-1.5" style={{ color: 'var(--gold)' }}>7-day free trial</p>
            </div>

            <ul className="space-y-2.5 mb-8">
              {FEATURES.pro.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
                  <Check size={13} style={{ color: 'var(--gold)', flexShrink: 0 }} />
                  {f}
                </li>
              ))}
            </ul>

            <button
              onClick={() => handleUpgrade('pro')}
              disabled={loading || currentPlan === 'pro'}
              className="w-full py-2.5 rounded-xl text-sm font-medium transition-opacity disabled:opacity-50"
              style={{
                background: 'var(--gold)',
                color: '#0f0e0d',
              }}
            >
              {loading ? 'Redirecting...' : currentPlan === 'pro' ? 'Current plan' : 'Start free trial'}
            </button>
          </motion.div>
        </div>

        <p className="text-center text-xs mt-8" style={{ color: 'var(--text-muted)' }}>
          Cancel anytime. No questions asked. Billed by Stripe.
        </p>
      </div>
    </div>
  )
}
