'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ExplorePage() {
  const router = useRouter()
  useEffect(() => {
    router.replace('/app/library?mode=browse')
  }, [router])
  return null
}
