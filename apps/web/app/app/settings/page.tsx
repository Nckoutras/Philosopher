'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ExternalLink, CreditCard, User, Trash2, Shield } from 'lucide-react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'

export default function SettingsPage() {
  const { user, clearAuth, subscription } = useStore()
  const router = useRouter()
  const [portalLoading, setPortalLoading] = useState(false)
  const plan = subscription?.plan ?? 'free'

  const { data: sub } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => api.getSubscription(),
  })

  const handleBillingPortal = async () => {
    setPortalLoading(true)
    try {
      const { portal_url } = await api.getPortalUrl()
      window.location.href = portal_url
    } catch {
      toast.error('Could not open billing portal')
      setPortalLoading(false)
    }
  }

  const handleLogout = () => {
    api.setToken(null)
    clearAuth()
    router.replace('/login')
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-xl mx-auto px-6 py-12">

        <motion.h1
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-2xl font-medium mb-10"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
        >
          Settings
        </motion.h1>

        {/* Account */}
        <Section icon={<User size={14} />} title="Account">
          <Row label="Email"   value={user?.email ?? '—'} />
          <Row label="Name"    value={user?.full_name ?? 'Not set'} />
          <Row label="Member since" value={user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' }) : '—'} />
        </Section>

        {/* Subscription */}
        <Section icon={<CreditCard size={14} />} title="Subscription">
          <Row
            label="Plan"
            value={
              <span className="capitalize font-medium" style={{ color: plan === 'free' ? 'var(--text-muted)' : 'var(--gold)' }}>
                {plan}
              </span>
            }
          />
          {sub?.status && <Row label="Status" value={<span className="capitalize">{sub.status}</span>} />}
          {sub?.current_period_end && (
            <Row
              label={sub.cancel_at_period_end ? 'Cancels on' : 'Renews on'}
              value={new Date(sub.current_period_end).toLocaleDateString()}
            />
          )}

          <div className="mt-4 flex flex-col gap-2">
            {plan === 'free' ? (
              <SettingsButton onClick={() => router.push('/upgrade')} primary>
                Upgrade to Pro
              </SettingsButton>
            ) : (
              <SettingsButton onClick={handleBillingPortal} loading={portalLoading} icon={<ExternalLink size={13} />}>
                Manage billing
              </SettingsButton>
            )}
          </div>
        </Section>

        {/* Privacy */}
        <Section icon={<Shield size={14} />} title="Privacy">
          <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            Your memory and conversations are private to your account. You can delete individual
            memory entries from the Memory page, or delete your entire account below.
          </p>
        </Section>

        {/* Danger zone */}
        <Section icon={<Trash2 size={14} />} title="Danger zone" danger>
          <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
            Signing out removes your session. Account deletion is permanent and removes all your data.
          </p>
          <div className="flex gap-2">
            <SettingsButton onClick={handleLogout}>
              Sign out
            </SettingsButton>
            <SettingsButton onClick={() => toast.error('Contact support to delete your account')} danger>
              Delete account
            </SettingsButton>
          </div>
        </Section>

      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Section({ icon, title, children, danger }: {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
  danger?: boolean
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-8 rounded-2xl p-6"
      style={{
        background: 'var(--bg-surface)',
        border: `1px solid ${danger ? 'rgba(139,80,80,0.3)' : 'var(--border)'}`,
      }}
    >
      <h2
        className="flex items-center gap-2 text-xs uppercase tracking-widest mb-5"
        style={{ color: danger ? '#c97070' : 'var(--text-muted)' }}
      >
        {icon}
        {title}
      </h2>
      {children}
    </motion.section>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
      <span className="text-sm" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{value}</span>
    </div>
  )
}

function SettingsButton({ children, onClick, loading, primary, danger, icon }: {
  children: React.ReactNode
  onClick: () => void
  loading?: boolean
  primary?: boolean
  danger?: boolean
  icon?: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-opacity disabled:opacity-50 hover:opacity-80"
      style={{
        background: primary ? 'var(--gold)' : danger ? 'rgba(139,80,80,0.15)' : 'var(--bg-secondary)',
        color: primary ? '#0f0e0d' : danger ? '#c97070' : 'var(--text-secondary)',
        border: danger ? '1px solid rgba(139,80,80,0.3)' : '1px solid var(--border)',
      }}
    >
      {icon}
      {loading ? 'Loading...' : children}
    </button>
  )
}
