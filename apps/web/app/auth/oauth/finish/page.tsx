'use client'

import { Suspense, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

export const dynamic = 'force-dynamic'

function OAuthFinish() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const attempted = useRef(false)

  useEffect(() => {
    if (attempted.current) return
    attempted.current = true

    const token = searchParams.get('token')
    const needsDisclaimer = searchParams.get('needs_disclaimer') === '1'

    if (!token) {
      toast.error('Sign-in failed. Please try again.')
      router.replace('/auth?error=oauth_no_token')
      return
    }

    async function finish() {
      try {
        api.setToken(token)
        const user = await api.me()
        useStore.getState().setAuth(user, token)
        if (needsDisclaimer) {
          router.replace('/auth/disclaimer')
        } else {
          router.replace('/app/today')
        }
      } catch {
        api.setToken(null)
        toast.error('Sign-in failed. Please try again.')
        router.replace('/auth')
      }
    }

    finish()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum">
      <p className="font-lora text-[13px] text-charcoal">Signing you in…</p>
    </main>
  )
}

export default function OAuthFinishPage() {
  return (
    <Suspense fallback={null}>
      <OAuthFinish />
    </Suspense>
  )
}
