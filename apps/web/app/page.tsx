import Link from 'next/link'
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Philosopher — Think with the great minds of history',
}

export default function LandingPage() {
  return (
    <main
      className="min-h-dvh flex flex-col items-center justify-center px-6 text-center"
      style={{ background: 'var(--bg-primary)' }}
    >
      <div className="max-w-lg">
        <div className="text-5xl mb-8">⚗️</div>

        <h1
          className="text-4xl font-medium leading-tight mb-5"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
        >
          Think with the great minds of history
        </h1>

        <p className="text-base mb-10" style={{ color: 'var(--text-secondary)', lineHeight: 1.75 }}>
          A premium AI reflective companion grounded in historical philosophy.
          Not therapy. Not self-help. A discipline.
        </p>

        <div className="flex items-center justify-center gap-3">
          <Link
            href="/register"
            className="px-6 py-3 rounded-xl text-sm font-medium transition-opacity hover:opacity-80"
            style={{ background: 'var(--gold)', color: '#0f0e0d' }}
          >
            Begin for free
          </Link>
          <Link
            href="/login"
            className="px-6 py-3 rounded-xl text-sm transition-opacity hover:opacity-70"
            style={{
              background: 'var(--bg-surface)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
            }}
          >
            Sign in
          </Link>
        </div>

        {/* Social proof placeholder */}
        <p className="mt-10 text-xs" style={{ color: 'var(--text-muted)' }}>
          Free to start · 7-day Pro trial · Cancel anytime
        </p>

        {/* Philosopher preview names */}
        <div className="mt-14 flex flex-wrap justify-center gap-3">
          {[
            { name: 'Marcus Aurelius', emoji: '🏛️', tier: 'free' },
            { name: 'Simone de Beauvoir', emoji: '📖', tier: 'pro' },
            { name: 'Epictetus', emoji: '⛓️', tier: 'pro' },
            { name: 'Nietzsche', emoji: '⚡', tier: 'pro' },
          ].map(({ name, emoji, tier }) => (
            <div
              key={name}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs"
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                color: 'var(--text-secondary)',
              }}
            >
              <span>{emoji}</span>
              <span>{name}</span>
              {tier !== 'free' && (
                <span
                  className="text-[10px] px-1.5 rounded-full"
                  style={{ background: 'rgba(201,169,110,0.12)', color: 'var(--gold)' }}
                >
                  Pro
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}
