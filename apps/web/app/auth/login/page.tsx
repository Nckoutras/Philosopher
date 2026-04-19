'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const router = useRouter()
  const { setAuth } = useStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await api.login(email, password)
      setAuth(data.user, data.access_token)
      router.replace('/app/dashboard')
    } catch (err: any) {
      toast.error(err.message ?? 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Welcome back.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthInput label="Email" type="email" value={email} onChange={setEmail} />
        <AuthInput label="Password" type="password" value={password} onChange={setPassword} />
        <AuthButton loading={loading}>Sign in</AuthButton>
      </form>
      <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
        No account?{' '}
        <Link href="/register" className="underline" style={{ color: 'var(--gold)' }}>
          Begin here
        </Link>
      </p>
    </AuthLayout>
  )
}
