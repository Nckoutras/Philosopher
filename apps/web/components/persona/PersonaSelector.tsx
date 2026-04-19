'use client'

import { clsx } from 'clsx'
import { Lock } from 'lucide-react'
import type { Persona } from '@/lib/api'

// ── PersonaCard ───────────────────────────────────────────────────────────────

interface PersonaCardProps {
  persona: Persona
  onSelect: (persona: Persona) => void
  isActive?: boolean
}

export function PersonaCard({ persona, onSelect, isActive }: PersonaCardProps) {
  return (
    <button
      onClick={() => persona.is_accessible && onSelect(persona)}
      className={clsx(
        'relative w-full text-left rounded-2xl p-5 transition-all duration-200',
        'border focus-visible:ring-2',
        isActive
          ? 'border-[var(--gold)] bg-[rgba(201,169,110,0.06)]'
          : 'border-[var(--border)] bg-[var(--bg-surface)] hover:border-[var(--border-strong)]',
        !persona.is_accessible && 'opacity-60 cursor-not-allowed',
      )}
    >
      {/* Tier badge */}
      {persona.tier !== 'free' && (
        <span
          className="absolute top-3 right-3 text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider font-medium"
          style={{ background: 'rgba(201,169,110,0.15)', color: 'var(--gold)', border: '1px solid rgba(201,169,110,0.3)' }}
        >
          {persona.tier}
        </span>
      )}

      <div className="flex items-start gap-3">
        <span className="text-2xl mt-0.5">{persona.avatar_emoji ?? '🏛️'}</span>
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-sm text-[var(--text-primary)]">{persona.name}</h3>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">{persona.era} · {persona.tradition}</p>
          {persona.tagline && (
            <p className="text-xs text-[var(--text-secondary)] mt-2 leading-relaxed line-clamp-2">
              {persona.tagline}
            </p>
          )}
        </div>
      </div>

      {!persona.is_accessible && (
        <div className="mt-3 flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <Lock size={11} />
          Upgrade to unlock
        </div>
      )}
    </button>
  )
}


// ── PersonaSelector ───────────────────────────────────────────────────────────

interface PersonaSelectorProps {
  personas: Persona[]
  activeSlug?: string
  onSelect: (persona: Persona) => void
  onUpgrade: () => void
}

export function PersonaSelector({ personas, activeSlug, onSelect, onUpgrade }: PersonaSelectorProps) {
  const free = personas.filter((p) => p.tier === 'free')
  const paid = personas.filter((p) => p.tier !== 'free')

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-xs uppercase tracking-widest text-[var(--text-muted)] mb-3 px-1">Free</h2>
        <div className="space-y-2">
          {free.map((p) => (
            <PersonaCard key={p.slug} persona={p} onSelect={onSelect} isActive={p.slug === activeSlug} />
          ))}
        </div>
      </section>

      {paid.length > 0 && (
        <section>
          <h2 className="text-xs uppercase tracking-widest text-[var(--text-muted)] mb-3 px-1">Pro</h2>
          <div className="space-y-2">
            {paid.map((p) => (
              <PersonaCard
                key={p.slug}
                persona={p}
                onSelect={(p) => {
                  if (!p.is_accessible) { onUpgrade(); return }
                  onSelect(p)
                }}
                isActive={p.slug === activeSlug}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
