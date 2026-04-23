'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import toast from 'react-hot-toast'
import { AuthLayout, AuthInput, AuthButton } from '@/components/ui/AuthComponents'

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
