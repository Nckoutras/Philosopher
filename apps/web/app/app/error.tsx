'use client'

import { useEffect } from 'react'
import Link from 'next/link'

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error('App segment error:', error)
  }, [error])

  return (
    <main className="min-h-screen flex flex-col bg-vellum text-ink">
      <header className="px-6 pt-8 flex justify-center">
        <span className="font-cormorant text-[14px] font-medium italic text-ink/60">
          The Wise Room
        </span>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <div className="w-6 h-px bg-bronze mb-8" aria-hidden="true" />

        <h1 className="font-lora text-[28px] md:text-[32px] text-ink mb-4">
          Something quieted.
        </h1>
        <p className="font-lora text-[16px] text-charcoal max-w-[400px] mb-10">
          The companion will return shortly. Try again, or step back.
        </p>

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => reset()}
            className="bg-bronze text-white font-lora text-[14px] px-8 py-3 rounded-sm hover:bg-bronze-dark transition-colors"
          >
            Try again
          </button>
          <Link
            href="/app/today"
            className="border border-ink text-ink font-lora text-[14px] px-8 py-3 rounded-sm hover:bg-ink hover:text-vellum transition-colors text-center"
          >
            Return to Today
          </Link>
        </div>
      </div>

      <footer className="px-6 pb-8 flex justify-center gap-4 text-[12px] text-sepia">
        <Link href="/legal/privacy" className="hover:underline">Privacy</Link>
        <span aria-hidden="true">·</span>
        <Link href="/legal/terms" className="hover:underline">Terms</Link>
      </footer>
    </main>
  )
}
