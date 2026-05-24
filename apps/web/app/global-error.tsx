'use client'

import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error('Catastrophic error:', error)
  }, [error])

  const supportEmail = process.env.NEXT_PUBLIC_SUPPORT_EMAIL || 'nckoutras@gmail.com'

  // 'reset' intentionally unused — for catastrophic failures we prefer
  // a full page reload over an ORM reset that may re-throw the same error.
  void reset

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          padding: 0,
          background: '#EFE3CC',
          color: '#1F1B14',
          fontFamily: 'Georgia, serif',
        }}
      >
        <main className="min-h-screen flex flex-col bg-vellum text-ink">
          <header className="px-6 pt-8 flex justify-center">
            <span className="font-cormorant text-[14px] font-medium italic text-ink/60">
              Great Minds
            </span>
          </header>

          <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
            <h1 className="font-lora text-[28px] md:text-[32px] text-ink mb-4">
              Something went wrong.
            </h1>
            <p className="font-lora text-[16px] text-charcoal max-w-[420px] mb-10">
              We&apos;ve hit an unexpected problem. Please try reloading.
              If this keeps happening, email us at{' '}
              <a
                href={`mailto:${supportEmail}`}
                className="text-bronze underline"
              >
                {supportEmail}
              </a>
              .
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => window.location.reload()}
                className="bg-bronze text-white font-lora text-[14px] px-8 py-3 rounded-sm hover:bg-bronze-dark transition-colors"
              >
                Reload page
              </button>
              <a
                href={`mailto:${supportEmail}`}
                className="border border-ink text-ink font-lora text-[14px] px-8 py-3 rounded-sm hover:bg-ink hover:text-vellum transition-colors text-center"
              >
                Contact support
              </a>
            </div>
          </div>

          <footer className="px-6 pb-8 flex justify-center gap-4 text-[12px] text-sepia">
            <a href="/legal/privacy" className="hover:underline">Privacy</a>
            <span aria-hidden="true">·</span>
            <a href="/legal/terms" className="hover:underline">Terms</a>
          </footer>
        </main>
      </body>
    </html>
  )
}
