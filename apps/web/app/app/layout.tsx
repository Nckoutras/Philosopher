'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { AppSidebar } from '@/components/ui/AppSidebar'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user } = useStore()
  const router = useRouter()

  useEffect(() => {
    if (!user) router.replace('/login')
  }, [user, router])

  if (!user) return null

  return (
    <div className="flex h-dvh overflow-hidden">
      <AppSidebar />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
