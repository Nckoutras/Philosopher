'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const router = useRouter()
  const { setAuth } = useStore()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await api.register(email, password, name || undefined)
      setAuth(data.user, data.access_token)
      router.replace('/app/dashboard')
    } catch (err: any) {
      toast.error(err.message ?? 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Begin the practice.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthInput label="Name (optional)" type="text" value={name} onChange={setName} />
        <AuthInput label="Email" type="email" value={email} onChange={setEmail} required />
        <AuthInput label="Password" type="password" value={password} onChange={setPassword} required />
        <AuthButton loading={loading}>Create account</AuthButton>
      </form>
      <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
        Already a member?{' '}
        <Link href="/login" className="underline" style={{ color: 'var(--gold)' }}>
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}


// ── Shared auth components ────────────────────────────────────────────────────

export function AuthLayout({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="min-h-dvh flex items-center justify-center px-4"
      style={{ background: 'var(--bg-primary)' }}
    >
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-sm"
      >
        {/* Logo */}
        <div className="text-center mb-10">
          <span className="text-3xl">⚗️</span>
          <h1
            className="text-2xl font-medium mt-3"
            style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
          >
            {title}
          </h1>
        </div>

        <div
          className="rounded-2xl p-7"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
        >
          {children}
        </div>
      </motion.div>
    </div>
  )
}

interface InputProps {
  label: string
  type: string
  value: string
  onChange: (v: string) => void
  required?: boolean
}

export function AuthInput({ label, type, value, onChange, required }: InputProps) {
  return (
    <div>
      <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full px-3.5 py-2.5 rounded-xl text-sm outline-none transition-colors"
        style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
          color: 'var(--text-primary)',
        }}
        onFocus={(e) => (e.target.style.borderColor = 'var(--gold)')}
        onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
      />
    </div>
  )
}

interface BtnProps {
  children: React.ReactNode
  loading?: boolean
  onClick?: () => void
}

export function AuthButton({ children, loading, onClick }: BtnProps) {
  return (
    <button
      type={onClick ? 'button' : 'submit'}
      onClick={onClick}
      disabled={loading}
      className="w-full py-2.5 rounded-xl text-sm font-medium transition-opacity disabled:opacity-60"
      style={{ background: 'var(--gold)', color: '#0f0e0d', marginTop: '8px' }}
    >
      {loading ? 'Please wait...' : children}
    </button>
  )
}
