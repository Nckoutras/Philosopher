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
    <div className="min-h-dvh flex items-center justify-center px-4" style={{ background: 'var(--bg-primary)' }}>
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full max-w-sm">
        <div className="text-center mb-10">
          <span className="text-3xl">⚗️</span>
          <h1 className="text-2xl font-medium mt-3" style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}>Begin the practice.</h1>
        </div>
        <div className="rounded-2xl p-7" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>Name (optional)</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full px-3.5 py-2.5 rounded-xl text-sm outline-none" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full px-3.5 py-2.5 rounded-xl text-sm outline-none" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required className="w-full px-3.5 py-2.5 rounded-xl text-sm outline-none" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)' }} />
            </div>
            <button type="submit" disabled={loading} className="w-full py-2.5 rounded-xl text-sm font-medium transition-opacity disabled:opacity-60" style={{ background: 'var(--gold)', color: '#0f0e0d', marginTop: '8px' }}>
              {loading ? 'Please wait...' : 'Create account'}
            </button>
          </form>
          <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            Already a member?{' '}
            <Link href="/auth/login" className="underline" style={{ color: 'var(--gold)' }}>Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
