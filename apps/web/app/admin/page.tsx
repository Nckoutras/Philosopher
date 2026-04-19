'use client'

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Users, ShieldAlert, TrendingUp, Search } from 'lucide-react'
import { api } from '@/lib/api'

export default function AdminPage() {
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState('')

  const { data: summary } = useQuery({
    queryKey: ['admin-summary'],
    queryFn: () => api.request<any>('/admin/analytics/summary'),
    refetchInterval: 30_000,
  })

  const { data: users = [] } = useQuery({
    queryKey: ['admin-users', search],
    queryFn: () => api.request<any[]>(`/admin/users?search=${search}&limit=50`),
  })

  const { data: safetyEvents = [] } = useQuery({
    queryKey: ['safety-events', riskFilter],
    queryFn: () => api.request<any[]>(`/admin/safety-events?risk_level=${riskFilter}&limit=100`),
  })

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-12">

        <h1
          className="text-2xl font-medium mb-10"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
        >
          Admin
        </h1>

        {/* KPI row */}
        {summary && (
          <div className="grid grid-cols-3 gap-4 mb-10">
            <KPICard icon={<Users size={14} />}       label="Total users"     value={summary.total_users} />
            <KPICard icon={<TrendingUp size={14} />}  label="Paying users"    value={`${summary.paying_users} (${summary.conversion_rate}%)`} gold />
            <KPICard icon={<ShieldAlert size={14} />} label="High-risk safety" value={summary.high_safety_events} warn={summary.high_safety_events > 0} />
          </div>
        )}

        {/* Safety events */}
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Safety events</h2>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg outline-none"
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                color: 'var(--text-secondary)',
              }}
            >
              <option value="">All levels</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div
            className="rounded-2xl overflow-hidden"
            style={{ border: '1px solid var(--border)' }}
          >
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                  {['When', 'Stage', 'Level', 'Category', 'Action'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 font-medium" style={{ color: 'var(--text-muted)' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {safetyEvents.slice(0, 20).map((e: any) => (
                  <tr key={e.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td className="px-4 py-3" style={{ color: 'var(--text-muted)' }}>
                      {new Date(e.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-secondary)' }}>{e.trigger_stage}</td>
                    <td className="px-4 py-3">
                      <RiskBadge level={e.risk_level} />
                    </td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-secondary)' }}>{e.category ?? '—'}</td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-secondary)' }}>{e.action_taken}</td>
                  </tr>
                ))}
                {safetyEvents.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                      No safety events
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Users */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Users</h2>
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
            >
              <Search size={12} style={{ color: 'var(--text-muted)' }} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search email..."
                className="text-xs bg-transparent outline-none w-40"
                style={{ color: 'var(--text-secondary)' }}
              />
            </div>
          </div>
          <div
            className="rounded-2xl overflow-hidden"
            style={{ border: '1px solid var(--border)' }}
          >
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                  {['Email', 'Name', 'Plan', 'Status', 'Joined'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 font-medium" style={{ color: 'var(--text-muted)' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((u: any) => (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td className="px-4 py-3" style={{ color: 'var(--text-secondary)' }}>{u.email}</td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-muted)' }}>{u.full_name ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className="px-2 py-0.5 rounded-full capitalize"
                        style={{
                          background: u.plan !== 'free' ? 'rgba(201,169,110,0.1)' : 'var(--bg-secondary)',
                          color: u.plan !== 'free' ? 'var(--gold)' : 'var(--text-muted)',
                        }}
                      >
                        {u.plan}
                      </span>
                    </td>
                    <td className="px-4 py-3 capitalize" style={{ color: 'var(--text-muted)' }}>{u.status}</td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-muted)' }}>
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KPICard({ icon, label, value, gold, warn }: {
  icon: React.ReactNode; label: string; value: any; gold?: boolean; warn?: boolean
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="px-5 py-4 rounded-2xl"
      style={{
        background: 'var(--bg-surface)',
        border: `1px solid ${warn ? 'rgba(139,80,80,0.3)' : 'var(--border)'}`,
      }}
    >
      <div className="flex items-center gap-1.5 mb-2" style={{ color: gold ? 'var(--gold)' : warn ? '#c97070' : 'var(--text-muted)' }}>
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-xl font-medium" style={{ color: 'var(--text-primary)' }}>{value}</p>
    </motion.div>
  )
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    high: '#c97070', medium: '#c9a96e', low: '#6b8b6b', none: '#5a574f',
  }
  return (
    <span
      className="px-2 py-0.5 rounded-full capitalize text-[10px]"
      style={{ background: colors[level] + '1a', color: colors[level] ?? 'var(--text-muted)' }}
    >
      {level}
    </span>
  )
}
