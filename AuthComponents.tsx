'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

export function AuthLayout({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex items-center justify-center px-4" style={{ background: 'var(--bg-primary)' }}>
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full max-w-sm">
        <div className="text-center mb-10">
          <span className="text-3xl">⚗️</span>
          <h1 className="text-2xl font-medium mt-3" style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}>{title}</h1>
        </div>
        <div className="rounded-2xl p-7" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          {children}
        </div>
      </motion.div>
    </div>
  )
}

export function AuthInput({ label, type, value, onChange, required }: {
  label: string; type: string; value: string; onChange: (v: string) => void; required?: boolean
}) {
  return (
    <div>
      <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} required={required}
        className="w-full px-3.5 py-2.5 rounded-xl text-sm outline-none"
        style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
      />
    </div>
  )
}

export function AuthButton({ children, loading, onClick }: {
  children: React.ReactNode; loading?: boolean; onClick?: () => void
}) {
  return (
    <button type={onClick ? 'button' : 'submit'} onClick={onClick} disabled={loading}
      className="w-full py-2.5 rounded-xl text-sm font-medium transition-opacity disabled:opacity-60"
      style={{ background: 'var(--gold)', color: '#0f0e0d', marginTop: '8px' }}>
      {loading ? 'Please wait...' : children}
    </button>
  )
}
