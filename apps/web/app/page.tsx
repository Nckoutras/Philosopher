'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { Spinner } from '@/components/ui/Spinner'

export default function SplashPage() {
  const router = useRouter()

  useEffect(() => {
    async function check() {
      const start = Date.now()
      let path: string

      const { token } = useStore.getState()
      if (!token) {
        path = '/auth'
      } else {
        try {
          const user = await api.me()
          useStore.getState().setAuth(user, token)
          path = '/home'
        } catch {
          useStore.getState().clearAuth()
          path = '/auth'
        }
      }

      const elapsed = Date.now() - start
      if (elapsed < 500) await new Promise<void>((r) => setTimeout(r, 500 - elapsed))
      router.replace(path)
    }

    check()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <main className="h-screen [height:100svh] flex flex-col items-center justify-center bg-vellum">
      <div className="flex flex-col items-center gap-6">
        <h1 className="font-cormorant font-light text-[38px] text-ink text-center leading-tight">
          Great Minds
        </h1>
        <BronzeDivider />
        <Spinner />
      </div>
    </main>
  )
}
