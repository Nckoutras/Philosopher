'use client'

import { useRouter } from 'next/navigation'
import { Zap, Lock } from 'lucide-react'
import { clsx } from 'clsx'

// ── UpgradeBanner ─────────────────────────────────────────────────────────────

interface BannerProps {
  className?: string
  message?: string
}

export function UpgradeBanner({ className, message }: BannerProps) {
  const router = useRouter()

  return (
    <div
      className={clsx('flex items-center gap-3 px-4 py-3 rounded-xl', className)}
      style={{
        background: 'rgba(201,169,110,0.07)',
        border: '1px solid rgba(201,169,110,0.2)',
      }}
    >
      <Zap size={14} style={{ color: 'var(--gold)', flexShrink: 0 }} />
      <p className="flex-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
        {message ?? 'Upgrade to Pro for all philosophers, memory, and insights.'}
      </p>
      <button
        onClick={() => router.push('/upgrade')}
        className="px-3 py-1 rounded-lg text-xs font-medium flex-shrink-0 transition-opacity hover:opacity-80"
        style={{ background: 'var(--gold)', color: '#0f0e0d' }}
      >
        Upgrade
      </button>
    </div>
  )
}


// ── PlanGate ──────────────────────────────────────────────────────────────────

interface PlanGateProps {
  requiredPlan: 'pro' | 'premium'
  userPlan: string
  children: React.ReactNode
  fallback?: React.ReactNode
}

const PLAN_ORDER = { free: 0, pro: 1, premium: 2 }

export function PlanGate({ requiredPlan, userPlan, children, fallback }: PlanGateProps) {
  const hasAccess =
    (PLAN_ORDER[userPlan as keyof typeof PLAN_ORDER] ?? 0) >=
    (PLAN_ORDER[requiredPlan] ?? 99)

  if (hasAccess) return <>{children}</>

  return (
    <>
      {fallback ?? (
        <div
          className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm"
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
          }}
        >
          <Lock size={13} />
          <span>This feature requires {requiredPlan}.</span>
        </div>
      )}
    </>
  )
}
