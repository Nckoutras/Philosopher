import Link from 'next/link'

export default function NotFound() {
  return (
    <main className="min-h-screen flex flex-col bg-vellum text-ink">
      <header className="px-6 pt-8 flex justify-center">
        <span className="font-cormorant text-[14px] font-medium italic text-ink/60">
          Great Minds
        </span>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <div className="w-6 h-px bg-bronze mb-8" aria-hidden="true" />

        <h1 className="font-lora text-[28px] md:text-[32px] text-ink mb-4">
          This page never was.
        </h1>
        <p className="font-lora text-[16px] text-charcoal max-w-[400px] mb-10">
          Try another path. The companion is waiting where you left it.
        </p>

        <Link
          href="/"
          className="inline-block bg-bronze text-white font-lora text-[14px] px-8 py-3 rounded-sm hover:bg-bronze-dark transition-colors"
        >
          Return to Today
        </Link>
      </div>

      <footer className="px-6 pb-8 flex justify-center gap-4 text-[12px] text-sepia">
        <Link href="/legal/privacy" className="hover:underline">Privacy</Link>
        <span aria-hidden="true">·</span>
        <Link href="/legal/terms" className="hover:underline">Terms</Link>
      </footer>
    </main>
  )
}
