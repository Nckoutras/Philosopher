'use client'
import { useEffect } from 'react'
export default function BodyScrollLock() {
  useEffect(() => {
    const b = document.body.style.overflow
    const h = document.documentElement.style.overflow
    document.body.style.overflow = 'hidden'
    document.documentElement.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = b
      document.documentElement.style.overflow = h
    }
  }, [])
  return null
}
